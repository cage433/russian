"""Rebuild the 797 tag:aspect-convert notes (already switched to Cloze Aspect) from the snapshots."""
import sys, re, json, glob
sys.path.insert(0, "scripts"); import anki_utils as a, aspect_cloze as ac
DRY = "--dry" in sys.argv
SP = "/private/tmp/claude-501/-Users-alex-repos-russian/7614c079-9005-40b1-8985-ac956cc10da1/scratchpad"
K = ["type", "queue", "due", "ivl", "factor", "reps", "lapses", "left"]
TD = '<td style="padding: 2px 10px; vertical-align: top;">'
snap = {}
for p in glob.glob("tutoring/retired/aspect-batchA*-before-*.json"):
    d = json.load(open(p))
    cards = {c["cardId"]: c for c in d["cards"]}
    for n in d["notes"]:
        snap[n["noteId"]] = (n, {cards[c]["ord"]: cards[c] for c in n["cards"]})
EXS = {}
for k in range(6):
    for o in json.load(open(f"{SP}/rv_out_{k}.json")): EXS[o["nid"]] = o
vn = a.call("notesInfo", notes=a.call("findNotes", query='"note:3000 Verbs"'))
V = {}
for n in vn:
    f = n["fields"]; verb = re.sub(r"<[^>]+>|&nbsp;", "", f["Verb"]["value"]).strip()
    V.setdefault(a.destress(verb), (verb, f["Aspect"]["value"].strip(),
                 dict(re.findall(r"<td>(1s|2s|3p)\s*</td><td><em>(.*?)</em>", f["Conjugation"]["value"]))))
def tup(word):
    if a.destress(word) == "быть": return ("быть", "бу́ду", "бу́дешь (pres. есть)", ""), "impf."
    verb, asp, d = V[a.destress(word)]
    return (ac.tidy(verb), d.get("1s", ""), d["2s"], d.get("3p", "")), asp
def clean(h): return re.sub(r"(&nbsp;|\s)+$", "", re.sub(r"\[sound:[^\]]*\]", "", h)).strip()
plan, problems = [], []
for nid in a.call("findNotes", query="tag:aspect-convert"):
    if nid not in snap: problems.append(("no snapshot", nid)); continue
    n, old = snap[nid]; f = n["fields"]
    back = clean(f["Back"]["value"]); lines = [l for l in re.split(r"<br\s*/?>", back) if re.sub(r"<[^>]+>|&nbsp;|\s", "", l)]
    first = re.sub(r"<[^>]+>", "", lines[0]).replace("&nbsp;", " ").strip()
    extra = "".join(f"<br><i>{l.strip()}</i>" for l in lines[1:])
    gloss = clean(f["Front"]["value"])
    ex = EXS.get(nid)
    if not ex: problems.append(("no example", nid, first)); continue
    m = re.match(r"^([а-яё́\-]+)\s*/\s*([а-яё́\-]+)\s*(.*)$", first, re.I)
    try:
        if m:
            (ti, _), (tp, _) = tup(m.group(1)), tup(m.group(2)); gov = m.group(3).strip()
            text = ac.build_text(gloss, f"{ti[0]} / {tp[0]}" + (f" {gov}" if gov else ""), ti, tp, gov)
            bx = ac.build_back_extra(ex["ex_impf"], ex["ex_pf"]) + extra
            kind = "pair"
        else:
            w = re.match(r"^([а-яё́\-]+)\s*(.*)$", first); t, asp = tup(w.group(1)); gov = w.group(2).strip()
            label = "i/p:" if "(i/p)" in gov or "," in asp else ("pf:" if asp.startswith("perf") else "impf:")
            gov2 = re.sub(r"\((i|p|i/p|impf\.?|pf\.?)\)\s*", "", gov).strip()
            text = (f'<div class="ru-pair">{t[0]}' + (f" {gov}" if gov else "") + f'</div><b>{{{{c3::{gloss}}}}}</b><br><br>'
                    '<table class="aspect" style="margin: 0 auto; text-align: left; border-collapse: collapse;">'
                    f"<tr>{TD}{label}</td>{TD}{{{{c1::{ac.row(*t, gov2)}}}}}</td></tr></table>")
            bx = f'{{{{c1::{ex["example"]}}}}} {{{{c3::{ex["example"]}}}}}' + extra
            kind = "single"
    except KeyError as e:
        problems.append(("forms", nid, first, str(e))); continue
    plan.append((nid, kind, text, bx, old))
print(len(plan), "to convert;", len(problems), "problems")
for p in problems[:30]: print(" ", p)
if DRY:
    for p in plan[:2] + [x for x in plan if x[1] == "single"][:2]: print(p[2]); print(p[3]); print()
    sys.exit()
for i, (nid, kind, text, bx, old) in enumerate(plan):
    a.call("updateNoteFields", note={"id": nid, "fields": {"Text": text, "Back Extra": bx, "Audio": ""}})
    cs = {c["ord"]: c for c in a.call("cardsInfo", cards=a.call("findCards", query=f"nid:{nid}"))}
    prod, rec = old[0], old.get(1)
    sv = lambda c: [c["type"], c["queue"], c["due"], c["interval"], c["factor"], c["reps"], 0, c["left"]]
    targets = {0: prod, 2: rec}
    if kind == "pair": targets[1] = prod
    for ord_, src in targets.items():
        if src is None or ord_ not in cs: continue
        assert a.call("setSpecificValueOfCard", card=cs[ord_]["cardId"], keys=K, newValues=sv(src), warning_check=True) in (True, [True])
    if (i + 1) % 100 == 0: print(i + 1, flush=True)
a.call("removeTags", notes=[p[0] for p in plan], tags="aspect-convert")
a.call("addTags", notes=[p[0] for p in plan], tags="aspect")
json.dump([p[0] for p in plan], open(f"{SP}/converted_ids.json", "w"))
print("converted", len(plan))
