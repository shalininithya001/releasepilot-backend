"""Find and (optionally) delete duplicate / pre-existing copies of the dataset in the project.

Default is a read-only report. Groups:
  mine      = created by import_jira.py (dataset label + an rr-* label)
  old       = other issues with kind-*/source-* labels or REC-n / REQ-n / MANIFEST in the summary (an earlier import)
  dup_mine  = extra copies of the same [source id] among 'mine' (the lowest Jira key is kept)
  other     = everything else in the project (never touched)
Usage:  python cleanup_jira.py                       # report only
        python cleanup_jira.py --delete-old --delete-dup-mine
        python cleanup_jira.py --delete-all                  # wipe the whole project for a fresh import
"""
import argparse, re, collections
from concurrent.futures import ThreadPoolExecutor
from config import get_settings
from jira_client import JiraClient, source_id_of

SRC = re.compile(r"\b(REC-\d+|REQ-\d+|MANIFEST)\b")


def classify(jira, s):
    issues = jira.search(f'project = "{s.jira_project_key}"', "summary,labels", limit=5000)
    mine, old, other = [], [], []
    for i in issues:
        labels, summ = i["fields"].get("labels") or [], i["fields"]["summary"] or ""
        if s.dataset_label in labels and any(l.startswith("rr-") for l in labels):
            mine.append(i)
        elif SRC.search(summ) or any(l.startswith(("kind-", "source-")) for l in labels):
            old.append(i)
        else:
            other.append(i)
    num = lambda i: int(i["key"].split("-")[1])
    groups = collections.defaultdict(list)
    for i in mine:
        groups[source_id_of(i["fields"]["summary"])].append(i)
    dup = [i for g in groups.values() for i in sorted(g, key=num)[1:]]
    return issues, mine, old, other, dup


def show(name, items, n=3):
    print(f"\n{name}: {len(items)}")
    for i in items[:n]:
        print(f"   {i['key']}  {i['fields']['summary'][:70]!r}  labels={i['fields'].get('labels')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delete-old", action="store_true")
    ap.add_argument("--delete-dup-mine", action="store_true")
    ap.add_argument("--delete-all", action="store_true", help="delete EVERY issue in the project (fresh start)")
    a = ap.parse_args()
    s = get_settings(); jira = JiraClient(s)
    issues, mine, old, other, dup = classify(jira, s)
    print(f"Project {s.jira_project_key}: {len(issues)} issues in total")
    show("mine (from import_jira.py)", mine); show("old (earlier import, no dataset label / [ID] prefix)", old)
    show("dup_mine (extra copies of the same source id)", dup); show("other (left alone)", other)
    todo = issues if a.delete_all else (old if a.delete_old else []) + (dup if a.delete_dup_mine else [])
    if not todo:
        print("\nReport only. Re-run with --delete-old and/or --delete-dup-mine to delete."); return
    word = "DELETE ALL" if a.delete_all else "DELETE"
    if input(f"\nPermanently delete {len(todo)} issues from project {s.jira_project_key}? Type {word} to confirm: ").strip() != word:
        print("Aborted."); return
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda i: jira.delete_issue(i["key"]), todo))
    print(f"Deleted {len(todo)} issues. Wait ~1 minute for Jira's search index, then run import_jira.py to finish the import.")


if __name__ == "__main__":
    main()