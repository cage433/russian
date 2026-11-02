# -польз- split into I "use" / II "benefit" (2026-11-03). The old note becomes II, keeping по́льза's
# history on c1; its c4–c6 cards are left empty (Tools → Empty Cards).
import sys, json, time; sys.path.insert(0, 'scripts'); import anki_utils as a
TD = '<td%s style="padding: 2px 10px; vertical-align: top;">%s</td>'
HEAD = '<b>-польз- %s</b> &nbsp;"use, benefit"<br><br>'
I = [
 ('to use, make use of (a phone, a service); to enjoy (popularity, rights)', '—', 'по́льзоваться / воспо́льзоваться (+inst)', '(plain)'),
 ('to use, utilise (something for a purpose)', 'ис-', 'испо́льзовать (i/p) (+a)', '(idiomatic)'),
 ('to be used (passive)', 'ис- …-ся', 'испо́льзоваться', '(idiomatic)'),
 ('utilisation, application (of resources, methods)', 'ис-', 'испо́льзование', '(idiomatic)'),
 ('use (of a service), having the use of', '—', 'по́льзование (+inst)', '(plain)'),
 ('user', '—', 'по́льзователь', '(plain)'),
]
II = [
 ('benefit, usefulness', '—', 'по́льза', '(plain)'),
 ('useful, beneficial (adj.)', '—', 'поле́зный', '(plain)'),
 ('useless (adj.)', 'бес-', 'бесполе́зный', 'without'),
]
def text(part, rows):
    t = ''.join('<tr>' + TD % ('', g) + TD % (' class="pc"', '{{c%d::%s}}' % (i, p)) + TD % ('', '{{c%d::%s}}' % (i, w))
                + TD % (' class="pm"', '<i>%s</i>' % m) + '</tr>' for i, (g, p, w, m) in enumerate(rows, 1))
    return HEAD % part + '<table style="margin: 0 auto; text-align: left; border-collapse: collapse;">' + t + '</table>'
OLD, DELETE = 1791363621969, [1726634605458, 1726634612874]          # Basic испо́льзование, по́льзование
GLOSS = {1726634604958: ('{{c3::to use, utilize}}', '{{c3::to use, utilise (something for a purpose)}}'),
         1791455794277: ('{{c3::to use, make use of}}', '{{c3::to use, make use of; to enjoy (popularity, rights)}}'),
         1782914058831: ('{{c3::to be used}}', '{{c3::to be used (passive)}}')}
notes = a.call('notesInfo', notes=[OLD] + DELETE + list(GLOSS))
cards = a.call('cardsInfo', cards=[c for n in notes for c in n['cards']])
if not a.call('findNotes', query='"Text:*-польз- I*" -"Text:*-польз- II*"'):
  json.dump({'notes': notes, 'cards': cards}, open(f"tutoring/retired/polz-family-{time.strftime('%Y%m%d-%H%M%S')}.json", 'w'),
          ensure_ascii=False, indent=0)
au = notes[0]['fields']['Audio']['value']
snd = dict(re.findall(r'\{\{c(\d+)::(\[sound:[^\]]+\])\}\}', au)) if (re := __import__('re')) else None
if '-польз- II' not in notes[0]['fields']['Text']['value']:
  a.call('updateNoteFields', note={'id': OLD, 'fields': {'Text': text('II', II),
       'Audio': '{{c1::%s}} {{c2::%s}} {{c3::%s}}' % (snd['1'], snd['4'], snd['6'])}})
for nid, (o, n) in GLOSS.items():
    t = next(x for x in notes if x['noteId'] == nid)['fields']['Text']['value']
    if n in t: continue
    assert t.count(o) == 1, nid
    a.call('updateNoteFields', note={'id': nid, 'fields': {'Text': t.replace(o, n)}})
new = a.call('addNote', note={'deckName': 'Vocab::Roots', 'modelName': 'Cloze', 'tags': ['claude', 'root'],
             'fields': {'Text': text('I', I), 'Back Extra': '', 'Audio': ''}})
a.call('deleteNotes', notes=DELETE)
print(new, a.call('generateClozeAudio', noteIds=[new]))
