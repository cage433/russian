#!/usr/bin/env python3
"""Write Obsidian notes listing the vocab currently in Anki's learning steps, split by
part of speech.

Scope: cards in the **learning** state (first pass through the learning steps), per **card**: a Cloze-family note (root family,
near-synonym group, Cloze Aspect, Cloze Sentence) contributes only the rows whose cards are learning. — cards part-way through their
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
    ("Roots", {"root"}),          # root-family cloze rows go here only, whatever their POS
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
    sep = "<br>" if any(" — " in p for p in parts) else " / "     # conjugation rows: one per line
    return en, sep.join(p for p in parts if p)


CLOZE = re.compile(r"\{\{c(\d+)::(.*?)(?:::[^}]*)?\}\}", re.S)


def cloze_entry(model, text, ords):
    """Cloze-family notes (root families, near-synonym groups, Cloze Aspect, Cloze Sentence) ->
    (english, russian) for the row(s) the learning cards are teaching. One Anki note holds many
    words, so only the clozes whose cards are in the query are listed."""
    if model == "Cloze Aspect":
        pair = re.search(r'ru-pair[^>]*>(.*?)</div>', text, re.S)
        gloss = re.search(r"\{\{c3::(.*?)\}\}", text, re.S)
        # the conjugation rows (impf, then pf) rather than the bare pair
        rows = [clean(m.group(2)) for m in CLOZE.finditer(text) if m.group(1) in ("1", "2")]
        ru = "<br>".join(rows) if rows else (clean(pair.group(1)) if pair else "")
        return [(clean(gloss.group(1)) if gloss else "", ru)]
    if model == "Cloze Sentence":
        out = []
        for div in re.findall(r'<div class="sent">(.*?)</div>', text, re.S):
            m = CLOZE.search(div)
            if m and int(m.group(1)) in ords:
                en = re.search(r'<span class="en">(.*?)</span>', div, re.S)
                ru = CLOZE.sub(lambda x: f"**{x.group(2)}**", re.sub(r'<span class="en">.*?</span>', "", div, flags=re.S))
                out.append((clean(en.group(1)) if en else "", clean(ru)))
        return out
    head = re.search(r"<b>(.*?)</b>", text, re.S)
    head = clean(head.group(1)) if head else ""
    out = []
    for row in re.findall(r"<tr>(.*?)</tr>", text, re.S):
        nums = {int(n) for n, _ in CLOZE.findall(row)}
        if not nums & ords:
            continue
        cells = re.findall(r"<td([^>]*)>(.*?)</td>", row, re.S)
        word = " ".join(clean(c) for attrs, c in cells
                        if "{{c" in c and 'class="pc"' not in attrs and 'class="pm"' not in attrs)
        word = clean(CLOZE.sub(lambda x: x.group(2), word))
        gloss = [clean(c) for attrs, c in cells if "{{c" not in c and 'class="pm"' not in attrs
                 and not re.fullmatch(r"\s*\d+:\s*", clean(c))]
        en = gloss[0] if gloss else ""
        # near-synonym rows only make sense with their headword; root rows gain their root
        out.append((f"{head}: {en}" if head and not en.lower().startswith("to ") else en, word))
    return out


_FORMS = None


def forms_index():
    """destressed infinitive -> "infinitive — я, ты" from every Cloze Aspect row, falling back to
    the Wiktionary "3000 Verbs" deck."""
    global _FORMS
    if _FORMS is None:
        _FORMS = {}
        for i, ids in enumerate([a.call("findNotes", query='"note:3000 Verbs"')]):
            for j in range(0, len(ids), 500):
                for n in a.call("notesInfo", notes=ids[j:j + 500]):
                    f = n["fields"]
                    v = clean(f["Verb"]["value"]).strip()
                    d = dict(re.findall(r"<td>(1s|2s|3p)\s*</td><td><em>(.*?)</em>", f["Conjugation"]["value"]))
                    if d.get("1s") and d.get("2s"):
                        _FORMS.setdefault(v, f"{v} — {d['1s']}, {d['2s']}")
        ids = a.call("findNotes", query='"note:Cloze Aspect"')
        for j in range(0, len(ids), 500):
            for n in a.call("notesInfo", notes=ids[j:j + 500]):
                for m in CLOZE.finditer(n["fields"]["Text"]["value"]):
                    if m.group(1) in ("1", "2"):
                        row = clean(m.group(2))
                        head = row.split(" — ")[0].strip()
                        if " — " in row:
                            _FORMS[head] = re.sub(r"(\s*\([^)]*\))+\s*$", "", row)
    return _FORMS


def regular_forms(v):
    """Type-1 verbs that keep their -а-/-я- (чита́ть, пока́зывать, переде́лать) conjugate with the
    stress where the infinitive has it, so the forms can be built safely; anything else -> None."""
    m = re.match(r"^(.*[ая]́?)(ть)(ся)?$", v)
    if not m:
        return None
    import pymorphy3
    d = a.destress(v)
    ps = [p for p in pymorphy3.MorphAnalyzer().parse(d) if p.tag.POS == "INFN" and p.normal_form == d]
    if not ps:
        return None
    tense = "futr" if ps[0].tag.aspect == "perf" else "pres"
    f1 = ps[0].inflect({"1per", "sing", tense, "indc"})
    stem, refl = m.group(1), m.group(3) or ""
    if not f1 or f1.word != a.destress(stem) + ("юсь" if refl else "ю"):
        return None
    return f"{v} — {stem}ю{'сь' if refl else ''}, {stem}ешь{'ся' if refl else ''}"


def with_forms(ru):
    """'перевя́зывать / перевяза́ть (+a)' -> one conjugation row per verb, where known."""
    if " — " in ru:
        return ru
    m = re.match(r"^([а-яё́\-]+)(?:\s*/\s*([а-яё́\-]+))?\s*(.*)$", ru.replace("<br>", " "))
    if not m:
        return ru
    idx = forms_index()
    rows = [idx.get(v) or regular_forms(v) for v in m.groups()[:2] if v]
    if not rows or not all(rows):
        return ru
    gov = m.group(3).strip()
    return "<br>".join(r + (f" {gov}" if gov else "") for r in rows)


def pos_tags(en, tags):
    """Cloze rows mostly carry no POS tag; infer one from the gloss so they land in a group."""
    pos = tags & {"noun", "verb", "adj", "adv"}
    if pos:
        return pos
    if en.lower().startswith("to "):
        return {"verb"}
    if "(adj" in en:
        return {"adj"}
    return set()


def cards_for(query):
    cards = []
    cids = a.call("findCards", query=query)
    for i in range(0, len(cids), 500):
        cards += a.call("cardsInfo", cards=cids[i:i + 500])
    return cards


def fetch(query=None, cards=None):
    """-> list of (english, russian, {tags}) with fields cleaned but not yet condensed."""
    if cards is None:
        cards = cards_for(query)
    ords = {}
    for c in cards:
        ords.setdefault(c["note"], set()).add(c["ord"] + 1)
    nids = sorted(ords)
    out = []
    for i in range(0, len(nids), 500):
        for n in a.call("notesInfo", notes=nids[i:i + 500]):
            f = n["fields"]
            if "Text" in f:
                for en, ru in cloze_entry(n["modelName"], f["Text"]["value"], ords[n["noteId"]]):
                    if en or ru:
                        tags = {"root"} if "root" in n["tags"] else pos_tags(en, set(n["tags"]))
                        out.append((en, ru, tags))
                continue
            en, ru = clean(f["Front"]["value"]), clean(f["Back"]["value"])
            # The motion cards' `Verb of motion` header is card-type metadata, not gloss.
            # Left in, it sorts all nine under "V" and — worse — `briefly()` takes the first
            # <br>-line, so the English cell would read "Verb of motion" and lose the gloss.
            # The Back's (Abs)/(Conc) lines already carry the signal.
            en = re.sub(r"^Verb of motion<br>", "", en, flags=re.I)
            if en or ru:
                out.append((en, ru, set(n["tags"])))
    out = [(en, with_forms(ru) if ("verb" in tags or (tags == {"root"} and en.lower().startswith("to ")))
            else ru, tags) for en, ru, tags in out]
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


def render_group(name, pairs, query, stamp, coming=()):
    """Cards already in play (learning, or first seen in the last few days), then today's new ones."""
    out = render_section(pairs)
    if coming:
        out += "\n## New today\n\n" + render_section(coming)
    return out


def render_section(pairs):
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


def render_index(buckets, total, query, stamp, coming=None):
    coming = coming or {g: [] for g, _ in GROUPS}
    return "\n".join(["| Group | Learning |", "|---|---|"] +
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
    coming = {g: [] for g, _ in GROUPS}
    stamp = time.strftime("%Y-%m-%d %H:%M")
    index = render_index(buckets, len(entries), args.query, stamp, coming)

    if args.show:
        print(index)
        for g, _ in GROUPS:
            print("\n" + "=" * 60 + "\n")
            print(render_group(g, buckets[g], args.query, stamp, coming[g]))
        sys.exit()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for g, _ in GROUPS:
        (args.out_dir / f"{g}.md").write_text(
            render_group(g, buckets[g], args.query, stamp, coming[g]), encoding="utf-8")
    # folder note: sits beside the folder, same name, so Obsidian treats it as its index
    (args.out_dir.parent / f"{args.out_dir.name}.md").write_text(index, encoding="utf-8")

    print(f"{len(entries)} words -> {args.out_dir}/")
    for g, _ in GROUPS:
        print(f"    {g}.md  {len(buckets[g])}")
