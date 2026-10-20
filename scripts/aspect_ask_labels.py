#!/usr/bin/env python3
"""Say on the front what a Cloze Aspect row asks for (Alex, 2026-10-20).

Since the tricky rows were cut to the infinitive, a card may want just the infinitive or the
infinitive + я, ты. The row label (outside the cloze, visible on the front) gets a grey
<span class="ask">: «impf · inf. only» or «impf · inf., я, ты». Idempotent.

  ./scripts/aspect_ask_labels.py --dry-run
"""
import sys, re, argparse
sys.path.insert(0, 'scripts')
import anki_utils as a
a.use_venv()

def relabel(text):
    def fix(m):
        tr = m.group(0)
        if 'class="ask"' in tr: return tr
        cells = re.findall(r'(<td[^>]*>)(.*?)(</td>)', tr, re.S)
        if len(cells) < 2: return tr
        cm = re.search(r'\{\{c\d::(.*?)\}\}', cells[1][1], re.S)
        if not cm: return tr
        ask = 'inf., я, ты' if ' — ' in cm.group(1) else 'inf. only'
        o, lab, c = cells[0]
        lab2 = re.sub(r':\s*$', '', lab.strip())
        return tr.replace(o + lab + c, o + '%s <span class="ask">· %s</span>' % (lab2, ask) + c, 1)
    return re.sub(r'<tr>.*?</tr>', fix, text, flags=re.S)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    nids = a.call('findNotes', query='"note:Cloze Aspect"')
    n_changed = 0
    for i in range(0, len(nids), 200):
        for n in a.call('notesInfo', notes=nids[i:i + 200]):
            t = n['fields']['Text']['value']; new = relabel(t)
            if new == t: continue
            n_changed += 1
            if args.dry_run:
                if n_changed <= 3: print(re.sub(r'<(?!span)[^>]+>', ' ', new)[-260:])
                continue
            a.call('updateNoteFields', note={'id': n['noteId'], 'fields': {'Text': new}})
    print('notes', 'to change' if args.dry_run else 'changed', n_changed)
    if not args.dry_run:
        css = a.call('modelStyling', modelName='Cloze Aspect')['css']
        if '.ask' not in css:
            a.call('updateModelStyling', model={'name': 'Cloze Aspect', 'css': css +
                   '\n.ask { font-size: 0.75em; color: #888; white-space: nowrap; }\n'})

if __name__ == '__main__':
    main()
