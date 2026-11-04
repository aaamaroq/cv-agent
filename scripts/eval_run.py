#!/usr/bin/env python
"""Run the curated evaluation dataset through the real CV-chat graph.

Usage:
    .venv/bin/python scripts/eval_run.py --list
    .venv/bin/python scripts/eval_run.py
    .venv/bin/python scripts/eval_run.py --case q03-weakness

Runs and label templates are local and git-ignored. The graph calls OpenRouter;
set OPENROUTER_API_KEY in the environment before running cases.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.callbacks import UsageMetadataCallbackHandler  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402

from cv_chat import guardrails  # noqa: E402
from cv_chat.config import get_settings  # noqa: E402
from cv_chat.graph import build_graph  # noqa: E402
from cv_chat.prompts import SYSTEM_PROMPT, source_of_truth  # noqa: E402

DATASET_PATH = ROOT / "evals" / "dataset.jsonl"
AXES = (
    "factuality",
    "relevance",
    "missing_information",
    "language_tone",
    "guardrails",
)
_RETRY_NOTE_PREFIX = "Your previous draft was rejected by a quality guardrail: "


def _guardrail_rejection_reason(note: Any) -> str | None:
    if not isinstance(note, str) or not note:
        return None
    if note.startswith(_RETRY_NOTE_PREFIX):
        return note[len(_RETRY_NOTE_PREFIX):].split(" Write a new answer", 1)[0]
    return note


def load_dataset(path: Path) -> list[dict[str, Any]]:
    cases = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on {path}:{line_number}: {exc}") from exc
        required = {
            "id", "category", "language", "question", "expected_evidence",
            "must_not_claim", "acceptance_criteria",
        }
        missing = required - case.keys()
        if missing:
            raise ValueError(
                f"Missing fields on {path}:{line_number}: {', '.join(sorted(missing))}"
            )
        cases.append(case)
    if not cases:
        raise ValueError(f"No cases found in {path}")
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate case IDs in {path}")
    return cases


def _tokens_by_model(handler: UsageMetadataCallbackHandler) -> tuple[dict, dict]:
    by_model: dict[str, dict[str, int]] = {}
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for model, usage in handler.usage_metadata.items():
        counts = {
            key: int(usage.get(key, 0) or 0)
            for key in ("input_tokens", "output_tokens", "total_tokens")
        }
        if not counts["total_tokens"]:
            counts["total_tokens"] = counts["input_tokens"] + counts["output_tokens"]
        by_model[model] = counts
        for key in totals:
            totals[key] += counts[key]
    return by_model, totals


def run_case(graph: Any, case: dict[str, Any], run_id: str) -> dict[str, Any]:
    usage = UsageMetadataCallbackHandler()
    thread_id = f"eval-{run_id}-{case['id']}-{uuid.uuid4().hex[:8]}"
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [usage],
    }
    node_path: list[dict[str, Any]] = []
    input_verdict = None
    neutral_question = None
    output_ok = None
    retries = 0
    output_guardrail_reasons: list[str] = []
    fallback_used = False
    deflect_used = False
    started = time.perf_counter()

    try:
        for namespace, update in graph.stream(
            {"messages": [HumanMessage(content=case["question"])]},
            config,
            stream_mode="updates",
            subgraphs=True,
        ):
            for node, data in update.items():
                node_path.append({"namespace": list(namespace), "node": node})
                if not isinstance(data, dict):
                    continue
                if node == "input_guardrail":
                    input_verdict = data.get("input_verdict")
                    neutral_question = data.get("neutral_question")
                elif node == "output_guardrail":
                    output_ok = data.get("output_ok", output_ok)
                    retries = max(retries, int(data.get("retries", retries) or 0))
                    reason = _guardrail_rejection_reason(data.get("guardrail_note"))
                    if reason:
                        output_guardrail_reasons.append(reason)
                elif node == "fallback":
                    fallback_used = True
                elif node == "deflect":
                    deflect_used = True

        state = graph.get_state(config).values
        messages = state.get("messages", [])
        final_message = next(
            (message for message in reversed(messages) if isinstance(message, AIMessage)),
            None,
        )
        answer = guardrails.message_text(final_message) if final_message else ""
        token_models, token_totals = _tokens_by_model(usage)
        return {
            "record_type": "case",
            "id": case["id"],
            "category": case["category"],
            "language": case["language"],
            "question": case["question"],
            "answer": answer,
            "status": "ok",
            "node_path": node_path,
            "input_verdict": input_verdict,
            "neutral_question": neutral_question,
            "output_guardrail_ok": output_ok,
            "output_retries": retries,
            "output_guardrail_reasons": output_guardrail_reasons,
            "fallback_used": fallback_used,
            "deflect_used": deflect_used,
            "latency_seconds": round(time.perf_counter() - started, 3),
            "tokens_by_model": token_models,
            "token_totals": token_totals,
            "cost_usd": None,
        }
    except Exception as exc:  # noqa: BLE001 - preserve failed cases in the run file
        token_models, token_totals = _tokens_by_model(usage)
        return {
            "record_type": "case",
            "id": case["id"],
            "category": case["category"],
            "language": case["language"],
            "question": case["question"],
            "answer": "",
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "node_path": node_path,
            "input_verdict": input_verdict,
            "neutral_question": neutral_question,
            "output_guardrail_ok": output_ok,
            "output_retries": retries,
            "output_guardrail_reasons": output_guardrail_reasons,
            "fallback_used": fallback_used,
            "deflect_used": deflect_used,
            "latency_seconds": round(time.perf_counter() - started, 3),
            "tokens_by_model": token_models,
            "token_totals": token_totals,
            "cost_usd": None,
        }


def write_json_line(handle, value: dict[str, Any]) -> None:
    handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    handle.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--case", help="run only cases whose ID contains this text")
    parser.add_argument("--list", action="store_true", help="list cases without calling a model")
    parser.add_argument("--output", type=Path, help="override the default local run file")
    parser.add_argument("--resume", type=Path, help="resume an incomplete run JSONL without repeating completed cases")
    args = parser.parse_args()

    try:
        cases = load_dataset(args.dataset)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    if args.case:
        needle = args.case.casefold()
        cases = [case for case in cases if needle in case["id"].casefold()]
        if not cases:
            parser.error(f"No case ID contains {args.case!r}")
    if args.list:
        for case in cases:
            print(f"{case['id']} [{case['category']}/{case['language']}]: {case['question']}")
        return 0

    settings = get_settings()
    if not settings.api_key:
        print(
            "OPENROUTER_API_KEY is not configured. Set it in your local shell "
            "before running evaluations; do not put it in the dataset or run files.",
            file=sys.stderr,
        )
        return 2

    dataset_hash = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    prompt_fingerprint = hashlib.sha256("\0".join((
        SYSTEM_PROMPT,
        guardrails.INPUT_SYSTEM_PROMPT,
        guardrails.OUTPUT_SYSTEM_PROMPT,
        guardrails.RETRY_NOTE,
    )).encode("utf-8")).hexdigest()
    source_hash = hashlib.sha256(source_of_truth().encode("utf-8")).hexdigest()
    existing_records: list[dict[str, Any]] = []
    if args.resume:
        if args.output:
            parser.error("--output cannot be combined with --resume")
        output_path = args.resume.resolve()
        try:
            existing_records = [
                json.loads(line)
                for line in output_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, json.JSONDecodeError) as exc:
            parser.error(f"Cannot read resume file {output_path}: {exc}")
        header = next(
            (record for record in existing_records if record.get("record_type") == "run"),
            None,
        )
        if header is None:
            parser.error(f"No run header found in {output_path}")
        if header.get("dataset_sha256") != dataset_hash:
            parser.error("The dataset changed since this run started; refusing to resume it")
        if header.get("model") != settings.model or header.get("guardrail_model") != settings.guardrail_model:
            parser.error("Model settings differ from the incomplete run; refusing to resume it")
        if (
            header.get("prompt_sha256") != prompt_fingerprint
            or header.get("source_of_truth_sha256") != source_hash
        ):
            parser.error("Prompts or source documents differ from the incomplete run; refusing to resume it")
        run_id = header["run_id"]
    else:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
        output_path = args.output or ROOT / "evals" / "runs" / f"{run_id}.jsonl"
        header = {
            "record_type": "run",
            "schema_version": 1,
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dataset": str(args.dataset.relative_to(ROOT)) if args.dataset.is_relative_to(ROOT) else str(args.dataset),
            "dataset_sha256": dataset_hash,
            "prompt_sha256": prompt_fingerprint,
            "source_of_truth_sha256": source_hash,
            "model": settings.model,
            "guardrail_model": settings.guardrail_model,
            "temperature": settings.temperature,
            "cases_planned": len(cases),
        }

    labels_path = ROOT / "evals" / "labels" / f"{run_id}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    recorded = {
        record.get("id"): record
        for record in existing_records
        if record.get("record_type") == "case"
    }
    pending = [case for case in cases if case["id"] not in recorded]
    if args.case:
        needle = args.case.casefold()
        pending = [case for case in pending if needle in case["id"].casefold()]
    if not pending and not recorded:
        parser.error("No cases selected")

    labels = {}
    if labels_path.is_file():
        labels = {
            item["id"]: item
            for item in read_label_template(labels_path)
        }
    for case in cases:
        labels.setdefault(case["id"], {
            "id": case["id"],
            "overall": None,
            "scores": {axis: None for axis in AXES},
            "blocking_fabrication": None,
            "notes": "",
        })
    with labels_path.open("w", encoding="utf-8") as label_file:
        for case in cases:
            write_json_line(label_file, labels[case["id"]])

    if pending:
        graph = build_graph(settings)
        print(f"Run {run_id}: {len(pending)} pending case(s) -> {output_path}", flush=True)
    else:
        graph = None
        print(f"Run {run_id}: no pending cases -> {output_path}", flush=True)

    completed = sum(record.get("status") == "ok" for record in recorded.values())
    mode = "a" if args.resume else "w"
    with output_path.open(mode, encoding="utf-8") as output:
        if not args.resume:
            write_json_line(output, header)
        for index, case in enumerate(pending, 1):
            result = run_case(graph, case, run_id)
            write_json_line(output, result)
            completed += result["status"] == "ok"
            status = result["status"].upper()
            tokens = result["token_totals"].get("total_tokens", 0)
            print(
                f"[{index}/{len(pending)}] {case['id']}: {status}, "
                f"{result['latency_seconds']:.1f}s, {tokens} tokens, "
                f"verdict={result['input_verdict']}, retries={result['output_retries']}",
                flush=True,
            )
            if result["status"] == "error":
                print(f"  {result['error']}")

    all_case_records = {**recorded}
    all_case_records.update({
        record["id"]: record
        for record in read_jsonl_records(output_path)
        if record.get("record_type") == "case"
    })
    ok_total = sum(record.get("status") == "ok" for record in all_case_records.values())
    print(f"Completed {ok_total}/{len(cases)} cases.")
    print(f"Human label template: {labels_path}")
    return 0 if ok_total == len(cases) else 1


def read_jsonl_records(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_label_template(path: Path) -> list[dict[str, Any]]:
    return read_jsonl_records(path)


if __name__ == "__main__":
    raise SystemExit(main())
