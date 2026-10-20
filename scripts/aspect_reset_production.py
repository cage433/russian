#!/usr/bin/env python3
"""Reset the Cloze Aspect production cards (impf / pf, card 1 and 2) to new — 2026-10-20.

Their history came from the old English → Russian Basic cards, which never asked for the
forms, so it measured the wrong thing (Alex's call). Card 3 (Russian → English, 95% pass) keeps
its history. Each deck's reset cards go just in front of its existing new queue — never below
position 2, so the promote leak guard is not tripped — best-known words first (card 3's interval),
impf before pf. Suspended cards stay suspended.

  ./scripts/aspect_reset_production.py --dry-run
  ./scripts/aspect_reset_production.py
"""
import sys, json, time, argparse
sys.path.insert(0, 'scripts')
import anki_utils as a
a.use_venv()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--resume', help='backup JSON of a run whose forget succeeded but positions failed')
    args = ap.parse_args()
    if args.resume:
        cards = json.load(open(args.resume)); cids = [c['cardId'] for c in cards]
    else:
        cids = a.call('findCards', query='"note:Cloze Aspect" -is:new (card:1 OR card:2)')
        cards = []
        for i in range(0, len(cids), 500): cards += a.call('cardsInfo', cards=cids[i:i + 500])
    c3 = {}
    c3ids = a.call('findCards', query='"note:Cloze Aspect" card:3')
    for i in range(0, len(c3ids), 500):
        for c in a.call('cardsInfo', cards=c3ids[i:i + 500]): c3[c['note']] = c['interval']
    by_deck = {}
    for c in cards: by_deck.setdefault(c['deckName'], []).append(c)
    for d, cs in sorted(by_deck.items()): print(f'{d}: {len(cs)}')
    print('total', len(cards))
    if args.dry_run: return
    if args.resume:
        return place(cards, cids, by_deck, c3)
    keep = ['cardId', 'note', 'ord', 'deckName', 'type', 'queue', 'due', 'interval', 'factor', 'reps', 'lapses', 'left']
    path = f"tutoring/retired/aspect-production-reset-{time.strftime('%Y%m%d-%H%M%S')}.json"
    json.dump([{k: c.get(k) for k in keep} for c in cards], open(path, 'w'), ensure_ascii=False, indent=0)
    print('backup', path)
    a.call('forgetCards', cards=cids)
    place(cards, cids, by_deck, c3)

def place(cards, cids, by_deck, c3):
    mine = set(cids)
    for deck, cs in by_deck.items():
        others = [c['due'] for c in a.call('cardsInfo', cards=a.call('findCards', query=f'"deck:{deck}" -deck:"{deck}::*" is:new'))
                  if c['cardId'] not in mine]
        cs.sort(key=lambda c: (-c3.get(c['note'], 0), c['note'], c['ord']))
        cs.sort(key=lambda c: c['ord'])  # stable: all impf first, then pf, each best-known first
        pos = max(2, (min(others) if others else 2) - len(cs))
        a.set_new_positions([(c['cardId'], pos + i) for i, c in enumerate(cs)])
        for c in cs:
            r = a.call('setSpecificValueOfCard', card=c['cardId'], keys=['reps', 'lapses'],
                       newValues=[0, 0], warning_check=True)
            assert r in (True, [True]), r
        print(f'{deck}: {len(cs)} cards from position {pos}')
    if any(c['queue'] == -1 for c in cards):
        a.call('suspend', cards=[c['cardId'] for c in cards if c['queue'] == -1])

if __name__ == '__main__':
    main()
