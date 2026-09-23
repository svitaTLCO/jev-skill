import unittest
from pathlib import Path
from unittest.mock import patch
import os
import tempfile

from scripts import demo_server


class DemoServerTests(unittest.TestCase):
    def setUp(self):
        demo_server.RUNS.clear()

    def test_extract_html_requires_complete_document(self):
        self.assertEqual(demo_server.extract_html("text <!doctype html><html>x</html>"), "<!doctype html><html>x</html>")
        self.assertEqual(demo_server.extract_html("<html><body>play</body></html>"), "<html><body>play</body></html>")
        with self.assertRaises(ValueError):
            demo_server.extract_html("```html\n<div>not a document</div>\n```")

    def test_secret_reader_extracts_only_requested_dotenv_value(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("UNRELATED=keep-private\nTYPESAFE_API_KEY='expected-key'\n")
            path = handle.name
        try:
            with patch.dict(os.environ, {"DEMO_TEST_SECRET_FILE": path}, clear=False):
                self.assertEqual(demo_server.read_env_file_value("DEMO_TEST_SECRET_FILE", "TYPESAFE_API_KEY"), "expected-key")
                self.assertIsNone(demo_server.read_env_file_value("DEMO_TEST_SECRET_FILE", "MISSING"))
        finally:
            os.unlink(path)

    @patch("scripts.demo_server.threading.Thread")
    def test_create_run_exposes_two_independent_lanes(self, thread):
        run = demo_server.create_run()
        self.assertEqual(run["status"], "running")
        self.assertEqual(set(run["lanes"]), {"direct", "guided"})
        self.assertEqual(thread.call_count, 2)

    @patch("scripts.demo_server.urllib.request.urlopen")
    def test_ollama_adapter_is_cap_free_and_uses_native_generate_endpoint(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = b'{"response":"<!doctype html><html></html>","eval_count":12}'
        content, tokens = demo_server.ollama_generate("make a game", thinking=False)
        self.assertEqual(tokens, 12)
        self.assertIn("<!doctype html>", content)
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/api/generate"))
        self.assertIn(b'"think": false', request.data)
        # Cap-free policy (2026-09-22): no token ceiling in the payload; the
        # client deadline is a wall-clock hang guard, not a content budget.
        self.assertNotIn(b"num_predict", request.data)
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 2400)

    def test_v2_requirement_has_no_size_language(self):
        text = demo_server.GUIDED_REQUIREMENT_V2.lower()
        self.assertNotIn("token", text)
        self.assertNotIn("compact", text)
        self.assertIn("<!doctype html>", text)

    @patch("scripts.demo_server.threading.Thread")
    def test_create_run_accepts_requested_lane_subset(self, thread):
        run = demo_server.create_run(["guided", "guided_v2"])
        self.assertEqual(set(run["lanes"]), {"guided", "guided_v2"})
        self.assertEqual(thread.call_count, 2)

    @patch("scripts.demo_server.threading.Thread")
    def test_create_run_rejects_unknown_lane(self, thread):
        with self.assertRaises(ValueError):
            demo_server.create_run(["direct", "warp"])

    def test_persist_raw_writes_gitignored_run_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(demo_server, "RUN_ROOT", Path(tmp)):
                demo_server.persist_raw("abc123", "direct", "<truncated output>")
                ledger = Path(tmp) / "abc123" / "direct.raw.txt"
                self.assertEqual(ledger.read_text(encoding="utf-8"), "<truncated output>")


if __name__ == "__main__":
    unittest.main()
