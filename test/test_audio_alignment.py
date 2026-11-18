import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audio_alignment as alignment
import publisher


def synthetic(text):
    import re
    words=[]
    for i,m in enumerate(re.finditer(r'\S+',alignment.normalize_for_alignment(text))):
        words.append({'word':m.group(),'start':i*.2+.02,'end':i*.2+.15,'score':.9})
    return {'word_segments':words}


class MappingTests(unittest.TestCase):
    def convert(self,text,result=None):
        return alignment.convert_result(text,result or synthetic(text),10000,'fixture',1,'a'*64)

    def test_unicode_offsets_and_repeated_occurrences(self):
        text='😀 Don’t pay $1,200.50—today. Go go.'
        timeline,report=self.convert(text)
        spelling=[text.encode('utf-16-le')[t['startChar']*2:t['endChar']*2].decode('utf-16-le') for t in timeline['tokens']]
        self.assertEqual(spelling,['Don’t','pay','1,200.50—today','Go','go'])
        self.assertEqual(timeline['tokens'][0]['startChar'],3)
        self.assertNotEqual(timeline['tokens'][-2]['id'],timeline['tokens'][-1]['id'])
        self.assertEqual(report['coveragePercent'],100)
        self.assertEqual(report['humanSyncReview'],'not_performed')

    def test_missing_time_not_interpolated(self):
        raw=synthetic('a 400 b');raw['word_segments'][1]={'word':'400'}
        timeline,report=self.convert('a 400 b',raw)
        self.assertEqual(len(timeline['cues']),2)
        self.assertEqual(report['missingTokens'][0]['text'],'400')
        self.assertEqual(report['status'],'review_required')

    def test_outer_punctuation_is_excluded_from_cue(self):
        raw={'word_segments':[{'word':'"Go."','start':.1,'end':1.0,'score':.8}],
             'segments':[{'text':'"Go."','chars':[
                 {'char':'"','start':.1,'end':.2,'score':1},
                 {'char':'G','start':.2,'end':.3,'score':.8},
                 {'char':'o','start':.3,'end':.4,'score':.8},
                 {'char':'.','start':.4,'end':.9,'score':1},
                 {'char':'"','start':.9,'end':1.,'score':1}]}]}
        timeline,_=self.convert('"Go."',raw)
        self.assertEqual(timeline['tokens'][0],{'id':0,'startChar':1,'endChar':3})
        self.assertEqual(timeline['cues'][0],{'startMs':200,'endMs':400,'tokenIds':[0]})

    def test_unmapped_input_is_rejected(self):
        raw=synthetic('one two three');raw['word_segments'].pop(1)
        with self.assertRaisesRegex(ValueError,'mismatch'):
            self.convert('one two three',raw)

    def test_overlapping_times_are_rejected(self):
        raw=synthetic('one two');raw['word_segments'][1]['start']=.05
        with self.assertRaisesRegex(ValueError,'cue_time'):
            self.convert('one two',raw)

    def test_hash_change_rejected(self):
        timeline,_=self.convert('one two')
        with self.assertRaisesRegex(ValueError,'input_hash'):
            alignment.validate_timeline(timeline,'one  two','a'*64)

    def test_invalid_token_ids_rejected(self):
        timeline,_=self.convert('one two');timeline['cues'][0]['tokenIds']=[99]
        with self.assertRaisesRegex(ValueError,'cue_token'):
            alignment.validate_timeline(timeline,'one two','a'*64)

    def test_zero_duration_not_accepted(self):
        raw=synthetic('one');raw['word_segments'][0]['end']=raw['word_segments'][0]['start']
        with self.assertRaisesRegex(ValueError,'cue_time'):
            self.convert('one',raw)

    def test_newlines_and_curly_quotes_preserve_positions(self):
        text='“Hello,”\n\nsaid Bob. Hello.'
        timeline,_=self.convert(text)
        self.assertEqual(len(timeline['tokens']),4)
        self.assertEqual(timeline['tokens'][1]['startChar'],10)


class RuntimeTests(unittest.TestCase):
    def test_preflight_checks_local_punkt_presence_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            english = root / 'nltk_data/tokenizers/punkt_tab/english'
            english.mkdir(parents=True)
            models = root / 'models'
            models.mkdir()
            model = models / alignment.MODEL_FILENAME
            model.write_bytes(b'model fixture')
            provenance = root / 'provenance.json'
            data = {name: name.encode() for name in (
                'abbrev_types.txt', 'collocations.tab', 'ortho_context.tab', 'sent_starters.txt'
            )}
            provenance.write_text(json.dumps({'files': [
                {'name': name, 'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
                for name, value in data.items()
            ]}))
            with patch.dict(os.environ, {}, clear=True), \
                    patch.object(alignment, 'RUNTIME_ROOT', root), \
                    patch.object(alignment, 'PUNKT_PROVENANCE', provenance), \
                    patch.object(alignment, 'MODEL_SHA256', hashlib.sha256(model.read_bytes()).hexdigest()), \
                    patch.object(alignment.shutil, 'which', return_value='/ffmpeg'):
                with self.assertRaisesRegex(RuntimeError, 'Punkt resource missing'):
                    alignment.check_runtime(sys.executable)
                for name, value in data.items():
                    (english / name).write_bytes(value)
                self.assertEqual(alignment.check_runtime(sys.executable)[2], english)
                with patch.dict(os.environ, {'LEVEL_READ_PUNKT_DIR': str(root / 'alternate')}):
                    with self.assertRaisesRegex(RuntimeError, 'Punkt resource missing.*alternate'):
                        alignment.check_runtime(sys.executable)
                path = english / 'abbrev_types.txt'
                path.write_bytes(b'x' * path.stat().st_size)
                with self.assertRaisesRegex(RuntimeError, 'Punkt resource checksum mismatch'):
                    alignment.check_runtime(sys.executable)


class ArchiveTests(unittest.TestCase):
    def test_inputs_unchanged_and_audio_hash_key_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source';source.mkdir();out=root/'out'
            package={'titleid':'fixture','title':'Test','levels':[{'level':n,'content':'a a'} for n in (1,2,3)]}
            p=source/'news-package.json';p.write_text(json.dumps(package));before=p.read_bytes()
            for n in (1,2,3):(source/f'fixture-level-{n}.mp3').write_bytes(b'mp3'+bytes([n]))
            alignment.prepare_archive(p,source,out)
            old=json.loads((out/'level-1/sample.json').read_text())['alignmentKey']
            (source/'fixture-level-1.mp3').write_bytes(b'new-mp3')
            alignment.prepare_archive(p,source,out)
            self.assertNotEqual(old,json.loads((out/'level-1/sample.json').read_text())['alignmentKey'])
            self.assertEqual(p.read_bytes(),before)
            with self.assertRaisesRegex(ValueError,'separate'):
                alignment.prepare_archive(p,source,source)

    def test_duplicate_level_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'news.json';p.write_text(json.dumps({'titleid':'x','title':'x','levels':[{'level':1},{'level':1}]}))
            with self.assertRaisesRegex(ValueError,'duplicate'):
                alignment.prepare_archive(p,Path(d),Path(d)/'out',[1])


class PublisherTests(unittest.TestCase):
    def fixture(self,root):
        # A real, already-reviewed source validates the production boundary.
        source=Path(__file__).parent/'fixtures/audio-alignment'
        levels=root/'levels.json';review=root/'review.json';cover=root/'cover.png'
        levels.write_bytes((source/'news-complete.json').read_bytes())
        review.write_bytes((source/'editorial-review.json').read_bytes())
        cover.write_bytes(b'local-test-cover')
        return argparse.Namespace(levels=str(levels),editorial_review=str(review),cover=str(cover),original_url='manual-input:local-test',
                                  date='2026-10-28',output=str(root/'story'),titleid='local-test',resume=False,
                                  align_audio=True,alignment_python=None,alignment_model_dir=None)

    def test_produce_alignment_stops_before_upload_and_pg(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d))
            with patch.object(publisher,'check_alignment_runtime') as runtime,patch.object(publisher,'load_config',return_value={}), \
                 patch.object(publisher,'generate_audio',return_value=b'local-fake-audio') as tts, \
                 patch.object(publisher,'align_archive',return_value={'status':'review_required'}) as align, \
                 patch.object(publisher,'cos_upload',side_effect=AssertionError('upload forbidden')), \
                 patch.object(publisher,'pg_primary',side_effect=AssertionError('PG forbidden')):
                self.assertEqual(publisher.cmd_produce(args),0)
                self.assertEqual(tts.call_count,3);align.assert_called_once();runtime.assert_called_once()
            state=json.loads((Path(args.output)/'production-state.json').read_text())
            self.assertEqual(state['stage'],'audio_alignment_review_required')
            self.assertFalse((Path(args.output)/'news-package.json').exists())

    def test_missing_runtime_fails_before_tts(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d))
            with patch.object(publisher,'check_alignment_runtime',side_effect=RuntimeError('missing runtime')), \
                 patch.object(publisher,'generate_audio',side_effect=AssertionError('must not synthesize')):
                with self.assertRaisesRegex(RuntimeError,'missing runtime'):
                    publisher.cmd_produce(args)

    def test_alignment_failure_keeps_audio_and_blocks_upload(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d))
            with patch.object(publisher,'check_alignment_runtime'),patch.object(publisher,'load_config',return_value={}), \
                 patch.object(publisher,'generate_audio',return_value=b'audio'), \
                 patch.object(publisher,'align_archive',side_effect=RuntimeError('bad alignment')), \
                 patch.object(publisher,'cos_upload',side_effect=AssertionError('upload forbidden')):
                with self.assertRaisesRegex(RuntimeError,'bad alignment'):
                    publisher.cmd_produce(args)
            self.assertTrue((Path(args.output)/'local-test-level-1.mp3').exists())
            self.assertEqual(json.loads((Path(args.output)/'production-state.json').read_text())['stage'],'audio_alignment_failed')

    def test_default_produce_aligns_all_levels_and_emits_complete_references(self):
        from timing_test_fixtures import fake_alignment, fake_upload
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d));args.align_audio=False
            with patch.object(publisher,'check_alignment_runtime') as runtime, \
                 patch.object(publisher,'load_config',return_value={}),patch.object(publisher,'generate_audio',return_value=b'audio'), \
                 patch.object(publisher,'align_archive',side_effect=fake_alignment) as align, \
                 patch('audio_timing_assets.decoded_duration_ms',return_value=1000), \
                 patch.object(publisher,'upload_timing_assets',side_effect=fake_upload) as timing_upload, \
                 patch.object(publisher,'cos_upload',return_value='https://example.com/mock-cover') as upload:
                self.assertEqual(publisher.cmd_produce(args),0)
                runtime.assert_called_once();align.assert_called_once();timing_upload.assert_called_once()
                self.assertEqual(upload.call_count,1)
                self.assertEqual([r['level'] for r in timing_upload.call_args.args[1]],[1,2,3])
            news=json.loads((Path(args.output)/'news-package.json').read_text())
            self.assertTrue(all(level['audioTiming']['audioUrl']==level['audio'] for level in news['levels']))
            self.assertEqual(news['public'],False)

    def test_archived_alignment_needs_no_credentials_or_remote_services(self):
        args=argparse.Namespace(input='/tmp/package.json',audio_dir='/tmp/audio',output='/tmp/align-output',
                                alignment_python=None,alignment_model_dir=None,level=[1],resume=True)
        with patch.object(publisher,'load_config',side_effect=AssertionError('no credentials')), \
             patch.object(publisher,'pg_primary',side_effect=AssertionError('no PG')), \
             patch.object(publisher,'generate_audio',side_effect=AssertionError('no TTS')), \
             patch.object(publisher,'cos_upload',side_effect=AssertionError('no upload')), \
             patch.object(publisher,'align_archive',return_value={'status':'review_required','outcomes':[{}]}) as align:
            self.assertEqual(publisher.cmd_align_audio(args),0)
            self.assertTrue(align.call_args.kwargs['resume'])


if __name__=='__main__':
    unittest.main()
