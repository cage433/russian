New cards paused on 2026-11-23 (Alex: swamped, catching up on reviews). Every deck's "This deck" new-cards/day limit was set to 0. Restore them once the backlog is down.

| Deck | New/day before the pause |
|---|---|
| Vocab::10000 words | 3 |
| Vocab::Tochka Ru::B2.1 | 5 |
| Vocab::Tochka Ru::B1.1 | 2 |
| Vocab::Tochka Ru::B1.2 | 2 |
| Vocab::Verb forms::1 Base verbs | 1 |
| Vocab::Verb forms::2 Consonant change -ать | 1 |
| Vocab::Verb forms::3 Prefixed | 1 |
| Pronunciation::Final ь | 3 |
| Pronunciation::Hard vs soft | 3 |
| Pronunciation::ш vs щ | 3 |
| Declensions::Adjectives | 1 |
| Declensions::Cardinals | 1 |
| Declensions::Nouns | 1 |
| Declensions::Pronouns::Personal | 1 |
| Declensions::Pronouns::Possessive | 1 |
| shit you need to know | 10 |

Already 0 before the pause: Vocab::Roots, Verbs::3000 Verbs::16::b. Parent decks stay at 9999 (they are the sum of their children). The full snapshot, every deck, is `tutoring/new-card-limits-before-pause.json`.

To restore all of them (or ask Claude to "restore the new-card limits"):

```
./.venv/bin/python -c "
import sys,json; sys.path.insert(0,'scripts'); import anki_utils as a
s=json.load(open('tutoring/new-card-limits-before-pause.json'))['deckNewLimit']
for d,n in s.items():
    if n not in (None,0,9999): a.call('setDeckNewLimit',deck=d,newLimit=n); print(d,n)
"
```

Promotion still works while paused: tagging words `promote` stamps a today-only limit for just those words (base rate 0).
