import importlib.util
import unittest
from pathlib import Path

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

    def test_slugify_rejects_non_ascii_only_title(self):
        with self.assertRaises(RuntimeError):
            publisher.slugify("中文标题")


if __name__ == "__main__":
    unittest.main()

