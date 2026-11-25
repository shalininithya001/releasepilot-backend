import json, datetime, collections
from agent import overall


def enrich(ctx, decisions):
    for d in decisions:
        for e in d["evidence"]:
            data = ctx.fetched.get(e["issue_key"], {}).get("data")
            c = next((c for c in (data or {}).get("comments", []) if c["comment_id"] == e["comment_id"]), None)
            if c:
                e.update({"recorded_actor": c["actor"], "recorded_role": c["role"], "recorded_event_time": c["event_time"],
                          "excerpt": c["text"][:240]})
    return decisions


def build(settings, project, release, agent, decisions, metrics):
    ctx = agent.ctx
    decisions = enrich(ctx, decisions)
    counts = collections.Counter(d["decision"] for d in decisions)
    rep = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "jira_project": project, "dataset_label": settings.dataset_label, "target_release": release, "target": ctx.target,
        "incomplete_requirements": sum(1 for d in decisions if d.get("assessment_status") == "incomplete"),
        "overall_decision": overall(decisions), "decision_counts": dict(counts), "requirements": decisions,
        "run_integrity": {"degraded": bool(agent.warnings or ctx.errors or agent.llm.failures),
                          "warnings": agent.warnings, "tool_errors": ctx.errors, "llm_failures": agent.llm.failures},
        "metrics": metrics,
    }
    return rep


def to_markdown(rep):
    L = [f"# Release readiness report: {rep['target']['service']} {rep['target_release']}", "",
         f"**Overall decision: {rep['overall_decision']}**", "",
         *([f"> **INCOMPLETE RUN:** {rep['incomplete_requirements']} of {len(rep['requirements'])} requirements were not assessed "
            "(see Run integrity). This is not a valid readiness assessment."] + [""] if rep["incomplete_requirements"] else []),
         f"- Target: release `{rep['target']['release']}`, commit `{rep['target']['commit']}`, service `{rep['target']['service']}`, "
         f"environment `{rep['target']['environment']}`, prompt `{rep['target']['prompt']}`",
         f"- Jira project `{rep['jira_project']}`, dataset scope label `{rep['dataset_label']}`, generated {rep['generated_at']}",
         f"- Counts: " + ", ".join(f"{k} {v}" for k, v in sorted(rep["decision_counts"].items())), "",
         "| Requirement | Title | Decision |", "|---|---|---|"]
    for r in rep["requirements"]:
        L.append(f"| {r['requirement_id']} | {r['title']} | {r['decision']} |")
    for r in rep["requirements"]:
        L += ["", f"## {r['requirement_id']}: {r['title']} — {r['decision']}", "",
              f"Jira: [{r['requirement_key']}]({r['requirement_url']})  ", f"Acceptance criterion: {r['acceptance_criterion']}", "",
              r["rationale"], "", "**Evidence**"]
        if not r["evidence"]:
            L.append("- (none cited)")
        for e in r["evidence"]:
            who = f"{e.get('recorded_actor')} ({e.get('recorded_role')}), {e.get('recorded_event_time')}" if e.get("recorded_actor") else "ticket-level"
            ref = f"{e['source_id']} / {e['issue_key']}" + (f"#{e['comment_id']}" if e["comment_id"] else "")
            L.append(f"- [{ref}]({e['url']}) [{e['use']}] {who}: {e['note']}")
            if e.get("excerpt"):
                L.append(f"  > {e['excerpt'].replace(chr(10), ' ')}")
        if r["outstanding"]:
            L += ["", "**Outstanding verification / clarification**"] + [f"- {o}" for o in r["outstanding"]]
        if r.get("assessment_status") not in ("done", "forced"):
            L += ["", f"_Assessment status: {r['assessment_status']}_"]
    ri, m = rep["run_integrity"], rep["metrics"]
    L += ["", "## Run integrity", "", f"Degraded run: **{ri['degraded']}**"]
    for w in ri["warnings"]:
        L.append(f"- warning: {w}")
    for e in ri["tool_errors"]:
        L.append(f"- tool error in {e['requirement']}: `{e['tool']}` {e['error'][:160]}")
    for f in ri["llm_failures"]:
        L.append(f"- model failure ({f['provider']}, {f['scope']}): {f['error'][:160]}")
    L += ["", "## Metrics", "", f"- Wall time: {m['wall_seconds']} s (discovery {m['phase_seconds'].get('discovery')} s, assessment {m['phase_seconds'].get('assessment')} s)",
          f"- Tool calls: {m['tool_calls']}; Jira API calls: {m['jira_api_calls']} ({m['jira_api_failures']} failed); unique issues opened: {m['unique_issues_opened']}",
          "- Model usage: " + ("; ".join(f"{k}: {v['calls']} calls, {v['total_tokens']} tokens" for k, v in m["llm_usage"].items()) or "none")]
    return "\n".join(L) + "\n"