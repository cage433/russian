#!/usr/bin/env python3
"""Restructure `Vocab::Verb forms` (2026-10-30, Alex): definitions on every card, and the
Prefixed notes laid out like `Vocab::Roots`.

  ::1 / ::2   the header gains the English: «бежа́ть  "to run"». Clozes untouched.
  ::3 Prefixed  header = base infinitive + English only (the base's conjugation gave the answer
              away). One row per prefixed verb: English | prefix (td.pc) | infinitive (+gov) |
              я, ты (td.vff) | prefix meaning (td.pm), all of a row under one cloze number, so
              the card asks English → infinitive + forms. Other rows show their infinitives;
              their forms stay hidden (CSS on td.vff), since they'd give the stem away.
              Spoken text changes, so the audio is regenerated.

Glosses, prefixes, prefix meanings and government overrides: scripts/verb_forms_glosses.tsv
(row: inf, prefix, gloss, meaning[, government]; base: ## inf, gloss[, government]). Cloze numbers are kept,
so card history survives. Backup in tutoring/retired/. Idempotent on the base decks; the
Prefixed rebuild reads the current rows, so it can be re-run after editing the TSV.

  ./scripts/verb_forms_restructure.py --dry-run
  ./scripts/verb_forms_restructure.py
"""
import sys, re, json, time, argparse
sys.path.insert(0, 'scripts')
import anki_utils as a
a.use_venv()

TSV = 'scripts/verb_forms_glosses.tsv'
TD = '<td%s style="padding: 2px 10px; vertical-align: top;">%s</td>'
OLD_CSS = 'table.vf-family .cloze-inactive { visibility: hidden; }'
NEW_CSS = 'table.vf-family td.vff .cloze-inactive, table.vf-family td.vfd .cloze-inactive { visibility: hidden; }'
strip = lambda s: ' '.join(re.sub(r'<[^>]+>|&nbsp;', ' ', s).split())

def load():
    A, cur = {}, None
    for l in open(TSV):
        l = l.rstrip('\n')
        if l.startswith('## '):
            f = l[3:].split('\t'); cur = a.destress(f[0])
            A[cur] = {'gloss': f[1], 'gov': f[2] if len(f) > 2 else None, 'rows': {}}
        elif l:
            f = l.split('\t')               # inf, prefix, gloss, prefix meaning[, government]
            A[cur]['rows'][a.destress(f[0])] = (f[1], f[2], f[3], f[4] if len(f) > 4 else None)
    return A

def family_text(base, gloss, rows):
    out = []
    twice = {inf for inf in [r[1] for r in rows] if [r[1] for r in rows].count(inf) > 1}
    for n, inf, gov, forms, (p, g, pm, gov2) in rows:
        gov = gov if gov2 is None else gov2
        # a verb split by construction has two rows: hide the other row's infinitive too
        dup = ' class="vfd"' if inf in twice else ''
        out.append('<tr>' + TD % ('', g) + TD % (' class="pc"', '{{c%d::%s}}' % (n, p))
                   + TD % (dup, '{{c%d::%s}}' % (n, inf + (' ' + gov if gov else '')))
                   + TD % (' class="vff"', '{{c%d::%s}}' % (n, forms))
                   + TD % (' class="pm"', '<i>%s</i>' % pm) + '</tr>')
    return ('<b>%s</b> &nbsp;"%s"<br><br><table class="vf vf-family" style="margin: 0 auto; '
            'text-align: left; border-collapse: collapse;">' % (base, gloss) + ''.join(out) + '</table>')

def old_rows(text):
    """Rows of a family note in either layout → [(n, infinitive, gov, forms)]."""
    rows = []
    for row in re.findall(r'<tr>(.*?)</tr>', text):
        tds = re.findall(r'<td[^>]*>(.*?)</td>', row)
        cl = [re.match(r'\{\{c(\d+)::(.*)\}\}$', t) for t in tds]
        if len(tds) == 2:                       # original: label | {{cN::forms}}
            lab = strip(tds[0]); inf = lab.split()[0]
            rows.append((int(cl[1].group(1)), inf, lab[len(inf):].strip(), cl[1].group(2)))
        else:                                   # rebuilt: gloss | pc | inf (gov) | forms | pm
            lab = cl[2].group(2); inf = lab.split()[0]
            rows.append((int(cl[3].group(1)), inf, lab[len(inf):].strip(), cl[3].group(2)))
    return rows

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    A = load()
    notes = a.call('notesInfo', notes=a.call('findNotes', query='tag:verb-forms'))
    updates, fam_ids = [], []
    for n in notes:
        t = n['fields']['Text']['value']
        if 'verb-forms-family' in n['tags']:
            m = re.search(r'<div class="vf-base">(.*?)</div>', t) or re.search(r'<b>(.*?)</b>', t)
            base = strip(m.group(1)).split(' — ')[0]
            fam = A[a.destress(base)]
            rows, seen = [], []
            for k, inf, gov, forms in old_rows(t):
                key = a.destress(inf) + ('#2' if a.destress(inf) in seen else '')
                seen.append(key)
                rows.append((k, inf, gov, forms, fam['rows'][key]))
            for key in fam['rows']:            # a sense split off by construction: new cloze number
                if key not in seen:
                    k, inf, gov, forms, _ = next(r for r in rows if a.destress(r[1]) == key.split('#')[0])
                    rows.append((max(r[0] for r in rows) + 1, inf, gov, forms, fam['rows'][key]))
            assert len(rows) == len(fam['rows']), base
            order = list(fam['rows'].values())
            rows.sort(key=lambda r: order.index(r[4]))
            new = family_text(base, fam['gloss'], rows)
            fam_ids.append(n['noteId'])
        else:
            head, rest = t.split('<br><br>', 1)
            base = strip(re.search(r'<b>(.*?)</b>', head).group(1))
            spec = A[a.destress(base)]
            gov = spec['gov'] or (strip(re.search(r'<span[^>]*>(.*?)</span>', head).group(1))
                                  if '<span' in head else '')
            new = ('<b>%s</b>' % base + (' <span style="font-weight: normal;">%s</span>' % gov if gov else '')
                   + ' &nbsp;"%s"<br><br>' % spec['gloss'] + rest)
        if new != t:
            updates.append((n, new))
    print(len(updates), 'notes to update,', len(fam_ids), 'Prefixed')
    if args.dry_run:
        for n, new in updates[:2] + [u for u in updates if u[0]['noteId'] in fam_ids][:1]:
            print(new, '\n')
        return
    stamp = time.strftime('%Y%m%d-%H%M%S')
    json.dump([{'noteId': n['noteId'], 'fields': {k: v['value'] for k, v in n['fields'].items()}} for n, _ in updates],
              open(f'tutoring/retired/verb-forms-restructure-{stamp}.json', 'w'), ensure_ascii=False, indent=0)
    css = a.call('modelStyling', modelName='Cloze')['css']
    if OLD_CSS in css:
        css = css.replace(OLD_CSS, NEW_CSS)
        css = re.sub(r'\.vf-base \{[^}]*\}\n?|\.nightMode \.vf-base \{[^}]*\}\n?', '', css)
        a.call('updateModelStyling', model={'name': 'Cloze', 'css': css})
    for n, new in updates:
        a.call('updateNoteFields', note={'id': n['noteId'], 'fields': {'Text': new}})
    redo = [n['noteId'] for n, _ in updates if n['noteId'] in fam_ids]
    for i in range(0, len(redo), 10):
        print(a.call('generateClozeAudio', noteIds=redo[i:i + 10], force=True))
    print('updated', len(updates))

if __name__ == '__main__':
    main()
