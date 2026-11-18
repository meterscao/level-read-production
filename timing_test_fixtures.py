"""Synthetic unit-test media and exact source maps; never an acoustic assertion."""
import hashlib
import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts'))
import audio_alignment as alignment


def fake_alignment(package_path, audio_dir, output, **_kwargs):
    package = json.loads(Path(package_path).read_text())
    alignment.prepare_archive(Path(package_path), Path(audio_dir), Path(output))
    outcomes = []
    for row in package['levels']:
        directory = Path(output) / f'level-{row["level"]}'
        sample = json.loads((directory / 'sample.json').read_text())
        tokens = []
        for chunk in re.finditer(r'\S+', row['content']):
            core = alignment.word_core(row['content'], chunk.start(), chunk.end())
            if core:
                tokens.append({'id': len(tokens), 'startChar': alignment.utf16_offset(row['content'], core[0]), 'endChar': alignment.utf16_offset(row['content'], core[1])})
        cues = [{'startMs': i * 2, 'endMs': i * 2 + 1, 'tokenIds': [i]} for i in range(len(tokens))]
        timeline = {'schemaVersion': 1, 'language': 'en', 'offsetEncoding': 'utf16', 'timeUnit': 'ms', 'tokenizationVersion': 'en-display-v1', 'titleid': package['titleid'], 'level': row['level'], 'contentSha256': sample['contentSha256'], 'audioSha256': sample['audioSha256'], 'durationMs': 1000, 'tokens': tokens, 'cues': cues}
        alignment.write_json(directory / 'timeline.json', timeline)
        alignment.write_json(directory / 'quality.json', {'alignmentKey': sample['alignmentKey'], 'timelineSha256': alignment.sha256_file(directory / 'timeline.json'), 'structuralIssues': [], 'humanSyncReview': 'not_performed'})
        outcomes.append({'level': row['level'], 'status': 'review_required'})
    summary = {'titleid': package['titleid'], 'failedLevels': [], 'outcomes': outcomes, 'status': 'review_required'}
    alignment.write_json(Path(output) / 'alignment-manifest.json', summary)
    return summary


def fake_upload(_config, prepared, receipt_path):
    audios, timings = {}, {}
    for row in prepared:
        url = 'https://bucket-123.cos.ap-guangzhou.myqcloud.com/' + row['audioKey']
        ref = {'schemaVersion': 1, 'audioUrl': url, 'timelineUrl': 'https://bucket-123.cos.ap-guangzhou.myqcloud.com/' + row['timelineKey'], **{k: row[k] for k in ['contentSha256', 'audioSha256', 'timelineSha256', 'durationMs']}}
        audios[str(row['level'])] = url; timings[str(row['level'])] = ref
    return {'audios': audios, 'timings': timings, 'assets': []}
