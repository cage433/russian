# One-off (2026-11-03): glosses whose " / " separates distinct meanings → bullet list. Candidates in
# scratch/slash_candidates.json (top-level " / ", not parallel to a Russian pair, no pf/impf marker);
# KEEP = indices judged by hand to be synonyms, adv/predicative or adj/noun pairs, aspect parallels.
import sys, re, json, time; sys.path.insert(0, 'scripts'); import anki_utils as a
KEEP = set(map(int, """0 1 3 5 9 28 33 34 38 41 42 44 46 49 50 52 53 57 62 63 66 74 85 90 100 104 105 106 108 127 141 167
175 181 189 194 196 197 201 203 204 210 217 218 220 223 225 227 233 234 242 247 250 264 267 269 277 280 283 286 289 293
295 300 302 304 306 308 313 314 315 316 317 318 322 335 344 346 347 348 357 361 362 370 376 380 381 384 388 389 392 393
395 401 402 404 405 406 408 412 417 419 425 430 434 438 448 449 461 463 468 469 471 475 481 484 485 487 497 500 505 512
518 519 520 524 525 529 533 535 540 542 543 550 553 557 561 562 563 564 566 567 569 571 572 582 583 585 588 598 599 603
606 610 618 620 623 624 627 633 636 637 640 643 644 645 646 651 656 665 666 669 670 672 673 692 693 700 703 704 707 708
712 717 718 720 722 723 727 731 739 740 743 745 748 754 756 758 768 769 781 785 787 790 793 798 801 803 806 807 817 821
830 833 836 837 843 845 847 852 853 855 859 863 865 866 868 869 872 874 881 882 902 907 916 919 921 924 928 929 930 932
934 937 939 952 954 956 957 959 960 961 962 970 977 978 979 985 986 992 1000 1002 1004 1005 1006 1007 1009 1013 1016 1018
1020 1021 1023 1024 1028 1031 1032 1033 1034 1035 1040 1045 1046 1048 1049 1054 1056 1057 1058 1059 1060 1061 1063 1064
1065 1068 1071 1074 1075 1078 1080 1087 1089 1090 1093 1101 1102 1106 1108 1110 1114 1115 1116 1118 1119 1121 1122 1124
1126""".split()))
WRAP = '<div style="display: inline-block; text-align: left;">%s</div>'
UL = '<ul style="margin: 0; padding-left: 1.2em;">%s</ul>'
TAIL = re.compile(r'(?:<br\s*/?>\s*)+(?=\()', re.I)
def top(s, sep=' / '):
    out, d, cur, i = [], 0, '', 0
    while i < len(s):
        if s.startswith(sep, i) and d == 0:
            out.append(cur); cur = ''; i += len(sep); continue
        ch = s[i]; d += ch in '(['; d -= ch in ')]'; cur += ch; i += 1
    return out + [cur]
def bul(g):
    m = TAIL.search(g)
    head, tail = (g[:m.start()], g[m.start():]) if m else (g, '')
    items = [re.sub(r'^[\s;]+|[\s;]+$', '', x.replace('&nbsp;', ' ')) for x in top(head)]
    return UL % ''.join('<li>%s</li>' % x for x in items if x), tail
cands = json.load(open('scratch/slash_candidates.json'))
todo = [(i, c) for i, c in enumerate(cands) if i not in KEEP]
log = []
for i, (nid, k, h, ru) in todo:
    n = a.call('notesInfo', notes=[nid])[0]
    if k == 'A':
        t = n['fields']['Text']['value']
        m = re.search(r'<b>\{\{c3::(.*?)\}\}</b>', t, re.S)
        ul, tail = bul(m.group(1))
        pre = t[:m.start()]
        wrapped = pre.endswith('text-align: left;">')
        new = t[:m.start()] + ('<b>{{c3::%s%s}}</b>' % (ul, tail) if wrapped else WRAP % ('<b>{{c3::%s%s}}</b>' % (ul, tail))) + t[m.end():]
        field, old = 'Text', t
    else:
        old = n['fields']['Front']['value']; ul, tail = bul(old)
        new, field = WRAP % ul + tail, 'Front'
    log.append({'noteId': nid, 'field': field, 'old': old})
    if '--dry' not in sys.argv:
        a.call('updateNoteFields', note={'id': nid, 'fields': {field: new}})
    elif len(log) < 4 or i in (311, 557 - 1, 1044):
        print(i, new[-300:])
if '--dry' not in sys.argv:
    json.dump(log, open(f"tutoring/retired/gloss-bullets-slash-{time.strftime('%Y%m%d-%H%M%S')}.json", 'w'), ensure_ascii=False, indent=0)
print(len(todo), 'converted;', len(KEEP), 'kept')
