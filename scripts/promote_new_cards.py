#!/usr/bin/env python3
"""Bring tagged NEW cards to the front of their deck's new queue and lift that deck's
new-card limit for today, so the tagged words enter the learning phase today.

Workflow: tag notes `promote` in the Anki browser, then run this script. It handles every
deck the tagged cards live in.

Positions
---------
Per note, the lowest-ord available new card becomes the note's "primary" and goes to
position 0; its remaining new siblings go to position 1. Untagged new cards start at
position >= 2 (asserted at runtime — the run aborts for a deck if that isn't true), so with
the limit set to the primary count the gathered batch is exactly one card per promoted note:
no untagged card can leak in, and no two gathered cards are siblings, so sibling burying
never eats into the batch. The siblings at position 1 come up on a following day.

Daily limit
-----------
Set as a **today-only** per-deck limit (`Deck.Normal.new_limit_today`), which self-clears at
rollover — so nothing has to be reset afterwards and no options preset is touched. Stock
AnkiConnect cannot reach that field, so this needs the companion add-on in
`anki_addon/russian_promote/` (install: symlink it into
~/Library/Application Support/Anki2/addons21/ and restart Anki). Without it the script still
repositions and just prints the number for you to enter by hand.

Deliberately NOT used: editing the deck's options preset. `Vocab::10000 words` and the
Точка Ру decks share the "Paused" preset with ~50 other decks, and a preset limit is
persistent — it would keep letting untagged cards through until manually reset. Also never
call AnkiConnect's `removeDeckConfigId`: `decks.remove_config()` runs `mod_schema(check=True)`,
raising a full-sync confirmation modal that BLOCKS AnkiConnect (same GUI thread) and freezes
Anki until it is dismissed by hand.

    ./.venv/bin/python scripts/promote_new_cards.py --dry-run
    ./.venv/bin/python scripts/promote_new_cards.py
    ./.venv/bin/python scripts/promote_new_cards.py --clear-limit
    ./.venv/bin/python scripts/promote_new_cards.py --restore scratch/promote-snapshot-*.json
"""
import argparse, json, re, sys, time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import anki_utils as a

TAG = "promote"
SNAPSHOT_DIR = ROOT / "scratch"          # gitignored
PRIMARY_POS, SIBLING_POS = 0, 1          # untagged new cards must live at >= 2

QUEUE_NAMES = {0: "new", -1: "suspended", -2: "sib-buried", -3: "buried",
               1: "learn", 2: "review", 3: "day-learn"}


def have_addon():
    """True if the russian_promote add-on has registered its actions."""
    try:
        return "setNewLimitToday" in a.call("apiReflect", scopes=["actions"])["actions"]
    except Exception:
        return False


def cards_info(card_ids):
    """cardsInfo in batches of 500 (same batching as build_drill_vocab.py)."""
    out = []
    for i in range(0, len(card_ids), 500):
        out += a.call("cardsInfo", cards=card_ids[i:i + 500])
    return out


def preview(card):
    s = re.sub(r"\[sound:[^\]]*\]", "", card["fields"]["Back"]["value"])
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def set_due(card_id, due):
    """setSpecificValueOfCard takes a single card id, not a list. 'due' is not in
    AnkiConnect's guarded key list, so no warning_check is needed — but it writes with
    skip_undo_entry=True, so Anki's undo will NOT bring the old position back."""
    r = a.call("setSpecificValueOfCard", card=card_id, keys=["due"], newValues=[due])
    if r is not True and r != [True]:
        raise RuntimeError(f"setSpecificValueOfCard failed for {card_id}: {r!r}")


def reap_tag(tag, dry_run):
    """Drop the tag from notes whose cards have all reached plain review — nothing new and
    nothing still in learning steps, so the tag has done its job.

    Deliberately checks `is:new or is:learn`, not `is:new` alone: a note whose cards are
    part-way through the learning steps (including one just unsuspended mid-learning) has no
    new cards, and testing `is:new` alone would silently strip a tag the moment it was
    applied. `is:learn` is type-based, so it also covers relearning and suspended-mid-learning
    cards — all cases where the tag is still doing something."""
    done = sorted(set(a.call("findNotes", query=f"tag:{tag}"))
                  - set(a.call("findNotes", query=f"tag:{tag} (is:new or is:learn)")))
    if not done:
        return []
    if dry_run:
        print(f"would remove tag:{tag} from {len(done)} finished note(s)")
        return done
    a.call("removeTags", notes=done, tags=tag)
    print(f"removed tag:{tag} from {len(done)} finished note(s) (all cards introduced)")
    return done


def plan_deck(cards):
    """-> (primaries, siblings). One primary per note; its other new cards are siblings."""
    bynote = defaultdict(list)
    for c in cards:
        if c["type"] == 0:                     # new-type; may still be buried/suspended
            bynote[c["note"]].append(c)
    primaries, siblings = [], []
    for cs in bynote.values():
        cs.sort(key=lambda c: c["ord"])
        avail = [c for c in cs if c["queue"] == 0] or cs
        primaries.append(avail[0])
        siblings += [c for c in cs if c["cardId"] != avail[0]["cardId"]]
    return primaries, siblings


def front_is_clear(deck, tag):
    """False if any *untagged* new card already occupies position 0 or 1 in this deck —
    which would let it into today's batch ahead of the promoted cards."""
    ids = a.call("findCards", query=f'deck:"{deck}" is:new -tag:{tag}')
    intruders = [c for c in cards_info(ids) if c["due"] in (PRIMARY_POS, SIBLING_POS)]
    if intruders:
        print(f"    ABORT: {len(intruders)} untagged new card(s) already sit at position "
              f"{PRIMARY_POS}/{SIBLING_POS} and would enter today's batch:")
        for c in intruders[:5]:
            print(f"      {preview(c)[:40]}  pos={c['due']}")
        print("    Move them back (Browser -> Cards -> Reposition) and re-run.")
    return not intruders


def set_today_limit(deck, n, addon):
    if not addon:
        print(f"    -> set by hand: Deck Options -> Daily Limits -> scope 'Today only'"
              f" -> New cards/day = {n}")
        return
    r = a.call("setNewLimitToday", deck=deck, newLimit=n)
    lim = (r.get("limits") or {}).get("newLimitToday") or {}
    print(f"    today-only new limit = {lim.get('limit', '?')} "
          f"(via {r.get('method')}; clears at rollover)")
    if lim.get("limit") != n:
        print(f"    WARNING: expected {n}, add-on reported {lim.get('limit')!r} — check by hand")


def promote(tag, dry_run, clear_tag, set_limit, untag_finished=True):
    if untag_finished:
        reap_tag(tag, dry_run)
    ids = a.call("findCards", query=f"tag:{tag}")
    if not ids:
        print(f"Nothing tagged {tag!r}.")
        return
    addon = have_addon() if set_limit and not dry_run else False
    if set_limit and not dry_run and not addon:
        print("NOTE: russian_promote add-on not detected — limits must be set by hand.\n")

    all_cards = cards_info(ids)
    bydeck = defaultdict(list)
    for c in all_cards:
        bydeck[c["deckName"]].append(c)

    snapshot, summary = [], []
    for deck in sorted(bydeck):
        cards = bydeck[deck]
        primaries, siblings = plan_deck(cards)
        done = [c for c in cards if c["type"] != 0]
        print(f"\n{deck}")
        print(f"  tagged: {len(cards)} cards / {len({c['note'] for c in cards})} notes"
              f"   new: {len(primaries)} notes ({len(primaries) + len(siblings)} cards)"
              f"   already studied: {len(done)} cards")
        if not primaries:
            print("  no new cards here — nothing to reposition (already in learning/review;")
            print("  learning cards are not gated by the new-card limit, so they surface on their own)")
            continue

        for c in sorted(primaries, key=preview):
            flag = "" if c["queue"] == 0 else f"   << {QUEUE_NAMES.get(c['queue'], c['queue'])}"
            print(f"    {preview(c)[:34]:36s} ord={c['ord']} pos {c['due']:>8d} -> {PRIMARY_POS}{flag}")
        if siblings:
            print(f"    + {len(siblings)} sibling card(s) -> position {SIBLING_POS} (a later day)")
        blocked = [c for c in primaries if c["queue"] != 0]
        if blocked:
            print(f"    NOTE: {len(blocked)} of these are buried/suspended and will not appear")
            print("          today whatever the position (burying clears at rollover).")

        limit = len([c for c in primaries if c["queue"] == 0])
        if dry_run:
            print(f"    would set today-only New cards/day = {limit}")
            continue
        if not front_is_clear(deck, tag):
            continue

        for c in primaries:
            set_due(c["cardId"], PRIMARY_POS)
        for c in siblings:
            set_due(c["cardId"], SIBLING_POS)
        print(f"    repositioned {len(primaries)} primary + {len(siblings)} sibling card(s)")
        snapshot += [{"cardId": c["cardId"], "deck": deck, "note": c["note"], "ord": c["ord"],
                      "due": c["due"], "queue": c["queue"], "back": preview(c)}
                     for c in primaries + siblings]
        summary.append((deck, limit))
        if set_limit:
            set_today_limit(deck, limit, addon)

    if dry_run:
        print("\n--dry-run: nothing changed.")
        return
    if not snapshot:
        print("\nNothing repositioned.")
        return

    SNAPSHOT_DIR.mkdir(exist_ok=True)
    snap = SNAPSHOT_DIR / f"promote-snapshot-{time.strftime('%Y%m%d-%H%M%S')}.json"
    snap.write_text(json.dumps({"tag": tag, "cards": snapshot}, ensure_ascii=False, indent=1))
    print(f"\nsnapshot -> {snap.relative_to(ROOT)}   (only rollback path; no Anki undo)")

    if clear_tag:
        notes = list({c["note"] for c in all_cards})
        a.call("removeTags", notes=notes, tags=tag)
        print(f"removed tag:{tag} from {len(notes)} note(s)")

    print("\nready to study:")
    for deck, limit in summary:
        print(f"  {deck}   {limit} new card(s) today")
    a.call("guiDeckBrowser")


def clear_limits(decks, tag):
    """Drop the today-only override early (it would expire at rollover anyway).
    Decks are named explicitly, or discovered from the tag — and if the tag has been
    cleared, that is reported rather than silently doing nothing."""
    if not decks:
        ids = a.call("findCards", query=f"tag:{tag}")
        if not ids:
            print(f"Nothing tagged {tag!r} to discover decks from — pass --deck explicitly.")
            return
        decks = sorted({c["deckName"] for c in cards_info(ids)})
        print(f"decks from tag:{tag} -> {', '.join(decks)}")
    if not have_addon():
        print("russian_promote add-on not detected; clear it in Deck Options by hand.")
        return
    for deck in decks:
        r = a.call("clearNewLimitToday", deck=deck)
        print(f"  {deck}: {r.get('note', 'today-only limit cleared')}")


def restore(path):
    data = json.loads(Path(path).read_text())
    for c in data["cards"]:
        set_due(c["cardId"], c["due"])
        print(f"  {c['back'][:34]:36s} ord={c['ord']} -> pos {c['due']}")
    print(f"restored {len(data['cards'])} card position(s) from {path}")
    print("NOTE: today-only limits are not in the snapshot; they expire at rollover,")
    print("      or use --clear-limit.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--tag", default=TAG)
    p.add_argument("--deck", action="append", default=[],
                   help="restrict --clear-limit to these decks (repeatable)")
    p.add_argument("--dry-run", action="store_true", help="show what would change; change nothing")
    p.add_argument("--no-limit", action="store_true",
                   help="reposition only; don't touch any daily limit")
    p.add_argument("--clear-limit", action="store_true",
                   help="drop the today-only limit override and exit")
    p.add_argument("--clear-tag", action="store_true",
                   help="remove the tag from ALL matched notes afterwards, finished or not")
    p.add_argument("--keep-finished-tags", action="store_true",
                   help="don't auto-remove the tag from notes whose cards are all introduced")
    p.add_argument("--restore", metavar="SNAPSHOT.json",
                   help="write the original positions back and exit")
    args = p.parse_args()

    if args.restore:
        restore(args.restore)
    elif args.clear_limit:
        clear_limits(args.deck, args.tag)
    else:
        promote(args.tag, args.dry_run, args.clear_tag, not args.no_limit,
                untag_finished=not args.keep_finished_tags)
