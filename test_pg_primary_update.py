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
 def failed_receipt(self, args):
  package = json.loads(Path(args.input).read_text())
  return {"backend": "postgresql", "success": False, "public": False,
          "title": package["title"], "titleid": package["titleid"]}
 def test_inspection_is_read_only(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);args=self.args(root);before={f.name:f.read_bytes() for f in root.iterdir()}
   result,remote=self.call('cmd_inspect',args,{'ok':True,'status':'missing','total':0})
   self.assertEqual(result,0);self.assertEqual(remote.call_args.args[1]['action'],'inspect');self.assertEqual(before,{f.name:f.read_bytes() for f in root.iterdir()})
 def use_legacy_translations(self, args, fields=("title_translations", "body_translations")):
  for field in fields:
   path = Path(getattr(args, field))
   artifact = json.loads(path.read_text())
   for row in artifact["translations"]:
    if row["languageCode"] == "ru":
     row["languageCode"] = "ko"
   path.write_text(json.dumps(artifact))

 def test_legacy_set_rejects_new_ingest_but_remains_readable(self):
  with tempfile.TemporaryDirectory() as tmp:
   root = Path(tmp)
   args = self.args(root)
   self.use_legacy_translations(args)
   before = {path.name: path.read_bytes() for path in root.iterdir()}
   result, remote = self.call("cmd_inspect", args, {"ok": True, "status": "existing"})
   self.assertEqual(result, 0)
   request = remote.call_args.args[1]
   self.assertEqual(request["action"], "inspect")
   self.assertEqual([row["languageCode"] for row in request["titleTranslations"]],
                    ["zh-CN", "zh-TW", "ja", "ko", "es", "pt-BR"])
   with patch.object(publisher, "load_config") as config, patch.object(publisher, "pg_primary") as pg:
    with self.assertRaisesRegex(RuntimeError, "ja, ru, es"):
     publisher.cmd_ingest(args)
    config.assert_not_called()
    pg.assert_not_called()
   self.assertEqual(before, {path.name: path.read_bytes() for path in root.iterdir()})

 def test_legacy_attempt_reuses_original_set_and_writes_its_contract_to_receipt(self):
  with tempfile.TemporaryDirectory() as tmp:
   root = Path(tmp)
   args = self.args(root)
   self.use_legacy_translations(args)
   receipt_path = root / "ingest-result.json"
   package = json.loads(Path(args.input).read_text())
   receipt = self.failed_receipt(args)
   receipt_path.write_text(json.dumps(receipt))
   result, remote = self.call("cmd_ingest", args, {"ok": False, "status": "unavailable"})
   self.assertEqual(result, 1)
   attempted = remote.call_args.args[1]
   self.assertIs(attempted["legacyTranslationRetry"], True)
   self.assertEqual(attempted["package"], package)
   self.assertEqual([row["languageCode"] for row in attempted["bodyTranslations"]],
                    ["zh-CN", "zh-TW", "ja", "ko", "es", "pt-BR"])
   self.assertEqual(json.loads(receipt_path.read_text())["translationLanguages"],
                    ["zh-CN", "zh-TW", "ja", "ko", "es", "pt-BR"])
   result, remote = self.call("cmd_ingest", args, {"ok": True, "status": "ingested", "reused": True})
   self.assertEqual(result, 0)
   self.assertEqual(remote.call_args.args[1], attempted)

 def test_receipt_for_another_package_or_the_current_contract_cannot_retry_legacy(self):
  with tempfile.TemporaryDirectory() as tmp:
   root = Path(tmp)
   args = self.args(root)
   self.use_legacy_translations(args)
   receipt_path = root / "ingest-result.json"
   receipt = self.failed_receipt(args)
   invalid_attempts = [
    {**receipt, "titleid": "other-story"},
    {**receipt, "translationLanguages": list(publisher.TITLE_TRANSLATION_LANGUAGES)},
   ]
   for invalid in invalid_attempts:
    with self.subTest(receipt=invalid):
     receipt_path.write_text(json.dumps(invalid))
     with patch.object(publisher, "load_config") as config:
      with self.assertRaisesRegex(RuntimeError, "does not match|ja, ru, es"):
       publisher.cmd_ingest(args)
      config.assert_not_called()
     self.assertEqual(json.loads(receipt_path.read_text()), invalid)

 def test_russian_retry_preserves_original_korean_intent_before_any_remote_call(self):
  with tempfile.TemporaryDirectory() as tmp:
   root = Path(tmp)
   args = self.args(root)
   receipt_path = root / "ingest-result.json"
   historical = {**self.failed_receipt(args), "status": "unavailable"}
   for receipt in (historical, {**historical, "translationLanguages": list(publisher.LEGACY_TRANSLATION_LANGUAGES)}):
    with self.subTest(receipt=receipt):
     receipt_path.write_text(json.dumps(receipt))
     before = receipt_path.read_bytes()
     with patch.object(publisher, "load_config") as config, patch.object(publisher, "pg_primary") as pg:
      with self.assertRaisesRegex(RuntimeError, "Retry requires the original translation languages:.*ja, ko, es"):
       publisher.cmd_ingest(args)
      config.assert_not_called()
      pg.assert_not_called()
     self.assertEqual(receipt_path.read_bytes(), before)
   self.use_legacy_translations(args)
   result, pg = self.call("cmd_ingest", args, {"ok": True, "status": "ingested", "reused": True})
   self.assertEqual(result, 0)
   self.assertIs(pg.call_args.args[1]["legacyTranslationRetry"], True)

 def test_retry_rejects_changed_content_for_a_fingerprinted_receipt(self):
  with tempfile.TemporaryDirectory() as tmp:
   root = Path(tmp)
   args = self.args(root)
   self.use_legacy_translations(args)
   receipt_path = root / "ingest-result.json"
   receipt_path.write_text(json.dumps(self.failed_receipt(args)))
   result, _ = self.call("cmd_ingest", args, {"ok": False, "status": "unavailable"})
   self.assertEqual(result, 1)
   before = receipt_path.read_bytes()
   self.assertRegex(json.loads(before)["requestSha256"], r"^[0-9a-f]{64}$")
   path = Path(args.body_translations)
   body = json.loads(path.read_text())
   body["translations"][0]["summary"] = "Changed since the unsuccessful attempt"
   path.write_text(json.dumps(body))
   with patch.object(publisher, "load_config") as config, patch.object(publisher, "pg_primary") as pg:
    with self.assertRaisesRegex(RuntimeError, "Retry requires the same package and translations"):
     publisher.cmd_ingest(args)
    config.assert_not_called()
    pg.assert_not_called()
   self.assertEqual(receipt_path.read_bytes(), before)

 def test_concurrent_ingest_cannot_overwrite_the_first_receipt(self):
  with tempfile.TemporaryDirectory() as tmp:
   root = Path(tmp)
   args = self.args(root)
   package = json.loads(Path(args.input).read_text())
   timings = {str(row["level"]): {"fixture": row["level"]} for row in package["levels"]}
   for row in package["levels"]:
    row["audioTiming"] = timings[str(row["level"])]
   Path(args.input).write_text(json.dumps(package))
   alternate = root / "alternate-bodies.json"
   body = json.loads(Path(args.body_translations).read_text())
   body["translations"][0]["summary"] = "A competing translation"
   alternate.write_text(json.dumps(body))
   competing_args = SimpleNamespace(**{**vars(args), "body_translations": str(alternate)})
   receipt_path = root / "ingest-result.json"

   def verify_timing(*_):
    self.assertFalse(receipt_path.exists())
    with self.assertRaisesRegex(RuntimeError, "Another ingest is in progress"):
     publisher.cmd_ingest(competing_args)
    self.assertFalse(receipt_path.exists())
    return {"timings": timings}

   with patch.object(publisher, "load_config", return_value={}), \
        patch.object(publisher, "validate_package_timings"), \
        patch.object(publisher, "verify_uploaded_timings", side_effect=verify_timing), \
        patch.object(publisher, "pg_primary", return_value={"ok": True, "status": "ingested", "id": "first"}) as pg, \
        contextlib.redirect_stdout(io.StringIO()):
    self.assertEqual(publisher.cmd_ingest(args), 0)
    pg.assert_called_once()
    with self.assertRaisesRegex(RuntimeError, "already been ingested"):
     publisher.cmd_ingest(competing_args)
   self.assertEqual(json.loads(receipt_path.read_bytes())["id"], "first")

 def test_mismatched_translation_sets_are_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   args = self.args(Path(tmp))
   self.use_legacy_translations(args, ("body_translations",))
   with patch.object(publisher, "load_config") as config:
    with self.assertRaisesRegex(RuntimeError, "each reviewed title language"):
     publisher.cmd_inspect(args)
    config.assert_not_called()

 def test_unrecognized_and_completed_pg_receipts_block_remote_writes(self):
  for receipt in [{'success':True,'id':'other-receipt'},{'success':True,'backend':'postgresql'}]:
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);args=self.args(root);path=root/'ingest-result.json';path.write_text(json.dumps(receipt))
    with patch.object(publisher,'load_config',return_value={}),patch.object(publisher,'pg_primary') as remote:
     with self.assertRaises(RuntimeError):publisher.cmd_ingest(args)
     remote.assert_not_called();self.assertEqual(json.loads(path.read_text()),receipt)
 def test_incomplete_receipt_retry_persists_intent_and_result(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);args=self.args(root);receipt=root/'ingest-result.json';self.use_legacy_translations(args);receipt.write_text(json.dumps(self.failed_receipt(args)))
   def remote(config,request):
    self.assertFalse(json.loads(receipt.read_text())['success']);self.assertEqual(request['action'],'ingest');return {'ok':True,'status':'ingested','id':'news-id','reused':True,'total':13}
   with patch.object(publisher,'load_config',return_value={}),patch.object(publisher,'pg_primary',side_effect=remote),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(publisher.cmd_ingest(args),0)
   self.assertTrue(json.loads(receipt.read_text())['success']);self.assertTrue(json.loads(receipt.read_text())['reused'])
 def test_unavailable_keeps_incomplete_pg_receipt(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);args=self.args(root);self.use_legacy_translations(args);(root/'ingest-result.json').write_text(json.dumps(self.failed_receipt(args)));result,_=self.call('cmd_ingest',args,{'ok':False,'status':'unavailable'})
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
  response = {"ok": True, "status": "existing", "total": 15,
              "extraTitleLanguages": ["ru"], "extraBodyLanguages": ["ru"]}
  with patch.object(pg_primary_remote.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(response))):
   self.assertEqual(pg_primary_remote.pg_primary({}, {'action':'inspect'}), response)
  with self.assertRaises(RuntimeError):pg_primary_remote.pg_primary({'pg_primary':{'ssh_host':'-oBad'}},{'action':'check'})
if __name__=='__main__':unittest.main()
