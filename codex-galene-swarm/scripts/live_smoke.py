"""Exercise the MCP boundary against live Galene and Jev without printing candidate text."""

from __future__ import annotations

import asyncio
import json

from mcp import Client

from codex_galene_swarm.server import mcp


def structured(result):
    payload = result.structured_content
    if isinstance(payload, dict) and set(payload) == {"result"}:
        return payload["result"]
    return payload


async def main() -> None:
    contract = {
        "task_id": "live-smoke",
        "role": "analyst",
        "objective": "Describe a Python function signature for adding two integers in one concise sentence.",
        "interfaces": ["Inputs are two integers; output is one integer."],
        "allowed_files": [],
        "acceptance_checks": ["No implementation", "No extra functions", "One concise sentence"],
        "output_kind": "analysis",
        "max_tokens": 1200,
    }
    async with Client(mcp) as client:
        started = structured(await client.call_tool(
            "swarm_start",
            {"goal": "Verify the live Galene and Jev orchestration path", "tasks": [contract], "require_jev": True},
        ))
        run_id = started["run_id"]
        for _ in range(120):
            status = structured(await client.call_tool("swarm_status", {"run_id": run_id}))
            if status["status"] in {"completed", "failed", "cancelled"}:
                break
            await asyncio.sleep(0.5)
        else:
            raise TimeoutError("live smoke run did not finish within 60 seconds")

        result = structured(await client.call_tool("swarm_result", {"run_id": run_id}))
        task = result["tasks"][0]
        evidence = task.get("result") or {}
        provider = evidence.get("provider") or evidence.get("provider_error") or {}
        jev = evidence.get("jev") or {}
        summary = {
            "run_id": run_id,
            "run_status": result["status"],
            "task_status": task["status"],
            "error": task.get("error"),
            "provider": {
                "request_id_present": bool(provider.get("provider_request_id")),
                "finish_reason": provider.get("finish_reason"),
                "completion_tokens": provider.get("completion_tokens"),
                "reasoning_tokens": provider.get("reasoning_tokens"),
                "latency_ms": provider.get("latency_ms"),
            },
            "jev": jev,
        }
        print(json.dumps(summary, indent=2))
        if result["status"] != "completed" or task["status"] != "passed":
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
