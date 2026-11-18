import importlib.util,sys,json,tempfile,unittest,contextlib,io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'scripts'))
import publisher,pg_primary_remote
spec=importlib.util.spec_from_file_location('fixtures',ROOT/'test_publisher.py');fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
class PrimaryTests(unittest.TestCase):
 def args(self,root):
  news=publisher.normalize_quizzes(fixtures.make_news());news.update({'titleid':'a-useful-story','cover':'https://test/cover','public':False})
  for l in news['levels']:l['audio']='https://test/audio'
  (root/'news-package.json').write_text(json.dumps(news));(root/'review.json').write_text(json.dumps(fixtures.make_review(news)))
  titles={'titleid':news['titleid'],'sourceTitle':news['title'],'translations':[{'languageCode':c,'title':'Translated title'} for c in publisher.TITLE_TRANSLATION_LANGUAGES]}
  bodies={'titleid':news['titleid'],'sourceFingerprint':publisher.translation_source_fingerprint(news),'translations':[{'languageCode':t['languageCode'],'title':t['title'],'summary':'Translated summary','levels':[{'level':l['level'],'title':'','content':l['content']} for l in news['levels']]} for t in titles['translations']]}
  (root/'titles.json').write_text(json.dumps(titles));(root/'bodies.json').write_text(json.dumps(bodies))
  return SimpleNamespace(input=str(root/'news-package.json'),editorial_review=str(root/'review.json'),title_translations=str(root/'titles.json'),body_translations=str(root/'bodies.json'),confirm_unpublished_ingest=True)
 def call(self,name,args,response):
  with patch.object(publisher,'load_config',return_value={}),patch.object(publisher,'pg_primary',return_value=response) as remote,contextlib.redirect_stdout(io.StringIO()):
   result=getattr(publisher,name)(args)
  return result,remote
 def test_inspection_is_read_only(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);args=self.args(root);before={f.name:f.read_bytes() for f in root.iterdir()}
   result,remote=self.call('cmd_inspect',args,{'ok':True,'status':'missing','total':0})
   self.assertEqual(result,0);self.assertEqual(remote.call_args.args[1]['action'],'inspect');self.assertEqual(before,{f.name:f.read_bytes() for f in root.iterdir()})
 def test_unrecognized_and_completed_pg_receipts_block_remote_writes(self):
  for receipt in [{'success':True,'id':'other-receipt'},{'success':True,'backend':'postgresql'}]:
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);args=self.args(root);path=root/'ingest-result.json';path.write_text(json.dumps(receipt))
    with patch.object(publisher,'load_config',return_value={}),patch.object(publisher,'pg_primary') as remote:
     with self.assertRaises(RuntimeError):publisher.cmd_ingest(args)
     remote.assert_not_called();self.assertEqual(json.loads(path.read_text()),receipt)
 def test_incomplete_receipt_retry_persists_intent_and_result(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);args=self.args(root);receipt=root/'ingest-result.json';receipt.write_text(json.dumps({'backend':'postgresql','success':False}))
   def remote(config,request):
    self.assertFalse(json.loads(receipt.read_text())['success']);self.assertEqual(request['action'],'ingest');return {'ok':True,'status':'ingested','id':'news-id','reused':True,'total':13}
   with patch.object(publisher,'load_config',return_value={}),patch.object(publisher,'pg_primary',side_effect=remote),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(publisher.cmd_ingest(args),0)
   self.assertTrue(json.loads(receipt.read_text())['success']);self.assertTrue(json.loads(receipt.read_text())['reused'])
 def test_unavailable_keeps_incomplete_pg_receipt(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);args=self.args(root);(root/'ingest-result.json').write_text(json.dumps({'backend':'postgresql','success':False}));result,_=self.call('cmd_ingest',args,{'ok':False,'status':'unavailable'})
   self.assertEqual(result,1);self.assertFalse(json.loads((root/'ingest-result.json').read_text())['success'])
 def test_invalid_translations_block_write(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);args=self.args(root);(root/'bodies.json').write_text('{}')
   with patch.object(publisher,'pg_primary') as remote:
    with self.assertRaises(RuntimeError):publisher.cmd_ingest(args)
    remote.assert_not_called()
 def test_invalid_titles_block_write(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);args=self.args(root);titles=json.loads((root/'titles.json').read_text());titles['translations'].pop();(root/'titles.json').write_text(json.dumps(titles))
   with patch.object(publisher,'pg_primary') as remote:
    with self.assertRaises(RuntimeError):publisher.cmd_ingest(args)
    remote.assert_not_called()
 def test_bridge_keeps_host_verification_and_redacts_errors(self):
  with patch.object(pg_primary_remote.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='private-secret')) as run:
   self.assertEqual(pg_primary_remote.pg_primary({}, {'action':'check'}),{'ok':False,'status':'unavailable'})
   self.assertIn('StrictHostKeyChecking=yes',run.call_args.args[0]);compile(run.call_args.kwargs['input'],'remote','exec')
 def test_bridge_allows_read_only_inspection_and_rejects_option_injection(self):
  with patch.object(pg_primary_remote.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{"ok":true,"status":"missing","total":0}')):
   self.assertEqual(pg_primary_remote.pg_primary({}, {'action':'inspect'})['status'],'missing')
  with self.assertRaises(RuntimeError):pg_primary_remote.pg_primary({'pg_primary':{'ssh_host':'-oBad'}},{'action':'check'})
if __name__=='__main__':unittest.main()
