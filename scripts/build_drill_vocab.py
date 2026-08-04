#!/usr/bin/env python3
"""Build the "vocabulary Alex knows" cache for grammar-drill sentence construction.

"Known" = cards that have left the 'new' queue (studied) in the Vocab::* decks — i.e. words
Alex can actually recall, not merely words that have a card. This is DIFFERENT from
anki_utils.build_known(), which unions every note (new or not) in explicit decks to filter
words already carded when authoring new decks.

Writes, at the repo root:
  known_lemmas.txt  one normalised token/lemma per line (membership set for check_vocab.py)
  known_vocab.tsv   russian <TAB> english   (one row per studied note, for browsing / gloss lookup)

Normalisation follows the repo convention (anki_utils.norm/destress): strip ONLY the stress
accent, keep й/ё. Regenerate at session start — the studied set grows.
Run: .venv/bin/python scripts/build_drill_vocab.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import anki_utils as a  # noqa: E402

QUERY = "deck:Vocab::* -is:new"  # studied set. Conservative alt: append " prop:ivl>=21".
TOKEN = re.compile(r"[а-яё]+(?:-[а-яё]+)?")


def clean_front(html):
    s = re.sub(r"\[sound:[^\]]*\]", "", html)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def main():
    ids = a.call("findNotes", query=QUERY)
    print(f"{len(ids)} studied notes matched `{QUERY}`", file=sys.stderr)

    lemmas, rows, seen = set(), [], set()
    for i in range(0, len(ids), 500):
        for n in a.call("notesInfo", notes=ids[i:i + 500]):
            ru = a.norm(n["fields"]["Back"]["value"])          # destressed plain text, ё kept
            if not ru:
                continue
            if ru not in seen:
                seen.add(ru)
                rows.append((ru, clean_front(n["fields"]["Front"]["value"])))
            for w in TOKEN.findall(ru):
                if len(w) >= 2:
                    lemmas.add(w)
                    lemmas.add(a.lemma(w))

    (ROOT / "known_lemmas.txt").write_text("\n".join(sorted(lemmas)) + "\n", encoding="utf-8")
    (ROOT / "known_vocab.tsv").write_text(
        "\n".join(f"{ru}\t{en}" for ru, en in sorted(rows)) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} vocab rows, {len(lemmas)} lemmas", file=sys.stderr)


if __name__ == "__main__":
    main()
