#!/usr/bin/env python3
"""Run a full 24-round game with AI recommendations applied at every step.

Compares AI-guided play against the actual physical board-game baseline
(without IDSS). No running server needed — calls the engine and recommender
directly.

Usage:
    cd backend
    ./venv/bin/python scripts/run_full_game.py [--seed SEED] [--quiet] [--csv PREFIX]
"""

import sys
import os
import argparse
import csv
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.enums import StepType, DepartmentId
from models.actions import ArrivalsAction, ExitsAction, ClosedAction, StaffingAction
from models.game_state import GameState
from engine.game_engine import (
    create_game,
    process_event_step,
    process_arrivals_step,
    process_exits_step,
    process_closed_step,
    process_staffing_step,
    process_paperwork_step,
)
from agent.recommender import Recommender


DEPT_LABELS = {
    DepartmentId.ER: "ER",
    DepartmentId.SURGERY: "Surg",
    DepartmentId.CRITICAL_CARE: "CC",
    DepartmentId.STEP_DOWN: "SD",
}

# Actual baseline from physical board game (without IDSS)
PHYSICAL_BASELINE = {
    "Emergency":     {"financial": 101_850, "quality": 6_065},
    "Surgery":       {"financial":  24_380, "quality":   475},
    "Critical Care": {"financial":  26_140, "quality":   975},
    "Step-Down":     {"financial":   6_830, "quality": 2_085},
}
PHYSICAL_BASELINE_TOTAL = {
    "financial": 159_200,
    "quality": 9_600,
}

# Detail key prefixes per department (for aggregating from round_costs.details)
DEPT_DETAIL_KEYS = {
    "Emergency": {
        "waiting_fin": ["er_patients_waiting_fin"],
        "waiting_qual": ["er_patients_waiting_qual"],
        "extra_fin": ["er_extra_staff_fin"],
        "extra_qual": ["er_extra_staff_qual"],
        "diversion_fin": ["er_diversion_fin"],
        "diversion_qual": ["er_diversion_qual"],
    },
    "Surgery": {
        "waiting_fin": ["surgery_arrivals_waiting_fin", "surgery_requests_waiting_fin"],
        "waiting_qual": ["surgery_arrivals_waiting_qual", "surgery_requests_waiting_qual"],
        "extra_fin": ["surgery_extra_staff_fin"],
        "extra_qual": ["surgery_extra_staff_qual"],
    },
    "Critical Care": {
        "waiting_fin": ["cc_arrivals_waiting_fin", "cc_requests_waiting_fin"],
        "waiting_qual": ["cc_arrivals_waiting_qual", "cc_requests_waiting_qual"],
        "extra_fin": ["cc_extra_staff_fin"],
        "extra_qual": ["cc_extra_staff_qual"],
    },
    "Step-Down": {
        "waiting_fin": ["sd_arrivals_waiting_fin", "sd_requests_waiting_fin"],
        "waiting_qual": ["sd_arrivals_waiting_qual", "sd_requests_waiting_qual"],
        "extra_fin": ["sd_extra_staff_fin"],
        "extra_qual": ["sd_extra_staff_qual"],
    },
}


def aggregate_dept_costs(state: GameState) -> dict:
    """Aggregate cost details by department across all rounds."""
    totals = {}
    for dept_name, keys in DEPT_DETAIL_KEYS.items():
        waiting_fin = 0
        waiting_qual = 0
        extra_fin = 0
        extra_qual = 0
        diversion_fin = 0
        diversion_qual = 0

        for rc in state.round_costs:
            for k in keys.get("waiting_fin", []):
                waiting_fin += rc.details.get(k, 0)
            for k in keys.get("waiting_qual", []):
                waiting_qual += rc.details.get(k, 0)
            for k in keys.get("extra_fin", []):
                extra_fin += rc.details.get(k, 0)
            for k in keys.get("extra_qual", []):
                extra_qual += rc.details.get(k, 0)
            for k in keys.get("diversion_fin", []):
                diversion_fin += rc.details.get(k, 0)
            for k in keys.get("diversion_qual", []):
                diversion_qual += rc.details.get(k, 0)

        total_fin = waiting_fin + extra_fin + diversion_fin
        total_qual = waiting_qual + extra_qual + diversion_qual

        totals[dept_name] = {
            "waiting_fin": waiting_fin,
            "waiting_qual": waiting_qual,
            "extra_fin": extra_fin,
            "extra_qual": extra_qual,
            "diversion_fin": diversion_fin,
            "diversion_qual": diversion_qual,
            "total_fin": total_fin,
            "total_qual": total_qual,
            "total": total_fin + total_qual,
        }

    return totals


def print_dept_table(label: str, dept_costs: dict) -> None:
    """Print per-department Financial / Quality table (matching presentation format)."""
    print(f"\n  {label}")
    print(f"  {'Department':<16} {'Financial Cost':>16} {'Quality Cost':>14}")
    print(f"  {'-'*16} {'-'*16} {'-'*14}")

    total_fin = 0
    total_qual = 0
    for dept_name, costs in dept_costs.items():
        fin = costs["total_fin"]
        qual = costs["total_qual"]
        total_fin += fin
        total_qual += qual
        print(f"  {dept_name:<16} ${fin:>14,} {qual:>13,}")

    print(f"  {'-'*16} {'-'*16} {'-'*14}")
    print(f"  {'Total':<16} ${total_fin:>14,} {total_qual:>13,}")


def print_dept_breakdown(label: str, dept_costs: dict) -> None:
    """Print detailed per-department cost breakdown."""
    print(f"\n  {label} — Cost Breakdown by Category")
    print(f"  {'Department':<16} {'Waiting':>14} {'Extra Staff':>14} {'Diversion':>14} {'Total':>14}")
    print(f"  {'-'*16} {'-'*14} {'-'*14} {'-'*14} {'-'*14}")

    grand_total = 0
    for dept_name, costs in dept_costs.items():
        waiting = costs["waiting_fin"] + costs["waiting_qual"]
        extra = costs["extra_fin"] + costs["extra_qual"]
        diversion = costs["diversion_fin"] + costs["diversion_qual"]
        total = costs["total"]
        grand_total += total
        div_str = f"${diversion:>12,}" if diversion > 0 else f"{'—':>13}"
        print(
            f"  {dept_name:<16} ${waiting:>12,} ${extra:>12,} {div_str} ${total:>12,}"
        )

    print(f"  {'-'*16} {'-'*14} {'-'*14} {'-'*14} {'-'*14}")
    print(f"  {'TOTAL':<16} {'':>14} {'':>14} {'':>14} ${grand_total:>12,}")


def run_game(seed: int, quiet: bool, recommender: Recommender) -> dict:
    """Run a full 24-round AI-guided game."""
    state = create_game("ai-game")
    start_time = time.time()

    if not quiet:
        print("=" * 80)
        print("  AI-GUIDED GAME (With IDSS) — 24 Rounds")
        print(f"  LLM available: {recommender._llm.is_available()}")
        print("=" * 80)
        print()

    for round_num in range(1, 25):
        round_start = time.time()

        # Step 0: Events
        state = process_event_step(state, event_seed=seed + round_num)

        # Steps 1-4: AI recommendations
        for step_type, action_cls in [
            (StepType.ARRIVALS, ArrivalsAction),
            (StepType.EXITS, ExitsAction),
            (StepType.CLOSED, ClosedAction),
            (StepType.STAFFING, StaffingAction),
        ]:
            rec = recommender.recommend(state, step_type, horizon=6, mc_simulations=50)
            try:
                action = action_cls(**rec.recommended_action)
            except Exception:
                action = action_cls()

            step_fn = {
                StepType.ARRIVALS: process_arrivals_step,
                StepType.EXITS: process_exits_step,
                StepType.CLOSED: process_closed_step,
                StepType.STAFFING: process_staffing_step,
            }[step_type]

            try:
                state = step_fn(state, action)
            except Exception:
                state = step_fn(state, action_cls())

        # Step 5: Paperwork
        state = process_paperwork_step(state)

        round_cost = state.round_costs[-1]
        elapsed = time.time() - round_start

        if not quiet:
            dept_info = []
            for did, label in DEPT_LABELS.items():
                d = state.departments[did]
                dept_info.append(
                    f"{label}: {d.total_patients}p/{d.staff.total_on_duty}s"
                    f"({'C' if d.is_closed else 'O'})"
                )
            dept_str = "  ".join(dept_info)

            print(
                f"  Round {round_num:2d}  "
                f"Fin: ${round_cost.financial:>7,}  "
                f"Qual: ${round_cost.quality:>5,}  "
                f"| {dept_str}  ({elapsed:.1f}s)"
            )

    total_time = time.time() - start_time
    dept_costs = aggregate_dept_costs(state)

    if not quiet:
        print()
        print("-" * 80)
        print(f"  FINAL SCORE (With IDSS)")
        print(f"    Financial: ${state.total_financial_cost:>10,}")
        print(f"    Quality:   ${state.total_quality_cost:>10,}")
        print(f"    Combined:  ${state.total_financial_cost + state.total_quality_cost:>10,}")
        print(f"    Time:      {total_time:.1f}s")
        print("-" * 80)

        print_dept_table("With IDSS", dept_costs)
        print_dept_breakdown("With IDSS", dept_costs)

    return {
        "financial": state.total_financial_cost,
        "quality": state.total_quality_cost,
        "combined": state.total_financial_cost + state.total_quality_cost,
        "round_costs": [(rc.financial, rc.quality) for rc in state.round_costs],
        "dept_costs": dept_costs,
        "time": total_time,
    }


def print_comparison(ai: dict) -> None:
    """Print side-by-side comparison: AI (With IDSS) vs physical baseline (Without IDSS)."""

    # Physical baseline table
    print()
    print("=" * 80)
    print("  WITHOUT IDSS (Physical Board Game Baseline)")
    print("=" * 80)
    print()
    print(f"  {'Department':<16} {'Financial Cost':>16} {'Quality Cost':>14}")
    print(f"  {'-'*16} {'-'*16} {'-'*14}")
    for dept_name, costs in PHYSICAL_BASELINE.items():
        print(f"  {dept_name:<16} ${costs['financial']:>14,} {costs['quality']:>13,}")
    print(f"  {'-'*16} {'-'*16} {'-'*14}")
    print(f"  {'Total':<16} ${PHYSICAL_BASELINE_TOTAL['financial']:>14,} {PHYSICAL_BASELINE_TOTAL['quality']:>13,}")

    # AI table
    print()
    print("=" * 80)
    print("  WITH IDSS (AI-Guided)")
    print("=" * 80)
    print_dept_table("With IDSS", ai["dept_costs"])

    # Comparison
    print()
    print("=" * 80)
    print("  COMPARISON: With IDSS vs Without IDSS")
    print("=" * 80)
    print()
    print(f"  {'Metric':<20} {'With IDSS':>14} {'Without IDSS':>14} {'Savings':>12} {'%':>8}")
    print(f"  {'-'*20} {'-'*14} {'-'*14} {'-'*12} {'-'*8}")

    for label, key in [("Financial", "financial"), ("Quality", "quality")]:
        ai_val = ai[key]
        base_val = PHYSICAL_BASELINE_TOTAL[key]
        savings = base_val - ai_val
        pct = (savings / base_val * 100) if base_val > 0 else 0
        marker = "better" if savings > 0 else "WORSE" if savings < 0 else "same"
        print(f"  {label:<20} ${ai_val:>12,} ${base_val:>12,} ${savings:>10,} {pct:>+7.1f}%  {marker}")

    ai_combined = ai["combined"]
    base_combined = PHYSICAL_BASELINE_TOTAL["financial"] + PHYSICAL_BASELINE_TOTAL["quality"]
    savings = base_combined - ai_combined
    pct = (savings / base_combined * 100) if base_combined > 0 else 0
    marker = "better" if savings > 0 else "WORSE" if savings < 0 else "same"
    print(f"  {'Combined':<20} ${ai_combined:>12,} ${base_combined:>12,} ${savings:>10,} {pct:>+7.1f}%  {marker}")

    # Department comparison
    print()
    print(f"  {'Department':<16} {'IDSS Fin':>10} {'IDSS Qual':>10} {'Base Fin':>10} {'Base Qual':>10} {'Savings':>10}")
    print(f"  {'-'*16} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    for dept_name in DEPT_DETAIL_KEYS:
        ai_d = ai["dept_costs"][dept_name]
        base_d = PHYSICAL_BASELINE[dept_name]
        ai_total = ai_d["total_fin"] + ai_d["total_qual"]
        base_total = base_d["financial"] + base_d["quality"]
        savings = base_total - ai_total
        print(
            f"  {dept_name:<16} ${ai_d['total_fin']:>8,} {ai_d['total_qual']:>9,}"
            f" ${base_d['financial']:>8,} {base_d['quality']:>9,}"
            f" ${savings:>8,}"
        )

    print()


def write_csv(prefix: str, ai: dict) -> None:
    """Write results to CSV files comparing AI vs physical baseline."""
    base_combined = PHYSICAL_BASELINE_TOTAL["financial"] + PHYSICAL_BASELINE_TOTAL["quality"]

    # 1. Per-round AI costs
    rounds_path = f"{prefix}_rounds.csv"
    with open(rounds_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["round", "financial", "quality", "combined"])
        for i, (fin, qual) in enumerate(ai["round_costs"], 1):
            w.writerow([i, fin, qual, fin + qual])
    print(f"  Wrote {rounds_path}")

    # 2. Department comparison (matches presentation tables)
    dept_path = f"{prefix}_departments.csv"
    with open(dept_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["department",
                     "with_idss_financial", "with_idss_quality", "with_idss_combined",
                     "without_idss_financial", "without_idss_quality", "without_idss_combined",
                     "financial_savings", "quality_savings", "combined_savings"])
        total_ai_fin = total_ai_qual = 0
        for dept_name in DEPT_DETAIL_KEYS:
            ai_d = ai["dept_costs"][dept_name]
            base_d = PHYSICAL_BASELINE[dept_name]
            ai_fin, ai_qual = ai_d["total_fin"], ai_d["total_qual"]
            base_fin, base_qual = base_d["financial"], base_d["quality"]
            total_ai_fin += ai_fin
            total_ai_qual += ai_qual
            w.writerow([
                dept_name,
                ai_fin, ai_qual, ai_fin + ai_qual,
                base_fin, base_qual, base_fin + base_qual,
                base_fin - ai_fin, base_qual - ai_qual,
                (base_fin + base_qual) - (ai_fin + ai_qual),
            ])
        # Total row
        w.writerow([
            "Total",
            total_ai_fin, total_ai_qual, total_ai_fin + total_ai_qual,
            PHYSICAL_BASELINE_TOTAL["financial"], PHYSICAL_BASELINE_TOTAL["quality"], base_combined,
            PHYSICAL_BASELINE_TOTAL["financial"] - total_ai_fin,
            PHYSICAL_BASELINE_TOTAL["quality"] - total_ai_qual,
            base_combined - (total_ai_fin + total_ai_qual),
        ])
    print(f"  Wrote {dept_path}")

    # 3. Department breakdown by category (AI only — waiting/extra/diversion)
    breakdown_path = f"{prefix}_breakdown.csv"
    with open(breakdown_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["department", "category", "financial", "quality", "combined"])
        for dept_name in DEPT_DETAIL_KEYS:
            d = ai["dept_costs"][dept_name]
            for cat, fin_key, qual_key in [
                ("waiting", "waiting_fin", "waiting_qual"),
                ("extra_staff", "extra_fin", "extra_qual"),
                ("diversion", "diversion_fin", "diversion_qual"),
            ]:
                if d[fin_key] + d[qual_key] > 0:
                    w.writerow([dept_name, cat, d[fin_key], d[qual_key], d[fin_key] + d[qual_key]])
            w.writerow([dept_name, "TOTAL", d["total_fin"], d["total_qual"], d["total"]])
    print(f"  Wrote {breakdown_path}")

    # 4. Overall summary
    summary_path = f"{prefix}_summary.csv"
    with open(summary_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "with_idss", "without_idss", "savings", "savings_pct"])
        for label, key in [("financial", "financial"), ("quality", "quality")]:
            ai_val = ai[key]
            base_val = PHYSICAL_BASELINE_TOTAL[key]
            savings = base_val - ai_val
            pct = (savings / base_val * 100) if base_val > 0 else 0
            w.writerow([label, ai_val, base_val, savings, round(pct, 1)])
        ai_comb = ai["combined"]
        savings = base_combined - ai_comb
        pct = (savings / base_combined * 100) if base_combined > 0 else 0
        w.writerow(["combined", ai_comb, base_combined, savings, round(pct, 1)])
        w.writerow(["time_seconds", round(ai["time"], 1), "", "", ""])
    print(f"  Wrote {summary_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run a full AI-guided game and compare against physical board-game baseline"
    )
    parser.add_argument("--seed", type=int, default=42, help="Event RNG seed (default: 42)")
    parser.add_argument("--quiet", action="store_true", help="Only show final results")
    parser.add_argument("--csv", metavar="PREFIX", default=None,
                        help="Write CSV files (PREFIX_rounds.csv, PREFIX_departments.csv, PREFIX_breakdown.csv, PREFIX_summary.csv)")
    args = parser.parse_args()

    recommender = Recommender()
    ai_result = run_game(seed=args.seed, quiet=args.quiet, recommender=recommender)
    print_comparison(ai_result)

    if args.csv:
        print()
        write_csv(args.csv, ai_result)


if __name__ == "__main__":
    main()
