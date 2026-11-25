"""Thin Jira Cloud REST client: retry/backoff, ADF helpers, scoped search."""
import re, time, logging, threading
import requests
from requests.auth import HTTPBasicAuth

log = logging.getLogger("jira")


class JiraError(Exception):
    pass


def adf_doc(text: str) -> dict:
    """Plain text -> ADF, one paragraph per line (verbatim round-trip)."""
    paras = []
    for line in text.split("\n"):
        paras.append({"type": "paragraph", "content": [{"type": "text", "text": line}] if line else []})
    return {"type": "doc", "version": 1, "content": paras}


def adf_to_text(node) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    out = []

    def walk(n):
        if isinstance(n, dict):
            t = n.get("type")
            if t == "text":
                out.append(n.get("text", ""))
            elif t == "hardBreak":
                out.append("\n")
            for c in n.get("content", []) or []:
                walk(c)
            if t in ("paragraph", "heading", "listItem", "codeBlock"):
                out.append("\n")
        elif isinstance(n, list):
            for c in n:
                walk(c)
    walk(node)
    return "".join(out).rstrip("\n")


class JiraClient:
    def __init__(self, s):
        self.base = s.jira_base_url
        self.project = s.jira_project_key
        self.label = s.dataset_label
        self.timeout = s.jira_timeout_seconds
        self.retries = s.jira_max_retries
        self.backoff = s.jira_retry_backoff_seconds
        self.http = requests.Session()
        self.http.auth = HTTPBasicAuth(s.jira_email, s.jira_api_token)
        self.http.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        self.calls = 0
        self.failures = 0
        self._lock = threading.Lock()

    # ---- low level -------------------------------------------------
    def request(self, method, path, **kw):
        url = f"{self.base}/rest/api/3{path}"
        last = None
        for attempt in range(self.retries + 1):
            with self._lock:
                self.calls += 1
            try:
                r = self.http.request(method, url, timeout=self.timeout, **kw)
            except requests.RequestException as e:
                last = f"network error: {e}"
            else:
                if r.status_code in (429, 500, 502, 503, 504):
                    last = f"HTTP {r.status_code}: {r.text[:200]}"
                    wait = float(r.headers.get("Retry-After") or self.backoff * (2 ** attempt))
                    time.sleep(min(wait, 30))
                    continue
                if r.status_code >= 400:
                    with self._lock:
                        self.failures += 1
                    raise JiraError(f"{method} {path} -> HTTP {r.status_code}: {r.text[:300]}")
                return r.json() if r.text.strip() else {}
            time.sleep(self.backoff * (2 ** attempt))
        with self._lock:
            self.failures += 1
        raise JiraError(f"{method} {path} failed after retries: {last}")

    # ---- reads -----------------------------------------------------
    def scoped(self, extra: str = "") -> str:
        jql = f'project = "{self.project}" AND labels = "{self.label}"'
        return f"{jql} AND {extra}" if extra else jql

    def search(self, jql, fields, limit=1000):
        out, token = [], None
        while len(out) < limit:
            body = {"jql": jql, "fields": fields.split(",") if isinstance(fields, str) else fields,
                    "maxResults": min(100, limit - len(out))}
            if token:
                body["nextPageToken"] = token
            d = self.request("POST", "/search/jql", json=body)
            out += d.get("issues", [])
            token = d.get("nextPageToken")
            if not token or not d.get("issues"):
                break
        return out

    def get_issue(self, key, fields="summary,description,status,labels,issuelinks,comment,created"):
        return self.request("GET", f"/issue/{key}", params={"fields": fields})

    def get_comments(self, key):
        out, start = [], 0
        while True:
            d = self.request("GET", f"/issue/{key}/comment", params={"startAt": start, "maxResults": 100, "orderBy": "created"})
            out += d.get("comments", [])
            start += len(d.get("comments", []))
            if not d.get("comments") or start >= d.get("total", 0):
                break
        return out

    # ---- writes (importer only) -----------------------------------
    def create_issue(self, summary, description, labels, issue_type):
        return self.request("POST", "/issue", json={"fields": {
            "project": {"key": self.project}, "summary": summary[:250], "issuetype": {"name": issue_type},
            "description": adf_doc(description), "labels": labels}})

    def add_comment(self, key, text):
        return self.request("POST", f"/issue/{key}/comment", json={"body": adf_doc(text)})

    def create_link(self, link_type, outward_key, inward_key):
        # "outwardIssue" is the issue on the outward side of the phrase (e.g. "relates to")
        return self.request("POST", "/issueLink", json={"type": {"name": link_type},
                            "inwardIssue": {"key": inward_key}, "outwardIssue": {"key": outward_key}})

    def delete_issue(self, key):
        return self.request("DELETE", f"/issue/{key}", params={"deleteSubtasks": "true"})

    def transition_to(self, key, status_name):
        d = self.request("GET", f"/issue/{key}/transitions")
        for t in d.get("transitions", []):
            if t["to"]["name"].lower() == status_name.lower():
                self.request("POST", f"/issue/{key}/transitions", json={"transition": {"id": t["id"]}})
                return True
        return False


SRC_RE = re.compile(r"^\[([A-Za-z0-9_\-]+)\]")


def source_id_of(summary: str):
    m = SRC_RE.match(summary or "")
    return m.group(1) if m else None