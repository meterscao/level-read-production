"""Cached-model, offline WhisperX worker. No TTS, upload, or database capability."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import time

from audio_alignment import MODEL_FILENAME, MODEL_SHA256, PIPELINE_VERSION, convert_result, sha256_file, validate_timeline, verify_punkt_resources, write_json, normalize_for_alignment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--model-dir', required=True)
    parser.add_argument('--punkt-dir', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text())
    model_dir = Path(args.model_dir)
    model_file = model_dir / MODEL_FILENAME
    if not model_file.is_file() or sha256_file(model_file) != MODEL_SHA256:
        raise RuntimeError('English model missing or checksum differs; install verified model before offline alignment')
    provenance = verify_punkt_resources(args.punkt_dir)
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    import torch
    import whisperx
    from whisperx import alignment as alignment_module
    from nltk.tokenize.punkt import PunktSentenceTokenizer, load_punkt_params
    from nltk.data import FileSystemPathPointer
    if importlib.metadata.version('whisperx') != '3.8.6':
        raise RuntimeError('Expected pinned WhisperX 3.8.6; validate other versions separately')
    splitter = PunktSentenceTokenizer(load_punkt_params(FileSystemPathPointer(str(args.punkt_dir))))
    original_loader = alignment_module.nltk_load
    def local_data(name):
        if name == 'tokenizers/punkt_tab/english.pickle':
            return splitter
        raise ValueError('Unexpected alignment resource')
    alignment_module.nltk_load = local_data
    torch.set_num_threads(4)
    model_started = time.perf_counter()
    model, metadata = whisperx.load_align_model('en', 'cpu', model_dir=str(model_dir))
    model_seconds = time.perf_counter() - model_started
    outcomes = []
    for directory in manifest['samples']:
        root = Path(directory)
        sample = json.loads((root/'sample.json').read_text())
        try:
            if sha256_file(root/'sample.mp3') != sample['audioSha256']:
                raise ValueError('audio_hash_changed')
            previous = root/'quality.json'
            if args.resume and previous.is_file() and (root/'timeline.json').is_file():
                q = json.loads(previous.read_text())
                timeline = json.loads((root/'timeline.json').read_text())
                if q.get('alignmentKey') == sample['alignmentKey'] and q.get('timelineSha256') == sha256_file(root/'timeline.json'):
                    validate_timeline(timeline, sample['content'], sample['audioSha256'])
                    (root/'failure.json').unlink(missing_ok=True)
                    outcomes.append({'level': sample['level'], 'status': 'review_required', 'reused': True, 'directory': directory, 'quality': q})
                    continue
            audio = whisperx.load_audio(str(root/'sample.mp3'))
            duration_ms = round(len(audio)/16000*1000)
            started = time.perf_counter()
            result = whisperx.align([{'start': 0.0, 'end': len(audio)/16000, 'text': normalize_for_alignment(sample['content'])}],
                                    model, metadata, audio, 'cpu', interpolate_method='ignore', return_char_alignments=True)
            seconds = time.perf_counter()-started
            # Native output is inspectable even when the strict adapter rejects it.
            write_json(root/'alignment.raw.json', result)
            timeline, quality = convert_result(sample['content'], result, duration_ms, sample['titleid'], sample['level'], sample['audioSha256'])
            write_json(root/'timeline.json', timeline)
            quality.update(alignmentKey=sample['alignmentKey'], pipelineVersion=PIPELINE_VERSION,
                           modelName='WAV2VEC2_ASR_BASE_960H', modelSha256=MODEL_SHA256,
                           whisperxVersion=importlib.metadata.version('whisperx'), torchVersion=torch.__version__,
                           device='cpu', threads=4, durationMs=duration_ms, alignmentSeconds=round(seconds,3),
                           timelineSha256=sha256_file(root/'timeline.json'), sentenceData=provenance)
            write_json(root/'quality.json', quality)
            (root/'failure.json').unlink(missing_ok=True)
            outcomes.append({'level': sample['level'], 'status': 'review_required', 'reused': False, 'directory': directory, 'quality': quality})
        except Exception as error:
            write_json(root/'failure.json', {'status': 'failed', 'alignmentKey': sample['alignmentKey'], 'error': str(error)})
            outcomes.append({'level': sample['level'], 'status': 'failed', 'directory': directory, 'error': str(error)})
    alignment_module.nltk_load = original_loader
    summary = {**manifest, 'outcomes': outcomes, 'failedLevels': [x['level'] for x in outcomes if x['status']=='failed'],
               'status': 'failed' if any(x['status']=='failed' for x in outcomes) else 'review_required',
               'modelLoadSeconds': round(model_seconds,3), 'uploaded': False, 'attached': False}
    write_json(manifest_path.parent/'alignment-manifest.json', summary)
    print(json.dumps({'status':summary['status'], 'failedLevels':summary['failedLevels'],
                      'levels':len(outcomes), 'modelLoadSeconds':summary['modelLoadSeconds']},ensure_ascii=False))
    return 1 if summary['failedLevels'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
