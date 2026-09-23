"""Run bounded game contracts through the installed swarm MCP boundary.

This is an operator pilot harness, executed only inside the swarm Docker image.
Candidates are written to the approved local pilot ledger volume for Codex review.
"""

import asyncio
import json
from pathlib import Path

from mcp import Client

from codex_galene_swarm.server import mcp


def structured(response):
    payload = response.structured_content
    if isinstance(payload, dict) and set(payload) == {"result"}:
        return payload["result"]
    return payload


async def main():
    request = json.loads(Path("/run/contracts.json").read_text())
    async with Client(mcp) as client:
        started = structured(await client.call_tool("swarm_start", request))
        run_id = started["run_id"]
        for _ in range(600):
            status = structured(await client.call_tool("swarm_status", {"run_id": run_id}))
            if status["status"] in {"completed", "failed", "cancelled"}:
                break
            await asyncio.sleep(0.5)
        else:
            raise TimeoutError(f"run {run_id} did not finish within five minutes")

        result = structured(await client.call_tool("swarm_result", {"run_id": run_id}))
        output = Path("/data/circuit-sprint-candidates") / run_id
        output.mkdir(parents=True, exist_ok=True)
        summary = {"run_id": run_id, "run_status": result["status"], "tasks": []}
        for task in result["tasks"]:
            evidence = task.get("result") or {}
            candidate = evidence.get("candidate")
            if isinstance(candidate, str):
                (output / f"{task['task_id']}.js").write_text(candidate)
            provider = evidence.get("provider") or evidence.get("provider_error") or {}
            summary["tasks"].append({
                "task_id": task["task_id"],
                "status": task["status"],
                "error": task.get("error"),
                "finish_reason": provider.get("finish_reason"),
                "completion_tokens": provider.get("completion_tokens"),
                "jev": (evidence.get("jev") or {}).get("status"),
            })
        (output / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))
        return all(task["status"] == "passed" for task in summary["tasks"])


if __name__ == "__main__":
    if not asyncio.run(main()):
        raise SystemExit(1)
