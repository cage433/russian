#!/usr/bin/env python3
"""Rewrite the HyperTTS 'Back' preset's text-processing so <br> becomes a real pause.

Why: `strip_brackets` deletes anything in <...> (text_utils.py:62) and, with
`run_replace_rules_after` on, it runs before the replacement rules — so the existing
`<br>` -> <break/> rule never fires. Every multi-line Back is spoken as one run-on
line, and the 96 Backs holding &nbsp; emit stray semicolons.

Fix: turn bracket-stripping off and do it in the rules instead, matching the
SSML-escaped `&lt;br&gt;` (the SSML pass also runs before the rules).

Anki must be closed: HyperTTS caches the config at startup (hypertts.py:59) and
rewrites the whole dict on any save, so a live edit gets clobbered.

Add-ons do not sync, so this has to be run once per laptop. Idempotent — it just
stamps the rule list below over whatever is there, after backing meta.json up.
"""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

ADDON = Path.home() / "Library/Application Support/Anki2/addons21/111623432"
META = ADDON / "meta.json"
PRESET = "Back"
BACKUP_DIR = Path(__file__).resolve().parent.parent / "scratch/hypertts-config-backups"
APPLIED_MARKER = BACKUP_DIR / "last-applied"

CHECKBOXES = {
    "html_to_text_line": False,       # strip_html would eat <br> before the rules see it
    "strip_brackets": False,          # now done by a rule, for the same reason
    "strip_cloze": False,
    "ssml_convert_characters": True,  # escapes stray & and <; runs BEFORE the rules
    "run_replace_rules_after": True,  # so the SSML pass can't escape our own <break/>
    "ignore_case": False,
}

# Order matters twice over:
#  - the `/` rule must be FIRST: every SSML insertion contains a `/`, and a later
#    `/` rule would chew it into `<break time="150ms"<break time="100ms"/>>`.
#  - the <br> rule must match the ESCAPED form, because ssml_convert_characters
#    runs before the replacement rules.
RULES = [
    {"rule_type": "Simple", "source": "/", "target": '<break time="100ms"/>'},
    # Sense labels are silent; the line break below supplies the pause. One regex rather
    # than a rule per digit — it also covers senses past 7, which the old list didn't.
    # Safe as an unanchored match: no Back holds a digit-colon that isn't a sense label
    # (checked over all 10,721), and nothing inserted above this point contains one.
    {"rule_type": "Regex", "source": r"\d+:\s*", "target": ""},
    # ssml_convert_characters has already turned &nbsp; into &amp;nbsp;
    {"rule_type": "Simple", "source": "&amp;nbsp;", "target": " "},
    {"rule_type": "Regex", "source": r"(&lt;br\s*/?&gt;\s*)+", "target": '<break time="250ms"/>'},
    {"rule_type": "Regex", "source": r"&lt;[^&]*?&gt;", "target": ""},          # other tags, e.g. <i>
    {"rule_type": "Regex", "source": r"\([^)]*\)|\[[^\]]*\]", "target": ""},    # was strip_brackets
    # every Back ends in <br><br>, which would otherwise leave 250ms of dead air on
    # all 10,721 clips. Runs last, once the breaks above have been inserted.
    {"rule_type": "Regex", "source": r'(\s*<break time="\d+ms"/>)+\s*$', "target": ""},
    {"rule_type": "Regex", "source": r"^\s+|\s+$", "target": ""},
]


def anki_running():
    out = subprocess.run(["pgrep", "-f", "aqt.run"], capture_output=True, text=True)
    return bool(out.stdout.strip())


def read_preset():
    """-> (whole config dict, the 'Back' preset's text_processing dict). Raises if absent.

    Reading is safe with Anki up: meta.json on disk is the last state written. Only
    *writing* needs it closed.
    """
    cfg = json.loads(META.read_text())
    presets = [p for p in cfg["config"]["presets"].values() if p.get("name") == PRESET]
    if len(presets) != 1:
        raise LookupError(f"expected one preset named {PRESET!r}, found {len(presets)}")
    return cfg, presets[0]["text_processing"]


def drift():
    """-> list of setting names where the installed config differs from this file."""
    _, tp = read_preset()
    out = [k for k, v in CHECKBOXES.items() if tp.get(k) != v]
    if tp.get("text_replacement_rules") != RULES:
        out.append("text_replacement_rules")
    return out


def apply():
    """Stamp CHECKBOXES + RULES onto the installed preset. -> the backup path.

    Callers must check `anki_running()` first; this doesn't, so anki_doctor can decide
    what to do about it.
    """
    cfg, tp = read_preset()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(os.path.getmtime(META)))
    backup = BACKUP_DIR / f"meta.{stamp}.json"
    shutil.copy2(META, backup)
    tp.update(CHECKBOXES)
    tp["text_replacement_rules"] = RULES
    META.write_text(json.dumps(cfg, ensure_ascii=False, indent=1))
    # Records *our* write specifically. meta.json's own mtime can't stand in: HyperTTS
    # rewrites it whenever a preset is saved, so anki_doctor would read every ordinary
    # session as "edited behind Anki's back".
    APPLIED_MARKER.write_text(f"{time.time()}\n")
    return backup


def main():
    if anki_running():
        sys.exit("Anki is running — quit it first, or the change will be overwritten.")
    changes = drift()
    if not changes:
        print(f"already up to date ({len(RULES)} rules)")
        return
    print("differs:", ", ".join(changes))
    backup = apply()
    print(f"backed up -> {backup}")
    print(f"wrote {META} ({len(RULES)} rules)")


if __name__ == "__main__":
    main()
