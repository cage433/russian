import sys, json, time; sys.path.insert(0, 'scripts'); import anki_utils as a
TD = '<td%s style="padding: 2px 10px; vertical-align: top;">%s</td>'
HEAD = ('<b>-меш- %s</b> &nbsp;"mix; get in the way"<br>'
        '<span style="font-size: 0.8em; color: #888;">not смеши́ть, смешно́й: those are смех</span><br><br>')
I = [
 ('to stir; to mix', '—', 'меша́ть (+a)', '(plain)'),
 ('to blend (one thing with another)', 'с-', 'сме́шивать / смеша́ть (+a с +inst)', 'together'),
 ('to mingle, blend (intrans.)', 'с- …-ся', 'сме́шиваться / смеша́ться (с +inst)', 'together'),
 ('to mix thoroughly; to shuffle (cards)', 'пере-', 'переме́шивать / перемеша́ть (+a)', 'all'),
 ('to stir in, dissolve (sugar in tea)', 'раз-', 'разме́шивать / размеша́ть (+a в +pr)', 'apart, all over'),
 ('to add in (as an ingredient)', 'при-', 'приме́шивать / примеша́ть (+a к +d)', 'addition'),
 ('mixture', 'с-', 'смесь (f)', 'together'),
 ('admixture, trace (of)', 'при-', 'при́месь (f)', 'addition'),
]
II = [
 ('to get in the way (of), hinder (+d)', '—', 'меша́ть / помеша́ть (+d)', '(plain)'),
 ('to interfere (in)', 'в- …-ся', 'вме́шиваться / вмеша́ться (в +a)', 'into'),
 ('interference (in)', 'в-', 'вмеша́тельство (в +a)', 'into'),
 ('hindrance; interference (on a line)', 'по-', 'поме́ха', '(idiomatic)'),
 ('confusion, consternation', 'за-', 'замеша́тельство', '(idiomatic)'),
 ('implicated, involved (in)', 'за-', 'заме́шан (в +pr)', '(idiomatic)'),
]
def text(part, rows):
    t = ''.join('<tr>' + TD % ('', g) + TD % (' class="pc"', '{{c%d::%s}}' % (i, p)) + TD % ('', '{{c%d::%s}}' % (i, w))
                + TD % (' class="pm"', '<i>%s</i>' % m) + '</tr>' for i, (g, p, w, m) in enumerate(rows, 1))
    return HEAD % part + '<table style="margin: 0 auto; text-align: left; border-collapse: collapse;">' + t + '</table>'
DELETE = [1726634611456, 1726634610366, 1726634611457, 1782914442649,   # aspect: меша́ть/смеша́ть, сме́шивать, сме́шиваться, переме́шивать
          1726634607371, 1726634613179, 1726634609019, 1726634611373]   # Basic: вмеша́тельство, замеша́тельство, при́месь, поме́ха
if '--dry' in sys.argv:
    print(text('I', I)); sys.exit()
notes = a.call('notesInfo', notes=DELETE + [1726634605008])
cards = a.call('cardsInfo', cards=[c for n in notes for c in n['cards']])
stamp = time.strftime('%Y%m%d-%H%M%S')
json.dump({'notes': notes, 'cards': cards}, open(f'tutoring/retired/mesh-family-{stamp}.json', 'w'), ensure_ascii=False, indent=0)
new = []
for part, rows in (('I', I), ('II', II)):
    new.append(a.call('addNote', note={'deckName': 'Vocab::Roots', 'modelName': 'Cloze', 'tags': ['claude', 'root'],
                      'fields': {'Text': text(part, rows), 'Back Extra': '', 'Audio': ''}}))
m = notes[-1]['fields']['Text']['value']
m2 = (m.replace('меша́ть / помеша́ть (+a) (+d)</div>', 'меша́ть / помеша́ть (+d)</div>')
       .replace('{{c3::to mix, stir (+a) / to hinder, prevent (+d)}}', '{{c3::to get in the way (of), hinder}}')
       .replace('меша́ешь (+a) (+d)}}', 'меша́ешь (+d)}}'))
assert m2.count('(+d)') == 3 and '(+a)' not in m2
a.call('updateNoteFields', note={'id': 1726634605008, 'fields': {'Text': m2}})
a.call('deleteNotes', notes=DELETE)
print('new', new, a.call('generateClozeAudio', noteIds=new))
