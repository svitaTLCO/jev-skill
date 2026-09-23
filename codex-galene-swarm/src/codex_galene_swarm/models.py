from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
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
    max_tokens: int | None = None
    verification_command: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TaskContract":
        if not isinstance(value, dict):
            raise ValueError("task must be an object")
        allowed = {
            "task_id", "role", "objective", "interfaces", "allowed_files",
            "acceptance_checks", "context", "output_kind", "max_tokens",
            "verification_command",
        }
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"Unknown task fields: {sorted(unknown)}")
        for name, limit in (("task_id", 64), ("role", 64), ("objective", 4000)):
            item = value.get(name)
            if not isinstance(item, str) or not item.strip() or len(item) > limit:
                raise ValueError(f"{name} must be a non-empty string of at most {limit} characters")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value["task_id"]):
            raise ValueError(f"Unsafe task_id: {value['task_id']!r}")
        context = value.get("context", "")
        if not isinstance(context, str) or len(context) > 16000:
            raise ValueError("context must be a string of at most 16000 characters")
        for name, max_items, max_item_length in (
            ("interfaces", 32, 1000),
            ("allowed_files", 64, 512),
            ("acceptance_checks", 32, 1000),
        ):
            items = value.get(name, [])
            if (not isinstance(items, list) or len(items) > max_items or any(
                not isinstance(item, str) or not item.strip() or len(item) > max_item_length
                for item in items
            )):
                raise ValueError(f"{name} must be a bounded list of non-empty strings")
        contract = cls(**value)
        if not isinstance(contract.output_kind, str) or contract.output_kind not in {"unified_diff", "code", "analysis"}:
            raise ValueError(f"Unsupported output_kind: {contract.output_kind}")
        if contract.max_tokens is not None and (type(contract.max_tokens) is not int or contract.max_tokens < 1):
            raise ValueError("max_tokens must be a positive integer or null")
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
