#!/usr/bin/env python3
"""Rebuild verb notes that have been switched to the "Cloze Aspect" note type.

Layout (settled with Alex on врать / совра́ть, 2026-10-07):
  Text  = <div class="ru-pair">impf / pf</div>          ← shown only on card 3
          <b>{{c3::English gloss}}</b>                   ← card 3 = Russian → English
          <table class="aspect">
            impf: {{c1::inf — 1sg, 2sg}}                 ← card 1
            pf:   {{c2::inf — 1sg, 2sg}}                 ← card 2
  Back Extra = {{c1::impf example}} {{c2::pf example}} {{c3::both}}   (rendered with cloze-only)
The other aspect's row is hidden by the note type's styling behind an "other aspect" link.

Forms come from the user's Wiktionary-derived "3000 Verbs" deck (1s / 2s / 3p, stressed). Verbs
whose 3pl isn't predictable from the 2sg (дать and compounds) also show the 3pl.

Scheduling: card 1 keeps its production (English → Russian) history and card 2 is given a copy
of it; card 3 is given the old recognition card's history (snapshot taken before the type change).
New notes: all three cards take card 1's queue position.
"""
import re
import sys

sys.path.insert(0, "scripts")
import anki_utils as a  # noqa: E402

TD = '<td style="padding: 2px 10px; vertical-align: top;">'
VOWELS = re.compile(r"[аеёиоуыэюяАЕЁИОУЫЭЮЯ]")
# дать and its prefixed compounds (+ созда́ть, same conjugation): дам, дашь … даду́т. Matched by
# prefix, not by suffix — a bare "-дать" ending also catches убежда́ть and опозда́ть, which are
# regular (found in the 2026-10-07 trial).
DAT_PREFIXES = ("", "про", "пере", "раз", "рас", "за", "вы", "от", "по", "из", "при", "пре", "об",
                "на", "у", "под", "до", "вос", "воз", "пред", "недо")


def irregular_3p(verb):
    v = a.destress(verb)
    return v == "создать" or (v.endswith("дать") and v[:-4] in DAT_PREFIXES)


def tidy(word):
    """Drop a stress mark on a one-syllable word (дать, дам, шить)."""
    return word.replace("́", "") if len(VOWELS.findall(word)) == 1 else word


def row(verb, s1, s2, p3, gov):
    txt = f"{tidy(verb)} — {tidy(s1)}, {tidy(s2)}"
    if irregular_3p(verb) and p3:
        txt += f" … {tidy(p3)}"
    return txt + (f" {gov}" if gov else "")


def build_text(gloss, pair_line, impf, pf, gov):
    return (f'<div class="ru-pair">{pair_line}</div><b>{{{{c3::{gloss}}}}}</b><br><br>'
            '<table class="aspect" style="margin: 0 auto; text-align: left; border-collapse: collapse;">'
            f'<tr>{TD}impf:</td>{TD}{{{{c1::{row(*impf, gov)}}}}}</td></tr>'
            f'<tr>{TD}pf:</td>{TD}{{{{c2::{row(*pf, gov)}}}}}</td></tr></table>')


def build_back_extra(ex_impf, ex_pf):
    return f"{{{{c1::{ex_impf}}}}} {{{{c2::{ex_pf}}}}} {{{{c3::{ex_impf}<br>{ex_pf}}}}}"


SCHED_KEYS = ["type", "queue", "due", "ivl", "factor", "reps", "lapses", "left"]


def sched(c):
    return [c["type"], c["queue"], c["due"], c["interval"], c["factor"], c["reps"], c["lapses"], c["left"]]


def copy_sched(card_id, values):
    r = a.call("setSpecificValueOfCard", card=card_id, keys=SCHED_KEYS, newValues=values, warning_check=True)
    assert r in (True, [True]), r
