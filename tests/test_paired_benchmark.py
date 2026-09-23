import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_paired_benchmark as benchmark


class ShapeChoosingFakeJev:
    def evaluate(self, _state, questions):
        self.chosen = next(iter(questions["implementation_shape"]["criteria"]))
        return {"implementation_shape": {"choice": self.chosen}}, 0.012


class PairedBenchmarkTests(unittest.TestCase):
    TASK = {
        "id": "sum_positive_integers",
        "split": "development",
        "language": "python",
        "prompt": "Implement only sum_positive_integers(values).",
        "tests": "assert sum_positive_integers([1, -1]) == 1",
    }

    def args(self):
        return argparse.Namespace(
            manifest="benchmarks/evaluation_manifest.json",
            provider="ollama",
            worker_url="http://worker.test/api/generate",
            model="qwen-test",
            seed=7,
            seed_count=1,
            output_dir="benchmark-runs",
            resume_ledger=None,
            temperature=0.2,
            think=False,
            timeout=30,
            typesafe_url="http://typesafe.test/v1",
        )

    def test_extract_code_prefers_the_largest_python_fence(self):
        raw = "ignore\n```python\ndef f():\n return 1\n```\n```python\nx = 1\n```"
        self.assertEqual(benchmark.extract_code(raw), "def f():\n return 1")

    def test_secret_file_loader_reads_only_the_requested_value(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("UNRELATED=not-exported\nTYPESAFE_API_KEY='expected'\n")
            path = handle.name
        try:
            self.assertEqual(benchmark.load_env_value(path, "TYPESAFE_API_KEY"), "expected")
            self.assertIsNone(benchmark.load_env_value(path, "MISSING"))
            self.assertNotIn("UNRELATED", os.environ)
        finally:
            os.unlink(path)

    def test_manifest_is_fixed_nine_task_dev_holdout_corpus(self):
        manifest_path = Path(__file__).parents[1] / "benchmarks" / "evaluation_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["tasks"]), 9)
        self.assertEqual({task["split"] for task in manifest["tasks"]}, {"development", "holdout"})
        browser = next(task for task in manifest["tasks"] if task["id"] == "accessible_counter_browser")
        self.assertEqual(browser["browser_oracle"]["steps"][1]["activation"], "keyboard")

    def test_p0_defaults_to_twenty_paired_seeds(self):
        with patch.object(sys, "argv", ["run_paired_benchmark.py", "--model", "qwen3.5:4b"]):
            self.assertEqual(benchmark.parse_args().seed_count, 20)

    def test_guided_prompt_adds_only_the_jev_selected_shape(self):
        prompt = "Implement the requested function."
        self.assertEqual(
            benchmark.guided_worker_prompt(prompt, "minimal_pure_function"),
            prompt + "\n\nJev-selected implementation shape: minimal_pure_function.",
        )

    def test_resume_ledger_loads_arm_checkpoints_and_rejects_config_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "run.ndjson"
            header = {"record_type": "run_start", "run_id": "run-1", "temperature": 0.2}
            arm = {"task_id": "sum", "seed_requested": 1, "arm": "direct", "status": "completed"}
            resume = {"record_type": "run_resume", "model_warmup": {"eval_count": 1}}
            ledger.write_text("\n".join(json.dumps(item) for item in (header, arm, resume)) + "\n")
            loaded_header, records, events = benchmark.read_resume_ledger(ledger)
            self.assertEqual(loaded_header, header)
            self.assertEqual(records, [arm])
            self.assertEqual(events, [resume])
            benchmark.validate_resume_header(loaded_header, {"temperature": 0.2})
            with self.assertRaisesRegex(ValueError, "temperature"):
                benchmark.validate_resume_header(loaded_header, {"temperature": 0.5})

    @patch("scripts.run_paired_benchmark.urllib.request.urlopen")
    def test_ollama_request_is_uncapped_and_reuses_model_residency(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps({"response": "def f(): pass", "eval_count": 4}).encode()
        code, result, _ = benchmark.generate_ollama(
            "http://worker/api/generate", "qwen3.5:4b", "write f", 17, 0.2, False, 30
        )
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(code, "def f(): pass")
        self.assertEqual(result["eval_count"], 4)
        self.assertEqual(payload["options"], {"temperature": 0.2, "seed": 17})
        self.assertNotIn("num_predict", payload["options"])
        self.assertEqual(payload["keep_alive"], "30m")

    @patch("scripts.run_paired_benchmark.urllib.request.urlopen")
    def test_model_digest_resolves_exact_named_tag(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps({"models": [
            {"name": "qwen3.5:4b", "digest": "sha256:test-digest"},
        ]}).encode()
        self.assertEqual(
            benchmark.model_digest("http://worker:11434/api/generate", "qwen3.5:4b", 10),
            "sha256:test-digest",
        )
        self.assertEqual(urlopen.call_args.args[0].full_url, "http://worker:11434/api/tags")

    def test_oracle_constraints_detect_scope_creep(self):
        self.assertEqual(
            benchmark.check_constraints(
                "def target(x): return x\n",
                {"top_level_functions": ["target"], "forbid_imports": True},
            ),
            (True, "structural constraints passed"),
        )
        passed, reason = benchmark.check_constraints(
            "import os\ndef target(x): return x\ndef helper(): pass\n",
            {"top_level_functions": ["target"], "forbid_imports": True},
        )
        self.assertFalse(passed)
        self.assertIn("top-level functions", reason)

    def test_percentile_interpolates_and_handles_empty_input(self):
        self.assertEqual(benchmark.percentile([0, 10], 0.5), 5)
        self.assertIsNone(benchmark.percentile([], 0.95))

    def test_multi_file_json_protocol_rejects_path_traversal(self):
        parsed = benchmark.parse_file_map(
            '{"files":{"pkg/__init__.py":"from .core import run\\n",'
            '"pkg/core.py":"def run(): return 1\\n"}}'
        )
        self.assertEqual(set(parsed), {"pkg/__init__.py", "pkg/core.py"})
        with self.assertRaisesRegex(ValueError, "unsafe candidate path"):
            benchmark.parse_file_map('{"files":{"../outside.py":"print(1)"}}')

    def test_jev_choice_receives_task_prompt_but_no_oracle_cases(self):
        class FakeJev:
            state = ""

            def evaluate(self, state, questions):
                self.state = state
                key = next(iter(questions["implementation_shape"]["criteria"]))
                return {"implementation_shape": {"choice": key}}, 0.01

        client = FakeJev()
        task = {
            "prompt": "Implement a button.", "tests": "visible requirement",
            "hidden_tests": "SECRET HIDDEN ASSERT", "browser_oracle": {"secret": "SECRET BROWSER ORACLE"},
            "artifact_type": "html",
        }
        benchmark.choose_implementation(client, task)
        self.assertIn("Implement a button.", client.state)
        self.assertNotIn("visible requirement", client.state)
        self.assertNotIn("SECRET HIDDEN ASSERT", client.state)
        self.assertNotIn("SECRET BROWSER ORACLE", client.state)

    @patch("scripts.run_paired_benchmark.subprocess.run")
    def test_multifile_sandbox_is_network_disabled_and_read_only(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        passed, _ = benchmark.validate_python_package(
            {"pkg/__init__.py": "", "pkg/core.py": "def run(): return 1"},
            "from pkg.core import run\nassert run() == 1",
        )
        self.assertTrue(passed)
        command = run.call_args.args[0]
        self.assertIn("none", command)
        self.assertIn("--read-only", command)
        self.assertIn("--cap-drop", command)

    @patch("scripts.run_paired_benchmark.subprocess.run")
    def test_browser_oracle_runs_in_separate_network_disabled_container(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, '{"passed":true}', "")
        passed, _ = benchmark.validate_browser_html(
            "<!doctype html><html><title>Counter</title></html>",
            {"title": "Counter", "initial_text": "Count: 0", "steps": []},
        )
        self.assertTrue(passed)
        command = run.call_args.args[0]
        self.assertIn("none", command)
        self.assertIn("--user", command)
        self.assertIn("pwuser", command)

    @patch("scripts.run_paired_benchmark.GenericRuntimeValidator.validate_with_tests", return_value=(True, "sandbox pass"))
    @patch("scripts.run_paired_benchmark.generate_ollama", return_value=("def sum_positive_integers(values): return sum(v for v in values if v > 0)", {"eval_count": 12, "seed": 7}, 0.1))
    def test_paired_arms_persist_redacted_records_and_raw_candidates(self, _generate, _validate):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = self.args()
            direct = benchmark.run_arm("direct", self.TASK, args, "run-1", root, None, 7)
            fake_jev = ShapeChoosingFakeJev()
            guided = benchmark.run_arm("guided", self.TASK, args, "run-1", root, fake_jev, 7)
            self.assertEqual(direct["status"], "completed")
            self.assertTrue(direct["passed"])
            self.assertTrue(direct["provider_seed_confirmed"])
            self.assertEqual(guided["status"], "completed")
            self.assertTrue(guided["passed"])
            self.assertEqual(guided["jev"]["implementation_shape"], fake_jev.chosen)
            self.assertNotIn("api_key", json.dumps(guided).lower())
            self.assertTrue(Path(direct["raw_candidate_path"]).is_file())
            self.assertTrue(Path(guided["raw_candidate_path"]).is_file())

    @patch("scripts.run_paired_benchmark.subprocess.run")
    @patch("scripts.run_paired_benchmark.urllib.request.urlopen")
    def test_html_arm_extracts_document_and_runs_browser_oracle(self, urlopen, run):
        document = ("<!doctype html><html><head><title>Counter</title></head>"
                    "<body><span id='n'>Count: 0</span></body></html>")
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps({
            "response": f"Here is the page:\n{document}\nDone.",
            "eval_count": 90, "seed": 7, "done_reason": "stop",
        }).encode()
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"passed": True}), "")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = {
                "id": "counter_page", "split": "holdout", "language": "html",
                "prompt": "Build an accessible counter page.", "tests": "",
                "artifact_type": "html",
                "browser_oracle": {"title": "Counter", "initial_text": "Count: 0", "steps": []},
            }
            record = benchmark.run_arm("direct", task, self.args(), "run-1", root, None, 7)
            self.assertEqual(record["status"], "completed", record.get("error"))
            self.assertTrue(record["passed"])
            self.assertTrue(record["provider_seed_confirmed"])
            candidate_path = Path(record["raw_candidate_path"])
            self.assertTrue(candidate_path.name.endswith(".html"))
            self.assertIn("<html>", candidate_path.read_text(encoding="utf-8").lower())

    def test_paired_summary_bootstrap_is_deterministic_and_empty_safe(self):
        tasks = [{"id": "t"}]
        empty = benchmark.paired_summary([], tasks, 20)
        self.assertIsNone(empty["bootstrap_95_ci_paired_pass_delta"])
        self.assertEqual(empty["requested_pairs"], 20)

        def row(arm, seed, passed):
            return {"task_id": "t", "seed_requested": seed, "arm": arm,
                    "status": "completed", "passed": passed, "wall_clock_ms": 1000.0}

        all_pass = [row("direct", s, True) for s in range(4)] + [row("guided", s, True) for s in range(4)]
        summary = benchmark.paired_summary(all_pass, tasks, 4)
        self.assertEqual(summary["completed_pairs"], 4)
        self.assertEqual(summary["mean_paired_pass_delta_guided_minus_direct"], 0.0)
        self.assertEqual(summary["bootstrap_95_ci_paired_pass_delta"], [0.0, 0.0])
        self.assertEqual(summary["by_task"]["t"]["paired_seeds_completed"], 4)

        mixed = [row("direct", 0, False), row("guided", 0, True),
                 row("direct", 1, True), row("guided", 1, True)]
        first = benchmark.paired_summary(mixed, tasks, 2)["bootstrap_95_ci_paired_pass_delta"]
        second = benchmark.paired_summary(mixed, tasks, 2)["bootstrap_95_ci_paired_pass_delta"]
        self.assertEqual(first, second)
        self.assertEqual(benchmark.paired_summary(mixed, tasks, 2)["mean_paired_pass_delta_guided_minus_direct"], 0.5)
        self.assertLessEqual(first[0], first[1])

    def test_seed_floor_refuses_underpowered_p0_without_directional_flag(self):
        with self.assertRaisesRegex(SystemExit, "allow-directional"):
            benchmark.validate_p0_seed_floor(5, False)
        self.assertIsNone(benchmark.validate_p0_seed_floor(5, True))
        self.assertIsNone(benchmark.validate_p0_seed_floor(20, False))

    def test_seed_count_below_twenty_is_rejected_by_cli_validation(self):
        argv = ["run_paired_benchmark.py", "--model", "qwen3.5:4b", "--seed-count", "5"]
        with patch.object(sys, "argv", argv):
            parsed = benchmark.parse_args()
            with self.assertRaisesRegex(SystemExit, "allow-directional"):
                benchmark.validate_p0_seed_floor(parsed.seed_count, parsed.allow_directional)
        argv.append("--allow-directional")
        with patch.object(sys, "argv", argv):
            parsed = benchmark.parse_args()
            self.assertIsNone(benchmark.validate_p0_seed_floor(parsed.seed_count, parsed.allow_directional))


if __name__ == "__main__":
    unittest.main()
