"""Reusable helpers for building Точка Ру Anki vocab decks.

Run with the project venv:  ~/repos/russian-anki/.venv/bin/python
Needs Anki running with the AnkiConnect add-on (localhost:8765).
"""
import urllib.request, json, re, unicodedata

ANKI = "http://localhost:8765"
MODEL = "Basic (and reversed card)"          # note type used by all vocab decks
FIELDS = ("Front", "Back", "Example")

_morph = None
def morph():
    global _morph
    if _morph is None:
        import pymorphy3
        _morph = pymorphy3.MorphAnalyzer()
    return _morph

def call(action, **params):
    data = json.dumps({"action": action, "version": 6, "params": params}).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(ANKI, data=data)))
    if r.get("error"):
        raise RuntimeError(f"{action}: {r['error']}")
    return r["result"]

def call_soft(action, **params):
    """Like call() but returns the raw {result,error} dict (for dupe-tolerant addNote)."""
    data = json.dumps({"action": action, "version": 6, "params": params}).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(ANKI, data=data)))

# --- Cyrillic normalisation -------------------------------------------------
def destress(s):
    """Strip ONLY the stress accent (U+0301/U+0300); keep й and ё intact."""
    s = unicodedata.normalize("NFD", s).replace("́", "").replace("̀", "")
    return unicodedata.normalize("NFC", s).lower()

def norm(field_html):
    """Back-field HTML -> destressed plain text (drops [sound:], tags, &nbsp;)."""
    s = re.sub(r"\[sound:[^\]]*\]", "", field_html)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;?", " ", s)
    return destress(s)

def lemma(word):
    return morph().parse(word)[0].normal_form

# --- filter set (words already known) --------------------------------------
def build_known(decks):
    """Union of normalised surface forms + pymorphy lemmas across the given decks.
    Typical: ["Vocab::10000 words","Vocab::RLC","Vocab::Tochka Ru::B1.1", ...]."""
    known = set()
    for d in decks:
        for n in call("notesInfo", notes=call("findNotes", query=f'deck:"{d}"')):
            for w in re.findall(r"[а-яё]+(?:-[а-яё]+)?", norm(n["fields"]["Back"]["value"])):
                if len(w) >= 2:
                    known.add(w); known.add(lemma(w))
    return known

# --- PDF text ---------------------------------------------------------------
def page_text(pdf_path, start, end):
    """1-indexed inclusive page range -> text (vector PDFs; no OCR)."""
    import fitz
    d = fitz.open(pdf_path)
    return "\n".join(d[i].get_text() for i in range(start - 1, end))

# --- authoring --------------------------------------------------------------
def add_notes(deck, rows):
    """rows: list of (back, front, example, tags). tags may be a str (POS) -> [pos,'claude']
    or a list. Appends a trailing <br><br> to Back. Adds one-by-one so Front-duplicate
    collisions (checked across the whole note type, incl. 10K) are skipped, not fatal."""
    ok = dup = err = 0; errs = []
    for back, front, example, tags in rows:
        back = re.sub(r"(<br>\s*)+$", "", back).rstrip() + "<br><br>"
        tags = tags if isinstance(tags, list) else [tags, "claude"]
        note = {"deckName": deck, "modelName": MODEL,
                "fields": {"Front": front, "Back": back, "Example": example},
                "tags": tags, "options": {"allowDuplicate": False}}
        r = call_soft("addNote", note=note)
        if r.get("error"):
            if "duplicate" in str(r["error"]): dup += 1
            else: err += 1; errs.append((front, r["error"]))
        else: ok += 1
    print(f"{deck}: added {ok}, dupe {dup}, err {err}")
    for f, e in errs[:10]: print("   ERR", f, e)
    return ok, dup, err

def strip_pos_from_front(deck):
    """Remove '(noun)/(adj)/(verb)/(adv)' POS descriptors from English Fronts
    (keep only on genuine ambiguity, which you add by hand)."""
    POS = r"noun|adj|adjective|verb|adv|adverb"
    upd = 0
    for n in call("notesInfo", notes=call("findNotes", query=f'deck:"{deck}"')):
        f = n["fields"]["Front"]["value"]
        s = re.sub(rf"\((?:{POS}),\s*", "(", f)
        s = re.sub(rf"\((?:{POS});\s*", "(", s)
        s = re.sub(rf"\s*\((?:{POS})\)\s*$", "", s).strip()
        if s != f:
            call("updateNoteFields", note={"id": n["noteId"], "fields": {"Front": s}}); upd += 1
    print(f"{deck}: stripped POS from {upd} fronts")
