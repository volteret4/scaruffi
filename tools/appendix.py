#!/usr/bin/env python3
"""Apéndices del libro (texto de pdftotext -layout) -> JSON.

Uso: python3 -I tools/appendix.py <book.txt> <salida.json>

- «Best albums» de los 60 y 70: agrupados por nota (9/10, 8.5/10…).
- «Best albums» de los 80 y 90: ranking numerado.
- «The greatest (bands) of the …»: ranking de artistas.
"""
import json
import re
import sys

lines = open(sys.argv[1]).read().splitlines()
SKIP = re.compile(r'History Of Rock Music|^\s*\d{1,3}\s*$|^\s*$')
HEAD = re.compile(r'^\s*(\d\.\d+)\s+(.*?)\s*$')
sections, cur = {}, None
for l in lines[120:]:  # tras el índice
    m = HEAD.match(l)
    if m and ('Appendix' in m.group(2) or 'Best' in m.group(2) or 'greatest' in m.group(2).lower()):
        cur = m.group(1)
        sections[cur] = {'title': m.group(2), 'lines': []}
        continue
    if m and cur and not l.startswith(' '):
        cur = None
    if re.match(r'^\s*\d\s+\S', l) and cur and not re.match(r'^\s*\d+\.\s', l):
        cur = None
    if cur and not SKIP.search(l):
        sections[cur]['lines'].append(l.strip(' •\t'))

DECADE = {'2.8': 1960, '2.9': 1960, '4.9': 1970, '4.10': 1970, '5.25': 1980, '5.26': 1980, '6.23': 1990, '6.24': 1990}
ALBUM = re.compile(r'^(?:(\d+)\.\s+)?(.+?)(?::\s+(.+?))?\s*(?:\(([^()]*?)\))?\s*$')
albums, greatest = [], {}
for num, sec in sections.items():
    dec = DECADE.get(num)
    if 'greatest' in sec['title'].lower():
        names = []
        for l in sec['lines']:
            m = re.match(r'^(\d+)\.\s*(.*)$', l)
            n = (m.group(2) if m else l).strip()
            if n:
                names.append(n)
        greatest[dec] = names
        continue
    rating = None
    for l in sec['lines']:
        m = re.match(r'^(\d+(?:\.5)?)/10$', l)
        if m:
            rating = float(m.group(1)); continue
        m = ALBUM.match(l)
        if not m:
            continue
        rank, artist, title, paren = m.groups()
        if title is None:  # «Doors (Elektra, 1967)», «Velvet Underground & Nico (Verve, 1967)»
            artist, title = artist, artist
        label, year = None, None
        if paren:
            pm = re.match(r'^(?:(.*?),\s*)?((?:19|20)\d\d)$', paren.strip())
            if pm:
                label, year = pm.group(1), int(pm.group(2))
            else:
                label = paren.strip()
        if title.lower() in ('self-titled', 'self titled'):
            title = artist
        albums.append({'decade': dec, 'a': artist.strip(), 't': title.strip(), 'label': label, 'y': year,
                       'rating': rating, 'rank': int(rank) if rank else None})
json.dump({'albums': albums, 'greatest': greatest}, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
for d in (1960, 1970, 1980, 1990):
    print(d, sum(1 for a in albums if a['decade'] == d), 'discos;', len(greatest.get(d, [])), 'artistas')
