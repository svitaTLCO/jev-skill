"""Re-evaluate one pilot candidate after removing an enclosing Markdown fence."""

import json
import sys
from pathlib import Path

from codex_galene_swarm.jev import JevEvaluator
from codex_galene_swarm.models import TaskContract


task_id = sys.argv[1]
candidate = Path("/run/candidate.js").read_text().strip()
lines = candidate.splitlines()
if lines and lines[0].startswith("```") and lines[-1].strip() == "```":
    candidate = "\n".join(lines[1:-1]).strip()
request = json.loads(Path("/run/contracts.json").read_text())
contract = next(TaskContract.from_dict(item) for item in request["tasks"] if item["task_id"] == task_id)
gate = JevEvaluator().evaluate(contract, candidate)
print(json.dumps({"task_id": task_id, "gate": gate.to_dict(), "candidate_characters": len(candidate)}, indent=2))
