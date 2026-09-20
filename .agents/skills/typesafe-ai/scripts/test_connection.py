#!/usr/bin/env python3
"""
Test connection to TypeSafe AI (Jev) API.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

ENDPOINT = "https://api.typesafe.ai/v1/systemone"

def resolve_api_key() -> str:
    env_key = os.environ.get("TYPESAFE_API_KEY")
    if env_key:
        return env_key
    if sys.platform == "darwin":
        services = ["network-infra-typesafe-jev", "typesafe-api-key", "typesafe", "jev"]
        import subprocess
        for svc in services:
            try:
                res = subprocess.run(
                    ["security", "find-generic-password", "-s", svc, "-w"],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except Exception:
                pass
    return None

def test_connection():
    api_key = resolve_api_key()
    if not api_key:
        print("❌ Error: TYPESAFE_API_KEY not found in environment or macOS Keychain.")
        print("Please export TYPESAFE_API_KEY=\"<your-key>\"")
        print("Obtain a key at https://console.typesafe.ai/keys")
        sys.exit(1)

    payload = {
        "state": "The quick brown fox jumps over the lazy dog.",
        "model": "jev-latest",
        "questions": {
            "is_english": {
                "type": "noul",
                "instructions": "Is this text written in the English language?"
            }
        }
    }

    print(f"Connecting to TypeSafe API ({ENDPOINT})...")
    start_time = time.time()

    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "TypeSafe-Agent-Skill/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            elapsed = (time.time() - start_time) * 1000
            data = json.loads(resp.read().decode("utf-8"))
            print("✅ Connection successful!")
            print(f"- Latency: {elapsed:.1f}ms")
            print(f"- Model: {data.get('model')}")
            print(f"- Response: {json.dumps(data.get('answers'), indent=2)}")
            print(f"- Tokens: {data.get('usage')}")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"❌ HTTP Error {e.code}: {err}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"❌ Connection Error: {e.reason}")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()
