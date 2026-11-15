#!/usr/bin/env python3
"""Small Google Sheets CLI for the Codex Reels runner (uses a service account).

Usage (run from /opt/codex-reels with .env loaded):
  python3 tools/sheet.py get    "ตั้งค่า!A1:B22"        -> JSON 2D array of displayed values
  python3 tools/sheet.py all    "ประวัติโพสต์"           -> whole tab as JSON 2D array
  python3 tools/sheet.py tail   "ประวัติโพสต์" 40        -> header row + last N rows
  python3 tools/sheet.py set    "ค้นหา!B2" '[["ห้องครัว"]]'
  python3 tools/sheet.py append "ประวัติโพสต์" '["2026-11-16 11:07", "..."]'

Values for set/append may also be given as @path/to/file.json.
Writes use USER_ENTERED, so "=DATE(2026,11,16)" becomes a real formula/date.
"""
import json
import os
import sys

import gspread

SHEET_ID = os.environ.get("SHEET_ID", "1IKNyEA6vhfeQH8Z6SYcLMTHHv5_fsdO66cOYDSf1XtE")


def load_value(arg):
    if arg.startswith("@"):
        with open(arg[1:], encoding="utf-8") as f:
            return json.load(f)
    return json.loads(arg)


def split(target):
    if "!" not in target:
        sys.exit("target must look like 'Tab!A1:B2'")
    tab, rng = target.split("!", 1)
    return tab, rng


def out(data):
    print(json.dumps(data, ensure_ascii=False))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, target = sys.argv[1], sys.argv[2]
    gc = gspread.service_account(filename=os.environ["GSA_FILE"])
    sh = gc.open_by_key(SHEET_ID)

    if cmd == "get":
        tab, rng = split(target)
        out(sh.worksheet(tab).get(rng))
    elif cmd == "all":
        out(sh.worksheet(target).get_all_values())
    elif cmd == "tail":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
        rows = sh.worksheet(target).get_all_values()
        out(rows[:1] + rows[1:][-n:])
    elif cmd == "set":
        tab, rng = split(target)
        values = load_value(sys.argv[3])
        sh.worksheet(tab).update(range_name=rng, values=values, value_input_option="USER_ENTERED")
        out({"ok": True, "range": target})
    elif cmd == "append":
        row = load_value(sys.argv[3])
        sh.worksheet(target).append_row(row, value_input_option="USER_ENTERED")
        out({"ok": True, "tab": target})
    else:
        sys.exit("unknown command: " + cmd)


if __name__ == "__main__":
    main()
