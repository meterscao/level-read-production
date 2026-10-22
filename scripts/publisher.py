#!/usr/bin/env python3
"""Internal Level Read publisher. Uses only the Python standard library."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import itertools
import json
import mimetypes
import os
import random
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pg_primary_remote import pg_primary

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("LEVEL_READ_PRODUCTION_CONFIG", Path.home() / ".codex" / "level-read-production" / "config.json"))
OUTPUT_ROOT = Path(os.environ.get("LEVEL_READ_PRODUCTION_OUTPUT_ROOT", Path.home() / "Documents" / "Level Read Production"))
COLLECTION = "enil_news"
TITLE_TRANSLATION_COLLECTION = "enli_news_title_translation"
NEWS_TRANSLATION_COLLECTION = "enli_news_translation"
TITLE_TRANSLATION_PROVIDER = "codex"
TITLE_TRANSLATION_VERSION = "v1"
TITLE_TRANSLATION_LANGUAGES = ("zh-CN", "zh-TW", "ja", "ko", "es", "pt-BR")


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


def paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text.strip()) if paragraph.strip()]


def contains_exact_word(content: str, word: str) -> bool:
    return bool(re.search(rf"(?i)(?<![a-z]){re.escape(word)}(?![a-z])", content))


def contains_answer_evidence(content: str, answer: str) -> bool:
    """Check that a review's quoted evidence occurs in the current reading."""
    normalized_content = re.sub(r"\s+", " ", content.casefold()).strip()
    normalized_answer = re.sub(r"\s+", " ", answer.casefold()).strip()
    return bool(normalized_answer) and normalized_answer in normalized_content


def editorial_fingerprint(news: dict[str, Any]) -> str:
    """Bind an editorial review to the wording, allowing option-position shuffles."""
    basis = {
        "title": news.get("title"),
        "summary": news.get("summary"),
        "levels": [
            {
                "level": level.get("level"),
                "content": level.get("content"),
                "quiz": [
                    {"question": quiz.get("question"), "options": sorted(quiz.get("options", []))}
                    for quiz in level.get("quiz", [])
                ],
            }
            for level in news.get("levels", [])
        ],
    }
    return hashlib.sha256(compact_json(basis).encode("utf-8")).hexdigest()


def blind_review_sheet(news: dict[str, Any]) -> dict[str, Any]:
    """Show all quiz wording without exposing the draft answer key."""
    return {
        "fingerprint": editorial_fingerprint(news),
        "title": news["title"],
        "summary": news["summary"],
        "levels": [
            {
                "level": level["level"],
                "content": level["content"],
                "quiz": [
                    {"id": f"L{level['level']}Q{index}", "question": quiz["question"], "options": quiz["options"]}
                    for index, quiz in enumerate(level["quiz"], 1)
                ],
            }
            for level in news["levels"]
        ],
    }


def validate_editorial_review(news: dict[str, Any], review: dict[str, Any]) -> list[str]:
    """Check review completeness and agreement with the key; semantic judgment is editorial."""
    errors: list[str] = []
    if not isinstance(review, dict) or review.get("fingerprint") != editorial_fingerprint(news):
        return ["editorial review fingerprint does not match the current article"]
    headline = review.get("headline")
    if not isinstance(headline, dict) or any(headline.get(key) is not True for key in ("simple", "clear", "faithful")) or not isinstance(headline.get("rationale"), str) or not headline["rationale"].strip():
        errors.append("headline needs a reasoned simple, clear, and faithful approval")
    reviewed = review.get("quizzes")
    expected = [(f"L{level['level']}Q{index}", level, quiz) for level in news["levels"] for index, quiz in enumerate(level["quiz"], 1)]
    if not isinstance(reviewed, list) or len(reviewed) != len(expected):
        return errors + [f"editorial review needs {len(expected)} quiz decisions"]
    for item, (identifier, level, quiz) in zip(reviewed, expected):
        if not isinstance(item, dict) or item.get("id") != identifier:
            errors.append(f"{identifier}: review id/order mismatch")
            continue
        selected = item.get("selectedOption")
        if selected not in quiz["options"] or selected != quiz["options"][int(quiz["answer"]) - 1]:
            errors.append(f"{identifier}: blind choice disagrees with the keyed answer")
        evidence = item.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip() or not contains_answer_evidence(level["content"], evidence):
            errors.append(f"{identifier}: evidence must quote text from this level")
        if not isinstance(item.get("rationale"), str) or not item["rationale"].strip():
            errors.append(f"{identifier}: explain why this option answers the question")
        rejected = item.get("rejectedOptions")
        other_options = [option for option in quiz["options"] if option != selected]
        if not isinstance(rejected, list) or len(rejected) != 2 or {entry.get("option") for entry in rejected if isinstance(entry, dict)} != set(other_options) or any(not isinstance(entry, dict) or not isinstance(entry.get("reason"), str) or not entry["reason"].strip() for entry in rejected):
            errors.append(f"{identifier}: explain why each other option is wrong")
        if any(item.get(key) is not True for key in ("answerFitsQuestion", "onlyOneCorrect", "optionsStandAlone")):
            errors.append(f"{identifier}: answer fit, uniqueness, and standalone options must be approved")
    return errors


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
    title = news.get("title")
    summary = news.get("summary")
    if not isinstance(title, str) or not title.strip():
        errors.append("title is required")
    elif word_count(title) > 10:
        errors.append("title must be at most 10 words")
    if not isinstance(summary, str) or not summary.strip():
        errors.append("summary is required")
    elif not 2 <= word_count(summary) <= 15:
        errors.append("summary must be 2-15 words")
    elif isinstance(title, str) and summary.casefold().strip(" .!?") == title.casefold().strip(" .!?"):
        errors.append("summary must add information beyond the title")
    if not isinstance(levels, list) or [item.get("level") for item in levels if isinstance(item, dict)] != [1, 2, 3]:
        errors.append("levels must be exactly 1, 2, 3 in order")
        return errors, warnings
    expected = {
        1: {"vocabulary": 3, "quiz": 1, "minimum": 100, "maximum": 120, "paragraph_minimum": 2, "paragraph_maximum": 3},
        2: {"vocabulary": 4, "quiz": 2, "minimum": 150, "maximum": 180, "paragraph_minimum": 3, "paragraph_maximum": 4},
        3: {"vocabulary": 5, "quiz": 3, "minimum": 180, "maximum": 220, "paragraph_minimum": 3, "paragraph_maximum": 4},
    }
    all_answers: list[str] = []
    for level in levels:
        number = level["level"]
        requirements = expected[number]
        content = level.get("content")
        if not isinstance(content, str) or not content.strip():
            errors.append(f"level {number} content is required")
            continue
        count = word_count(content)
        if count < requirements["minimum"] or count > requirements["maximum"]:
            errors.append(f"level {number} word count {count} must be {requirements['minimum']}-{requirements['maximum']}")
        paragraph_count = len(paragraphs(content))
        if paragraph_count < requirements["paragraph_minimum"] or paragraph_count > requirements["paragraph_maximum"]:
            errors.append(f"level {number} must contain {requirements['paragraph_minimum']}-{requirements['paragraph_maximum']} paragraphs separated by blank lines")
        vocabulary = level.get("vocabulary") or []
        quizzes = level.get("quiz") or []
        if len(vocabulary) != requirements["vocabulary"]:
            errors.append(f"level {number} must have {requirements['vocabulary']} vocabulary items")
        if len(quizzes) != requirements["quiz"]:
            errors.append(f"level {number} must have {requirements['quiz']} quizzes")
        for item in vocabulary:
            word = item.get("word") if isinstance(item, dict) else None
            if not isinstance(word, str) or not word.strip() or re.search(r"\s", word):
                errors.append(f"level {number} vocabulary must be a single word")
            elif not contains_exact_word(content, word):
                errors.append(f"level {number} vocabulary word {word!r} must appear in its content")
        for quiz in quizzes:
            options = quiz.get("options") if isinstance(quiz, dict) else None
            answer = quiz.get("answer") if isinstance(quiz, dict) else None
            if not isinstance(quiz, dict) or not isinstance(quiz.get("question"), str) or not quiz["question"].strip():
                errors.append(f"level {number} quiz question is required")
            if not isinstance(options, list) or len(options) != 3 or any(not isinstance(item, str) or not item.strip() for item in options) or len({item.strip().casefold() for item in options if isinstance(item, str)}) != 3:
                errors.append(f"level {number} quiz must have three nonempty, distinct text options")
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
    candidates = [
        positions
        for positions in itertools.product(("1", "2", "3"), repeat=6)
        if all(1 <= positions.count(answer) <= 3 for answer in ("1", "2", "3"))
        and not any(positions[index] == positions[index - 1] == positions[index - 2] for index in range(2, 6))
    ]
    targets = list(random.SystemRandom().choice(candidates))
    for quiz, target in zip(quizzes, targets):
        answer_index = int(quiz["answer"]) - 1
        options = quiz["options"]
        if answer_index not in (0, 1, 2) or len(options) != 3:
            raise RuntimeError("Cannot normalize a malformed quiz")
        correct = options[answer_index]
        distractors = [option for index, option in enumerate(options) if index != answer_index]
        random.SystemRandom().shuffle(distractors)
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
    # COS expects the hexadecimal SignKey text as the key for the second HMAC.
    signature = hmac.new(sign_key.encode(), string_to_sign.encode(), hashlib.sha1).hexdigest()
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


def validate_title_translations(value: Any, package: dict[str, Any]) -> list[dict[str, str]]:
    """Validate the Codex-authored title translation artifact before any CMS write."""
    if not isinstance(value, dict):
        raise RuntimeError("Title translations must be a JSON object")
    if value.get("titleid") != package.get("titleid"):
        raise RuntimeError("Title translations titleid must match the news package")
    if value.get("sourceTitle") != package.get("title"):
        raise RuntimeError("Title translations sourceTitle must exactly match the news package title")
    translations = value.get("translations")
    if not isinstance(translations, list) or len(translations) != len(TITLE_TRANSLATION_LANGUAGES):
        raise RuntimeError("Title translations must contain exactly six target languages")
    normalized: list[dict[str, str]] = []
    languages: list[str] = []
    for item in translations:
        if not isinstance(item, dict):
            raise RuntimeError("Each title translation must be an object")
        language = item.get("languageCode")
        title = item.get("title")
        if not isinstance(language, str) or not isinstance(title, str) or not title.strip():
            raise RuntimeError("Each title translation needs a languageCode and non-empty title")
        languages.append(language)
        normalized.append({"languageCode": language, "title": title.strip()})
    if set(languages) != set(TITLE_TRANSLATION_LANGUAGES) or len(set(languages)) != len(TITLE_TRANSLATION_LANGUAGES):
        expected = ", ".join(TITLE_TRANSLATION_LANGUAGES)
        raise RuntimeError(f"Title translations must contain each required language exactly once: {expected}")
    return normalized


def translation_source_fingerprint(package: dict[str, Any]) -> str:
    source = {
        "title": package.get("title"),
        "summary": package.get("summary"),
        "levels": [
            {"level": level.get("level"), "title": level.get("title", ""), "content": level.get("content")}
            for level in package.get("levels", [])
        ],
    }
    return hashlib.sha256(compact_json(source).encode("utf-8")).hexdigest()

def validate_body_translations(value: Any, package: dict[str, Any], titles: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Check all six translations against the final source package before CMS writes."""
    if not isinstance(value, dict) or value.get("titleid") != package.get("titleid"):
        raise RuntimeError("Body translations titleid must match the news package")
    if value.get("sourceFingerprint") != translation_source_fingerprint(package):
        raise RuntimeError("Body translations sourceFingerprint must match the final news package")
    items = value.get("translations")
    if not isinstance(items, list) or len(items) != len(TITLE_TRANSLATION_LANGUAGES):
        raise RuntimeError("Body translations must contain exactly six target languages")
    title_by_language = {item["languageCode"]: item["title"] for item in titles}
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError("Each body translation must be an object")
        language = item.get("languageCode")
        if not isinstance(language, str) or language not in TITLE_TRANSLATION_LANGUAGES or language in seen:
            raise RuntimeError("Body translations need each required language exactly once")
        seen.add(language)
        if item.get("title") != title_by_language[language]:
            raise RuntimeError(f"{language}: body title must match the reviewed title translation")
        if not isinstance(item.get("summary"), str) or not item["summary"].strip():
            raise RuntimeError(f"{language}: translated summary is required")
        levels = item.get("levels")
        if not isinstance(levels, list) or len(levels) != 3:
            raise RuntimeError(f"{language}: three translated levels are required")
        normalized_levels: list[dict[str, Any]] = []
        for source_level, translated_level in zip(package["levels"], levels):
            if not isinstance(translated_level, dict) or translated_level.get("level") != source_level["level"]:
                raise RuntimeError(f"{language}: translated level order must be 1, 2, 3")
            content = translated_level.get("content")
            if not isinstance(content, str) or not content.strip() or len(paragraphs(content)) != len(paragraphs(source_level["content"])):
                raise RuntimeError(f"{language}: level {source_level['level']} must preserve the source paragraph count")
            title = translated_level.get("title", "")
            if not isinstance(title, str) or (source_level.get("title") and not title.strip()):
                raise RuntimeError(f"{language}: level {source_level['level']} title is invalid")
            normalized_levels.append({
                "level": source_level["level"], "title": title.strip(), "content": content.strip(),
                "vocabulary": [{"explanation": vocabulary["explanation"]} for vocabulary in source_level.get("vocabulary", [])],
            })
        result.append({"languageCode": language, "title": item["title"], "summary": item["summary"].strip(), "levels": normalized_levels})
    return result


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", "utf-8")


def read_production_state(output: Path) -> dict[str, Any]:
    state_path = output / "production-state.json"
    if not state_path.is_file():
        return {}
    try:
        state = json.loads(state_path.read_text("utf-8"))
    except json.JSONDecodeError:
        return {}
    return state if isinstance(state, dict) else {}


def is_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


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
    required = {"ai": ("base_url", "api_key"), "cos": ("secret_id", "secret_key", "bucket", "region")}
    report = {section: {"configured": not [key for key in keys if not isinstance(config.get(section, {}).get(key), str) or not config[section][key].strip() or config[section][key] == "replace-me"], "missing": [key for key in keys if not isinstance(config.get(section, {}).get(key), str) or not config[section][key].strip() or config[section][key] == "replace-me"]} for section, keys in required.items()}
    print(json.dumps({"success": all(item["configured"] for item in report.values()), "config_path": str(CONFIG_PATH), "capabilities": report}, ensure_ascii=False, indent=2))
    return 0


def cmd_review_sheet(args: argparse.Namespace) -> int:
    news = json.loads(Path(args.input).read_text("utf-8"))
    sheet = blind_review_sheet(news)
    write_json(Path(args.output), sheet)
    print(json.dumps({"success": True, "output": args.output, "quizzes": sum(len(level["quiz"]) for level in sheet["levels"])}, ensure_ascii=False))
    return 0


def cmd_review_check(args: argparse.Namespace) -> int:
    news = json.loads(Path(args.input).read_text("utf-8"))
    review = json.loads(Path(args.editorial_review).read_text("utf-8"))
    errors, _ = validate_levels(news)
    errors.extend(validate_editorial_review(news, review))
    if errors:
        raise RuntimeError("Editorial review failed: " + "; ".join(errors))
    print(json.dumps({"success": True, "quizzes": len(review["quizzes"]), "fingerprint": review["fingerprint"]}, ensure_ascii=False))
    return 0


def cmd_translation_fingerprint(args: argparse.Namespace) -> int:
    package = json.loads(Path(args.input).read_text("utf-8"))
    print(json.dumps({"titleid": package.get("titleid"), "sourceFingerprint": translation_source_fingerprint(package)}, ensure_ascii=False))
    return 0


def cmd_produce(args: argparse.Namespace) -> int:
    levels = json.loads(Path(args.levels).read_text("utf-8"))
    levels = normalize_quizzes(levels)
    errors, warnings = validate_levels(levels)
    review = json.loads(Path(args.editorial_review).read_text("utf-8"))
    errors.extend(validate_editorial_review(levels, review))
    if errors:
        raise RuntimeError("Level package failed validation: " + "; ".join(errors))
    config = load_config()
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
    write_json(output / "editorial-review.json", review)
    archived_cover = output / f"cover{cover.suffix.lower() or '.png'}"
    if cover.resolve() != archived_cover.resolve():
        shutil.copy2(cover, archived_cover)
    resume = getattr(args, "resume", False)
    previous_state = read_production_state(output) if resume else {}
    previous_cover = previous_state.get("cover") if is_url(previous_state.get("cover")) else None
    previous_audios = previous_state.get("audios") if isinstance(previous_state.get("audios"), dict) else {}
    write_production_state(output, "local_assets_ready", titleid)
    local_audios: dict[str, Path] = {}
    for level in levels["levels"]:
        filename = f"{titleid}-level-{level['level']}.mp3"
        local_audio = output / filename
        if resume and local_audio.is_file() and local_audio.stat().st_size > 0:
            local_audios[str(level["level"])] = local_audio
            continue
        try:
            local_audio.write_bytes(generate_audio(config, level["content"]))
        except Exception as error:
            message = f"Audio generation failed at level {level['level']} before any upload: {error}"
            write_production_state(output, "audio_generation_failed", titleid, error=message)
            raise RuntimeError(message) from error
        local_audios[str(level["level"])] = local_audio
    write_production_state(output, "audio_generated", titleid)
    if previous_cover:
        cover_url = previous_cover
    else:
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
        if resume and is_url(previous_audios.get(number)):
            audios[number] = previous_audios[number]
            continue
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
    write_json(output / "qa.json", {"valid": True, "editorialReview": True, "warnings": warnings})
    write_production_state(output, "complete", titleid, cover_url=cover_url, audios=audios)
    print(json.dumps({"success": True, "output": str(output), "titleid": titleid, "public": False, "qa": "needs review" if warnings else "ready for CMS review"}, ensure_ascii=False, indent=2))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    if not args.confirm_unpublished_ingest:
        raise RuntimeError("ingest requires --confirm-unpublished-ingest")
    package = json.loads(Path(args.input).read_text("utf-8"))
    if package.get("public") is not False:
        raise RuntimeError("Refusing to ingest a package unless public is false")
    errors, warnings = validate_levels(package)
    review = json.loads(Path(args.editorial_review).read_text("utf-8"))
    errors.extend(validate_editorial_review(package, review))
    if errors:
        raise RuntimeError("News package failed validation: " + "; ".join(errors))
    if not isinstance(package.get("cover"), str) or not package["cover"].startswith(("http://", "https://")):
        raise RuntimeError("News package needs an uploaded cover URL")
    if any(not item.get("audio", "").startswith(("http://", "https://")) for item in package["levels"]):
        raise RuntimeError("News package needs uploaded audio URLs for all levels")
    translations_path = Path(args.title_translations)
    try:
        title_translations = validate_title_translations(json.loads(translations_path.read_text("utf-8")), package)
    except FileNotFoundError as error:
        raise RuntimeError(f"Title translations file not found: {translations_path}") from error
    body_path = Path(args.body_translations)
    try:
        body_translations = validate_body_translations(json.loads(body_path.read_text("utf-8")), package, title_translations)
    except FileNotFoundError as error:
        raise RuntimeError(f"Body translations file not found: {body_path}") from error
    receipt_path = Path(args.input).resolve().parent / "ingest-result.json"
    config = load_config()
    request = {"action":"ingest", "package":package, "titleTranslations":title_translations, "bodyTranslations":body_translations}
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text("utf-8"))
        if previous.get("backend") != "postgresql":
            raise RuntimeError("Legacy ingest receipt requires explicit review; never replay a CloudBase ingest")
        if previous.get("success") is True:
            raise RuntimeError("This package has already been ingested")
    # Persist intent before an ambiguous network/COMMIT failure. Identical retries
    # use deterministic IDs and the PG digest; a changed package is rejected.
    receipt = {"success":False, "backend":"postgresql", "title":package["title"], "titleid":package["titleid"], "public":False}
    write_json(receipt_path, receipt)
    result = pg_primary(config, request)
    receipt.update(result)
    receipt["success"] = result.get("ok") is True
    write_json(receipt_path, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["success"] else 1


def cmd_sync_ingest(args: argparse.Namespace) -> int:
    raise RuntimeError("CloudBase synchronization is retired; retry the same PG ingest command for an incomplete PG receipt")


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal Level Read publisher")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    review_sheet = commands.add_parser("review-sheet", help="Create a quiz worksheet without answer keys")
    review_sheet.add_argument("--input", required=True)
    review_sheet.add_argument("--output", required=True)
    review_check = commands.add_parser("review-check", help="Check a completed review against the final article")
    review_check.add_argument("--input", required=True)
    review_check.add_argument("--editorial-review", required=True)
    translation_fingerprint = commands.add_parser("translation-fingerprint", help="Bind body translations to the final news package")
    translation_fingerprint.add_argument("--input", required=True)
    produce = commands.add_parser("produce")
    produce.add_argument("--levels", required=True)
    produce.add_argument("--editorial-review", required=True)
    produce.add_argument("--cover", required=True)
    produce.add_argument("--original-url", required=True)
    produce.add_argument("--date", required=True)
    produce.add_argument("--output", help="Override the default per-story directory for controlled testing")
    produce.add_argument("--titleid")
    produce.add_argument("--resume", action="store_true", help="Reuse local audio and successfully uploaded assets recorded in the story directory")
    ingest = commands.add_parser("ingest")
    ingest.add_argument("--input", required=True)
    ingest.add_argument("--editorial-review", required=True)
    ingest.add_argument("--title-translations", required=True, help="Codex-generated title-translations.json for this package")
    ingest.add_argument("--body-translations", required=True, help="Codex-generated body-translations.json for this package")
    ingest.add_argument("--confirm-unpublished-ingest", action="store_true")
    sync_ingest = commands.add_parser("sync-ingest", help="Retry PG sync from an existing ingest receipt without creating CMS records")
    sync_ingest.add_argument("--receipt", required=True)
    args = parser.parse_args()
    if args.command == "sync-ingest": return cmd_sync_ingest(args)
    if args.command == "doctor": return cmd_doctor(args)
    if args.command == "review-sheet": return cmd_review_sheet(args)
    if args.command == "review-check": return cmd_review_check(args)
    if args.command == "translation-fingerprint": return cmd_translation_fingerprint(args)
    if args.command == "produce": return cmd_produce(args)
    return cmd_ingest(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"success": False, "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)
