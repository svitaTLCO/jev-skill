#!/usr/bin/env python3
"""
TypeSafe AI (Jev) Code Evaluator CLI

Evaluates code quality, regression risk, and specification compliance using
TypeSafe AI's System One model (Jev).
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

DEFAULT_API_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"

BUILTIN_MODES = {
    "review": {
        "maintainability": {
            "type": "score",
            "instructions": "Rate the maintainability, modularity, readability, and idiomatic quality of the code.",
            "criteria": [
                "Level 0 (Poor): Messy, convoluted, opaque variable names, tightly coupled, missing basic error handling.",
                "Level 1 (Needs Polish): Functional but fragile, inconsistent formatting, mixed levels of abstraction.",
                "Level 2 (Solid): Clean structure, meaningful names, good separation of concerns, idiomatic conventions.",
                "Level 3 (Exemplary): Production-grade excellence, highly cohesive, self-documenting, and robust error handling."
            ]
        },
        "satisfies_spec": {
            "type": "noul",
            "instructions": "Does the proposed code completely fulfill the explicit requirements and intent in the prompt/specification?"
        },
        "has_regression_risk": {
            "type": "noul",
            "instructions": "Does this implementation introduce risk of regressions, unhandled edge cases, or broken backward compatibility?"
        },
        "simplicity": {
            "type": "score",
            "instructions": "Evaluate the simplicity of the solution compared to the problem complexity.",
            "criteria": [
                "Overengineered: Premature abstraction, unnecessary design patterns or boilerplate.",
                "Balanced: Appropriate complexity and structure for the problem.",
                "Minimalist: Simple, clear, and elegant with no gratuitous complexity."
            ]
        }
    },
    "security": {
        "security_posture": {
            "type": "score",
            "instructions": "Rate the security quality and defenses of the code.",
            "criteria": [
                "Vulnerable: Direct injection risks, unvalidated user input, or hardcoded secrets.",
                "Questionable: Insufficient validation or missing sanitization on boundaries.",
                "Defensive: Explicit input validation, parameterized queries, and safe defaults.",
                "Hardened: Rigorous validation, principle of least privilege, and comprehensive defense in depth."
            ]
        },
        "has_vulnerability": {
            "type": "noul",
            "instructions": "Does the code introduce any obvious vulnerability (e.g. injection, auth bypass, unsanitized HTML/SQL)?"
        }
    },
    "plan": {
        "plan_soundness": {
            "type": "score",
            "instructions": "Rate the technical rigor, step sequencing, explicit file paths, and completeness of this implementation plan.",
            "criteria": [
                "Level 0 (Unsound): Vague hand-waving, missing file paths, no verification commands.",
                "Level 1 (Shallow): Basic outline, but leaves architectural choices ambiguous or lacks failure recovery.",
                "Level 2 (Solid): Clear step-by-step demarcations, explicit dependencies, concrete automated verification.",
                "Level 3 (Exemplary): Production-grade, zero-ambiguity, backwards-compatible with rigorous edge-case verification."
            ]
        },
        "is_overengineered": {
            "type": "noul",
            "instructions": "Does this plan introduce gratuitous complexity, unnecessary dependencies, premature abstractions, or heavy build tooling where simpler standard solutions suffice?"
        },
        "has_actionable_verification": {
            "type": "noul",
            "instructions": "Does the plan include concrete, automated verification commands or test scripts rather than vague manual checks?"
        },
        "covers_edge_cases": {
            "type": "noul",
            "instructions": "Does the plan explicitly address edge cases, failure states, and backward compatibility?"
        }
    },
    "prompt": {
        "architectural_direction": {
            "type": "choice",
            "instructions": "Select the optimal architectural pattern for the user requirement",
            "criteria": {
                "lightweight_standalone": "Zero/minimal external dependencies, self-contained single or dual file, rapid execution.",
                "modular_layered": "Strict separation of concerns into components/services with dedicated interfaces.",
                "heavy_framework": "Requires full framework boilerplate, build tooling, and package ecosystem."
            }
        },
        "scope_boundary": {
            "type": "choice",
            "instructions": "Select the appropriate scope boundary for this task",
            "criteria": {
                "focused_vertical_slice": "End-to-end working MVP with core happy path and critical edge cases.",
                "broad_comprehensive": "Full feature completeness across all potential user flows."
            }
        },
        "overengineering_risk": {
            "type": "noul",
            "instructions": "Is there a significant risk that the agent will overengineer this request with unnecessary abstractions?"
        },
        "has_underspecified_edge_cases": {
            "type": "noul",
            "instructions": "Are there critical missing constraints or ambiguous requirements in the prompt that must be clarified?"
        }
    }
}


def build_state(prompt: str, code: str, context: str = "") -> str:
    sections = []
    if prompt:
        sections.append(f"## Task / Requirements Specification\n{prompt.strip()}")
    if context:
        sections.append(f"## Codebase Context\n{context.strip()}")
    if code:
        sections.append(f"## Proposed Code / Changes\n```\n{code.strip()}\n```")
    return "\n\n".join(sections)


def call_typesafe_api(payload: dict, api_key: str, endpoint: str = DEFAULT_API_URL) -> dict:
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=req_data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "TypeSafe-Agent-Skill/1.0"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            return json.loads(resp_body)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TypeSafe API HTTP {e.code}: {err_msg}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to reach TypeSafe API: {e.reason}")


def format_markdown_report(result: dict) -> str:
    answers = result.get("answers", {})
    usage = result.get("usage", {})
    model = result.get("model", "unknown")

    lines = [
        f"### TypeSafe AI (Jev) Code Evaluation Report",
        f"- **Model**: `{model}`",
        f"- **Token Usage**: {usage.get('input_tokens', 0)} in / {usage.get('output_tokens', 0)} out",
        "",
        "| Dimension | Type | Result | Confidence / Detail |",
        "| :--- | :--- | :--- | :--- |"
    ]

    for qid, ans in answers.items():
        qtype = ans.get("type")
        if qtype == "score":
            score_val = ans.get("score")
            conf = ans.get("confidence", 0.0)
            lines.append(f"| `{qid}` | `Score` | **{score_val:.2f}** | Confidence: {conf:.2f} |")
        elif qtype == "noul":
            noul_val = ans.get("noul", 0.0)
            status = "⚠️ High Risk" if "risk" in qid and noul_val > 0.3 else "✅ Passed"
            lines.append(f"| `{qid}` | `Noul` | **{noul_val:.3f}** (P=Yes) | {status} |")
        elif qtype == "choice":
            choice_val = ans.get("choice")
            conf = ans.get("confidence", 0.0)
            lines.append(f"| `{qid}` | `Choice` | **`{choice_val}`** | Confidence: {conf:.2f} |")

    return "\n".join(lines)


def resolve_api_key(explicit_key: str = None) -> str:
    if explicit_key:
        return explicit_key
    env_key = os.environ.get("TYPESAFE_API_KEY")
    if env_key:
        return env_key
    # Check macOS Keychain
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


def main():
    parser = argparse.ArgumentParser(description="Evaluate code using TypeSafe AI (Jev).")
    parser.add_argument("--prompt", "-p", help="Task requirement or specification prompt.", default="")
    parser.add_argument("--file", "-f", help="Path to code file to evaluate.")
    parser.add_argument("--diff", "-d", help="Path to git diff or patch file.")
    parser.add_argument("--context", "-c", help="Additional context or existing file code.")
    parser.add_argument("--mode", "-m", choices=["review", "security", "plan", "prompt", "custom"], default="review")
    parser.add_argument("--questions-file", help="Path to JSON file containing custom questions.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="TypeSafe model identifier (default: jev-latest).")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of markdown.")
    parser.add_argument("--dry-run", action="store_true", help="Print request payload without making API call.")
    parser.add_argument("--api-key", help="TypeSafe API key (or set TYPESAFE_API_KEY env var).")

    args = parser.parse_args()

    # Read code
    code_content = ""
    if args.file:
        if not os.path.exists(args.file):
            sys.exit(f"Error: File not found: {args.file}")
        with open(args.file, "r", encoding="utf-8") as f:
            code_content = f.read()
    elif args.diff:
        if not os.path.exists(args.diff):
            sys.exit(f"Error: Diff file not found: {args.diff}")
        with open(args.diff, "r", encoding="utf-8") as f:
            code_content = f.read()
    elif not sys.stdin.isatty():
        code_content = sys.stdin.read()

    if not code_content and not args.prompt:
        sys.exit("Error: Must provide code via --file, --diff, stdin, or a prompt via --prompt.")

    # Determine questions
    if args.mode == "custom" or args.questions_file:
        if not args.questions_file:
            sys.exit("Error: --mode custom requires --questions-file <path>.")
        with open(args.questions_file, "r", encoding="utf-8") as f:
            questions = json.load(f)
    else:
        questions = BUILTIN_MODES[args.mode]

    state = build_state(args.prompt, code_content, args.context or "")

    payload = {
        "state": state,
        "model": args.model,
        "questions": questions
    }

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return

    api_key = resolve_api_key(args.api_key)
    if not api_key:
        sys.exit(
            "Error: Missing TypeSafe API key. Set TYPESAFE_API_KEY environment variable, "
            "store it in macOS Keychain (service: network-infra-typesafe-jev), "
            "or provide --api-key. (Get a key at https://console.typesafe.ai/keys)"
        )

    try:
        result = call_typesafe_api(payload, api_key)
    except Exception as e:
        sys.exit(f"API Call Failed: {e}")

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_markdown_report(result))


if __name__ == "__main__":
    main()
