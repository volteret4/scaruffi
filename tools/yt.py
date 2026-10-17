#!/usr/bin/env python3
"""Busca en YouTube cada disco/canción de build/tracks.json con yt-dlp.

Uso: python3 -I tools/yt.py [--retry] [--accept]

Caché en data/yt.json (clave "artista|título" → vídeo); genera data/yt.js
para la web. Solo busca lo que no está en caché (--retry vuelve a intentar
las búsquedas fallidas; los vídeos sin relación aparente con el artista ni el
título se buscan otra vez sin «full album» y, si siguen sin encajar, se
descartan; --accept da por buenas las dudosas actuales, tras
revisarlas). Las coincidencias dudosas ya revisadas a mano se listan en
tools/yt-ok.txt; las claves de tools/yt-q.txt («artista|título<TAB>consulta»)
fuerzan otra consulta («-» = sin vídeo).
"""
import json
import re
import subprocess
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def query(a, t, kind):
    t = re.sub(r'\([^)]*\)', ' ', t)
    a = '' if a.lower().startswith('varios') else re.sub(r'\([^)]*\)', ' ', a)
    q = f'{a} {t}' + (' full album' if kind == 'a' else '')
    return re.sub(r'\s+', ' ', q).strip()


def search(q):
    if q == '-':
        return None
    # YouTube devuelve a veces 0 resultados para una consulta exacta: variantes de respaldo.
    plain = re.sub(r"[’'´`]", '', q)
    for variant in dict.fromkeys([q, plain, plain.replace(' full album', '')]):
        res = search_once(variant)
        if res:
            return res
    return None


def search_once(q):
    try:
        out = subprocess.run(
            ['yt-dlp', '--flat-playlist', '--no-warnings', '--print',
             '%(id)s\t%(title)s\t%(channel)s\t%(duration)s', f'ytsearch1:{q}'],
            capture_output=True, text=True, timeout=60).stdout.strip()
    except subprocess.TimeoutExpired:
        return None
    if not out:
        return None
    vid, title, channel, dur = (out.split('\t') + ['', '', ''])[:4]
    return {'id': vid, 'title': title, 'channel': channel, 'dur': dur}


def words(s):
    return set(re.findall(r'\w{4,}', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()))


def mismatch(key, res):
    """Ni el artista ni el título buscados aparecen en el vídeo: casi seguro que es otra cosa."""
    a, t = key.split('|', 1)
    toks = lambda s: set(re.findall(r'\w{2,}', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())) - {'the', 'and', 'of', 'de', 'la', 'el'}
    got = toks(res['title'] + ' ' + res['channel'])
    return not toks(a) & got and not toks(re.sub(r'\([^)]*\)', ' ', t)) & got


def plausible(key, res):
    """Algún término del título buscado aparece en el título o canal del vídeo, y lo mismo con el artista."""
    a, t = key.split('|', 1)
    got = words(res['title'] + ' ' + res['channel'])
    want_t = words(re.sub(r'\([^)]*\)', ' ', t))
    want_a = set() if a.lower().startswith('varios') else words(a)
    return (not want_t or bool(want_t & got)) and (not want_a or bool(want_a & got))


def main(*flags):
    cache_file = ROOT / 'data' / 'yt.json'
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    forced = {}
    qfile = ROOT / 'tools' / 'yt-q.txt'
    if qfile.exists():
        for line in qfile.read_text().splitlines():
            if '\t' in line:
                k, q = line.split('\t', 1)
                forced[k] = q.strip()
    tracks = {}
    for tr in json.loads((ROOT / 'build' / 'tracks.json').read_text()):
        k = f'{tr["a"]}|{tr["t"]}'
        tracks[k] = forced.get(k) or query(tr['a'], tr['t'], tr['k'])
    todo = [k for k in tracks if k not in cache
            or ('--retry' in flags and not (cache[k] or {}).get('id') and not (cache[k] or {}).get('retried') and tracks[k] != '-')
            or (cache[k] and cache[k].get('q') != tracks[k])]
    print(f'{len(tracks)} títulos, {len(todo)} por buscar', flush=True)
    done = 0
    with ThreadPoolExecutor(8) as pool:
        for k, res in zip(todo, pool.map(lambda k: search(tracks[k]), todo)):
            cache[k] = res and {**res, 'q': tracks[k]}
            done += 1
            print(('OK  ' if res else 'NADA') + f' {tracks[k]}  →  {res["title"] if res else ""}', flush=True)
            if done % 200 == 0:   # guardado parcial por si se interrumpe
                cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True))
    # Vídeos que no coinciden en nada: otra búsqueda sin «full album»; si sigue igual, sin vídeo.
    bad = [k for k in tracks if (cache.get(k) or {}).get('id') and k not in forced and not cache[k].get('retried') and mismatch(k, cache[k])]
    if bad:
        print(f'{len(bad)} vídeos sin relación aparente: reintentando', flush=True)
        with ThreadPoolExecutor(8) as pool:
            for k, res in zip(bad, pool.map(lambda k: search(query(*k.split('|', 1), 's')), bad)):
                good = res and not mismatch(k, res)
                cache[k] = {**res, 'q': tracks[k], 'retried': 1} if good else {'id': None, 'q': tracks[k], 'retried': 1}
                print(('REHECHO ' if good else 'DESCARTADO ') + k + (f'  →  {res["title"]}' if good else ''), flush=True)
    ok_file = ROOT / 'tools' / 'yt-ok.txt'
    accepted = set(ok_file.read_text().splitlines()) if ok_file.exists() else set()
    doubtful = [k for k in tracks if cache.get(k, {}) and (cache.get(k) or {}).get('id') and k not in accepted and not plausible(k, cache[k])]
    for k in doubtful:
        print('DUDOSO', k, '→', cache[k]['title'], '/', cache[k]['channel'])
    if '--accept' in flags and doubtful:
        with ok_file.open('a') as f:
            f.write(''.join(k + '\n' for k in doubtful))
        print(f'{len(doubtful)} aceptadas')
    cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True))
    live = {k: v for k, v in cache.items() if v and v.get('id') and k in tracks}
    (ROOT / 'data' / 'yt.js').write_text(
        '// Generado por tools/yt.py — no editar a mano.\n'
        f'window.ROCK_YT = {json.dumps(live, ensure_ascii=False)};\n')
    print(f'{len(live)} con vídeo, {sum(1 for k in tracks if not (cache.get(k) or {}).get('id'))} sin vídeo, {len(doubtful)} dudosos')


if __name__ == '__main__':
    main(*sys.argv[1:])
