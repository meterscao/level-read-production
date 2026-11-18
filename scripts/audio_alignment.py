"""Standard-library orchestration for local-only news audio alignment."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

PIPELINE_VERSION = 'whisperx-en-v1'
TOKENIZATION_VERSION = 'en-display-v1'
MODEL_FILENAME = 'wav2vec2_fairseq_base_ls960_asr_ls960.pth'
MODEL_SHA256 = '488fd4f16de84438ffc945334278c1b9fb9b7159a806c1080b16111a958c945d'
RUNTIME_ROOT = Path.home() / '.codex/level-read-production/alignment-runtime'
PUNKT_PROVENANCE = Path(__file__).resolve().parent.parent / 'resources/punkt-english/provenance.json'


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_punkt_resources(directory: Path) -> dict:
    provenance = json.loads(PUNKT_PROVENANCE.read_text(encoding='utf-8'))
    for item in provenance['files']:
        path = directory / item['name']
        if not path.is_file():
            raise RuntimeError(f'English Punkt resource missing: {path}. See references/audio-alignment.md.')
        if path.stat().st_size != item['bytes'] or sha256_file(path) != item['sha256']:
            raise RuntimeError(f'English Punkt resource checksum mismatch: {path}')
    return provenance


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def utf16_offset(content: str, codepoint_offset: int) -> int:
    return len(content[:codepoint_offset].encode('utf-16-le')) // 2


def normalize_for_alignment(content: str) -> str:
    replacements = {'’': "'", '‘': "'", '“': '"', '”': '"', '—': '-', '–': '-'}
    return ''.join(' ' if c.isspace() else replacements.get(c, c) for c in content)


def word_core(content: str, start: int, end: int) -> tuple[int, int] | None:
    # v1: whitespace-delimited occurrence; trim only outer non-letter/number/mark
    # characters, retaining internal apostrophes, dots, commas and hyphens.
    def lexical(c: str) -> bool:
        return unicodedata.category(c)[0] in ('L', 'N', 'M')
    while start < end and not lexical(content[start]):
        start += 1
    while end > start and not lexical(content[end - 1]):
        end -= 1
    return (start, end) if start < end else None


def convert_result(content: str, result: dict, duration_ms: int, titleid: str, level: int,
                   audio_sha256: str) -> tuple[dict, dict]:
    normalized = normalize_for_alignment(content)
    # WhisperX word intervals include outer punctuation; project exact character
    # times onto display-word cores so a quoted/period-ending word does not
    # absorb punctuation or a sentence pause. Preserve unmodified raw output.
    character_times = {}
    sentence_cursor = 0
    for segment in result.get('segments', []):
        if not segment.get('chars'):
            continue
        sentence = segment['text']
        sentence_start = normalized.find(sentence, sentence_cursor)
        if sentence_start < 0 or normalized[sentence_cursor:sentence_start].strip():
            raise ValueError('sentence_source_map_mismatch')
        for offset, char in enumerate(segment['chars']):
            pos = sentence_start + offset
            if pos >= len(normalized) or char['char'] != normalized[pos]:
                raise ValueError('character_source_map_mismatch')
            character_times[pos] = char
        sentence_cursor = sentence_start + len(sentence)
    cursor = 0
    tokens, cues, diagnostics = [], [], []
    for word in result.get('word_segments', []):
        spelling = word.get('word', '')
        if not spelling:
            raise ValueError('empty_raw_word')
        pos = normalized.find(spelling, cursor)
        if pos < 0 or normalized[cursor:pos].strip():
            raise ValueError('alignment_text_occurrence_mismatch')
        end = pos + len(spelling)
        cursor = end
        core = word_core(content, pos, end)
        if core is None:
            continue
        start_char, end_char = core
        identifier = len(tokens)
        tokens.append({'id': identifier, 'startChar': utf16_offset(content, start_char),
                       'endChar': utf16_offset(content, end_char)})
        score = word.get('score')
        start, stop = word.get('start'), word.get('end')
        core_chars = [character_times[p] for p in range(start_char, end_char) if p in character_times]
        observed = [c for c in core_chars if isinstance(c.get('start'), (int, float)) and isinstance(c.get('end'), (int, float))
                    and math.isfinite(c['start']) and math.isfinite(c['end'])]
        if observed:
            start, stop = min(c['start'] for c in observed), max(c['end'] for c in observed)
            scores = [c['score'] for c in observed if isinstance(c.get('score'), (int, float)) and math.isfinite(c['score'])]
            score = round(sum(scores)/len(scores), 3) if scores else None
        score = float(score) if isinstance(score, (int, float)) and math.isfinite(score) else None
        diagnostic = {'tokenId': identifier, 'text': content[start_char:end_char], 'score': score}
        if isinstance(start, (int, float)) and isinstance(stop, (int, float)) and math.isfinite(start) and math.isfinite(stop):
            cue = {'startMs': round(start * 1000), 'endMs': round(stop * 1000), 'tokenIds': [identifier]}
            cues.append(cue)
            diagnostic.update(startMs=cue['startMs'], endMs=cue['endMs'])
        else:
            diagnostic['unaligned'] = True
        diagnostic['risk'] = bool(re.search(r'\d', diagnostic['text'])) or score is None or score < .5
        diagnostics.append(diagnostic)
    if normalized[cursor:].strip():
        raise ValueError('unmapped_trailing_text')
    expected = sum(word_core(content, m.start(), m.end()) is not None for m in re.finditer(r'\S+', content))
    if len(tokens) != expected:
        raise ValueError('display_token_count_mismatch')
    timeline = {'schemaVersion': 1, 'language': 'en', 'offsetEncoding': 'utf16', 'timeUnit': 'ms',
                'tokenizationVersion': TOKENIZATION_VERSION, 'titleid': titleid, 'level': level,
                'contentSha256': content_hash(content), 'audioSha256': audio_sha256,
                'durationMs': duration_ms, 'tokens': tokens, 'cues': cues}
    validate_timeline(timeline, content, audio_sha256)
    missing = [d for d in diagnostics if d.get('unaligned')]
    low = [d for d in diagnostics if d['score'] is None or d['score'] < .5]
    report = {'status': 'review_required', 'tokenCount': len(tokens), 'timedTokenCount': len(cues),
              'coveragePercent': round(len(cues) / len(tokens) * 100, 2) if tokens else 0,
              'missingTokens': missing, 'lowScoreTokens': low,
              'riskTokens': [d for d in diagnostics if d['risk']], 'wordDiagnostics': diagnostics,
              'structuralIssues': [], 'humanSyncReview': 'not_performed',
              'accuracyNote': 'Coverage and model score are not measured synchronization accuracy.'}
    return timeline, report


def validate_timeline(timeline: dict, content: str, audio_sha256: str) -> None:
    if timeline.get('schemaVersion') != 1 or timeline.get('offsetEncoding') != 'utf16' or timeline.get('timeUnit') != 'ms':
        raise ValueError('timeline_schema')
    if timeline.get('contentSha256') != content_hash(content) or timeline.get('audioSha256') != audio_sha256:
        raise ValueError('timeline_input_hash')
    duration = timeline['durationMs']
    if type(duration) is not int or duration <= 0:
        raise ValueError('timeline_duration')
    encoded = content.encode('utf-16-le')
    previous = 0
    tokens = timeline['tokens']
    if not tokens or len(tokens) > 10000 or len(timeline['cues']) > 30000:
        raise ValueError('timeline_size')
    for identifier, token in enumerate(tokens):
        a, b = token['startChar'], token['endChar']
        if type(token['id']) is not int or token['id'] != identifier or type(a) is not int or type(b) is not int or not 0 <= previous <= a < b <= len(encoded) // 2:
            raise ValueError('timeline_token_range')
        spelling = encoded[a*2:b*2].decode('utf-16-le')
        if not spelling.strip():
            raise ValueError('timeline_empty_token')
        previous = b
    previous_end = 0
    for cue in timeline['cues']:
        a, b = cue['startMs'], cue['endMs']
        ids = cue['tokenIds']
        if type(a) is not int or type(b) is not int or not 0 <= previous_end <= a < b <= duration:
            raise ValueError('timeline_cue_time')
        if not ids or len(set(ids)) != len(ids) or any(type(i) is not int or not 0 <= i < len(tokens) for i in ids):
            raise ValueError('timeline_cue_token')
        previous_end = b


def prepare_archive(package_path: Path, audio_dir: Path, output: Path, levels: list[int] | None = None) -> dict:
    news = json.loads(package_path.read_text(encoding='utf-8'))
    titleid = news.get('titleid', '')
    if not isinstance(titleid, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,199}', titleid):
        raise ValueError('invalid_titleid')
    if output.resolve() in (audio_dir.resolve(), package_path.parent.resolve()):
        raise ValueError('alignment_output_must_be_separate')
    rows = news.get('levels', [])
    requested = levels or [1, 2, 3]
    if not requested or len(set(requested)) != len(requested) or any(x not in (1, 2, 3) for x in requested):
        raise ValueError('invalid_levels')
    if not isinstance(rows, list) or any(sum(r.get('level') == n for r in rows) != 1 for n in requested):
        raise ValueError('duplicate_or_missing_level')
    pipeline_files = [Path(__file__), Path(__file__).with_name('whisperx_align.py'), PUNKT_PROVENANCE]
    pipeline_digest = hashlib.sha256(':'.join(sha256_file(p) for p in pipeline_files).encode()).hexdigest()
    samples = []
    for number in requested:
        row = next(r for r in rows if r.get('level') == number)
        content = row.get('content')
        if not isinstance(content, str) or not content.strip() or len(content) > 100000:
            raise ValueError('invalid_content')
        audio = audio_dir / f'{titleid}-level-{number}.mp3'
        if not audio.is_file() or not 0 < audio.stat().st_size <= 50_000_000:
            raise ValueError(f'missing_or_invalid_local_audio_level_{number}')
        destination = output / f'level-{number}'
        destination.mkdir(parents=True, exist_ok=True)
        audio_hash = sha256_file(audio)
        key = hashlib.sha256(f'{content_hash(content)}:{audio_hash}:{PIPELINE_VERSION}:{MODEL_SHA256}:{pipeline_digest}'.encode()).hexdigest()
        sample = {'newsTitle': news['title'], 'levelTitle': row.get('title'), 'titleid': titleid,
                  'level': number, 'content': content, 'sourcePackage': str(package_path.resolve()),
                  'sourceAudio': str(audio.resolve()), 'audioSha256': audio_hash,
                  'contentSha256': content_hash(content), 'alignmentKey': key,
                  'pipelineVersion': PIPELINE_VERSION, 'pipelineDigest': pipeline_digest, 'modelSha256': MODEL_SHA256}
        # Never trust only an existing filename; bind the copied media to bytes.
        target = destination / 'sample.mp3'
        if not target.exists() or sha256_file(target) != audio_hash:
            shutil.copyfile(audio, target)
        (destination / 'transcript.txt').write_text(content, encoding='utf-8')
        write_json(destination / 'sample.json', sample)
        samples.append(str(destination))
    manifest = {'schemaVersion': 1, 'titleid': titleid, 'newsTitle': news['title'],
                'pipelineVersion': PIPELINE_VERSION, 'samples': samples, 'localOnly': True}
    write_json(output / 'alignment-input.json', manifest)
    return manifest


def check_runtime(python: str | None = None, model_dir: str | None = None) -> tuple[Path, Path, Path]:
    executable = Path(python or os.environ.get('LEVEL_READ_ALIGNMENT_PYTHON', RUNTIME_ROOT / '.venv/bin/python'))
    models = Path(model_dir or os.environ.get('LEVEL_READ_ALIGNMENT_MODEL_DIR', RUNTIME_ROOT / 'models'))
    if not executable.is_file():
        raise RuntimeError(f'Local alignment runtime not installed: {executable}')
    if not shutil.which('ffmpeg'):
        raise RuntimeError('FFmpeg is required for local alignment')
    model = models / MODEL_FILENAME
    if not model.is_file() or sha256_file(model) != MODEL_SHA256:
        raise RuntimeError('Verified English alignment model is not installed')
    punkt = Path(os.environ.get('LEVEL_READ_PUNKT_DIR') or RUNTIME_ROOT / 'nltk_data/tokenizers/punkt_tab/english').expanduser()
    verify_punkt_resources(punkt)
    return executable, models, punkt


def align_archive(package_path: Path, audio_dir: Path, output: Path, *, python: str | None = None,
                  model_dir: str | None = None, levels: list[int] | None = None, resume: bool = False) -> dict:
    executable, models, punkt = check_runtime(python, model_dir)
    manifest = prepare_archive(package_path, audio_dir, output, levels)
    command = [str(executable), str(Path(__file__).with_name('whisperx_align.py')),
               '--manifest', str(output / 'alignment-input.json'), '--model-dir', str(models),
               '--punkt-dir', str(punkt)]
    if resume:
        command.append('--resume')
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    (output / 'alignment-run.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    summary_path = output / 'alignment-manifest.json'
    if result.returncode or not summary_path.is_file():
        raise RuntimeError(f'Local alignment failed; see {output / "alignment-run.log"}')
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    if summary.get('failedLevels'):
        raise RuntimeError(f'Alignment validation failed for levels {summary["failedLevels"]}; see {summary_path}')
    from alignment_preview import build_preview
    build_preview(output)
    return summary
