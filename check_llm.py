"""Pre-flight check of your LLM providers, exactly as the agent uses them (no Jira needed, costs a few cents/free-tier calls).
    python check_llm.py                      # all providers in LLM_PROVIDER_ORDER that have a key and model
    python check_llm.py --only gemini,openrouter
    python check_llm.py --only gemini --model gemini-3.5-flash     # try another model without editing .env
Each provider must pass 5 checks: plain chat, tool call, tool-result round trip, replay of a tool call made by ANOTHER provider
(this is what failover does and what broke Gemini 3), and forced tool choice (used for the final decision)."""
import argparse, json, sys, time
from config import get_settings
from llm import LLMRouter, Provider, build_providers
from tracing import Tracer

GET_ISSUE = {"type": "function", "function": {"name": "get_issue", "description": "Open an issue by key",
             "parameters": {"type": "object", "properties": {"ref": {"type": "string"}}, "required": ["ref"]}}}
SUBMIT = {"type": "function", "function": {"name": "submit_decision", "description": "Record a decision",
          "parameters": {"type": "object", "properties": {"decision": {"type": "string", "enum": ["PASS", "FAIL", "INSUFFICIENT_EVIDENCE"]},
                                                          "rationale": {"type": "string"}}, "required": ["decision", "rationale"]}}}
TOOL_RESULT = json.dumps({"key": "KAN-1", "summary": "demo issue", "jira_status": "Done"})

HINTS = [("thought_signature", "update llm.py from the latest releasepilot.zip (Gemini 3 needs thought signatures)"),
         ("404", "model name not available to your key: run `python list_models.py` and fix *_MODEL in .env"),
         ("402", "not enough credits for this model: use a ':free' model or lower LLM_MAX_TOKENS"),
         ("429", "rate-limited: wait a few minutes, use another model, or raise LLM_MIN_INTERVAL_SECONDS"),
         ("401", "API key rejected: check the key in .env"), ("403", "API key rejected or region blocked: check the key in .env"),
         ("timeout", "provider too slow: raise LLM_TIMEOUT_SECONDS or choose a lighter model"),
         ("503", "provider overloaded right now: retry later or use another provider")]


def hint(msg):
    return next((h for k, h in HINTS if k.lower() in msg.lower()), "see the error text above")


def check_provider(settings, p):
    router = LLMRouter(settings, Tracer(None), [p])
    rows, state = [], {}

    def step(name, fn):
        p.cooldown_until = 0.0
        t0 = time.time()
        try:
            detail = fn()
            rows.append((name, True, f"{time.time() - t0:.1f}s {detail or ''}".strip()))
        except Exception as e:  # noqa
            rows.append((name, False, str(e)[:260]))

    def plain():
        m, _ = router.chat([{"role": "user", "content": "Reply with the single word OK."}], None, "check")
        assert (m.get("content") or "").strip(), "empty answer (raise LLM_MAX_TOKENS if this is a thinking model)"
        return "answered"

    def tool_call():
        m, _ = router.chat([{"role": "system", "content": "Use tools when asked."},
                            {"role": "user", "content": "Open issue KAN-1 using the get_issue tool."}], [GET_ISSUE], "check")
        tcs = m.get("tool_calls") or []
        assert tcs and tcs[0]["function"]["name"] == "get_issue", "model did not call the tool"
        json.loads(tcs[0]["function"]["arguments"] or "{}")
        state["msg"] = m
        return "called get_issue"

    def roundtrip():
        m = state["msg"]
        router.chat([{"role": "user", "content": "Open issue KAN-1 using the get_issue tool."}, m,
                     {"role": "tool", "tool_call_id": m["tool_calls"][0]["id"], "name": "get_issue", "content": TOOL_RESULT}],
                    [GET_ISSUE], "check")
        return "accepted tool result"

    def foreign():
        foreign_call = {"role": "assistant", "content": "", "tool_calls": [{"id": "call_foreign1", "type": "function",
                        "function": {"name": "get_issue", "arguments": json.dumps({"ref": "KAN-1"})}}]}
        router.chat([{"role": "user", "content": "Open issue KAN-1 using the get_issue tool."}, foreign_call,
                     {"role": "tool", "tool_call_id": "call_foreign1", "name": "get_issue", "content": TOOL_RESULT}], [GET_ISSUE], "check")
        return "accepted another provider's tool call"

    def forced():
        m, _ = router.chat([{"role": "user", "content": "Record decision INSUFFICIENT_EVIDENCE with a short rationale."}], [SUBMIT], "check",
                           tool_choice="required")
        tcs = m.get("tool_calls") or []
        assert tcs and tcs[0]["function"]["name"] == "submit_decision", "forced tool choice not honoured"
        return "forced submit_decision"

    for name, fn in (("plain chat", plain), ("tool call", tool_call)):
        step(name, fn)
    if "msg" in state:
        step("tool-result round trip", roundtrip)
    else:
        rows.append(("tool-result round trip", False, "skipped (tool call failed)"))
    step("replay of another provider's tool call", foreign)
    step("forced tool choice", forced)
    return rows


def main():
    s = get_settings()
    ap = argparse.ArgumentParser(); ap.add_argument("--only", default="")
    ap.add_argument("--model", default="", help="override the model for the single provider in --only, e.g. --only gemini --model gemini-3.5-flash")
    a = ap.parse_args()
    wanted = [x.strip() for x in (a.only or s.llm_provider_order).split(",") if x.strip()]
    providers = {p.name: p for p in build_providers(s)}
    if a.model:
        if len(wanted) != 1 or wanted[0] not in providers:
            sys.exit("--model needs exactly one provider in --only (with its key set), e.g. --only gemini --model gemini-3.5-flash")
        providers[wanted[0]].model = a.model
    good = []
    for name in wanted:
        print(f"\n== {name}" + (f"  model={providers[name].model}" if name in providers else ""))
        if name not in providers:
            print("   SKIPPED: no API key or model set in .env"); continue
        rows = check_provider(s, providers[name])
        for n, ok, d in rows:
            print(f"   [{'OK' if ok else 'FAIL'}] {n}: {d}")
        bad = [d for _, ok, d in rows if not ok]
        if bad:
            print(f"   -> NOT READY. {hint(bad[0])}")
        else:
            print("   -> READY"); good.append(name)
        if name == "gemini":
            time.sleep(s.llm_min_interval_seconds)
    print("\n" + ("Working providers: " + ", ".join(good) + f"\nSuggested: LLM_PROVIDER_ORDER={','.join(good)}" if good
                  else "No provider passed. Fix the items above before running main.py."))
    sys.exit(0 if good else 1)


if __name__ == "__main__":
    main()