import sys, json
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTTextLine
pdf, first, last = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
for pno, page in enumerate(extract_pages(pdf, page_numbers=range(first-1, last)), first):
    out = []
    for el in page:
        if not isinstance(el, LTTextContainer): continue
        for line in el:
            if not isinstance(line, LTTextLine): continue
            cur, buf = None, ''
            for ch in line:
                f = ch.fontname if isinstance(ch, LTChar) else cur
                tag = 'I' if f and 'Italic' in f else ('B' if f and 'Bold' in f else 'R')
                if tag != cur and buf:
                    out.append((cur, buf)); buf = ''
                cur = tag; buf += ch.get_text()
            if buf: out.append((cur, buf))
    s = ''.join(f'[{t}:{b}]' if t != 'R' else b for t, b in out)
    print(f'=== PAGE {pno}\n{s}')
