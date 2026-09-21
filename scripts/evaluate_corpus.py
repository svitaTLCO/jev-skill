#!/usr/bin/env python3
"""Reproducibly score supplied candidate artifacts against the fixed public corpus."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from jev_swarm import GenericRuntimeValidator


def sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="benchmarks/evaluation_manifest.json")
    parser.add_argument("--candidates", required=True, help="Directory containing named candidate files")
    parser.add_argument("--model", required=True, help="Exact model identifier or digest")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output", default="evaluation-results.json")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    candidate_dir = Path(args.candidates)
    records = []
    for task in manifest["tasks"]:
        path = candidate_dir / task["candidate_file"]
        if not path.is_file():
            records.append({"id": task["id"], "passed": False, "reason": "candidate file missing"})
            continue
        candidate = path.read_text(encoding="utf-8")
        passed, reason = GenericRuntimeValidator.validate_with_tests(candidate, task["tests"], task["language"])
        records.append({
            "id": task["id"], "split": task["split"], "passed": passed, "reason": reason,
            "candidate_sha256": sha256(candidate),
        })

    report = {
        "schema_version": 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "seed": args.seed,
        "manifest_sha256": sha256(json.dumps(manifest, sort_keys=True)),
        "results": records,
        "passed": sum(record["passed"] for record in records),
        "total": len(records),
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
