import json, time, threading


class Tracer:
    def __init__(self, path=None):
        self.path, self.t0, self.events, self._l = path, time.time(), [], threading.Lock()
        if path:
            open(path, "w").close()

    def _emit(self, ev):
        ev["t"] = round(time.time() - self.t0, 2)
        with self._l:
            self.events.append(ev)
            if self.path:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def tool(self, scope, name, args, result_text, ok, secs):
        self._emit({"type": "tool_call", "scope": scope, "tool": name, "args": args, "ok": ok,
                    "latency_s": round(secs, 3), "result_preview": result_text[:500]})

    def llm(self, scope, provider, model, usage, secs, note=""):
        self._emit({"type": "llm_call", "scope": scope, "provider": provider, "model": model,
                    "usage": usage, "latency_s": round(secs, 3), "note": note})

    def note(self, scope, msg, level="info"):
        self._emit({"type": level, "scope": scope, "message": msg})
