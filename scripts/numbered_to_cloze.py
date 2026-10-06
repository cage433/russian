"""Convert a numbered near-synonym Basic note to the Cloze form (see CLAUDE.md, Merge conventions).

build(note) -> (Text, Back Extra). Strips Cyrillic / accented-transliteration parentheticals from
the sense glosses so a visible row cannot give away a hidden answer. Running the module dry-runs
a few awkward notes; the 2026-10-06 bulk conversion was driven from a one-off script around it."""
import sys,re,json,time,html; sys.path.insert(0,'scripts'); import anki_utils as a
SND=r'\[sound:[^\]]*\]'
TD='<td style="padding: 2px 10px; vertical-align: top;">'
def lines(h):
    h=re.sub(SND,'',h); h=re.sub(r'<br\s*/?>','\n',h,flags=re.I); h=re.sub(r'</?div>','\n',h)
    return [l.strip() for l in h.split('\n')]
def parse(n):
    F=lines(n['fields']['Front']['value']); B=lines(n['fields']['Back']['value'])
    fs={};head=[];extra=[]
    for l in F:
        m=re.match(r'^(\d+):\s*(.*)$',l)
        if m: fs[int(m.group(1))]=m.group(2)
        elif l and not fs: head.append(l)
        elif l: extra.append(l)
    bs={};bextra=[]
    for l in B:
        for m in re.finditer(r'(\d+):\s*(.*?)(?=\s+\d+:\s|$)',l): bs[int(m.group(1))]=m.group(2).strip()
        if l and not re.match(r'^\d+:',l): bextra.append(l)
    return head,fs,bs,extra,bextra
CYR=re.compile(r'[а-яёА-ЯЁ]'); TRANSLIT=re.compile(r'[a-z]*[áéíóúý][a-z]*',re.I)
def clean_gloss(g,own):
    g=re.sub(r'\(([^()]*)\)',lambda m: '' if CYR.search(m.group(1)) or TRANSLIT.fullmatch(m.group(1).strip()) else m.group(0),g)
    for w in own: g=re.sub(re.escape(w),'…',g,flags=re.I)
    return re.sub(r'\s{2,}',' ',g).strip().rstrip(',;')
def build(n):
    head,fs,bs,extra,bextra=parse(n)
    own={a.destress(re.sub(r'<[^>]+>','',w)).lower() for v in bs.values() for w in re.findall(r'[а-яёА-ЯЁ́-]{3,}',v)}
    own|={w for v in bs.values() for w in re.findall(r'[а-яёА-ЯЁ́-]{3,}',v)}
    hdr=[h for h in head]+[e for e in extra if not any(w in a.destress(e).lower() for w in own)]
    rows=''.join(f'<tr>{TD}{i}:</td>{TD}<i>{clean_gloss(fs[i],own)}</i></td>{TD}{{{{c{i}::{bs[i]}}}}}</td></tr>' for i in sorted(fs))
    text=('<b>'+'<br>'.join(hdr)+'</b><br><br>' if hdr else '')+f'<table style="margin: 0 auto; text-align: left; border-collapse: collapse;">{rows}</table>'
    return text, n['fields']['Example']['value']
if __name__=='__main__':
    ids=[1726634607470,1726634607180,1726634610257,1726634612609,1726634604239]
    for n in a.call('notesInfo',notes=ids):
        t,e=build(n); q=re.sub(r'</tr>','\n',t); q=re.sub(r'<br\s*/?>','\n',q); q=re.sub(r'\{\{c\d+::(.*?)\}\}',r'[\1]',q); q=re.sub(r'<[^>]+>',' ',q)
        print('---',n['noteId']); print(re.sub(r'[ \t]+',' ',html.unescape(q)).strip())
