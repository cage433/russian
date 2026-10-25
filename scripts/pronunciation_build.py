#!/usr/bin/env python3
"""Build the Pronunciation deck: listening cards for sounds an English ear merges.

One note per word, note type "Pronunciation": the front is only a label naming the contrast
(«ш or щ?») and the recording; the back is the word, its gloss, and its minimal-pair partner
with the partner's recording, which autoplays so the two can be compared. Words come in
minimal pairs: with a word you know, its spelling would give the answer away, so only a
partner that differs in the target sound alone makes the card a test of hearing.

Audio is the Back preset's HyperTTS voice via the add-on's generateBasicAudio: the word is
written into Audio, recorded, then Audio is cut down to the bare [sound:] tag.
Idempotent: existing notes (by Word) are skipped. Decks start paused (Shared preset, 0/day).
"""
import sys
sys.path.insert(0, 'scripts')
import anki_utils as a
a.use_venv()
import re

ROOT = 'Pronunciation'
MODEL = 'Pronunciation'
TAGS = ['claude', 'pronunciation']

SETS = [
    ('ш vs щ', 'ш or щ?', [
        (('ча́ша', 'cup, bowl'), ('ча́ща', 'thicket')),
        (('шит', 'sewn'), ('щит', 'shield')),
        (('шёлк', 'silk'), ('щёлк', 'click!')),
        (('пишу́', 'I write'), ('пищу́', 'I squeak')),
        (('шиплю́', 'I hiss'), ('щиплю́', 'I pinch')),
    ]),
    ('Final ь', 'ь or not?', [
        (('у́гол', 'corner'), ('у́голь', 'coal')),
        (('брат', 'brother'), ('брать', 'to take')),
        (('мат', 'checkmate; swearing'), ('мать', 'mother')),
        (('вес', 'weight'), ('весь', 'all, the whole')),
        (('ест', 'eats'), ('есть', 'to eat; there is')),
        (('цел', 'intact (short form)'), ('цель', 'goal')),
        (('стал', 'became'), ('сталь', 'steel')),
        (('пыл', 'ardour'), ('пыль', 'dust')),
        (('шест', 'pole'), ('шесть', 'six')),
        (('кров', 'shelter, roof'), ('кровь', 'blood')),
        (('вон', 'over there'), ('вонь', 'stench')),
        (('ел', 'ate'), ('ель', 'fir tree')),
        (('мол', 'breakwater, pier'), ('моль', 'moth')),
        (('по́лка', 'shelf'), ('по́лька', 'Polish woman; polka')),
        (('га́лка', 'jackdaw'), ('га́лька', 'pebbles')),
    ]),
    ('Hard vs soft', 'hard or soft?', [
        (('быть', 'to be'), ('бить', 'to beat')),
        (('был', 'was'), ('бил', 'beat (past)')),
        (('мы́ло', 'soap'), ('ми́ло', 'nicely, sweetly')),
        (('мыл', 'washed'), ('мил', 'dear, sweet (short form)')),
        (('лук', 'onion'), ('люк', 'hatch, manhole')),
        (('рад', 'glad'), ('ряд', 'row')),
        (('нос', 'nose'), ('нёс', 'carried')),
        (('мал', 'small (short form)'), ('мял', 'crumpled')),
        (('вол', 'ox'), ('вёл', 'led')),
        (('ток', 'current'), ('тёк', 'flowed')),
    ]),
]

CSS = """.card { font-family: arial; font-size: 24px; text-align: center; color: black; background-color: white; }
.nightMode .card, .card.nightMode { color: #eee; background-color: #2f2f31; }
.label { font-size: 0.8em; color: #888; margin-bottom: 1em; }
.word { font-size: 1.6em; margin: 0.4em 0; }
.gloss { font-size: 0.8em; color: #666; }
.nightMode .gloss { color: #aaa; }
.partner { margin-top: 1.5em; font-size: 0.9em; }
.partner .pg { color: #888; font-size: 0.85em; }
"""
FRONT = '<div class="label">{{Label}}</div>\n{{Audio}}'
BACK = ('{{FrontSide}}\n<hr id=answer>\n<div class="word">{{Word}}</div>\n<div class="gloss">{{Gloss}}</div>\n'
        '<div class="partner">vs {{Partner}} <span class="pg">{{Partner gloss}}</span><br>{{Partner audio}}</div>')
FIELDS = ['Word', 'Gloss', 'Label', 'Audio', 'Partner', 'Partner gloss', 'Partner audio']


def ensure_model():
    if MODEL in a.call('modelNames'):
        return
    a.call('createModel', modelName=MODEL, inOrderFields=FIELDS, css=CSS,
           cardTemplates=[{'Name': 'Listen', 'Front': FRONT, 'Back': BACK}])


def ensure_decks():
    shared = a.call('getDeckConfig', deck='Vocab::10000 words')
    assert shared['name'] == 'Shared', shared['name']
    decks = [ROOT] + [f'{ROOT}::{name}' for name, _, _ in SETS]
    for d in decks:
        a.call('createDeck', deck=d)
    a.call('setDeckConfigId', decks=decks, configId=shared['id'])
    a.call('setDeckNewLimit', deck=ROOT, newLimit=9999)


def main():
    ensure_model()
    ensure_decks()
    made = {}
    for name, label, pairs in SETS:
        deck = f'{ROOT}::{name}'
        for pair in pairs:
            for (w, g), (pw, pg) in (pair, pair[::-1]):
                if a.call('findNotes', query=f'"note:{MODEL}" "Word:{w}"'):
                    continue
                nid = a.call('addNote', note={
                    'deckName': deck, 'modelName': MODEL, 'tags': TAGS,
                    'fields': {'Word': w, 'Gloss': g, 'Label': label, 'Audio': w,
                               'Partner': pw, 'Partner gloss': pg},
                    'options': {'allowDuplicate': False}})
                made[w] = nid
    print(f'added {len(made)} notes')
    ids = list(made.values())
    for i in range(0, len(ids), 10):
        print(a.call('generateBasicAudio', noteIds=ids[i:i + 10], field='Audio'))
    # Audio holds "word<br><br> [sound:x]" now: cut it to the tag, then copy it to the partner.
    nids = a.call('findNotes', query=f'"note:{MODEL}"')
    notes = a.call('notesInfo', notes=nids)
    tag = {}
    for n in notes:
        m = re.search(r'\[sound:[^\]]+\]', n['fields']['Audio']['value'])
        assert m, n['fields']['Word']['value']
        tag[n['fields']['Word']['value']] = m.group(0)
    for n in notes:
        f = n['fields']
        a.call('updateNoteFields', note={'id': n['noteId'], 'fields': {
            'Audio': tag[f['Word']['value']], 'Partner audio': tag[f['Partner']['value']]}})
    print(f'{len(notes)} notes have audio')


if __name__ == '__main__':
    main()
