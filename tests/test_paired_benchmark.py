import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_paired_benchmark


TASK = {
    "id": "sum_positive_integers",
    "split": "development",
    "language": "python",
    "prompt": "Implement only sum_positive_integers(values).",
    "tests": "assert sum_positive_integers([1, -1]) == 1",
}


class FakeJev:
    def evaluate(self, _state, _questions):
        return {"implementation_shape": {"choice": "minimal_pure_function"}}, 0.012


class PairedBenchmarkTests(unittest.TestCase):
    def args(self, seed=7):
        return argparse.Namespace(
            seed=seed,
            worker_url="http://worker.test/api/generate",
            model="qwen-test@sha256:abc",
            max_tokens=1200,
            temperature=0.2,
            think=False,
            timeout=30,
        )

    def test_extract_code_prefers_the_largest_python_fence(self):
        raw = "ignore\n```python\ndef f():\n return 1\n```\n```python\nx = 1\n```"
        self.assertEqual(run_paired_benchmark.extract_code(raw), "def f():\n return 1")

    def test_secret_file_loader_reads_only_the_requested_value(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("UNRELATED=not-exported\nTYPESAFE_API_KEY='expected'\n")
            path = handle.name
        try:
            self.assertEqual(run_paired_benchmark.load_env_value(path, "TYPESAFE_API_KEY"), "expected")
            self.assertIsNone(run_paired_benchmark.load_env_value(path, "MISSING"))
            self.assertNotIn("UNRELATED", os.environ)
        finally:
            os.unlink(path)

    @patch("scripts.run_paired_benchmark.urllib.request.urlopen")
    def test_ollama_generation_records_seed_request_without_exposing_secrets(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({
            "response": "```python\ndef f(): return 1\n```", "eval_count": 4, "seed": 7
        }).encode("utf-8")
        candidate, response, _elapsed = run_paired_benchmark.generate_ollama(
            "http://worker.test/api/generate", "qwen-test", "write f", 7, 1200, 0.2, False, 30
        )
        self.assertEqual(candidate, "def f(): return 1")
        self.assertEqual(response["seed"], 7)
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["options"]["seed"], 7)
        self.assertFalse(payload["think"])

    @patch("scripts.run_paired_benchmark.urllib.request.urlopen")
    def test_openai_generation_disables_thinking_and_keeps_key_out_of_payload(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({
            "choices": [{"message": {"content": "```python\ndef f(): return 1\n```"}}],
            "usage": {"completion_tokens": 4},
        }).encode("utf-8")
        candidate, response, _elapsed = run_paired_benchmark.generate_openai(
            "https://worker.test/v1", "Galene/LLM", "write f", 1200, 0.2, False, 30, "private-key"
        )
        self.assertEqual(candidate, "def f(): return 1")
        self.assertEqual(response["eval_count"], 4)
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/v1/chat/completions"))
        self.assertIn(b'"enable_thinking": false', request.data)
        self.assertNotIn(b"private-key", request.data)

    @patch("scripts.run_paired_benchmark.urllib.request.urlopen")
    def test_openai_missing_content_preserves_safe_response_metadata(self, urlopen):
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({
            "id": "request-123",
            "choices": [{"finish_reason": "length", "message": {"content": ""}}],
            "usage": {"completion_tokens": 1200, "completion_tokens_details": {"reasoning_tokens": 1180}},
        }).encode("utf-8")
        with self.assertRaises(run_paired_benchmark.WorkerResponseError) as caught:
            run_paired_benchmark.generate_openai(
                "https://worker.test/v1", "Galene/LLM", "write f", 1200, 0.2, False, 30, "private-key"
            )
        self.assertEqual(caught.exception.metadata["finish_reason"], "length")
        self.assertEqual(caught.exception.metadata["reasoning_tokens"], 1180)

    @patch("scripts.run_paired_benchmark.GenericRuntimeValidator.validate_with_tests", return_value=(True, "sandbox pass"))
    @patch("scripts.run_paired_benchmark.generate_ollama", return_value=("def sum_positive_integers(values): return sum(v for v in values if v > 0)", {"eval_count": 12, "seed": 7}, 0.1))
    def test_paired_arms_persist_redacted_records_and_raw_candidates(self, _generate, _validate):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = self.args()
            args.provider = "ollama"
            direct = run_paired_benchmark.run_arm("direct", TASK, args, "run-1", root, None, None)
            guided = run_paired_benchmark.run_arm("guided", TASK, args, "run-1", root, FakeJev(), None)
            self.assertTrue(direct["passed"])
            self.assertTrue(guided["passed"])
            self.assertTrue(direct["provider_seed_confirmed"])
            self.assertEqual(guided["jev"]["implementation_shape"], "minimal_pure_function")
            self.assertNotIn("api_key", json.dumps(guided).lower())
            self.assertTrue(Path(direct["raw_candidate_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
