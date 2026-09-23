from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


TaskStatus = Literal["queued", "running", "passed", "rejected", "failed", "cancelled"]
RunStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


@dataclass(frozen=True)
class TaskContract:
    task_id: str
    role: str
    objective: str
    interfaces: list[str] = field(default_factory=list)
    allowed_files: list[str] = field(default_factory=list)
    acceptance_checks: list[str] = field(default_factory=list)
    context: str = ""
    output_kind: Literal["unified_diff", "code", "analysis"] = "unified_diff"
    max_tokens: int = 1400
    verification_command: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TaskContract":
        allowed = {
            "task_id", "role", "objective", "interfaces", "allowed_files",
            "acceptance_checks", "context", "output_kind", "max_tokens",
            "verification_command",
        }
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"Unknown task fields: {sorted(unknown)}")
        contract = cls(**value)
        if not contract.task_id or not contract.objective or not contract.role:
            raise ValueError("task_id, role, and objective are required")
        if not contract.task_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Unsafe task_id: {contract.task_id!r}")
        if contract.output_kind not in {"unified_diff", "code", "analysis"}:
            raise ValueError(f"Unsupported output_kind: {contract.output_kind}")
        if not 1 <= contract.max_tokens <= 4000:
            raise ValueError("max_tokens must be between 1 and 4000")
        if not isinstance(contract.verification_command, list) or any(
            not isinstance(part, str) or not part for part in contract.verification_command
        ):
            raise ValueError("verification_command must be a list of non-empty strings")
        if len(contract.verification_command) > 32 or sum(map(len, contract.verification_command)) > 4096:
            raise ValueError("verification_command exceeds the bounded command size")
        if contract.verification_command and contract.output_kind != "unified_diff":
            raise ValueError("verification_command requires output_kind='unified_diff'")
        if contract.verification_command and not contract.allowed_files:
            raise ValueError("verification_command requires allowed_files")
        return contract

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderResult:
    content: str
    provider_request_id: str | None
    finish_reason: str | None
    completion_tokens: int | None
    reasoning_tokens: int | None
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GateResult:
    status: Literal["passed", "rejected", "ungated"]
    policy_version: str = "1"
    model: str | None = None
    reference_integrity: float | None = None
    spec_compliance: float | None = None
    no_scope_creep: float | None = None
    quality_score: float | None = None
    latency_ms: float | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationResult:
    status: Literal["passed", "rejected"]
    image: str
    command: list[str]
    exit_code: int
    duration_ms: float
    output: str
    network_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
