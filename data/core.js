// Registro de géneros. Cada fichero de sección (data/NN-*.js, generados por
// tools/build_data.py) llama a ROCK.add([...]) con los géneros que nacen en esa
// sección; data/books.js describe partes, secciones y subapartados del libro, y
// data/best.js los apéndices de mejores discos y grupos de cada década.
window.ROCK = (function () {
  const genres = new Map();
  const book = { parts: [], sections: [] };
  const best = { albums: [], greatest: {} };

  const FAMILIES = {
    raices:     { name: "Raíces: rock'n'roll, country y roots", color: '#f59e0b' },
    folk:       { name: 'Folk y cantautores', color: '#a3e635' },
    psico:      { name: 'Psicodelia, garage y shoegaze', color: '#c084fc' },
    prog:       { name: 'Progresivo, krautrock y jazz-rock', color: '#38bdf8' },
    hard:       { name: 'Hard rock, metal y grunge', color: '#f87171' },
    punk:       { name: 'Punk, new wave, hardcore y noise', color: '#fb7185' },
    pop:        { name: 'Pop, power-pop y synth-pop', color: '#f472b6' },
    dark:       { name: 'Gótico e industrial', color: '#94a3b8' },
    negra:      { name: 'Soul, funk, disco, hip hop y baile', color: '#facc15' },
    vanguardia: { name: 'Vanguardia, electrónica y ambient', color: '#2dd4bf' },
  };

  function add(list) {
    for (const g of list) {
      genres.set(g.id, { place: '', influences: [], artists: [], tracks: [], secs: [], ...g });
    }
  }

  return {
    FAMILIES,
    genres,
    book: Object.assign((b) => { book.parts = b.parts; book.sections = b.sections; }, { data: book }),
    best: Object.assign((b) => { best.albums = b.albums; best.greatest = b.greatest; }, { data: best }),
    add,
  };
})();
