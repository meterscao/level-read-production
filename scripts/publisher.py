#!/usr/bin/env python3
"""Internal Level Read publisher. Uses only the Python standard library."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import mimetypes
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("LEVEL_READ_PRODUCTION_CONFIG", Path.home() / ".codex" / "level-read-production" / "config.json"))
OUTPUT_ROOT = Path(os.environ.get("LEVEL_READ_PRODUCTION_OUTPUT_ROOT", Path.home() / "Documents" / "Level Read Production"))
COLLECTION = "enil_news"


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def load_config() -> dict[str, Any]:
    try:
        return json.loads(CONFIG_PATH.read_text("utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"Missing configuration file: {CONFIG_PATH}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid JSON configuration: {CONFIG_PATH}") from error


def get_setting(config: dict[str, Any], section: str, key: str) -> str:
    value = config.get(section, {}).get(key)
    if not isinstance(value, str) or not value.strip() or value == "replace-me":
        raise RuntimeError(f"Missing configuration: {section}.{key}")
    return value.strip()


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9\s-]", "", title.lower())
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise RuntimeError("Title cannot produce a URL-safe titleid")
    return slug[:120]


def story_output_directory(publication_date: dt.date, titleid: str) -> Path:
    """Return the stable, per-story local archive directory."""
    return OUTPUT_ROOT.expanduser() / f"{publication_date.isoformat()}-{titleid}"


def validate_levels(news: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    levels = news.get("levels")
    if not isinstance(news.get("title"), str) or not news["title"].strip():
        errors.append("title is required")
    if not isinstance(news.get("summary"), str) or not news["summary"].strip():
        errors.append("summary is required")
    if not isinstance(levels, list) or [item.get("level") for item in levels if isinstance(item, dict)] != [1, 2, 3]:
        errors.append("levels must be exactly 1, 2, 3 in order")
        return errors, warnings
    expected = {1: (3, 1, 90, 140), 2: (4, 2, 130, 210), 3: (5, 3, 180, 290)}
    all_answers: list[str] = []
    for level in levels:
        number = level["level"]
        expected_vocab, expected_quiz, minimum, maximum = expected[number]
        content = level.get("content")
        if not isinstance(content, str) or not content.strip():
            errors.append(f"level {number} content is required")
            continue
        count = word_count(content)
        if count < minimum or count > maximum:
            warnings.append(f"level {number} word count {count} is outside {minimum}-{maximum}")
        vocabulary = level.get("vocabulary") or []
        quizzes = level.get("quiz") or []
        if len(vocabulary) != expected_vocab:
            errors.append(f"level {number} must have {expected_vocab} vocabulary items")
        if len(quizzes) != expected_quiz:
            errors.append(f"level {number} must have {expected_quiz} quizzes")
        for item in vocabulary:
            word = item.get("word") if isinstance(item, dict) else None
            if not isinstance(word, str) or not re.search(rf"(?i)(?<![a-z]){re.escape(word)}(?![a-z])", content):
                errors.append(f"level {number} vocabulary must appear in its content")
        for quiz in quizzes:
            options = quiz.get("options") if isinstance(quiz, dict) else None
            answer = quiz.get("answer") if isinstance(quiz, dict) else None
            if not isinstance(options, list) or len(options) != 3 or len({str(item).strip() for item in options}) != 3:
                errors.append(f"level {number} quiz must have three distinct options")
            if answer not in {"1", "2", "3"}:
                errors.append(f"level {number} quiz answer must be 1, 2, or 3")
            else:
                all_answers.append(answer)
    if len(all_answers) == 6:
        counts = [all_answers.count(answer) for answer in ("1", "2", "3")]
        repeated = any(all_answers[index] == all_answers[index - 1] == all_answers[index - 2] for index in range(2, 6))
        if min(counts) < 1 or max(counts) > 3 or repeated:
            errors.append("six quiz answers need a balanced distribution without three matching positions in sequence")
    return errors, warnings


def normalize_quizzes(news: dict[str, Any]) -> dict[str, Any]:
    quizzes = [quiz for level in news.get("levels", []) for quiz in level.get("quiz", [])]
    if len(quizzes) != 6:
        return news
    targets = ["1", "2", "3", "1", "2", "3"]
    # Rotating by a time-derived offset avoids a fixed answer key while staying deterministic within one run.
    offset = int(time.time()) % 6
    targets = targets[offset:] + targets[:offset]
    for quiz, target in zip(quizzes, targets):
        answer_index = int(quiz["answer"]) - 1
        options = quiz["options"]
        if answer_index not in (0, 1, 2) or len(options) != 3:
            raise RuntimeError("Cannot normalize a malformed quiz")
        correct = options[answer_index]
        distractors = [option for index, option in enumerate(options) if index != answer_index]
        target_index = int(target) - 1
        quiz["options"] = [correct if index == target_index else distractors.pop(0) for index in range(3)]
        quiz["answer"] = target
    return news


def cos_authorization(secret_id: str, secret_key: str, method: str, host: str, object_key: str, content_length: int) -> str:
    now = int(time.time())
    key_time = f"{now};{now + 1800}"
    sign_key = hmac.new(secret_key.encode(), key_time.encode(), hashlib.sha1).hexdigest()
    headers = f"content-length={content_length}&host={host}"
    http_string = f"{method.lower()}\n/{object_key}\n\n{headers}\n"
    string_to_sign = f"sha1\n{key_time}\n{hashlib.sha1(http_string.encode()).hexdigest()}\n"
    signature = hmac.new(bytes.fromhex(sign_key), string_to_sign.encode(), hashlib.sha1).hexdigest()
    return f"q-sign-algorithm=sha1&q-ak={secret_id}&q-sign-time={key_time}&q-key-time={key_time}&q-header-list=content-length;host&q-url-param-list=&q-signature={signature}"


def cos_upload(config: dict[str, Any], local_path: Path, object_key: str) -> str:
    secret_id = get_setting(config, "cos", "secret_id")
    secret_key = get_setting(config, "cos", "secret_key")
    bucket = get_setting(config, "cos", "bucket")
    region = get_setting(config, "cos", "region")
    body = local_path.read_bytes()
    host = f"{bucket}.cos.{region}.myqcloud.com"
    request = urllib.request.Request(
        f"https://{host}/{urllib.parse.quote(object_key)}",
        data=body,
        method="PUT",
        headers={
            "Host": host,
            "Content-Length": str(len(body)),
            "Authorization": cos_authorization(secret_id, secret_key, "PUT", host, object_key, len(body)),
            "Content-Type": mimetypes.guess_type(local_path.name)[0] or "application/octet-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60):
            pass
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"COS upload failed for {object_key}: HTTP {error.code} {error.read().decode('utf-8', 'replace')}") from error
    except (urllib.error.URLError, OSError) as error:
        raise RuntimeError(f"COS upload network failure for {object_key}: {getattr(error, 'reason', error)}") from error
    return f"https://{host}/{urllib.parse.quote(object_key)}"


def generate_audio(config: dict[str, Any], text: str) -> bytes:
    base_url = get_setting(config, "ai", "base_url").rstrip("/")
    api_key = get_setting(config, "ai", "api_key")
    model = config.get("ai", {}).get("tts_model") or "tts-1"
    voice = config.get("ai", {}).get("tts_voice") or "shimmer"
    request = urllib.request.Request(
        f"{base_url}/audio/speech",
        data=compact_json({"model": model, "voice": voice, "input": text}).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"AI audio generation failed: HTTP {error.code} {error.read().decode('utf-8', 'replace')}") from error
    except (urllib.error.URLError, OSError) as error:
        raise RuntimeError(f"AI audio generation network failure: {getattr(error, 'reason', error)}") from error


def tc3_hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


def cloudbase_authorization(secret_id: str, secret_key: str, method: str, url: str, headers: dict[str, str], params: dict[str, Any], timestamp: int) -> str:
    parsed = urllib.parse.urlparse(url)
    canonical_headers = {urllib.parse.quote(key.lower().strip(), safe="~"): str(value).strip().lower() for key, value in headers.items()}
    signed_headers = ";".join(sorted(canonical_headers))
    canonical_header_text = "\n".join(f"{key}:{canonical_headers[key]}" for key in sorted(canonical_headers)) + "\n"
    signed_params = {urllib.parse.quote(key.lower().strip(), safe="~"): compact_json(value) if isinstance(value, (dict, list)) else str(value) for key, value in params.items() if value not in (None, "", False, 0)}
    payload = "".join(f"&{key}={signed_params[key]}\r\n" for key in sorted(signed_params))
    canonical_request = f"{method.lower()}\n//{parsed.netloc}\n{parsed.query}\n{canonical_header_text}\n{signed_headers}\n{hashlib.sha256(payload.encode()).hexdigest()}"
    date = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).strftime("%Y-%m-%d")
    scope = f"{date}/tcb/tc3_request"
    string_to_sign = f"TC3-HMAC-SHA256\n{timestamp}\n{scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    secret_date = tc3_hmac(f"TC3{secret_key}".encode(), date)
    secret_service = tc3_hmac(secret_date, "tcb")
    secret_signing = tc3_hmac(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
    return f"TC3-HMAC-SHA256 Credential={secret_id}/{scope}, SignedParams={';'.join(sorted(signed_params))}, SignedHeaders={signed_headers}, Signature={signature}"


def cloudbase_insert(config: dict[str, Any], news: dict[str, Any]) -> str:
    secret_id = get_setting(config, "cloudbase", "secret_id")
    secret_key = get_setting(config, "cloudbase", "secret_key")
    environment = get_setting(config, "cloudbase", "env")
    region = get_setting(config, "cloudbase", "region")
    url = "https://tcb-api.tencentcloudapi.com"
    timestamp = int(time.time()) - 1
    params = {"action": "database.insertDocument", "collectionName": COLLECTION, "data": [compact_json(news)], "instance": "", "database": "", "envName": environment}
    headers = {"Content-Type": "application/json", "Host": "tcb-api.tencentcloudapi.com", "X-TCB-Source": ",", "X-Client-Timestamp": str(int(time.time() * 1000)), "X-SDK-Version": "level-read-production/1.0.0", "X-TCB-Region": region}
    headers["Authorization"] = cloudbase_authorization(secret_id, secret_key, "post", url, headers, params, timestamp)
    headers["X-Signature-Expires"] = "600"
    headers["X-Timestamp"] = str(timestamp)
    request = urllib.request.Request(url, data=compact_json(params).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"CloudBase ingest failed: HTTP {error.code} {error.read().decode('utf-8', 'replace')}") from error
    if payload.get("code"):
        raise RuntimeError(f"CloudBase ingest failed: {payload.get('code')} {payload.get('message', '')}")
    identifiers = payload.get("data", {}).get("insertedIds", [])
    if not identifiers:
        raise RuntimeError("CloudBase ingest returned no inserted id")
    return str(identifiers[0])


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", "utf-8")


def write_production_state(output: Path, stage: str, titleid: str, cover_url: str | None = None, audios: dict[str, str] | None = None, error: str | None = None) -> None:
    state: dict[str, Any] = {"stage": stage, "titleid": titleid, "updatedAt": int(time.time() * 1000)}
    if cover_url:
        state["cover"] = cover_url
    if audios:
        state["audios"] = audios
    if error:
        state["error"] = error
    write_json(output / "production-state.json", state)


def cmd_doctor(_: argparse.Namespace) -> int:
    config = load_config()
    required = {"ai": ("base_url", "api_key"), "cos": ("secret_id", "secret_key", "bucket", "region"), "cloudbase": ("env", "secret_id", "secret_key", "region")}
    report = {section: {"configured": not [key for key in keys if not isinstance(config.get(section, {}).get(key), str) or not config[section][key].strip() or config[section][key] == "replace-me"], "missing": [key for key in keys if not isinstance(config.get(section, {}).get(key), str) or not config[section][key].strip() or config[section][key] == "replace-me"]} for section, keys in required.items()}
    print(json.dumps({"success": all(item["configured"] for item in report.values()), "config_path": str(CONFIG_PATH), "capabilities": report}, ensure_ascii=False, indent=2))
    return 0


def cmd_produce(args: argparse.Namespace) -> int:
    config = load_config()
    levels = json.loads(Path(args.levels).read_text("utf-8"))
    levels = normalize_quizzes(levels)
    errors, warnings = validate_levels(levels)
    if errors:
        raise RuntimeError("Level package failed validation: " + "; ".join(errors))
    cover = Path(args.cover)
    if not cover.is_file():
        raise RuntimeError(f"Cover file not found: {cover}")
    try:
        publication_date = dt.date.fromisoformat(args.date)
    except ValueError as error:
        raise RuntimeError("date must use YYYY-MM-DD") from error
    titleid = args.titleid or slugify(levels["title"])
    output = Path(args.output).expanduser().resolve() if args.output else story_output_directory(publication_date, titleid).resolve()
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "news-complete.json", levels)
    archived_cover = output / f"cover{cover.suffix.lower() or '.png'}"
    if cover.resolve() != archived_cover.resolve():
        shutil.copy2(cover, archived_cover)
    write_production_state(output, "local_assets_ready", titleid)
    local_audios: dict[str, Path] = {}
    for level in levels["levels"]:
        filename = f"{titleid}-level-{level['level']}.mp3"
        local_audio = output / filename
        try:
            local_audio.write_bytes(generate_audio(config, level["content"]))
        except Exception as error:
            message = f"Audio generation failed at level {level['level']} before any upload: {error}"
            write_production_state(output, "audio_generation_failed", titleid, error=message)
            raise RuntimeError(message) from error
        local_audios[str(level["level"])] = local_audio
    write_production_state(output, "audio_generated", titleid)
    try:
        cover_url = cos_upload(config, archived_cover, f"covers/{int(time.time() * 1000)}-{archived_cover.name}")
    except Exception as error:
        message = f"Cover upload failed before any audio upload: {error}"
        write_production_state(output, "cover_upload_failed", titleid, error=message)
        raise RuntimeError(message) from error
    write_production_state(output, "cover_uploaded", titleid, cover_url=cover_url)
    audios: dict[str, str] = {}
    for level in levels["levels"]:
        number = str(level["level"])
        try:
            audios[number] = cos_upload(config, local_audios[number], f"audios/{local_audios[number].name}")
        except Exception as error:
            message = f"Audio upload failed at level {number}: {error}"
            write_production_state(output, "audio_upload_failed", titleid, cover_url=cover_url, audios=audios, error=message)
            raise RuntimeError(message) from error
        write_production_state(output, "audio_uploading", titleid, cover_url=cover_url, audios=audios)
    package = {"titleid": titleid, "title": levels["title"], "summary": levels["summary"], "levels": [{**level, "audio": audios[str(level["level"])]} for level in levels["levels"]], "cover": cover_url, "date": int(dt.datetime.combine(publication_date, dt.time.min, tzinfo=dt.timezone.utc).timestamp() * 1000), "originalUrl": args.original_url, "public": False, "readCount": 0}
    write_json(output / "cover-upload.json", {"url": cover_url})
    write_json(output / "audio-metadata.json", {"titleid": titleid, "audios": audios})
    write_json(output / "news-package.json", package)
    write_json(output / "qa.json", {"valid": True, "warnings": warnings})
    write_production_state(output, "complete", titleid, cover_url=cover_url, audios=audios)
    print(json.dumps({"success": True, "output": str(output), "titleid": titleid, "public": False, "qa": "needs review" if warnings else "ready for CMS review"}, ensure_ascii=False, indent=2))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    if not args.confirm_unpublished_ingest:
        raise RuntimeError("ingest requires --confirm-unpublished-ingest")
    config = load_config()
    package = json.loads(Path(args.input).read_text("utf-8"))
    if package.get("public") is not False:
        raise RuntimeError("Refusing to ingest a package unless public is false")
    errors, warnings = validate_levels(package)
    if errors:
        raise RuntimeError("News package failed validation: " + "; ".join(errors))
    if not isinstance(package.get("cover"), str) or not package["cover"].startswith(("http://", "https://")):
        raise RuntimeError("News package needs an uploaded cover URL")
    if any(not item.get("audio", "").startswith(("http://", "https://")) for item in package["levels"]):
        raise RuntimeError("News package needs uploaded audio URLs for all levels")
    identifier = cloudbase_insert(config, package)
    print(json.dumps({"success": True, "id": identifier, "title": package["title"], "titleid": package["titleid"], "public": False, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal Level Read publisher")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    produce = commands.add_parser("produce")
    produce.add_argument("--levels", required=True)
    produce.add_argument("--cover", required=True)
    produce.add_argument("--original-url", required=True)
    produce.add_argument("--date", required=True)
    produce.add_argument("--output", help="Override the default per-story directory for controlled testing")
    produce.add_argument("--titleid")
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--input", required=True)
    ingest.add_argument("--confirm-unpublished-ingest", action="store_true")
    args = parser.parse_args()
    if args.command == "doctor": return cmd_doctor(args)
    if args.command == "produce": return cmd_produce(args)
    return cmd_ingest(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"success": False, "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)
