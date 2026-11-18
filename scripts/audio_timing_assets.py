"""Hash-bound audio timelines and immutable COS assets for normal news production.

This module never creates a CMS approval or claims human acoustic review. Network
operations are called only by the explicitly selected production/ingest command.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from audio_alignment import content_hash, sha256_file, utf16_offset, validate_timeline, word_core

ORIGINS = ('https://levelread.com', 'http://127.0.0.1:3130')
REFERENCE_KEYS = {'schemaVersion', 'timelineUrl', 'timelineSha256', 'contentSha256', 'audioSha256', 'audioUrl', 'durationMs'}
TIMELINE_KEYS = {'schemaVersion', 'language', 'offsetEncoding', 'timeUnit', 'tokenizationVersion', 'titleid', 'level', 'contentSha256', 'audioSha256', 'durationMs', 'tokens', 'cues'}


def _json(path: Path) -> Any:
    return json.loads(path.read_text('utf-8'))


def _atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', 'utf-8')
    temporary.replace(path)


def decoded_duration_ms(path: Path) -> int:
    # Same ffmpeg PCM decoding and 16kHz sample clock as WhisperX load_audio.
    result = subprocess.run(['ffmpeg', '-nostdin', '-threads', '0', '-i', str(path), '-f', 's16le',
                             '-ac', '1', '-acodec', 'pcm_s16le', '-ar', '16000', '-'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    if result.returncode or not result.stdout or len(result.stdout) % 2:
        raise RuntimeError('audio_duration_decode_failed')
    return round(len(result.stdout) / 2 / 16000 * 1000)


def _https_url(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError('invalid_asset_url')
    url = urllib.parse.urlsplit(value)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('invalid_asset_url')
    return value


def validate_reference(ref: Any, content: str, audio_url: str) -> dict:
    if not isinstance(ref, dict) or set(ref) != REFERENCE_KEYS or type(ref['schemaVersion']) is not int or ref['schemaVersion'] != 1:
        raise ValueError('timing_reference_schema')
    for key in ('contentSha256', 'audioSha256', 'timelineSha256'):
        if not isinstance(ref[key], str) or not re.fullmatch('[a-f0-9]{64}', ref[key]):
            raise ValueError('timing_reference_hash')
    if ref['contentSha256'] != content_hash(content) or ref['audioUrl'] != audio_url:
        raise ValueError('timing_reference_source_changed')
    if type(ref['durationMs']) is not int or not 0 < ref['durationMs'] <= 86400000:
        raise ValueError('timing_reference_duration')
    _https_url(ref['audioUrl']); _https_url(ref['timelineUrl'])
    return ref


def _validate_source_map(timeline: dict, content: str, audio_hash: str, titleid: str, level: int) -> None:
    if type(timeline.get('schemaVersion')) is not int or timeline.get('schemaVersion') != 1 or set(timeline) != TIMELINE_KEYS or timeline.get('language') != 'en' or timeline.get('tokenizationVersion') != 'en-display-v1' or timeline.get('titleid') != titleid or type(timeline.get('level')) is not int or timeline['level'] != level:
        raise ValueError('timeline_identity_schema')
    validate_timeline(timeline, content, audio_hash)
    expected = []
    for word in re.finditer(r'\S+', content):
        core = word_core(content, word.start(), word.end())
        if core:
            expected.append({'id': len(expected), 'startChar': utf16_offset(content, core[0]), 'endChar': utf16_offset(content, core[1])})
    if timeline['tokens'] != expected or not timeline['cues']:
        raise ValueError('timeline_exact_source_map')
    previous_token = -1
    for cue in timeline['cues']:
        if set(cue) != {'startMs', 'endMs', 'tokenIds'} or cue['tokenIds'] != list(range(cue['tokenIds'][0], cue['tokenIds'][-1] + 1)) or cue['tokenIds'][0] <= previous_token:
            raise ValueError('timeline_cue_token_order')
        previous_token = cue['tokenIds'][-1]


def prepare_timing_assets(package: dict, audio_dir: Path, alignment_dir: Path) -> list[dict]:
    """Validate every Level before the first upload. No configuration/network I/O."""
    titleid = package.get('titleid')
    if not isinstance(titleid, str) or not re.fullmatch('[a-z0-9][a-z0-9-]{0,199}', titleid):
        raise ValueError('timing_titleid')
    rows = package.get('levels')
    if not isinstance(rows, list) or len(rows) != 3 or any(not isinstance(r, dict) or type(r.get('level')) is not int for r in rows) or [r.get('level') for r in rows] != [1, 2, 3]:
        raise ValueError('timing_three_unique_levels_required')
    manifest = _json(alignment_dir / 'alignment-manifest.json')
    if manifest.get('titleid') != titleid or manifest.get('failedLevels') or sorted(r.get('level') for r in manifest.get('outcomes', [])) != [1, 2, 3]:
        raise ValueError('alignment_manifest_incomplete')
    prepared = []
    for row in rows:
        level = row['level']; content = row.get('content')
        if not isinstance(content, str) or not content.strip():
            raise ValueError('timing_content')
        audio_path = audio_dir / f'{titleid}-level-{level}.mp3'
        directory = alignment_dir / f'level-{level}'
        timeline_path = directory / 'timeline.json'
        audio_hash, timeline_hash = sha256_file(audio_path), sha256_file(timeline_path)
        if not 0 < audio_path.stat().st_size <= 50_000_000 or not 0 < timeline_path.stat().st_size <= 1_000_000:
            raise ValueError('timing_asset_size')
        sample, quality, timeline = _json(directory / 'sample.json'), _json(directory / 'quality.json'), _json(timeline_path)
        if (sample.get('titleid'), sample.get('level'), sample.get('content'), sample.get('audioSha256'), sample.get('contentSha256')) != (titleid, level, content, audio_hash, content_hash(content)):
            raise ValueError('alignment_sample_changed')
        pipeline_digest = sample.get('pipelineDigest')
        if not isinstance(pipeline_digest, str) or not re.fullmatch('[a-f0-9]{64}', pipeline_digest) or quality.get('timelineSha256') != timeline_hash or quality.get('alignmentKey') != sample.get('alignmentKey') or quality.get('structuralIssues'):
            raise ValueError('alignment_quality_changed')
        if sha256_file(directory / 'sample.mp3') != audio_hash:
            raise ValueError('alignment_audio_changed')
        _validate_source_map(timeline, content, audio_hash, titleid, level)
        if abs(decoded_duration_ms(audio_path) - timeline['durationMs']) > 2:
            raise ValueError('timeline_media_duration_mismatch')
        audio_key = f'audios/{titleid}/level-{level}/{audio_hash}.mp3'
        timeline_key = f'audio-timings/{titleid}/level-{level}/{content_hash(content)}/{audio_hash}/{pipeline_digest}/{timeline_hash}.json'
        prepared.append({'level': level, 'titleid': titleid, 'content': content, 'durationMs': timeline['durationMs'],
                         'contentSha256': content_hash(content), 'audioSha256': audio_hash, 'timelineSha256': timeline_hash,
                         'pipelineDigest': pipeline_digest, 'audioPath': str(audio_path.resolve()), 'timelinePath': str(timeline_path.resolve()),
                         'audioKey': audio_key, 'timelineKey': timeline_key})
    return prepared


def _target(config: dict) -> tuple[str, str, str]:
    cos = config.get('cos', {})
    values = [cos.get(k) for k in ('secret_id', 'secret_key', 'bucket', 'region')]
    if any(not isinstance(v, str) or not v or v == 'replace-me' for v in values):
        raise ValueError('cos_configuration_incomplete')
    secret_id, secret_key, bucket, region = values
    if not re.fullmatch('[a-z0-9][a-z0-9-]*-[0-9]+', bucket) or not re.fullmatch('[a-z0-9-]+', region):
        raise ValueError('cos_target_invalid')
    return f'{bucket}.cos.{region}.myqcloud.com', secret_id, secret_key


def _authorization(secret_id: str, secret_key: str, method: str, key: str, headers: dict, query: dict) -> str:
    now = int(time.time()); key_time = f'{now};{now + 1800}'
    quote = lambda v: urllib.parse.quote(str(v), safe='-_.~')
    names = sorted(k.lower() for k in headers)
    encoded_headers = '&'.join(f'{quote(k)}={quote(headers[k])}' for k in names)
    params = sorted(query)
    encoded_query = '&'.join(f'{quote(k)}={quote(query[k])}' for k in params)
    http_string = f'{method.lower()}\n/{urllib.parse.quote(key, safe="/-_.~")}\n{encoded_query}\n{encoded_headers}\n'
    sign_key = hmac.new(secret_key.encode(), key_time.encode(), hashlib.sha1).hexdigest()
    string_to_sign = f'sha1\n{key_time}\n{hashlib.sha1(http_string.encode()).hexdigest()}\n'
    signature = hmac.new(sign_key.encode(), string_to_sign.encode(), hashlib.sha1).hexdigest()
    return f'q-sign-algorithm=sha1&q-ak={secret_id}&q-sign-time={key_time}&q-key-time={key_time}&q-header-list={";".join(names)}&q-url-param-list={";".join(params)}&q-signature={signature}'


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


def _http(request: urllib.request.Request, limit: int) -> tuple[int, dict, bytes]:
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=60) as response:
            body = response.read(limit + 1)
            if len(body) > limit:
                raise RuntimeError('cos_readback_size_exceeded')
            return response.status, {k.lower(): v for k, v in response.headers.items()}, body
    except urllib.error.HTTPError as error:
        return error.code, {}, b''
    except (urllib.error.URLError, OSError) as error:
        raise RuntimeError('cos_network_failure') from error


def _signed(config: dict, method: str, key: str, *, body: bytes | None = None, content_type: str | None = None, query: dict | None = None, limit: int = 50_000_000) -> tuple[int, dict, bytes]:
    host, secret_id, secret_key = _target(config)
    headers = {'host': host}
    if method == 'PUT':
        headers.update({'content-length': str(len(body)), 'content-type': content_type,
                        'cache-control': 'public,max-age=31536000,immutable', 'x-cos-forbid-overwrite': 'true'})
    params = query or {}
    authorization = _authorization(secret_id, secret_key, method, key, headers, params)
    url = f'https://{host}/{urllib.parse.quote(key, safe="/-_.~")}'
    if params:
        url += '?' + urllib.parse.urlencode(params)
    return _http(urllib.request.Request(url, method=method, data=body,
                 headers={**headers, 'Authorization': authorization}), limit)


def _verify(config: dict, key: str, data: bytes, content_type: str) -> dict:
    status, headers, readback = _signed(config, 'GET', key, limit=len(data))
    if status != 200 or hashlib.sha256(readback).digest() != hashlib.sha256(data).digest() or headers.get('content-type', '').split(';')[0] != content_type:
        raise RuntimeError('cos_signed_readback_mismatch')
    host, _, _ = _target(config); url = f'https://{host}/{key}'
    for origin in ORIGINS:
        status, headers, readback = _http(urllib.request.Request(url, headers={'Origin': origin}), len(data))
        if status != 200 or hashlib.sha256(readback).digest() != hashlib.sha256(data).digest() or headers.get('content-type', '').split(';')[0] != content_type or headers.get('access-control-allow-origin') not in ('*', origin):
            raise RuntimeError('cos_public_readback_or_cors_mismatch')
    return {'key': key, 'sha256': hashlib.sha256(data).hexdigest(), 'byteLength': len(data), 'contentType': content_type}


def _materialize(prepared: list[dict]) -> list[tuple[dict, str, bytes, str]]:
    if len(prepared) != 3 or [r.get('level') for r in prepared] != [1, 2, 3]:
        raise ValueError('timing_three_unique_levels_required')
    result = []
    for row in prepared:
        for kind, mime in [('audio', 'audio/mpeg'), ('timeline', 'application/json')]:
            data = Path(row[kind + 'Path']).read_bytes()
            if hashlib.sha256(data).hexdigest() != row[kind + 'Sha256']:
                raise ValueError('timing_prepared_asset_changed')
            result.append((row, kind, data, mime))
    return result


def _result(config: dict, prepared: list[dict], assets: list[dict]) -> dict:
    host, _, _ = _target(config)
    audios, timings = {}, {}
    for row in prepared:
        audio = f'https://{host}/{row["audioKey"]}'
        reference = {'schemaVersion': 1, 'timelineUrl': f'https://{host}/{row["timelineKey"]}',
                     **{k: row[k] for k in ('contentSha256', 'audioSha256', 'timelineSha256', 'durationMs')}, 'audioUrl': audio}
        validate_reference(reference, row['content'], audio)
        audios[str(row['level'])] = audio; timings[str(row['level'])] = reference
    return {'schemaVersion': 1, 'status': 'verified', 'audios': audios, 'timings': timings, 'assets': assets,
            'humanSyncReview': 'not_performed', 'cmsApprovalsCreated': 0}


def verify_uploaded_timings(config: dict, prepared: list[dict]) -> dict:
    """Fresh read-only signed/public verification before an authorized PG ingest."""
    return _result(config, prepared, [_verify(config, row[kind + 'Key'], data, mime) for row, kind, data, mime in _materialize(prepared)])


def upload_timing_assets(config: dict, prepared: list[dict], receipt_path: Path) -> dict:
    materialized = _materialize(prepared)  # Read all six source files before any remote I/O.
    status, _, body = _signed(config, 'GET', '', query={'versioning': ''}, limit=65536)
    if status != 200:
        raise RuntimeError('cos_versioning_check_failed')
    try:
        version = ET.fromstring(body)
    except ET.ParseError as error:
        raise RuntimeError('cos_versioning_check_failed') from error
    if version.tag.rsplit('}', 1)[-1] != 'VersioningConfiguration' or any(node.tag.rsplit('}', 1)[-1] == 'Status' for node in version.iter()):
        raise RuntimeError('cos_bucket_versioning_not_never_enabled')
    assets = []
    for row, kind, data, mime in materialized:
        key = row[kind + 'Key']
        status, _, _ = _signed(config, 'HEAD', key, limit=0)
        disposition = 'reused'
        if status == 404:
            status, _, _ = _signed(config, 'PUT', key, body=data, content_type=mime, limit=65536)
            if status not in (200, 409, 412):
                raise RuntimeError(f'cos_put_failed_http_{status}')
            disposition = 'created' if status == 200 else 'reused'
        elif status != 200:
            raise RuntimeError(f'cos_head_failed_http_{status}')
        assets.append({**_verify(config, key, data, mime), 'disposition': disposition})
        _atomic(receipt_path, {'schemaVersion': 1, 'status': 'uploading', 'completedObjects': len(assets), 'assets': assets})
    result = _result(config, prepared, assets)
    _atomic(receipt_path, result)
    return result


def validate_package_timings(package: dict, directory: Path, require_all: bool = False) -> list[dict]:
    references = [row.get('audioTiming') for row in package.get('levels', [])]
    if not any(ref is not None for ref in references) and not require_all:
        return []  # Existing legacy inspect/validation remains read-only and compatible.
    for row in package.get('levels', []):
        validate_reference(row.get('audioTiming'), row['content'], row.get('audio'))
    prepared = prepare_timing_assets(package, directory, directory / 'audio-timings')
    for row, level in zip(prepared, package['levels']):
        ref = level['audioTiming']
        if any(ref[k] != row[k] for k in ('contentSha256', 'audioSha256', 'timelineSha256', 'durationMs')) or not ref['audioUrl'].endswith('/' + row['audioKey']) or not ref['timelineUrl'].endswith('/' + row['timelineKey']):
            raise ValueError('package_timing_local_binding_changed')
    return prepared
