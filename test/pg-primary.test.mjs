import {verifyLockPolicy} from './lock-policy-contract.mjs'
import test from'node:test';import assert from'node:assert/strict';import{createRequire}from'node:module';import{createHash}from'node:crypto';import{readFileSync}from'node:fs';
const require=createRequire(import.meta.url),{Pool}=require('pg'),{createPrimaryDatabase,ingest,inspectStory}=require(process.env.LEVELREAD_TEST_RUNTIME || '../scripts/pg-primary-runtime.cjs');const socket=process.env.PG_PRIMARY_TEST_SOCKET;
test('production ingest commits all thirteen records once on real PostgreSQL',{skip:!socket},async t=>{
 const pool=new Pool({host:socket,port:55449,database:'pg_primary_test',max:6});await pool.query(readFileSync(new URL('./primary-schema.sql',import.meta.url),'utf8'));const db=createPrimaryDatabase(pool)
 const languages=['zh-CN','zh-TW','ja','ru','es','pt-BR'];const request={action:'ingest',package:{titleid:'atomic-fixture',title:'Fixture',cover:'https://example.test/cover.png',originalUrl:'https://example.test/story',summary:'Unpublished fixture',public:false,readCount:0,date:1,levels:[]},titleTranslations:languages.map(languageCode=>({languageCode,title:'Translated'})),bodyTranslations:languages.map(languageCode=>({languageCode,title:'Translated',summary:'Fixture',levels:[]}))}
 try{
 await t.test('late translation failure rolls back news and all earlier translations',async()=>{
  await pool.query("CREATE FUNCTION fail_translation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.language_code='pt-BR' THEN RAISE EXCEPTION 'fixture_failure'; END IF; RETURN NEW; END $$; CREATE TRIGGER fixture_failure BEFORE INSERT ON public.enli_news_translation FOR EACH ROW EXECUTE FUNCTION fail_translation()")
  try{await assert.rejects(ingest(db,request),/fixture_failure/)}finally{await pool.query('DROP TRIGGER fixture_failure ON public.enli_news_translation; DROP FUNCTION fail_translation()')}
  for(const collection of ['enil_news','enli_news_title_translation','enli_news_translation'])assert.equal((await db.collection(collection).count()).total,0)
 })
 await t.test('concurrent identical retry creates one news and twelve READY/reader translations',async()=>{
  const results=await Promise.all(Array.from({length:4},()=>ingest(db,request)));assert.equal(results.filter(r=>r.reused).length,3)
  assert.equal((await db.collection('enil_news').count()).total,1);assert.equal((await db.collection('enli_news_title_translation').where({status:'READY'}).count()).total,6);assert.equal((await db.collection('enli_news_translation').count()).total,6)
  const news=(await db.collection('enil_news').get()).data[0];assert.equal(news.public,false)
  for (const collection of ['enli_news_title_translation', 'enli_news_translation']) {
   const rows = (await db.collection(collection).get()).data
   assert.deepEqual(rows.map(row => row.languageCode).sort(), [...languages].sort())
   for (const row of rows) assert.equal(row.newsId, news._id)
  }
 })
 await t.test('same titleid with changed payload fails instead of modifying existing story',async()=>{
  await assert.rejects(ingest(db,{...request,package:{...request.package,title:'Changed'}}),/ingest_titleid_conflict/)
  assert.equal((await db.collection('enil_news').get()).data[0].title,'Fixture')
 })
 await t.test('physical and logical translation conflicts never overwrite records',async()=>{
  const candidate={...request,package:{...request.package,titleid:'conflicting-fixture'}}
  const id='news-'+createHash('sha256').update(candidate.package.titleid).digest('hex')
  const collection='enli_news_title_translation',target=id+'-title-zh-CN'
  await db.collection(collection).doc(target).set({newsId:'another-news',languageCode:'zh-CN',title:'Keep me',status:'READY',provider:'fixture',version:'v1',createdAt:1,updatedAt:1})
  await assert.rejects(ingest(db,candidate),/ingest_titleid_conflict/)
  assert.equal((await db.collection('enil_news').doc(id).get()).data,null)
  assert.equal((await db.collection(collection).doc(target).get()).data.title,'Keep me')
  await db.collection(collection).doc(target).remove()
  await db.collection(collection).doc('different-physical-id').set({newsId:id,languageCode:'zh-CN',title:'Keep binding',status:'READY',provider:'fixture',version:'v1',createdAt:1,updatedAt:1})
  await assert.rejects(ingest(db,candidate),/ingest_titleid_conflict/)
  assert.equal((await db.collection('enil_news').doc(id).get()).data,null)
  await db.collection(collection).doc('different-physical-id').remove()
 })
 await t.test('deleted package IDs may be legitimately recreated without migration tables',async()=>{
  const original=await ingest(db,request)
  await db.runTransaction(async tx=>{
   for(const [collection,ids]of [['enli_news_title_translation',original.titleTranslationIds],['enli_news_translation',original.bodyTranslationIds],['enil_news',[original.id]]])for(const id of ids)await tx.collection(collection).doc(id).remove()
  })
  const recreated=await ingest(db,request)
  assert.equal(recreated.id,original.id);assert.equal(recreated.reused,false)
  for(const table of ['pg_primary_authority','pg_primary_owned_fields','pg_sync_guard_config','pg_sync_record_state','pg_sync_domain_state','pg_sync_deletion_log'])assert.equal((await pool.query('SELECT to_regclass($1) AS name',['public.'+table])).rows[0].name,null)
 })
 await t.test('legacy translations require retry mode and preserve deterministic replay', async () => {
  const useKorean = rows => rows.map(row => row.languageCode === 'ru' ? {...row, languageCode: 'ko'} : row)
  const legacy = {
   ...request,
   package: {...request.package, titleid: 'legacy-languages-fixture'},
   titleTranslations: useKorean(request.titleTranslations),
   bodyTranslations: useKorean(request.bodyTranslations),
  }
  const news = db.collection('enil_news').where({titleid: legacy.package.titleid})
  await assert.rejects(ingest(db, legacy), /ingest_languages/)
  await assert.rejects(ingest(db, {...legacy, titleTranslations: request.titleTranslations}), /ingest_languages/)
  await assert.rejects(ingest(db, {...legacy, bodyTranslations: request.bodyTranslations, legacyTranslationRetry: true}), /ingest_languages/)
  assert.equal((await news.count()).total, 0)
  const original = await ingest(db, {...legacy, legacyTranslationRetry: true})
  const retry = await ingest(db, {...legacy, legacyTranslationRetry: true})
  assert.equal(retry.reused, true)
  assert.deepEqual(retry.titleTranslationIds, original.titleTranslationIds)
  assert.deepEqual(retry.bodyTranslationIds, original.bodyTranslationIds)
  assert(retry.titleTranslationIds.some(id => id.endsWith('-ko')))
  assert(!retry.bodyTranslationIds.some(id => id.endsWith('-ru')))
  const inspected = await inspectStory(db, legacy)
  for (const key of ['newsMatches', 'titleMatches', 'bodyMatches', 'titlesReady']) assert.equal(inspected[key], true)
  await db.collection('enli_news_title_translation').doc('fixture-ru-title').set({
   newsId: original.id, languageCode: 'ru', status: 'PROCESSING', title: '',
   provider: 'fixture', version: 'v1', createdAt: 2, updatedAt: 2,
  })
  await db.collection('enli_news_translation').doc('fixture-ru-body').set({
   newsId: original.id, languageCode: 'ru', title: 'Cached title', summary: 'Cached summary', levels: [],
  })
  const withCaches = await inspectStory(db, legacy)
  for (const key of ['newsMatches', 'titleMatches', 'bodyMatches', 'titlesReady']) assert.equal(withCaches[key], true)
  assert.equal(withCaches.total, 15)
  assert.deepEqual(withCaches.extraTitleLanguages, ['ru'])
  assert.deepEqual(withCaches.extraBodyLanguages, ['ru'])
  await assert.rejects(ingest(db, {
   ...legacy, legacyTranslationRetry: true, package: {...legacy.package, title: 'Changed'},
  }), /ingest_titleid_conflict/)
 })
 await verifyLockPolicy(t,db,pool)
}finally{await pool.end()}
})
