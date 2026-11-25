"""Run the full assessment once per provider (separate reports) and compare the decisions.
    python compare_runs.py --release R2.4                        # all providers that have a key + model in .env, in parallel
    python compare_runs.py --release R2.4 --providers gemini,nvidia --sequential
Output: out_compare/<provider>/{report.md,report.json,trace.jsonl,metrics.json} and out_compare/comparison.{md,json}"""
import argparse, collections, json, logging, os, sys
from concurrent.futures import ThreadPoolExecutor
from config import get_settings
from llm import build_providers
from main import run_assessment

DECISIONS = ("PASS", "FAIL", "INSUFFICIENT_EVIDENCE")


def run_all(settings, names, project, label, release, out_root, parallel=True, runner=run_assessment):
    def one(name):
        s = settings.model_copy()
        s.llm_provider_order = name          # this run may only use this provider (no failover to the others)
        try:
            return name, {"report": runner(s, project, label, release, os.path.join(out_root, name))}
        except Exception as e:  # noqa  (a provider that is down must not stop the other runs)
            return name, {"error": str(e)[:500]}
    if parallel and len(names) > 1:
        with ThreadPoolExecutor(len(names)) as ex:
            return dict(ex.map(one, names))
    return dict(one(n) for n in names)


def _cell(req):
    return req["decision"] + ("*" if req.get("assessment_status") == "incomplete" else "")


def build_comparison(results: dict) -> dict:
    ok = {n: r["report"] for n, r in results.items() if "report" in r}
    summary = {}
    for n, r in results.items():
        if "report" not in r:
            summary[n] = {"error": r["error"]}; continue
        rep, m = r["report"], r["report"]["metrics"]
        summary[n] = {"model": ", ".join(x for x in m.get("providers_configured", [])), "overall": rep["overall_decision"],
                      "degraded": rep["run_integrity"]["degraded"], "incomplete": rep.get("incomplete_requirements", 0),
                      "wall_seconds": m["wall_seconds"], "tool_calls": m["tool_calls"],
                      "tokens": sum(u["total_tokens"] for u in m["llm_usage"].values()),
                      "counts": rep["decision_counts"]}
    ids = sorted({q["requirement_id"] for rep in ok.values() for q in rep["requirements"]})
    rows = []
    for rid in ids:
        per = {n: next((q for q in rep["requirements"] if q["requirement_id"] == rid), None) for n, rep in ok.items()}
        assessed = {n: q["decision"] for n, q in per.items() if q and q.get("assessment_status") != "incomplete"}
        votes = collections.Counter(assessed.values()).most_common()
        agree = None if len(assessed) < 2 else len(set(assessed.values())) == 1
        majority = votes[0][0] if votes and (len(votes) == 1 or votes[0][1] > votes[1][1]) else None
        title = next((q["title"] for q in per.values() if q), "")
        rows.append({"requirement_id": rid, "title": title, "decisions": {n: (_cell(q) if q else "-") for n, q in per.items()},
                     "agree": agree, "majority": majority, "detail": per})
    return {"summary": summary, "rows": rows, "providers": list(results)}


def to_markdown(cmp: dict, release: str) -> str:
    names = cmp["providers"]; S = cmp["summary"]
    L = [f"# Provider comparison for release {release}", "", "`*` = that provider could not finish the requirement (not a real decision).", "",
         "| Provider | Model | Overall | Degraded | Not assessed | Wall time (s) | Tool calls | Tokens |", "|---|---|---|---|---|---|---|---|"]
    for n in names:
        s = S[n]
        L.append(f"| {n} | {s['model']} | {s['overall']} | {s['degraded']} | {s['incomplete']} | {s['wall_seconds']} | {s['tool_calls']} | {s['tokens']} |"
                 if "error" not in s else f"| {n} | - | RUN FAILED: {s['error'][:120]} | - | - | - | - | - |")
    good = [n for n in names if "error" not in S[n]]
    L += ["", "| Requirement | Title | " + " | ".join(good) + " | Agree | Majority |", "|---|---|" + "---|" * (len(good) + 2)]
    for r in cmp["rows"]:
        a = {None: "n/a", True: "yes", False: "NO"}[r["agree"]]
        L.append(f"| {r['requirement_id']} | {r['title'].split('] ', 1)[-1]} | " + " | ".join(r["decisions"].get(n, "-") for n in good) + f" | {a} | {r['majority'] or '-'} |")
    agreed = sum(1 for r in cmp["rows"] if r["agree"]); comparable = sum(1 for r in cmp["rows"] if r["agree"] is not None)
    L += ["", f"Providers agree on {agreed} of {comparable} comparable requirements."]
    dis = [r for r in cmp["rows"] if r["agree"] is False]
    if dis:
        L += ["", "## Disagreements (read the evidence and decide)"]
        for r in dis:
            L += ["", f"### {r['requirement_id']}: {r['title'].split('] ', 1)[-1]}"]
            for n in good:
                q = r["detail"].get(n)
                if not q or q.get("assessment_status") == "incomplete":
                    continue
                refs = ", ".join(f"{e['source_id']}#{e['comment_id']}" for e in q["evidence"] if e.get("comment_id") and e["use"] in ("decisive", "supporting", "contradicting")) or "none"
                L += [f"- **{n}: {q['decision']}**. Key evidence: {refs}", f"  {q['rationale'][:500]}"]
    return "\n".join(L) + "\n"


def main():
    s = get_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=s.jira_project_key); ap.add_argument("--dataset-label", default=s.dataset_label)
    ap.add_argument("--release", required=True); ap.add_argument("--out", default="out_compare")
    ap.add_argument("--providers", default=""); ap.add_argument("--sequential", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=s.log_level, format="%(asctime)s %(levelname)s %(message)s")
    have = [p.name for p in build_providers(s)]
    names = [x.strip() for x in a.providers.split(",") if x.strip()] or have
    missing = [n for n in names if n not in have]
    if missing:
        sys.exit(f"No API key/model in .env for: {', '.join(missing)}")
    print(f"Running {len(names)} separate assessments ({'sequential' if a.sequential else 'parallel'}): {', '.join(names)}")
    results = run_all(s, names, a.project, a.dataset_label, a.release, a.out, not a.sequential)
    cmp = build_comparison(results)
    os.makedirs(a.out, exist_ok=True)
    json.dump({k: v for k, v in cmp.items() if k != "rows"} | {"rows": [{k: v for k, v in r.items() if k != "detail"} for r in cmp["rows"]]},
              open(os.path.join(a.out, "comparison.json"), "w"), indent=2)
    md = to_markdown(cmp, a.release)
    open(os.path.join(a.out, "comparison.md"), "w", encoding="utf-8").write(md)
    print(md)


if __name__ == "__main__":
    main()