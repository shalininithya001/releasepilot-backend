"""Print models your keys can actually use (tool-calling capable). Run: python list_models.py"""
import requests
from config import get_settings
s = get_settings()
if s.gemini_api_key:
    print("== Gemini models that support generateContent (use the name after 'models/')")
    r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": s.gemini_api_key, "pageSize": 200}, timeout=30)
    if r.ok:
        for m in r.json().get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m["name"]:
                print("  ", m["name"].replace("models/", ""))
    else:
        print("  error", r.status_code, r.text[:200])
print("\n== OpenRouter FREE models that support tools (use the full id)")
r = requests.get("https://openrouter.ai/api/v1/models", timeout=30)
if r.ok:
    for m in r.json().get("data", []):
        if m["id"].endswith(":free") and "tools" in (m.get("supported_parameters") or []):
            print("  ", m["id"])
if s.nvidia_api_key:
    print("\n== NVIDIA models")
    r = requests.get(f"{s.nvidia_base_url}/models", headers={"Authorization": f"Bearer {s.nvidia_api_key}"}, timeout=30)
    if r.ok:
        for m in r.json().get("data", []):
            if any(k in m["id"].lower() for k in ("llama-3.3", "llama-3.1-70b", "nemotron", "qwen", "mistral-large")):
                print("  ", m["id"])