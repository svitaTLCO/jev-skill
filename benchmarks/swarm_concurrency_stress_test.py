#!/usr/bin/env python3
"""
Swarm Concurrency & Maximum Agent Capacity Stress Test
Hardware: Apple M1 (8 cores), 16GB Unified Memory, macOS Darwin
Evaluates maximum concurrent agent saturation for:
1. huihui-qwen3.5:0.8b
2. huihui-qwen3.5:2b
"""

import concurrent.futures
import json
import os
import subprocess
import sys
import time
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELS = [
    "huihui-qwen3.5:0.8b",
    "huihui-qwen3.5:2b"
]

CONCURRENCY_LEVELS = [1, 2, 4, 8, 12, 16, 24]

PROMPT = (
    "Task for agent specialist: Return a JSON object with keys "
    "'agent_id', 'vector_x', 'vector_y', 'status' for a particle with angle 45 and velocity 10. "
    "Output JSON only."
)

def get_ram_usage_mb():
    try:
        # Get resident memory of ollama and llama processes
        res = subprocess.run(
            ["ps", "-eo", "rss,comm"],
            capture_output=True, text=True
        )
        total_rss = 0
        for line in res.stdout.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and ("ollama" in parts[1].lower() or "llama" in parts[1].lower()):
                total_rss += int(parts[0])
        return total_rss / 1024.0  # MB
    except Exception:
        return 0.0

def single_agent_call(agent_id, model, timeout=120):
    t0 = time.perf_counter()
    payload = {
        "model": model,
        "prompt": f"<|im_start|>user\nAgent #{agent_id}: {PROMPT}<|im_end|>\n<|im_start|>assistant\n<think>\n",
        "options": {
            "num_predict": 120,
            "temperature": 0.1
        },
        "stream": False
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elapsed = time.perf_counter() - t0
        eval_count = data.get("eval_count", 0)
        return {
            "agent_id": agent_id,
            "success": True,
            "elapsed": elapsed,
            "tokens": eval_count,
            "error": None
        }
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return {
            "agent_id": agent_id,
            "success": False,
            "elapsed": elapsed,
            "tokens": 0,
            "error": str(e)
        }

def test_concurrency(model, num_agents):
    print(f"   -> Testing Swarm of {num_agents:2d} concurrent agents...", end="", flush=True)
    t_start = time.perf_counter()
    ram_before = get_ram_usage_mb()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_agents) as executor:
        futures = [executor.submit(single_agent_call, i, model) for i in range(num_agents)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    t_wall = time.perf_counter() - t_start
    ram_after = get_ram_usage_mb()

    successful = [r for r in results if r["success"]]
    total_tokens = sum(r["tokens"] for r in successful)
    latencies = [r["elapsed"] for r in successful]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0
    throughput = total_tokens / t_wall if t_wall > 0 else 0.0

    print(f" Completed in {t_wall:.2f}s | Success: {len(successful)}/{num_agents} | "
          f"Avg Lat: {avg_latency:.2f}s | P95: {p95_latency:.2f}s | Total Tok/s: {throughput:.1f} | RAM: {ram_after:.0f}MB")

    return {
        "num_agents": num_agents,
        "wall_clock_s": round(t_wall, 2),
        "success_rate": f"{len(successful)}/{num_agents}",
        "avg_latency_s": round(avg_latency, 2),
        "p95_latency_s": round(p95_latency, 2),
        "total_tokens": total_tokens,
        "throughput_tok_s": round(throughput, 2),
        "ram_mb": round(ram_after, 0)
    }

def main():
    print("=" * 80)
    print("🚀 OLLAMA SWARM CAPACITY & CONCURRENCY STRESS TEST")
    print("   Hardware: Apple M1 (8 cores), 16GB Unified Memory, macOS Darwin")
    print("   Models Evaluated: huihui-qwen3.5:0.8b and huihui-qwen3.5:2b")
    print("=" * 80)

    # Warmup
    print("\nWarming up Ollama engine...")
    single_agent_call(0, "huihui-qwen3.5:0.8b")
    single_agent_call(0, "huihui-qwen3.5:2b")

    all_results = {}

    for model in MODELS:
        print(f"\n{'='*60}")
        print(f"📊 STRESS TESTING MODEL: {model}")
        print(f"{'='*60}")
        model_results = []
        for n in CONCURRENCY_LEVELS:
            res = test_concurrency(model, n)
            model_results.append(res)
            # Give macOS memory manager a brief breath between bursts
            time.sleep(1.0)
        all_results[model] = model_results

    out_file = "benchmarks/swarm_capacity_benchmark.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 80)
    print("🏆 FINAL BENCHMARK SUMMARY")
    print("=" * 80)
    for model, results in all_results.items():
        print(f"\n### Model: {model}")
        print(f"| Agents | Wall Time | Success | Avg Latency | P95 Latency | Throughput | RAM |")
        print(f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in results:
            print(f"| {r['num_agents']:2d} | {r['wall_clock_s']:6.2f}s | {r['success_rate']:7s} | {r['avg_latency_s']:6.2f}s | {r['p95_latency_s']:6.2f}s | {r['throughput_tok_s']:5.1f} tok/s | {r['ram_mb']:5.0f}MB |")

if __name__ == "__main__":
    main()
