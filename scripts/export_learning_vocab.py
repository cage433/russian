#!/usr/bin/env python3
"""Write Obsidian notes listing the vocab currently in Anki's learning steps, split by
part of speech.

Scope: `deck:Vocab::* is:learn -is:review -is:suspended` — cards part-way through their
**first** pass through the learning steps.

Both exclusions matter, and neither is obvious:
- Relearning cards (lapsed reviews coming back round) also match `is:learn`; a relearning card
  matches `is:review` too, which is the only way to tell the two apart.
- **`is:learn` matches on the card's TYPE, not its queue**, so a card suspended part-way through
  its learning steps keeps `type=learn` indefinitely and goes on matching `is:learn` forever,
  despite being unable to appear in reviews. Without `-is:suspended` this list silently filled
  up with cards suspended months ago (e.g. the `needs-audio` batch awaiting re-recording).

The set turns over quickly — it empties as cards graduate and refills as new ones are
introduced — so re-run this whenever you want the notes refreshed. Each run rewrites every
note in the folder, so words that have graduated simply disappear.

Output: one note per POS group in `<vault>/Anki learning vocab/`, plus a folder-note index
alongside it. Cards carry POS tags (`noun`/`verb`/`adj`/`adv`/…) set when they were authored;
a note tagged with more than one POS (e.g. an adj/adv merge, or `chocolate (noun / adj)`)
appears in **each** group it belongs to, so per-group counts can exceed the distinct total.

    ./.venv/bin/python scripts/export_learning_vocab.py
    ./.venv/bin/python scripts/export_learning_vocab.py --print
    ./.venv/bin/python scripts/export_learning_vocab.py --full
    ./.venv/bin/python scripts/export_learning_vocab.py --query 'deck:Vocab::* introduced:7'

Needs Anki running with AnkiConnect. No third-party imports.
"""
import argparse, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import anki_utils as a
a.use_venv()

QUERY = "deck:Vocab::* is:learn -is:review -is:suspended"
VAULT = Path("/Users/alex/.obsidian-vaults/Russian")
OUT_DIR = VAULT / "Anki learning vocab"

# (note name, POS tags). The final group takes whatever no earlier group claimed.
GROUPS = [
    ("Nouns", {"noun"}),
    ("Verbs", {"verb"}),
    ("Adjectives and adverbs", {"adj", "adv"}),
    ("Other", None),
]


def clean(html):
    """Field HTML -> table-safe text. Keeps stress marks; <br> survives as a line break,
    which Obsidian renders inside a table cell."""
    s = re.sub(r"\[sound:[^\]]*\]", "", html)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</?div[^>]*>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in s.split("\n")]
    s = "<br>".join(ln for ln in lines if ln)          # drop blank lines, keep real breaks
    return s.replace("|", r"\|").strip()               # pipes would break the table


SENSE = re.compile(r"^(\d+):\s*(.*)$")


def senses(field):
    """'1: a<br>2: b' -> {'1': 'a', '2': 'b'} (empty if the field isn't numbered)."""
    out = {}
    for part in field.split("<br>"):
        m = SENSE.match(part.strip())
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def is_group(ru):
    """True for merged near-synonym cards, which number their senses. Aspect pairs and
    adj/adv merges use a bare slash instead, so they stay in the compact table."""
    return bool(SENSE.match(ru.split("<br>")[0].strip()))


def briefly(en, ru):
    """Headword only, Russian slash-joined — the scannable form used for single entries."""
    en = en.split("<br>")[0].strip()
    parts = [re.sub(r"^\d+:\s*", "", p).strip() for p in ru.split("<br>")]
    return en, " / ".join(p for p in parts if p)


def fetch(query):
    """-> list of (english, russian, {tags}) with fields cleaned but not yet condensed."""
    nids = a.call("findNotes", query=query)
    out = []
    for i in range(0, len(nids), 500):
        for n in a.call("notesInfo", notes=nids[i:i + 500]):
            f = n["fields"]
            en, ru = clean(f["Front"]["value"]), clean(f["Back"]["value"])
            if en or ru:
                out.append((en, ru, set(n["tags"])))
    return sorted(out, key=lambda r: r[0].casefold())


def split(entries):
    """-> {group name: [(en, ru), …]}. Multi-POS notes land in every matching group;
    anything unmatched falls to the last group."""
    named = [(g, tags) for g, tags in GROUPS if tags]
    fallback = GROUPS[-1][0]
    buckets = {g: [] for g, _ in GROUPS}
    for en, ru, tags in entries:
        hit = False
        for g, want in named:
            if tags & want:
                buckets[g].append((en, ru)); hit = True
        if not hit:
            buckets[fallback].append((en, ru))
    return buckets


def plural(n):
    return f"{n} word" + ("" if n == 1 else "s")


def table(pairs):
    return "\n".join(["| English | Русский |", "|---|---|"] +
                     [f"| {en} | {ru} |" for en, ru in pairs])


def render_synonym_group(en, ru):
    """One near-synonym card -> headword + a sense-by-sense table, so the numbered glosses
    line up with the words they distinguish. The compact one-line form loses that mapping,
    which is the whole point of these cards."""
    head = en.split("<br>")[0].strip()
    glosses, words = senses(en), senses(ru)
    keys = sorted(set(glosses) | set(words), key=lambda k: int(k))
    rows = [f"| {k} | {glosses.get(k, '')} | {words.get(k, '')} |" for k in keys]
    return "\n".join([f"**{head}**", "", "| # | English | Русский |", "|---|---|---|"] + rows)


def render_group(name, pairs, query, stamp):
    """Singles as one compact table; near-synonym groups each get their own fuller table.
    No title — Obsidian shows the filename, and this is a personal scratch list."""
    singles = [briefly(en, ru) for en, ru in pairs if not is_group(ru)]
    groups = [(en, ru) for en, ru in pairs if is_group(ru)]
    if not singles and not groups:
        return "*(none right now)*\n"
    out = [table(singles)] if singles else []
    if groups:
        if singles:
            out.append("")
        out += ["## Near-synonym groups", ""]
        out.append("\n\n".join(render_synonym_group(en, ru) for en, ru in groups))
    return "\n".join(out) + "\n"


def render_index(buckets, total, query, stamp):
    return "\n".join(["| Group | Words |", "|---|---|"] +
                      [f"| [[{g}]] | {len(buckets[g])} |" for g, _ in GROUPS] + [""])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--query", default=QUERY)
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    p.add_argument("--print", dest="show", action="store_true",
                   help="print to stdout instead of writing the notes")
    args = p.parse_args()

    entries = fetch(args.query)
    buckets = split(entries)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    index = render_index(buckets, len(entries), args.query, stamp)

    if args.show:
        print(index)
        for g, _ in GROUPS:
            print("\n" + "=" * 60 + "\n")
            print(render_group(g, buckets[g], args.query, stamp))
        sys.exit()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for g, _ in GROUPS:
        (args.out_dir / f"{g}.md").write_text(
            render_group(g, buckets[g], args.query, stamp), encoding="utf-8")
    # folder note: sits beside the folder, same name, so Obsidian treats it as its index
    (args.out_dir.parent / f"{args.out_dir.name}.md").write_text(index, encoding="utf-8")

    print(f"{len(entries)} words -> {args.out_dir}/")
    for g, _ in GROUPS:
        print(f"    {g}.md  {len(buckets[g])}")
