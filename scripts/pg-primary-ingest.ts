import { createHash } from 'node:crypto'
import { Pool } from 'pg'
import {createPrimaryDatabase} from 'website-primary'
import {poolOptions} from 'website-config'
const currentLanguages = ['zh-CN', 'zh-TW', 'ja', 'ru', 'es', 'pt-BR']
const legacyLanguages = ['zh-CN', 'zh-TW', 'ja', 'ko', 'es', 'pt-BR']
function stable(value:any):any {return Array.isArray(value)?value.map(stable):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,stable(value[k])])):value}
export async function ingest(database:any,request:any){
 const {package:news,titleTranslations:titles,bodyTranslations:bodies}=request
 if(!news||news.public!==false||typeof news.titleid!=='string'||!/^[a-z0-9][a-z0-9-]{0,199}$/.test(news.titleid)||!Array.isArray(titles)||!Array.isArray(bodies))throw Error('ingest_scope')
 // The publisher sets this flag only when resuming a matching legacy receipt.
 const languages = request.legacyTranslationRetry === true ? legacyLanguages : currentLanguages
 for (const rows of [titles, bodies]) {
  if (rows.length !== languages.length || languages.some(code => rows.filter((row:any) => row?.languageCode === code).length !== 1)) {
   throw Error('ingest_languages')
  }
 }
 const digest=createHash('sha256').update(JSON.stringify(stable({news,titles,bodies}))).digest('hex')
 const id='news-'+createHash('sha256').update(news.titleid).digest('hex'),now=Date.now()
 const titleIds=languages.map(l=>id+'-title-'+l),bodyIds=languages.map(l=>id+'-body-'+l)
 return database.runTransaction(async(tx:any)=>{
  // Serialize only this deterministic news ID, including the absent-row case.
  await tx.collection('enil_news').doc(id).get()
  const existing=(await tx.collection('enil_news').where({titleid:news.titleid}).limit(2).get()).data
  if(existing.length){
   if(existing.length!==1||existing[0]._id!==id||existing[0].ingestDigest!==digest)throw Error('ingest_titleid_conflict')
   for(let i=0;i<6;i++)for(const [collection,ids]of [['enli_news_title_translation',titleIds],['enli_news_translation',bodyIds]]as const){
    const record=(await tx.collection(collection).doc(ids[i]).get()).data
    if(!record||record.newsId!==id||record.languageCode!==languages[i])throw Error('ingest_receipt_incomplete')
   }
   return {ok:true,status:'ingested',id,titleTranslationIds:titleIds,bodyTranslationIds:bodyIds,total:13,reused:true}
  }
  // The shared facade supports upserts. Ingestion must never overwrite an
  // unrelated physical row or an existing logical translation binding.
  if((await tx.collection('enil_news').doc(id).get()).data)throw Error('ingest_titleid_conflict')
  for(let i=0;i<6;i++)for(const [collection,ids]of [['enli_news_title_translation',titleIds],['enli_news_translation',bodyIds]]as const){
   if((await tx.collection(collection).doc(ids[i]).get()).data)throw Error('ingest_titleid_conflict')
   if((await tx.collection(collection).where({newsId:id,languageCode:languages[i]}).limit(1).get()).data.length)throw Error('ingest_titleid_conflict')
  }
  await tx.collection('enil_news').doc(id).set({...news,ingestDigest:digest})
  for(let i=0;i<6;i++){
   const title=titles.find((r:any)=>r.languageCode===languages[i]);const body=bodies.find((r:any)=>r.languageCode===languages[i])
   await tx.collection('enli_news_title_translation').doc(titleIds[i]).set({...title,newsId:id,status:'READY',provider:'codex',version:'v1',createdAt:now,updatedAt:now})
   await tx.collection('enli_news_translation').doc(bodyIds[i]).set({...body,newsId:id})
  }
  return {ok:true,status:'ingested',id,titleTranslationIds:titleIds,bodyTranslationIds:bodyIds,total:13,reused:false}
 })
}
export async function inspectStory(database:any, request:any) {
  const news=request.package;
  if (!news || typeof news.titleid!=="string" || !Array.isArray(request.titleTranslations) || !Array.isArray(request.bodyTranslations)) throw Error("inspect_scope");
  return database.runReadTransaction(async (tx:any)=>{
    const rows=(await tx.collection("enil_news").where({titleid:news.titleid}).limit(2).get()).data;
    if (!rows.length) return {ok:true,status:"missing",total:0};
    if (rows.length!==1) return {ok:false,status:"conflict",total:rows.length};
    const row=rows[0];
    const titles=(await tx.collection("enli_news_title_translation").where({newsId:row._id}).limit(100).get()).data;
    const bodies=(await tx.collection("enli_news_translation").where({newsId:row._id}).limit(100).get()).data;
    const equal=(a:any,b:any)=>JSON.stringify(stable(a))===JSON.stringify(stable(b));
    const subset=(actual:any,expected:any)=>Object.keys(expected).every(k=>equal(actual[k],expected[k]));
    const compareTranslations = (actual: any[], expected: any[]) => {
      const expectedLanguages = new Set(expected.map(row => row.languageCode));
      const rowsByLanguage = new Map<string, any[]>();
      for (const row of actual) {
        const matching = rowsByLanguage.get(row.languageCode) ?? [];
        matching.push(row);
        rowsByLanguage.set(row.languageCode, matching);
      }
      const check = (predicate: (row: any, expected: any) => boolean) =>
        expected.length === 6 && expectedLanguages.size === 6 && expected.every(row => {
          const matching = rowsByLanguage.get(row.languageCode);
          return matching?.length === 1 && predicate(matching[0], row);
        });
      const extras = [...rowsByLanguage.keys()].filter(code => !expectedLanguages.has(code)).sort();
      return {check, extras};
    };
    const comparedTitles = compareTranslations(titles, request.titleTranslations);
    const comparedBodies = compareTranslations(bodies, request.bodyTranslations);
    return {ok:true,status:"existing",id:row._id,public:row.public,
      newsMatches:subset(row,news),titleMatches:comparedTitles.check(subset),bodyMatches:comparedBodies.check(subset),
      titlesReady:comparedTitles.check(row => row.status === "READY"),
      extraTitleLanguages:comparedTitles.extras,extraBodyLanguages:comparedBodies.extras,
      titleTranslationIds:titles.map((r:any)=>r._id),bodyTranslationIds:bodies.map((r:any)=>r._id),
      total:1+titles.length+bodies.length};
  });
}

export async function run(request:any){
 const pool=new Pool({...poolOptions(),application_name:'levelread-production-primary'});const db=createPrimaryDatabase(pool)
 try{
  if(request.action==='check'){await db.runReadTransaction(async()=>{});return{ok:true,status:'ready'}}
  if(request.action==='inspect')return await inspectStory(db,request)
  if(request.action!=='ingest')throw Error('ingest_action')
  return await ingest(db,request)
 }catch(error){return{ok:false,status:(error as Error).message==='ingest_titleid_conflict'?'conflict':'unavailable'}}finally{await pool.end()}
}

export {createPrimaryDatabase}
