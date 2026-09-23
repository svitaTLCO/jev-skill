from __future__ import annotations

import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock
from typing import Any

from .jev import CandidateEvaluator, UngatedEvaluator
from .models import GateResult, TaskContract
from .providers import ProviderError, WorkerProvider
from .store import RunStore
from .verifier import CandidateVerifier, VerificationError


class SwarmOrchestrator:
    def __init__(
        self,
        store: RunStore,
        provider: WorkerProvider,
        jev_evaluator: CandidateEvaluator | None = None,
        verifier: CandidateVerifier | None = None,
        max_concurrency: int = 4,
    ) -> None:
        if type(max_concurrency) is not int or max_concurrency < 1:
            raise ValueError("max_concurrency must be a positive integer")
        self.store = store
        self.provider = provider
        self.jev_evaluator = jev_evaluator
        self.verifier = verifier
        self.executor = ThreadPoolExecutor(max_workers=max_concurrency, thread_name_prefix="galene-worker")
        self._futures: dict[str, list[Future[None]]] = {}
        self._lock = Lock()

    def start(self, goal: str, tasks: list[dict[str, Any]], require_jev: bool = False) -> dict[str, Any]:
        if not isinstance(goal, str) or not goal.strip() or len(goal) > 4000:
            raise ValueError("goal must be a non-empty string of at most 4000 characters")
        if not isinstance(tasks, list) or not tasks:
            raise ValueError("tasks must contain at least one contract")
        if not isinstance(require_jev, bool):
            raise ValueError("require_jev must be a boolean")
        contracts = [TaskContract.from_dict(item) for item in tasks]
        if len({item.task_id for item in contracts}) != len(contracts):
            raise ValueError("task_id values must be unique within a run")
        if require_jev and self.jev_evaluator is None:
            raise ValueError("Jev gating was required but TYPESAFE_API_KEY is not configured")
        if any(item.verification_command for item in contracts) and self.verifier is None:
            raise ValueError("Executable verification was requested but the Docker verifier is not configured")

        run_id = uuid.uuid4().hex
        self.store.create_run(run_id, goal.strip(), contracts, require_jev)
        self.store.set_run_status(run_id, "running")
        with self._lock:
            self._futures[run_id] = []
        for item in contracts:
            future = self.executor.submit(self._execute, run_id, goal.strip(), item, require_jev)
            with self._lock:
                self._futures.setdefault(run_id, []).append(future)
            future.add_done_callback(lambda done, key=run_id: self._forget_future(key, done))
        return {"run_id": run_id, "status": "running", "task_count": len(contracts)}

    def _forget_future(self, run_id: str, future: Future[None]) -> None:
        with self._lock:
            futures = self._futures.get(run_id)
            if futures is not None:
                futures.remove(future)
                if not futures:
                    self._futures.pop(run_id, None)

    def _execute(self, run_id: str, goal: str, contract: TaskContract, require_jev: bool) -> None:
        if not self.store.update_task(run_id, contract.task_id, "running"):
            return
        evidence: dict[str, Any] | None = None
        try:
            provider_result = self.provider.generate(goal, contract)
            if self.store.is_cancel_requested(run_id):
                return
            evaluator = self.jev_evaluator if require_jev else UngatedEvaluator()
            gate: GateResult = evaluator.evaluate(contract, provider_result.content)
            evidence = {"candidate": provider_result.content, "provider": provider_result.to_dict(), "jev": gate.to_dict()}
            status = "passed" if gate.status in {"passed", "ungated"} else "rejected"
            if self.store.is_cancel_requested(run_id):
                return
            if status == "passed" and contract.verification_command:
                verification = self.verifier.verify(contract, provider_result.content)
                evidence["verification"] = verification.to_dict()
                status = "passed" if verification.status == "passed" else "rejected"
            self.store.update_task(
                run_id,
                contract.task_id,
                status,
                evidence,
            )
        except ProviderError as exc:
            self.store.update_task(
                run_id,
                contract.task_id,
                "failed",
                result={"provider_error": exc.metadata},
                error=f"ProviderError: {str(exc)[:400]}",
            )
        except VerificationError as exc:
            self.store.update_task(
                run_id,
                contract.task_id,
                "failed",
                result=evidence,
                error=f"VerificationError: {str(exc)[:400]}",
            )
        except Exception as exc:
            self.store.update_task(run_id, contract.task_id, "failed", error=f"{type(exc).__name__}: {str(exc)[:400]}")
        finally:
            self.store.finish_if_terminal(run_id)

    def status(self, run_id: str) -> dict[str, Any]:
        run = self.store.get_run(run_id, include_results=False)
        if not run:
            raise ValueError(f"Unknown run_id: {run_id}")
        return run

    def result(self, run_id: str) -> dict[str, Any]:
        run = self.store.get_run(run_id, include_results=True)
        if not run:
            raise ValueError(f"Unknown run_id: {run_id}")
        return run

    def cancel(self, run_id: str) -> dict[str, Any]:
        status = self.store.request_cancel(run_id)
        if status is None:
            raise ValueError(f"Unknown run_id: {run_id}")
        with self._lock:
            for future in self._futures.get(run_id, []):
                future.cancel()
        return {"run_id": run_id, "status": status}

    def close(self) -> None:
        self.executor.shutdown(wait=True, cancel_futures=True)
