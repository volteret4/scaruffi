#!/usr/bin/env python3
"""Genera data/*.js a partir de la extracción del PDF, la curación y los apéndices.

Uso: python3 -I tools/build_data.py <sections.json> <appendix.json>

- <sections.json>: salida de tools/extract.py (títulos con su índice #n).
- tools/curado.txt: géneros, resúmenes, influencias y correcciones (ver su cabecera).
- <appendix.json>: salida de tools/appendix.py (mejores discos y grupos por década).

Escribe data/books.js (partes y secciones), data/NN-<sección>.js (un fichero
por sección con sus géneros y discos), data/best.js (apéndices) y
build/tracks.json (lista única de discos/canciones para tools/yt.py).
Con --dudosas lista las atribuciones heurísticas a nombres ambiguos (Love, Can, Who…)
para revisarlas en la curación.
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {'1', '2.8', '2.9', '4.9', '4.10', '5.25', '5.26', '6.23', '6.24', '8'}
# Cabecera «Body Music» copiada por error en el libro al principio de estas secciones.
BOGUS_SUB = {('6.17', 'Body Music'), ('6.18', 'Body Music'), ('6.19', 'Body Music'), ('6.20', 'Body Music')}
META = ('id', 'name', 'fam', 'years', 'place', 'from', 'desc')
FAMS = {'raices', 'folk', 'psico', 'prog', 'hard', 'punk', 'pop', 'dark', 'negra', 'vanguardia'}
# Nombres de grupo que coinciden con palabras corrientes: la heurística los confunde con frecuencia.
SUSPECT = {'Love', 'Can', 'Band', 'Who', 'Rain', 'Green', 'Sky', 'Story', 'Fear', 'Air', 'Kansas', 'Death',
           'God', 'Trance', 'Sound', 'Come', 'Will', 'Family', 'Medicine', 'Rush', 'Roses', 'Queen', 'Kill',
           'Scream', 'Orchestra', 'Saint', 'Ice', 'Bag', 'Mountain', 'Truth', 'Tomorrow', 'Keith', 'Cooper',
           'Smith', 'Riley', 'Wire', 'Japan', 'Berlin', 'Productions', 'Gate', 'Bright', 'Fudge', 'Low',
           'Further', 'Estate', 'Maria', 'Mac', 'Bowie', 'Hopper', 'Almond', 'Kiss', 'Box', 'Ride', 'Cracker',
           'Run On', 'Surgery', 'Roots', 'Criminals', 'Lid', 'Paradise', 'Tool', 'Saints', 'Seeds', 'Church'}


def norm(s):
    s = unicodedata.normalize('NFKD', s.replace('’', "'")).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'^the\s+', '', s.strip())
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


# Nombres de grupo que llevan genitivo de verdad (no «Chicago's Green» ni «Jad Fair's Half Japanese»).
POSSESSIVE_NAMES = {"Devils' Anvil", "Tonto's Expanding Head Band", "It's A Beautiful Day", "Shiva's Headband",
                    "Jane's Addiction", "Pandora's Box", "Jacob's Mouse", "Eric's Trip", "Satan's Pilgrims",
                    "Victim's Family", "Zuzu's Petals"}


def clean_artist(a):
    """Limpia restos típicos de la heurística: «San Diego's Trumans Water», «y Nick Cave», «1965. Paul Anka»."""
    if not a:
        return a
    a = re.sub(r'\s+', ' ', a).strip(' ,;:')
    if a.endswith('.') and not re.search(r'(?:^|\s)(?:[A-Z]\.)+$', a):
        a = a[:-1]
    if a in POSSESSIVE_NAMES:
        return a
    a = re.sub(r'^(?:(?:y|le|ly|der|of|and|by|from|with|the)\s+)+', '', a)
    a = re.sub(r'^.*\d{4}\.?\s+', '', a)
    a = re.sub(r'^[^.]*\.\s+(?=[A-Z])', '', a) if '. ' in a and not re.match(r'^[A-Z]\.', a) else a
    m = re.match(r"^.+?(?:'s|s')\s+(.+)$", a)
    if m:
        a = m.group(1)
    a = re.sub(r'^(?:The|the)\s+', '', a)
    return a.strip()


def parse_curado(path):
    blocks, cur, in_fix = [], None, False
    for raw in open(path):
        line = raw.rstrip('\n')
        if not line.strip() or line.startswith('#'):
            continue
        m = re.match(r'^== (\S+)(?: \| (.+))?$', line)
        if m:
            cur = {'num': m.group(1), 'sub': m.group(2), 'fix': []}
            blocks.append(cur)
            in_fix = False
            continue
        if line == 'fix:':
            in_fix = True
            continue
        if in_fix:
            m = re.match(r'^(\d+)(?:-(\d+))?\s+(.*)$', line)
            if not m:
                sys.exit(f'Corrección ilegible en {cur["num"]}: {line}')
            a, b, rest = int(m.group(1)), int(m.group(2) or m.group(1)), m.group(3).strip()
            fx = {'drop': rest == 'x'}
            if not fx['drop']:
                tm = re.search(r'\s*=(.+)$', rest)
                if tm:
                    fx['t'] = tm.group(1).strip()
                    rest = rest[:tm.start()]
                ym = re.search(r'\s*@(\d{4})$', rest)
                if ym:
                    fx['y'] = int(ym.group(1))
                    rest = rest[:ym.start()]
                fx['a'] = rest.strip()
            for i in range(a, b + 1):
                cur['fix'].append((i, fx))
            continue
        m = re.match(r'^(\w+):\s*(.*)$', line)
        if not m or m.group(1) not in META:
            sys.exit(f'Línea desconocida en {cur["num"]}: {line}')
        cur[m.group(1)] = m.group(2)
    return blocks


def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def main(sections_file, appendix_file, *flags):
    data = json.load(open(sections_file))
    sections = {s['num']: s for s in data['sections']}
    for s in data['sections']:
        s['subs'] = [x for x in s['subs'] if (s['num'], x['name']) not in BOGUS_SUB]
        for x in s['items'] + s['rated']:
            if (s['num'], x['sub']) in BOGUS_SUB:
                x['sub'] = None
    blocks = parse_curado(ROOT / 'tools' / 'curado.txt')

    genres, order = {}, []
    by_sec = defaultdict(dict)          # num -> {sub|None: genre id}
    fixes = defaultdict(dict)           # num -> {índice: corrección}
    for b in blocks:
        if b['num'] not in sections:
            sys.exit(f'Sección inexistente en la curación: {b["num"]}')
        if b['sub'] and b['sub'] not in [x['name'] for x in sections[b['num']]['subs']]:
            sys.exit(f'Subapartado inexistente en {b["num"]}: {b["sub"]!r}')
        gid = b.get('id')
        if not gid:
            sys.exit(f'Bloque sin id en {b["num"]} {b["sub"] or ""}')
        g = genres.get(gid)
        if g is None:
            if 'name' not in b:
                sys.exit(f'Género nuevo sin nombre: {gid}')
            g = genres[gid] = {'id': gid, 'tracks': [], 'artists': [], 'secs': []}
            order.append(gid)
        for k in ('name', 'fam', 'place', 'desc'):
            if k in b:
                g['family' if k == 'fam' else k] = b[k]
        if 'years' in b:
            g['start'], g['end'] = map(int, b['years'].split('-'))
        if 'from' in b:
            g['influences'] = [x.strip() for x in b['from'].split(',') if x.strip()]
        by_sec[b['num']][b['sub']] = gid
        for i, fx in b['fix']:
            fixes[b['num']][i] = fx

    # Discos y artistas valorados de cada sección, repartidos por género según su subapartado.
    suspects, tracks_all = [], {}
    for num, sec in sections.items():
        if num in SKIP:
            continue
        if None not in by_sec[num]:
            sys.exit(f'La sección {num} no tiene bloque principal en la curación')
        gid_of = lambda sub: by_sec[num].get(sub) or by_sec[num][None]
        for i, it in enumerate(sec['items']):
            fx = fixes[num].get(i, {})
            if fx.get('drop'):
                continue
            a = fx.get('a') or clean_artist(it['a'])
            t = re.sub(r'\s+', ' ', fx.get('t') or it['t']).strip(' ,;:')
            y = fx.get('y') or it['y']
            if not a or not t:
                print(f'SIN ARTISTA {num}#{i}: {t}')
                continue
            if not fx and (a in SUSPECT or it['how'] == 'near' and len(a.split()) == 1 and a in SUSPECT):
                suspects.append(f'{num}#{i} [{a}] {t}')
            g = genres[gid_of(it['sub'])]
            tr = {'a': a, 't': t, 'k': 'a' if it['k'] == 'album' else 's', 'p': it['p'], 's': num}
            if y:
                tr['y'] = y
            if it['sub']:
                tr['sub'] = it['sub']
            key = norm(a) + '|' + norm(t)
            if any(norm(x['a']) + '|' + norm(x['t']) == key for x in g['tracks']):
                continue
            g['tracks'].append(tr)
            if num not in g['secs']:
                g['secs'].append(num)
            tracks_all.setdefault(f'{a}|{t}', {'a': a, 't': t, 'k': tr['k']})
        for r in sec['rated']:
            g = genres[gid_of(r['sub'])]
            name = clean_artist(r['a'])
            if name and not any(norm(x['a']) == norm(name) for x in g['artists']):
                g['artists'].append({'a': name, 'r': r['r']})
        for sub in [None] + [x['name'] for x in sec['subs']]:
            gid = gid_of(sub)
            if num not in genres[gid]['secs']:
                genres[gid]['secs'].append(num)

    for g in genres.values():
        for k in ('name', 'family', 'start', 'desc'):
            if k not in g:
                sys.exit(f'Al género {g["id"]} le falta {k}')
        if g['family'] not in FAMS:
            sys.exit(f'Familia desconocida en {g["id"]}: {g["family"]}')
        for p in g.get('influences', []):
            if p not in genres:
                sys.exit(f'Influencia desconocida en {g["id"]}: {p}')

    # Apéndices: se enlazan con los discos ya citados (mismo artista y título) o con el género del artista.
    app = json.load(open(appendix_file))
    index = {}
    for g in genres.values():
        for tr in g['tracks']:
            index.setdefault(norm(tr['a']) + '|' + norm(tr['t']), (g['id'], tr))
            index.setdefault('*|' + norm(tr['t']) + '|' + (norm(tr['a'])[:6]), (g['id'], tr))
    artist_genre = defaultdict(Counter)
    for g in genres.values():
        for tr in g['tracks']:
            artist_genre[norm(tr['a'])][g['id']] += 1
        for ar in g['artists']:
            artist_genre[norm(ar['a'])][g['id']] += 2
    best, unmatched = [], 0
    for b in app['albums']:
        a, t = b['a'], b['t']
        if a == t and ' & ' in a:          # «Velvet Underground & Nico (Verve, 1967)»
            a = a.split(' & ')[0]
        hit = index.get(norm(a) + '|' + norm(t)) or index.get('*|' + norm(t) + '|' + norm(a)[:6])
        item = {'a': a, 't': t, 'd': b['decade']}
        if b['y']:
            item['y'] = b['y']
        if b['rating'] is not None:
            item['r'] = b['rating']
        if b['rank'] is not None:
            item['n'] = b['rank']
        if hit:
            gid, tr = hit
            item['a'], item['t'], item['g'] = tr['a'], tr['t'], gid
            tr['best'] = {k: item[k] for k in ('d', 'r', 'n') if k in item}
            if 'y' not in tr and 'y' in item:
                tr['y'] = item['y']
        else:
            unmatched += 1
            cands = artist_genre.get(norm(a))
            if cands:
                item['g'] = cands.most_common(1)[0][0]
        tracks_all.setdefault(f'{item["a"]}|{item["t"]}', {'a': item['a'], 't': item['t'], 'k': 'a'})
        best.append(item)

    # Salida.
    out = ROOT / 'data'
    out.mkdir(exist_ok=True)
    for f in out.glob('[0-9][0-9]-*.js'):
        f.unlink()
    parts = [{'n': p['num'], 'title': p['title']} for p in data['parts']]
    secs = [{'n': s['num'], 'title': re.sub(r'\s+', ' ', s['title']), 'p': s['page'],
             'subs': [{'name': x['name'], 'p': x['page']} for x in s['subs']]}
            for s in data['sections'] if s['num'] not in SKIP]
    (out / 'books.js').write_text('// Generado por tools/build_data.py — no editar a mano.\n'
                                  f'ROCK.book({js({"parts": parts, "sections": secs})});\n')
    written = set()
    for i, s in enumerate(secs):
        gids = []
        for gid in order:
            if s['n'] in genres[gid]['secs'] and gid not in written:
                gids.append(gid)
                written.add(gid)
        body = ',\n'.join(js({k: v for k, v in genres[g].items() if k != 'secs'} | {'secs': genres[g]['secs']}) for g in gids)
        slug = s['n'].replace('.', '_')
        (out / f'{i + 1:02d}-{slug}.js').write_text(
            f'// Sección {s["n"]} · {s["title"]} — generado por tools/build_data.py.\nROCK.add([\n{body}\n]);\n')
    (out / 'best.js').write_text('// Generado por tools/build_data.py — no editar a mano.\n'
                                 f'ROCK.best({js({"albums": best, "greatest": app["greatest"]})});\n')
    (ROOT / 'build').mkdir(exist_ok=True)
    (ROOT / 'build' / 'tracks.json').write_text(json.dumps(list(tracks_all.values()), ensure_ascii=False, indent=0))

    n = sum(len(g['tracks']) for g in genres.values())
    print(f'{len(genres)} géneros, {n} discos/canciones, {len(tracks_all)} únicos para YouTube')
    print(f'Apéndices: {len(best)} discos ({len(best) - unmatched} enlazados con el texto)')
    if suspects and '--dudosas' in flags:
        print(f'{len(suspects)} atribuciones dudosas:')
        for s in suspects:
            print('  DUDOSO', s)


if __name__ == '__main__':
    main(*sys.argv[1:])
