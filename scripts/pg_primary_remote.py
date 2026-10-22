"""Use the running Website's PG runtime; credentials never leave its container."""
import json
import re
import subprocess
from pathlib import Path


def remote_program(request, runtime, service):
    return '\n'.join([
        'import subprocess,json', 'request='+repr(request), 'runtime='+repr(runtime), 'service='+repr(service),
        '''try:
 tasks=subprocess.check_output(['docker','service','ps','--filter','desired-state=running','--format','{{.ID}}',service],text=True).split()
 if len(tasks)!=1: raise RuntimeError('ambiguous_service')
 task=json.loads(subprocess.check_output(['docker','inspect','--type','task',tasks[0]]))[0]
 if task['Status']['State']!='running': raise RuntimeError('not_running')
 cid=task['Status']['ContainerStatus']['ContainerID']
 code=runtime+'\\nmodule.exports.run('+json.dumps(request)+').then(r=>console.log(JSON.stringify(r))).catch(()=>console.log(JSON.stringify({ok:false,status:"unavailable"})));'
 result=subprocess.run(['docker','exec','-i','-w','/app',cid,'node'],input=code,capture_output=True,text=True,timeout=90)
 lines=result.stdout.splitlines()
 print(lines[-1] if result.returncode==0 and lines else json.dumps({'ok':False,'status':'unavailable'}))
except Exception:
 print(json.dumps({'ok':False,'status':'unavailable'}))'''])


def pg_primary(config, request):
    options=config.get('pg_primary', {})
    host=options.get('ssh_host', 'qcloud-CD')
    service=options.get('service', 'levelread-levelreadwebsite-2jbjx9')
    if not all(isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}',value) for value in (host,service)):
        raise RuntimeError('Invalid PG runtime configuration')
    if request.get('action') not in ('check','ingest'):
        raise RuntimeError('Invalid PG request')
    runtime=Path(__file__).with_name('pg-primary-runtime.cjs').read_text('utf-8')
    program=remote_program(request,runtime,service)
    try:
        response=subprocess.run(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10',host,'python3 -'],input=program,capture_output=True,text=True,timeout=120,check=False)
        result=json.loads(response.stdout) if response.returncode==0 else {}
        allowed={'ok','status','id','titleTranslationIds','bodyTranslationIds','total','reused'}
        if not isinstance(result,dict) or set(result)-allowed or not isinstance(result.get('ok'),bool) or result.get('status') not in ('ready','ingested','conflict','unavailable'):
            return {'ok':False,'status':'unavailable'}
        return result
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return {'ok':False,'status':'unavailable'}
