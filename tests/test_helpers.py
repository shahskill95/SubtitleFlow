import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pc"))

from engine import _timestamp  # noqa: E402
from server import safe_filename, redact_log_message  # noqa: E402


class TimestampTests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(_timestamp(0), "00:00:00,000")

    def test_rounds_milliseconds(self):
        self.assertEqual(_timestamp(65.6789), "00:01:05,679")

    def test_hours(self):
        self.assertEqual(_timestamp(3661.25), "01:01:01,250")


class FilenameTests(unittest.TestCase):
    def test_removes_path_components(self):
        self.assertEqual(safe_filename("../../movie.mp4"), "movie.mp4")

    def test_replaces_unsafe_characters(self):
        self.assertEqual(safe_filename("video<>name.mp4"), "video_name.mp4")

    def test_empty_falls_back(self):
        self.assertEqual(safe_filename("..."), "video.mp4")


class AccessLogTests(unittest.TestCase):
    def test_access_log_redacts_temporary_key(self):
        message = "GET /?key=super-secret-token HTTP/1.1"
        redacted = redact_log_message(message)
        self.assertNotIn("super-secret-token", redacted)
        self.assertIn("key=[REDACTED]", redacted)


if __name__ == "__main__":
    unittest.main()
