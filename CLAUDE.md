# Russian Anki — Точка Ру vocabulary decks

Building and curating Russian Anki vocab decks from the **Точка Ру** (Tochka Ru) textbook
series. Words the textbooks teach that aren't already known get authored as flashcards.

## Environment
- **Anki** must be running with the **AnkiConnect** add-on (localhost:8765). All deck reads/writes go through it.
- **Python venv**: `./.venv/bin/python` — has `pymorphy3` (+`pymorphy3-dicts-ru`) for lemmatisation and `PyMuPDF`(`fitz`) for PDF text. Recreate with `python3 -m venv .venv && .venv/bin/pip install pymorphy3 pymorphy3-dicts-ru PyMuPDF`.
- **Helpers**: `scripts/anki_utils.py` — `call()`, `destress()`, `norm()`, `lemma()`, `build_known()`, `page_text()`, `add_notes()`, `strip_pos_from_front()`. Import with `sys.path.insert(0,'scripts'); import anki_utils as a`.
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
   skipped if not), so a limit of *one per note* gathers exactly the promoted words — no leak, and
   no two gathered cards are siblings, so **sibling burying never eats into the batch**. The
   position-1 siblings come up a following day. Old positions snapshot to `scratch/`
   (**`setSpecificValueOfCard` writes with `skip_undo_entry=True` — Anki's undo will not
   bring them back**; `--restore` is the only way back).
2. **Limit.** Sets a **today-only** per-deck limit (`Deck.Normal.new_limit_today`), which
   self-clears at rollover — nothing to reset, no options preset touched.

3. **Tag reaping.** A note loses the `promote` tag once it has **no `is:new` cards left** — both
   directions introduced. `is:new` includes buried/suspended cards, so a note whose remaining
   sibling is merely buried keeps its tag. (`--keep-finished-tags` disables; `--clear-tag` is the
   blunt version — strips the tag from *all* matched notes, finished or not.)

The limit needs the companion add-on **`anki_addon/russian_promote/`** (symlinked into
`~/Library/Application Support/Anki2/addons21/`; restart Anki after changing it). It attaches
`setNewLimitToday` / `clearNewLimitToday` / `getDeckLimits` / `autoLimitNow` onto AnkiConnect's
class on the `profile_did_open` hook — AnkiConnect finds actions by walking its methods for an
`api` attribute, so this needs no fork and survives its updates. Writes go through
`decks.update_dict` (absolute + idempotent), falling back to `extend_limits` (a delta — Custom
Study's mechanism). Without the add-on the script still repositions and just prints the number
to enter by hand.

**The same hook also sets the limits at every Anki startup**, so a normal day needs no command at
all: open Anki and the promoted words are there. It only counts promoted cards *already
repositioned* to positions 0/1 (tagging alone never raises a limit), **skips a deck entirely if
any untagged new card shares those positions** (the leak guard — tested), and is a no-op when the
limit is already stamped for `sched.today`. Toggles at the top of the add-on:
`AUTO_LIMIT_ON_STARTUP`, `AUTO_UNTAG_FINISHED`. `autoLimitNow` triggers the pass on demand.
Known limit: in a mixed batch (some notes with only a sibling left, plus newly tagged notes with
both cards at the front) the gather can spend a slot on a primary and its own sibling, so burying
drops one — it under-delivers, never leaks. Re-running the script re-sorts it.
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
