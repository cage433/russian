# Russian Anki — Точка Ру vocabulary decks

Building and curating Russian Anki vocab decks from the **Точка Ру** (Tochka Ru) textbook
series. Words the textbooks teach that aren't already known get authored as flashcards.

## Environment
- **Anki** must be running with the **AnkiConnect** add-on (localhost:8765). All deck reads/writes go through it.
- **Python venv**: `./.venv/bin/python` — has `pymorphy3` (+`pymorphy3-dicts-ru`) for lemmatisation and `PyMuPDF`(`fitz`) for PDF text. Recreate with `python3 -m venv .venv && .venv/bin/pip install pymorphy3 pymorphy3-dicts-ru PyMuPDF`.
- **Helpers**: `scripts/anki_utils.py` — `call()`, `destress()`, `norm()`, `lemma()`, `build_known()`, `page_text()`, `add_notes()`, `strip_pos_from_front()`. Import with `sys.path.insert(0,'scripts'); import anki_utils as a`.
- **Machine parity**: `scripts/anki_doctor.py` (system python3, stdlib only — it checks the venv,
  so it can't use it). Fast-forwards the repo, creates the add-on symlink, and reports what needs
  a person: unpushed commits, a diverged branch, an add-on whose source changed after Anki loaded
  it (`addonInfo.stale` — a `git pull` does nothing until Anki restarts), non-default toggles, a
  broken venv, decks with no limit stamped for today, stale drill caches. `--check` reports only;
  `--quiet` prints just problems; exit 1 if any. Never pushes, commits, or merges non-fast-forward
  — unfinished work on the other laptop is normal, not an error. Repairs limits with
  `autoLimitNow(onlyUnstamped=True)` only, never the full pass (which mid-day would recompute
  downward and retire words left for later). `launchd/com.cage433.anki-doctor.plist` runs it at
  login and every 4h → `~/Library/Logs/anki-doctor.log`; launchd rather than cron because a job
  due while the laptop sleeps runs on wake instead of being missed.
- **Source PDFs**: `~/Proton Drive/books/Russian/Точка Ру/` → `B1.1/`, `B1.2/`, `B2.1/` each hold `<lvl> учебник.pdf` (textbook) + `<lvl> раб-тет.pdf` (workbook). B1.x textbooks are OCR'd scans (stress letters mangled — use OCR to identify *which* words, author spelling/stress yourself); B2.1 is clean vector text.

## Decks
- Pre-existing (the user's own): `Vocab::10000 words` (~8.9k, the main frequency deck), `Vocab::RLC`. These have review history — never delete/merge-away their history carelessly.
- Built here: `Vocab::Tochka Ru::B1.1`, `::B1.2` (each later split into `::Loanwords` + `::Native`), and `Vocab::Tochka Ru::B2.1::1.1 … ::2.2` (6 lesson subdecks).
- New decks sit on the **Default** preset (0 new/day) until the user sets a study rate — don't change it unprompted.

## Card conventions (match exactly)
- Note type **"Basic (and reversed card)"**, fields **Front / Back / Example**. Tags = POS (`noun`/`adj`/`verb`/`adv`/…) + `claude`; idioms get `claude` only.
- **Front** = English gloss. NO Russian on the Front. NO POS descriptor `(noun)` unless there's genuine POS ambiguity (then e.g. `chocolate (noun / adj)`). NO `(idiom)`/`(proverb)` markers.
- **Back** = Russian with stress marks (combining U+0301), ending in a trailing `<br><br>` (gap before future audio).
- **Example** = one Russian sentence with stress.
- **No audio** is added by us — the user runs a HyperTTS batch later.

## Merge conventions (consolidating variant forms onto one card)
- Aspect pair / adj-adv / m-f → slash: `<impf> / <pf>`, `<adj> / <adv>`, `<masc> / <fem>`; single combined gloss; both POS tags. Impf first. Only pair genuine aspect partners (not bi-aspectual, not impf-only, not inceptive pseudo-pairs).
- Near-synonyms (distinct words, same headword) → numbered: Front `headword<br><br>1: <distinguishing gloss><br>2: …`; Back `1: w1<br>2: w2`. **Do not repeat the headword** in the sense glosses (diet → "1: weight-loss regimen / 2: daily food intake").
- **If a merge involves a `Vocab::10000 words` or `Vocab::RLC` card, the result must end up in `Vocab::10000 words`** (edit that card as the base, or `changeDeck` the survivor into 10K; delete the others).

## Audio rule
Before an edit that would invalidate a card's `[sound:]` recording (changing/correcting the Russian word or its stress), **ask the user whether to delete the recording** — don't silently keep a now-wrong one or delete on your own. If deleting, remove only the `[sound:…]` reference; the orphaned media clears via Tools→Check Media.

## Promoting words into today's learning queue
Tag notes `promote` in the Anki browser, then `scripts/promote_new_cards.py` (`--dry-run` /
`--clear-limit` / `--clear-tag` / `--restore <snapshot>`). It finds `tag:promote` across **all**
decks and, per deck, does both halves of the job:
1. **Positions.** Per note, the lowest-ord available new card → position **0**, its remaining new
   siblings → position **1**. Untagged new cards start at ≥2 (asserted at runtime; the deck is
   skipped if not), so a limit of *one per note* gathers one card per promoted note and no two
   gathered cards are siblings. **That only keeps untagged words out if the limit is no bigger
   than the number of promoted cards Anki can actually gather** — spare room is filled from
   position 2 downwards. See the gather-time burying rule below. The
   position-1 siblings come up a following day. Old positions snapshot to `scratch/`
   (**`setSpecificValueOfCard` writes with `skip_undo_entry=True` — Anki's undo will not
   bring them back**; `--restore` is the only way back).
2. **Limit.** Sets a **today-only** per-deck limit (`Deck.Normal.new_limit_today`), which
   self-clears at rollover — nothing to reset, no options preset touched.

3. **Tag reaping.** A note loses the `promote` tag once it has **no `is:new` *and* no `is:learn`
   cards left** — i.e. both directions are through the learning steps and into plain review.
   Testing `is:new` alone would strip the tag the moment it was applied to anything already being
   learned; `is:learn` is type-based, so it also covers relearning and suspended-mid-learning
   cards. Both `scripts/promote_new_cards.py:97` and the add-on's `reap_tag` use this rule.
   `is:new` includes buried/suspended cards, so a note whose remaining sibling is merely buried
   keeps its tag. (`--keep-finished-tags` disables; `--clear-tag` is the blunt version — strips the
   tag from *all* matched notes, finished or not.)
   **Never strip the tag by hand from words that haven't been studied yet.** It does two kinds of
   damage: `auto_limit()` then has nothing to count, so those repositioned cards never surface;
   and they become *untagged* new cards at positions 0–1, which trips the leak guard and makes
   the add-on skip that deck for every future batch until they're studied or repositioned.

The limit needs the companion add-on **`anki_addon/russian_promote/`** (symlinked into
`~/Library/Application Support/Anki2/addons21/`; restart Anki after changing it). It attaches
`setNewLimitToday` / `clearNewLimitToday` / `getDeckLimits` / `autoLimitNow` / `peekQueue` onto AnkiConnect's
class on the `profile_did_open` hook — AnkiConnect finds actions by walking its methods for an
`api` attribute, so this needs no fork and survives its updates. Writes go through
`decks.update_dict` (absolute + idempotent), falling back to `extend_limits` (a delta — Custom
Study's mechanism). Without the add-on the script still repositions and just prints the number
to enter by hand.

**Add-ons do not sync — AnkiWeb syncs the collection only.** Each desktop machine needs the
symlink separately (clone this repo, `ln -s <repo>/anki_addon/russian_promote
~/Library/Application\ Support/Anki2/addons21/russian_promote`, restart Anki); `git pull` then
updates both. **iOS/Android cannot run it at all** — AnkiMobile and AnkiDroid have no Python
add-on support. The phone still *honours* a limit stamped by a laptop and synced across (it is
deck data), but it cannot stamp one: on a day no laptop has opened, the phone's deck falls back
to the preset (0/day) and no promoted words appear. Worse, a phone holding a stale deck copy is
the classic way the stamp gets clobbered — see the sync note below.

**The same hooks also set the limits without a command being run**, so a normal day needs none:
`profile_did_open` at startup, **`day_did_change` at the 4am rollover** (Anki's own timer
reschedules itself for each cutoff, so an instance left running for weeks still re-sizes daily),
`state_did_change` → deck list as a catch-up for a rollover the timer slept through (Qt's
monotonic clock doesn't advance while the machine is asleep), and **`sync_did_finish`** (see the
clobbered-limit note below). The pass only counts promoted cards
*already repositioned* to positions 0/1 (tagging alone never raises a limit), **skips a deck
entirely if any untagged new card shares those positions** (the leak guard — tested), and is a
no-op when the same limit is already stamped for `sched.today`. Toggles at the top of the add-on:
`AUTO_LIMIT_ON_STARTUP`, `AUTO_LIMIT_ON_DAY_CHANGE`, `AUTO_LIMIT_ON_SYNC`,
`AUTO_UNTAG_FINISHED`. `autoLimitNow`
triggers the pass on demand; `peekQueue` dumps what the scheduler would hand the reviewer right
now (same `col.sched.get_queued_cards` call `aqt.reviewer` makes — the way to see the real batch,
as opposed to what the positions imply).
- **A promoted card whose sibling is in today's queue will not be gathered, and the limit must not
  count it** (found 2026-08-30). With "bury new siblings" on, Anki drops a new card whose sibling
  is already queued **when it builds the queue** — not when the sibling is answered — and the
  dropped card is left at `queue == 0` in the database, indistinguishable from a gatherable one by
  card state. So a note whose other direction is a **review due today** or **in learning** cannot
  contribute a new card today, whatever its position, and counting it puts the limit above what
  the deck can deliver: Anki fills the gap from the next untagged cards down the list. Both
  `auto_limit()` (`_blocked_notes`) and the script (`blocked_notes`) subtract them, gated on the
  preset's `new.bury`, using one shared search string `BLOCKING_SEARCH` — keep the two copies
  identical. Symptom that led to it: `тесный` (position 15, untagged) appearing in a batch of 10;
  the queue held 3 promoted + 4 untagged.
- Sizing therefore **errs low on purpose**: the batch can come up short (a card buried or
  suspended by hand after the pass runs isn't foreseen), but it does not admit unchosen words.
- **Never call AnkiConnect's `removeDeckConfigId`.** `decks.remove_config()` is the only function in
  `anki/decks.py` that calls `mod_schema(check=True)`; it raises a full-sync confirmation modal, and
  since AnkiConnect serves requests on Anki's GUI thread that **deadlocks Anki** until the dialog is
  dismissed by hand. (`add_config`/`save`/`update_config` are all prompt-free.)
- Don't edit the deck's options **preset**: "Paused" is shared with ~50 other decks, and a preset
  limit is persistent — it keeps letting untagged cards through until manually reset.
- `newCardsIgnoreReviewLimit` is **not** a way around a 0 limit: it is collection-wide and only
  decides whether the *review* limit caps new cards.
- Don't use `setDueDate 0`: it converts new → *review*, skipping the learning steps.
- Cards already buried/suspended won't appear today whatever their position (burying clears at
  rollover); the script reports them rather than pretending otherwise.
- **The today-limit does not survive a sync from a device holding an older copy of that deck**
  (hit 2026-08-29). It lives in the **deck object**, not on the cards, so AnkiWeb's
  last-writer-wins merge can replace `{limit: 22, today: 1681}` with a phone's stale
  `{limit: 0, today: 1678}` — and with no valid stamp the deck falls back to its preset (0/day),
  so the promoted cards silently vanish from the front screen. **Card positions are per-card and
  survive intact**, which is the diagnostic: promoted cards still at 0/1 but nothing showing =
  clobbered limit, not lost work. No "out of sync" warning appears; nothing is corrupted.
  **Sync before promoting.** Repair is now automatic: the add-on's `sync_did_finish` hook
  re-stamps decks whose stamp didn't survive, and leaves alone any deck still stamped for today
  (a live stamp is an allowance partly spent — recomputing it would shrink it below what has
  already been used and retire the day's remaining words). `autoLimitNow` still does it by hand.
  The **first** sync of a session is treated differently, and deliberately: it is the auto-sync at
  profile open, which lands *after* the startup pass (`gui_hooks.profile_did_open()` then
  `maybe_auto_sync_on_open_close`, aqt/main.py:568-569), so on a laptop unused for a day the
  startup pass sized the limit from a pre-merge collection. That one re-runs in full.
- **The limit is an allowance, and it is recomputed from scratch every run.** It does not tick
  down as cards are studied — Anki shows `limit − introduced_today`, so a deck reads 0 new once
  today's introductions reach the number. Meanwhile each fresh `auto_limit()` / script run sizes
  the limit from promoted cards *still in the new queue*, so the figure shrinks as words are
  learnt (10K went 22 → 5 within one session on 2026-08-29). Both together mean a mid-day re-run
  can leave a deck showing 0 even though the morning's limit had headroom. Nothing is lost —
  the cards are repositioned and return at rollover.
- **The promoted queue is finite and self-draining**, which is the point: once the tagged words
  are learnt the recomputed limit is 0, `auto_limit()` writes no limit at all, and the deck's
  preset (0/day) takes over again. It cannot produce an open-ended stream of new cards, so it is
  not the thing to switch off if a review backlog is growing — that lever is on the review side.
- **A limit can also be consumed by cards the script never chose.** Anki counts *all* new cards
  introduced in that deck today against the limit, including any the other device let through, so
  the batch can under-deliver by that many. Check `introduced:1` against `tag:promote` before
  concluding the script mis-sorted something.

## Build workflow (per level / lesson)
1. Build the known/filter set: `a.build_known([...decks to exclude...])`. For B2.1 the user chose 10K + B1.1 + B1.2 + RLC.
2. Extract lesson text with `a.page_text(pdf, start, end)` (both textbook + workbook page ranges from the СОДЕРЖАНИЕ/TOC). Tokenise, lemmatise, drop proper nouns (Name/Surn/Patr/Geox), non-dictionary words (`morph().word_is_known`), grammar meta-terms (case names, деепричастие, приставка…), and anything in the known set.
3. Dedup across lessons (assign each word to its earliest lesson).
4. Curate the survivors (real thematic vocab + idioms; drop grammar-drill items like prefixed motion verbs, and brand names). Author correct spelling/stress/gloss/example from knowledge.
5. `a.add_notes(deck, rows)` — one-by-one, skips Front-duplicate collisions.

## Drill / tutoring workflow (using the decks, not building them)
This repo is also used to **tutor Alex through Точка Ру grammar** with English→Russian
translation drills. Drill examples should draw **mainly from vocabulary Alex already knows**;
when a sentence must reach beyond it, **gloss the unfamiliar word inline** (English). Drills
**never create or modify Anki cards** — gloss only (distinct from the card-building workflow above).
- **Known set = studied vocab**, i.e. cards that have left the 'new' queue: `deck:Vocab::* -is:new`
  (~3.3k words). Note this differs from `a.build_known()` (which unions *all* notes to filter
  already-carded words); here we want words Alex can *recall*.
- `scripts/build_drill_vocab.py` → regenerates `known_lemmas.txt` (membership set) + `known_vocab.tsv`
  (ru→en, for gloss lookup) at the repo root. **Run at session start** — the studied set grows.
  Also **offer to re-run it occasionally mid-session** (Alex's request, 2026-08-29) — he'd rather be
  nudged than have the caches quietly go stale. Natural moments: after cards get promoted or
  studied, when `check_vocab.py` flags a word he clearly knows, or on a long session. The files are
  gitignored, so a fresh machine always needs a run.
- `scripts/check_vocab.py "…russian…"` → prints content lemmas NOT in the known set (pymorphy3
  lemmatisation + a function-word stoplist). Run the expected Russian answer through it; gloss or
  swap whatever it flags. Aspect pairs can over-gloss (a sentence's сошлись lemmatises to сойтись
  while the card stores сходиться) — harmless; it never hides a genuine unknown.
- **Drill format:** English sentences one at a time → Alex translates → corrections in Russian,
  explanations in English. «ещё N таких» = mini-drill on the last error pattern. Track as
  "Sentence N of 20". Correct-or-typos-only → next sentence immediately.
- **Reference pane** — Alex runs `tail -F scratch/drill-pane.md` in an adjacent tmux pane to
  re-check things without scrolling. During a drill, **append** (`>>`, append-only so `tail -F`
  stays stable; never rewrite the file) the *look-up-able* material to `scratch/drill-pane.md`:
  the grammar-point **summary** when a point/drill begins (Alex usually asks for this first),
  **vocab glosses** (esp. words `check_vocab.py` flags), and standalone **grammar-rule
  explanations**. Keep the interactive exchange — prompts, Alex's answers, corrections — **in the
  session**, not the pane. Use short markdown headers per entry; `scratch/` is gitignored.
- Per-lesson grammar notes live in `grammar/tochka ru/<level>/<lesson>.md`. Evolving tutoring
  state is version-controlled here: `tutoring/progress.md` (unit progress + TODO drills) and
  `tutoring/error-patterns.md` (Alex's recurring mistakes — turn into «ещё N таких» mini-drills).
  Read and update both when tutoring. `tutoring/suspended-backlog.md` lists cards Alex suspended
  as too painful to learn, to be unsuspended **gradually** — don't bulk-unsuspend them.
- **Drills isolate one variable (set 2026-08-22):** keep the non-target part of the sentence
  trivial (vary it — don't reuse an identical clause, that becomes copying); carrier vocab from the studied set
  (`check_vocab.py` the expected answer *before* sending); no incidental adjective agreement,
  case-governed prepositions or aspect choices unless that's the point; **score the target
  separately** from incidental slips. Free-writing tasks are the separate place where everything
  is live at once. **General drills are level-gated:** 5 sentences at one level, 4+ correct moves up
  (A2 → B1 → B2), otherwise repeat the level with fresh sentences; typos alone don't fail a
  sentence. Level definitions in `tutoring/progress.md`.
- **Weekly homework goal (set 2026-08-23):** each week's written task should be reproducible
  **flawlessly by week's end**, drilled by back-translation (English → Russian, repeat until
  correct). The Obsidian homework note holds the final text, an English/Russian table for
  back-translation, and a «Повторение» table of review dates (+1/+3/+7) with first-attempt scores.
  **Open a session with the delayed re-run** before new material — same-session repetition mostly
  tests working memory, and the 2026-08-22 corrections were gone within a day.
- **Level (set 2026-08-22): write at A2, read/study at B2.** Alex's reliable production is short
  declarative sentences; his reach is B1–B2 and that's where errors cluster. Score **corrections per
  sentence, not ambition**; push for shorter sentences (Rule 0); and when assessing, **don't count
  echoes of the prompt as production**. Pre-send checklists in `tutoring/self-check.md`; the working
  approach is spelled out at the top of `tutoring/progress.md`.
- `scripts/export_learning_vocab.py` refreshes the Obsidian folder `Anki learning vocab/`
  (one note per POS, near-synonym groups given fuller sense-by-sense tables).
- `known_lemmas.txt` / `known_vocab.tsv` are generated caches (gitignored); the `books` symlink
  (→ Proton Drive PDFs) is also gitignored.

## Gotchas
- Interactive shell aliases `gs` → `git status`; use `/opt/homebrew/bin/gs` for Ghostscript.
- This system's `pdftotext` is the xpdf build and won't display Cyrillic from text layers — verify extraction with PyMuPDF, not pdftotext.
- `addNotes` (plural) is atomic and errors if ANY note is a duplicate — always add one-by-one (`add_notes` does this).
- **`is:learn` matches a card's TYPE, not its queue.** A card suspended part-way through its
  learning steps keeps `type=learn` for ever and goes on matching `is:learn`, though it can never
  appear. Any "what am I currently learning" query needs **`-is:suspended`** (and `-is:review`
  to drop relearning cards). Bit us once: the list silently filled with the `needs-audio` batch.
- Normalise Cyrillic by stripping ONLY the stress accent (keep й/ё); NFD-dropping all combining marks corrupts them.

Global background lives in the user memory files `anki_setup.md` and `anki_audio_recordings.md`.
