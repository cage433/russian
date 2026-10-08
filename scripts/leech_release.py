#!/usr/bin/env python3
"""Leech list + release: words Alex untags become fresh new cards.

  leech_release.py --snapshot   write tutoring/leeches.md (readable) and tutoring/leeches.json
                                (the list the release step diffs against) from the current
                                `tag:leech` notes
  leech_release.py [--dry-run]  release every note in the snapshot that no longer has the tag:
                                Forget all its cards, zero reps/lapses (a kept 8+ would re-leech
                                on the next fail), unsuspend, and put them at the FRONT of the
                                deck's new queue — production (ord 0) cards first, the other
                                direction behind them — so they come in over the following weeks
                                at the deck's own new/day rate. Then rewrites the snapshot.

Alex's call, 2026-10-08: many leeches are "words I pretty much know now with the occasional
fail". He untags those in the browser; they come back as new words rather than being
restructured. Prior card state goes to tutoring/retired/leech-released-*.json.
"""
import argparse
import datetime
import json
import re
import sys
import time

sys.path.insert(0, "scripts")
import anki_utils as a  # noqa: E402

a.use_venv()

SNAP_JSON = "tutoring/leeches.json"
SNAP_MD = "tutoring/leeches.md"
K = ["type", "queue", "due", "ivl", "factor", "reps", "lapses", "left"]


def plain(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"\[sound:[^\]]*\]", "", html))).strip()


def card_summary(c, revs):
    r = [x for x in revs if x["type"] != 4 and x["ease"] > 0]
    streak = 0
    for x in reversed(r):
        if x["ease"] == 1:
            break
        if x["type"] == 1:
            streak += 1
    fails = [x["id"] for x in r if x["ease"] == 1 and x["type"] in (1, 2)]
    last_fail = datetime.date.fromtimestamp(fails[-1] / 1000).isoformat() if fails else "—"
    state = "suspended" if c["queue"] == -1 else "new" if c["type"] == 0 else f"{c['interval']}d"
    return {"state": state, "lapses": c["lapses"], "streak": streak, "last_fail": last_fail}


def snapshot():
    nids = a.call("findNotes", query="tag:leech")
    notes = a.call("notesInfo", notes=nids)
    cids = [c for n in notes for c in n["cards"]]
    cards = {c["cardId"]: c for c in a.call("cardsInfo", cards=cids)} if cids else {}
    revs = a.call("getReviewsOfCards", cards=cids) if cids else {}
    out = {}
    for n in notes:
        f = n["fields"]
        front = plain(f["Front"]["value"]) if "Front" in f else plain(f.get("Text", {}).get("value", ""))[:80]
        back = plain(f["Back"]["value"]) if "Back" in f else ""
        cs = sorted((cards[c] for c in n["cards"]), key=lambda c: c["ord"])
        out[str(n["noteId"])] = {"front": front, "back": back, "deck": cs[0]["deckName"],
                                 "cards": [card_summary(c, revs[str(c["cardId"])]) for c in cs]}
    json.dump({"date": datetime.date.today().isoformat(), "notes": out},
              open(SNAP_JSON, "w"), ensure_ascii=False, indent=1)
    rows = sorted(out.items(), key=lambda kv: kv[1]["back"].lower())
    md = [f"# Leeches — {datetime.date.today().isoformat()}", "",
          f"{len(rows)} notes tagged `leech`. Untag a word in the Anki browser if you now know it, then run",
          "`scripts/leech_release.py`: it comes back as a **new** word (both directions, history reset)",
          "at the front of its deck's new queue. `streak` = passes in a row since the last fail.", "",
          "| Russian | English | EN→RU | RU→EN |", "|---|---|---|---|"]
    fmt = lambda c: f"{c['state']}, {c['lapses']} lapses, streak {c['streak']}, last fail {c['last_fail']}"
    for _, v in rows:
        cs = v["cards"] + [{"state": "—", "lapses": 0, "streak": 0, "last_fail": "—"}] * (2 - len(v["cards"]))
        md.append(f"| {v['back']} | {v['front']} | {fmt(cs[0])} | {fmt(cs[1])} |".replace("\n", " "))
    open(SNAP_MD, "w").write("\n".join(md) + "\n")
    print(f"snapshot: {len(rows)} leech notes → {SNAP_MD}, {SNAP_JSON}")


def release(dry_run):
    snap = json.load(open(SNAP_JSON))["notes"]
    tagged = set(a.call("findNotes", query="tag:leech"))
    gone = [int(n) for n in snap if int(n) not in tagged]
    existing = {n["noteId"]: n for n in a.call("notesInfo", notes=gone) if n.get("fields")}
    rel = [n for n in gone if n in existing]
    if not rel:
        print("nothing untagged since the snapshot")
        return
    for n in rel:
        print(f"  release: {snap[str(n)]['back']} — {snap[str(n)]['front']}")
    if dry_run:
        print(f"{len(rel)} notes would be released (dry run)")
        return
    cids = [c for n in rel for c in existing[n]["cards"]]
    before = a.call("cardsInfo", cards=cids)
    json.dump({"notes": rel, "cards": before},
              open(f"tutoring/retired/leech-released-{time.strftime('%Y%m%d-%H%M%S')}.json", "w"),
              ensure_ascii=False, indent=1)
    a.call("forgetCards", cards=cids)
    a.call("unsuspend", cards=cids)
    by_deck = {}
    for c in before:
        by_deck.setdefault(c["deckName"], []).append(c)
    for deck, cs in by_deck.items():
        others = [c["due"] for c in a.call("cardsInfo", cards=a.call("findCards", query=f'"deck:{deck}" is:new'))
                  if c["cardId"] not in set(cids)]
        cs.sort(key=lambda c: (c["ord"], rel.index(c["note"])))
        pos = (min(others) if others else 0) - len(cs)
        for c in cs:
            r = a.call("setSpecificValueOfCard", card=c["cardId"], keys=["due", "reps", "lapses"],
                       newValues=[pos, 0, 0], warning_check=True)
            assert r in (True, [True]), r
            pos += 1
        print(f"{deck}: {len(cs)} cards at the front of the new queue")
    print(f"released {len(rel)} notes")
    snapshot()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    snapshot() if args.snapshot else release(args.dry_run)
