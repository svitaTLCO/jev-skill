"""Probe Galene's Qwen non-thinking request shape without printing completion text."""

import json
import os
import urllib.request
from pathlib import Path

from codex_galene_swarm.models import TaskContract
from codex_galene_swarm.providers import build_worker_prompt


request_spec = json.loads(Path("/run/contracts.json").read_text())
contract = TaskContract.from_dict(request_spec["tasks"][0])
payload = {
    "model": os.environ.get("GALENE_MODEL", "Galene/LLM"),
    "messages": [
        {"role": "system", "content": "You execute one bounded software contract. Return code immediately."},
        {"role": "user", "content": build_worker_prompt(request_spec["goal"], contract)},
    ],
    "temperature": 0.2,
    "max_tokens": int(os.environ.get("PROBE_MAX_TOKENS", "2500")),
    "reasoning_effort": "low",
    "enable_thinking": os.environ.get("PROBE_THINKING", "0") == "1",
    "chat_template_kwargs": {"enable_thinking": os.environ.get("PROBE_THINKING", "0") == "1"},
    "stream": False,
}
base_url = os.environ["GALENE_BASE_URL"].rstrip("/")
request = urllib.request.Request(
    f"{base_url}/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Authorization": f"Bearer {os.environ['GALENE_API_KEY']}", "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=180) as response:
    data = json.load(response)
choice = (data.get("choices") or [{}])[0]
usage = data.get("usage") or {}
details = usage.get("completion_tokens_details") or {}
content = (choice.get("message") or {}).get("content")
print(json.dumps({
    "request_id_present": bool(data.get("id")),
    "finish_reason": choice.get("finish_reason"),
    "completion_tokens": usage.get("completion_tokens"),
    "reasoning_tokens": details.get("reasoning_tokens"),
    "content_present": isinstance(content, str) and bool(content.strip()),
    "content_characters": len(content) if isinstance(content, str) else 0,
}, indent=2))
