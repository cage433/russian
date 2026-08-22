"""Adds today-only daily-limit actions to AnkiConnect.

Why this exists
---------------
Anki's Deck Options -> Daily Limits has a scope dropdown with a **Today only** setting,
which writes `Deck.Normal.new_limit_today` — a per-deck limit that self-clears at rollover.
AnkiConnect exposes no way to reach it: all of its deck actions (`getDeckConfig`,
`saveDeckConfig`, `setDeckConfigId`, `cloneDeckConfigId`) operate on *presets*, and there is
no action that writes a deck's own dict. So `scripts/promote_new_cards.py` could reposition
cards but not let them through the limit without a manual click.

This add-on adds three actions:

    getDeckLimits(deck)                  -> diagnostic dict of every limit in play
    setNewLimitToday(deck, newLimit)     -> absolute today-only new limit
    clearNewLimitToday(deck)             -> drop the override, back to the preset

How it hooks in
---------------
AnkiConnect finds actions by walking its own methods and checking for an `api` attribute
(see its `handler()`). Attaching a function to the *class* with `.api = True` therefore
registers a first-class action — no fork of AnkiConnect and no edits to its files, so its
updates can't clobber this. Patching on `profile_did_open` sidesteps add-on load order.

Install: symlink or copy this folder into
    ~/Library/Application Support/Anki2/addons21/russian_promote
then restart Anki. Verify with:
    curl -s localhost:8765 -X POST \
      -d '{"action":"apiReflect","version":6,"params":{"scopes":["actions"]}}'
Remove by deleting the folder and restarting.

Fragile points, deliberately loud rather than silent: AnkiConnect's folder name
("2055492159") and its `.api` convention, plus the deck-dict limit keys. Any of these
changing raises at profile open or returns an error to the caller.
"""
import importlib

from aqt import gui_hooks, mw

ANKICONNECT_MODULE = "2055492159"
LIMIT_KEYS = ("newLimitToday", "new_limit_today")   # camel (legacy JSON) / snake

# --- startup auto-limit -----------------------------------------------------
AUTO_LIMIT_ON_STARTUP = True     # set False to disable the profile_did_open pass
AUTO_UNTAG_FINISHED = True       # drop `promote` once a note has no new cards left
PROMOTE_TAG = "promote"
FRONT_MAX = 1                    # positions 0 (primaries) and 1 (siblings)


def _deck_id(col, deck):
    did = col.decks.id_for_name(deck)
    if did is None:
        raise Exception(f"unknown deck: {deck!r}")
    return did


def _limit_field(deck_dict):
    """-> (key, value_dict) for whichever today-limit key this Anki build uses."""
    for k in LIMIT_KEYS:
        v = deck_dict.get(k)
        if isinstance(v, dict):
            return k, v
    return None, None


def _read_limits(col, deck):
    did = _deck_id(col, deck)
    d = col.decks.get_legacy(did)
    conf = col.decks.config_dict_for_deck_id(did)
    key, val = _limit_field(d)
    return {
        "deck": deck,
        "deckId": did,
        "presetName": conf.get("name"),
        "presetNewPerDay": conf.get("new", {}).get("perDay"),
        "deckNewLimit": d.get("newLimit", d.get("new_limit")),
        "newLimitTodayKey": key,
        "newLimitToday": val,
        "extendNew": d.get("extendNew", d.get("extend_new")),
        "schedToday": col.sched.today,
    }


def _patch():
    try:
        ac = importlib.import_module(ANKICONNECT_MODULE)
    except Exception as e:                                  # AnkiConnect absent/disabled
        print(f"russian_promote: AnkiConnect not importable ({e}); actions not registered")
        return

    def getDeckLimits(self, deck):
        return _read_limits(self.collection(), deck)

    def setNewLimitToday(self, deck, newLimit):
        """Set an absolute today-only new-card limit. Idempotent."""
        col = self.collection()
        newLimit = int(newLimit)
        did = _deck_id(col, deck)
        today = col.sched.today

        # Preferred: write the deck's own today-limit field.
        d = col.decks.get_legacy(did)
        key, _ = _limit_field(d)
        if key is None:
            key = LIMIT_KEYS[0]           # field absent until first set; create it
        d[key] = {"limit": newLimit, "today": today}
        col.decks.update_dict(d)

        got = _read_limits(col, deck)
        val = got["newLimitToday"] or {}
        if val.get("limit") == newLimit and val.get("today") == today:
            return {"ok": True, "method": "deck_dict", "limits": got}

        # Fallback: Custom Study's mechanism (a delta, not an absolute).
        delta = newLimit - int(got.get("presetNewPerDay") or 0)
        col._backend.extend_limits(deck_id=did, new_delta=delta, review_delta=0)
        got = _read_limits(col, deck)
        return {"ok": True, "method": "extend_limits", "delta": delta, "limits": got}

    def clearNewLimitToday(self, deck):
        col = self.collection()
        did = _deck_id(col, deck)
        d = col.decks.get_legacy(did)
        key, _ = _limit_field(d)
        if key is None:
            return {"ok": True, "note": "no today-limit override set"}
        d.pop(key, None)
        col.decks.update_dict(d)
        return {"ok": True, "limits": _read_limits(col, deck)}

    def autoLimitNow(self):
        """Run the startup pass on demand (same logic, for testing/scripting)."""
        auto_limit()
        return {"ok": True}

    for fn in (getDeckLimits, setNewLimitToday, clearNewLimitToday, autoLimitNow):
        fn.api, fn.versions = True, ()
        setattr(ac.AnkiConnect, fn.__name__, fn)
    print("russian_promote: registered getDeckLimits, setNewLimitToday, clearNewLimitToday")


def _set_today_limit(col, did, n):
    d = col.decks.get_legacy(did)
    key, _ = _limit_field(d)
    d[key or LIMIT_KEYS[0]] = {"limit": n, "today": col.sched.today}
    col.decks.update_dict(d)


def reap_tag(col):
    """Drop the `promote` tag from notes whose cards have all reached plain review.

    Checks `is:new or is:learn`, not `is:new` alone: a note part-way through the learning
    steps has no new cards, so testing `is:new` would strip a tag the moment it was applied
    to anything already being learned (e.g. a card just unsuspended mid-learning)."""
    tagged = set(col.find_notes(f"tag:{PROMOTE_TAG}"))
    unfinished = set(col.find_notes(f"tag:{PROMOTE_TAG} (is:new or is:learn)"))
    done = sorted(tagged - unfinished)
    if done:
        col.tags.bulk_remove(done, PROMOTE_TAG)
        print(f"russian_promote: removed tag:{PROMOTE_TAG} from {len(done)} finished note(s)")
    return done


def auto_limit():
    """Give every deck holding front-of-queue `promote` cards a today-only limit sized to
    the promoted words waiting there, so Anki simply opens with them available.

    Only counts promoted new cards already sitting at position <= FRONT_MAX, i.e. ones
    `promote_new_cards.py` has repositioned — tagging alone never raises a limit. A deck is
    skipped entirely if any *untagged* new card shares those positions, which is what
    guarantees the gathered batch can only contain promoted cards: the limit is the distinct
    note count, which is always <= the number of promoted cards at the front.

    Idempotent: re-running with the limit already stamped for today is a no-op, so it is
    safe on every profile open.
    """
    col = mw.col
    if col is None:
        return
    if AUTO_UNTAG_FINISHED:
        reap_tag(col)
    cards = [col.get_card(cid) for cid in col.find_cards(f"tag:{PROMOTE_TAG} is:new")]
    bydeck = {}
    for c in cards:
        if c.type == 0 and c.due <= FRONT_MAX:
            bydeck.setdefault(c.did, []).append(c)

    for did, cs in sorted(bydeck.items()):
        name = col.decks.name(did)
        # Everything new at the front of this deck must be tagged, or we would let
        # untagged cards through alongside the promoted ones.
        at_front = col.db.scalar(
            "select count() from cards where did = ? and type = 0 and due <= ?",
            did, FRONT_MAX) or 0
        if at_front != len(cs):
            print(f"russian_promote: {name}: {at_front - len(cs)} untagged new card(s) at "
                  f"position <= {FRONT_MAX}; leaving the limit alone")
            continue

        limit = len({c.nid for c in cs if c.queue == 0})
        if not limit:
            continue
        cur = _limit_field(col.decks.get_legacy(did))[1] or {}
        if cur.get("limit") == limit and cur.get("today") == col.sched.today:
            print(f"russian_promote: {name}: today-only limit already {limit}")
            continue
        _set_today_limit(col, did, limit)
        print(f"russian_promote: {name}: today-only new limit -> {limit}")


def _on_profile_open():
    _patch()
    if AUTO_LIMIT_ON_STARTUP:
        try:
            auto_limit()
        except Exception as e:                       # never block profile loading
            print(f"russian_promote: auto_limit failed: {e}")


gui_hooks.profile_did_open.append(_on_profile_open)
