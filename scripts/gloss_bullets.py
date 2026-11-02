#!/usr/bin/env python3
"""Multi-sense English glosses as a left-aligned bullet list (Alex, 2026-11-03).

A gloss whose senses are separated by top-level semicolons — "to delay; to detain" — becomes
  <div style="display: inline-block; text-align: left;"><ul …><li>to delay</li><li>to detain</li></ul></div>
centred as a block, left-aligned inside. Semicolons inside brackets ("(+a sth; +a s.o. +i sth)")
don't split. A trailing "<br>(cf. …)" line stays below the list. Applies to the Front of Basic
vocab cards and the English (c3) of Cloze Aspect notes; family and near-synonym tables are left
alone (Alex: too long for it). English only, so recordings are unaffected. Idempotent.

  ./scripts/gloss_bullets.py --dry-run
  ./scripts/gloss_bullets.py
"""
import sys, re, json, time
sys.path.insert(0, 'scripts')
import anki_utils as a
a.use_venv()

WRAP = '<div style="display: inline-block; text-align: left;">%s</div>'
UL = '<ul style="margin: 0; padding-left: 1.2em;">%s</ul>'
TAIL = re.compile(r'(?:<br\s*/?>\s*)+(?=\()', re.I)      # a following line that starts with "("


def split_top(s):
    out, depth, cur = [], 0, ''
    i = 0
    while i < len(s):
        m = re.match(r'&[a-z]+;|&#\d+;', s[i:])
        if m:
            cur += m.group(0); i += len(m.group(0)); continue
        ch = s[i]
        depth += ch == '('
        depth -= ch == ')'
        if ch == ';' and depth == 0:
            out.append(cur); cur = ''
        else:
            cur += ch
        i += 1
    return out + [cur]


def bullets(g):
    """gloss HTML → (new HTML, list?) or None if it has a single sense."""
    if '<ul' in g or re.search(r'(^|\s)\d+:\s', g):
        return None
    m = TAIL.search(g)
    head, tail = (g[:m.start()], g[m.start():]) if m else (g, '')
    items = [re.sub(r'^(?:\s|<br\s*/?>|&nbsp;)+|(?:\s|<br\s*/?>|&nbsp;)+$', '', x, flags=re.I)
             for x in split_top(head.replace('&nbsp;', ' '))]
    items = [x for x in items if x]
    if len(items) < 2:
        return None
    return UL % ''.join('<li>%s</li>' % x for x in items), tail


def main():
    dry = '--dry-run' in sys.argv
    todo = []
    for n in a.call('notesInfo', notes=a.call('findNotes', query='"note:Cloze Aspect"')):
        t = n['fields']['Text']['value']
        m = re.search(r'<b>\{\{c3::(.*?)\}\}</b>', t, re.S)
        if not m or t[max(0, m.start() - 60):m.start()].endswith('text-align: left;">'):
            continue
        r = bullets(m.group(1))
        if r:
            new = t[:m.start()] + WRAP % ('<b>{{c3::%s%s}}</b>' % r) + t[m.end():]
            todo.append((n, 'Text', new))
    for n in a.call('notesInfo', notes=a.call('findNotes', query='"note:Basic (and reversed card)" deck:Vocab::*')):
        f = n['fields']['Front']['value']
        if f.lstrip().startswith(WRAP.split('%s')[0]):
            continue
        r = bullets(f)
        if r:
            todo.append((n, 'Front', WRAP % r[0] + r[1]))
    print(len(todo), 'notes:', sum(1 for _, k, _ in todo if k == 'Text'), 'Cloze Aspect,',
          sum(1 for _, k, _ in todo if k == 'Front'), 'Basic')
    if dry:
        for n, k, new in todo[:4] + todo[-6:]:
            print('-', n['fields'][k]['value'][:160], '\n ->', new[:260])
        return
    json.dump([{'noteId': n['noteId'], 'field': k, 'old': n['fields'][k]['value']} for n, k, _ in todo],
              open(f"tutoring/retired/gloss-bullets-{time.strftime('%Y%m%d-%H%M%S')}.json", 'w'), ensure_ascii=False, indent=0)
    for n, k, new in todo:
        a.call('updateNoteFields', note={'id': n['noteId'], 'fields': {k: new}})
    print('updated', len(todo))


if __name__ == '__main__':
    main()
