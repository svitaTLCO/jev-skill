from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from mcp.server import MCPServer

from .jev import JevEvaluator
from .orchestrator import SwarmOrchestrator
from .providers import GaleneProvider
from .store import RunStore
from .verifier import DockerVerifier


mcp = MCPServer(
    "Codex Galene Swarm",
    instructions=(
        "Delegate only independent, bounded contracts. Workers return candidates and never edit the worktree. "
        "Review candidates and run repository tests before applying changes."
    ),
)


@lru_cache(maxsize=1)
def get_orchestrator() -> SwarmOrchestrator:
    if os.environ.get("SWARM_REQUIRE_JEV", "0") == "1" and not os.environ.get("TYPESAFE_API_KEY"):
        raise ValueError("SWARM_REQUIRE_JEV=1 requires TYPESAFE_API_KEY")
    provider = GaleneProvider()
    jev = JevEvaluator() if os.environ.get("TYPESAFE_API_KEY") else None
    repository_path = os.environ.get("SWARM_REPOSITORY_PATH")
    verifier_image = os.environ.get("SWARM_VERIFIER_IMAGE")
    verifier = None
    if repository_path and verifier_image:
        verifier = DockerVerifier(
            repository_path=repository_path,
            image=verifier_image,
            timeout_seconds=int(os.environ.get("SWARM_VERIFIER_TIMEOUT", "300")),
        )
    store = RunStore(os.environ.get("SWARM_DB_PATH", "/data/swarm.sqlite3"))
    return SwarmOrchestrator(
        store=store,
        provider=provider,
        jev_evaluator=jev,
        verifier=verifier,
        max_concurrency=int(os.environ.get("SWARM_MAX_CONCURRENCY", "4")),
    )


@mcp.tool()
def swarm_start(goal: str, tasks: list[dict[str, Any]], require_jev: bool = False) -> dict[str, Any]:
    """Start bounded Galene worker contracts and return a durable run identifier."""
    mandatory_jev = os.environ.get("SWARM_REQUIRE_JEV", "0") == "1"
    return get_orchestrator().start(goal=goal, tasks=tasks, require_jev=require_jev or mandatory_jev)


@mcp.tool()
def swarm_status(run_id: str) -> dict[str, Any]:
    """Return run and task states without candidate bodies."""
    return get_orchestrator().status(run_id)


@mcp.tool()
def swarm_result(run_id: str) -> dict[str, Any]:
    """Return completed candidates, provider metadata, and Jev gate evidence."""
    return get_orchestrator().result(run_id)


@mcp.tool()
def swarm_cancel(run_id: str) -> dict[str, Any]:
    """Cancel queued work and prevent in-flight results from being promoted."""
    return get_orchestrator().cancel(run_id)


def main() -> None:
    get_orchestrator()
    mcp.run()


if __name__ == "__main__":
    main()
