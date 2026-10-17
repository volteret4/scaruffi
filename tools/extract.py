#!/usr/bin/env python3
"""Texto con estilos del PDF -> secciones, subapartados y títulos.

Uso: python3 -I tools/extract.py <marcado.txt> <sections.json> <libro.txt>

<marcado.txt> sale de tools/pdfmarks.py (runs [I:…] cursiva = canción, [B:…]
negrita = álbum); <libro.txt> es `pdftotext -layout` del mismo PDF (para los
nombres de los apéndices). Atribución heurística de artista: «X's [Título]»,
«[Título] by X», el último artista conocido mencionado antes o el último
«Nombre (valoración)» visto. tools/curado.txt corrige lo que falle; sus
índices (#n) dependen de este script, así que cualquier cambio en la
detección de títulos obliga a revisar la curación.
"""
import json
import re
import sys

src, out = sys.argv[1], sys.argv[2]
raw = open(src).read()

# 1) Stream de (página, tag, texto) sin cabeceras ni números de página.
tokens = []
page = 0
for line in raw.split('\n'):
    m = re.match(r'=== PAGE (\d+)', line)
    if m:
        page = int(m.group(1)); continue
    if 'History Of Rock Music(Compiled By Prodigy)' in line:
        continue
    if re.fullmatch(r'\s*\d{1,3}\s*', line):
        continue
    for m in re.finditer(r'\[([IB]):([^\]]*)\]|([^\[]+)', line):
        if m.group(3) is not None:
            tokens.append([page, 'R', m.group(3)])
        elif not m.group(2).strip():
            tokens.append([page, 'R', m.group(2)])
        else:
            tokens.append([page, m.group(1), m.group(2)])
    tokens.append([page, 'NL', '\n'])

# 2) Fusionar runs del mismo estilo separados solo por espacios/saltos.
merged = []
i = 0
while i < len(tokens):
    p, t, s = tokens[i]
    if t in 'IB':
        j = i + 1
        while j < len(tokens):
            k = j
            gap = ''
            while k < len(tokens) and (tokens[k][1] == 'NL' or (tokens[k][1] == 'R' and not tokens[k][2].strip())):
                gap += ' '; k += 1
            if k < len(tokens) and tokens[k][1] == t:
                s += gap + tokens[k][2]; j = k + 1
            else:
                break
        merged.append([p, t, re.sub(r'\s+', ' ', s)])
        i = j
    else:
        merged.append([p, t, s]); i += 1

# 3) Reconstruir líneas lógicas para detectar cabeceras.
SEC = re.compile(r'^(\d(?:\.\d+)?)\s+(.+?)\s*$')
sections = []
parts = []
cur = None
sub = None
buf = []  # tokens de la línea actual


def new_section(num, title, p):
    global cur, sub
    cur = {'num': num, 'title': title.strip(), 'page': p, 'items': [], 'subs': [], 'text': []}
    sections.append(cur)
    sub = None


def flush_line(line):
    global sub
    stripped = [x for x in line if x[1] != 'NL']
    if not stripped:
        return
    txt = ''.join(x[2] for x in stripped).strip()
    tags = {x[1] for x in stripped if x[2].strip()}
    p = stripped[0][0]
    if tags == {'B'}:
        m = SEC.match(txt)
        if m and not re.search(r'·', txt) and p > 3:
            mm = re.match(r'^(.*?)\s+(\d\.\d+)\s+(.*)$', m.group(2))
            if mm:
                parts.append({'num': m.group(1), 'title': mm.group(1)})
                new_section(mm.group(2), mm.group(3), p); return
            if '.' not in m.group(1):
                parts.append({'num': m.group(1), 'title': m.group(2)})
            new_section(m.group(1), m.group(2), p); return
    if cur is None:
        return
    if tags == {'I'} and len(txt) < 70 and not re.search(r'\(\d{4}\)', txt):
        sub = txt
        cur['subs'].append({'name': txt, 'page': p})
        cur['text'].append(('H', txt, p))
        return
    cur['text'].append(('L', stripped, p))


line = []
for tok in merged:
    if tok[1] == 'NL':
        flush_line(line); line = []
    else:
        line.append(tok)
flush_line(line)

# Tras fusionar, un run I/B puede abarcar varias líneas: ya está en una sola.
# 4) Recorrer cada sección como texto continuo con títulos.
YEAR_AFTER = re.compile(r'^\s*\((?:([^()]*?),\s*)?((?:19|20)\d\d)\)|^\s*,\s*((?:19|20)\d\d)\)')
RATED = re.compile(r"((?:[A-Z0-9][\w.'&!\-]*\.?|of|the|and|de|la|le|du|van|von|der|di|da|y|&)(?:\s+(?:[A-Z0-9][\w.'&!\-]*\.?|of|the|and|de|la|le|du|van|von|der|di|da|y|&))*)\s*\((\d{1,3})\)")
POSS = re.compile(r"((?:[A-Z0-9][\w.&!\-]*\.?)(?:\s+(?:[A-Z0-9][\w.&!\-]*\.?|of|the|and|&))*)['`’]s?\s*$")
STOP = {'The', 'His', 'Her', 'Their', 'Its', 'In', 'On', 'And', 'But', 'With', 'A', 'An'}

BY_AFTER = re.compile(r"^\s*(?:\([^()]*\))?\s*,?\s*(?:by|from|off)\s+(?:the\s+)?([A-Z][\w.&!'\-]*(?:\s+(?:[A-Z][\w.&!'\-]*|of|and|&))*)")
streams = []
known = set()
for sec in sections:
    stream = []  # (tag, text, page, sub)
    s_sub = None
    for kind, val, p in sec['text']:
        if kind == 'H':
            s_sub = val
            stream.append(('H', val, p, s_sub)); continue
        for (pp, t, s) in val:
            stream.append((t, s, pp, s_sub))
        stream.append(('R', ' ', p, s_sub))
    streams.append(stream)
    prose = ''
    for t, s, p, sb in stream:
        if t == 'R':
            for m in RATED.finditer(s):
                known.add(re.sub(r'^(?:The|the|and|of)\s+', '', m.group(1)))
        elif t in 'IB':
            pm = POSS.search(prose[-80:])
            if pm:
                w = pm.group(1).split()
                while w and w[0] in STOP:
                    w = w[1:]
                if w:
                    known.add(' '.join(w))
        prose += s
for line in open(sys.argv[3]):
    m = re.match(r'^\s*(?:\d+\.\s+)?([A-Z][^:()]{1,40}):\s', line)
    if m:
        known.add(m.group(1).strip())
known = {k for k in known if len(k) > 2 and k not in STOP and not k.isdigit()}
KNOWN = re.compile(r"(?<![\w])(?:the\s+|The\s+)?(" + '|'.join(sorted(map(re.escape, known), key=len, reverse=True)) + r")(?![\w])")

for sec, stream in zip(sections, streams):
    sec['body'] = []
    sec['rated'] = []  # artistas con su valoración «(NNN)» y el subapartado donde aparecen
    current = None
    prose = ''
    for idx, (t, s, p, sb) in enumerate(stream):
        if t == 'H':
            sec['body'].append({'h': s, 'p': p}); prose = ''; continue
        if t == 'R':
            sec['body'].append({'r': s})
            prose += s
            for m in RATED.finditer(s):
                current = re.sub(r'^(?:The|the|and|of)\s+', '', m.group(1))
                sec['rated'].append({'a': current, 'r': m.group(2), 'sub': sb, 'p': p})
            continue
        after = ''.join(x[1] for x in stream[idx + 1: idx + 4] if x[0] == 'R')
        m = YEAR_AFTER.match(after)
        year = int(m.group(2) or m.group(3)) if m else None
        label = m.group(1) if m and m.group(1) else None
        artist, how = None, None
        pm = POSS.search(prose[-80:])
        if pm:
            w = pm.group(1).split()
            while w and w[0] in STOP:
                w = w[1:]
            if w:
                artist, how = ' '.join(w), 'poss'
        if not artist:
            bm = BY_AFTER.match(after)
            if bm:
                artist, how = bm.group(1), 'by'
        if not artist:
            hits = list(KNOWN.finditer(prose[-600:]))
            if hits:
                artist, how = hits[-1].group(1), 'near'
        if not artist and current:
            artist, how = current, 'rated'
        title = s.strip().strip(',').strip()
        sec['body'].append({'i': len(sec['items'])})
        sec['items'].append({'t': title, 'k': 'song' if t == 'I' else 'album', 'y': year, 'label': label,
                             'a': artist, 'how': how, 'p': p, 'sub': sb})
        prose += ' ' + title + ' '
    del sec['text']

json.dump({'parts': parts, 'sections': sections}, open(out, 'w'), ensure_ascii=False, indent=0)
print(len(sections), 'secciones', sum(len(s['items']) for s in sections), 'títulos')
for s in sections:
    print(s['num'], s['title'], s['page'], len(s['subs']), len(s['items']))
