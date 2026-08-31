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
| `tag:family::*` | a cluster worked as a unit; promote its members one at a time |

Three clusters are tagged so far — `family::bring`, `family::kaz`, `family::uch`. The tag
records **the group that competes**, which is not always a root: получа́ться sits in
`family::kaz` because its "to turn out" gloss collided with оказа́ться, not because of
its stem. Members already established at long intervals are tagged too, so the tag answers
"what else is in this family, and what must I not disturb?" — the promotion queue is a
separate question, answered by `leech-fixed` and `promote`.

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
- **учи́ть / вы́учить (+a)** — Forgotten + promoted 2026-08-31, head of the учить family below.
- проводи́ть, приводи́ть — recognition cards Forgotten + promoted 2026-08-31.

## The учить family — rebuilt 2026-08-31, awaiting serial promotion

Alex's call: *"I'm not convinced I understand those at any deep level… the whole family should
be forgotten, reformulated, and gradually re-introduced."* So unlike every other cluster, all
eight cards were reset **in both directions** regardless of interval — a 438-day production
card is a prediction, not evidence, and the recognition side told the truth (учи́ть's was at
21 days with 15 lapses).

**Why a bare gloss can never work here.** учи́ть is ambiguous *in Russian*, and the perfective
is what resolves it:

    учи́ть + acc (a thing)      -> вы́учить    = learn, memorise    учить слова
    учи́ть + acc (person) + dat -> научи́ть    = teach              учить детей вежливости
    учи́ться (в/на + place)     -> вы́учиться  = be a student -> qualify
    учи́ться + infinitive       -> научи́ться  = learn how to do something

Same imperfective, opposite meanings, a different perfective for each sense. Every Front
therefore names the **argument frame in English** (project convention forbids Russian on the
Front), so exactly one verb answers each.

Find them all with **`tag:family::uch`**. Promote in this order, next only when the previous
clears 30 days — the two senses of учи́ть must never be in circulation in the same week:

1. **учи́ть / вы́учить (+a)** — to learn by heart, memorise (words, a poem) *(in flight)*
2. **учи́ться / вы́учиться (в/на +pr)** — to be a student, study at (an institution); pf. to qualify
3. **учи́ть / научи́ть (+a +d)** — to teach (someone something)
4. **учи́ться / научи́ться (+inf)** — to learn how to (do something)
5. **изуча́ть / изучи́ть (+a)** — to study, investigate (a subject) in depth
6. **занима́ться / заня́ться (+inst)** — to occupy oneself with, work on (a subject, a sport)
7. **преподава́ть (i) (+a)** — to teach (a subject, as a profession)
8. **обуча́ть / обучи́ть (+a +d)** — to train, instruct (someone in something — formal)

Six duplicates were deleted first: a messy second `учи́ть / научи́ть`, `вы́учить` standing alone,
and RLC copies of учи́ться, изуча́ть, занима́ться and a `преподава́тель m., учи́тель m.` card that
put two words on one note.

**Not part of this family, despite the spelling** — do not merge them in:
- уча́стие / уча́стник / уча́ствовать / уча́сток are from **часть** (part).
- учи́тывать / уче́сть ("take into account") is from **счита́ть**.

**Still to do here:** the nouns (учи́тель, преподава́тель, учени́к, уча́щийся, учёный, уче́ние,
учи́лище, уче́бник) only need Front tightening, not resetting — they are not confusing. The one
exception is the numbered `1: учёба 2: обуче́ние 3: изуче́ние` card (suspended, 5 lapses), which
overlaps изуча́ть and belongs in this rebuild: the three separate on *whose* activity it is —
your own studies, instruction given to someone, or investigation of a subject.

## Clusters done

- **bring / lead** — `family::bring` (2026-08-31): приноси́ть deduped (10K twin deleted); приводи́ть, вводи́ть,
  своди́ть, проводи́ть, вести́ narrowed. Fixed a stress error — `ве́сти` → `вести́`.
- **-каз- family** — `family::kaz` (2026-08-31): six 10K/RLC dedupes; каза́ться, ока́зываться, получа́ться,
  отка́зываться, прика́зывать, ука́зывать, зака́зывать, дока́зывать narrowed. Separated the two
  "to order" cards (person vs goods) and the two "to turn out" cards (copular vs effort).
  Fixed a Latin-`ot`-for-`от` typo and a получа́ться example that didn't contain the word.
  Left alone: пока́зывать 589d, расска́зывать 395d, получа́ть 328d, говори́ть 782d.

## Example-sentence defects in `Vocab::10000 words`

### The off-by-one shift — **fixed 2026-08-31**

At least 38 notes carried the example sentence belonging to the **next** note by creation
order — an off-by-one in a batch authoring run, in unbroken chains:
воро́та -> дворе́ц -> зо́лото -> откры́тие -> отсю́да -> специали́ст -> длина́.

Repaired per link rather than by shifting a run, which is what made it safe: for each pair
the replacement sentence **provably contains the target's headword**, checked by pymorphy3
lemma before every write. 38 links, no conflicts, **34 applied**; the other 4 already held a
correct, fully-stressed example (наблюда́ть, получа́ться, уча́стие, влия́ние) and were skipped.
Snapshot: `scratch/example-shift-repair-2026-08-31.json`.

**Left over:** the restored sentences are only *partially* stressed, unlike the rest of the
collection — the shifted batch was authored without full stress marking. Strictly better than
being about the wrong word, but they don't yet meet the card convention. Adding the marks is
34 sentences of careful work and a wrong mark actively teaches an error, so it wants doing
deliberately, not in passing.

Detector note, if this is ever re-run: build the headword set from the **whole** Back
including parentheticals. Stripping `(pf. …)` first hides the aspect partner, and the example
usually uses it — that alone produced 36 false positives (120 flagged vs 84).

### Mixed Cyrillic/Latin words — **found, not fixed**

33 tokens across the collection mix the two scripts, i.e. contain a character that cannot be
typed or searched for. **11 are in the Back field**, so the headword itself is misspelled and
HyperTTS generated audio from the corrupt text. Two distinct causes:

* **Homoglyph substitution** (21): a Latin letter or precomposed accented vowel standing in
  for Cyrillic — `ду́шнo`, `пoходи́ть`, `cгоре́ть`, `земледeлец`, `пoста́виться`,
  `изготáвливать`, `Черéз`, `цéлый`, `улóвом`. Also the reverse: Cyrillic `р` inside `(рf)`,
  Cyrillic `о` inside `оr`, Cyrillic `а` inside `(+а)`.
* **Keyboard-layout slip** (12): a run of Russian typed with the Latin layout active —
  `желу́dok` (желудок), `упа́dok`, `оса́dok`, `прodúкт`, `Паrikмахер`, `реgióна`, `по́грébе`.

Candidate list in `scratch/mixed-script.json`. Exclude HTML entities when scanning — an
unescaped `&nbsp;` reads as a mixed-script token and produced 81 false positives.

## Next

- Clusters not yet touched: **«turn»** partially done via -каз-; **«spend»**
  (пробы́ть vs проводи́ть вре́мя), **вноси́ть / заноси́ть / подноси́ть** ("bring in", all unseen —
  cheap to fix now), сбыва́ться (suspended, 13 lapses).
- **The 289 production cards at 5–7 lapses are untouched.** Decide after re-measuring the 8+
  cohort — 15× cost per card, so the same move may be justified.
- **Re-measure ~2026-12-01**: interval growth of the recognition-only cohort, and of the
  returned cards. The metric is *interval growth at constant retention*, not lapse count
  (which only ever rises). Baseline to beat: 8d → 13d per six months.
