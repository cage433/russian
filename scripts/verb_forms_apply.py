#!/usr/bin/env python3
"""Apply the conjugation classification to Cloze Aspect notes (2026-10-20).

Each conjugation row gets a hidden rule cell (`<td class="rl">`), shown by the template's
"show rule" link. Rows the rules don't predict are cut down to the infinitive (+ government):
their card then asks only English → infinitive, and the forms are learned in `Vocab::Verb forms`.

  ./scripts/verb_forms_apply.py --dry-run [--limit N]
  ./scripts/verb_forms_apply.py            # writes; prints the note ids whose audio must be regenerated

Idempotent: a row that already has a rule cell is left alone.
"""
import sys, re, json, argparse
sys.path.insert(0, 'scripts')
import anki_utils as a
a.use_venv()
import conj_classify as cc

TD = '<td class="rl" style="padding: 2px 10px; vertical-align: top;">%s</td>'

def infinitive_only(raw):
    """«брать — беру́, берёшь (+a)» → «брать (+a)»; keeps trailing words of a phrase (вы́йти … за́муж)."""
    m = re.match(r'(.*?) — (.*)$', raw, re.S)
    if not m: return raw
    inf, rest = m.groups()
    rest = re.sub(r'…\s*\S+', '', rest)
    parts = rest.split(',', 1)
    tail = parts[1].strip() if len(parts) > 1 else ''
    tail = re.sub(r'^\S+', '', tail).strip()          # drop the ты form
    return (inf + (' ' + tail if tail else '')).strip()

def label_for(r):
    if r['kind'] != 'tricky': return r['label']
    own = re.sub('(ся|сь)$', '', cc.ds(r.get('inf', '')))
    like = r.get('base') and r['base'] not in (own, own + 'ся')
    return 'forms: Verb forms deck' + (' · like %s' % r['base'] if like else '')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    res = cc.classify_collection()
    by = {}
    for r in res: by[(r['note'], r['c'])] = r
    nids = sorted({r['note'] for r in res})
    if args.limit: nids = nids[:args.limit]
    changed, audio = 0, []
    for i in range(0, len(nids), 200):
        for n in a.call('notesInfo', notes=nids[i:i + 200]):
            text = n['fields']['Text']['value']
            new, cut = text, False
            def fix(m):
                nonlocal cut
                tr = m.group(0)
                if 'class="rl"' in tr: return tr
                cm = re.search(r'\{\{c(\d)::(.*?)\}\}', tr, re.S)
                if not cm: return tr
                r = by.get((n['noteId'], int(cm.group(1))))
                if not r: return tr
                if r['kind'] == 'tricky' and r['label'] != 'unparsed':
                    short = infinitive_only(cm.group(2))
                    if short != cm.group(2):
                        tr = tr.replace(cm.group(0), '{{c%s::%s}}' % (cm.group(1), short)); cut = True
                return tr.replace('</tr>', TD % label_for(r) + '</tr>')
            new = re.sub(r'<tr>.*?</tr>', fix, text, flags=re.S)
            if new == text: continue
            changed += 1
            if cut: audio.append(n['noteId'])
            if args.dry_run:
                if changed <= 6 or (cut and len(audio) <= 6):
                    print(n['noteId'], re.sub(r'<td class="rl"[^>]*>', '[RULE ', re.sub(r'<(?!td class="rl")[^>]+>', ' ', new))[-300:])
                continue
            a.call('updateNoteFields', note={'id': n['noteId'], 'fields': {'Text': new}})
    print('notes changed:', changed, ' rows cut to infinitive in', len(audio), 'notes')
    if not args.dry_run:
        json.dump(audio, open('scratch/verb_forms_audio_todo.json', 'w'))
        print('audio to regenerate: scratch/verb_forms_audio_todo.json')

if __name__ == '__main__':
    main()
