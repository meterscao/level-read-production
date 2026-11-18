import argparse
import contextlib
import hashlib
import hmac
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
import audio_timing_assets as assets
import publisher
from test_publisher import make_news, make_review
import test_publisher as publisher_tests
from timing_test_fixtures import fake_alignment

CONFIG = {'cos': {'secret_id': 'synthetic-id', 'secret_key': 'synthetic-key', 'bucket': 'bucket-123', 'region': 'ap-guangzhou'}}


class ObjectStore:
    def __init__(self):
        self.objects = {}
        self.puts = []
        self.public_origins = []
        self.bad_cors = False
        self.fail_put = None
        self.version = b'<VersioningConfiguration/>'

    def signed(self, _config, method, key, *, body=None, content_type=None, query=None, limit=50000000):
        if query:
            return 200, {}, self.version
        if method == 'PUT':
            self.puts.append(key)
            if self.fail_put == key:
                return 500, {}, b''
            if key in self.objects:
                return 409, {}, b''
            self.objects[key] = (body, content_type)
            return 200, {}, b''
        if key not in self.objects:
            return 404, {}, b''
        body, mime = self.objects[key]
        return 200, {'content-type': mime}, body if method == 'GET' else b''

    def public(self, request, limit):
        from urllib.parse import urlsplit
        key = urlsplit(request.full_url).path[1:]
        origin = request.get_header('Origin')
        self.public_origins.append(origin)
        body, mime = self.objects[key]
        return 200, {'content-type': mime, 'access-control-allow-origin': 'https://wrong.test' if self.bad_cors else origin}, body


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.news = {'titleid': 'fixture', 'title': 'Fixture', 'levels': [{'level': n, 'content': '😀 Go go. Don’t pay $1,200.50.'} for n in (1, 2, 3)]}
        self.package = self.root / 'news.json'; self.package.write_text(json.dumps(self.news))
        for row in self.news['levels']:
            (self.root / f'fixture-level-{row["level"]}.mp3').write_bytes(b'synthetic-mp3-' + str(row['level']).encode())
        fake_alignment(self.package, self.root, self.root / 'audio-timings')
        self.duration = patch.object(assets, 'decoded_duration_ms', return_value=1000)
        self.duration.start(); self.addCleanup(self.duration.stop)

    def prepared(self):
        return assets.prepare_timing_assets(self.news, self.root, self.root / 'audio-timings')

    def change_timeline(self, edit):
        directory = self.root / 'audio-timings/level-3'; path = directory / 'timeline.json'
        data = json.loads(path.read_text()); edit(data); path.write_text(json.dumps(data))
        q = json.loads((directory / 'quality.json').read_text()); q['timelineSha256'] = assets.sha256_file(path)
        (directory / 'quality.json').write_text(json.dumps(q))

    def test_streaming_hash_supports_host_without_hashlib_file_digest(self):
        original=getattr(hashlib,'file_digest',None)
        if original is not None:delattr(hashlib,'file_digest')
        try:
            path=self.root/'fixture-level-1.mp3'
            self.assertEqual(assets.sha256_file(path),hashlib.sha256(path.read_bytes()).hexdigest())
        finally:
            if original is not None:setattr(hashlib,'file_digest',original)

    def test_prepares_exact_utf16_source_tokens_and_hash_keys(self):
        rows = self.prepared(); self.assertEqual([r['level'] for r in rows], [1,2,3])
        self.assertEqual(rows[0]['contentSha256'], assets.content_hash(self.news['levels'][0]['content']))
        timeline = json.loads(Path(rows[0]['timelinePath']).read_text())
        self.assertEqual(timeline['tokens'][0], {'id':0,'startChar':3,'endChar':5})
        self.assertRegex(rows[0]['timelineKey'], r'^audio-timings/fixture/level-1/(?:[a-f0-9]{64}/){3}[a-f0-9]{64}\.json$')

    def test_same_count_wrong_source_positions_rejected(self):
        self.change_timeline(lambda t: t['tokens'][0].update(startChar=2))
        with self.assertRaisesRegex(ValueError, 'exact_source_map'):
            self.prepared()

    def test_wrong_titleid_and_duplicate_cue_rejected(self):
        self.change_timeline(lambda t: t.update(titleid='other'))
        with self.assertRaisesRegex(ValueError, 'identity_schema'):
            self.prepared()
        self.change_timeline(lambda t: (t.update(titleid='fixture'), t['cues'][1].update(tokenIds=[0])))
        with self.assertRaisesRegex(ValueError, 'token_order'):
            self.prepared()

    def test_boolean_schema_and_level_are_rejected_like_website(self):
        self.change_timeline(lambda t: t.update(schemaVersion=True))
        with self.assertRaisesRegex(ValueError,'identity_schema'):self.prepared()
        self.change_timeline(lambda t: t.update(schemaVersion=1))
        self.news['levels'][0]['level']=True
        with self.assertRaisesRegex(ValueError,'three_unique_levels'):self.prepared()

    def test_json_byte_budget_matches_web_consumer_exactly(self):
        path=self.root/'audio-timings/level-3/timeline.json'
        path.write_bytes(path.read_bytes()+b' '*(1_020_000-len(path.read_bytes())))
        quality=json.loads(path.with_name('quality.json').read_text());quality['timelineSha256']=assets.sha256_file(path)
        path.with_name('quality.json').write_text(json.dumps(quality))
        with self.assertRaisesRegex(ValueError,'asset_size'):self.prepared()

    def test_audio_and_duration_drift_fail(self):
        with patch.object(assets, 'decoded_duration_ms', return_value=1200):
            with self.assertRaisesRegex(ValueError, 'duration_mismatch'):
                self.prepared()
        (self.root / 'fixture-level-2.mp3').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'sample_changed'):
            self.prepared()

    def test_complete_signed_and_two_origin_readbacks_idempotent(self):
        store = ObjectStore(); rows = self.prepared(); receipt = self.root / 'receipt.json'
        with patch.object(assets, '_signed', side_effect=store.signed), patch.object(assets, '_http', side_effect=store.public):
            first = assets.upload_timing_assets(CONFIG, rows, receipt)
            second = assets.upload_timing_assets(CONFIG, rows, receipt)
        self.assertEqual(len(store.puts), 6)
        self.assertTrue(all(a['disposition']=='created' for a in first['assets']))
        self.assertTrue(all(a['disposition']=='reused' for a in second['assets']))
        self.assertEqual(first['timings'], second['timings'])
        self.assertEqual(store.public_origins.count('https://levelread.com'),12)
        self.assertEqual(store.public_origins.count('http://127.0.0.1:3130'),12)
        self.assertEqual(first['cmsApprovalsCreated'],0)
        self.assertEqual(json.loads(receipt.read_text())['status'],'verified')

    def test_existing_wrong_bytes_never_overwritten(self):
        store = ObjectStore(); rows = self.prepared()
        store.objects[rows[0]['audioKey']] = (b'wrong', 'audio/mpeg')
        with patch.object(assets, '_signed', side_effect=store.signed), patch.object(assets, '_http', side_effect=store.public):
            with self.assertRaisesRegex(RuntimeError, 'signed_readback_mismatch'):
                assets.upload_timing_assets(CONFIG, rows, self.root/'receipt.json')
        self.assertEqual(store.puts,[])

    def test_public_cors_failure_cannot_mark_verified(self):
        store = ObjectStore(); store.bad_cors = True
        with patch.object(assets, '_signed', side_effect=store.signed), patch.object(assets, '_http', side_effect=store.public):
            with self.assertRaisesRegex(RuntimeError, 'cors_mismatch'):
                assets.upload_timing_assets(CONFIG, self.prepared(), self.root/'receipt.json')
        self.assertFalse((self.root/'receipt.json').exists())

    def test_partial_failure_resumes_by_head_and_verified_readback(self):
        store = ObjectStore(); rows = self.prepared(); store.fail_put=rows[1]['audioKey']; receipt=self.root/'receipt.json'
        with patch.object(assets, '_signed', side_effect=store.signed), patch.object(assets, '_http', side_effect=store.public):
            with self.assertRaisesRegex(RuntimeError,'put_failed'):
                assets.upload_timing_assets(CONFIG, rows, receipt)
            self.assertEqual(json.loads(receipt.read_text())['completedObjects'],2)
            first_key=rows[0]['audioKey']; store.fail_put=None
            result=assets.upload_timing_assets(CONFIG, rows, receipt)
        self.assertEqual(store.puts.count(first_key),1)
        self.assertEqual(result['status'],'verified')
        self.assertEqual(len(result['assets']),6)

    def test_changed_file_rejected_before_any_network_request(self):
        rows=self.prepared();Path(rows[-1]['timelinePath']).write_bytes(b'changed')
        with patch.object(assets, '_signed', side_effect=AssertionError('no network')):
            with self.assertRaisesRegex(ValueError,'prepared_asset_changed'):
                assets.upload_timing_assets(CONFIG,rows,self.root/'receipt.json')

    def test_versioned_bucket_rejected_before_put(self):
        store=ObjectStore();store.version=b'<VersioningConfiguration><Status>Suspended</Status></VersioningConfiguration>'
        with patch.object(assets,'_signed',side_effect=store.signed):
            with self.assertRaisesRegex(RuntimeError,'versioning_not_never_enabled'):
                assets.upload_timing_assets(CONFIG,self.prepared(),self.root/'receipt.json')
        self.assertEqual(store.puts,[])

    def test_signing_covers_immutable_header_and_uses_hex_key_text(self):
        captured=[]
        with patch.object(assets,'_http',side_effect=lambda req,limit:captured.append(req) or (200,{},b'')), patch.object(assets.time,'time',return_value=1700000000):
            assets._signed(CONFIG,'PUT','audios/fixture/hash.mp3',body=b'abc',content_type='audio/mpeg')
        req=captured[0];self.assertEqual(req.get_header('X-cos-forbid-overwrite'),'true')
        auth=req.get_header('Authorization');self.assertIn('x-cos-forbid-overwrite',auth)
        key_time='1700000000;1700001800'; sign_key=hmac.new(b'synthetic-key',key_time.encode(),hashlib.sha1).hexdigest()
        canonical='cache-control=public%2Cmax-age%3D31536000%2Cimmutable&content-length=3&content-type=audio%2Fmpeg&host=bucket-123.cos.ap-guangzhou.myqcloud.com&x-cos-forbid-overwrite=true'
        request_string='put\n/audios/fixture/hash.mp3\n\n'+canonical+'\n'
        expected=hmac.new(sign_key.encode(),('sha1\n'+key_time+'\n'+hashlib.sha1(request_string.encode()).hexdigest()+'\n').encode(),hashlib.sha1).hexdigest()
        self.assertIn('q-signature='+expected,auth)

    def test_package_requires_all_three_timings_and_local_identity(self):
        with self.assertRaisesRegex(ValueError,'reference_schema'):
            assets.validate_package_timings(self.news,self.root,require_all=True)
        self.assertEqual(assets.validate_package_timings(self.news,self.root),[])
        rows=self.prepared();refs=assets._result(CONFIG,rows,[])
        for row in self.news['levels']:
            row['audio']=refs['audios'][str(row['level'])];row['audioTiming']=refs['timings'][str(row['level'])]
        self.assertEqual(len(assets.validate_package_timings(self.news,self.root,True)),3)
        self.news['levels'][1]['audioTiming']['timelineSha256']='0'*64
        with self.assertRaisesRegex(ValueError,'local_binding_changed'):
            assets.validate_package_timings(self.news,self.root,True)


class DefaultProductionTests(unittest.TestCase):
    def args(self, root):
        news=make_news();(root/'levels.json').write_text(json.dumps(news));(root/'review.json').write_text(json.dumps(make_review(news)));(root/'cover.png').write_bytes(b'cover')
        return argparse.Namespace(levels=str(root/'levels.json'),editorial_review=str(root/'review.json'),cover=str(root/'cover.png'),date='2026-10-29',original_url='https://example.test/source',output=str(root/'story'),titleid='fixture',resume=False,align_audio=False,alignment_python=None,alignment_model_dir=None)

    def test_alignment_failure_never_uploads_or_claims_complete(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);args=self.args(root)
            with patch.object(publisher,'check_alignment_runtime'), patch.object(publisher,'load_config',return_value={}),patch.object(publisher,'generate_audio',return_value=b'audio'),patch.object(publisher,'align_archive',side_effect=RuntimeError('failure')),patch.object(publisher,'cos_upload',side_effect=AssertionError('no upload')):
                with self.assertRaisesRegex(RuntimeError,'failure'):publisher.cmd_produce(args)
            self.assertEqual(json.loads((root/'story/production-state.json').read_text())['stage'],'audio_alignment_failed')
            self.assertFalse((root/'story/news-package.json').exists())

    def test_runtime_precheck_default_runs_before_billable_audio(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.args(Path(d))
            with patch.object(publisher,'check_alignment_runtime',side_effect=RuntimeError('missing runtime')),patch.object(publisher,'load_config',side_effect=AssertionError('no private config')),patch.object(publisher,'generate_audio',side_effect=AssertionError('no TTS')):
                with self.assertRaisesRegex(RuntimeError,'missing runtime'):publisher.cmd_produce(args)

    def _assert_failed_ingest_cannot_restart_production(self, timing_required):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);args=self.args(root);args.resume=True;story=root/'story';story.mkdir()
            news=make_news()
            (story/'production-input.json').write_text(json.dumps({'fingerprint':publisher.production_input_fingerprint(news,root/'cover.png')}))
            (story/'news-complete.json').write_text(json.dumps(news));(story/'cover.png').write_bytes(b'cover')
            (story/'news-package.json').write_text('original exact PG request package')
            (story/'audio-metadata.json').write_text(json.dumps({'timingRequired':timing_required}))
            for level in (1,2,3):(story/f'fixture-level-{level}.mp3').write_bytes(b'synthetic-test-audio')
            receipt={'backend':'postgresql','success':False}
            if timing_required:receipt['timingRequired']=True
            (story/'ingest-result.json').write_text(json.dumps(receipt))
            before={str(p.relative_to(story)):p.read_bytes() for p in story.rglob('*') if p.is_file()}
            store=ObjectStore()
            with patch.object(publisher,'check_alignment_runtime'),patch.object(publisher,'load_config',return_value=CONFIG),patch.object(publisher,'generate_audio',side_effect=AssertionError('no TTS')),patch.object(publisher,'align_archive',side_effect=fake_alignment),patch.object(assets,'decoded_duration_ms',return_value=1000),patch.object(publisher,'cos_upload',return_value='https://example.test/cover.png'),patch.object(assets,'_signed',side_effect=store.signed),patch.object(assets,'_http',side_effect=store.public),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError,'ingest attempt'):
                    publisher.cmd_produce(args)
            self.assertEqual(before,{str(p.relative_to(story)):p.read_bytes() for p in story.rglob('*') if p.is_file()})
            self.assertEqual(store.puts,[])

    def test_failed_legacy_ingest_receipt_preserves_exact_package_during_produce_resume(self):
        self._assert_failed_ingest_cannot_restart_production(False)

    def test_failed_timed_ingest_receipt_preserves_exact_package_during_produce_resume(self):
        self._assert_failed_ingest_cannot_restart_production(True)

    def test_completed_ingest_receipt_preserved_without_regeneration(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);args=self.args(root);story=root/'story';story.mkdir();(story/'ingest-result.json').write_text('{"success":true}');(story/'news-package.json').write_text('historical package')
            with patch.object(publisher,'check_alignment_runtime'),patch.object(publisher,'load_config',return_value={}),patch.object(publisher,'generate_audio',side_effect=AssertionError('no TTS')):
                with self.assertRaisesRegex(RuntimeError,'already been ingested'):publisher.cmd_produce(args)
            self.assertEqual((story/'news-package.json').read_text(),'historical package')

    def test_default_produce_upload_and_unpublished_ingest_keep_exact_three_references(self):
        store=ObjectStore();requests=[]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);args=self.args(root)
            with patch.object(publisher,'check_alignment_runtime'),patch.object(publisher,'load_config',return_value=CONFIG),patch.object(publisher,'generate_audio',return_value=b'synthetic-test-audio'),patch.object(publisher,'align_archive',side_effect=fake_alignment),patch.object(assets,'decoded_duration_ms',return_value=1000),patch.object(publisher,'cos_upload',return_value='https://example.test/cover.png') as cover,patch.object(assets,'_signed',side_effect=store.signed),patch.object(assets,'_http',side_effect=store.public),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(publisher.cmd_produce(args),0)
                cover.assert_called_once()
                story=root/'story';news=json.loads((story/'news-package.json').read_text())
                self.assertEqual(len(store.puts),6)
                self.assertEqual([l['level'] for l in news['levels']],[1,2,3])
                self.assertTrue(all(l['audio']==l['audioTiming']['audioUrl'] for l in news['levels']))
                helper=publisher_tests.PublisherTests();titles=helper.title_translations();titles['titleid']='fixture'
                (story/'title-translations.json').write_text(json.dumps(titles))
                (story/'body-translations.json').write_text(json.dumps(helper.body_translations(news)))
                ingest=argparse.Namespace(input=str(story/'news-package.json'),editorial_review=str(story/'editorial-review.json'),title_translations=str(story/'title-translations.json'),body_translations=str(story/'body-translations.json'),confirm_unpublished_ingest=True)
                def commit(_config,request):
                    requests.append(request);return {'ok':True,'id':'synthetic-news','status':'ingested','total':13}
                with patch.object(publisher,'pg_primary',side_effect=commit):
                    self.assertEqual(publisher.cmd_ingest(ingest),0)
            self.assertEqual(len(requests),1)
            self.assertEqual(requests[0]['package'],news)
            self.assertEqual(requests[0]['package']['public'],False)
            self.assertEqual(len(store.puts),6) # ingest is read-only toward COS.
            self.assertEqual(len(store.public_origins),24) # fresh two-origin verification twice.

    def test_new_pg_failure_receipt_cannot_be_downgraded_to_legacy_retry(self):
        store=ObjectStore()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);args=self.args(root)
            with patch.object(publisher,'check_alignment_runtime'),patch.object(publisher,'load_config',return_value=CONFIG),patch.object(publisher,'generate_audio',return_value=b'synthetic-test-audio'),patch.object(publisher,'align_archive',side_effect=fake_alignment),patch.object(assets,'decoded_duration_ms',return_value=1000),patch.object(publisher,'cos_upload',return_value='https://example.test/cover.png'),patch.object(assets,'_signed',side_effect=store.signed),patch.object(assets,'_http',side_effect=store.public),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(publisher.cmd_produce(args),0)
                story=root/'story';news=json.loads((story/'news-package.json').read_text())
                helper=publisher_tests.PublisherTests();titles=helper.title_translations();titles['titleid']='fixture'
                (story/'title-translations.json').write_text(json.dumps(titles));(story/'body-translations.json').write_text(json.dumps(helper.body_translations(news)))
                ingest=argparse.Namespace(input=str(story/'news-package.json'),editorial_review=str(story/'editorial-review.json'),title_translations=str(story/'title-translations.json'),body_translations=str(story/'body-translations.json'),confirm_unpublished_ingest=True)
                with patch.object(publisher,'pg_primary',return_value={'ok':False,'status':'unavailable'}):
                    self.assertEqual(publisher.cmd_ingest(ingest),1)
                self.assertTrue(json.loads((story/'ingest-result.json').read_text())['timingRequired'])
                (story/'audio-metadata.json').unlink()
                for row in news['levels']:row.pop('audioTiming')
                (story/'news-package.json').write_text(json.dumps(news))
                with patch.object(publisher,'pg_primary',side_effect=AssertionError('no PG call')):
                    with self.assertRaisesRegex(RuntimeError,'Retry requires the same package'):publisher.cmd_ingest(ingest)

    def test_corrupt_third_alignment_prevents_the_first_cover_write(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);args=self.args(root)
            def malformed(*args,**kwargs):
                result=fake_alignment(*args,**kwargs)
                (root/'story/audio-timings/level-3/timeline.json').write_bytes(b'changed')
                return result
            with patch.object(publisher,'check_alignment_runtime'),patch.object(publisher,'load_config',return_value=CONFIG),patch.object(publisher,'generate_audio',return_value=b'synthetic'),patch.object(publisher,'align_archive',side_effect=malformed),patch.object(assets,'decoded_duration_ms',return_value=1000),patch.object(publisher,'cos_upload',side_effect=AssertionError('no cover upload')),patch.object(assets,'_signed',side_effect=AssertionError('no COS request')):
                with self.assertRaises(ValueError):publisher.cmd_produce(args)
            self.assertFalse((root/'story/news-package.json').exists())
            self.assertEqual(json.loads((root/'story/production-state.json').read_text())['stage'],'audio_alignment_validation_failed')

    def test_new_timing_required_package_cannot_use_legacy_receipt_to_skip_timings(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);args=publisher_tests.PublisherTests().valid_ingest_args(root)
            (root/'audio-metadata.json').write_text('{"timingRequired":true}')
            package = json.loads(Path(args.input).read_text())
            (root/'ingest-result.json').write_text(json.dumps({
                'backend': 'postgresql', 'success': False, 'public': False,
                'title': package['title'], 'titleid': package['titleid'],
                'translationLanguages': list(publisher.TITLE_TRANSLATION_LANGUAGES),
            }))
            with patch.object(publisher,'load_config',return_value={}),patch.object(publisher,'pg_primary',side_effect=AssertionError('no PG')):
                with self.assertRaisesRegex(ValueError,'reference_schema'):publisher.cmd_ingest(args)

    def test_missing_timing_ingest_fails_before_pg_and_remote_asset_reads(self):
        with tempfile.TemporaryDirectory() as d:
            args=publisher_tests.PublisherTests().valid_ingest_args(Path(d))
            with patch.object(publisher,'load_config',return_value={}),patch.object(publisher,'pg_primary',side_effect=AssertionError('no PG')),patch.object(publisher,'verify_uploaded_timings',side_effect=AssertionError('no remote')):
                with self.assertRaisesRegex(ValueError,'reference_schema'):publisher.cmd_ingest(args)
            self.assertFalse((Path(d)/'ingest-result.json').exists())


if __name__=='__main__':unittest.main()
