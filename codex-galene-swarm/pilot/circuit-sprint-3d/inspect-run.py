"""Print pilot run evidence without candidate text or credentials."""

import json
import sys

from codex_galene_swarm.store import RunStore


run = RunStore("/data/swarm.sqlite3").get_run(sys.argv[1])
if run is None:
    raise SystemExit("unknown run")
print(json.dumps({
    "run_id": run["run_id"],
    "status": run["status"],
    "tasks": [{
        "id": task["task_id"],
        "status": task["status"],
        "error": task["error"],
        "candidate_characters": len((task.get("result") or {}).get("candidate") or ""),
        "jev": (task.get("result") or {}).get("jev"),
        "provider": {
            key: value for key, value in (
                (task.get("result") or {}).get("provider")
                or (task.get("result") or {}).get("provider_error")
                or {}
            ).items() if key != "content"
        },
    } for task in run["tasks"]],
}, indent=2))
