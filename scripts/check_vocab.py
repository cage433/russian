#!/usr/bin/env python3
"""Report Russian content words in a sentence that are NOT in Alex's known set.

Used when constructing grammar-drill examples: run the expected Russian answer through this;
gloss (English) whatever it flags, or swap for a known synonym. Empty output = all content
words known.

Depends on known_lemmas.txt (produced by build_drill_vocab.py) at the repo root.
Normalisation matches the repo convention (strip stress only, keep ё) via anki_utils.
Run:  .venv/bin/python scripts/check_vocab.py "…the Russian sentence…"
  or  echo "…" | .venv/bin/python scripts/check_vocab.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import anki_utils as a  # noqa: E402
a.use_venv()

# Function words (grammar, not vocabulary to look up). Destressed forms, ё kept.
STOP = set("""
и а но да или же ли бы б не ни ведь вот уже ещё то как так там тут вон
в во на за под над по о об обо от до из изо у к ко с со при про для без через между
среди около возле мимо вдоль кроме вместо благодаря несмотря сквозь ради
я ты он она оно мы вы они меня тебя его её нас вас их мне тебе ему ей нам вам им
мной тобой ими себя себе собой свой своя своё свои
этот эта это эти тот та те такой весь вся всю все всех всем чей
что чтобы который кто где когда куда откуда почему зачем сколько разве неужели
если хотя пока потому поэтому значит нужно надо можно нельзя есть быть тоже также
""".split())


def main():
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    known = set((ROOT / "known_lemmas.txt").read_text(encoding="utf-8").split())

    out, seen = [], set()
    for tok in re.findall(r"[а-яёА-ЯЁ][а-яёА-ЯЁ-]*", text):
        w = a.destress(tok)                 # lowercase, stress stripped, ё kept
        if w in STOP:
            continue
        lem = a.lemma(w)
        if lem in STOP or w in known or lem in known:
            continue
        if lem not in seen:
            seen.add(lem)
            out.append(lem)
    print("\n".join(out))


if __name__ == "__main__":
    main()
