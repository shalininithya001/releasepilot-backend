import json, os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tests.mock_jira import start_mock
from config import Settings
from jira_client import JiraClient
from tracing import Tracer
from tools import execute, extract_scope, parse_comment
from agent import Agent, overall

ROOT = os.path.dirname(os.path.dirname(__file__))


def settings(url):
    return Settings(_env_file=None, jira_base_url=url, jira_email="a", jira_api_token="b")


def run_import(url, *extra):
    env = {**os.environ, "JIRA_BASE_URL": url, "JIRA_EMAIL": "a", "JIRA_API_TOKEN": "b", "JIRA_RETRY_BACKOFF_SECONDS": "0.1"}
    r = subprocess.run([sys.executable, "import_jira.py", *extra], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-1500:]
    return r.stderr + r.stdout


def test_import_is_idempotent_and_complete():
    st, srv, url = start_mock()
    d = json.load(open(os.path.join(ROOT, "dataset.json")))
    out = run_import(url)
    assert len(st.issues) == 400 and sum(len(i["comments"]) for i in st.issues.values()) == 2059
    assert "VERIFY issues=400/400 comments=2059/2059" in out
    n_links = sum(len(i["links"]) for i in st.issues.values()) // 2
    assert n_links == sum(len(r["links"]) for r in d["records"])
    run_import(url)
    assert len(st.issues) == 400 and sum(len(i["comments"]) for i in st.issues.values()) == 2059
    assert sum(len(i["links"]) for i in st.issues.values()) // 2 == n_links
    assert all("tyn-release-assessment-v2" in i["labels"] for i in st.issues.values())
    assert sum("rr-requirement" in i["labels"] for i in st.issues.values()) == 12
    srv.shutdown()


class ScriptedLLM:
    """Stand-in model: opens requirement links, runs check_applicability, then submits INSUFFICIENT."""
    def __init__(self, getter):
        self.g, self.providers, self.failures, self.tracer = getter, [], [], None
        self.usage = {"fake": {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "failures": 0}}

    def chat(self, messages, tools, scope="", tool_choice="auto"):
        self.usage["fake"]["calls"] += 1
        names = [t["function"]["name"] for t in tools]
        tool_msgs = [m for m in messages if m["role"] == "tool"]
        mk = lambda n, a: ({"role": "assistant", "content": "", "tool_calls": [{"id": f"c{len(messages)}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}]}, "fake")
        if "declare_requirements" in names:
            if not tool_msgs:
                return mk("get_target_manifest", {})
            man = json.loads(tool_msgs[0]["content"])
            return mk("declare_requirements", {"requirements": [l["source_id"] for l in man["linked_requirements"]]})
        ctx = self.g(); rk = ctx.current_req
        links = [l["source_id"] for l in ctx._load(rk)["links"]]
        blob = json.dumps(messages[2:])
        for l in links:
            if f'\\"ref\\": \\"{l}\\"' not in blob:
                return mk("get_issue", {"ref": l})
        if "comments_with_scope" not in blob and links:
            return mk("check_applicability", {"ref": links[0]})
        cid = ctx.fetched[ctx.resolve(links[0])]["data"]["comments"][0]["ref"]
        return mk("submit_decision", {"requirement": rk, "decision": "INSUFFICIENT_EVIDENCE", "rationale": "scripted test decision for plumbing only",
                                      "evidence_refs": [{"ref": cid, "use": "context", "note": "n"}]})


def test_agent_pipeline_with_scripted_llm(tmp_path):
    st, srv, url = start_mock(); run_import(url, "--no-transition")
    s = settings(url); jira = JiraClient(s); tr = Tracer(str(tmp_path / "t.jsonl"))
    holder = {}
    llm = ScriptedLLM(lambda: holder["a"].ctx); llm.tracer = tr
    agent = Agent(s, jira, llm, tr); holder["a"] = agent
    decisions = agent.run("R2.4")
    assert len(decisions) == 12 and all(d["decision"] == "INSUFFICIENT_EVIDENCE" for d in decisions)
    assert overall(decisions) == "NEEDS_REVIEW"
    assert agent.ctx.target["commit"] == "b7a91f2" and len(agent.ctx.fetched) < 60
    assert not agent.warnings, agent.warnings
    ctx = agent.ctx
    _, ok = execute(ctx, "submit_decision", {"requirement": "REQ-01", "decision": "PASS", "rationale": "x" * 40, "evidence_refs": []}, "t")
    assert not ok
    _, ok = execute(ctx, "get_issue", {"ref": "KAN-99999"}, "t")
    assert not ok
    srv.shutdown()


def test_applicability_parsing_on_real_dataset_comments():
    e = extract_scope("Isolation verification ISO-290: release R2.3; commit 42d09ce; service atlas-assistant; environment production. 40 of 40 isolation cases pass.")
    assert (e["release"], e["commit"], e["service"], e["environment"]) == ("R2.3", "42d09ce", "atlas-assistant", "production")
    e = extract_scope("Approved: release R2.4, commit b7a91f2, service atlas-assistant. Approval scope: staging. Production sign-off scheduled.")
    assert e["service"] == "atlas-assistant" and e["approval_scope"] == "staging"
    e = extract_scope("Evaluation EVAL-55 harness configured with prompt bundle p6 (frozen on 2026-11-01).")
    assert e["prompt_bundle_declared"] == "p6" and e["prompt"] is None
    p = parse_comment("Recorded event 2026-11-08T14:00:00+05:30 | actor Priya Nair | role QA Lead\nhello")
    assert (p["actor"], p["role"], p["text"]) == ("Priya Nair", "QA Lead", "hello")
