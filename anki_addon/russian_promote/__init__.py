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

from aqt import gui_hooks

ANKICONNECT_MODULE = "2055492159"
LIMIT_KEYS = ("newLimitToday", "new_limit_today")   # camel (legacy JSON) / snake


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

    for fn in (getDeckLimits, setNewLimitToday, clearNewLimitToday):
        fn.api, fn.versions = True, ()
        setattr(ac.AnkiConnect, fn.__name__, fn)
    print("russian_promote: registered getDeckLimits, setNewLimitToday, clearNewLimitToday")


gui_hooks.profile_did_open.append(_patch)
