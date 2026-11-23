// Results explorer: one JPEG sprite per sequence group (assets/results/<group>.jpg, the paper's error and support style)
// and assets/results/meta.json with each row's offset and scores. Rows are drawn as scaled background windows.
(function () {
  'use strict';
  const BASE = 'assets/results/';
  const PAGE = 40;            // rows rendered per batch
  const GAP = 4, EXTRA = 3 * GAP, N_EXTRA = 3;   // panel gaps used by tools/build_results.py
  const groupSel = document.getElementById('group');
  const sortSel = document.getElementById('sort');
  const find = document.getElementById('find');
  const rowsEl = document.getElementById('rows');
  const countEl = document.getElementById('count');
  const moreEl = document.getElementById('more');
  let meta = [], kind = 'main', shown = 0, current = [];

  const fmt = v => (v === null || v === undefined || isNaN(v)) ? '–' : (v >= 10 ? v.toFixed(1) : v >= 1 ? v.toFixed(2) : v.toFixed(3));
  const stripWidth = w => w.reduce((a, b) => a + b, 0) + GAP * (w.length - 1) + EXTRA * N_EXTRA;

  function fillGroups() {
    groupSel.innerHTML = '';
    meta.filter(g => g.kind === kind).forEach(g => {
      const o = document.createElement('option');
      o.value = g.id; o.textContent = g.title.replace(/^Distortion: /, '') + ` (${g.rows.length})`;
      groupSel.appendChild(o);
    });
  }

  function rowEl(g, r) {
    const d = document.createElement('article'); d.className = 'row';
    const m = document.createElement('div'); m.className = 'meta';
    const lab = document.createElement('span'); lab.className = 'label'; lab.textContent = r.label;
    m.appendChild(lab);
    const ours = document.createElement('span'); ours.className = 'num ours';
    ours.innerHTML = r.ours ? `RayCal <b>${fmt(r.ours[0])}&deg;</b> / ${fmt(r.ours[1])}&deg;` : 'RayCal –';
    m.appendChild(ours);
    const best = document.createElement('span'); best.className = 'num';
    best.innerHTML = r.best ? `best baseline (${r.best[0]}) <b>${fmt(r.best[1])}&deg;</b> / ${fmt(r.best[2])}&deg;` : 'no baseline output';
    m.appendChild(best);
    const note = document.createElement('span'); note.className = 'num'; note.textContent = 'Mean / P90';
    m.appendChild(note);
    d.appendChild(m);
    const s = document.createElement('div');
    if (r.error || !r.widths) {
      s.className = 'strip missing'; s.style.aspectRatio = '8 / 1'; s.textContent = 'not available';
    } else {
      const wt = stripWidth(r.widths), ph = g.ph;
      s.className = 'strip';
      s.style.aspectRatio = `${wt} / ${ph}`;
      const file = BASE + g.id + '.jpg';
      s.style.backgroundImage = `url("${file}")`;
      s.style.backgroundSize = `${(g.width / wt) * 100}% auto`;
      const span = g.height - ph;
      s.style.backgroundPosition = `0 ${span > 0 ? (r.y / span) * 100 : 0}%`;
      s.setAttribute('role', 'img');
      s.setAttribute('aria-label', `${r.label}: input frames, ground truth, baseline and RayCal error, RayCal support`);
    }
    d.appendChild(s);
    return d;
  }

  // Missing scores sort last; the improvement is the best baseline's Mean over ours (no baseline output counts as largest).
  const ours = r => (r.ours && r.ours[0] != null) ? r.ours[0] : Infinity;
  const base = r => (r.best && r.best[1] != null) ? r.best[1] : Infinity;
  const gain = r => (ours(r) === Infinity) ? -Infinity : base(r) / ours(r);
  function sortRows(rows) {
    const by = {
      'name': (a, b) => a.label.localeCompare(b.label),
      'ours-asc': (a, b) => ours(a) - ours(b),
      'ours-desc': (a, b) => (ours(b) === Infinity ? -1 : ours(a) === Infinity ? 1 : ours(b) - ours(a)),
      'base-desc': (a, b) => base(b) - base(a),
      'gain-desc': (a, b) => gain(b) - gain(a),
    }[sortSel.value];
    rows.sort((a, b) => by(a, b) || a.label.localeCompare(b.label));
  }

  function render(reset) {
    const g = meta.find(x => x.id === groupSel.value);
    if (!g) return;
    if (reset) {
      const q = find.value.trim().toLowerCase();
      current = g.rows.filter(r => !q || r.label.toLowerCase().includes(q));
      sortRows(current);
      rowsEl.innerHTML = ''; rowsEl.scrollTop = 0; shown = 0;
    }
    const next = current.slice(shown, shown + PAGE);
    const frag = document.createDocumentFragment();
    next.forEach(r => frag.appendChild(rowEl(g, r)));
    rowsEl.appendChild(frag); shown += next.length;
    countEl.textContent = `${current.length} sequences`;
    moreEl.hidden = true;
  }

  // The rows scroll inside their own box; the next batch loads near its bottom.
  rowsEl.addEventListener('scroll', () => {
    if (shown < current.length && rowsEl.scrollTop + rowsEl.clientHeight > rowsEl.scrollHeight - 600) render(false);
  }, { passive: true });

  document.querySelectorAll('.seg button').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('.seg button').forEach(x => x.setAttribute('aria-selected', String(x === b)));
    kind = b.dataset.kind; fillGroups(); render(true);
  }));
  groupSel.addEventListener('change', () => render(true));
  sortSel.addEventListener('change', () => render(true));
  find.addEventListener('input', () => render(true));
  document.getElementById('showmore').addEventListener('click', () => render(false));

  fetch(BASE + 'meta.json').then(r => r.json()).then(m => { meta = m; fillGroups(); render(true); })
    .catch(() => { rowsEl.innerHTML = '<p class="muted">Results could not be loaded.</p>'; });
})();
