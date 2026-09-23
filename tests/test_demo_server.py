import shutil
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import os
import tempfile

from scripts import demo_server


class DemoServerTests(unittest.TestCase):
    def setUp(self):
        demo_server.RUNS.clear()
        self.run_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.run_tmp.cleanup)
        patcher = patch.object(demo_server, "RUN_ROOT", Path(self.run_tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)

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

    def test_run_checkpoint_survives_restart_and_marks_active_lanes_interrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(demo_server, "RUN_ROOT", Path(tmp)):
                run_id = "a" * 32
                run = {
                    "id": run_id,
                    "status": "running",
                    "model": "qwen3.5:4b",
                    "lanes": {
                        "guided_aa": {"status": "generating", "detail": "sampling", "started_at": 1.0,
                                      "elapsed_seconds": 12.0, "tokens": 100},
                    },
                }
                demo_server.persist_run(run)
                snapshot = json.loads((Path(tmp) / run_id / "run.json").read_text(encoding="utf-8"))
                self.assertNotIn("started_at", snapshot["lanes"]["guided_aa"])
                demo_server.RUNS.clear()
                demo_server.restore_runs()
                restored = demo_server.RUNS[run_id]
                self.assertEqual(restored["status"], "interrupted")
                self.assertEqual(restored["lanes"]["guided_aa"]["status"], "failed")
                self.assertIn("raw artifacts", restored["lanes"]["guided_aa"]["detail"])

    def test_gate_feedback_names_only_failing_dimensions(self):
        text = demo_server.gate_feedback(0.30, 0.63, 1.69)
        self.assertIn("contract=0.30", text)
        self.assertIn("scope=0.63", text)
        self.assertNotIn("quality=", text)
        # The gate passed in race #4's v2 arm only on quality; feedback must stay empty there.
        self.assertEqual(demo_server.gate_feedback(0.80, 0.90, 1.50), "")

    def test_assemble_repair_issues_puts_gate_feedback_first(self):
        issues = demo_server.assemble_repair_issues(
            "contract=0.30 below 0.70 — missing requirement",
            ["Does the specified input actually start the game?"],
            parse_ok=False, parse_err="SyntaxError: Unexpected identifier 'e'",
        )
        lines = issues.splitlines()
        self.assertTrue(lines[0].startswith("GATE FEEDBACK:"))
        self.assertEqual(lines[1], "PARSER ERROR: SyntaxError: Unexpected identifier 'e'")
        self.assertEqual(lines[2], "VIOLATES REQUIREMENT: Does the specified input actually start the game?")
        parsed = demo_server.assemble_repair_issues("gate still failing", [], parse_ok=True, parse_err="")
        self.assertNotIn("PARSER ERROR", parsed)

    @patch("scripts.demo_server.threading.Thread")
    def test_create_run_accepts_guided_a_lane_subset(self, thread):
        run = demo_server.create_run(["guided_v2", "guided_a"])
        self.assertEqual(set(run["lanes"]), {"guided_v2", "guided_a"})
        self.assertEqual(thread.call_count, 2)

    @patch("scripts.demo_server.threading.Thread")
    def test_create_run_accepts_guided_aa_lane_subset(self, thread):
        run = demo_server.create_run(["guided_v2", "guided_aa"])
        self.assertEqual(set(run["lanes"]), {"guided_v2", "guided_aa"})
        self.assertEqual(thread.call_count, 2)

    def test_semantic_critic_accepts_only_named_defect_options(self):
        class FakeJev:
            def evaluate(self, state, questions):
                self.asserted_state = state
                self.asserted_questions = questions
                return {"defect": {"choice": "collision_geometry"}}, 0.25

        jev = FakeJev()
        choice, elapsed = demo_server.name_semantic_defect(jev, "<html>candidate</html>")
        self.assertEqual(choice, "collision_geometry")
        self.assertEqual(elapsed, 0.25)
        self.assertIn("Trusted requirement", jev.asserted_state)
        self.assertIn("collision_geometry", jev.asserted_questions["defect"]["criteria"])

        class InvalidJev:
            def evaluate(self, state, questions):
                return {"defect": {"choice": "invented_issue"}}, 0.0

        with self.assertRaisesRegex(ValueError, "unknown defect choice"):
            demo_server.name_semantic_defect(InvalidJev(), "<html>candidate</html>")

    @unittest.skipUnless(shutil.which("node"), "node not available on PATH")
    def test_syntax_check_flags_unparseable_and_missing_script_blocks(self):
        ok, message = demo_server.syntax_check("<!doctype html><html><script>var x = 1;</script></html>")
        self.assertTrue(ok)
        # A broken second block must fail the check even though the first parses.
        multi, _ = demo_server.syntax_check(
            "<html><script>var a = 1;</script><script src=\"ext.js\"></script><script>let = ;</script></html>")
        self.assertFalse(multi)
        bad, msg = demo_server.syntax_check("<!doctype html><html><script>let = ;</script></html>")
        self.assertFalse(bad)
        self.assertIn("SyntaxError", msg)
        none_js, msg = demo_server.syntax_check("<!doctype html><html><body>plain</body></html>")
        self.assertFalse(none_js)
        self.assertIn("no executable", msg)


if __name__ == "__main__":
    unittest.main()
