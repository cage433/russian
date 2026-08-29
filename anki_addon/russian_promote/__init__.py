"""Adds today-only daily-limit actions to AnkiConnect.

Why this exists
---------------
Anki's Deck Options -> Daily Limits has a scope dropdown with a **Today only** setting,
which writes `Deck.Normal.new_limit_today` — a per-deck limit that self-clears at rollover.
AnkiConnect exposes no way to reach it: all of its deck actions (`getDeckConfig`,
`saveDeckConfig`, `setDeckConfigId`, `cloneDeckConfigId`) operate on *presets*, and there is
no action that writes a deck's own dict. So `scripts/promote_new_cards.py` could reposition
cards but not let them through the limit without a manual click.

This add-on adds these actions:

    getDeckLimits(deck)                  -> diagnostic dict of every limit in play
    setNewLimitToday(deck, newLimit)     -> absolute today-only new limit
    clearNewLimitToday(deck)             -> drop the override, back to the preset
    autoLimitNow()                       -> run the startup sizing pass on demand
    peekQueue(fetchLimit)                -> what the scheduler would hand the reviewer now

How it hooks in
---------------
AnkiConnect finds actions by walking its own methods and checking for an `api` attribute
(see its `handler()`). Attaching a function to the *class* with `.api = True` therefore
registers a first-class action — no fork of AnkiConnect and no edits to its files, so its
updates can't clobber this. Patching on `profile_did_open` sidesteps add-on load order.

The same hooks re-size the day's limits without a command being run: `profile_did_open` at
startup, `day_did_change` at the 4am rollover (so an Anki left running for weeks still
gets a fresh limit each day), and `state_did_change` as a catch-up for a rollover the
timer slept through. See `_on_day_change` / `_on_state_change`.

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

# --- automatic sizing passes ------------------------------------------------
AUTO_LIMIT_ON_STARTUP = True     # set False to disable the profile_did_open pass
AUTO_LIMIT_ON_DAY_CHANGE = True  # re-size at the 4am rollover, for an Anki left running
AUTO_UNTAG_FINISHED = True       # drop `promote` once a note has no new cards left
PROMOTE_TAG = "promote"
FRONT_MAX = 1                    # positions 0 (primaries) and 1 (siblings)

_last_limit_day = None           # sched.today at the last auto_limit() pass


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

    def peekQueue(self, fetchLimit=20):
        """Diagnostic: the cards the v3 scheduler would hand the reviewer right now.

        Deliberately goes through `col.sched.get_queued_cards` — the very call
        `aqt.reviewer._get_next_v3_card` makes — so it observes the same backend queue
        state the reviewer sees. That is what makes it a valid probe of whether a limit
        written mid-session actually takes effect, rather than the reviewer running on a
        queue gathered when the deck was opened. Idempotent: consumes nothing.

        Reads the queue of the *currently selected* deck, which is reported back so a
        surprising answer can't be mistaken for a scheduler result.
        """
        col = self.collection()
        q = col.sched.get_queued_cards(fetch_limit=int(fetchLimit))
        cards = []
        for qc in q.cards:
            c = col.get_card(qc.card.id)
            n = c.note()
            cards.append({
                "cardId": c.id, "ord": c.ord, "type": c.type, "queue": c.queue,
                "due": c.due, "deck": col.decks.name(c.did),
                "promote": PROMOTE_TAG in n.tags,
                "front": (n.fields[0] if n.fields else "")[:48],
            })
        return {
            "selectedDeck": col.decks.name(col.decks.selected()),
            "newCount": q.new_count,
            "learningCount": q.learning_count,
            "reviewCount": q.review_count,
            "cards": cards,
        }

    for fn in (getDeckLimits, setNewLimitToday, clearNewLimitToday, autoLimitNow, peekQueue):
        fn.api, fn.versions = True, ()
        setattr(ac.AnkiConnect, fn.__name__, fn)
    print("russian_promote: registered getDeckLimits, setNewLimitToday, clearNewLimitToday, "
          "autoLimitNow, peekQueue")


def _set_today_limit(col, did, n):
    d = col.decks.get_legacy(did)
    key, _ = _limit_field(d)
    d[key or LIMIT_KEYS[0]] = {"limit": n, "today": col.sched.today}
    col.decks.update_dict(d)


# Cards that are in today's queue and so will bury a new sibling out of it. Scoped to the
# promoted notes by the caller. `-is:buried` matters: a buried sibling is not in the queue,
# so it blocks nothing. Kept identical to BLOCKING_SEARCH in scripts/promote_new_cards.py.
BLOCKING_SEARCH = "-is:new -is:suspended -is:buried (is:due or is:learn)"


def _blocked_notes(col, cards):
    """-> nids among `cards` whose new card cannot be gathered today, because a sibling is
    already in today's queue.

    Anki settles this when it *builds* the queue, not when the sibling is answered: with
    "bury new siblings" on, a new card whose sibling is queued for today is dropped from
    the queue and left `queue == 0` in the database — unqueueable, yet indistinguishable
    from a gatherable card by card state alone. Counting one inflates the limit above what
    the deck can deliver, and Anki makes up the difference from the next untagged cards
    down the position list.

    Observed 2026-08-30: four promoted cards whose reverse-direction sibling was a review
    due that day were absent from a 7-card queue which had admitted 4 untagged words.

    Errs low, as the caller wants: `is:learn` matches a card's type, so an interday
    *relearning* sibling due days from now also blocks, though it is not in today's queue.
    """
    blocking = col.find_cards(f"tag:{PROMOTE_TAG} {BLOCKING_SEARCH}")
    return {col.get_card(cid).nid for cid in blocking} & {c.nid for c in cards}


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
    `promote_new_cards.py` has repositioned — tagging alone never raises a limit. Three
    things are then subtracted, and each one matters:

      * a deck is skipped entirely if any *untagged* new card shares those positions,
      * cards that are buried or suspended are not counted (they cannot appear today),
      * nor are cards whose sibling is in today's queue — see `_blocked_notes`.

    Together those make the limit no larger than the number of promoted cards Anki can
    actually gather, which is what keeps untagged cards out of the batch: a limit above
    that number is filled from the next positions down. The failure direction is deliberate
    — the batch can come up short (a card buried or suspended by hand after this runs is
    not foreseen here), but it does not admit words you did not choose.

    Idempotent: re-running with the same limit already stamped for today is a no-op, so it
    is safe on every profile open.
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

        conf = col.decks.config_dict_for_deck_id(did)
        blocked = (_blocked_notes(col, cs)
                   if conf.get("new", {}).get("bury") else set())
        limit = len({c.nid for c in cs if c.queue == 0 and c.nid not in blocked})
        if blocked:
            print(f"russian_promote: {name}: {len(blocked)} promoted note(s) have a sibling in "
                  f"today's queue; Anki drops their new card at gather, so it is not counted")

        cur = _limit_field(col.decks.get_legacy(did))[1] or {}
        stamped_today = cur.get("today") == col.sched.today
        if stamped_today and cur.get("limit") == limit:
            print(f"russian_promote: {name}: today-only limit already {limit}")
            continue
        if not limit and not stamped_today:
            continue          # nothing to let through, and no earlier stamp to correct
        _set_today_limit(col, did, limit)
        print(f"russian_promote: {name}: today-only new limit -> {limit}")


def _run_auto_limit(why, mark_day=True):
    """auto_limit() with its exceptions contained.

    Not merely defensive: the generated hook classes in aqt/hooks.py *remove* a callback
    that raises, so an escaping exception would quietly unregister the pass for the rest of
    the session — and the rollover is the case where it matters most.

    `mark_day=False` leaves the day unrecorded, so the deck-list catch-up will run one more
    pass. See `_on_day_change` for why the rollover pass alone can't be trusted.
    """
    global _last_limit_day
    try:
        auto_limit()
        if mark_day:
            _last_limit_day = mw.col.sched.today if mw.col is not None else None
    except Exception as e:
        print(f"russian_promote: auto_limit ({why}) failed: {e}")


def _on_profile_open():
    _patch()
    if AUTO_LIMIT_ON_STARTUP:
        _run_auto_limit("startup")


def _on_day_change():
    """Anki's own rollover timer (aqt/main.py: refresh_reviewer_on_day_rollover_change)
    reschedules itself for the next cutoff, so this fires at 4am in a long-running Anki —
    which is when yesterday's today-only limit has just expired and a fresh one is needed.

    Deliberately does not record the day. Rollover also unburies yesterday's sibling-buried
    cards, and that happens in the backend when the queues are next built — possibly after
    this hook. A pass that ran first would count those cards as buried and stamp a limit
    too small for the day, with the day guard then suppressing any correction. Leaving the
    day unmarked lets the deck-list catch-up run one further pass, after the queues exist.
    Both passes are idempotent, so the cost of the extra one is nil.
    """
    if AUTO_LIMIT_ON_DAY_CHANGE:
        print("russian_promote: day rollover")
        _run_auto_limit("day change", mark_day=False)


def _on_state_change(new_state, old_state):
    """Second pass: corrects the rollover pass above, and covers a rollover that was missed
    rather than late — Qt's timer runs on a monotonic clock that does not advance while the
    machine sleeps, so a laptop shut overnight reaches the deck list on a new day with the
    4am callback still pending.

    Fires from `moveToState` *after* the state has rendered (aqt/main.py:782 vs 779), so the
    deck counts — and any rollover unburying they triggered — are already settled. The day
    guard then holds it to one pass per day rather than one per navigation.
    """
    if not AUTO_LIMIT_ON_DAY_CHANGE or mw.col is None:
        return
    if new_state in ("deckBrowser", "overview") and mw.col.sched.today != _last_limit_day:
        _run_auto_limit("day catch-up")


gui_hooks.profile_did_open.append(_on_profile_open)
gui_hooks.day_did_change.append(_on_day_change)
gui_hooks.state_did_change.append(_on_state_change)
