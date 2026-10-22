import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location("publisher", Path(__file__).parent / "scripts" / "publisher.py")
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


def make_level(number, quiz_count):
    vocabulary = [{"word": f"word{chr(97 + number)}{chr(97 + index)}", "explanation": "A useful word"} for index in range(number + 2)]
    quiz = [
        {"question": f"Question {number}-{index}", "options": [f"answer{number}{index}", f"wrong{number}{index}a", f"wrong{number}{index}b"], "answer": "1"}
        for index in range(quiz_count)
    ]
    target_words = {1: 110, 2: 160, 3: 200}[number]
    words = [item["word"] for item in vocabulary] + [item["options"][0] for item in quiz]
    words.extend(["simple"] * (target_words - len(words)))
    paragraph_count = {1: 2, 2: 3, 3: 3}[number]
    size, extra = divmod(len(words), paragraph_count)
    chunks, start = [], 0
    for index in range(paragraph_count):
        end = start + size + (1 if index < extra else 0)
        chunks.append(" ".join(words[start:end]))
        start = end
    return {"level": number, "content": "\n\n".join(chunks), "vocabulary": vocabulary, "quiz": quiz}


def make_news():
    return {
        "title": "A Useful Story",
        "summary": "A short learner summary explains the key event clearly.",
        "levels": [make_level(1, 1), make_level(2, 2), make_level(3, 3)],
    }


def make_review(news):
    return {
        "fingerprint": publisher.editorial_fingerprint(news),
        "headline": {"simple": True, "clear": True, "faithful": True, "rationale": "Names the event in common words."},
        "quizzes": [
            {
                "id": f"L{level['level']}Q{index}",
                "selectedOption": quiz["options"][int(quiz["answer"]) - 1],
                "evidence": quiz["options"][int(quiz["answer"]) - 1],
                "rationale": "This phrase in the reading answers the question.",
                "rejectedOptions": [
                    {"option": option, "reason": "The reading does not support this alternative."}
                    for option in quiz["options"] if option != quiz["options"][int(quiz["answer"]) - 1]
                ],
                "answerFitsQuestion": True,
                "onlyOneCorrect": True,
                "optionsStandAlone": True,
            }
            for level in news["levels"] for index, quiz in enumerate(level["quiz"], 1)
        ],
    }


def write_review(root, news):
    path = root / "editorial-review.json"
    path.write_text(json.dumps(make_review(news)), "utf-8")
    return path


class PublisherTests(unittest.TestCase):
    def title_translations(self):
        return {
            "titleid": "a-useful-story",
            "sourceTitle": "A Useful Story",
            "translations": [
                {"languageCode": "zh-CN", "title": "一个有用的故事"},
                {"languageCode": "zh-TW", "title": "一個有用的故事"},
                {"languageCode": "ja", "title": "役立つ物語"},
                {"languageCode": "ko", "title": "유용한 이야기"},
                {"languageCode": "es", "title": "Una historia útil"},
                {"languageCode": "pt-BR", "title": "Uma história útil"},
            ],
        }

    def package_for_ingest(self):
        package = publisher.normalize_quizzes(make_news())
        package.update({
            "titleid": "a-useful-story",
            "cover": "https://example.test/cover.png",
            "public": False,
        })
        for level in package["levels"]:
            level["audio"] = f"https://example.test/{level['level']}.mp3"
        return package

    def body_translations(self, package):
        return {
            "titleid": package["titleid"],
            "sourceFingerprint": publisher.translation_source_fingerprint(package),
            "translations": [
                {"languageCode": item["languageCode"], "title": item["title"],
                 "summary": "Translated summary",
                 "levels": [{"level": level["level"], "title": "", "content": "\n\n".join(["Translated paragraph"] * len(publisher.paragraphs(level["content"]))) } for level in package["levels"]]}
                for item in self.title_translations()["translations"]
            ],
        }

    def test_title_translations_require_exact_api_languages_and_matching_source(self):
        translations = self.title_translations()
        package = self.package_for_ingest()
        validated = publisher.validate_title_translations(translations, package)
        self.assertEqual([item["languageCode"] for item in validated], list(publisher.TITLE_TRANSLATION_LANGUAGES))
        translations["translations"][5]["languageCode"] = "fr"
        with self.assertRaisesRegex(RuntimeError, "each required language exactly once"):
            publisher.validate_title_translations(translations, package)
        translations = self.title_translations()
        translations["sourceTitle"] = "Different headline"
        with self.assertRaisesRegex(RuntimeError, "sourceTitle"):
            publisher.validate_title_translations(translations, package)

    def test_ingest_writes_news_then_six_ready_title_translations(self):
        package = self.package_for_ingest()
        translations = self.title_translations()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_path = root / "news-package.json"
            translations_path = root / "title-translations.json"
            body_path = root / "body-translations.json"
            package_path.write_text(json.dumps(package), "utf-8")
            translations_path.write_text(json.dumps(translations), "utf-8")
            body_path.write_text(json.dumps(self.body_translations(package)), "utf-8")
            review_path = write_review(root, package)
            original_config, original_pg = publisher.load_config, publisher.pg_primary
            self.addCleanup(setattr,publisher,"load_config",original_config)
            self.addCleanup(setattr,publisher,"pg_primary",original_pg)
            publisher.load_config=lambda: {}
            captured={}
            def ingest(_config,request):
                captured.update(request)
                return {"ok":True,"status":"ingested","id":"news-123","total":13,"titleTranslationIds":[str(i) for i in range(6)],"bodyTranslationIds":[str(i) for i in range(6)]}
            publisher.pg_primary=ingest
            result = publisher.cmd_ingest(SimpleNamespace(
                input=str(package_path),
                title_translations=str(translations_path),
                body_translations=str(body_path),
                editorial_review=str(review_path),
                confirm_unpublished_ingest=True,
            ))
            self.assertEqual(result, 0)
            self.assertEqual(captured["package"]["titleid"], package["titleid"])
            self.assertEqual([item["languageCode"] for item in captured["titleTranslations"]], list(publisher.TITLE_TRANSLATION_LANGUAGES))

    def test_ingest_does_not_write_news_when_title_translations_are_invalid(self):
        package = self.package_for_ingest()
        translations = self.title_translations()
        translations["translations"].pop()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_path = root / "news-package.json"
            translations_path = root / "title-translations.json"
            package_path.write_text(json.dumps(package), "utf-8")
            translations_path.write_text(json.dumps(translations), "utf-8")
            review_path = write_review(root, package)
            original_config = publisher.load_config
            original_insert = publisher.pg_primary
            self.addCleanup(setattr, publisher, "load_config", original_config)
            self.addCleanup(setattr, publisher, "pg_primary", original_insert)
            publisher.load_config = lambda: {}
            publisher.pg_primary = lambda *_args: (_ for _ in ()).throw(AssertionError("news must not be written"))
            with self.assertRaisesRegex(RuntimeError, "exactly six target languages"):
                publisher.cmd_ingest(SimpleNamespace(
                    input=str(package_path),
                    title_translations=str(translations_path),
                    body_translations=str(root / "body-translations.json"),
                    editorial_review=str(review_path),
                    confirm_unpublished_ingest=True,
                ))


    def test_normalizes_answers_without_changing_correct_text(self):
        news = make_news()
        normalized = publisher.normalize_quizzes(news)
        answers = [quiz["answer"] for level in normalized["levels"] for quiz in level["quiz"]]
        self.assertEqual(set(answers), {"1", "2", "3"})
        self.assertFalse(any(answers[index] == answers[index - 1] == answers[index - 2] for index in range(2, 6)))
        for level in normalized["levels"]:
            for quiz in level["quiz"]:
                self.assertTrue(quiz["options"][int(quiz["answer"]) - 1].startswith("answer"))
        self.assertEqual(publisher.validate_levels(normalized)[0], [])

    def test_validator_requires_short_metadata_paragraphs_and_exact_word_counts(self):
        news = make_news()
        news["title"] = "This Title Is Far Too Long For A Single News Card Today"
        news["summary"] = "The same title is repeated without adding anything new at all."
        news["levels"][0]["content"] = "answer10"
        errors, _ = publisher.validate_levels(news)
        self.assertTrue(any("title must be at most 10 words" in error for error in errors))
        self.assertTrue(any("level 1 word count" in error for error in errors))
        self.assertTrue(any("level 1 must contain 2-3 paragraphs" in error for error in errors))

    def test_validator_allows_paraphrased_quiz_answer(self):
        news = make_news()
        news["levels"][1]["quiz"][0]["options"][0] = "missing evidence"
        errors, _ = publisher.validate_levels(publisher.normalize_quizzes(news))
        self.assertEqual(errors, [])

    def test_body_translations_match_source_and_paragraphs(self):
        package = self.package_for_ingest()
        body = self.body_translations(package)
        result = publisher.validate_body_translations(body, package, self.title_translations()["translations"])
        self.assertEqual(len(result), 6)
        self.assertEqual(len(result[0]["levels"][0]["vocabulary"]), 3)
        body["translations"][0]["levels"][0]["content"] = "One paragraph"
        with self.assertRaisesRegex(RuntimeError, "paragraph count"):
            publisher.validate_body_translations(body, package, self.title_translations()["translations"])

    def test_ingest_rejects_stale_body_translations_before_cms_write(self):
        package = self.package_for_ingest()
        body = self.body_translations(package)
        body["sourceFingerprint"] = "stale"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_path = root / "news-package.json"
            title_path = root / "title-translations.json"
            body_path = root / "body-translations.json"
            package_path.write_text(json.dumps(package), "utf-8")
            title_path.write_text(json.dumps(self.title_translations()), "utf-8")
            body_path.write_text(json.dumps(body), "utf-8")
            review_path = write_review(root, package)
            original_insert = publisher.pg_primary
            self.addCleanup(setattr, publisher, "pg_primary", original_insert)
            publisher.pg_primary = lambda *_args: (_ for _ in ()).throw(AssertionError("news must not be written"))
            with self.assertRaisesRegex(RuntimeError, "sourceFingerprint"):
                publisher.cmd_ingest(SimpleNamespace(
                    input=str(package_path), title_translations=str(title_path),
                    body_translations=str(body_path), editorial_review=str(review_path),
                    confirm_unpublished_ingest=True,
                ))


    def test_blind_sheet_hides_keys_and_review_catches_wrong_key(self):
        news = make_news()
        sheet = publisher.blind_review_sheet(news)
        self.assertNotIn('"answer"', json.dumps(sheet))
        review = make_review(news)
        self.assertEqual(publisher.validate_editorial_review(news, review), [])
        news["levels"][0]["quiz"][0]["answer"] = "2"
        self.assertIn("L1Q1: blind choice disagrees with the keyed answer", publisher.validate_editorial_review(news, review))

    def test_place_name_in_reading_does_not_make_it_answer_a_why_question(self):
        news = make_news()
        level = news["levels"][0]
        level["content"] = level["content"].replace("answer10", "Beijing because sunset came earlier", 1)
        level["quiz"][0] = {
            "question": "Why did the city turn on lights earlier?",
            "options": ["Beijing", "because sunset came earlier", "because summer began"],
            "answer": "1",
        }
        normalized = publisher.normalize_quizzes(news)
        self.assertEqual(publisher.validate_levels(normalized)[0], [])
        review = make_review(normalized)
        review["quizzes"][0]["selectedOption"] = "because sunset came earlier"
        review["quizzes"][0]["evidence"] = "because sunset came earlier"
        self.assertIn("L1Q1: blind choice disagrees with the keyed answer", publisher.validate_editorial_review(normalized, review))

    def test_review_requires_evidence_and_repeats_after_option_shuffle(self):
        news = make_news()
        review = make_review(news)
        review["quizzes"][1]["evidence"] = "A sentence that is absent"
        self.assertIn("L2Q1: evidence must quote text from this level", publisher.validate_editorial_review(news, review))
        review = make_review(news)
        normalized = publisher.normalize_quizzes(news)
        self.assertEqual(publisher.validate_editorial_review(normalized, review), [])
        normalized["title"] = "A Changed Story"
        self.assertIn("editorial review fingerprint does not match the current article", publisher.validate_editorial_review(normalized, review))

    def test_review_requires_reasons_for_both_wrong_options(self):
        news = make_news()
        review = make_review(news)
        review["quizzes"][0]["rejectedOptions"].pop()
        self.assertIn("L1Q1: explain why each other option is wrong", publisher.validate_editorial_review(news, review))

    def test_produce_rejects_wrong_key_before_audio_or_upload(self):
        news = make_news()
        review = make_review(news)
        news["levels"][0]["quiz"][0]["answer"] = "2"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            levels_path = root / "levels.json"
            review_path = root / "review.json"
            levels_path.write_text(json.dumps(news), "utf-8")
            review_path.write_text(json.dumps(review), "utf-8")
            original_config = publisher.load_config
            self.addCleanup(setattr, publisher, "load_config", original_config)
            publisher.load_config = lambda: (_ for _ in ()).throw(AssertionError("config must not be loaded"))
            with self.assertRaisesRegex(RuntimeError, "blind choice disagrees with the keyed answer"):
                publisher.cmd_produce(SimpleNamespace(levels=str(levels_path), editorial_review=str(review_path)))

    def test_cos_signature_has_required_fields(self):
        auth = publisher.cos_authorization("id", "key", "PUT", "bucket.cos.ap-guangzhou.myqcloud.com", "covers/a.png", 42)
        self.assertIn("q-sign-algorithm=sha1", auth)
        self.assertIn("q-ak=id", auth)
        self.assertIn("q-header-list=content-length;host", auth)

    def test_cos_signature_uses_hex_sign_key_text_for_second_hmac(self):
        original_time = publisher.time.time
        self.addCleanup(setattr, publisher.time, "time", original_time)
        publisher.time.time = lambda: 1_700_000_000
        host = "bucket.cos.ap-guangzhou.myqcloud.com"
        key = "covers/a.png"
        auth = publisher.cos_authorization("id", "key", "PUT", host, key, 42)
        key_time = "1700000000;1700001800"
        http_string = f"put\n/{key}\n\ncontent-length=42&host={host}\n"
        string_to_sign = f"sha1\n{key_time}\n{publisher.hashlib.sha1(http_string.encode()).hexdigest()}\n"
        sign_key = publisher.hmac.new(b"key", key_time.encode(), publisher.hashlib.sha1).hexdigest()
        expected_signature = publisher.hmac.new(sign_key.encode(), string_to_sign.encode(), publisher.hashlib.sha1).hexdigest()
        self.assertIn(f"q-signature={expected_signature}", auth)



    def test_slugify_rejects_non_ascii_only_title(self):
        with self.assertRaises(RuntimeError):
            publisher.slugify("中文标题")

    def test_story_output_directory_is_stable_and_grouped_by_date(self):
        original_root = publisher.OUTPUT_ROOT
        self.addCleanup(setattr, publisher, "OUTPUT_ROOT", original_root)
        publisher.OUTPUT_ROOT = Path("/tmp/level-read-output")
        result = publisher.story_output_directory(publisher.dt.date(2026, 8, 23), "useful-story")
        self.assertEqual(result, Path("/tmp/level-read-output/2026-08-23-useful-story"))

    def test_produce_archives_cover_and_outputs_in_one_story_directory(self):
        news = make_news()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            levels_path = root / "levels.json"
            cover_path = root / "generated-cover.png"
            levels_path.write_text(json.dumps(news), "utf-8")
            cover_path.write_bytes(b"png")
            review_path = write_review(root, news)
            original_root = publisher.OUTPUT_ROOT
            original_config = publisher.load_config
            original_upload = publisher.cos_upload
            original_audio = publisher.generate_audio
            self.addCleanup(setattr, publisher, "OUTPUT_ROOT", original_root)
            self.addCleanup(setattr, publisher, "load_config", original_config)
            self.addCleanup(setattr, publisher, "cos_upload", original_upload)
            self.addCleanup(setattr, publisher, "generate_audio", original_audio)
            publisher.OUTPUT_ROOT = root / "archive"
            publisher.load_config = lambda: {}
            publisher.cos_upload = lambda _config, local_path, _key: f"https://example.test/{local_path.name}"
            publisher.generate_audio = lambda _config, _text: b"audio"
            publisher.cmd_produce(SimpleNamespace(levels=str(levels_path), editorial_review=str(review_path), cover=str(cover_path), original_url="https://example.test/source", date="2026-08-23", output=None, titleid=None))
            output = root / "archive" / "2026-08-23-a-useful-story"
            self.assertEqual((output / "cover.png").read_bytes(), b"png")
            self.assertEqual((output / "a-useful-story-level-1.mp3").read_bytes(), b"audio")
            self.assertTrue((output / "news-package.json").is_file())
            self.assertTrue((output / "qa.json").is_file())
            self.assertEqual(publisher.validate_editorial_review(json.loads((output / "news-package.json").read_text("utf-8")), json.loads((output / "editorial-review.json").read_text("utf-8"))), [])
            self.assertEqual(json.loads((output / "production-state.json").read_text("utf-8"))["stage"], "complete")

    def test_cover_upload_failure_is_recorded_after_local_audio_generation(self):
        news = make_news()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            levels_path = root / "levels.json"
            cover_path = root / "generated-cover.png"
            levels_path.write_text(json.dumps(news), "utf-8")
            cover_path.write_bytes(b"png")
            review_path = write_review(root, news)
            original_root = publisher.OUTPUT_ROOT
            original_config = publisher.load_config
            original_upload = publisher.cos_upload
            original_audio = publisher.generate_audio
            self.addCleanup(setattr, publisher, "OUTPUT_ROOT", original_root)
            self.addCleanup(setattr, publisher, "load_config", original_config)
            self.addCleanup(setattr, publisher, "cos_upload", original_upload)
            self.addCleanup(setattr, publisher, "generate_audio", original_audio)
            publisher.OUTPUT_ROOT = root / "archive"
            publisher.load_config = lambda: {}
            publisher.generate_audio = lambda _config, _text: b"audio"
            publisher.cos_upload = lambda *_args: (_ for _ in ()).throw(BrokenPipeError("Broken pipe"))
            args = SimpleNamespace(levels=str(levels_path), editorial_review=str(review_path), cover=str(cover_path), original_url="https://example.test/source", date="2026-08-23", output=None, titleid=None)
            with self.assertRaisesRegex(RuntimeError, "Cover upload failed before any audio upload"):
                publisher.cmd_produce(args)
            output = root / "archive" / "2026-08-23-a-useful-story"
            self.assertTrue((output / "a-useful-story-level-3.mp3").is_file())
            state = json.loads((output / "production-state.json").read_text("utf-8"))
            self.assertEqual(state["stage"], "cover_upload_failed")
            self.assertIn("Broken pipe", state["error"])

    def test_resume_reuses_local_audio_and_uploaded_assets(self):
        news = make_news()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            levels_path = root / "levels.json"
            cover_path = root / "generated-cover.png"
            levels_path.write_text(json.dumps(news), "utf-8")
            cover_path.write_bytes(b"png")
            review_path = write_review(root, news)
            original_root = publisher.OUTPUT_ROOT
            original_config = publisher.load_config
            original_upload = publisher.cos_upload
            original_audio = publisher.generate_audio
            self.addCleanup(setattr, publisher, "OUTPUT_ROOT", original_root)
            self.addCleanup(setattr, publisher, "load_config", original_config)
            self.addCleanup(setattr, publisher, "cos_upload", original_upload)
            self.addCleanup(setattr, publisher, "generate_audio", original_audio)
            publisher.OUTPUT_ROOT = root / "archive"
            publisher.load_config = lambda: {}
            publisher.generate_audio = lambda _config, _text: b"audio"
            publisher.cos_upload = lambda _config, local_path, _key: f"https://example.test/{local_path.name}"
            args = SimpleNamespace(levels=str(levels_path), editorial_review=str(review_path), cover=str(cover_path), original_url="https://example.test/source", date="2026-08-23", output=None, titleid=None, resume=False)
            publisher.cmd_produce(args)
            publisher.generate_audio = lambda *_args: (_ for _ in ()).throw(AssertionError("audio must be reused"))
            publisher.cos_upload = lambda *_args: (_ for _ in ()).throw(AssertionError("uploads must be reused"))
            args.resume = True
            self.assertEqual(publisher.cmd_produce(args), 0)


if __name__ == "__main__":
    unittest.main()
