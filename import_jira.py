"""Repeatable, idempotent importer: issues -> links -> comments -> (optional) status transitions.

Source IDs live in the summary as "[REC-1234] ..." and in the description. Original comment text
(with actor, role and event time) is written verbatim; native Jira author/time are the importer's.
"""
import argparse, json, logging, sys
from concurrent.futures import ThreadPoolExecutor
from config import get_settings
from jira_client import JiraClient, adf_to_text, source_id_of

log = logging.getLogger("import")
KIND_LABEL = {"requirement": "rr-requirement", "manifest": "rr-manifest", "evidence": "rr-evidence", "work": "rr-work"}


def build_description(r):
    head = (f"Source ID: {r['source_id']}\nKind: {r['kind']}\nRelease: {r['release']}\n"
            f"Recorded status: {r['recorded_status']}\n---\n")
    return head + r["description"]


def labels_for(r, dataset_label):
    return [dataset_label, KIND_LABEL.get(r["kind"], "rr-other"), "release-" + str(r["release"]).replace(" ", "_")]


def load_existing(jira):
    """source_id -> {key, links:set(source_ids-or-keys), comment_texts:list}"""
    issues = jira.search(jira.scoped(), "summary,issuelinks,status,comment")
    by_key = {i["key"]: i for i in issues}
    idx = {}
    for i in issues:
        sid = source_id_of(i["fields"]["summary"])
        if sid:
            idx[sid] = {"key": i["key"], "status": i["fields"]["status"]["name"], "issue": i}
    return idx, by_key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-transition", action="store_true", help="skip setting Jira status to recorded_status")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    s = get_settings()
    data = json.load(open(a.dataset, encoding="utf-8"))
    if data["dataset_label"] != s.dataset_label:
        sys.exit(f"DATASET_LABEL mismatch: env={s.dataset_label} dataset={data['dataset_label']}")
    recs = data["records"]
    ids = [r["source_id"] for r in recs]
    assert len(ids) == len(set(ids)), "duplicate source_ids in dataset"
    jira = JiraClient(s)
    idx, by_key = load_existing(jira)
    log.info("dataset: %d records, %d comments; already in Jira: %d", len(recs), sum(len(r["comments"]) for r in recs), len(idx))
    if a.dry_run:
        log.info("dry run: would create %d issues", len([i for i in ids if i not in idx]))
        return

    # 1. issues
    def mk(r):
        res = jira.create_issue(f"[{r['source_id']}] {r['summary']}", build_description(r),
                                labels_for(r, s.dataset_label), s.jira_issue_type)
        return r["source_id"], res["key"]
    todo = [r for r in recs if r["source_id"] not in idx]
    with ThreadPoolExecutor(a.workers) as ex:
        for n, (sid, key) in enumerate(ex.map(mk, todo), 1):
            idx[sid] = {"key": key, "status": "To Do", "issue": None}
            if n % 50 == 0:
                log.info("created %d/%d issues", n, len(todo))
    key_of = {sid: v["key"] for sid, v in idx.items()}

    # 2. links (skip pairs that already exist in either direction)
    existing_pairs = set()
    for k, i in by_key.items():
        for l in i["fields"].get("issuelinks") or []:
            other = (l.get("outwardIssue") or l.get("inwardIssue") or {}).get("key")
            if other:
                existing_pairs.add(frozenset((k, other)))
    made = 0
    for r in recs:
        for tgt in r["links"]:
            pair = frozenset((key_of[r["source_id"]], key_of[tgt]))
            if pair in existing_pairs:
                continue
            jira.create_link(s.jira_link_type, key_of[r["source_id"]], key_of[tgt])
            existing_pairs.add(pair); made += 1
    log.info("links created: %d", made)

    # 3. comments (append only the ones missing, preserving dataset order)
    def do_comments(r):
        key = key_of[r["source_id"]]
        have = [adf_to_text(c["body"]) for c in jira.get_comments(key)] if idx[r["source_id"]]["issue"] else []
        if have != r["comments"][:len(have)]:
            log.warning("%s: existing comments differ from dataset prefix; appending only the missing tail", r["source_id"])
        added = 0
        for text in r["comments"][len(have):]:
            jira.add_comment(key, text); added += 1
        return added
    with ThreadPoolExecutor(a.workers) as ex:
        total = sum(ex.map(do_comments, recs))
    log.info("comments added: %d", total)

    # 4. statuses (best effort; the recorded status is also in the description)
    if not a.no_transition:
        bad = 0
        for r in recs:
            cur = idx[r["source_id"]]["status"]
            if cur.lower() != r["recorded_status"].lower():
                try:
                    if not jira.transition_to(key_of[r["source_id"]], r["recorded_status"]):
                        bad += 1
                except Exception as e:  # noqa
                    bad += 1; log.warning("transition failed %s: %s", r["source_id"], e)
        log.info("status transitions not applied: %d", bad)

    # 5. verify
    idx2, by_key2 = load_existing(jira)
    n_comments = sum((i["fields"].get("comment") or {}).get("total", 0) for i in by_key2.values())
    log.info("VERIFY issues=%d/%d comments=%d/%d", len(idx2), len(recs), n_comments, sum(len(r["comments"]) for r in recs))
    log.info("Jira API calls=%d failures=%d", jira.calls, jira.failures)


if __name__ == "__main__":
    main()
