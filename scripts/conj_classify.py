#!/usr/bin/env python3
"""Classify every Cloze Aspect conjugation row against the conjugation rules.

For each row (one infinitive with its я / ты forms) decide whether the rules in the Obsidian
note «Conjugation — from the infinitive» predict it, and produce the short rule label shown by
the card's "show rule" link. Rows the rules don't predict are *tricky*: their forms move to
`Vocab::Verb forms`, grouped under a base verb.

  ./scripts/conj_classify.py               # summary + writes scratch/conj_classify.json
  ./scripts/conj_classify.py --list FILE   # also writes a markdown review list

Forms are compared without stress; stress only feeds the label ("stress moves back in ты").
Read-only: never writes to Anki.
"""
import sys, re, json, argparse, collections
sys.path.insert(0, 'scripts')
import anki_utils as a
a.use_venv()

ACC = '́'
HUSH = 'жшчщ'
LAB = 'бпвфм'
VOW = 'аеёиоуыэюя'
PREFIXES = ('пере|при|пре|предо|пред|подо|под|разо|раз|рас|возо|воз|вос|взо|вз|вс|без|бес|со|с|ото|от|'
            'обо|об|о|на|за|вы|до|по|про|у|во|в|изо|из|ис|недо|низ|нис')
PREF_RE = re.compile(r'(?:(?:%s)ъ?){1,3}' % PREFIXES)

def ds(s): return s.replace(ACC, '')
def ne(s): return s.replace('ё', 'е')

def stress_pos(w):
    """Syllable index of the stress counted from the end (0 = last), or None."""
    if ACC not in w and 'ё' not in w: return None
    i = w.index(ACC) - 1 if ACC in w else w.index('ё')
    return sum(1 for ch in ds(w)[i + 1:] if ch in VOW)

def unrefl(w):
    w = ds(w)
    for e in ('ся', 'сь'):
        if w.endswith(e) and len(w) > 4: return w[:-2], True
    return w, False

# --- tricky bases: (base infinitive, regex on the destressed non-reflexive infinitive) -----------
# A verb whose infinitive *ends* in the base (after real prefixes) belongs to that base.
TRICKY_BASES = [
    # irregular stems
    'брать', 'звать', 'рвать', 'драть', 'врать', 'жрать', 'ждать', 'жаждать', 'ткать', 'сосать', 'орать',
    'стонать', 'лгать', 'гнать', 'спать', 'слать', 'стлать', 'взять', 'нять', 'мять', 'жать',
    'крыть', 'мыть', 'рыть', 'ныть', 'выть', 'быть', 'слыть', 'стыть', 'стрять', 'ехать', 'деть',
    'стать', 'дать', 'есть', 'бежать', 'хотеть', 'тереть', 'мереть', 'переть', 'простереть', 'петь',
    'дуть', 'обуть', 'колоть', 'бороться', 'пить', 'бить', 'лить', 'шить', 'вить', 'жить', 'брить',
    'гнить', 'шибить', 'чтить', 'реветь', 'смеяться', 'лечь', 'сесть', 'класть', 'расти', 'идти',
    'мочь', 'печь', 'влечь', 'речь', 'сечь', 'жечь', 'течь', 'беречь', 'стричь', 'честь', 'честь',
    'нести', 'вести', 'везти', 'мести', 'брести', 'цвести', 'грести', 'расти', 'лезть', 'ползти',
    'красть', 'прясть', 'упасть', 'пасть', 'клясть', 'плести', 'трясти', 'пасти', 'грызть', 'лезти',
    'прячь', 'стичь', 'пренебречь', 'начать', 'блюсти', 'ыскать', 'язать',
    # 1st-conjugation -ать with a consonant change in every person
    'писать', 'казать', 'плакать', 'искать', 'резать', 'прятать', 'махать', 'шептать', 'клеветать',
    'сыпать', 'колебать', 'дремать', 'бормотать', 'грохотать', 'хохотать', 'щекотать', 'хлопотать',
    'трепетать', 'топтать', 'трепать', 'скакать', 'пахать', 'лизать', 'мазать', 'метать', 'плескать',
    'хлестать', 'чесать', 'вязать', 'низать', 'тыкать', 'колыхать', 'слыхать', 'полоскать', 'щипать',
    'глодать', 'кликать', 'рыскать', 'свистать', 'стегать', 'ласкать', 'лепетать',
    'роптать', 'скрежетать', 'щебетать', 'шептать', 'дремать', 'сыпать', 'кропать', 'цыкать', 'пыхать',
    'брызгать', 'мурлыкать', 'хныкать',
]
# Cases the prefix strip gets wrong (stem-final letters look like a prefix + base)
NOT_BASE = {'сушить': None, 'высушить': None, 'сулить': None, 'посулить': None, 'обнажить': None,
            'изволить': None, 'уволить': None, 'одобрить': None, 'понадобить': None, 'приспособить': None,
            'ослабить': None, 'создать': 'дать'}
# imperfectives in -вать with a root е (успева́ть): regular -аю, not -ева- → -ю-
# detected by the existence of an -еть partner, falling back to this list
FALSE_EVAT = {'девать', 'зевать', 'сомневаться', 'намереваться', 'издеваться', 'подозревать', 'затевать',
              'разевать', 'запечатлевать', 'овладевать', 'заболевать', 'застревать', 'устаревать',
              'поспевать', 'успевать', 'нагревать', 'согревать', 'разогревать', 'созревать', 'запевать',
              'напевать', 'подпевать', 'преодолевать', 'одевать', 'надевать', 'раздевать', 'переодевать',
              'задевать', 'одолевать', 'сожалевать', 'обогревать', 'прозревать'}
# -ать after ж/ш/ч/щ that are 2nd conjugation: decided by the card's own ты form, not listed

def base_of(b):
    """The tricky base this (non-reflexive, destressed) infinitive belongs to, or None."""
    if b in NOT_BASE: return NOT_BASE[b]
    if b.endswith('йти') and PREF_RE.fullmatch(b[:-3]): return 'идти'
    for base in sorted(set(TRICKY_BASES), key=len, reverse=True):
        if b == base or (b.endswith(base) and PREF_RE.fullmatch(b[:-len(base)])):
            return BASE_ALIAS.get(base, base)
    return None

# bound roots that only occur after a prefix → the verb they are learned from
BASE_ALIAS = {'ыскать': 'искать', 'язать': 'вязать', 'прячь': 'запрячь', 'стичь': 'постичь',
              'лезти': 'лезть'}

def mutate2(stem):
    """2nd-conjugation я stems (one or two allowed forms) and the change's name."""
    if stem.endswith('ст'): return [stem[:-2] + 'щ'], 'ст→щ'
    c, s = stem[-1], stem[:-1]
    if c == 'с': return [s + 'ш'], 'с→ш'
    if c == 'з': return [s + 'ж'], 'з→ж'
    if c == 'т': return [s + 'ч', s + 'щ'], 'т→ч'
    if c == 'д': return [s + 'ж', s + 'жд'], 'д→ж'
    if c in LAB: return [stem + 'л'], '%s→%sл' % (c, c)
    return [stem], None

def actual(ch, ya):
    """Name the change the я form really shows (т→ч vs т→щ, д→ж vs д→жд)."""
    if ch == 'т→ч' and ya and re.search('щу$', ya): return 'т→щ'
    if ch == 'д→ж' and ya and re.search('жду$', ya): return 'д→жд'
    return ch

def end1(stem): return 'у' if stem[-1] in HUSH else 'ю'

def pred2(stem):
    ms, ch = mutate2(stem)
    ya = {m + end1(m) for m in ms}
    if ch == 'т→ч' and ms[1] + 'у' in ya: pass
    return ya, {stem + 'ишь'}, ch

def judge(inf, f1, f2):
    """-> dict(kind=rules|choice|tricky, label, base)."""
    b, refl = unrefl(inf)
    g1 = ne(unrefl(f1)[0]) if f1 else None
    g2 = ne(unrefl(f2)[0]) if f2 else None
    def fits(p1, p2):
        return (g1 is None or g1 in {ne(x) for x in p1}) and (g2 is None or g2 in {ne(x) for x in p2})
    full = b + ('ся' if refl else '')
    base = base_of(b) or base_of(full)
    stem_shift = ''
    if f1 and f2:
        s1, s2 = stress_pos(f1.split('сь')[0] if refl else f1), stress_pos(f2)
        if s1 == 0 and s2 is not None and s2 > 0 and not refl: stem_shift = ' · stress moves back in ты'
        if refl:
            s1 = stress_pos(re.sub('сь$', '', f1)); s2 = stress_pos(re.sub('ся$', '', f2))
            if s1 == 0 and s2 is not None and s2 > 0: stem_shift = ' · stress moves back in ты'

    def out(kind, label, base=None): return dict(kind=kind, label=label + stem_shift, base=base)

    if re.search('(ыв|ив)ать$', b) and fits({b[:-2] + 'ю'}, {b[:-2] + 'ешь'}):
        return out('rules', 'I · -ывать/-ивать: always -аю')
    if re.search('(дав|став|знав)ать$', b) and fits({b[:-4] + 'ю'}, {b[:-4] + 'ешь'}):
        return out('rules', 'I · да-/зна-/ста- + -вать: -ва- drops')
    if b.endswith('евать') and (b in FALSE_EVAT or fits({b[:-2] + 'ю'}, {b[:-2] + 'ешь'})):
        if fits({b[:-2] + 'ю'}, {b[:-2] + 'ешь'}):
            return out('rules', 'I · -аю: -вать after a root е (impf of an -еть verb)')
    if re.search('[ое]вать$', b):
        s = b[:-5]; v = 'у' if (b.endswith('овать') or s[-1:] in HUSH + 'ц') else 'ю'
        if fits({s + v + 'ю'}, {s + v + 'ешь'}):
            return out('rules', 'I · -ова-/-ева- → -у-/-ю-')
    if b.endswith('нуть') and fits({b[:-3] + 'у'}, {b[:-3] + 'ешь'}):
        return out('rules', 'I · -нуть: -ну, -нешь')
    if b.endswith('ить'):
        p1, p2, ch = pred2(b[:-3])
        if fits(p1, p2):
            return out('rules', 'II · ' + ('%s in я only' % actual(ch, g1) if ch else 'no consonant change'))
    if b.endswith('еть'):
        if fits({b[:-2] + 'ю'}, {b[:-2] + 'ешь'}):
            return out('choice', 'I · -еть → -ею')
        p1, p2, ch = pred2(b[:-3])
        if fits(p1, p2):
            return out('choice', 'II · -еть → -ю, -ишь' + (' · %s in я only' % actual(ch, g1) if ch else ''))
    if re.search('[аеуо]ять$', b) and b != 'стоять' and fits({b[:-2] + 'ю'}, {b[:-2] + 'ешь'}):
        return out('rules', 'I · vowel + -ять: -яю')  # ла́ять → ла́ю is caught below
    if re.search('[аеу]ять$', b) and fits({b[:-3] + 'ю'}, {b[:-3] + 'ешь'}):
        return out('rules', 'I · vowel + -ять: the я drops (се́ю, та́ю)')
    if b in ('стоять', 'бояться') or (b.endswith('стоять')) or (full.endswith('бояться')):
        stem = b[:-3] if b.endswith('стоять') else b[:-3]
        return out('choice', 'II · стоя́ть / боя́ться: -ю, -ишь')
    if re.search('[ая]ть$', b):
        s = b[:-3]
        if s and s[-1] in HUSH and b.endswith('ать'):
            if fits({s + 'у'}, {s + 'ишь'}):
                return out('choice', 'II · -ать after ж/ш/ч/щ → -у, -ишь')
            if fits({b[:-2] + 'ю'}, {b[:-2] + 'ешь'}):
                return out('choice', 'I · -ать after ж/ш/ч/щ, but -аю')
        if fits({b[:-2] + 'ю'}, {b[:-2] + 'ешь'}):
            return out('rules', 'I · -аю (the default)')
    if base:
        return out('tricky', 'like %s' % base, base)
    return out('tricky', 'not covered by the rules')

ROW = re.compile(r'(\S+) — (.+)$')

def parse_row(raw):
    row = re.sub('<[^>]+>', '', raw).strip()
    row = re.sub(r'\s*\((?:[^()]*\+[^()]*)\)\s*$', '', row)
    m = ROW.match(row)
    if not m: return None
    inf, rest = m.groups()
    if '3rd person' in rest: return dict(inf=inf, f1=None, f2=None, third=True)
    parts = [p.strip() for p in rest.split(',')]
    f1 = None if 'not used' in parts[0] else parts[0].split()[0]
    f2 = parts[1].split()[0] if len(parts) > 1 else None
    return dict(inf=inf, f1=f1, f2=f2, third=False)

def rows_of(text):
    """[(cloze number, label cell, raw row)] for each conjugation row of a Cloze Aspect Text."""
    out = []
    for tr in re.findall(r'<tr>(.*?)</tr>', text, re.S):
        cells = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
        if len(cells) < 2: continue
        m = re.search(r'\{\{c(\d)::(.*?)\}\}', cells[1], re.S)
        if m: out.append((int(m.group(1)), re.sub('<[^>]+>', '', cells[0]).strip(), m.group(2)))
    return out

def classify_collection():
    nids = a.call('findNotes', query='"note:Cloze Aspect"')
    notes = []
    for i in range(0, len(nids), 300):
        notes += a.call('notesInfo', notes=nids[i:i + 300])
    res = []
    for n in notes:
        for num, lab, raw in rows_of(n['fields']['Text']['value']):
            p = parse_row(raw)
            if not p:
                res.append(dict(note=n['noteId'], c=num, aspect=lab, row=raw, kind='tricky',
                                label='unparsed', base=None)); continue
            j = (dict(kind='rules', label='3rd person only', base=None) if p['third']
                 else judge(p['inf'], p['f1'], p['f2']))
            res.append(dict(note=n['noteId'], c=num, aspect=lab, row=raw, inf=p['inf'], **j))
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', help='write a markdown review list here')
    args = ap.parse_args()
    res = classify_collection()
    json.dump(res, open('scratch/conj_classify.json', 'w'), ensure_ascii=False, indent=1)
    by_note = collections.defaultdict(list)
    for r in res: by_note[r['note']].append(r['kind'])
    C = collections.Counter(r['kind'] for r in res)
    print('rows:', len(res), dict(C))
    N = collections.Counter('tricky' if 'tricky' in k else 'choice' if 'choice' in k else 'rules'
                            for k in by_note.values())
    print('notes:', len(by_note), dict(N))
    if args.list:
        tricky = [r for r in res if r['kind'] == 'tricky']
        fam = collections.defaultdict(list)
        for r in tricky: fam[r['base'] or '(no base)'].append(r)
        L = ['Tricky rows by base verb. Bases with no prefixed members are single verbs.', '']
        for base in sorted(fam, key=lambda k: (-len(fam[k]), k)):
            L.append('**%s** (%d): %s' % (base, len(fam[base]),
                     ', '.join(sorted({re.sub(r'\s*\(.*', '', r['row']) for r in fam[base]}))))
            L.append('')
        labs = collections.Counter(re.sub(' · stress.*', '', r['label']) for r in res if r['kind'] != 'tricky')
        L += ['', 'Rule labels on the rule-following rows:', '']
        L += ['- %s — %d' % (k, v) for k, v in labs.most_common()]
        open(args.list, 'w').write('\n'.join(L) + '\n')
        print('wrote', args.list)

if __name__ == '__main__':
    main()
