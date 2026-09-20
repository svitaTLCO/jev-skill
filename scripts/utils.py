"""
Shared utilities for TypeSafe AI (Jev) scripts and benchmark runners.
"""

import os
import subprocess
import sys


def resolve_api_key(explicit_key: str = None) -> str:
    """
    Resolves the TypeSafe API Key in order of precedence:
    1. Explicit argument
    2. Environment variable TYPESAFE_API_KEY
    3. macOS Keychain (if on Darwin)
    """
    if explicit_key:
        return explicit_key

    env_key = os.environ.get("TYPESAFE_API_KEY")
    if env_key:
        return env_key

    if sys.platform == "darwin":
        services = ["network-infra-typesafe-jev", "typesafe-api-key", "typesafe", "jev"]
        for svc in services:
            try:
                res = subprocess.run(
                    ["security", "find-generic-password", "-s", svc, "-w"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except Exception:
                pass

    return None
