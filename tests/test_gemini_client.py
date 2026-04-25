import unittest

from services.gemini_client import _sanitize_threads_summary


class GeminiClientTests(unittest.TestCase):
    def test_sanitize_threads_summary_removes_social_tail(self):
        summary = _sanitize_threads_summary(
            "NVIDIA открыла доступ к 80 моделям через OpenAI-compatible API. "
            "Сохрани, чтобы вернуться позже. #ai"
        )

        self.assertEqual(summary, "NVIDIA открыла доступ к 80 моделям через OpenAI-compatible API")

    def test_sanitize_threads_summary_limits_length(self):
        summary = _sanitize_threads_summary(" ".join(["важный контекст"] * 40))

        self.assertLessEqual(len(summary), 220)
        self.assertTrue(summary.endswith("…"))


if __name__ == "__main__":
    unittest.main()
