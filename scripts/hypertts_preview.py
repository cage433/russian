#!/usr/bin/env python3
"""Run HyperTTS's own text pipeline over every Back and report what Google would hear.

Imports `text_utils.py` straight from the installed add-on (with its import/logging lines
stripped) so this is HyperTTS's code, not a reimplementation of it — the whole point is to
check the real rule list, including the ordering traps documented in CLAUDE.md.

Reads the collection through AnkiConnect when Anki is up, and from a copy of
collection.anki2 when it isn't, so it works either way.

  scripts/hypertts_preview.py                 # audit the saved rules
  scripts/hypertts_preview.py --proposed      # audit scripts/hypertts_text_processing.py's
                                              # RULES instead, and diff against the saved ones
  scripts/hypertts_preview.py --grep '\\d+:'   # show Backs matching a regex, with output
"""
import argparse, html, json, re, shutil, sqlite3, subprocess, sys, tempfile, types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anki_utils as a
a.use_venv()

ADDON = Path.home() / "Library/Application Support/Anki2/addons21/111623432"
COLLECTION = Path.home() / "Library/Application Support/Anki2/User 1/collection.anki2"
NOTETYPE = "Basic (and reversed card)"


def load_pipeline():
    """HyperTTS's text_utils, importable outside Anki."""
    src = ADDON.joinpath("hypertts_addon/text_utils.py").read_text()
    src = "\n".join(l for l in src.split("\n") if not l.startswith(("import ", "from ")))
    src = src.replace("logger = logging_utils.get_child_logger(__name__)", "")
    ns = {"re": re, "html": html,
          "constants": types.SimpleNamespace(
              TextReplacementRuleType=types.SimpleNamespace(Regex="Regex", Simple="Simple")),
          "logger": types.SimpleNamespace(debug=lambda *x: None, info=lambda *x: None),
          "errors": types.SimpleNamespace(TextReplacementError=Exception)}
    exec(src, ns)
    return ns


class _Rule:
    def __init__(s, d): s.rule_type, s.source, s.target = d["rule_type"], d["source"], d["target"]


class _Model:
    def __init__(s, d):
        s.__dict__.update({k: v for k, v in d.items() if k != "text_replacement_rules"})
        s.text_replacement_rules = [_Rule(r) for r in d["text_replacement_rules"]]


def saved_text_processing():
    cfg = json.loads(ADDON.joinpath("meta.json").read_text())
    preset = next(v for v in cfg["config"]["presets"].values() if v.get("name") == "Back")
    return preset["text_processing"]


def read_backs():
    """-> list of Back field values, via AnkiConnect if Anki is up, else via sqlite."""
    if not subprocess.run(["pgrep", "-f", "aqt.run"], capture_output=True).stdout.strip():
        db = Path(tempfile.mkdtemp()) / "collection.anki2"
        shutil.copy2(COLLECTION, db)
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        # Anki registers this collation itself; we only need it to satisfy the schema
        con.create_collation("unicase", lambda x, y: (x.lower() > y.lower()) - (x.lower() < y.lower()))
        mids = [r[0] for r in con.execute("select id from notetypes where name=?", (NOTETYPE,))]
        rows = con.execute(f"select flds from notes where mid in ({','.join('?' * len(mids))})", mids)
        return [r[0].split("\x1f")[1] for r in rows]
    ids = a.call("findNotes", query=f'"note:{NOTETYPE}"')
    out = []
    for i in range(0, len(ids), 500):
        out += [n["fields"]["Back"]["value"] for n in a.call("notesInfo", notes=ids[i:i + 500])]
    return out


BREAK = re.compile(r'<break time="\d+ms"/>')
BR = re.compile(r"<br\s*/?>", re.I)


def core(back):
    """The Back as the learner sees it: no sound tag, no trailing <br><br>."""
    return re.sub(r"(<br\s*/?>\s*)+$", "", re.sub(r"\[sound:[^\]]*\]", "", back)).strip()


def anomalies(back, out):
    """Ways the spoken text can be wrong that a human wouldn't spot in a rule list."""
    bare = BREAK.sub("", out)
    if any(c in bare for c in "&<>"):
        return "STRAY-MARKUP"
    if ";" in bare and ";" not in core(back):
        return "STRAY-SEMICOLON"      # the &nbsp; residue this config was written to kill
    if re.search(r"[а-яё]", core(back), re.I) and not re.search(r"[а-яё]", bare, re.I):
        return "LOST-ALL-RUSSIAN"
    if out != out.strip():
        return "EDGE-WHITESPACE"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposed", action="store_true",
                    help="use RULES from hypertts_text_processing.py instead of the saved config")
    ap.add_argument("--grep", metavar="REGEX", help="only show Backs matching this")
    args = ap.parse_args()

    tu = load_pipeline()
    saved = saved_text_processing()
    model = _Model(saved)
    other = None
    if args.proposed:
        from hypertts_text_processing import RULES, CHECKBOXES
        proposed = {**saved, **CHECKBOXES, "text_replacement_rules": RULES}
        other, model = model, _Model(proposed)
        print(f"comparing SAVED ({len(saved['text_replacement_rules'])} rules) "
              f"-> PROPOSED ({len(RULES)} rules)\n")

    backs = read_backs()
    print(f"{len(backs)} Backs, {sum(1 for b in backs if BR.search(core(b)))} of them multi-line")

    if args.grep:
        pat = re.compile(args.grep)
        hits = [b for b in backs if pat.search(core(b))]
        print(f"\n{len(hits)} Backs match /{args.grep}/")
        for b in hits[:25]:
            print(f"  in : {core(b)[:95]}")
            print(f"  out: {tu['process_text'](b, model)[:110]}")
        return

    bad, changed = [], 0
    for b in backs:
        out = tu["process_text"](b, model)
        if other is not None and tu["process_text"](b, other) != out:
            changed += 1
        kind = anomalies(b, out)
        if kind:
            bad.append((kind, b, out))
    if other is not None:
        print(f"output differs on {changed} Backs")
    print(f"anomalies: {len(bad)}")
    for kind, b, out in bad[:15]:
        print(f"  {kind}\n    in : {core(b)[:100]}\n    out: {out[:100]}")

    print("\nsamples:")
    for b in [x for x in backs if BR.search(core(x))][:5]:
        print(f"  in : {core(b)[:95]}")
        print(f"  out: {tu['process_text'](b, model)[:110]}\n")


if __name__ == "__main__":
    main()
