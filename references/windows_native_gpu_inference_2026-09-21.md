# Windows-native GPU inference path — 2026-09-21

## Decision

Use a **Windows-native Ollama server with its Vulkan backend** for the local
worker. Keep the paired benchmark runner and its network-disabled candidate
sandbox in Docker/WSL. A Linux Docker Ollama container on this host cannot
reach the Windows Intel GPU reliably, while the native server can use the
installed Windows graphics driver.

This replaces the CPU-only `jev-local-ollama` service for performance
experiments. Do not run both servers on port `11434` at the same time.

## Hardware finding on this host

| Resource | Observed state | Consequence |
| --- | --- | --- |
| GPU | Intel Iris Xe (`PCI\\VEN_8086&DEV_9A49`), driver `32.0.101.7084` | Candidate for the Windows Vulkan backend. |
| Vulkan loader | `C:\\Windows\\System32\\vulkan-1.dll`, version `1.4.313.0` | Vulkan is installed at OS level; native Ollama can attempt GPU discovery. |
| NPU | No Windows `ComputeAccelerator` device; i7-1185G7 has no Intel AI Boost NPU | There is no general-purpose NPU path to configure. Its older GNA 2.0 is not a worker-model accelerator. |

The Iris Xe is an integrated GPU using shared system memory, not a discrete
VRAM device. It may run a small quantized model, but no speed claim is valid
until Ollama reports a Vulkan GPU load and the paired benchmark is repeated.

## One-time Windows setup

Install the current Windows Ollama release from <https://ollama.com/download>.
This is intentionally a Windows-native installation: Docker/WSL is retained
for every project operation, but cannot provide the required access to this
Windows GPU.

In a Windows PowerShell session, start Ollama with Vulkan explicitly enabled:

```powershell
$env:OLLAMA_VULKAN = "1"
ollama serve
```

In a second Windows PowerShell session, pull the exact research worker:

```powershell
ollama pull qwen3.5:2b
```

Keep the server bound to loopback; do not expose port `11434` on the LAN.

## Acceptance check before any experiment

Run a short no-think request and inspect the server log. The log must show a
Vulkan device/offload, rather than CPU-only loading:

```powershell
$body = @{ model = "qwen3.5:2b"; prompt = "Return only: ok"; stream = $false; think = $false } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:11434/api/generate -Method Post -ContentType application/json -Body $body
```

If Ollama falls back to CPU, stop: a Windows installation alone has not solved
the throughput problem. Capture the server discovery lines and update the
Intel graphics driver before retrying. Do not silently compare that fallback
against the Mac GPU results.

## Running the existing Docker benchmark against Windows Ollama

First stop the CPU-only container, so only the Windows service owns the port:

```bash
docker compose -f benchmarks/docker-compose.local-ollama.yml stop
```

The paired runner uses normal Docker bridge networking. It reaches the Windows
loopback service through `host.docker.internal`; do not enable
`network_mode: host`, because that WSL network namespace cannot reach Windows
`127.0.0.1`.

```bash
JEV_BENCHMARK_PROVIDER=ollama \
JEV_BENCHMARK_WORKER_URL=http://host.docker.internal:11434/api/generate \
JEV_BENCHMARK_MODEL=qwen3.5:2b \
JEV_BENCHMARK_SEED=1 \
JEV_GIT_REVISION="$(git rev-parse HEAD)" \
JEV_SANDBOX_HOST_DIR="$PWD/benchmark-runs/.sandbox" \
  docker compose -f benchmarks/docker-compose.paired.yml run --rm paired-benchmark
```

The runner records the endpoint and model identifier in its result. Before
using the result as evidence, record the Ollama startup log proving GPU
offload, and repeat matched direct/guided seeds as prescribed in the paired
study.

## Non-goals

- This host cannot use an NPU for Qwen worker inference: it has no exposed
  general-purpose NPU.
- Vulkan support is an enablement path, not a performance guarantee for a
  2.7 GB model on an integrated GPU.
- The benchmark Docker sandbox remains network-disabled; no change is made to
  its security boundary.

## Measured outcome (2026-09-22)

The acceptance check **passed**: Ollama v0.34.2 reported `Vulkan0` (Intel
Iris Xe) and loaded `qwen3.5:4b` with all 34 layers offloaded
(`OLLAMA_VULKAN=true`, no CPU fallback). Sustained generation on the broad
think-on demo task measured ~3.4 tok/s (probe: 4202 tokens in 20.6 minutes);
prompt evaluation ran at ~12 tok/s. See
[windows_gpu_ollama_race_2026-09-22.md](windows_gpu_ollama_race_2026-09-22.md)
for the full race evidence, including the direct/guided outcomes and the
instrumentation history that preceded them.
