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
    vocabulary = [{"word": f"word{number}{index}", "explanation": "A useful word"} for index in range(number + 2)]
    return {
        "level": number,
        "content": (" ".join(item["word"] for item in vocabulary) + " ") * 50,
        "vocabulary": vocabulary,
        "quiz": [
            {"question": f"Question {number}-{index}", "options": [f"correct-{number}-{index}", f"wrong-a-{number}-{index}", f"wrong-b-{number}-{index}"], "answer": "1"}
            for index in range(quiz_count)
        ],
    }


class PublisherTests(unittest.TestCase):
    def test_normalizes_answers_without_changing_correct_text(self):
        news = {"title": "A Useful Story", "summary": "A short learner summary.", "levels": [make_level(1, 1), make_level(2, 2), make_level(3, 3)]}
        normalized = publisher.normalize_quizzes(news)
        answers = [quiz["answer"] for level in normalized["levels"] for quiz in level["quiz"]]
        self.assertEqual(set(answers), {"1", "2", "3"})
        self.assertFalse(any(answers[index] == answers[index - 1] == answers[index - 2] for index in range(2, 6)))
        for level in normalized["levels"]:
            for quiz in level["quiz"]:
                self.assertTrue(quiz["options"][int(quiz["answer"]) - 1].startswith("correct-"))
        self.assertEqual(publisher.validate_levels(normalized)[0], [])

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

    def test_cloudbase_admin_url_matches_sdk_database_route(self):
        url = publisher.cloudbase_admin_url("level-read-123", "ap-guangzhou", "seq-42")
        self.assertEqual(
            url,
            "https://level-read-123.ap-guangzhou.tcb-api.tencentcloudapi.com/admin?env=level-read-123&seqId=seq-42",
        )

    def test_cloudbase_signature_includes_admin_path(self):
        auth = publisher.cloudbase_authorization(
            "id",
            "key",
            "post",
            "https://level-read-123.ap-guangzhou.tcb-api.tencentcloudapi.com/admin?env=level-read-123&seqId=seq-42",
            {
                "Content-Type": "application/json",
                "Host": "level-read-123.ap-guangzhou.tcb-api.tencentcloudapi.com",
                "X-TCB-Region": "ap-guangzhou",
            },
            {"action": "database.insertDocument", "collectionName": "enil_news", "envName": "level-read-123"},
            1_700_000_000,
        )
        self.assertIn("Credential=id/2023-11-14/tcb/tc3_request", auth)
        self.assertIn("SignedParams=action;collectionname;envname", auth)
        self.assertNotEqual(
            auth,
            publisher.cloudbase_authorization(
                "id", "key", "post", "https://level-read-123.ap-guangzhou.tcb-api.tencentcloudapi.com/?env=level-read-123&seqId=seq-42",
                {"Content-Type": "application/json", "Host": "level-read-123.ap-guangzhou.tcb-api.tencentcloudapi.com", "X-TCB-Region": "ap-guangzhou"},
                {"action": "database.insertDocument", "collectionName": "enil_news", "envName": "level-read-123"},
                1_700_000_000,
            ),
        )

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
        news = {"title": "A Useful Story", "summary": "A short learner summary.", "levels": [make_level(1, 1), make_level(2, 2), make_level(3, 3)]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            levels_path = root / "levels.json"
            cover_path = root / "generated-cover.png"
            levels_path.write_text(json.dumps(news), "utf-8")
            cover_path.write_bytes(b"png")
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
            publisher.cmd_produce(SimpleNamespace(levels=str(levels_path), cover=str(cover_path), original_url="https://example.test/source", date="2026-08-23", output=None, titleid=None))
            output = root / "archive" / "2026-08-23-a-useful-story"
            self.assertEqual((output / "cover.png").read_bytes(), b"png")
            self.assertEqual((output / "a-useful-story-level-1.mp3").read_bytes(), b"audio")
            self.assertTrue((output / "news-package.json").is_file())
            self.assertTrue((output / "qa.json").is_file())
            self.assertEqual(json.loads((output / "production-state.json").read_text("utf-8"))["stage"], "complete")

    def test_cover_upload_failure_is_recorded_after_local_audio_generation(self):
        news = {"title": "A Useful Story", "summary": "A short learner summary.", "levels": [make_level(1, 1), make_level(2, 2), make_level(3, 3)]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            levels_path = root / "levels.json"
            cover_path = root / "generated-cover.png"
            levels_path.write_text(json.dumps(news), "utf-8")
            cover_path.write_bytes(b"png")
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
            args = SimpleNamespace(levels=str(levels_path), cover=str(cover_path), original_url="https://example.test/source", date="2026-08-23", output=None, titleid=None)
            with self.assertRaisesRegex(RuntimeError, "Cover upload failed before any audio upload"):
                publisher.cmd_produce(args)
            output = root / "archive" / "2026-08-23-a-useful-story"
            self.assertTrue((output / "a-useful-story-level-3.mp3").is_file())
            state = json.loads((output / "production-state.json").read_text("utf-8"))
            self.assertEqual(state["stage"], "cover_upload_failed")
            self.assertIn("Broken pipe", state["error"])

    def test_resume_reuses_local_audio_and_uploaded_assets(self):
        news = {"title": "A Useful Story", "summary": "A short learner summary.", "levels": [make_level(1, 1), make_level(2, 2), make_level(3, 3)]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            levels_path = root / "levels.json"
            cover_path = root / "generated-cover.png"
            levels_path.write_text(json.dumps(news), "utf-8")
            cover_path.write_bytes(b"png")
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
            args = SimpleNamespace(levels=str(levels_path), cover=str(cover_path), original_url="https://example.test/source", date="2026-08-23", output=None, titleid=None, resume=False)
            publisher.cmd_produce(args)
            publisher.generate_audio = lambda *_args: (_ for _ in ()).throw(AssertionError("audio must be reused"))
            publisher.cos_upload = lambda *_args: (_ for _ in ()).throw(AssertionError("uploads must be reused"))
            args.resume = True
            self.assertEqual(publisher.cmd_produce(args), 0)


if __name__ == "__main__":
    unittest.main()
