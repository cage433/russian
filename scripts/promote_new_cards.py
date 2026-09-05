#!/usr/bin/env python3
"""Bring tagged NEW cards to the front of their deck's new queue and lift that deck's
new-card limit for today, so the tagged words enter the learning phase today.

Workflow: tag notes `promote` in the Anki browser, then run this script. It handles every
deck the tagged cards live in.

Positions
---------
Per note, the lowest-ord available new card becomes the note's "primary" and goes to
position 0; its remaining new siblings go to position 1. Untagged new cards start at
position >= 2 (asserted at runtime — the run aborts for a deck if that isn't true), so the
gathered batch is one card per promoted note and no two gathered cards are siblings. The
siblings at position 1 come up on a following day.

That holds the batch only if the limit is no larger than the number of primaries Anki can
actually gather, because a limit with room to spare is filled from position 2 downwards —
with untagged words. So a primary is left out of the count when it is buried or suspended,
and when a sibling is already in today's queue: Anki drops a new card whose sibling is
queued (bury new siblings) at the moment it *builds* the queue, without waiting for the
sibling to be answered, and the dropped card still reads `queue == 0`. The count therefore
errs low — the batch can come up short, but it will not contain words you did not choose.

Pre-promotion gloss index
-------------------------
Every Front is indexed when it is written, but nothing checks it against what is *in flight*:
печа́тать (10K) and распеча́тывать (B1.2) were promoted the same day from different decks with
both Fronts pointing at a printer (2026-09-05). So before repositioning anything, the run
reports promoted Fronts that share a **rare** English word (document frequency <= MAX_DF)
with another promoted note or a card already in circulation, and Backs repeating a Russian
headword. Advisory: it prints, it never blocks. `--skip-index` turns it off.

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
import argparse, html, json, re, sys, time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import anki_utils as a
a.use_venv()

TAG = "promote"
SNAPSHOT_DIR = ROOT / "scratch"          # gitignored
PRIMARY_POS, SIBLING_POS = 0, 1          # untagged new cards must live at >= 2

QUEUE_NAMES = {0: "new", -1: "suspended", -2: "sib-buried", -3: "buried",
               1: "learn", 2: "review", 3: "day-learn"}

# Cards in today's queue, which therefore bury a new sibling out of it. `-is:buried` matters:
# a buried sibling is not in the queue and so blocks nothing. Kept identical to
# BLOCKING_SEARCH in anki_addon/russian_promote/__init__.py — change both together.
BLOCKING_SEARCH = "-is:new -is:suspended -is:buried (is:due or is:learn)"


# ---------------------------------------------------------------- gloss index
# A promoted card has to be answerable from its English Front against everything Alex can
# already recall. Each Front is checked when it is written, but nothing checks it against
# what is *in flight*: печа́тать (10K) and распеча́тывать (B1.2) were promoted on the same
# day, from different decks, both Fronts pointing at a printer (2026-09-05).
#
# Shared *common* words are meaningless — "make", "take", "away" appear on dozens of Fronts.
# So a word only counts as a clash when it is rare across the indexed Fronts: document
# frequency <= MAX_DF. That needs no stoplist to maintain and it is what makes the signal
# readable ("printer", "cope", "lead" survive; "make" does not).
#
# Indexed set = promoted notes + notes already in circulation. Unseen cards are deliberately
# left out: at new/day = 0 they cannot be confused with anything until they are promoted too,
# at which point this same check sees them.
MAX_DF = 8

# Placeholders, not content: every second gloss says "someone" or "something", and the df
# filter alone does not catch them because they are not *that* common.
INDEX_STOP = {"someone", "something", "somebody", "oneself", "one's", "sth", "s.o", "o.s",
              "etc", "e.g", "coll", "colloq", "impf", "pf", "adj", "adv", "noun", "verb"}

def _plain(field):
    s = re.sub(r"\[sound:[^\]]*\]", " ", field)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(s)


def _content_words(front):
    """Words from the *bare* gloss only.

    Parentheses and brackets are dropped, because on this collection they hold the material
    that RESOLVES a clash rather than causing one — навеща́ть "to visit (a person)" against
    посеща́ть "to visit (a place)" must still be reported as sharing "visit". Indexing the
    parentheses instead buries that under matches on "goods", "patient" and the like.
    `(cf. X = …)` goes too: it names a rival on purpose."""
    s = _plain(front)
    s = re.sub(r"\(\s*cf\..*?\)", " ", s, flags=re.I | re.S)
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", s)
    return {w for w in re.findall(r"[a-z][a-z'-]{2,}", s.lower()) if w not in INDEX_STOP}


def _headwords(back):
    """Russian headwords on a Back, one per line, skipping 1:/Abs:/Conc: labels and
    annotation lines. Destressed, so `гля́нуть` and `глянуть` compare equal — a stress mark
    inside the stem otherwise defeats the match."""
    out = set()
    for seg in _plain(back).split("\n"):
        seg = re.sub(r"^\s*(?:\d+|Abs|Conc|Abstract|Concrete)\s*:\s*", "", seg.strip(),
                     flags=re.I).strip()
        if not seg or seg.startswith("("):
            continue
        m = re.match(r"[^\s/(,;]+", seg)
        if m and re.search(r"[а-яё]", m.group(0), re.I):
            out.add(a.destress(m.group(0)))
    return out


def notes_info(note_ids):
    out = []
    for i in range(0, len(note_ids), 500):
        out += a.call("notesInfo", notes=note_ids[i:i + 500])
    return out


def gloss_index(tag, max_df=MAX_DF):
    """Report Fronts of promoted notes that share a rare English word with another promoted
    note or with a card already in circulation, and Backs that repeat a Russian headword.
    Advisory only — it prints and returns findings, it never blocks the run."""
    tagged = a.call("findNotes", query=f"tag:{tag}")
    if not tagged:
        return []
    circulating = a.call("findNotes", query=f'"note:{a.MODEL}" -is:new -tag:{tag}')
    notes = notes_info(sorted(set(tagged) | set(circulating)))
    tagged = set(tagged)

    df, words, heads = defaultdict(int), {}, {}
    for n in notes:
        w = _content_words(n["fields"]["Front"]["value"])
        words[n["noteId"]] = w
        heads[n["noteId"]] = _headwords(n["fields"]["Back"]["value"])
        for t in w:
            df[t] += 1
    byhead = defaultdict(list)
    for nid, hs in heads.items():
        for h in hs:
            byhead[h].append(nid)
    txt = {n["noteId"]: (re.sub(r"\s+", " ", _plain(n["fields"]["Back"]["value"])).strip(),
                         re.sub(r"\s+", " ", _plain(n["fields"]["Front"]["value"])).strip())
           for n in notes}

    findings = []
    for nid in sorted(tagged, key=lambda i: txt[i][0]):
        hits = []
        for other in notes:
            oid = other["noteId"]
            if oid == nid:
                continue
            shared = {t for t in words[nid] & words[oid] if df[t] <= max_df}
            dup = heads[nid] & heads[oid]
            if shared or dup:
                hits.append((oid, shared, dup))
        if hits:
            # same headword first, then same-batch clashes, then the rest: a pair both
            # going out today is the urgent case, and the one nothing else checks.
            hits.sort(key=lambda h: (not h[2], h[0] not in tagged, txt[h[0]][0]))
            findings.append((nid, hits))

    if not findings:
        print(f"gloss index: {len(tagged)} promoted note(s) vs {len(circulating)} "
              f"in circulation — no clashes")
        return []
    print(f"\ngloss index: {len(tagged)} promoted note(s) vs {len(circulating)} in circulation")
    for nid, hits in findings:
        back, front = txt[nid]
        print(f"  ! {back[:38]:<38} {front[:44]!r}")
        for oid, shared, dup in hits[:4]:
            oback, ofront = txt[oid]
            where = "also promoted" if oid in tagged else "in circulation"
            what = ("SAME HEADWORD " + ", ".join(sorted(dup))) if dup \
                   else "shares " + ", ".join(f'"{w}"' for w in sorted(shared))
            print(f"      {what}  [{where}]")
            print(f"        {oback[:38]:<38} {ofront[:44]!r}")
    print("  (advisory — nothing is blocked; regloss or untag if a pair is unanswerable)")
    return findings


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


def blocked_notes(tag):
    """-> nids of tagged notes with a card in today's queue, whose new sibling Anki will
    therefore drop when it builds that queue.

    The exclusion happens at gather time, not when the sibling is answered, and it leaves
    the dropped card at `queue == 0` — so card state alone cannot tell a gatherable primary
    from one that will never be offered. Counting the latter sizes the limit above what the
    deck can deliver and Anki backfills with untagged cards."""
    ids = a.call("findCards", query=f"tag:{tag} {BLOCKING_SEARCH}")
    return {c["note"] for c in cards_info(ids)} if ids else set()


def buries_new_siblings(deck):
    """The exclusion above only applies if the deck's preset buries new siblings."""
    conf = a.call("getDeckConfig", deck=deck)
    return bool((conf.get("new") or {}).get("bury"))


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


def promote(tag, dry_run, clear_tag, set_limit, untag_finished=True, index=True):
    if untag_finished:
        reap_tag(tag, dry_run)
    ids = a.call("findCards", query=f"tag:{tag}")
    if not ids:
        print(f"Nothing tagged {tag!r}.")
        return
    if index:
        gloss_index(tag)
    addon = have_addon() if set_limit and not dry_run else False
    if set_limit and not dry_run and not addon:
        print("NOTE: russian_promote add-on not detected — limits must be set by hand.\n")

    all_cards = cards_info(ids)
    bydeck = defaultdict(list)
    for c in all_cards:
        bydeck[c["deckName"]].append(c)
    blocked_nids = blocked_notes(tag)      # note-scoped: a sibling may live in another deck

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

        # queue == 0 keeps this disjoint from the buried/suspended report below: a card that
        # is already out of the queue is reported once, as buried, not twice.
        blocked_ids = ({c["cardId"] for c in primaries
                        if c["queue"] == 0 and c["note"] in blocked_nids}
                       if buries_new_siblings(deck) else set())
        for c in sorted(primaries, key=preview):
            if c["queue"] != 0:
                flag = f"   << {QUEUE_NAMES.get(c['queue'], c['queue'])}"
            elif c["cardId"] in blocked_ids:
                flag = "   << sibling in today's queue"
            else:
                flag = ""
            print(f"    {preview(c)[:34]:36s} ord={c['ord']} pos {c['due']:>8d} -> {PRIMARY_POS}{flag}")
        if siblings:
            print(f"    + {len(siblings)} sibling card(s) -> position {SIBLING_POS} (a later day)")
        blocked = [c for c in primaries if c["queue"] != 0]
        if blocked:
            print(f"    NOTE: {len(blocked)} of these are buried/suspended and will not appear")
            print("          today whatever the position (burying clears at rollover).")
        if blocked_ids:
            print(f"    NOTE: {len(blocked_ids)} have a sibling due for review or in learning today.")
            print("          Anki drops a new card whose sibling is already in the queue, so these")
            print("          are not counted in the limit; they come up on a day the sibling is not due.")

        limit = len([c for c in primaries
                     if c["queue"] == 0 and c["cardId"] not in blocked_ids])
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
    p.add_argument("--skip-index", action="store_true",
                   help="skip the pre-promotion gloss/headword clash report")
    p.add_argument("--restore", metavar="SNAPSHOT.json",
                   help="write the original positions back and exit")
    args = p.parse_args()

    if args.restore:
        restore(args.restore)
    elif args.clear_limit:
        clear_limits(args.deck, args.tag)
    else:
        promote(args.tag, args.dry_run, args.clear_tag, not args.no_limit,
                untag_finished=not args.keep_finished_tags, index=not args.skip_index)
