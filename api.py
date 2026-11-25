
"""ReleasePilot API.

Run:
    uvicorn api:app --reload --host 0.0.0.0 --port 8000
"""

import json
import uuid
import threading

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_settings
from main import run_assessment


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

s = get_settings()

BASE_DIR = Path(__file__).resolve().parent
COMPARISON_DIR = BASE_DIR / "out_compare"

PROVIDERS = ("gemini", "openrouter", "nvidia")

app = FastAPI(
    title=s.app_name,
    version=s.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------
# Request models
# ---------------------------------------------------------

class Req(BaseModel):
    project: str = s.jira_project_key
    dataset_label: str = s.dataset_label
    release: str


# ---------------------------------------------------------
# Existing assessment job functionality
# ---------------------------------------------------------

def _work(job_id: str, r: Req):
    try:
        report = run_assessment(
            get_settings(),
            r.project,
            r.dataset_label,
            r.release,
            f"out/{job_id}",
        )

        JOBS[job_id] = {
            "status": "done",
            "report": report,
        }

    except Exception as e:
        JOBS[job_id] = {
            "status": "failed",
            "error": str(e),
        }


@app.post(f"{s.api_prefix}/assessments", status_code=202)
def start(r: Req):
    jid = uuid.uuid4().hex[:8]

    JOBS[jid] = {"status": "running"}

    threading.Thread(
        target=_work,
        args=(jid, r),
        daemon=True,
    ).start()

    return {"id": jid, "status": "running"}


@app.get(f"{s.api_prefix}/assessments/{{jid}}")
def get(jid: str):
    if jid not in JOBS:
        raise HTTPException(404, "Unknown job")

    return JOBS[jid]


# ---------------------------------------------------------
# Shared file helpers
# ---------------------------------------------------------

def read_json(path: Path) -> dict:
    """Read a JSON file safely and return an object."""

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {path.name}",
        )

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object")

        return data

    except (json.JSONDecodeError, OSError, ValueError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read {path.name}: {str(e)}",
        )


def get_comparison() -> dict:
    return read_json(COMPARISON_DIR / "comparison.json")


def get_provider_report(provider: str) -> dict:
    provider = provider.lower()

    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown provider: {provider}",
        )

    return read_json(
        COMPARISON_DIR / provider / "report.json"
    )


def get_release_report_info() -> dict:
    """Read available provider reports and determine release metadata."""

    reports = {}

    for provider in PROVIDERS:
        path = COMPARISON_DIR / provider / "report.json"

        if path.exists():
            reports[provider] = read_json(path)

    if not reports:
        raise HTTPException(
            status_code=404,
            detail="No provider reports found in out_compare.",
        )

    first_report = next(iter(reports.values()))

    return {
        "reports": reports,
        "release": first_report.get("target_release", "R2.4"),
        "project": first_report.get("jira_project", s.jira_project_key),
        "dataset_label": first_report.get("dataset_label", s.dataset_label),
    }


# ---------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": s.app_name,
    }


# ---------------------------------------------------------
# Release comparison summary
# ---------------------------------------------------------

@app.get("/api/releases/{release}")
def release_summary(release: str):
    comparison = get_comparison()
    report_info = get_release_report_info()

    actual_release = report_info["release"]

    if release.lower() != str(actual_release).lower():
        raise HTTPException(
            status_code=404,
            detail=f"No comparison data available for release {release}.",
        )

    summary = comparison.get("summary", {})

    providers = {}

    for provider in PROVIDERS:
        provider_summary = summary.get(provider)

        if provider_summary is None:
            providers[provider] = {
                "available": False,
                "message": "Provider comparison data unavailable.",
            }
            continue

        providers[provider] = {
            "available": True,
            **provider_summary,
        }

    return {
        "release": actual_release,
        "project": report_info["project"],
        "dataset_label": report_info["dataset_label"],
        "providers": providers,
        "provider_order": comparison.get("providers", list(PROVIDERS)),
        "total_requirements": len(comparison.get("rows", [])),
    }


# ---------------------------------------------------------
# Requirement-by-requirement comparison
# ---------------------------------------------------------

@app.get("/api/releases/{release}/requirements")
def release_requirements(release: str):
    comparison = get_comparison()
    report_info = get_release_report_info()

    if release.lower() != str(report_info["release"]).lower():
        raise HTTPException(
            status_code=404,
            detail=f"No comparison data available for release {release}.",
        )

    rows = comparison.get("rows", [])

    return {
        "release": report_info["release"],
        "total": len(rows),
        "providers": comparison.get("providers", list(PROVIDERS)),
        "requirements": rows,
    }


# ---------------------------------------------------------
# Individual provider report
# ---------------------------------------------------------

@app.get("/api/releases/{release}/providers/{provider}")
def provider_report(release: str, provider: str):
    report = get_provider_report(provider)

    actual_release = report.get("target_release")

    if actual_release and release.lower() != str(actual_release).lower():
        raise HTTPException(
            status_code=404,
            detail=f"No {provider} report available for release {release}.",
        )

    return {
        "provider": provider.lower(),
        "release": actual_release,
        "report": report,
    }


# ---------------------------------------------------------
# Provider execution health / reliability
# ---------------------------------------------------------

@app.get("/api/releases/{release}/providers")
def provider_health(release: str):
    comparison = get_comparison()
    report_info = get_release_report_info()

    if release.lower() != str(report_info["release"]).lower():
        raise HTTPException(
            status_code=404,
            detail=f"No comparison data available for release {release}.",
        )

    results = {}

    for provider in PROVIDERS:
        path = COMPARISON_DIR / provider / "report.json"

        if not path.exists():
            results[provider] = {
                "available": False,
            }
            continue

        report = read_json(path)

        integrity = report.get("run_integrity", {})
        metrics = report.get("metrics", {})
        usage = metrics.get("llm_usage", {})

        provider_usage = usage.get(provider, {})

        results[provider] = {
            "available": True,
            "overall_decision": report.get("overall_decision"),
            "decision_counts": report.get("decision_counts", {}),
            "incomplete_requirements": report.get(
                "incomplete_requirements", 0
            ),
            "degraded": integrity.get("degraded", False),
            "llm_failures": integrity.get("llm_failures", []),
            "tool_errors": integrity.get("tool_errors", []),
            "warnings": integrity.get("warnings", []),
            "metrics": {
                "wall_seconds": metrics.get("wall_seconds", 0),
                "tool_calls": metrics.get("tool_calls", 0),
                "jira_api_calls": metrics.get("jira_api_calls", 0),
                "jira_api_failures": metrics.get("jira_api_failures", 0),
                "unique_issues_opened": metrics.get(
                    "unique_issues_opened", 0
                ),
                "llm_usage": provider_usage,
            },
        }

    return {
        "release": report_info["release"],
        "providers": results,
    }


# ---------------------------------------------------------
# Submission endpoint used by the frontend
# ---------------------------------------------------------

@app.post("/api/releases/{release}/submission", status_code=202)
def submit_release(release: str, r: Req | None = None):
    """Start a new assessment using the configured LLM provider.

    This starts the existing single-provider assessment workflow.
    It does not automatically rerun all three comparison providers.
    """

    request_data = r or Req(release=release)

    if request_data.release.lower() != release.lower():
        raise HTTPException(
            status_code=400,
            detail="Release in request body does not match URL.",
        )

    return start(request_data)
