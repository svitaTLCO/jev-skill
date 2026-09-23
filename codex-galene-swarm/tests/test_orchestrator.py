from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from threading import Event

from codex_galene_swarm.models import GateResult, ProviderResult, TaskContract, VerificationResult
from codex_galene_swarm.orchestrator import SwarmOrchestrator
from codex_galene_swarm.providers import ProviderError
from codex_galene_swarm.store import RunStore


class FakeProvider:
    def generate(self, goal: str, contract: TaskContract) -> ProviderResult:
        return ProviderResult(
            content=f"candidate for {contract.task_id}",
            provider_request_id="request-1",
            finish_reason="stop",
            completion_tokens=12,
            reasoning_tokens=0,
            latency_ms=1.0,
        )


class PassingEvaluator:
    def evaluate(self, contract: TaskContract, candidate: str) -> GateResult:
        return GateResult(
            status="passed",
            model="jev-test",
            reference_integrity=0.9,
            spec_compliance=0.9,
            no_scope_creep=0.9,
            quality_score=2.0,
            latency_ms=1.0,
        )


class FailingProvider:
    def generate(self, goal: str, contract: TaskContract) -> ProviderResult:
        raise ProviderError(
            "no completion",
            {"finish_reason": "length", "reasoning_tokens": 120},
        )


class PassingVerifier:
    def verify(self, contract: TaskContract, candidate: str) -> VerificationResult:
        return VerificationResult(
            status="passed",
            image="project-tests:local",
            command=contract.verification_command,
            exit_code=0,
            duration_ms=2.0,
            output="1 test passed",
        )


class BrokenVerifier:
    def verify(self, contract: TaskContract, candidate: str) -> VerificationResult:
        from codex_galene_swarm.verifier import VerificationError

        raise VerificationError("daemon unavailable")


class BlockingProvider(FakeProvider):
    def __init__(self) -> None:
        self.entered = Event()
        self.release = Event()

    def generate(self, goal: str, contract: TaskContract) -> ProviderResult:
        self.entered.set()
        if not self.release.wait(5):
            raise TimeoutError("test provider was not released")
        return super().generate(goal, contract)


class OrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        store = RunStore(str(Path(self.temp.name) / "runs.sqlite3"))
        self.orchestrator = SwarmOrchestrator(store, FakeProvider(), PassingEvaluator(), max_concurrency=2)

    def tearDown(self) -> None:
        self.orchestrator.close()
        self.temp.cleanup()

    def wait_for_terminal(self, run_id: str) -> dict:
        for _ in range(100):
            result = self.orchestrator.result(run_id)
            if result["status"] in {"completed", "failed", "cancelled"}:
                return result
            time.sleep(0.01)
        self.fail("run did not reach a terminal state")

    def test_persists_candidate_and_jev_evidence(self) -> None:
        started = self.orchestrator.start(
            "Implement a bounded change",
            [{"task_id": "one", "role": "implementer", "objective": "Return the candidate"}],
            require_jev=True,
        )
        result = self.wait_for_terminal(started["run_id"])
        self.assertEqual("completed", result["status"])
        self.assertEqual("passed", result["tasks"][0]["status"])
        self.assertEqual("candidate for one", result["tasks"][0]["result"]["candidate"])
        self.assertEqual("passed", result["tasks"][0]["result"]["jev"]["status"])

    def test_rejects_duplicate_task_ids(self) -> None:
        task = {"task_id": "same", "role": "implementer", "objective": "Return code"}
        with self.assertRaisesRegex(ValueError, "unique"):
            self.orchestrator.start("goal", [task, task])

    def test_research_batch_has_no_fixed_task_or_worker_ceiling(self) -> None:
        other = SwarmOrchestrator(self.orchestrator.store, FakeProvider(), max_concurrency=9)
        self.addCleanup(other.close)
        tasks = [
            {"task_id": f"task-{index}", "role": "analyst", "objective": "Answer"}
            for index in range(13)
        ]
        started = other.start("Research batch", tasks)
        result = self.wait_for_terminal(started["run_id"])
        self.assertEqual(13, started["task_count"])
        self.assertEqual(13, len(result["tasks"]))
        self.assertTrue(all(task["status"] == "passed" for task in result["tasks"]))

    def test_rejects_oversized_and_malformed_prompt_fields(self) -> None:
        valid = {"task_id": "one", "role": "implementer", "objective": "Return code"}
        invalid = [
            ("x" * 4001, [valid]),
            ("goal", [{**valid, "context": "x" * 16001}]),
            ("goal", [{**valid, "interfaces": "not a list"}]),
            ("goal", [{**valid, "acceptance_checks": [1]}]),
            ("goal", [{**valid, "max_tokens": True}]),
            ("goal", [{**valid, "max_tokens": 0}]),
            ("goal", [{**valid, "output_kind": []}]),
        ]
        for goal, tasks in invalid:
            with self.subTest(goal_length=len(goal), tasks=tasks):
                with self.assertRaises(ValueError):
                    self.orchestrator.start(goal, tasks)

    def test_reconciles_interrupted_run_after_store_restart(self) -> None:
        path = str(Path(self.temp.name) / "restart.sqlite3")
        first = RunStore(path)
        contract = TaskContract(task_id="pending", role="analyst", objective="Answer")
        first.create_run("interrupted", "goal", [contract], False)
        first.set_run_status("interrupted", "running")
        first.update_task("interrupted", "pending", "running")

        recovered = RunStore(path).get_run("interrupted")
        self.assertEqual("failed", recovered["status"])
        self.assertEqual("failed", recovered["tasks"][0]["status"])
        self.assertEqual("Interrupted by server restart", recovered["tasks"][0]["error"])

    def test_cancelled_inflight_result_cannot_reappear(self) -> None:
        provider = BlockingProvider()
        other = SwarmOrchestrator(self.orchestrator.store, provider, None, max_concurrency=1)
        self.addCleanup(other.close)
        started = other.start("goal", [{"task_id": "slow", "role": "analyst", "objective": "Answer"}])
        self.assertTrue(provider.entered.wait(2))
        self.assertEqual("cancelled", other.cancel(started["run_id"])["status"])
        provider.release.set()
        for _ in range(100):
            if started["run_id"] not in other._futures:
                break
            time.sleep(0.01)
        result = other.result(started["run_id"])
        self.assertEqual("cancelled", result["status"])
        self.assertEqual("cancelled", result["tasks"][0]["status"])
        self.assertIsNone(result["tasks"][0]["result"])
        self.assertNotIn(started["run_id"], other._futures)

    def test_cancelling_completed_run_does_not_change_evidence(self) -> None:
        started = self.orchestrator.start(
            "goal", [{"task_id": "done", "role": "analyst", "objective": "Answer"}]
        )
        completed = self.wait_for_terminal(started["run_id"])
        self.assertEqual("completed", completed["status"])
        self.assertEqual("completed", self.orchestrator.cancel(started["run_id"])["status"])
        self.assertEqual(completed, self.orchestrator.result(started["run_id"]))

    def test_requires_configured_jev_when_requested(self) -> None:
        other = SwarmOrchestrator(self.orchestrator.store, FakeProvider(), None, max_concurrency=1)
        self.addCleanup(other.close)
        with self.assertRaisesRegex(ValueError, "TYPESAFE_API_KEY"):
            other.start(
                "goal",
                [{"task_id": "one", "role": "implementer", "objective": "Return code"}],
                require_jev=True,
            )

    def test_persists_provider_failure_metadata(self) -> None:
        other = SwarmOrchestrator(self.orchestrator.store, FailingProvider(), None, max_concurrency=1)
        self.addCleanup(other.close)
        started = other.start(
            "goal",
            [{"task_id": "failure", "role": "implementer", "objective": "Return code"}],
        )
        result = self.wait_for_terminal(started["run_id"])
        task = result["tasks"][0]
        self.assertEqual("failed", task["status"])
        self.assertEqual("length", task["result"]["provider_error"]["finish_reason"])
        self.assertEqual(120, task["result"]["provider_error"]["reasoning_tokens"])

    def test_requires_configured_verifier_for_executable_check(self) -> None:
        with self.assertRaisesRegex(ValueError, "Docker verifier"):
            self.orchestrator.start(
                "goal",
                [{
                    "task_id": "verify",
                    "role": "implementer",
                    "objective": "Return a patch",
                    "allowed_files": ["src/example.py"],
                    "verification_command": ["python", "-m", "unittest"],
                }],
            )

    def test_persists_executable_verification_evidence(self) -> None:
        other = SwarmOrchestrator(
            self.orchestrator.store,
            FakeProvider(),
            PassingEvaluator(),
            PassingVerifier(),
            max_concurrency=1,
        )
        self.addCleanup(other.close)
        started = other.start(
            "goal",
            [{
                "task_id": "verify",
                "role": "implementer",
                "objective": "Return a patch",
                "allowed_files": ["src/example.py"],
                "verification_command": ["python", "-m", "unittest"],
            }],
            require_jev=True,
        )
        result = self.wait_for_terminal(started["run_id"])
        task = result["tasks"][0]
        self.assertEqual("passed", task["status"])
        self.assertEqual("passed", task["result"]["verification"]["status"])
        self.assertTrue(task["result"]["verification"]["network_disabled"])

    def test_preserves_generation_evidence_when_verifier_infrastructure_fails(self) -> None:
        other = SwarmOrchestrator(
            self.orchestrator.store,
            FakeProvider(),
            PassingEvaluator(),
            BrokenVerifier(),
            max_concurrency=1,
        )
        self.addCleanup(other.close)
        started = other.start(
            "goal",
            [{
                "task_id": "verify-failure",
                "role": "implementer",
                "objective": "Return a patch",
                "allowed_files": ["src/example.py"],
                "verification_command": ["python", "-m", "unittest"],
            }],
            require_jev=True,
        )
        task = self.wait_for_terminal(started["run_id"])["tasks"][0]
        self.assertEqual("failed", task["status"])
        self.assertIn("daemon unavailable", task["error"])
        self.assertEqual("request-1", task["result"]["provider"]["provider_request_id"])
        self.assertEqual("passed", task["result"]["jev"]["status"])


if __name__ == "__main__":
    unittest.main()
