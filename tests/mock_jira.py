"""Minimal in-memory Jira Cloud mock (only the endpoints we use) for offline tests."""
import json, re, threading, itertools
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


def adf_text(n):
    out = []
    def w(x):
        if isinstance(x, dict):
            if x.get("type") == "text": out.append(x["text"])
            for c in x.get("content", []) or []: w(c)
            if x.get("type") == "paragraph": out.append("\n")
        elif isinstance(x, list):
            for c in x: w(c)
    w(n); return "".join(out).rstrip("\n")


class State:
    def __init__(self):
        self.issues, self.n, self.cid, self.lid = {}, itertools.count(1), itertools.count(10000), itertools.count(500)
        self.lock = threading.Lock()


def make_handler(st, project="KAN"):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, obj):
            b = json.dumps(obj).encode(); self.send_response(code)
            self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b)
        def _body(self):
            n = int(self.headers.get("Content-Length") or 0); return json.loads(self.rfile.read(n) or b"{}")
        def _render(self, i):
            f = {"summary": i["summary"], "labels": i["labels"], "status": {"name": i["status"]},
                 "description": i["description"], "issuelinks": [], "comment": {"total": len(i["comments"]), "comments": []}}
            for lk in i["links"]:
                other = st.issues[lk["other"]]
                d = {"id": lk["id"], "type": {"name": "Relates"}}
                d["outwardIssue" if lk["dir"] == "out" else "inwardIssue"] = {"key": other["key"], "fields": {"summary": other["summary"], "status": {"name": other["status"]}}}
                f["issuelinks"].append(d)
            return {"key": i["key"], "fields": f}
        def do_GET(self):
            p = urlparse(self.path).path.replace("/rest/api/3", "")
            m = re.match(r"/issue/([A-Z]+-\d+)/comment$", p)
            if m:
                i = st.issues[m.group(1)]; return self._send(200, {"total": len(i["comments"]), "comments": [{"id": c["id"], "body": c["body"]} for c in i["comments"]]})
            m = re.match(r"/issue/([A-Z]+-\d+)/transitions$", p)
            if m: return self._send(200, {"transitions": [{"id": "1", "to": {"name": "In Progress"}}, {"id": "2", "to": {"name": "Done"}}, {"id": "3", "to": {"name": "To Do"}}]})
            m = re.match(r"/issue/([A-Z]+-\d+)$", p)
            if m:
                if m.group(1) not in st.issues: return self._send(404, {"errorMessages": ["nope"]})
                return self._send(200, self._render(st.issues[m.group(1)]))
            self._send(404, {})
        def do_POST(self):
            p = urlparse(self.path).path.replace("/rest/api/3", ""); b = self._body()
            with st.lock:
                if p == "/issue":
                    f = b["fields"]; k = f"{project}-{next(st.n)}"
                    st.issues[k] = {"key": k, "summary": f["summary"], "labels": f["labels"], "status": "To Do", "description": f["description"], "comments": [], "links": []}
                    return self._send(201, {"key": k})
                m = re.match(r"/issue/([A-Z]+-\d+)/comment$", p)
                if m:
                    c = {"id": str(next(st.cid)), "body": b["body"]}; st.issues[m.group(1)]["comments"].append(c); return self._send(201, c)
                if p == "/issueLink":
                    o, i = b["outwardIssue"]["key"], b["inwardIssue"]["key"]; lid = str(next(st.lid))
                    st.issues[o]["links"].append({"id": lid, "other": i, "dir": "out"}); st.issues[i]["links"].append({"id": lid, "other": o, "dir": "in"})
                    return self._send(201, {})
                m = re.match(r"/issue/([A-Z]+-\d+)/transitions$", p)
                if m:
                    st.issues[m.group(1)]["status"] = {"1": "In Progress", "2": "Done", "3": "To Do"}[b["transition"]["id"]]; return self._send(204, {})
                if p == "/search/jql":
                    jql = b["jql"]; res = list(st.issues.values())
                    for lab in re.findall(r'labels = "([^"]+)"', jql): res = [i for i in res if lab in i["labels"]]
                    for q in re.findall(r'text ~ "([^"]+)"', jql): res = [i for i in res if q.lower() in (i["summary"] + adf_text(i["description"])).lower()]
                    start = int(b.get("nextPageToken") or 0); size = b.get("maxResults", 50); page = res[start:start + size]
                    out = {"issues": [self._render(i) for i in page]}
                    if start + size < len(res): out["nextPageToken"] = str(start + size)
                    return self._send(200, out)
            self._send(404, {})
    return H


def start_mock():
    st = State(); srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(st)); threading.Thread(target=srv.serve_forever, daemon=True).start()
    return st, srv, f"http://127.0.0.1:{srv.server_address[1]}"
