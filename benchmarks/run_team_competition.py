#!/usr/bin/env python3
"""
Driver for the Multi-Team Swarm + Jev Competition
Runs 4 competing teams on the identical task (Space Invaders Deluxe)
Each team runs the complete Swarm + Jev pipeline.
"""

import concurrent.futures
import json
import os
import sys
import time

sys.path.append(os.path.abspath("scripts"))
from multi_team_competition_engine import CompetitiveTeam, build_competition_leaderboard

TEAMS = [
    (1, "Alpha"),
    (2, "Beta"),
    (3, "Gamma"),
    (4, "Delta")
]

def main():
    print("=" * 80)
    print("🏆 MULTI-TEAM SWARM + JEV COMPETITION ARENA")
    print("   Task: Space Invaders Deluxe (Identical Specification)")
    print("   Infrastructure: Every Team runs 4-Agent Swarm + Jev Gates at every step")
    print("   Models: huihui-qwen3.5:2b + TypeSafe AI System One (Jev)")
    print("=" * 80)

    base_dir = "benchmarks/team_competition"
    os.makedirs(base_dir, exist_ok=True)
    t_global_start = time.perf_counter()

    pipelines = [CompetitiveTeam(tid, tname, base_dir) for tid, tname in TEAMS]

    print("\n[Phase 1: Concurrent Team Lifecycles]")
    results = []
    # Run 2 teams at a time to optimize M1 GPU memory & Ollama throughput
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(team.run_team_pipeline): team for team in pipelines}
        for f in concurrent.futures.as_completed(futures):
            team = futures[f]
            try:
                res = f.result()
                results.append(res)
            except Exception as e:
                print(f"   ❌ Team {team.team_id} ({team.team_name}) failed: {e}")

    results.sort(key=lambda x: x["team_id"])
    total_time = round(time.perf_counter() - t_global_start, 2)
    total_tokens = sum(r["total_tokens"] for r in results)

    # Phase 2: Build Leaderboard
    dash_path = build_competition_leaderboard(results, base_dir)

    sorted_results = sorted(results, key=lambda x: (x["final_noul"] >= 0.7, x["final_quality_score"]), reverse=True)
    winner = sorted_results[0]

    report = {
        "event": "Multi-Team Swarm + Jev Competition",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "task": "Space Invaders Deluxe",
        "total_wall_clock_s": total_time,
        "total_tokens": total_tokens,
        "winner": {
            "team_id": winner["team_id"],
            "team_name": winner["team_name"],
            "quality_score": winner["final_quality_score"],
            "playable_noul": winner["final_noul"]
        },
        "teams": results,
        "leaderboard_path": dash_path
    }

    report_path = os.path.join(base_dir, "competition_results.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print("🏆 FINAL COMPETITION RESULTS & PODIUM")
    print("=" * 80)
    for idx, t in enumerate(sorted_results):
        medal = "🥇" if idx == 0 else ("🥈" if idx == 1 else "🥉")
        print(f"{medal} Team {t['team_name']}: Jev Quality Score = {t['final_quality_score']}/3.0 | Playable Noul = {t['final_noul']} | Tokens: {t['total_tokens']}")

    print("\n" + "=" * 80)
    print(f"🎉 COMPETITION FINISHED IN {total_time}s | TOTAL TOKENS: {total_tokens}")
    print(f"   Grand Champion: Team {winner['team_name']} (Quality Score: {winner['final_quality_score']} / 3.0)")
    print(f"   Interactive Arena: http://localhost:8080/team_competition/leaderboard.html")
    print("=" * 80)

if __name__ == "__main__":
    main()
