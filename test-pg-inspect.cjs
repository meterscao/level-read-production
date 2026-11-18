'use strict';
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
let queries=[],documents={};
class Pool {
 async connect(){return {on(){},removeListener(){},release(){},async query(sql){queries.push(sql);if(sql.startsWith('WITH documents AS')){const name=sql.match(/FROM public\.(\w+) t/)[1];return {rows:(documents[name]||[]).map(d=>({d}))};}if(sql==='COMMIT')return {rows:[],command:'COMMIT'};if(sql==='ROLLBACK')return {rows:[],command:'ROLLBACK'};return {rows:[],command:'OK'};}};}
 async end(){}
}
const mod={exports:{}},context={URL,module:mod,exports:mod.exports,console,process:{env:{DATABASE_URL:'postgresql://test:unused@invalid/levelread_prod',PG_SSL_CA_FILE:'unused'}},require(name){if(name==='pg')return {Pool};if(name==='node:fs')return {readFileSync(){return '-----BEGIN CERTIFICATE-----';}};return require(name);}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
const api=mod.exports,lang=['zh-CN','zh-TW','ja','ko','es','pt-BR'];
const request={action:'inspect',package:{titleid:'test-story',title:'Example',summary:'Summary',public:false,levels:[]},titleTranslations:lang.map(languageCode=>({languageCode,title:'Title'})),bodyTranslations:lang.map(languageCode=>({languageCode,title:'Title',summary:'Summary',levels:[]}))};
const news={...request.package,_id:'news-test'},titles=request.titleTranslations.map((t,i)=>({...t,_id:'title-'+i,newsId:'news-test',status:'READY'})),bodies=request.bodyTranslations.map((t,i)=>({...t,_id:'body-'+i,newsId:'news-test'}));
async function inspect(rows){documents=rows;queries=[];const result=await api.run(JSON.parse(JSON.stringify(request)));assert(queries.every(q=>!/^\s*(INSERT|UPDATE|DELETE|TRUNCATE)/i.test(q)));assert(!queries.some(q=>q.includes("levelread.business_write")));return result;}
(async()=>{
 let r=await inspect({});assert.equal(r.status,'missing');assert(queries.some(q=>q==='BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY'));
 const rows={enil_news:[news],enli_news_title_translation:titles,enli_news_translation:bodies};
 r=await inspect(rows);assert.equal(r.id,'news-test');assert.equal(r.public,false);assert.equal(r.total,13);for(const k of ['newsMatches','titleMatches','bodyMatches','titlesReady'])assert.equal(r[k],true);
 const cachedTitles=[...titles,{_id:'ru-title',newsId:news._id,languageCode:'ru',title:'',status:'PROCESSING'}];
 const cachedBodies=[...bodies,{_id:'ru-body',newsId:news._id,languageCode:'ru',title:'Cached'}];
 r=await inspect({...rows,enli_news_title_translation:cachedTitles,enli_news_translation:cachedBodies});
 assert.equal(r.total,15);
 for (const key of ['titleMatches','bodyMatches','titlesReady']) assert.equal(r[key],true);
 assert.deepEqual(Array.from(r.extraTitleLanguages),['ru']);
 assert.deepEqual(Array.from(r.extraBodyLanguages),['ru']);
 r=await inspect({...rows,enli_news_title_translation:[...cachedTitles,{...titles[0],_id:'duplicate-title'}]});
 assert.equal(r.titleMatches,false);assert.equal(r.titlesReady,false);
 r=await inspect({...rows,enil_news:[{...news,public:true}]});assert.equal(r.public,true);assert.equal(r.newsMatches,false);
 r=await inspect({...rows,enli_news_title_translation:[{...titles[0],title:'Wrong'},...titles.slice(1)]});assert.equal(r.titleMatches,false);
 r=await inspect({...rows,enli_news_translation:bodies.slice(1)});assert.equal(r.bodyMatches,false);
 r=await inspect({...rows,enil_news:[news,{...news,_id:'duplicate'}]});assert.equal(r.status,'conflict');assert.equal(r.ok,false);
 console.log('Inspect regression passed: read-only transaction, requested languages, extra caches, published state and conflicts.');
})().catch(e=>{console.error(e);process.exitCode=1;});
