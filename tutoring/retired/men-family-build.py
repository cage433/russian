# -мен- regrouped into I "change" / II "replace, exchange" / III "apply, cancel, betray" (2026-11-03).
# I and II are the existing notes (I keeps меня́ть's history on c1); III is new. Loose aspect and
# Basic notes for words now on the family are retired; the duplicate меня́ть aspect note goes.
import sys, json, time, re; sys.path.insert(0, 'scripts'); import anki_utils as a
TD = '<td%s style="padding: 2px 10px; vertical-align: top;">%s</td>'
HEAD = '<b>-мен- %s</b> &nbsp;"change, exchange"<br><br>'
I = [
 ('to change, swap', '—', 'меня́ть / поменя́ть (+a)', '(plain)'),
 ('to change (oneself); to swap (with each other)', '— …-ся', 'меня́ться / поменя́ться', '(plain)'),
 ('to change, alter (something)', 'из-', 'изменя́ть / измени́ть (+a)', '(idiomatic)'),
 ('to change (intrans.), undergo change', 'из- …-ся', 'изменя́ться / измени́ться', '(idiomatic)'),
 ('change, alteration', 'из-', 'измене́ние', '(idiomatic)'),
 ('change, break (between lessons)', 'пере-', 'переме́на', 'again, over'),
 ('to change, transform (lit.)', 'пере-', 'переменя́ть / перемени́ть (+a)', 'again, over'),
 ('to change (intrans.) (lit.)', 'пере- …-ся', 'переменя́ться / перемени́ться', 'again, over'),
]
II = [
 ('to replace (something with something)', 'за-', 'заменя́ть / замени́ть (+a +inst)', 'in place of'),
 ('replacement, substitute', 'за-', 'заме́на', 'in place of'),
 ('to replace, relieve (keeping the role: a shift, a guard)', 'с-', 'сменя́ть / смени́ть (+a)', '(idiomatic)'),
 ('to give way (to), be replaced; to alternate', 'с- …-ся', 'сменя́ться / смени́ться', '(idiomatic)'),
 ('change, replacement; shift (at work)', 'с-', 'сме́на', '(idiomatic)'),
 ('to exchange (something for something)', 'об-', 'обме́нивать / обменя́ть (+a на +a)', '(idiomatic)'),
 ('to exchange (with each other), swap', 'об- …-ся', 'обме́ниваться / обменя́ться (+inst)', '(idiomatic)'),
 ('exchange', 'об-', 'обме́н', '(idiomatic)'),
 ('to trade away (for something worse)', 'про-', 'проме́нивать / променя́ть (+a на +a)', '(idiomatic)'),
 ('in exchange (for), instead (of)', 'вз-', 'взаме́н (+g)', '(idiomatic)'),
]
III = [
 ('to apply, use, employ', 'при-', 'применя́ть / примени́ть (+a)', '(idiomatic)'),
 ('to be applied; to adapt (to)', 'при- …-ся', 'применя́ться / примени́ться (к +d)', '(idiomatic)'),
 ('application, use', 'при-', 'примене́ние', '(idiomatic)'),
 ('to cancel, abolish', 'от-', 'отменя́ть / отмени́ть (+a)', 'undoing'),
 ('cancellation, abolition', 'от-', 'отме́на', 'undoing'),
 ('to betray, be unfaithful to', 'из-', 'изменя́ть / измени́ть (+d)', '(idiomatic)'),
 ('betrayal, treason; infidelity', 'из-', 'изме́на', '(idiomatic)'),
 ('traitor', 'из-', 'изме́нник', '(idiomatic)'),
]
def text(part, rows):
    t = ''.join('<tr>' + TD % ('', g) + TD % (' class="pc"', '{{c%d::%s}}' % (i, p)) + TD % ('', '{{c%d::%s}}' % (i, w))
                + TD % (' class="pm"', '<i>%s</i>' % m) + '</tr>' for i, (g, p, w, m) in enumerate(rows, 1))
    return HEAD % part + '<table style="margin: 0 auto; text-align: left; border-collapse: collapse;">' + t + '</table>'
N1, N2, IZM = 1791380474747, 1791380474997, 1791455795377
DELETE = [1726634606057,                                                   # duplicate меня́ть aspect note
          1698948691475, 1726634606720, 1726634607959, 1726634610028, 1726634612328,  # aspect: обме́нивать, применя́ться, сменя́ться, переменя́ться, проме́нивать
          1726634606756, 1726634608944, 1726634610220, 1726634610591, 1726634610878]  # Basic: обме́н, заме́на, изме́нник, отме́на, изме́на
notes = a.call('notesInfo', notes=[N1, N2, IZM] + DELETE)
cards = a.call('cardsInfo', cards=[c for n in notes for c in n['cards']])
revs = a.call('getReviewsOfCards', cards=[c['cardId'] for c in cards])
json.dump({'notes': notes, 'cards': cards, 'reviews': revs},
          open(f"tutoring/retired/men-family-{time.strftime('%Y%m%d-%H%M%S')}.json", 'w'), ensure_ascii=False, indent=0)
a.call('updateNoteFields', note={'id': N1, 'fields': {'Text': text('I', I)}})
a.call('updateNoteFields', note={'id': N2, 'fields': {'Text': text('II', II)}})
t = notes[2]['fields']['Text']['value']
o = re.search(r'\{\{c3::[^}]*\}\}', t).group(0)
a.call('updateNoteFields', note={'id': IZM, 'fields': {'Text': t.replace(o, '{{c3::to change, alter (+a); to betray, be unfaithful to (+d)}}')}})
n3 = a.call('addNote', note={'deckName': 'Vocab::Roots', 'modelName': 'Cloze', 'tags': ['claude', 'root'],
            'fields': {'Text': text('III', III), 'Back Extra': '', 'Audio': ''}})
a.call('deleteNotes', notes=DELETE)
for ids, force in (([N1, N2], True), ([n3], False)):
    print(a.call('generateClozeAudio', noteIds=ids, force=force))
