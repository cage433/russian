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
- Per-lesson grammar notes live in `grammar/tochka ru/<level>/<lesson>.md`. Evolving tutoring
  state is version-controlled here: `tutoring/progress.md` (unit progress + TODO drills) and
  `tutoring/error-patterns.md` (Alex's recurring mistakes — turn into «ещё N таких» mini-drills).
  Read and update both when tutoring.
- `known_lemmas.txt` / `known_vocab.tsv` are generated caches (gitignored); the `books` symlink
  (→ Proton Drive PDFs) is also gitignored.

## Gotchas
- Interactive shell aliases `gs` → `git status`; use `/opt/homebrew/bin/gs` for Ghostscript.
- This system's `pdftotext` is the xpdf build and won't display Cyrillic from text layers — verify extraction with PyMuPDF, not pdftotext.
- `addNotes` (plural) is atomic and errors if ANY note is a duplicate — always add one-by-one (`add_notes` does this).
- Normalise Cyrillic by stripping ONLY the stress accent (keep й/ё); NFD-dropping all combining marks corrupts them.

Global background lives in the user memory files `anki_setup.md` and `anki_audio_recordings.md`.
