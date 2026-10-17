#!/usr/bin/env python3
"""Texto anotado de una sección para revisar atribuciones: «canción»#n[artista] / **álbum**#n[artista].

Uso: python3 -I tools/review.py build/sections.json [3.1 3.2 …]
"""
import json, re, sys
d = json.load(open(sys.argv[1]))
for sec in d['sections']:
    if sys.argv[2:] and sec['num'] not in sys.argv[2:]:
        continue
    out = [f"### {sec['num']} {sec['title']} (p{sec['page']})\n"]
    last = None
    for b in sec['body']:
        if 'h' in b:
            out.append(f"\n## {b['h']}\n")
        elif 'r' in b:
            out.append(b['r'])
        else:
            it = sec['items'][b['i']]
            a = it['a'] or '?'
            mark = f"«{it['t']}»" if it['k'] == 'song' else f"**{it['t']}**"
            out.append(f"{mark}#{b['i']}[{a}]")
    txt = re.sub(r' {4,}', '\n', ''.join(out))
    txt = re.sub(r'(?m)^\s*(?:19|20)\d\d: .*$\n?', '', txt)
    txt = re.sub(r'[ \t]+', ' ', txt)
    txt = re.sub(r'\n\s*\n+', '\n', txt)
    print(txt)
