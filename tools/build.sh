#!/bin/sh
# Regenera todo a partir del PDF: extracción, datos de la web, vídeos de YouTube e index.html.
# Uso: tools/build.sh [--yt]   (--yt busca en YouTube los títulos nuevos y sus portadas en Last.fm, Deezer y Wikidata; tarda)
set -e
cd "$(dirname "$0")/.."
PDF="A History of Rock Music - 1951-2000 (piero scaruffi) (z-library.sk, 1lib.sk, z-lib.sk).pdf"
mkdir -p build
[ -s build/marked.txt ] || python3 tools/pdfmarks.py "$PDF" 1 330 > build/marked.txt
[ -s build/book.txt ] || pdftotext -layout "$PDF" build/book.txt
python3 -I tools/extract.py build/marked.txt build/sections.json build/book.txt > /dev/null
python3 -I tools/appendix.py build/book.txt build/appendix.json > /dev/null
python3 -I tools/build_data.py build/sections.json build/appendix.json
if [ "$1" = "--yt" ]; then
python3 -I tools/yt.py | grep -v "^OK  " || true
if [ -n "$LASTFM_API_KEY" ]; then python3 -I tools/covers.py; else echo "Sin LASTFM_API_KEY: no se actualizan las portadas"; fi
fi
tags=$(for f in data/[0-9]*.js; do printf '<script src="%s"></script>\\n' "$f"; done)
python3 -I - "$tags" <<'PY'
import re, sys
p = 'index.html'
s = open(p).read()
block = '<!-- secciones:inicio -->\n' + sys.argv[1].replace('\\n', '\n') + '<!-- secciones:fin -->'
s = re.sub(r'<!-- secciones:inicio -->.*?<!-- secciones:fin -->', block, s, flags=re.S)
open(p, 'w').write(s)
PY
python3 -I tools/pdfpages.py --sin-discos - "$(ls *.pdf | head -n 1)"
for f in data/*.js app.js covers.js menciones.js; do node --check "$f"; done
