const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{execFileSync}=require('node:child_process'),{createHash}=require('node:crypto')
const esbuild=require(process.env.ESBUILD_PATH||'esbuild'),repo=path.resolve(process.argv[2]),revision='5118f5f92d798b3f670eaccc5ff8343dd99065b0'
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'levelread-primary-build.'))
try{
 const archive=execFileSync('git',['-C',repo,'archive',revision,'lib','types','tsconfig.json','scripts/migrations/cloudbase-pg','scripts/migrations/pg-relational-model','scripts/migrations/pg-json-storage','scripts/test-pg-current-schema.cjs'],{maxBuffer:67108864});execFileSync('tar',['-xf','-','-C',tmp],{input:archive})
 const schema=require(path.join(tmp,'scripts/test-pg-current-schema.cjs')).sql(tmp)
 fs.mkdirSync(path.join(__dirname,'../test'),{recursive:true});fs.writeFileSync(path.join(__dirname,'../test/primary-schema.sql'),schema)
 const output=path.join(__dirname,'pg-primary-runtime.cjs')
 fs.copyFileSync(path.join(__dirname,'pg-primary-ingest.ts'),path.join(tmp,'scripts/pg-primary-ingest.ts'))
 esbuild.buildSync({absWorkingDir:tmp,entryPoints:[path.join(tmp,'scripts/pg-primary-ingest.ts')],outfile:output,bundle:true,platform:'node',format:'cjs',external:['pg'],alias:{'website-primary':path.join(tmp,'lib/db/pg-primary.ts'),'website-config':path.join(tmp,'lib/postgres/config.ts'),'@':tmp},tsconfig:path.join(tmp,'tsconfig.json')})
 fs.writeFileSync(path.join(__dirname,'pg-primary-provenance.json'),JSON.stringify({websiteRevision:revision,schemaSha256:createHash('sha256').update(schema).digest('hex'),sourceSha256:createHash('sha256').update(fs.readFileSync(path.join(__dirname,'pg-primary-ingest.ts'))).digest('hex'),outputSha256:createHash('sha256').update(fs.readFileSync(output)).digest('hex')},null,2)+'\n')
}finally{fs.rmSync(tmp,{recursive:true,force:true})}
