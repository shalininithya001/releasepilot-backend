"""
Checkpointed sequential ReleasePilot runner.

Uses the existing Agent, Jira tools, LLMRouter and report builder.
Does not change the existing main.py or assessment logic.

Run:
    python sequential_runner.py --release R2.4
    python sequential_runner.py --release R2.4 --resume
    python sequential_runner.py --release R2.4 --restart
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from config import get_settings
from jira_client import JiraClient
from llm import LLMRouter, LLMUnavailable
from tracing import Tracer
from agent import Agent
import report as rpt


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)


def read_checkpoint(path: Path, project: str, label: str, release: str) -> dict:
    if not path.exists():
        return {
            "project": project,
            "dataset_label": label,
            "release": release,
            "completed": {},
            "failed": {},
        }

    data = json.loads(path.read_text(encoding="utf-8"))
    expected = (project, label, release)
    actual = (
        data.get("project"),
        data.get("dataset_label"),
        data.get("release"),
    )
    if actual != expected:
        raise RuntimeError(
            "Checkpoint belongs to a different assessment: "
            f"found {actual}, expected {expected}. Use --restart or another --out folder."
        )
    data.setdefault("completed", {})
    data.setdefault("failed", {})
    return data


def save_requirement(out_dir: Path, decision: dict) -> None:
    source_id = decision.get("requirement_id") or decision["requirement_key"]
    write_json(out_dir / "requirements" / f"{source_id}.json", decision)


def run_sequential(settings, project: str, label: str, release: str, out_dir: str,
                   resume: bool = True, max_new_requirements: int | None = None,
                   jira=None, llm=None) -> dict:
    settings.jira_project_key = project
    settings.dataset_label = label

    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    requirement_dir = root / "requirements"
    requirement_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = root / "checkpoint.json"
    if not resume and checkpoint_path.exists():
        checkpoint_path.unlink()

    checkpoint = read_checkpoint(checkpoint_path, project, label, release)
    tracer = Tracer(str(root / "trace.jsonl"))
    jira = jira or JiraClient(settings)
    llm = llm or LLMRouter(settings, tracer)
    llm.tracer = tracer

    # Fail fast if no provider can answer at all.
    try:
        llm.chat(
            [{"role": "user", "content": "Reply with the single word OK."}],
            None,
            "preflight",
        )
    except LLMUnavailable as exc:
        raise RuntimeError(
            "No configured LLM provider is currently available. "
            f"Check provider keys/models and retry. Details: {exc}"
        ) from exc

    agent = Agent(settings, jira, llm, tracer)
    started = time.time()

    # Requirement discovery and target validation use the existing logic.
    requirement_keys = agent.discover(release)
    requirement_keys = sorted(
        requirement_keys,
        key=lambda key: agent.ctx._load(key).get("source_id") or key,
    )
    count = len(requirement_keys)
    if count != 12:
        raise RuntimeError(
            f"Expected 12 manifest-linked requirements, discovered {count}. "
            "No assessment was started."
        )

    # Match the existing Agent.run() budgets so each requirement gets its own share.
    agent.ctx.global_call_cap = max(
        settings.agent_max_iterations,
        count * (agent.ctx.req_call_cap + 6) + 30,
    )
    agent.ctx.global_unique_cap = max(
        settings.agent_max_unique_issues,
        count * 25,
    )

    decisions_by_key = {}
    newly_processed = 0
    for req_key in requirement_keys:
        saved = checkpoint["completed"].get(req_key)
        saved_path = requirement_dir / (
            (saved or {}).get("requirement_id", req_key) + ".json"
        )

        if resume and saved and saved.get("assessment_status") in ("done", "forced"):
            # Only completed, submitted decisions are safe to skip.
            if saved_path.exists():
                decisions_by_key[req_key] = json.loads(
                    saved_path.read_text(encoding="utf-8")
                )
                print(
                    f"[SKIP] {req_key} "
                    f"({decisions_by_key[req_key]['decision']}) already checkpointed",
                    flush=True,
                )
                continue

        print(f"[START] {req_key}", flush=True)
        try:
            decision = agent.assess(req_key)
        except Exception as exc:
            # Keep the run moving, but never turn an execution error into FAIL.
            agent.warnings.append(
                f"{req_key}: unexpected assessment error: {type(exc).__name__}: {exc}"
            )
            req = agent.ctx._load(req_key)
            decision = {
                "requirement_key": req_key,
                "requirement_id": req.get("source_id"),
                "decision": "INSUFFICIENT_EVIDENCE",
                "rationale": (
                    "The assessment could not complete because of an execution error. "
                    "This is not evidence that the requirement failed."
                ),
                "evidence": [],
                "outstanding": ["Retry this requirement after resolving the execution error."],
                "title": req.get("summary"),
                "acceptance_criterion": None,
                "mandatory": True,
                "assessment_status": "incomplete",
                "requirement_url": f"{settings.jira_base_url}/browse/{req_key}",
            }

        # Enrich evidence while this requirement's Jira records are still in memory.
        rpt.enrich(agent.ctx, [decision])
        decisions_by_key[req_key] = decision
        save_requirement(root, decision)

        if decision.get("assessment_status") in ("done", "forced"):
            checkpoint["completed"][req_key] = decision
            checkpoint["failed"].pop(req_key, None)
        else:
            checkpoint["failed"][req_key] = {
                "decision": decision.get("decision"),
                "assessment_status": decision.get("assessment_status"),
                "reason": decision.get("rationale"),
            }

        # Persist immediately after every requirement.
        write_json(checkpoint_path, checkpoint)
        print(
            f"[SAVED] {req_key}: {decision['decision']} "
            f"({decision.get('assessment_status')})",
            flush=True,
        )
        newly_processed += 1
        if max_new_requirements is not None and newly_processed >= max_new_requirements:
            break

    # A limited pilot run intentionally writes only the per-requirement result
    # and checkpoint. It must not produce a misleading partial readiness report.
    if len(decisions_by_key) < len(requirement_keys):
        print(
            f"[CHECKPOINT] {len(decisions_by_key)}/{len(requirement_keys)} "
            f"requirements available. Re-run with --resume to continue.",
            flush=True,
        )
        return {
            "partial": True,
            "processed": len(decisions_by_key),
            "total": len(requirement_keys),
            "checkpoint": str(checkpoint_path),
        }

    # Build the normal project report from this run plus any resumed decisions.
    decisions = [
        decisions_by_key[k]
        for k in sorted(
            decisions_by_key,
            key=lambda k: (
                decisions_by_key[k].get("requirement_id") or k
            ),
        )
    ]

    agent.phase_secs["assessment"] = round(time.time() - started, 1)
    agent.phase_secs["total"] = round(time.time() - started, 1)

    metrics = {
        "wall_seconds": round(time.time() - started, 1),
        "phase_seconds": agent.phase_secs,
        "tool_calls": agent.ctx.total_calls,
        "jira_api_calls": jira.calls,
        "jira_api_failures": jira.failures,
        "unique_issues_opened": len(agent.ctx.fetched),
        "llm_usage": llm.usage,
        "providers_configured": [p.name + ":" + p.model for p in llm.providers],
        "sequential": True,
        "resumed_requirements": sum(
            1 for k in requirement_keys
            if checkpoint["completed"].get(k)
            and decisions_by_key[k].get("assessment_status") in ("done", "forced")
            and k not in agent.ctx.decisions
        ),
    }

    report = rpt.build(settings, project, release, agent, decisions, metrics)
    write_json(root / "report.json", report)
    (root / "report.md").write_text(
        rpt.to_markdown(report),
        encoding="utf-8",
    )
    write_json(root / "metrics.json", metrics)

    checkpoint["last_run_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    checkpoint["report_overall_decision"] = report["overall_decision"]
    write_json(checkpoint_path, checkpoint)
    return report


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Run ReleasePilot one requirement at a time with checkpoints."
    )
    parser.add_argument("--project", default=settings.jira_project_key)
    parser.add_argument("--dataset-label", default=settings.dataset_label)
    parser.add_argument("--release", required=True)
    parser.add_argument("--out", default="out_sequential")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume completed requirements from checkpoint.json.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most this many new requirements, then save a checkpoint (e.g. --limit 1 for a pilot).",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Ignore the existing checkpoint and start all requirements again.",
    )
    args = parser.parse_args()

    if args.resume and args.restart:
        parser.error("--resume and --restart cannot be used together.")

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    report = run_sequential(
        settings,
        args.project,
        args.dataset_label,
        args.release,
        args.out,
        resume=args.resume,
        max_new_requirements=args.limit,
    )
    if report.get("partial"):
        print(
            f"Pilot checkpoint saved: {report['processed']}/{report['total']} "
            f"requirements -> {report['checkpoint']}"
        )
        return
    print(
        f"Overall: {report['overall_decision']} "
        f"{report['decision_counts']} "
        f"wall={report['metrics']['wall_seconds']}s "
        f"-> {args.out}/report.md"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SEQUENTIAL ASSESSMENT FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
