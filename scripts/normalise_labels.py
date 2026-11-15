#!/usr/bin/env python3
"""Normalise grammatical labels on Vocab notes to bracketed, dot-free Wiktionary style (Alex, 2026-11-16):
(m) (f) (n) (pl) (m pl) (indecl) (impf) (pf) (impf/pf) (coll) (adj) (adv) (noun) (intrans) (trans) (fig);
government stays +a +d +g +inst +pr. Idempotent; dry run by default, writes scratch/normalise_preview.txt.
Usage: ./scripts/normalise_labels.py [--apply]  (backup to tutoring/retired/)"""
import sys, re, json, time, collections
sys.path.insert(0, __import__('os').path.dirname(__file__))
import anki_utils as a
a.use_venv()

APPLY = '--apply' in sys.argv
SKIP_FIELDS = {'Audio', 'Example'}
stats = collections.Counter()

WHOLE = {'i': 'impf', 'і': 'impf', 'p': 'pf', 'р': 'pf', 'i/p': 'impf/pf', 'p only': 'pf only',
         'impf./pf.': 'impf/pf', 'colloquial': 'coll', 'intransitive': 'intrans', 'transitive': 'trans'}
DOTTED = re.compile(r'(?<![\w.])(coll|adj|adv|impf|pf|fig|intrans|trans|m|f|n|nt|pl|sg|indecl)\.(?=[\s)/,;]|$)')
GOV = [(re.compile(r'\+(?:i|ins|instr| ins| instr)(?![a-z])'), '+inst'), (re.compile(r'\+ ?dat(?![a-z])'), '+d'),
       (re.compile(r'\+ ?gen(?![a-z])'), '+g'), (re.compile(r'\+ ?acc(?![a-z])'), '+a'),
       (re.compile(r'\+ ?prep(?![a-z])'), '+pr')]
LATIN_PREP = re.compile(r'(?<![A-Za-z])([co])(?= \+)')
BARE = re.compile(r'(?<=[а-яёА-ЯЁ́]) (m|f|n)\.( pl\.)?( indecl\.?)?(?=[\s,<;]|$)')


def fix_bracket(m):
    inner = m.group(1)
    s = inner.strip()
    if s in WHOLE:
        stats[f'({s}) -> ({WHOLE[s]})'] += 1
        return '(' + inner.replace(s, WHOLE[s]) + ')'
    new = inner
    for mm in DOTTED.finditer(new):
        stats[f'{mm.group(0)} -> {mm.group(1)}'] += 1
    new = DOTTED.sub(r'\1', new)
    for rx, rep in GOV:
        for mm in rx.finditer(new):
            stats[f'{mm.group(0)} -> {rep}'] += 1
        new = rx.sub(rep, new)
    for mm in LATIN_PREP.finditer(new):
        stats[f'Latin {mm.group(1)} -> Cyrillic'] += 1
    new = LATIN_PREP.sub(lambda mm: {'c': 'с', 'o': 'о'}[mm.group(1)], new)
    return '(' + new + ')'


def fix_text(seg):
    seg = re.sub(r'\(([^()<>]*)\)', fix_bracket, seg)
    def bare(m):
        lab = m.group(1) + (' pl' if m.group(2) else '')
        out = f' ({lab})' + (' (indecl)' if m.group(3) else '')
        stats[f'bare {m.group(0).strip()} ->{out}'] += 1
        return out
    return BARE.sub(bare, seg)


def fix_field(v, front=False):
    if front:
        v = re.sub(r'\((noun|n)\.\)', lambda m: (stats.update(['Front (n.) -> (noun)']), '(noun)')[1], v)
    parts = re.split(r'(<[^>]*>|\[sound:[^\]]*\])', v)
    return ''.join(p if (p.startswith('<') or p.startswith('[sound:')) else fix_text(p) for p in parts)


ids = a.call('findNotes', query='deck:Vocab::*')
notes = []
for i in range(0, len(ids), 500):
    notes += a.call('notesInfo', notes=ids[i:i + 500])
changes, backup = [], []
for n in notes:
    upd = {}
    for k, v in n['fields'].items():
        if k in SKIP_FIELDS:
            continue
        new = fix_field(v['value'], front=(k == 'Front'))
        if new != v['value']:
            upd[k] = new
    if upd:
        changes.append((n['noteId'], upd))
        backup.append({'id': n['noteId'], 'old': {k: n['fields'][k]['value'] for k in upd}})

print(len(changes), 'notes would change')
for k, c in stats.most_common():
    print(f'{c:5}  {k}')
S = '/Users/alex/repos/russian/scratch/'
with open(S + 'normalise_preview.txt', 'w') as f:
    for (nid, upd), b in zip(changes, backup):
        for k in upd:
            o = re.sub(r'<[^>]+>', ' ', b['old'][k]); nn = re.sub(r'<[^>]+>', ' ', upd[k])
            f.write(f'{nid} {k}\n  - {o[:200]}\n  + {nn[:200]}\n')
if APPLY:
    path = f'/Users/alex/repos/russian/tutoring/retired/label-normalise-{time.strftime("%Y%m%d-%H%M%S")}.json'
    json.dump(backup, open(path, 'w'), ensure_ascii=False, indent=1)
    for nid, upd in changes:
        a.call('updateNoteFields', note={'id': nid, 'fields': upd})
    print('applied; backup', path)
