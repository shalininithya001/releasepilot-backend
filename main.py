"""CLI: python main.py --project KAN --dataset-label tyn-release-assessment-v2 --release R2.4"""
import argparse, json, logging, os, sys, time
from config import get_settings
from jira_client import JiraClient
from llm import LLMRouter, LLMUnavailable
from tracing import Tracer
from agent import Agent
import report as rpt


def run_assessment(settings, project, label, release, out_dir, jira=None, llm=None):
    settings.jira_project_key, settings.dataset_label = project, label
    os.makedirs(out_dir, exist_ok=True)
    tracer = Tracer(os.path.join(out_dir, "trace.jsonl"))
    jira = jira or JiraClient(settings)
    llm = llm or LLMRouter(settings, tracer)
    llm.tracer = tracer
    try:   # fail fast instead of producing a meaningless all-INSUFFICIENT report
        llm.chat([{"role": "user", "content": "Reply with the single word OK."}], None, "preflight")
    except LLMUnavailable as e:
        raise RuntimeError(f"No language model is working, so no assessment was run. Fix .env (keys/models) and retry. Details: {e}")
    t0 = time.time()
    agent = Agent(settings, jira, llm, tracer)
    decisions = agent.run(release)
    metrics = {"wall_seconds": round(time.time() - t0, 1), "phase_seconds": agent.phase_secs, "tool_calls": agent.ctx.total_calls,
               "jira_api_calls": jira.calls, "jira_api_failures": jira.failures, "unique_issues_opened": len(agent.ctx.fetched),
               "llm_usage": llm.usage, "providers_configured": [p.name + ":" + p.model for p in llm.providers]}
    rep = rpt.build(settings, project, release, agent, decisions, metrics)
    json.dump(rep, open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8").write(rpt.to_markdown(rep))
    json.dump(metrics, open(os.path.join(out_dir, "metrics.json"), "w"), indent=2)
    return rep


def main():
    s = get_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=s.jira_project_key)
    ap.add_argument("--dataset-label", default=s.dataset_label)
    ap.add_argument("--release", required=True)
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    logging.basicConfig(level=s.log_level, format="%(asctime)s %(levelname)s %(message)s")
    rep = run_assessment(s, a.project, a.dataset_label, a.release, a.out)
    print(f"Overall: {rep['overall_decision']}  {rep['decision_counts']}  wall={rep['metrics']['wall_seconds']}s  -> {a.out}/report.md")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # honest failure
        print(f"ASSESSMENT FAILED: {e}", file=sys.stderr); sys.exit(1)