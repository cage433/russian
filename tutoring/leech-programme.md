# Leech rehabilitation programme

Started **2026-08-31**. Goal: return ~377 production leeches to circulation as cards that
can actually be answered, instead of hammering cards that don't converge.

## Why (the evidence that started it)

- Cards at 8+ lapses were **49% of review time on 14% of the cards in circulation**;
  the 8+ bucket alone cost 2.36 min/card/90d, **21× a clean mature card**.
- Measured over a median of six months at 8+ lapses, those cards moved from an **8-day to a
  13-day interval** — 92% still under 30 days, 71% lapsed again within 90 days. Hammering
  does not converge.
- The EN→RU (`ord 0`, production) direction carries **2.4× the lapses** and 3× the leech rate
  of RU→EN. So production was suspended and **recognition deliberately left running** — it is
  cheap (0.11 min/card) and it keeps the word warm.
- Collection-wide form interference is **not** the cause: 58% of leeches have a close
  orthographic neighbour vs **64% of a ≤1-lapse control**. Don't chase it. *But* a dense
  same-root family with overlapping glosses is a real cause — see the -каз- family below.

## The mechanism, in order

**dedupe → reformulate → Forget → promote**, one card at a time.

1. **Dedupe first.** 531 Russian headwords sit on more than one note, 455 spanning 10K/RLC.
   Where one copy is a leech and another is healthy, the leech is often just the duplicate —
   delete it rather than rewrite it. Deleting a note does **not** erase its revlog (82k
   orphaned rows exist), so history is never the reason to keep a card.
2. **Reformulate by cluster, never by card.** The fix is a *partition* of the semantic space;
   patching one card relocates the collision instead of removing it. Fronts must be
   English-only (project convention), so disambiguate by **argument structure described in
   English**, not by Russian prepositions.
3. **Forget** to clear the pinned FSRS difficulty — but only *after* reformulating, or the
   rebuilt card inherits a difficulty near 10 and a two-week ceiling.
4. **Promote**, because Forget makes the card **new** and `new/day = 0` parks it forever.

## Rules learned the hard way

- **A long interval is a prediction, not evidence of knowledge.** Do not let it outvote recent
  failures on a duplicate. каза́ться sat at 349d in RLC (untested 165 days, last passed at the
  *start* of a failure cluster) while its 10K twin failed 17 times. Recent observations win.
- **пока́зывать was 589d in 10K and 12d/3 lapses in RLC** — same word, opposite outcomes.
  Card design dominates word difficulty.
- **Recognition leeches exist.** проводи́ть had a 21-lapse *recognition* card while production
  sat at 276d. "Production is the harder direction" is a trend, not a rule — always check both.
- **Stale but not broken → `setDueDate`, not Forget.** Forget parks a review card at the back
  of a 26k new queue. `setDueDate` tests it soon and keeps it a review card. (Note: the `!`
  suffix makes Anki *rewrite* the interval to match the new due date — it does not preserve it.)
- **Reintroduce serially.** The three healthy -каз- members were learned years apart; the seven
  failing ones are all in circulation together at 3–22 day intervals, re-colliding constantly.
  Promote the next only when the previous clears a 30-day interval.
- Hold unseen members of a broken family out of circulation until it stabilises (automatic at
  `new/day = 0` — just don't promote them).

## State — the tags are the source of truth

These sync via AnkiWeb, unlike `scratch/` (gitignored) and unlike Claude's memory (per-machine).

| query | meaning |
|---|---|
| `tag:leech-parked` | production suspended, gloss **not yet fixed** — the backlog |
| `tag:leech-fixed is:suspended` | reformulated, **ready** to Forget + promote |
| `tag:promote` | in flight; `promote_new_cards.py` surfaces these |
| suspended, 8+ lapses, neither tag | **Alex's own** suspensions — not the programme's, leave alone |

As of 2026-08-31: **369 parked, 6 fixed-and-ready, 10 not mine.**

### Ready queue (serial order)

1. ока́зываться / оказа́ться — to turn out to be, prove to be
2. отка́зываться / отказа́ться — to refuse, decline; to give up, renounce
3. получа́ться / получи́ться — to work out, come out well (of an effort)
4. приводи́ть / привести́ — to bring, lead (a person, on foot)
5. вводи́ть / ввести́ — to introduce, bring in (a law, a rule)
6. своди́ть / свести́ — to take (someone) somewhere and back

### In flight

- **каза́ться / показа́ться** — Forgotten + promoted 2026-08-31. Next in the -каз- family
  waits until this clears 30 days.
- проводи́ть, приводи́ть — recognition cards Forgotten + promoted 2026-08-31.

## Clusters done

- **bring / lead** (2026-08-31): приноси́ть deduped (10K twin deleted); приводи́ть, вводи́ть,
  своди́ть, проводи́ть, вести́ narrowed. Fixed a stress error — `ве́сти` → `вести́`.
- **-каз- family** (2026-08-31): six 10K/RLC dedupes; каза́ться, ока́зываться, получа́ться,
  отка́зываться, прика́зывать, ука́зывать, зака́зывать, дока́зывать narrowed. Separated the two
  "to order" cards (person vs goods) and the two "to turn out" cards (copular vs effort).
  Fixed a Latin-`ot`-for-`от` typo and a получа́ться example that didn't contain the word.
  Left alone: пока́зывать 589d, расска́зывать 395d, получа́ть 328d, говори́ть 782d.

## Next

- Clusters not yet touched: **«turn»** partially done via -каз-; **«spend»**
  (пробы́ть vs проводи́ть вре́мя), **вноси́ть / заноси́ть / подноси́ть** ("bring in", all unseen —
  cheap to fix now), сбыва́ться (suspended, 13 lapses).
- **The 289 production cards at 5–7 lapses are untouched.** Decide after re-measuring the 8+
  cohort — 15× cost per card, so the same move may be justified.
- **Re-measure ~2026-12-01**: interval growth of the recognition-only cohort, and of the
  returned cards. The metric is *interval growth at constant retention*, not lapse count
  (which only ever rises). Baseline to beat: 8d → 13d per six months.
