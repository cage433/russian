"""Per-cloze HyperTTS recordings for Cloze notes.

A Cloze note's fields are shared by all its cards, so one `[sound:]` would play on every card.
Instead the note's `Audio` field holds one recording per cloze number, each wrapped in its own
cloze — `{{c1::[sound:a.mp3]}} {{c2::[sound:b.mp3]}}` — and the answer template renders it with
`{{cloze-only:Audio}}`, which emits only the current card's deletion. Anki extracts sound tags
after rendering, so exactly one recording plays, on Show Answer, on every client (the files are
ordinary synced media; no add-on is needed to play them).

Generation goes through HyperTTS's own objects, so the voice, text processing and file cache are
those of the Basic cards' preset (PRESET). HyperTTS keeps its HyperTTS instance only in GUI
closures, so it is found by type via `gc`; if a HyperTTS update renames things, this fails loudly
rather than writing anything.
"""
import gc
import importlib
import re
import sys

PRESET = "Back"          # the HyperTTS preset the Basic vocab cards use (scripts/hypertts_text_processing.py)
AUDIO_FIELD = "Audio"
CLOZE_RE = re.compile(r"\{\{c(\d+)::(.*?)(?:::[^}]*)?\}\}", re.S)

_hyper = None


def _hypertts():
    global _hyper
    if _hyper is None:
        for o in gc.get_objects():
            t = type(o)
            if t.__name__ == "HyperTTS" and t.__module__.endswith("hypertts_addon.hypertts"):
                _hyper = o
                break
        else:
            raise RuntimeError("HyperTTS instance not found (is HyperTTS installed and enabled?)")
    return _hyper


def _hmod(name):
    pkg = sys.modules[type(_hypertts()).__module__].__package__
    return importlib.import_module(f"{pkg}.{name}")


def _preset():
    h = _hypertts()
    ids = [p.id for p in h.get_preset_list() if p.name == PRESET]
    if len(ids) != 1:
        raise LookupError(f"expected one HyperTTS preset named {PRESET!r}, found {len(ids)}")
    return h.load_preset(ids[0])


def _is_prefix_cell(t):
    # Root-family cards hide the prefix cell with the word's cloze number: «у-», «про- + воз-»,
    # «от- …-ся», «—», «— …-ся». Those must not be spoken.
    t = t.strip()
    return t.startswith("—") or t.endswith("-") or t.endswith("-ся")


CYRILLIC = re.compile(r"[а-яё]", re.I)
RU_PAIR_RE = re.compile(r'<div class="ru-pair">(.*?)</div>', re.S)


def answers(text):
    """{cloze number: text to speak} for a Cloze note's Text field.

    A cloze whose hidden text has no Russian in it — the English header that Cloze Aspect's
    card 3 (Russian → English) hides — is spoken from the note's `ru-pair` line instead, i.e.
    the two infinitives, so the Russian voice never reads English."""
    out = {}
    for m in CLOZE_RE.finditer(text):
        n, t = int(m.group(1)), re.sub(r"<[^>]+>", " ", m.group(2))
        if _is_prefix_cell(t):
            continue
        out.setdefault(n, []).append(t.strip())
    ans = {n: " ".join(v) for n, v in out.items()}
    pair = RU_PAIR_RE.search(text)
    for n, t in list(ans.items()):
        # "English" = more Latin letters than Cyrillic — not "no Cyrillic at all": a gloss's
        # `(cf. ***** в/на = …)` line carries a little Russian, and the bare test let учи́ться's
        # card 3 read its English gloss in the Russian voice.
        if len(re.findall(r"[a-z]", t, re.I)) > len(CYRILLIC.findall(t)):
            if pair:
                ans[n] = re.sub(r"<[^>]+>", " ", pair.group(1)).strip()
            else:
                del ans[n]
    return ans


def generate(col, note_ids, force=False, dry_run=False):
    h = _hypertts() if not dry_run else None
    batch = _preset() if not dry_run else None
    ctx_mod = _hmod("context") if not dry_run else None
    consts = _hmod("constants") if not dry_run else None
    results = []
    for nid in note_ids:
        note = col.get_note(int(nid))
        if AUDIO_FIELD not in note.keys():
            results.append({"noteId": nid, "skipped": f"no {AUDIO_FIELD} field"})
            continue
        if note[AUDIO_FIELD].strip() and not force:
            results.append({"noteId": nid, "skipped": "has audio"})
            continue
        ans = answers(note["Text"])
        if dry_run:
            results.append({"noteId": nid, "answers": ans})
            continue
        tags = []
        for n in sorted(ans):
            processed = h.process_text(ans[n], batch.text_processing)
            ctx = ctx_mod.AudioRequestContext(consts.AudioRequestReason.batch)
            full, fname = h.get_audio_file(processed, batch.voice_selection, ctx)
            tag, _ = h.get_collection_sound_tag(full, fname)
            tags.append(f"{{{{c{n}::{tag}}}}}")
        note[AUDIO_FIELD] = " ".join(tags)
        col.update_note(note)
        results.append({"noteId": nid, "clozes": len(tags)})
    return results


SOUND_RE = re.compile(r"\s*\[sound:[^\]]*\]")


def generate_basic(col, note_ids, field="Back", dry_run=False):
    """Re-record a Basic note's Back: speak the field without its old [sound:] (the Back preset's
    text processing strips brackets and turns <br> into pauses, exactly as the HyperTTS batch
    did), then put the new tag where the old one was — after the trailing <br><br>."""
    h = _hypertts() if not dry_run else None
    batch = _preset() if not dry_run else None
    ctx_mod = _hmod("context") if not dry_run else None
    consts = _hmod("constants") if not dry_run else None
    results = []
    for nid in note_ids:
        note = col.get_note(int(nid))
        if field not in note.keys():
            results.append({"noteId": nid, "skipped": f"no {field} field"})
            continue
        text = SOUND_RE.sub("", note[field]).rstrip()
        if dry_run:
            results.append({"noteId": nid, "text": text})
            continue
        processed = h.process_text(text, batch.text_processing)
        full, fname = h.get_audio_file(processed, batch.voice_selection,
                                       ctx_mod.AudioRequestContext(consts.AudioRequestReason.batch))
        tag, _ = h.get_collection_sound_tag(full, fname)
        if not text.endswith("<br><br>"):
            text += "<br><br>"
        note[field] = f"{text} {tag}"
        col.update_note(note)
        results.append({"noteId": nid, "sound": tag})
    return results
