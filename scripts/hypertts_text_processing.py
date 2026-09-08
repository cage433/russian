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
BACKUP_DIR = Path(__file__).resolve().parent.parent / "scratch/hypertts-config-backups"

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


def main():
    if anki_running():
        sys.exit("Anki is running — quit it first, or the change will be overwritten.")

    cfg = json.loads(META.read_text())
    presets = cfg["config"]["presets"]
    matches = [(k, v) for k, v in presets.items() if v.get("name") == "Back"]
    assert len(matches) == 1, f"expected one preset named 'Back', got {[v.get('name') for v in presets.values()]}"
    uuid, preset = matches[0]

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(os.path.getmtime(META)))
    backup = BACKUP_DIR / f"meta.{stamp}.json"
    shutil.copy2(META, backup)
    print(f"backed up {META} -> {backup}")

    tp = preset["text_processing"]
    print("before:", json.dumps({k: v for k, v in tp.items() if k != "text_replacement_rules"}))
    tp.update(CHECKBOXES)
    tp["text_replacement_rules"] = RULES
    print("after :", json.dumps({k: v for k, v in tp.items() if k != "text_replacement_rules"}))

    META.write_text(json.dumps(cfg, ensure_ascii=False, indent=1))
    print(f"wrote {META} ({len(RULES)} rules)")


if __name__ == "__main__":
    main()
