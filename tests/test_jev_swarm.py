import os
import subprocess
import unittest
from unittest.mock import patch

from scripts.jev_swarm import GenericRuntimeValidator, JevSwarm


class FakeJev:
    def __init__(self, answers):
        self.answers = answers
        self.states = []

    def evaluate(self, state, _questions):
        self.states.append(state)
        return self.answers, 0.01


class RuntimeValidationTests(unittest.TestCase):
    def test_syntax_success_is_not_runtime_execution(self):
        valid, message = GenericRuntimeValidator.validate_code("raise RuntimeError('boom')", "python")
        self.assertTrue(valid)
        self.assertIn("syntax", message.lower())

    def test_unknown_language_fails_closed(self):
        valid, message = GenericRuntimeValidator.validate_code("echo unsafe", "shell")
        self.assertFalse(valid)
        self.assertIn("Unsupported", message)

    @patch("scripts.jev_swarm.subprocess.run")
    @patch("scripts.jev_swarm.shutil.which", return_value="/usr/bin/docker")
    def test_runtime_tests_use_restricted_docker(self, _which, run):
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        valid, _ = GenericRuntimeValidator.validate_with_tests("def f(): return 1", "assert f() == 1", "python")
        self.assertTrue(valid)
        command = run.call_args.args[0]
        for item in ("--network", "none", "--read-only", "--pids-limit", "--memory", "--cap-drop"):
            self.assertIn(item, command)
        self.assertIn("ALL", command)

    def test_non_python_runtime_fails_closed(self):
        valid, message = GenericRuntimeValidator.validate_with_tests("const x = 1", "console.assert(x === 1)", "javascript")
        self.assertFalse(valid)
        self.assertIn("Runtime sandbox", message)


class ContractGateTests(unittest.TestCase):
    @patch("scripts.jev_swarm.GenericRuntimeValidator.validate_code", return_value=(True, "syntax ok"))
    @patch("scripts.jev_swarm.OllamaWorker.generate", return_value=("x" * 3001, 0.01, 10))
    def test_scope_gate_is_enforced_and_full_spec_is_reviewed(self, _generate, _validate):
        swarm = object.__new__(JevSwarm)
        swarm.jev = FakeJev({
            "reference_integrity": {"noul": 0.9},
            "spec_compliance": {"noul": 0.9},
            "no_scope_creep": {"noul": 0.1},
            "code_quality": {"score": 2.0},
        })
        result = swarm.execute_micro_contract(
            task_id="scope-check", prompt="Implement only function target().", lang="python"
        )
        self.assertFalse(result["passed"])
        state = swarm.jev.states[-1]
        self.assertIn("Implement only function target().", state)
        self.assertIn("x" * 3001, state)

    def test_candidate_count_is_bounded(self):
        swarm = object.__new__(JevSwarm)
        with self.assertRaises(ValueError):
            swarm.execute_micro_contract("bounded", "x", sample_candidates=4)


if __name__ == "__main__":
    unittest.main()
