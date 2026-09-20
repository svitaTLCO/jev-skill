#!/usr/bin/env python3
"""
Executable Runner for the 24-Agent Competitive Teams Hackathon
Runs 6 isolated teams (4 specialists each), gathers metrics, invokes Jev Jury,
and builds the interactive live leaderboard.
"""

import concurrent.futures
import json
import os
import sys
import time

# Add scripts directory to path
sys.path.append(os.path.abspath("scripts"))
from hackathon_swarm_engine import TeamPipeline, evaluate_teams_with_jev, build_hackathon_dashboard

TEAMS_SPEC = [
    (1, "Neon-Pulse", "Functional Reactive Architecture"),
    (2, "Cyber-Matrix", "Object-Oriented Component State"),
    (3, "Retro-Arcade", "Double-Buffered Classic Loop"),
    (4, "Vector-Viper", "Particle Physics & Vector Momentum"),
    (5, "Quantum-Core", "Grid-Array Micro-Entity Architecture"),
    (6, "Hyper-Drive", "Event-Driven Autonomous Pipeline")
]

def main():
    print("=" * 80)
    print("🏁 24-AGENT COMPETITIVE TEAMS HACKATHON ARENA")
    print("   Architecture: 6 Isolated Teams of 4 Agents (Architect, Engine, Renderer, QA)")
    print("   Target Model: huihui-qwen3.5:2b (Core) + huihui-qwen3.5:0.8b (QA/Repair)")
    print("   Supreme Jury: TypeSafe AI System One (Jev)")
    print("=" * 80)

    base_dir = "benchmarks/hackathon_swarm"
    os.makedirs(base_dir, exist_ok=True)
    t_start = time.perf_counter()

    pipelines = [
        TeamPipeline(tid, tname, theme, base_dir)
        for tid, tname, theme in TEAMS_SPEC
    ]

    print("\n[Phase 1: Concurrent Team Hackathon Execution]")
    # Run teams in parallel (max_workers=3 to balance CPU/GPU load smoothly on M1)
    team_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(p.execute_team_lifecycle): p for p in pipelines}
        for future in concurrent.futures.as_completed(futures):
            p = futures[future]
            try:
                res = future.result()
                team_results.append(res)
            except Exception as e:
                print(f"   ❌ Team {p.team_id} failed: {e}")

    team_results.sort(key=lambda x: x["team_id"])
    t_teams_wall = time.perf_counter() - t_start

    # Phase 2: TypeSafe Jev Supreme Hackathon Jury
    jury_scorecard, winner_team = evaluate_teams_with_jev(team_results)

    # Phase 3: Build Interactive Arena Dashboard
    dash_path = build_hackathon_dashboard(jury_scorecard, winner_team, base_dir)

    total_time = round(time.perf_counter() - t_start, 2)
    total_tokens = sum(t["tokens"] for t in team_results)
    pass_rate = sum(1 for t in team_results if t["syntax_valid"]) / len(team_results) * 100

    report = {
        "event": "24-Agent Competitive Teams Hackathon",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_wall_clock_s": total_time,
        "total_tokens": total_tokens,
        "pass_rate_percent": pass_rate,
        "grand_champion": {
            "team_id": winner_team["team_id"],
            "team_name": winner_team["team_name"],
            "theme": winner_team["theme"],
            "quality_score": winner_team["quality_score"],
            "noul_compliance": winner_team["noul_compliance"]
        },
        "scorecard": jury_scorecard,
        "dashboard_path": dash_path
    }

    results_file = os.path.join(base_dir, "hackathon_final_results.json")
    with open(results_file, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print(f"🎉 HACKATHON CONCLUDED IN {total_time}s | {total_tokens} TOKENS GENERATED")
    print(f"   Zero-Touch Syntax Pass Rate: {pass_rate:.1f}%")
    print(f"   Grand Champion: Team {winner_team['team_id']} ({winner_team['team_name']})")
    print(f"   Interactive Leaderboard URL: http://localhost:8080/hackathon_swarm/leaderboard.html")
    print("=" * 80)

if __name__ == "__main__":
    main()
