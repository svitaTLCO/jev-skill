#!/usr/bin/env python3
"""
Tool-Calling Benchmark: Qwen 3.5 4B vs Llama 3 Groq Tool Use 8B
Evaluates whether Qwen 3.5 4B can match or outperform Llama 3 Groq Tool Use 8B
in tool execution, argument typing, negative abstention, parallel calls, and multi-turn state.

Metrics:
1. Accuracy (% tests passed)
2. Tool selection precision (avoiding distractors)
3. Argument validation (exact types, schemas, nested objects)
4. Negative abstention (zero false positives on conversational/math prompts)
5. Parallel tool calling (multi-call generation)
6. Stateful multi-turn context (follow-up execution)
7. Speed & Token Efficiency (Latency, Eval Count, Tokens/Sec)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.stdout.reconfigure(line_buffering=True)

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

# --- Common Tool Definitions for the Benchmark ---

TOOL_READ_FILE = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the contents of a file at the specified path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative path to the target file"}
            },
            "required": ["path"]
        }
    }
}

TOOL_WRITE_FILE = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Create a new file or overwrite an existing file with content.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {"type": "string", "description": "Content to write into the file"}
            },
            "required": ["path", "content"]
        }
    }
}

TOOL_EDIT_FILE = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Perform an exact string replacement in a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "old_str": {"type": "string", "description": "The exact substring to replace"},
                "new_str": {"type": "string", "description": "The replacement substring"}
            },
            "required": ["path", "old_str", "new_str"]
        }
    }
}

TOOL_RUN_BASH = {
    "type": "function",
    "function": {
        "name": "run_bash",
        "description": "Execute a shell command in the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command string to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds"},
                "background": {"type": "boolean", "description": "Whether to run in background"}
            },
            "required": ["command", "timeout", "background"]
        }
    }
}

TOOL_GREP_SEARCH = {
    "type": "function",
    "function": {
        "name": "grep_search",
        "description": "Search for exact pattern matches across files in a directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text or regex pattern to find"},
                "path": {"type": "string", "description": "Directory or file path to search inside"}
            },
            "required": ["query", "path"]
        }
    }
}

TOOL_LIST_DIR = {
    "type": "function",
    "function": {
        "name": "list_dir",
        "description": "List files and subdirectories inside a directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path"}
            },
            "required": ["path"]
        }
    }
}

TOOL_GIT_DIFF = {
    "type": "function",
    "function": {
        "name": "git_diff",
        "description": "Show changes between commits, commit and working tree, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "staged": {"type": "boolean", "description": "Show staged changes"}
            },
            "required": ["staged"]
        }
    }
}

TOOL_DEPLOY_SERVICE = {
    "type": "function",
    "function": {
        "name": "deploy_service",
        "description": "Deploy a containerized microservice to a target cluster environment.",
        "parameters": {
            "type": "object",
            "properties": {
                "environment": {
                    "type": "string",
                    "enum": ["development", "staging", "production"],
                    "description": "Target deployment tier"
                },
                "replicas": {"type": "integer", "description": "Number of replica instances"},
                "config": {
                    "type": "object",
                    "properties": {
                        "region": {"type": "string", "description": "Cloud region identifier"},
                        "memory_mb": {"type": "integer", "description": "Allocated memory in MB"}
                    },
                    "required": ["region", "memory_mb"]
                }
            },
            "required": ["environment", "replicas", "config"]
        }
    }
}

TOOL_GET_FILE_SIZE = {
    "type": "function",
    "function": {
        "name": "get_file_size",
        "description": "Get file size in bytes.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"}
            },
            "required": ["path"]
        }
    }
}

TOOL_CHECK_FILE_EXISTS = {
    "type": "function",
    "function": {
        "name": "check_file_exists",
        "description": "Check whether a given path exists on the filesystem.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to check"}
            },
            "required": ["path"]
        }
    }
}

TOOL_DOCKER_PS = {
    "type": "function",
    "function": {
        "name": "docker_ps",
        "description": "Inspect running or stopped docker containers.",
        "parameters": {
            "type": "object",
            "properties": {
                "filter": {"type": "string", "description": "Filter pattern for container name or status"}
            },
            "required": ["filter"]
        }
    }
}

TOOL_DOCKER_RESTART = {
    "type": "function",
    "function": {
        "name": "docker_restart",
        "description": "Restart a docker container with optional resource constraints.",
        "parameters": {
            "type": "object",
            "properties": {
                "container_id": {"type": "string", "description": "Container ID or name to restart"},
                "memory_limit": {"type": "string", "description": "Memory ceiling (e.g., '2g')"}
            },
            "required": ["container_id", "memory_limit"]
        }
    }
}

TOOL_BATCH_DELETE = {
    "type": "function",
    "function": {
        "name": "batch_delete_files",
        "description": "Delete multiple files simultaneously with safety flags.",
        "parameters": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths to remove"
                },
                "force": {"type": "boolean", "description": "Force deletion without prompt"},
                "dry_run": {"type": "boolean", "description": "Simulate deletion without deleting"}
            },
            "required": ["paths", "force", "dry_run"]
        }
    }
}

# --- Test Case Definitions ---

@dataclass
class TestCase:
    id: str
    name: str
    category: str
    tools: List[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    validator: Callable[[List[Dict[str, Any]], str], Tuple[bool, str]]

def make_test_cases() -> List[TestCase]:
    cases = []

    # 1. Simple Single-Arg Tool Call
    def validate_test_1(calls: List[Dict], content: str) -> Tuple[bool, str]:
        if not calls:
            return False, "No tool calls emitted"
        call = calls[0]
        name = call.get("function", {}).get("name")
        args = call.get("function", {}).get("arguments", {})
        if name != "read_file":
            return False, f"Expected 'read_file', got '{name}'"
        path = args.get("path", "")
        if path != "/workspace/src/index.ts":
            return False, f"Expected path '/workspace/src/index.ts', got '{path}'"
        return True, "Valid single-arg extraction"

    cases.append(TestCase(
        id="T01_read_file_single_arg",
        name="Single Argument Extraction",
        category="Basic Execution",
        tools=[TOOL_READ_FILE],
        messages=[{"role": "user", "content": "Please view the file at /workspace/src/index.ts"}],
        validator=validate_test_1
    ))

    # 2. Multi-Typed Arguments (str, int, bool)
    def validate_test_2(calls: List[Dict], content: str) -> Tuple[bool, str]:
        if not calls:
            return False, "No tool calls emitted"
        call = calls[0]
        name = call.get("function", {}).get("name")
        args = call.get("function", {}).get("arguments", {})
        if name != "run_bash":
            return False, f"Expected 'run_bash', got '{name}'"
        cmd = args.get("command", "")
        if "npm test -- --coverage" not in cmd:
            return False, f"Expected command containing 'npm test -- --coverage', got '{cmd}'"
        timeout = args.get("timeout")
        if timeout != 45:
            return False, f"Expected integer timeout 45, got {timeout} (type: {type(timeout)})"
        bg = args.get("background")
        if bg is not False:
            return False, f"Expected boolean background False, got {bg} (type: {type(bg)})"
        return True, "Valid multi-type argument extraction (str, int, bool)"

    cases.append(TestCase(
        id="T02_bash_multi_typed",
        name="Multi-Type Arguments (str, int, bool)",
        category="Argument Types",
        tools=[TOOL_RUN_BASH],
        messages=[{"role": "user", "content": "Execute `npm test -- --coverage` with a 45 second timeout without putting it in the background."}],
        validator=validate_test_2
    ))

    # 3. Disambiguation Among Multiple Distractors
    def validate_test_3(calls: List[Dict], content: str) -> Tuple[bool, str]:
        if not calls:
            return False, "No tool calls emitted"
        call = calls[0]
        name = call.get("function", {}).get("name")
        args = call.get("function", {}).get("arguments", {})
        if name != "grep_search":
            return False, f"Model picked distractor '{name}' instead of 'grep_search'"
        q = args.get("query", "")
        p = args.get("path", "")
        if "calculate_hash" not in q:
            return False, f"Expected query 'calculate_hash', got '{q}'"
        if "src" not in p:
            return False, f"Expected path containing 'src', got '{p}'"
        return True, "Correctly selected grep_search among 5 distractors"

    cases.append(TestCase(
        id="T03_distractor_selection",
        name="Tool Selection Among Distractors",
        category="Disambiguation",
        tools=[TOOL_READ_FILE, TOOL_WRITE_FILE, TOOL_LIST_DIR, TOOL_GREP_SEARCH, TOOL_GIT_DIFF],
        messages=[{"role": "user", "content": "Search for all occurrences of the function `calculate_hash` inside the 'src/' directory."}],
        validator=validate_test_3
    ))

    # 4. Complex Schema: Enum + Nested Dictionary + Int
    def validate_test_4(calls: List[Dict], content: str) -> Tuple[bool, str]:
        if not calls:
            return False, "No tool calls emitted"
        call = calls[0]
        name = call.get("function", {}).get("name")
        args = call.get("function", {}).get("arguments", {})
        if name != "deploy_service":
            return False, f"Expected 'deploy_service', got '{name}'"
        env = args.get("environment")
        if env != "production":
            return False, f"Expected enum 'production', got '{env}'"
        replicas = args.get("replicas")
        if replicas != 5:
            return False, f"Expected replicas 5, got {replicas}"
        cfg = args.get("config", {})
        if not isinstance(cfg, dict):
            return False, f"Expected nested dict config, got {type(cfg)}"
        if cfg.get("region") != "eu-central-1":
            return False, f"Expected region 'eu-central-1', got '{cfg.get('region')}'"
        if cfg.get("memory_mb") != 1024:
            return False, f"Expected memory_mb 1024, got {cfg.get('memory_mb')}"
        return True, "Valid enum, nested object, and typed ints"

    cases.append(TestCase(
        id="T04_complex_schema_enums_and_nested",
        name="Enums and Nested Object Schema",
        category="Complex Schema",
        tools=[TOOL_DEPLOY_SERVICE],
        messages=[{"role": "user", "content": "Deploy the service to production with 5 replicas, in region 'eu-central-1' and 1024 MB of memory."}],
        validator=validate_test_4
    ))

    # 5. Exact Code Patching (edit_file)
    def validate_test_5(calls: List[Dict], content: str) -> Tuple[bool, str]:
        if not calls:
            return False, "No tool calls emitted"
        call = calls[0]
        name = call.get("function", {}).get("name")
        args = call.get("function", {}).get("arguments", {})
        if name != "edit_file":
            return False, f"Expected 'edit_file', got '{name}'"
        p = args.get("path", "")
        old_s = args.get("old_str", "")
        new_s = args.get("new_str", "")
        if "app.py" not in p:
            return False, f"Expected path 'src/app.py', got '{p}'"
        if "PORT = 3000" not in old_s:
            return False, f"Expected old_str 'PORT = 3000', got '{old_s}'"
        if "PORT = 8080" not in new_s:
            return False, f"Expected new_str 'PORT = 8080', got '{new_s}'"
        return True, "Exact substring replacement parameters preserved"

    cases.append(TestCase(
        id="T05_edit_file_exact_code",
        name="Code Patching Substring Precision",
        category="Code Specialist",
        tools=[TOOL_EDIT_FILE, TOOL_WRITE_FILE, TOOL_READ_FILE],
        messages=[{"role": "user", "content": "In 'src/app.py', replace `PORT = 3000` with `PORT = 8080`."}],
        validator=validate_test_5
    ))

    # 6. Negative Abstention: Conversational Question (Zero False Positives)
    def validate_test_6(calls: List[Dict], content: str) -> Tuple[bool, str]:
        if calls:
            call_names = [c.get("function", {}).get("name") for c in calls]
            return False, f"Hallucinated tool call: {call_names} when pure text explanation requested"
        if not content or len(content.strip()) < 10:
            return False, "Failed to provide conversational explanation"
        return True, "Zero false positives: refrained from tool call and answered directly"

    cases.append(TestCase(
        id="T06_abstention_conversational",
        name="Zero False Positives (Abstention)",
        category="Negative Abstention",
        tools=[TOOL_READ_FILE, TOOL_WRITE_FILE, TOOL_RUN_BASH],
        messages=[{"role": "user", "content": "What is an architectural invariant in software design? Explain clearly in one sentence without using any tools."}],
        validator=validate_test_6
    ))

    # 7. Negative Abstention: In-Context Calculation
    def validate_test_7(calls: List[Dict], content: str) -> Tuple[bool, str]:
        if calls:
            call_names = [c.get("function", {}).get("name") for c in calls]
            return False, f"Hallucinated tool call: {call_names} for simple mental calculation"
        if "600" not in content:
            return False, f"Missing expected answer '600' in response: '{content}'"
        return True, "Zero false positives: answered calculation directly without tools"

    cases.append(TestCase(
        id="T07_abstention_mental_math",
        name="Direct Reasoning Without Tools",
        category="Negative Abstention",
        tools=[TOOL_RUN_BASH, TOOL_READ_FILE],
        messages=[{"role": "user", "content": "If a microservice handles 200 requests per second, how many requests does it handle in 3 seconds? Give the answer directly in plain text without tools."}],
        validator=validate_test_7
    ))

    # 8. Parallel Tool Calling (Calling multiple tools simultaneously)
    def validate_test_8(calls: List[Dict], content: str) -> Tuple[bool, str]:
        if len(calls) < 2:
            return False, f"Expected 2 parallel tool calls, got {len(calls)}"
        paths = []
        for c in calls:
            name = c.get("function", {}).get("name")
            if name != "get_file_size":
                return False, f"Expected 'get_file_size', got '{name}'"
            paths.append(c.get("function", {}).get("arguments", {}).get("path", ""))
        
        has_pkg = any("package.json" in p for p in paths)
        has_tsc = any("tsconfig.json" in p for p in paths)
        if not (has_pkg and has_tsc):
            return False, f"Missing expected paths in parallel calls: {paths}"
        return True, f"Successfully emitted 2 parallel tool calls: {paths}"

    cases.append(TestCase(
        id="T08_parallel_tool_calling",
        name="Parallel Tool Execution (2 Calls)",
        category="Parallel Execution",
        tools=[TOOL_GET_FILE_SIZE, TOOL_CHECK_FILE_EXISTS],
        messages=[{"role": "user", "content": "Get the file size of 'package.json' and also get the file size of 'tsconfig.json' simultaneously."}],
        validator=validate_test_8
    ))

    # 9. Stateful Multi-Turn Context (Tool Output in Prior Turn)
    def validate_test_9(calls: List[Dict], content: str) -> Tuple[bool, str]:
        if not calls:
            return False, "No tool calls emitted"
        call = calls[0]
        name = call.get("function", {}).get("name")
        args = call.get("function", {}).get("arguments", {})
        if name != "docker_restart":
            return False, f"Expected 'docker_restart', got '{name}'"
        cid = args.get("container_id", "")
        mem = args.get("memory_limit", "")
        if "c1a2b3" not in cid:
            return False, f"Expected container_id 'c1a2b3' from turn history, got '{cid}'"
        if "2g" not in mem:
            return False, f"Expected memory_limit '2g', got '{mem}'"
        return True, "Successfully used prior turn tool output context"

    cases.append(TestCase(
        id="T09_multi_turn_stateful",
        name="Multi-Turn Stateful Recovery",
        category="Stateful History",
        tools=[TOOL_DOCKER_PS, TOOL_DOCKER_RESTART],
        messages=[
            {"role": "user", "content": "Please check if container 'redis-prod' is running."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_inspect_1",
                        "function": {
                            "name": "docker_ps",
                            "arguments": {"filter": "redis-prod"}
                        }
                    }
                ]
            },
            {
                "role": "tool",
                "tool_call_id": "call_inspect_1",
                "content": json.dumps({"status": "exited", "exit_code": 137, "container_id": "c1a2b3"})
            },
            {"role": "user", "content": "Since container 'c1a2b3' crashed with code 137 (OOM), restart it with memory limit increased to '2g'."}
        ],
        validator=validate_test_9
    ))

    # 10. Array of Strings & Boolean Filters
    def validate_test_10(calls: List[Dict], content: str) -> Tuple[bool, str]:
        if not calls:
            return False, "No tool calls emitted"
        call = calls[0]
        name = call.get("function", {}).get("name")
        args = call.get("function", {}).get("arguments", {})
        if name != "batch_delete_files":
            return False, f"Expected 'batch_delete_files', got '{name}'"
        paths = args.get("paths", [])
        if not isinstance(paths, list) or len(paths) != 3:
            return False, f"Expected array of 3 paths, got {paths}"
        expected_paths = ["temp/cache1.tmp", "temp/cache2.tmp", "temp/cache3.tmp"]
        if sorted(paths) != sorted(expected_paths):
            return False, f"Expected {expected_paths}, got {paths}"
        force = args.get("force")
        dry_run = args.get("dry_run")
        if force is not True:
            return False, f"Expected force=True, got {force}"
        if dry_run is not True:
            return False, f"Expected dry_run=True, got {dry_run}"
        return True, "Valid array of strings and boolean flags"

    cases.append(TestCase(
        id="T10_array_and_boolean_filters",
        name="Array of Strings & Boolean Flags",
        category="Complex Schema",
        tools=[TOOL_BATCH_DELETE],
        messages=[{"role": "user", "content": "Perform a dry run to delete the temporary cache files: 'temp/cache1.tmp', 'temp/cache2.tmp', and 'temp/cache3.tmp' with force enabled."}],
        validator=validate_test_10
    ))

    return cases


# --- API Query Engine ---

def query_ollama_chat(
    model: str,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    think: bool = False,
    temperature: float = 0.1,
    timeout: int = 60
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "think": think,
        "options": {
            "temperature": temperature,
            "num_predict": 1024
        },
        "stream": False
    }
    if tools:
        payload["tools"] = tools

    t0 = time.perf_counter()
    req = urllib.request.Request(
        DEFAULT_OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            t1 = time.perf_counter()
            raw_data = json.loads(response.read().decode("utf-8"))
            latency = t1 - t0
            
            message = raw_data.get("message", {})
            content = message.get("content", "")
            thinking = message.get("thinking", "")
            tool_calls = message.get("tool_calls", [])
            eval_count = raw_data.get("eval_count", 0)
            eval_duration_ns = raw_data.get("eval_duration", 0)
            
            tokens_per_sec = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else (eval_count / latency if latency > 0 else 0)

            return {
                "success": True,
                "latency_s": latency,
                "content": content,
                "thinking": thinking,
                "tool_calls": tool_calls,
                "eval_count": eval_count,
                "tokens_per_sec": tokens_per_sec,
                "raw": raw_data
            }
    except Exception as e:
        t1 = time.perf_counter()
        return {
            "success": False,
            "latency_s": t1 - t0,
            "error": str(e),
            "content": "",
            "tool_calls": [],
            "eval_count": 0,
            "tokens_per_sec": 0
        }


# --- Benchmark Runner ---

@dataclass
class ModelResult:
    model_key: str
    display_name: str
    passed_count: int = 0
    total_count: int = 0
    total_latency: float = 0.0
    total_tokens: int = 0
    test_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

def run_benchmark(
    configurations: List[Tuple[str, str, bool]],  # (model_name, display_name, think_flag)
    verbose: bool = True
) -> Dict[str, ModelResult]:
    cases = make_test_cases()
    results: Dict[str, ModelResult] = {}

    for model_name, display_name, think_flag in configurations:
        config_key = f"{model_name}{' (think=True)' if think_flag else ''}"
        results[config_key] = ModelResult(model_key=config_key, display_name=display_name, total_count=len(cases))

    print("=" * 88)
    print("🚀 STARTING TOOL-CALLING BENCHMARK: QWEN 3.5 4B vs LLAMA 3 GROQ TOOL USE 8B")
    print(f"📊 Evaluated Test Scenarios: {len(cases)}")
    print(f"🎯 Target Models: {[c[1] for c in configurations]}")
    print("=" * 88)

    for i, case in enumerate(cases, 1):
        print(f"\n[{i}/{len(cases)}] Running Test: {case.name} ({case.category})")
        print(f"     Prompt: {case.messages[-1].get('content')[:75]}...")

        for model_name, display_name, think_flag in configurations:
            config_key = f"{model_name}{' (think=True)' if think_flag else ''}"
            res = query_ollama_chat(
                model=model_name,
                messages=case.messages,
                tools=case.tools,
                think=think_flag
            )

            if not res["success"]:
                passed = False
                reason = f"Ollama API Error: {res.get('error')}"
            else:
                passed, reason = case.validator(res["tool_calls"], res["content"])

            results[config_key].test_results[case.id] = {
                "passed": passed,
                "reason": reason,
                "latency_s": res["latency_s"],
                "eval_count": res["eval_count"],
                "tokens_per_sec": res["tokens_per_sec"],
                "tool_calls": res["tool_calls"],
                "content_preview": (res["content"] or "")[:60].replace("\n", " ")
            }

            if passed:
                results[config_key].passed_count += 1
            results[config_key].total_latency += res["latency_s"]
            results[config_key].total_tokens += res["eval_count"]

            status_icon = "✅ PASS" if passed else "❌ FAIL"
            print(f"     [{display_name:30}] {status_icon:8} | {res['latency_s']:5.2f}s | {res['eval_count']:3d} tok | {reason}")

    return results


def print_summary_table(results: Dict[str, ModelResult], output_file: Optional[str] = None):
    headers = ["Model / Configuration", "Pass Rate", "Accuracy", "Avg Latency", "Total Tokens", "Speed (t/s)"]
    rows = []
    
    for key, mr in results.items():
        acc = (mr.passed_count / mr.total_count * 100) if mr.total_count > 0 else 0
        avg_lat = (mr.total_latency / mr.total_count) if mr.total_count > 0 else 0
        avg_speed = (mr.total_tokens / mr.total_latency) if mr.total_latency > 0 else 0
        rows.append([
            mr.display_name,
            f"{mr.passed_count}/{mr.total_count}",
            f"{acc:5.1f}%",
            f"{avg_lat:5.2f}s",
            f"{mr.total_tokens:5d}",
            f"{avg_speed:5.1f}"
        ])

    print("\n" + "=" * 88)
    print("🏆 FINAL BENCHMARK COMPARISON TABLE")
    print("=" * 88)
    print(f"{headers[0]:34} | {headers[1]:10} | {headers[2]:9} | {headers[3]:11} | {headers[4]:12} | {headers[5]:11}")
    print("-" * 98)
    for r in rows:
        print(f"{r[0]:34} | {r[1]:10} | {r[2]:9} | {r[3]:11} | {r[4]:12} | {r[5]:11}")
    print("=" * 88)

    # Detailed Category Analysis
    cases = make_test_cases()
    print("\n📋 DETAILED TEST BREAKDOWN:")
    for case in cases:
        print(f"\n• {case.name} [{case.category}]:")
        for key, mr in results.items():
            tr = mr.test_results.get(case.id, {})
            icon = "✅" if tr.get("passed") else "❌"
            lat = tr.get("latency_s", 0)
            tok = tr.get("eval_count", 0)
            reason = tr.get("reason", "")
            print(f"    - {mr.display_name:30}: {icon} ({lat:4.2f}s, {tok:3d} tok) -> {reason}")

    if output_file:
        export_data = {}
        for key, mr in results.items():
            export_data[key] = {
                "display_name": mr.display_name,
                "passed_count": mr.passed_count,
                "total_count": mr.total_count,
                "accuracy_percent": round(mr.passed_count / mr.total_count * 100, 1),
                "total_latency_s": round(mr.total_latency, 2),
                "avg_latency_s": round(mr.total_latency / mr.total_count, 2),
                "total_tokens": mr.total_tokens,
                "tests": mr.test_results
            }
        with open(output_file, "w") as f:
            json.dump(export_data, f, indent=2)
        print(f"\n💾 Saved full JSON results to: {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Tool Calling Benchmark: Qwen 3.5 4B vs Llama 3 Groq Tool Use 8B")
    parser.add_argument("--include-2b", action="store_true", help="Include qwen3.5:2b as baseline comparison")
    parser.add_argument("--output", type=str, default="benchmarks/tool_calling_results.json", help="Path to save JSON benchmark output")
    args = parser.parse_args()

    configurations = [
        ("qwen3.5:4b", "Qwen 3.5 4B (No-Think)", False),
        ("llama3-groq-tool-use:8b", "Llama 3 Groq Tool Use 8B", False),
        ("qwen3.5:4b", "Qwen 3.5 4B (With Think)", True)
    ]

    if args.include_2b:
        configurations.insert(0, ("qwen3.5:2b", "Qwen 3.5 2B (Agile Baseline)", False))

    results = run_benchmark(configurations)
    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
    print_summary_table(results, output_file=args.output)


if __name__ == "__main__":
    main()
