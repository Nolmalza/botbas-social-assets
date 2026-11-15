#!/usr/bin/env python3
"""Make.com helper for the Codex Reels runner (no extra packages needed).

Usage (run from /opt/codex-reels with .env loaded):
  python3 tools/make.py run <job.json> <caption.txt> <comment.txt> [page_id]
        -> starts scenario 6940105 (render on VPS + post Reel + first comment),
           prints {"executionId": ...}. Retries once after 3 min if the
           scenario is already running.
  python3 tools/make.py status <executionId>   -> prints the execution JSON
  python3 tools/make.py wait <executionId>
        -> sleeps 540 s, then checks; if still running waits 240 s and checks
           again; at most 3 checks. Exit code 0 = success, 2 = error,
           3 = still running (unconfirmed). Never re-runs anything.

Env: MAKE_TOKEN (API token with scenarios:run, scenarios:read, executions:read),
     MAKE_ZONE (default us2.make.com), MAKE_SCENARIO (default 6940105),
     PAGE_ID (default 1373565455841925).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

ZONE = os.environ.get("MAKE_ZONE", "us2.make.com")
SCENARIO = os.environ.get("MAKE_SCENARIO", "6940105")
PAGE_ID = os.environ.get("PAGE_ID", "1373565455841925")
BASE = f"https://{ZONE}/api/v2"


def call(method, path, body=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Authorization", "Token " + os.environ["MAKE_TOKEN"])
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(text)
        except ValueError:
            return e.code, {"raw": text}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def run(job_path, caption_path, comment_path, page_id=PAGE_ID):
    job = read(job_path).strip()
    json.loads(job)  # must be valid JSON
    body = {
        "responsive": False,
        "data": {
            "job_json": job,
            "page_id": page_id,
            "caption": read(caption_path).strip(),
            "comment": read(comment_path).strip(),
        },
    }
    for attempt in (1, 2):
        code, res = call("POST", f"/scenarios/{SCENARIO}/run", body)
        if code < 300 and res.get("executionId"):
            print(json.dumps({"executionId": res["executionId"]}))
            return 0
        busy = "already" in json.dumps(res).lower()
        if attempt == 1 and busy:
            time.sleep(180)
            continue
        print(json.dumps({"error": code, "response": res}, ensure_ascii=False))
        return 1
    return 1


def state(res):
    s = str(res.get("status", "")).lower()
    if s in ("success", "1", "warning", "2"):
        return "success"
    if s in ("error", "3", "failed"):
        return "error"
    return "running"


def status(exec_id):
    code, res = call("GET", f"/scenarios/{SCENARIO}/executions/{exec_id}")
    res["_http"] = code
    return res


def wait(exec_id):
    waits = [540, 240, 240]
    res = {}
    for i, sec in enumerate(waits, 1):
        time.sleep(sec)
        res = status(exec_id)
        st = state(res)
        print(json.dumps({"check": i, "state": st, "execution": res}, ensure_ascii=False))
        if st == "success":
            return 0
        if st == "error":
            return 2
    return 3


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "run":
        sys.exit(run(*sys.argv[2:6]))
    if cmd == "status":
        print(json.dumps(status(sys.argv[2]), ensure_ascii=False))
        return
    if cmd == "wait":
        sys.exit(wait(sys.argv[2]))
    sys.exit("unknown command: " + cmd)


if __name__ == "__main__":
    main()
