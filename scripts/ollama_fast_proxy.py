#!/usr/bin/env python3
"""
Ollama Fast Proxy for OpenCode & Coding Agents (Port 11435 -> 11434)
Enforces No-Think / reasoning_effort: "none" and optimal 32k context for Ollama /v1 endpoints.
Eliminates thinking delays (56s -> 0.3s) and prevents empty-thought stalls.

Usage:
  python3 scripts/ollama_fast_proxy.py                # Run in foreground on port 11435
  python3 scripts/ollama_fast_proxy.py 11436          # Run on custom port
  python3 scripts/ollama_fast_proxy.py --install-daemon   # Install as macOS LaunchAgent
  python3 scripts/ollama_fast_proxy.py --uninstall-daemon # Remove macOS LaunchAgent
  python3 scripts/ollama_fast_proxy.py --status           # Check proxy health
"""

import os
import sys
import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error

OLLAMA_UPSTREAM = os.environ.get("OLLAMA_UPSTREAM", "http://127.0.0.1:11434")
DEFAULT_PORT = 11435
PLIST_LABEL = "ai.typesafe.ollama-fast-proxy"

class FastProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Quiet logging to avoid polluting agent output
        pass

    def do_GET(self):
        url = f"{OLLAMA_UPSTREAM}{self.path}"
        headers = {k: v for k, v in self.headers.items() if k.lower() != 'host'}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if "/v1/chat/completions" in self.path:
            try:
                data = json.loads(body.decode("utf-8"))
                # Enforce no reasoning effort so small models don't stall in <think>
                data["reasoning_effort"] = "none"
                # Cap context to 32768 (prevent Ollama 65536 KV cache latency explosion)
                opts = data.setdefault("options", {})
                if not opts.get("num_ctx") or opts["num_ctx"] > 32768:
                    opts["num_ctx"] = 32768
                body = json.dumps(data).encode("utf-8")
            except Exception:
                pass

        url = f"{OLLAMA_UPSTREAM}{self.path}"
        headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "content-length")}
        headers["Content-Length"] = str(len(body))

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() != "transfer-encoding":
                        self.send_header(k, v)
                self.end_headers()

                # Stream response chunks to support SSE streaming
                while True:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except BrokenPipeError:
            pass
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

def install_daemon(port=DEFAULT_PORT):
    if sys.platform != "darwin":
        print("❌ Daemon installation via LaunchAgent is only supported on macOS (Darwin).")
        print("On Linux, run as a systemd service or background process:")
        print(f"  nohup {sys.executable} {os.path.abspath(__file__)} {port} > /dev/null 2>&1 &")
        sys.exit(1)

    home = os.path.expanduser("~")
    launch_agents_dir = os.path.join(home, "Library", "LaunchAgents")
    os.makedirs(launch_agents_dir, exist_ok=True)
    plist_path = os.path.join(launch_agents_dir, f"{PLIST_LABEL}.plist")
    script_path = os.path.abspath(__file__)
    python_path = sys.executable

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
        <string>{port}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/ollama_fast_proxy.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/ollama_fast_proxy.err</string>
</dict>
</plist>
"""
    with open(plist_path, "w") as f:
        f.write(plist_content)

    subprocess.run(["launchctl", "unload", plist_path], stderr=subprocess.DEVNULL)
    res = subprocess.run(["launchctl", "load", plist_path], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"✅ Successfully installed and started {PLIST_LABEL} on port {port}!")
        print(f"   Config: {plist_path}")
        print(f"   Upstream: {OLLAMA_UPSTREAM}")
    else:
        print(f"❌ Failed to load LaunchAgent: {res.stderr}")

def uninstall_daemon():
    if sys.platform != "darwin":
        print("❌ LaunchAgent uninstallation is only supported on macOS.")
        sys.exit(1)

    home = os.path.expanduser("~")
    plist_path = os.path.join(home, "Library", "LaunchAgents", f"{PLIST_LABEL}.plist")
    if os.path.exists(plist_path):
        subprocess.run(["launchctl", "unload", plist_path], stderr=subprocess.DEVNULL)
        os.remove(plist_path)
        print(f"✅ Successfully uninstalled {PLIST_LABEL}.")
    else:
        print(f"ℹ️  {plist_path} not found. Nothing to uninstall.")

def check_status(port=DEFAULT_PORT):
    url = f"http://127.0.0.1:{port}/v1/models"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("id") for m in data.get("data", [])]
            print(f"✅ Ollama Fast Proxy is ACTIVE on http://127.0.0.1:{port}")
            print(f"   Connected to upstream {OLLAMA_UPSTREAM}")
            print(f"   Available models: {', '.join(models) if models else 'None'}")
    except Exception as e:
        print(f"❌ Ollama Fast Proxy is NOT responding on http://127.0.0.1:{port}: {e}")

def main():
    args = sys.argv[1:]
    if "--install-daemon" in args or "--install" in args:
        port = DEFAULT_PORT
        for a in args:
            if a.isdigit():
                port = int(a)
        install_daemon(port)
        return
    elif "--uninstall-daemon" in args or "--uninstall" in args:
        uninstall_daemon()
        return
    elif "--status" in args:
        port = DEFAULT_PORT
        for a in args:
            if a.isdigit():
                port = int(a)
        check_status(port)
        return

    port = int(args[0]) if args and args[0].isdigit() else DEFAULT_PORT
    server = HTTPServer(("127.0.0.1", port), FastProxyHandler)
    print(f"🚀 [Ollama Fast Proxy] Listening on http://127.0.0.1:{port} -> {OLLAMA_UPSTREAM}")
    print("   Enforcing: reasoning_effort='none' | max num_ctx=32768")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping proxy.")

if __name__ == "__main__":
    main()
