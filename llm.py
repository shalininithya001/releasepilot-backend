"""One OpenAI-compatible adapter for Gemini, OpenRouter, NVIDIA NIM and Ollama, with retry and provider failover."""
import json, time, uuid, logging
import requests

log = logging.getLogger("llm")


class LLMUnavailable(Exception):
    pass


class Provider:
    def __init__(self, name, base_url, key, model, headers=None):
        self.name, self.base_url, self.key, self.model = name, base_url.rstrip("/"), key, model
        self.headers = headers or {}
        self.last_call = 0.0
        self.cooldown_until = 0.0


def build_providers(s):
    reg = {
        "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", s.gemini_api_key, s.gemini_model, {}),
        "openrouter": (s.openrouter_base_url, s.openrouter_api_key, s.openrouter_model, {"X-Title": "ReleasePilot"}),
        "nvidia": (s.nvidia_base_url, s.nvidia_api_key, s.nvidia_model, {}),
        "ollama": (s.ollama_base_url + "/v1", "ollama", s.ollama_model, {}),
    }
    out = []
    for name in [x.strip() for x in s.llm_provider_order.split(",") if x.strip()]:
        if name in reg:
            base, key, model, h = reg[name]
            if key and model:
                out.append(Provider(name, base, key, model, h))
    return out


class LLMRouter:
    def __init__(self, settings, tracer, providers=None):
        self.s, self.tracer = settings, tracer
        self.providers = providers if providers is not None else build_providers(settings)
        self.usage = {}      # provider -> {calls, prompt_tokens, completion_tokens, total_tokens, failures}
        self.failures = []

    def _u(self, name):
        return self.usage.setdefault(name, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "failures": 0})

    def chat(self, messages, tools, scope="", tool_choice="auto"):
        if not self.providers:
            raise LLMUnavailable("no LLM provider configured (set a key and model in .env)")
        errors = []
        now = time.time()
        live = [p for p in self.providers if p.cooldown_until < 1e9]          # not permanently disabled
        if live and all(time.time() < p.cooldown_until for p in live):
            wait = min(p.cooldown_until for p in live) - time.time()
            if wait <= 120:
                self.tracer.note(scope, f"all providers cooling down; waiting {wait:.0f}s", "warning")
                time.sleep(max(wait, 0))
        for p in self.providers:
            if time.time() < p.cooldown_until:
                errors.append(f"{p.name}: cooling down")
                continue
            try:
                return self._call(p, messages, tools, scope, tool_choice)
            except Exception as e:  # noqa
                self._u(p.name)["failures"] += 1
                if p.cooldown_until < 1e9 and not str(e).startswith("HTTP 4"):
                    p.cooldown_until = time.time() + self.s.llm_provider_cooldown_seconds   # circuit breaker
                errors.append(f"{p.name}: {e}")
                self.failures.append({"scope": scope, "provider": p.name, "error": str(e)[:300]})
                self.tracer.note(scope, f"provider {p.name} failed: {str(e)[:200]}", "warning")
        raise LLMUnavailable("; ".join(errors)[:600])

    @staticmethod
    def _prepare(p, messages):
        """Gemini 3 needs a thought_signature on every replayed tool call; other providers must not see extra_content."""
        out = []
        for m in messages:
            if m.get("tool_calls"):
                m = dict(m); tcs = []
                for tc in m["tool_calls"]:
                    tc = dict(tc)
                    if p.name == "gemini":
                        if not ((tc.get("extra_content") or {}).get("google") or {}).get("thought_signature"):
                            tc["extra_content"] = {"google": {"thought_signature": "skip_thought_signature_validator"}}
                    else:
                        tc.pop("extra_content", None)
                    tcs.append(tc)
                m["tool_calls"] = tcs
            out.append(m)
        return out

    def _call(self, p, messages, tools, scope, tool_choice):
        body = {"model": p.model, "messages": self._prepare(p, messages), "temperature": 0.1, "max_tokens": self.s.llm_max_tokens}
        if tools:
            body["tools"], body["tool_choice"] = tools, tool_choice
        headers = {"Authorization": f"Bearer {p.key}", "Content-Type": "application/json", **p.headers}
        last = None
        for attempt in range(3):
            wait = p.last_call + self.s.llm_min_interval_seconds - time.time() if p.name == "gemini" else 0
            if wait > 0:
                time.sleep(wait)
            t0 = time.time()
            p.last_call = time.time()
            try:
                r = requests.post(f"{p.base_url}/chat/completions", headers=headers, json=body, timeout=self.s.llm_timeout_seconds)
            except requests.Timeout as e:
                raise RuntimeError(f"timeout after {self.s.llm_timeout_seconds}s; failing over")
            except requests.RequestException as e:
                last = f"network: {e}"; time.sleep(2 ** attempt); continue
            if r.status_code == 429 or r.status_code >= 500:
                ra = r.headers.get("Retry-After")
                delay = float(ra) if ra and ra.replace(".", "").isdigit() else 4 * (2 ** attempt)
                last = f"HTTP {r.status_code}"
                if delay > 20 or (r.status_code == 429 and attempt >= 1):
                    p.cooldown_until = time.time() + delay
                    raise RuntimeError(f"{last}; asked to wait {delay:.0f}s, failing over")
                time.sleep(delay); continue
            if r.status_code == 400 and body.get("tool_choice") == "required":
                body["tool_choice"] = "auto"; last = "400 with tool_choice=required; retrying auto"; continue
            if r.status_code in (401, 403, 404):
                p.cooldown_until = time.time() + 10 ** 9   # misconfigured key/model: do not retry for the rest of the run
                raise RuntimeError(f"HTTP {r.status_code} (provider disabled for this run; check key/model): {r.text[:200]}")
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            data = r.json()
            if not data.get("choices"):
                last = f"empty choices: {str(data)[:150]}"; time.sleep(2); continue
            msg = data["choices"][0]["message"]
            usage = data.get("usage") or {}
            u = self._u(p.name)
            u["calls"] += 1
            for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                u[k] += int(usage.get(k) or 0)
            self.tracer.llm(scope, p.name, p.model, usage, time.time() - t0)
            calls = []
            for tc in msg.get("tool_calls") or []:
                c = {"id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}", "type": "function",
                     "function": {"name": tc["function"]["name"], "arguments": tc["function"].get("arguments") or "{}"}}
                if tc.get("extra_content"):
                    c["extra_content"] = tc["extra_content"]
                calls.append(c)
            return {"role": "assistant", "content": msg.get("content") or "", **({"tool_calls": calls} if calls else {})}, p.name
        raise RuntimeError(f"gave up after retries: {last}")