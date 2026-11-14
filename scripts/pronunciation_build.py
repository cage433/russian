#!/usr/bin/env python3
"""Build the Pronunciation deck: listening cards for sounds an English ear merges.

One note per word, note type "Pronunciation". Since 2026-11-14 (Alex) a card plays BOTH words of
a minimal pair — the note's word, then its partner — and asks which order they came in: the front
names the contrast and shows the pair alphabetically («ш or щ / шёлк / щёлк», so the layout gives
nothing away); the back replays both and lists them 1, 2 with glosses. The pair's two notes give
the two orders. (Until then a card played one word and asked which it was; comparing two is the
easier, more useful discrimination.) Words come in minimal pairs: only a partner that differs in
the target sound alone makes the card a test of hearing.

Audio is the Back preset's HyperTTS voice via the add-on's generateBasicAudio: the word is
written into Audio, recorded, then Audio is cut down to the bare [sound:] tag.
Idempotent: existing notes (by Word) are skipped. `--pair-audio` rebuilds just the joined recordings. `--rerecord` re-records every note with VOICE. Decks start paused (Shared preset, 0/day).
"""
import sys
sys.path.insert(0, 'scripts')
import anki_utils as a
a.use_venv()
import hashlib
import os
import re
import subprocess
import tempfile

ROOT = 'Pronunciation'
# One speaker for every recording (Alex, 2026-11-02): the Back preset picks one of four voices at
# random, and a change of speaker between шест and шесть swamps the difference being trained.
VOICE = 'ru-RU-Wavenet-D'
MODEL = 'Pronunciation'
TAGS = ['claude', 'pronunciation']

SETS = [
    ('ш vs щ', 'ш or щ', [
        (('ча́ша', 'cup, bowl'), ('ча́ща', 'thicket')),
        (('шит', 'sewn'), ('щит', 'shield')),
        (('шёлк', 'silk'), ('щёлк', 'click!')),
        (('пишу́', 'I write'), ('пищу́', 'I squeak')),
        (('шиплю́', 'I hiss'), ('щиплю́', 'I pinch')),
    ]),
    ('Final ь', 'with or without ь', [
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
    ('Hard vs soft', 'hard or soft', [
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
.ask { font-size: 0.7em; color: #888; margin-bottom: 0.8em; }
.order { margin: 0.3em 0; }
.order .word { font-size: 1.3em; }
.pair { display: inline-block; margin-top: 0.4em; font-size: 1.4em; color: black; }
.nightMode .pair { color: #eee; }
"""
# One play button for both words (Alex, 2026-11-14): Pair audio is the word's recording, a gap,
# then the partner's, joined by ffmpeg (see pair_audio) — the recordings themselves are unchanged.
FRONT = '<div class="label">{{Label}}</div>\n<div class="ask">which order?</div>\n{{Pair audio}}'
GAP = 0.3   # seconds of silence between the two words (0.6 was too long, Alex 2026-11-14)
# The back replays both (they are in FrontSide) and spells out the order.
BACK = ('{{FrontSide}}\n<hr id=answer>\n'
        '<div class="order">1. <span class="word">{{Word}}</span> <span class="gloss">{{Gloss}}</span></div>\n'
        '<div class="order">2. <span class="word">{{Partner}}</span> <span class="gloss">{{Partner gloss}}</span></div>')
FIELDS = ['Word', 'Gloss', 'Label', 'Audio', 'Partner', 'Partner gloss', 'Partner audio', 'Pair audio']


def ensure_model():
    if MODEL in a.call('modelNames'):
        if 'Pair audio' not in a.call('modelFieldNames', modelName=MODEL):
            a.call('modelFieldAdd', modelName=MODEL, fieldName='Pair audio', index=len(FIELDS) - 1)
        # keep the templates in step with this file (the model predates the two-sound format)
        a.call('updateModelTemplates', model={'name': MODEL, 'templates': {'Listen': {'Front': FRONT, 'Back': BACK}}})
        a.call('updateModelStyling', model={'name': MODEL, 'css': CSS})
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
    if '--pair-audio' in sys.argv:          # rebuild only the joined recordings (+ templates)
        ensure_model()
        pair_audio()
        return
    if '--rerecord' in sys.argv:            # re-record every note with VOICE
        # an add-on loaded before `voice` existed would fail after Audio was blanked to the word
        assert not a.call('addonInfo')['stale'], 'restart Anki: the add-on changed since it loaded'
        nids = a.call('findNotes', query=f'"note:{MODEL}"')
        for n in a.call('notesInfo', notes=nids):
            a.call('updateNoteFields', note={'id': n['noteId'], 'fields': {'Audio': n['fields']['Word']['value']}})
        record(nids)
        return
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
                    'fields': {'Word': w, 'Gloss': g, 'Audio': w,
                               # both words, in a fixed order, so the front names the contrast
                               # without the position of the answer giving it away
                               'Label': '%s<br><span class="pair">%s</span>' % (
                                   label, ' / '.join(sorted([w, pw], key=a.destress))),
                               'Partner': pw, 'Partner gloss': pg},
                    'options': {'allowDuplicate': False}})
                made[w] = nid
    print(f'added {len(made)} notes')
    record(list(made.values()))


def record(ids):
    for i in range(0, len(ids), 10):
        print(a.call('generateBasicAudio', noteIds=ids[i:i + 10], field='Audio', voice=VOICE))
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
    pair_audio()


def pair_audio():
    """Pair audio = Audio + GAP of silence + Partner audio, as one mp3 stored in Anki's media
    (so it syncs). Named from the two source files and GAP, so a re-run only rebuilds what changed."""
    media = a.call('getMediaDirPath')
    nids = a.call('findNotes', query=f'"note:{MODEL}"')
    done = 0
    for n in a.call('notesInfo', notes=nids):
        f = n['fields']
        srcs = [re.search(r'\[sound:([^\]]+)\]', f[k]['value']).group(1) for k in ('Audio', 'Partner audio')]
        name = 'pron-pair-' + hashlib.sha1('|'.join(srcs + [str(GAP)]).encode()).hexdigest()[:16] + '.mp3'
        if f['Pair audio']['value'] == f'[sound:{name}]':
            continue
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, name)
            subprocess.run(['ffmpeg', '-v', 'error', '-y',
                            '-i', os.path.join(media, srcs[0]),
                            '-f', 'lavfi', '-t', str(GAP), '-i', 'anullsrc=r=24000:cl=mono',
                            '-i', os.path.join(media, srcs[1]),
                            '-filter_complex', '[0:a]aformat=sample_rates=24000:channel_layouts=mono[a];'
                            '[2:a]aformat=sample_rates=24000:channel_layouts=mono[b];'
                            '[a][1:a][b]concat=n=3:v=0:a=1', '-c:a', 'libmp3lame', '-q:a', '4', out],
                           check=True)
            a.call('storeMediaFile', filename=name, path=out)
        a.call('updateNoteFields', note={'id': n['noteId'], 'fields': {'Pair audio': f'[sound:{name}]'}})
        done += 1
    print(f'pair audio: {done} built')


if __name__ == '__main__':
    main()
