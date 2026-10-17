(function () {
  const { FAMILIES, genres } = ROCK;
  const BOOK = ROCK.book.data, BEST = ROCK.best.data;
  // El PDF del libro, junto a index.html: los números de página enlazan a él (solo en local).
  const PDF = 'A History of Rock Music - 1951-2000 (piero scaruffi) (z-library.sk, 1lib.sk, z-lib.sk).pdf';
  const Y0 = 1888, Y1 = 2006, PX = 22;
  const ROW = 24, LANE_PAD = 26, BAR_H = 18;
  const NS = 'http://www.w3.org/2000/svg';

  const all = [...genres.values()];
  const byId = genres;
  // Hijos calculados a partir de las influencias declaradas.
  const children = new Map(all.map((g) => [g.id, []]));
  for (const g of all) for (const p of g.influences) {
    if (!byId.has(p)) { console.warn('Influencia desconocida', g.id, '←', p); continue; }
    children.get(p).push(g.id);
  }
  const secByNum = new Map(BOOK.sections.map((s) => [s.n, s]));
  const partOf = (n) => BOOK.parts.find((p) => p.n === n.split('.')[0]);

  const state = { q: '', off: new Set(), view: 'timeline', kind: '', secBest: false };
  const $ = (s) => document.querySelector(s);
  const el = (tag, attrs = {}, parent) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const x = (y) => (y - Y0) * PX;
  const endOf = (g) => g.end ?? g.start + 8;
  const secName = (n) => { const s = secByNum.get(n); return s ? `${n} · ${s.title}` : n; };
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

  function matches(g) {
    if (state.off.has(g.family)) return false;
    if (!state.q) return true;
    const hay = [g.name, g.place, ...g.artists.map((a) => a.a), ...g.tracks.map((t) => t.a + ' ' + t.t)].join(' ').toLowerCase();
    return hay.includes(state.q);
  }

  // Cabecera
  const nTracks = all.reduce((n, g) => n + g.tracks.length, 0);
  const nSongs = all.reduce((n, g) => n + g.tracks.filter((t) => t.k === 's').length, 0);
  const YT = window.ROCK_YT || {};
  const nVideo = Object.keys(YT).length;
  $('#progress').innerHTML = `${all.length} géneros · ${BOOK.sections.length} secciones · ${nTracks} títulos (${nTracks - nSongs} álbumes, ${nSongs} canciones) · ${BEST.albums.length} en las listas de mejores discos<div class="bar"><i style="width:${Math.min(100, (nVideo / Math.max(1, nTracks)) * 100)}%"></i></div><div class="yt">${nVideo} con vídeo en YouTube</div>`;

  // Filtros de familia
  const famBox = $('#families');
  for (const [id, f] of Object.entries(FAMILIES)) {
    const b = document.createElement('button');
    b.className = 'chip';
    b.innerHTML = `<i style="background:${f.color}"></i>${f.name}`;
    b.onclick = () => { state.off.has(id) ? state.off.delete(id) : state.off.add(id); b.classList.toggle('off'); render(); };
    famBox.appendChild(b);
  }

  $('#q').addEventListener('input', (e) => { state.q = e.target.value.trim().toLowerCase(); render(); });
  // En móvil la búsqueda y las familias van plegadas tras el botón «Filtros».
  const ctl = $('.controls');
  $('#ftoggle').onclick = () => {
    const on = ctl.classList.toggle('fopen');
    $('#ftoggle').setAttribute('aria-expanded', on);
    fitScrollers();
    if (on) $('#q').focus();
  };
  document.querySelectorAll('.views button').forEach((b) => b.onclick = () => {
    state.view = b.dataset.view;
    document.querySelectorAll('.views button').forEach((o) => o.classList.toggle('on', o === b));
    document.querySelectorAll('.view').forEach((v) => v.classList.toggle('on', v.id === state.view));
    if (state.view !== 'focus') history.replaceState(null, '', state.view === 'timeline' ? location.pathname : '#view=' + state.view);
  });
  $('#close').onclick = closePanel;
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closePanel(); });

  // ---------- Timeline ----------
  const pos = new Map();
  function renderTimeline() {
    const svg = $('#svg');
    svg.innerHTML = '';
    pos.clear();
    const W = x(Y1) + 40;
    const axis = el('g', { class: 'axis' }, svg);
    const lanes = el('g', {}, svg);
    const links = el('g', { class: 'links' }, svg);
    const bars = el('g', {}, svg);
    const tags = el('g', { class: 'lane-tags' }, svg);
    const yearTags = el('g', { class: 'year-tags' }, svg);

    let y = 30;
    for (const [fid, fam] of Object.entries(FAMILIES)) {
      const items = all.filter((g) => g.family === fid && matches(g)).sort((a, b) => a.start - b.start);
      if (!items.length) continue;
      const rows = [];
      for (const g of items) {
        const tw = g.name.length * 6.6 + 10;
        const fits = tw < x(endOf(g)) - x(g.start);
        const reach = x(endOf(g)) + (fits ? 0 : tw) + 8;
        let r = rows.findIndex((end) => end < x(g.start));
        if (r < 0) { r = rows.length; rows.push(0); }
        rows[r] = reach;
        g._row = r;
      }
      const h = LANE_PAD + rows.length * ROW + 8;
      el('rect', { class: 'lane-bg', x: 0, y, width: W, height: h }, lanes);
      el('rect', { x: 0, y, width: 4, height: h, fill: fam.color }, lanes);
      const lbl = el('text', { class: 'lane-label', x: 12, y: y + 16 }, tags);
      lbl.textContent = fam.name;
      for (const g of items) {
        const gy = y + LANE_PAD + g._row * ROW;
        const gx = x(g.start), gw = Math.max(6, x(endOf(g)) - gx);
        pos.set(g.id, { x: gx, w: gw, y: gy + BAR_H / 2 });
        const node = el('g', { class: 'g', 'data-id': g.id }, bars);
        el('rect', { x: gx, y: gy, width: gw, height: BAR_H, fill: fam.color, 'fill-opacity': 0.85 }, node);
        const fits = g.name.length * 6.6 + 10 < gw;
        const t = el('text', { x: fits ? gx + 6 : gx + gw + 5, y: gy + 13 }, node);
        t.textContent = g.name;
        if (fits) t.setAttribute('style', 'fill:#111');
        el('title', {}, node).textContent = `${g.name} (${g.start}–${g.end ?? '…'}) · ${g.tracks.length} títulos`;
        node.addEventListener('mouseenter', () => highlight(g.id, links, bars));
        node.addEventListener('mouseleave', () => highlight(null, links, bars));
        node.addEventListener('click', (e) => { e.stopPropagation(); open(g.id); });
      }
      y += h + 6;
    }
    const H = y + 10;
    drawAxis(axis, yearTags, x, 1890, 2005, W, H);
    svg.setAttribute('width', W);
    svg.setAttribute('height', H);
  }

  // Rejilla de años + etiquetas en un grupo aparte que se mantiene fijo arriba al hacer scroll.
  function drawAxis(grid, tags, sx, from, to, W, H) {
    for (let yr = from; yr <= to; yr += 5) {
      const big = yr % 10 === 0;
      el('line', { x1: sx(yr), x2: sx(yr), y1: 20, y2: H, 'stroke-width': big ? 1 : 0.5, opacity: big ? 1 : 0.6 }, grid);
    }
    el('rect', { class: 'year-bg', x: 0, y: 0, width: W, height: 20 }, tags);
    for (let yr = Math.ceil(from / 10) * 10; yr <= to; yr += 10) {
      el('text', { x: sx(yr) + 3, y: 14 }, tags).textContent = yr;
    }
  }
  // Mantiene fijas las etiquetas de familia (horizontal) y de años (vertical) de un scroller.
  function stickTags(sc) {
    const upd = () => {
      sc.querySelectorAll('.lane-tags').forEach((t) => t.setAttribute('transform', `translate(${sc.scrollLeft},0)`));
      sc.querySelectorAll('.year-tags').forEach((t) => t.setAttribute('transform', `translate(0,${sc.scrollTop})`));
    };
    sc.addEventListener('scroll', upd);
    return upd;
  }

  function curve(a, b) {
    const x1 = a.x + Math.min(a.w, Math.max(6, b.x - a.x)), y1 = a.y;
    const x2 = b.x, y2 = b.y;
    const dx = Math.max(30, Math.abs(x2 - x1) / 2);
    return `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`;
  }

  function highlight(id, links, bars) {
    links.innerHTML = '';
    bars.querySelectorAll('.g').forEach((n) => n.classList.remove('dim', 'hit'));
    if (!id) return;
    const g = byId.get(id), me = pos.get(id);
    const related = new Set([id, ...g.influences, ...children.get(id)]);
    bars.querySelectorAll('.g').forEach((n) => {
      if (!related.has(n.dataset.id)) n.classList.add('dim');
      if (n.dataset.id === id) n.classList.add('hit');
    });
    for (const p of g.influences) if (pos.has(p)) el('path', { d: curve(pos.get(p), me), class: 'in' }, links);
    for (const c of children.get(id)) if (pos.has(c)) el('path', { d: curve(me, pos.get(c)), stroke: FAMILIES[g.family].color }, links);
  }

  // ---------- Lista de géneros ----------
  function renderList() {
    const box = $('#list');
    box.innerHTML = '';
    const decades = new Map();
    for (const g of all.filter(matches).sort((a, b) => a.start - b.start)) {
      const d = g.start < 1950 ? 0 : Math.floor(g.start / 10) * 10;
      if (!decades.has(d)) decades.set(d, []);
      decades.get(d).push(g);
    }
    for (const [d, items] of decades) {
      box.insertAdjacentHTML('beforeend', `<h2>${d < 1950 ? 'Antes de 1950' : 'Años ' + String(d).slice(2)}</h2>`);
      const grid = document.createElement('div');
      grid.className = 'cards';
      for (const g of items) {
        const c = document.createElement('div');
        c.className = 'card';
        c.style.borderLeftColor = FAMILIES[g.family].color;
        c.innerHTML = `<h3>${esc(g.name)}</h3><div class="meta">${g.start}–${g.end ?? '…'}${g.place ? ' · ' + esc(g.place) : ''} · ${plural(g.tracks.length, 'título', 'títulos')}</div><p>${esc(g.desc || '')}</p>`;
        c.onclick = () => open(g.id);
        grid.appendChild(c);
      }
      box.appendChild(grid);
    }
    if (!decades.size) box.innerHTML = '<p class="hint">Nada coincide con la búsqueda.</p>';
  }

  // ---------- Discos y canciones ----------
  const pdfLink = (p) => p ? `<a class="pg" href="${encodeURI(PDF)}#page=${p}" target="_blank" rel="noopener" title="Abrir el PDF del libro en esa página">p. ${p}</a>` : '';
  const ytKey = (t) => `${t.a}|${t.t}`;
  const bestTag = (b) => !b ? '' : b.r != null ? `<i class="star" title="Mejores discos de los ${String(b.d).slice(2)}: ${b.r}/10">★ ${b.r}</i>`
    : `<i class="star" title="Mejores discos de los ${String(b.d).slice(2)}: puesto ${b.n}">★ #${b.n}</i>`;
  function trackHtml(t, extra = '') {
    const v = YT[ytKey(t)];
    const search = 'https://www.youtube.com/results?search_query=' + encodeURIComponent(`${t.a} ${t.t}`.replace(/\([^)]*\)/g, ''));
    const links = v
      ? `<button class="play" data-v="${esc(v.id)}" title="Reproducir aquí: ${esc(v.title)}">▶</button><a href="https://www.youtube.com/watch?v=${esc(v.id)}" target="_blank" rel="noopener" title="${esc(v.title)} · ${esc(v.channel)}">↗</a>`
      : `<a href="${search}" target="_blank" rel="noopener" title="Buscar en YouTube">🔍</a>`;
    const kind = t.k === 's' ? '<i class="kind" title="Canción">♪</i>' : t.k === 'a' ? '<i class="kind" title="Álbum">◉</i>' : '';
    const best = t.best || (t.r != null || t.n != null ? t : null);
    return `<li${best ? ' class="ess"' : ''}><span class="tt">${kind}${bestTag(best)} <b>${esc(t.a)}</b> — ${t.k === 's' ? '«' + esc(t.t) + '»' : '<i>' + esc(t.t) + '</i>'} ${t.y ? `<span class="y">(${t.y})</span>` : ''}${extra}</span><span class="act">${links}${pdfLink(t.p)}</span></li>`;
  }
  // Lista de reproducción anónima de YouTube con los primeros 50 vídeos de un grupo.
  function playlistLink(tracks) {
    const ids = tracks.map((t) => YT[ytKey(t)]?.id).filter(Boolean).slice(0, 50);
    if (ids.length < 2) return '';
    return `<a class="plist" href="https://www.youtube.com/watch_videos?video_ids=${ids.join(',')}" target="_blank" rel="noopener" title="Abrir en YouTube una lista con ${ids.length} vídeos">▶ lista (${ids.length})</a>`;
  }

  // Un único reproductor en toda la página: se abre bajo el disco pulsado y se cierra al volver a pulsarlo.
  function togglePlayer(b) {
    const li = b.closest('li');
    const prev = $('.player');
    const same = prev && prev.parentElement === li;
    if (prev) prev.remove();
    if (same) return;
    li.insertAdjacentHTML('beforeend', `<div class="player"><iframe src="https://www.youtube-nocookie.com/embed/${b.dataset.v}?autoplay=1" allow="autoplay; encrypted-media" allowfullscreen></iframe></div>`);
  }

  // La búsqueda filtra por artista, título o género; los chips de familia, por género; el selector, por tipo.
  function trackMatches(g, t) {
    if (g && state.off.has(g.family)) return false;
    if (state.kind && t.k !== state.kind) return false;
    return !state.q || `${t.a} ${t.t} ${g ? g.name : ''}`.toLowerCase().includes(state.q);
  }
  const byYear = (a, b) => (a.y || 9999) - (b.y || 9999) || a.a.localeCompare(b.a, 'es');
  const dot = (g) => `<i class="dot" style="background:${FAMILIES[g.family].color}"></i>`;
  const genreLink = (g) => `<button class="glink" data-go="${g.id}">${dot(g)}${esc(g.name)}</button>`;
  const kindSel = () => `<label>Tipo <select data-kind><option value="">todo</option><option value="a"${state.kind === 'a' ? ' selected' : ''}>álbumes</option><option value="s"${state.kind === 's' ? ' selected' : ''}>canciones</option></select></label>`;

  function discGroups(box, groups, unit, tools = '') {
    const n = groups.reduce((s, gr) => s + (gr.count ?? gr.tracks.length), 0);
    const openAll = groups.length <= 12;
    box.innerHTML = `<div class="dbar"><span>${plural(n, 'título', 'títulos')} · ${plural(groups.length, unit[0], unit[1])}</span>${tools}<button data-fold="1">Desplegar todo</button><button data-fold="0">Plegar todo</button></div>`
      + (groups.length ? groups.map((gr) => gr.html ? gr.html : `<details class="dgroup"${openAll || gr.open ? ' open' : ''}><summary>${gr.head}<span class="n">${gr.tracks.length}</span></summary><div class="gtools">${playlistLink(gr.tracks)}</div><ol class="tracks">${gr.tracks.map(gr.row).join('')}</ol></details>`).join('')
        : '<p class="hint">Nada coincide con la búsqueda.</p>');
  }
  function renderDiscs() {
    const groups = [];
    for (const g of all.slice().sort((a, b) => a.start - b.start || a.name.localeCompare(b.name, 'es'))) {
      const tracks = g.tracks.filter((t) => trackMatches(g, t)).sort(byYear);
      if (tracks.length) groups.push({ head: `${dot(g)}<b>${esc(g.name)}</b><span class="yrs">${g.start}–${g.end ?? '…'}</span><button class="glink" data-go="${g.id}">ficha</button>`, tracks, row: (t) => trackHtml(t) });
    }
    discGroups($('#discs'), groups, ['género', 'géneros'], kindSel());
  }

  // Por secciones del libro: parte › sección › subapartado, en el orden en que aparecen en el texto.
  function renderBySection() {
    const sec = new Map();
    for (const g of all) for (const t of g.tracks) {
      if ((state.secBest && !t.best) || !trackMatches(g, t)) continue;
      if (!sec.has(t.s)) sec.set(t.s, []);
      sec.get(t.s).push({ ...t, g });
    }
    const out = [];
    let count = 0, lastPart = null;
    for (const s of BOOK.sections) {
      const tracks = sec.get(s.n);
      if (!tracks) continue;
      tracks.sort((a, b) => a.p - b.p);
      count += tracks.length;
      const part = partOf(s.n);
      if (part && part !== lastPart) { out.push(`<h2 class="part">${esc(part.n)} · ${esc(part.title)}</h2>`); lastPart = part; }
      const subs = new Map([[null, []]]);
      for (const t of tracks) {
        const k = t.sub || null;
        if (!subs.has(k)) subs.set(k, []);
        subs.get(k).push(t);
      }
      const row = (t) => trackHtml(t, `<span class="gl">${genreLink(t.g)}</span>`);
      const body = [...subs].filter(([, l]) => l.length).map(([name, l]) =>
        (name ? `<h3 class="subh">${esc(name)} <span class="n">${l.length}</span>${playlistLink(l)}</h3>` : '') + `<ol class="tracks">${l.map(row).join('')}</ol>`).join('');
      out.push(`<details class="dgroup"><summary><b>${esc(s.n)} · ${esc(s.title)}</b><span class="yrs">p. ${s.p}</span><span class="n">${tracks.length}</span></summary><div class="gtools">${playlistLink(tracks)}</div><div class="secbody">${body}</div></details>`);
    }
    const box = $('#bysec');
    box.innerHTML = `<div class="dbar"><span>${plural(count, 'título', 'títulos')} en el orden del libro</span>${kindSel()}<label><input type="checkbox" id="secbest"${state.secBest ? ' checked' : ''}> Solo los de las listas de mejores ★</label><button data-fold="1">Desplegar todo</button><button data-fold="0">Plegar todo</button></div>`
      + (out.length ? out.join('') : '<p class="hint">Nada coincide con la búsqueda.</p>');
  }

  // Mejores discos de cada década (apéndices del libro) y ranking de grupos.
  function renderBest() {
    const groups = [];
    const decades = [...new Set(BEST.albums.map((a) => a.d))].sort();
    for (const d of decades) {
      const list = BEST.albums.filter((a) => a.d === d && trackMatches(a.g && byId.get(a.g), { ...a, k: 'a' }));
      if (!list.length) continue;
      const rated = list.some((a) => a.r != null);
      const head = `<b>Mejores discos de los años ${String(d).slice(2)}</b><span class="yrs">${rated ? 'por nota' : 'por puesto'}</span>`;
      const row = (a) => trackHtml({ ...a, k: 'a' }, a.g && byId.has(a.g) ? `<span class="gl">${genreLink(byId.get(a.g))}</span>` : '');
      let html;
      if (rated) {
        const notes = [...new Set(list.map((a) => a.r))].sort((a, b) => b - a);
        html = notes.map((r) => { const l = list.filter((a) => a.r === r); return `<h3 class="subh">${r}/10 <span class="n">${l.length}</span>${playlistLink(l)}</h3><ol class="tracks">${l.map(row).join('')}</ol>`; }).join('');
      } else {
        html = `<ol class="tracks ranked">${list.sort((a, b) => a.n - b.n).map((a) => row(a).replace('<li', `<li value="${a.n}"`)).join('')}</ol>`;
      }
      const top = BEST.greatest[d] || [];
      const greatest = top.length ? `<details class="greatest"><summary>Los mejores grupos de los ${String(d).slice(2)} según Scaruffi (${top.length})</summary><ol>${top.map((n) => `<li><button class="alink" data-artist="${esc(n)}">${esc(n)}</button></li>`).join('')}</ol></details>` : '';
      groups.push({ count: list.length, html: `<details class="dgroup" open><summary>${head}<span class="n">${list.length}</span></summary><div class="gtools">${playlistLink(list)}</div><div class="secbody">${greatest}${html}</div></details>` });
    }
    discGroups($('#ess'), groups, ['década', 'décadas']);
  }

  for (const box of document.querySelectorAll('.discs')) {
    box.addEventListener('click', (e) => {
      const b = e.target.closest('button, input');
      if (!b) return;
      if (b.matches('.play')) togglePlayer(b);
      else if (b.dataset.go) { e.preventDefault(); open(b.dataset.go); }
      else if (b.dataset.artist != null) { $('#q').value = b.dataset.artist; state.q = b.dataset.artist.toLowerCase(); render(); document.querySelector('.views button[data-view="discs"]').click(); }
      else if (b.dataset.fold) box.querySelectorAll('details.dgroup').forEach((d) => d.open = b.dataset.fold === '1');
      else if (b.id === 'secbest') { state.secBest = b.checked; renderBySection(); }
    });
    box.addEventListener('change', (e) => {
      if (e.target.matches('[data-kind]')) { state.kind = e.target.value; renderDiscs(); renderBySection(); }
    });
  }

  // ---------- Ficha ----------
  function chipFor(id) {
    const g = byId.get(id);
    if (!g) return '';
    return `<button class="chip" data-go="${id}"><i style="background:${FAMILIES[g.family].color}"></i>${esc(g.name)}</button>`;
  }
  function open(id) {
    const g = byId.get(id);
    const f = FAMILIES[g.family];
    const kids = children.get(id).slice().sort((a, b) => byId.get(a).start - byId.get(b).start);
    const tracks = g.tracks.slice().sort(byYear);
    const albums = tracks.filter((t) => t.k === 'a'), songs = tracks.filter((t) => t.k === 's');
    const artists = g.artists.slice().sort((a, b) => b.r.length - a.r.length || b.r.localeCompare(a.r) || a.a.localeCompare(b.a, 'es'));
    $('#detail').innerHTML = `
      <h2>${esc(g.name)}</h2>
      <div class="facts">
        <span class="fam"><i style="background:${f.color}"></i>${f.name}</span>
        <span>${g.start}–${g.end ?? '…'}</span>
        ${g.place ? `<span>${esc(g.place)}</span>` : ''}
      </div>
      <button class="tofocus" data-focus="${id}">Ver su timeline individual</button>
      <div class="desc"><div class="src">Resumen a partir del libro</div>${esc(g.desc || '')}</div>
      <h4>En el libro</h4><div class="tags">${g.secs.map((n) => `<span>${esc(secName(n))} · ${pdfLink(secByNum.get(n)?.p) || ''}</span>`).join('')}</div>
      ${g.influences.length ? `<h4>Viene de</h4><div class="links">${g.influences.map(chipFor).join('')}</div>` : ''}
      ${kids.length ? `<h4>Genera / influye en</h4><div class="links">${kids.map(chipFor).join('')}</div>` : ''}
      ${artists.length ? `<h4>Artistas valorados (${artists.length})</h4><div class="tags rated">${artists.map((a) => `<span title="Valoración de Scaruffi: nº de discos de 9, 8 y 7">${esc(a.a)} <b>${esc(a.r)}</b></span>`).join('')}</div><p class="fine">El número es la valoración de Scaruffi: cuántos discos de 9, 8 y 7 tiene el artista (214 = dos de 9, uno de 8 y cuatro de 7).</p>` : ''}
      ${albums.length ? `<h4>Álbumes (${albums.length}) ${playlistLink(albums)}</h4><ol class="tracks">${albums.map((t) => trackHtml(t)).join('')}</ol>` : ''}
      ${songs.length ? `<h4>Canciones (${songs.length}) ${playlistLink(songs)}</h4><ol class="tracks">${songs.map((t) => trackHtml(t)).join('')}</ol>` : ''}
    `;
    $('#detail').querySelectorAll('[data-go]').forEach((b) => b.onclick = () => open(b.dataset.go));
    $('#detail').querySelector('[data-focus]').onclick = () => showFocus(id);
    $('#detail').querySelectorAll('.play').forEach((b) => b.onclick = () => togglePlayer(b));
    $('#panel').classList.add('open');
    $('#panel').setAttribute('aria-hidden', 'false');
    $('#panel').scrollTop = 0;
    history.replaceState(null, '', '#' + id);
  }
  function closePanel() {
    $('#panel').classList.remove('open');
    $('#panel').setAttribute('aria-hidden', 'true');
    const inFocus = state.view === 'focus' && focus.root;
    history.replaceState(null, '', inFocus ? '#focus=' + focus.root : location.pathname);
  }

  // ---------- Timeline individual ----------
  // Un género raíz con sus influencias (padres) y lo que influye (hijos); el botón «+» de
  // cualquier género visible despliega también sus padres e hijos, sin quitar lo anterior.
  const focus = { root: null, open: new Set() };
  const parentsOf = (id) => byId.get(id).influences.filter((p) => byId.has(p));
  const relatives = (id) => [...parentsOf(id), ...children.get(id)];
  const nameKey = (g) => `${g.name} (${g.start}–${g.end ?? '…'})`;
  const byName = new Map(all.map((g) => [nameKey(g).toLowerCase(), g.id]));
  const dl = $('#focus-names');
  for (const g of all.slice().sort((a, b) => a.name.localeCompare(b.name, 'es'))) {
    const o = document.createElement('option');
    o.value = nameKey(g);
    dl.appendChild(o);
  }
  function pickFocus(id) {
    focus.root = id;
    focus.open = new Set([id]);
    $('#fq').value = nameKey(byId.get(id));
    renderFocus();
    history.replaceState(null, '', '#focus=' + id);
  }
  $('#fq').addEventListener('input', (e) => {
    const id = byName.get(e.target.value.trim().toLowerCase());
    if (id) pickFocus(id);
  });
  $('#fq').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    const q = e.target.value.trim().toLowerCase();
    const hit = all.find((g) => g.name.toLowerCase() === q) || all.find((g) => g.name.toLowerCase().includes(q));
    if (hit) pickFocus(hit.id);
  });
  $('#freset').onclick = () => { if (focus.root) pickFocus(focus.root); };

  function renderFocus() {
    const svg = $('#fsvg');
    svg.innerHTML = '';
    const box = $('#fscroller');
    if (!focus.root) { svg.setAttribute('width', 0); svg.setAttribute('height', 0); $('#fhint').hidden = false; return; }
    $('#fhint').hidden = true;
    const shown = new Set();
    for (const id of focus.open) { shown.add(id); relatives(id).forEach((r) => shown.add(r)); }
    const items = [...shown].map((id) => byId.get(id)).sort((a, b) => a.start - b.start || a.name.localeCompare(b.name));
    const from = Math.floor((Math.min(...items.map((g) => g.start)) - 4) / 10) * 10;
    const to = Math.ceil((Math.max(...items.map(endOf)) + 4) / 10) * 10;
    const fx = (yr) => (yr - from) * PX + 10;
    const BTN = 22;
    const rows = [];
    const lay = new Map();
    for (const g of items) {
      const gx = fx(g.start), gw = Math.max(6, fx(endOf(g)) - gx);
      const fits = g.name.length * 6.6 + 10 < gw;
      const textEnd = fits ? gx + gw : gx + gw + 5 + g.name.length * 6.1;
      let r = rows.findIndex((end) => end < gx - 4);
      if (r < 0) { r = rows.length; rows.push(0); }
      rows[r] = textEnd + BTN + 10;
      lay.set(g.id, { gx, gw, fits, textEnd, row: r });
    }
    const W = Math.max(fx(to) + 40, ...rows.map((e) => e + 20));
    const H = 30 + rows.length * (ROW + 6) + 20;
    const grid = el('g', { class: 'axis' }, svg);
    const links = el('g', { class: 'links on' }, svg);
    const bars = el('g', {}, svg);
    const yearTags = el('g', { class: 'year-tags' }, svg);
    drawAxis(grid, yearTags, fx, from, to, W, H);
    const fpos = new Map();
    for (const g of items) {
      const L = lay.get(g.id);
      const gy = 30 + L.row * (ROW + 6);
      fpos.set(g.id, { x: L.gx, w: L.gw, y: gy + BAR_H / 2 });
      const fam = FAMILIES[g.family];
      const node = el('g', { class: 'g' + (g.id === focus.root ? ' root' : '') + (focus.open.has(g.id) ? ' expanded' : ''), 'data-id': g.id }, bars);
      el('rect', { x: L.gx, y: gy, width: L.gw, height: BAR_H, fill: fam.color, 'fill-opacity': 0.85 }, node);
      const t = el('text', { x: L.fits ? L.gx + 6 : L.gx + L.gw + 5, y: gy + 13 }, node);
      t.textContent = g.name;
      if (L.fits) t.setAttribute('style', 'fill:#111');
      el('title', {}, node).textContent = `${g.name} (${g.start}–${g.end ?? '…'}) · clic para abrir la ficha`;
      node.addEventListener('click', (e) => { e.stopPropagation(); open(g.id); });
      // Botón +/−: desplegar o plegar padres e hijos de este género.
      const more = relatives(g.id).filter((r) => !shown.has(r)).length;
      if (g.id !== focus.root && (more || focus.open.has(g.id))) {
        const isOpen = focus.open.has(g.id);
        const b = el('g', { class: 'fbtn', transform: `translate(${L.textEnd + 6},${gy})` }, bars);
        el('rect', { width: BTN, height: BAR_H, rx: 4 }, b);
        el('text', { x: BTN / 2, y: 13, 'text-anchor': 'middle' }, b).textContent = isOpen ? '−' : '+';
        el('title', {}, b).textContent = isOpen ? 'Plegar sus relaciones' : `Desplegar sus influencias y herederos (${more} nuevos)`;
        b.addEventListener('click', (e) => {
          e.stopPropagation();
          isOpen ? focus.open.delete(g.id) : focus.open.add(g.id);
          renderFocus();
        });
      }
    }
    for (const g of items) for (const p of parentsOf(g.id)) {
      if (!fpos.has(p) || !(focus.open.has(p) || focus.open.has(g.id))) continue;
      el('path', { d: curve(fpos.get(p), fpos.get(g.id)), stroke: FAMILIES[byId.get(p).family].color }, links);
    }
    svg.setAttribute('width', W);
    svg.setAttribute('height', H);
    stickFocus();
    const r = fpos.get(focus.root);
    if (r) box.scrollLeft = Math.max(0, r.x - box.clientWidth / 3);
  }
  const stickFocus = stickTags($('#fscroller'));
  $('#fsvg').addEventListener('click', (e) => { if (!e.target.closest('.g, .fbtn')) closePanel(); });
  function showFocus(id) {
    document.querySelector('.views button[data-view="focus"]').click();
    pickFocus(id);
  }
  const stickMain = stickTags($('#scroller'));
  // Clic en una zona vacía del timeline: cerrar la ficha.
  $('#svg').addEventListener('click', (e) => { if (!e.target.closest('.g')) closePanel(); });
  // Cada scroller ocupa el alto restante de la ventana: así la página no hace scroll
  // y el eje de años (fijo dentro del scroller) siempre queda visible.
  function fitScrollers() {
    for (const sc of document.querySelectorAll('.view.on .scroller')) {
      const top = sc.getBoundingClientRect().top + window.scrollY;
      sc.style.height = Math.max(240, window.innerHeight - top - 8) + 'px';
    }
  }
  window.addEventListener('resize', fitScrollers);
  document.querySelectorAll('.views button').forEach((b) => b.addEventListener('click', fitScrollers));
  // Pestaña «Portadas» (covers.js, común a todas las webs de Music_Books).
  const portadas = Portadas({
    all, FAMILIES, esc, trackHtml, togglePlayer, open, YT, data: window.ROCK_COVERS,
    matches: trackMatches, isKey: (t) => !!(t.best || t.r != null || t.n != null),
    keyLabel: 'Solo mejores discos ★', keyName: 'en las listas de mejores discos',
    where: (r) => r.s ? `${esc(secName(r.s))} ${pdfLink(r.p)}` : '',
  });
  function render() {
    $('#ftoggle').classList.toggle('active', !!state.q || state.off.size > 0);
    renderTimeline(); renderList(); renderDiscs(); renderBySection(); renderBest(); portadas.render(); stickMain(); fitScrollers();
  }
  render();
  const hash = location.hash.slice(1);
  const viewBtn = hash.startsWith('view=') && document.querySelector(`.views button[data-view="${hash.slice(5)}"]`);
  if (viewBtn) viewBtn.click();
  else if (hash.startsWith('focus=') && byId.has(hash.slice(6))) showFocus(hash.slice(6));
  else if (byId.has(hash)) open(hash);
  // Arrancar la vista hacia 1945, donde empieza la densidad.
  $('#scroller').scrollLeft = x(1945) - 40;
})();
