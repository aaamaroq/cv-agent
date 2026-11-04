#!/usr/bin/env python
"""Compare provisional LLM-judge scores with the human labels, without deciding a threshold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AXES = (
    "factuality",
    "relevance",
    "missing_information",
    "language_tone",
    "guardrails",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on {path}:{line_number}: {exc}") from exc
    return records


def _axis_metrics(
    human: dict[str, dict[str, Any]], judge: dict[str, dict[str, Any]], axis: str
) -> dict[str, Any]:
    pairs = [
        (human[case_id]["scores"].get(axis), judge[case_id]["scores"].get(axis))
        for case_id in human.keys() & judge.keys()
        if human[case_id].get("scores", {}).get(axis) in (1, 2, 3)
        and judge[case_id].get("scores", {}).get(axis) in (1, 2, 3)
    ]
    if not pairs:
        return {"n": 0, "exact": None, "mae": None}
    return {
        "n": len(pairs),
        "exact": sum(h == j for h, j in pairs) / len(pairs),
        "mae": sum(abs(h - j) for h, j in pairs) / len(pairs),
    }


def calibration_metrics(
    human_rows: list[dict[str, Any]], judge_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    human = {row["id"]: row for row in human_rows if row.get("overall") in (1, 2, 3)}
    judge = {
        row["id"]: row
        for row in judge_rows
        if row.get("status", "ok") == "ok" and row.get("overall") in (1, 2, 3)
    }
    shared = human.keys() & judge.keys()
    overall_pairs = [(human[key]["overall"], judge[key]["overall"]) for key in shared]
    if overall_pairs:
        overall = {
            "n": len(overall_pairs),
            "exact": sum(h == j for h, j in overall_pairs) / len(overall_pairs),
            "mae": sum(abs(h - j) for h, j in overall_pairs) / len(overall_pairs),
        }
    else:
        overall = {"n": 0, "exact": None, "mae": None}

    blocking_pairs = [
        (human[key].get("blocking_fabrication"), judge[key].get("blocking_fabrication"))
        for key in shared
        if isinstance(human[key].get("blocking_fabrication"), bool)
        and isinstance(judge[key].get("blocking_fabrication"), bool)
    ]
    false_negatives = [
        key for key in shared
        if human[key].get("blocking_fabrication") is True
        and judge[key].get("blocking_fabrication") is False
    ]
    false_positives = [
        key for key in shared
        if human[key].get("blocking_fabrication") is False
        and judge[key].get("blocking_fabrication") is True
    ]
    llm_false_negatives = [
        key for key in shared
        if human[key].get("blocking_fabrication") is True
        and judge[key].get("blocking_fabrication_llm") is False
    ]
    blocking = {
        "n": len(blocking_pairs),
        "exact": (
            sum(h == j for h, j in blocking_pairs) / len(blocking_pairs)
            if blocking_pairs else None
        ),
        "false_negatives": false_negatives,
        "false_positives": false_positives,
    }
    disagreements = [
        {
            "id": case_id,
            "human_overall": human[case_id]["overall"],
            "judge_overall": judge[case_id]["overall"],
            "human_blocking": human[case_id].get("blocking_fabrication"),
            "judge_blocking": judge[case_id].get("blocking_fabrication"),
            "judge_blocking_raw": judge[case_id].get("blocking_fabrication_llm"),
            "audit_block": judge[case_id].get("audit_block"),
            "human_axes": human[case_id].get("scores", {}),
            "judge_axes": judge[case_id].get("scores", {}),
            "rationale": judge[case_id].get("rationale", ""),
            "claim_audits": judge[case_id].get("claim_audits", []),
        }
        for case_id in sorted(shared)
        if human[case_id]["overall"] != judge[case_id]["overall"]
        or human[case_id].get("blocking_fabrication") != judge[case_id].get("blocking_fabrication")
        or (
            "blocking_fabrication_llm" in judge[case_id]
            and human[case_id].get("blocking_fabrication")
            != judge[case_id].get("blocking_fabrication_llm")
        )
        or any(
            human[case_id].get("scores", {}).get(axis) != judge[case_id].get("scores", {}).get(axis)
            for axis in AXES
        )
    ]
    return {
        "cases_compared": len(shared),
        "overall": overall,
        "axes": {axis: _axis_metrics(human, judge, axis) for axis in AXES},
        "blocking": blocking,
        "llm_blocking_false_negatives": llm_false_negatives,
        "disagreements": disagreements,
    }


def print_metrics(metrics: dict[str, Any]) -> None:
    def pct(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.0%}"

    print(f"Cases compared: {metrics['cases_compared']}")
    overall = metrics["overall"]
    print(f"Overall: exact agreement {pct(overall['exact'])}; MAE {overall['mae']:.2f}" if overall["mae"] is not None else "Overall: no comparable labels")
    print("\n| Axis | Exact agreement | Mean absolute error | n |\n|---|---:|---:|---:|")
    for axis, result in metrics["axes"].items():
        title = axis.replace("_", " ")
        mae = "n/a" if result["mae"] is None else f"{result['mae']:.2f}"
        print(f"| {title} | {pct(result['exact'])} | {mae} | {result['n']} |")
    blocking = metrics["blocking"]
    print(f"\nBlocking agreement: {pct(blocking['exact'])}; validated false negatives: {blocking['false_negatives']}; raw LLM false negatives: {metrics.get('llm_blocking_false_negatives', [])}; false positives: {blocking['false_positives']}")
    if metrics["disagreements"]:
        print("\nDisagreements:")
        for row in metrics["disagreements"]:
            print(
                f"- {row['id']}: overall human={row['human_overall']} / judge={row['judge_overall']}; "
                f"blocking human={row['human_blocking']} / judge={row['judge_blocking']}"
            )
            print(f"  Judge: {row['rationale']}")
            unsupported = [
                audit["claim"]
                for audit in row.get("claim_audits", [])
                if audit.get("unsupported_cv_fact")
            ]
            if unsupported:
                print(f"  Unsupported CV claims: {unsupported}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path, help="human label JSONL")
    parser.add_argument("judgements", type=Path, help="provisional judge JSONL")
    args = parser.parse_args()
    try:
        human_rows = read_jsonl(args.labels)
        judge_rows = read_jsonl(args.judgements)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    metrics = calibration_metrics(human_rows, judge_rows)
    print_metrics(metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
