const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{execFileSync}=require('node:child_process'),{createHash}=require('node:crypto')
const esbuild=require(process.env.ESBUILD_PATH||'esbuild'),repo=path.resolve(process.argv[2]),revision='73d57b37b9d4f9e9145814da51b98f5b17a486b0'
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'levelread-primary-build.'))
try{
 const archive=execFileSync('git',['-C',repo,'archive',revision,'lib','types','tsconfig.json'],{maxBuffer:67108864});execFileSync('tar',['-xf','-','-C',tmp],{input:archive})
 const output=path.join(__dirname,'pg-primary-runtime.cjs')
 esbuild.buildSync({entryPoints:[path.join(__dirname,'pg-primary-ingest.ts')],outfile:output,bundle:true,platform:'node',format:'cjs',external:['pg'],alias:{'website-primary':path.join(tmp,'lib/db/pg-primary.ts'),'website-config':path.join(tmp,'lib/replication/config.ts'),'@':tmp},tsconfig:path.join(tmp,'tsconfig.json')})
 fs.writeFileSync(path.join(__dirname,'pg-primary-provenance.json'),JSON.stringify({websiteRevision:revision,sourceSha256:createHash('sha256').update(fs.readFileSync(path.join(__dirname,'pg-primary-ingest.ts'))).digest('hex'),outputSha256:createHash('sha256').update(fs.readFileSync(output)).digest('hex')},null,2)+'\n')
}finally{fs.rmSync(tmp,{recursive:true,force:true})}
