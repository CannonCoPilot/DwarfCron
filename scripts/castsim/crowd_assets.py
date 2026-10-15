"""castsim.crowd_assets: the CSS and JS for the crowdedness-and-diversity charts (design_report.crowd_section)."""

CSS = r"""
.viz-root{--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#4a3aa7}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .viz-root{--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9}}
:root[data-theme="dark"] .viz-root{--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9}
.crowd-filters{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 0 6px}
.crowd-filters span{color:var(--muted);font-size:13px;margin-right:4px}
.crowd-filters button{font:inherit;font-size:13px;padding:5px 12px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer}
.crowd-filters button[aria-pressed="true"]{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.crowd-chart{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px 6px;margin:0 0 14px;position:relative}
.crowd-chart h4{margin:0 0 2px;font-size:15px}
.crowd-chart .sub{color:var(--muted);font:400 12.5px/1.45 var(--sans);margin:0 0 6px;max-width:none}
.crowd-legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;color:var(--ink);margin:4px 0 4px}
.crowd-legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.crowd-chart svg{display:block;width:100%;height:auto;overflow:visible}
.crowd-chart .grid line{stroke:var(--line);stroke-width:1}
.crowd-chart .axis text{fill:var(--muted);font-size:11px;font-family:var(--sans)}
.crowd-chart .season line{stroke:var(--muted);stroke-width:1;stroke-dasharray:3 3;opacity:.7}
.crowd-chart .season text{fill:var(--muted);font-size:11px}
.crowd-chart .hl{fill:var(--ink);opacity:.06}
.crowd-tip{position:absolute;pointer-events:none;z-index:5;background:var(--surface);border:1px solid var(--line);border-radius:8px;
  box-shadow:0 6px 18px rgba(0,0,0,.14);padding:8px 10px;font-size:12.5px;min-width:190px;max-width:280px;color:var(--ink)}
.crowd-tip b{font-weight:600}.crowd-tip .m{color:var(--muted)}
.crowd-tip table{border-collapse:collapse;margin-top:4px;width:100%}.crowd-tip td{padding:1px 0;font-family:var(--mono);font-size:11.5px}
.crowd-tip td.n{text-align:right;padding-left:10px}
.crowd-tip i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px}
.crowd-chart details{margin:4px 0 6px;font-size:13px}.crowd-chart details summary{cursor:pointer;color:var(--muted)}
"""

JS = r"""
(function(){
const C = JSON.parse(document.getElementById('crowd-data').textContent);
const root = document.getElementById('crowd-charts');
if (!root || typeof d3 === 'undefined') return;
const TYPES = C.type_order, SLOT = t => 'var(--s' + (TYPES.indexOf(t) + 1) + ')';
const FORT = Object.fromEntries(Object.entries(C.forts).map(([k, f]) => [k, f.name]));
const LAYER = {land: 'Land', water: 'Water', cavern: 'Caverns'};
const SEASON = d => { const s = Math.floor((d % 336) / 84), n = ['Spring', 'Summer', 'Autumn', 'Winter'][s];
  return n + ' ' + (d % 84 + 1) + (d >= 336 ? ' (y251)' : ''); };
const totals = (cs) => cs.map(c => c.reduce((a, p) => a + p[1], 0));
// each chart has its own fort selector (user 13 Oct): land, water and caverns can each show any of the forts
const charts = {}, arms = {};
for (const L of ['land', 'water', 'cavern']) {
  const box = document.createElement('div'); box.className = 'crowd-chart';
  box.innerHTML = `<h4>${LAYER[L]}</h4><div class="crowd-filters"><span>Fort</span>` + Object.keys(C.forts).map((a, i) =>
    `<button type="button" data-arm="${a}" aria-pressed="${i === 0}">${FORT[a]}</button>`).join('') +
    (L === 'cavern' ? '<span style="margin-left:14px">Caverns</span>' + [1, 2, 3].map(k =>
      `<button type="button" data-cave="${k}" aria-pressed="true">${k}</button>`).join('') : '') + `</div>
    <p class="sub"></p><div class="crowd-legend"></div><div class="plot"></div>
    <details><summary>Species table</summary><div class="tbl"></div></details>`;
  root.appendChild(box); charts[L] = box; arms[L] = Object.keys(C.forts)[0];
  box.querySelector('.crowd-filters').addEventListener('click', ev => {
    const c = ev.target.closest('button[data-cave]');
    if (c) {   // the cavern toggles: any combination of caverns 1, 2, 3 (at least one stays on)
      const on = c.getAttribute('aria-pressed') === 'true', n = box.querySelectorAll('button[data-cave][aria-pressed="true"]').length;
      if (on && n === 1) return;
      c.setAttribute('aria-pressed', String(!on)); draw(L); return;
    }
    const b = ev.target.closest('button[data-arm]'); if (!b) return;
    arms[L] = b.dataset.arm; box.querySelectorAll('button[data-arm]').forEach(x => x.setAttribute('aria-pressed', x === b)); draw(L); });
}
const tip = document.createElement('div'); tip.className = 'crowd-tip'; tip.hidden = true; root.appendChild(tip);
function draw(only) {
  for (const L of ['land', 'water', 'cavern']) {
    if (only && L !== only) continue;
    const arm = arms[L], F = C.forts[arm];
    const box = charts[L], days = F.days;
    let D = F.layers[L];
    if (L === 'cavern') {   // keep the caverns toggled on, summed per species
      const caves = new Set([...box.querySelectorAll('button[data-cave][aria-pressed="true"]')].map(b => +b.dataset.cave));
      D = {species: D.species, counts: D.counts.map(c => { const m = new Map();
        for (const [k, n, d] of c) if (caves.has(d)) m.set(k, (m.get(k) || 0) + n);
        return [...m.entries()].sort((a, b) => a[0] - b[0]); })};
    }
    const sp = D.species;
    const tot = totals(D.counts);
    // only species seen in the shown data: the cavern toggle leaves the others at 0 (user 14 Oct: no 0-count rows)
    const seen = new Set(D.counts.flatMap(c => c.map(p => p[0])));
    const present = new Set(sp.filter((t, k) => seen.has(k)).map(t => C.types[t]));
    box.querySelector('.crowd-legend').innerHTML = TYPES.filter(t => present.has(t))
      .map(t => `<span><i style="background:${SLOT(t)}"></i>${t}</span>`).join('');
    const nsp = D.counts.map(c => c.length);
    box.querySelector('.sub').textContent = `${FORT[arm]}: up to ${d3.max(tot) || 0} animals and ${d3.max(nsp) || 0} species on one day; ${seen.size} species over the run. One bar per day, one segment per species.`;
    const plot = box.querySelector('.plot'); plot.innerHTML = '';
    const W = Math.max(320, plot.clientWidth || 900), H = 210, m = {t: 18, r: 8, b: 22, l: 34};
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const x = d3.scaleBand().domain(days).range([0, iw]).paddingInner(days.length > 200 ? 0.15 : 0.25);
    const y = d3.scaleLinear().domain([0, Math.max(4, d3.max(tot) || 0)]).nice().range([ih, 0]);   // fits this chart (user 13 Oct)
    const svg = d3.select(plot).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img')
      .attr('aria-label', `${LAYER[L]}: wild animals on the map per day, ${FORT[arm]}`);
    const g = svg.append('g').attr('transform', `translate(${m.l},${m.t})`);
    g.append('g').attr('class', 'grid').selectAll('line').data(y.ticks(4)).join('line')
      .attr('x1', 0).attr('x2', iw).attr('y1', d => y(d)).attr('y2', d => y(d));
    g.append('g').attr('class', 'axis').selectAll('text').data(y.ticks(4)).join('text')
      .attr('x', -6).attr('y', d => y(d) + 4).attr('text-anchor', 'end').text(d => d);
    const hl = g.append('rect').attr('class', 'hl').attr('y', 0).attr('height', ih).attr('width', x.bandwidth()).attr('visibility', 'hidden');
    const bw = x.bandwidth(), gap = 1;
    days.forEach((d, i) => {
      let acc = 0;
      for (const [k, n] of D.counts[i]) {
        const y0 = y(acc), y1 = y(acc + n); acc += n;
        const h = Math.max(0.5, y0 - y1 - gap);
        g.append('rect').attr('x', x(d)).attr('y', y1 + gap).attr('width', bw).attr('height', h)
          .attr('rx', Math.min(1.5, bw / 3)).attr('fill', SLOT(C.types[sp[k]]));
      }
    });
    const sg = g.append('g').attr('class', 'season');
    for (const [d, label] of C.seasons) {
      if (d < days[0] || d > days[days.length - 1] + 1) continue;
      const xx = d === days[0] ? 0 : (x(d) ?? iw) - 0.5;
      sg.append('line').attr('x1', xx).attr('x2', xx).attr('y1', -6).attr('y2', ih);
      sg.append('text').attr('x', xx + 4).attr('y', -6).text(label);
    }
    if (days[0] > 0) sg.append('text').attr('x', 2).attr('y', -6).text('Spring ' + (days[0] + 1));
    g.append('g').attr('class', 'axis').selectAll('text').data(days.filter(d => d % 28 === 0)).join('text')
      .attr('x', d => x(d) + bw / 2).attr('y', ih + 15).attr('text-anchor', 'middle').text(d => 'day ' + d);
    // hover: the day under the pointer (hit target = the whole column)
    svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', iw).attr('height', ih).attr('fill', 'transparent')
      .on('pointermove', ev => {
        const [px] = d3.pointer(ev, g.node());
        const i = Math.max(0, Math.min(days.length - 1, Math.floor(px / x.step())));
        hl.attr('x', x(days[i])).attr('visibility', 'visible');
        const rows = D.counts[i].slice().sort((a, b) => b[1] - a[1]);
        tip.innerHTML = `<b>${SEASON(days[i])}</b> <span class="m">· day ${days[i]}</span><br>${tot[i]} animals, ${rows.length} species` +
          (rows.length ? '<table>' + rows.slice(0, 14).map(([k, n]) => `<tr><td><i style="background:${SLOT(C.types[sp[k]])}"></i>${sp[k].toLowerCase()}</td><td class="n">${n}</td></tr>`).join('') +
          (rows.length > 14 ? `<tr><td class="m">+ ${rows.length - 14} more</td><td></td></tr>` : '') + '</table>' : '');
        tip.hidden = false;
        const rb = root.getBoundingClientRect(), bb = box.getBoundingClientRect();
        let left = ev.clientX - rb.left + 14; const tw = tip.offsetWidth;
        if (left + tw > rb.width) left = ev.clientX - rb.left - tw - 14;
        tip.style.left = Math.max(0, left) + 'px'; tip.style.top = (bb.top - rb.top + 40) + 'px';
      })
      .on('pointerleave', () => { hl.attr('visibility', 'hidden'); tip.hidden = true; });
    // table view: species, type, days on the map, mean on the days present, peak
    const st = sp.map((t, k) => { let dd = 0, s = 0, pk = 0;
      for (const c of D.counts) { const p = c.find(q => q[0] === k); if (p) { dd++; s += p[1]; pk = Math.max(pk, p[1]); } }
      return {t, type: C.types[t], dd, mean: dd ? s / dd : 0, pk}; }).filter(r => r.dd > 0).sort((a, b) => b.dd - a.dd || b.pk - a.pk);
    box.querySelector('details .tbl').innerHTML = '<table><thead><tr><th>species</th><th data-t="cat">type</th><th class="num" data-t="num">days on the map</th><th class="num" data-t="num">mean when present</th><th class="num" data-t="num">peak</th></tr></thead><tbody>' +
      st.map(r => `<tr><td class="mono">${r.t}</td><td>${r.type}</td><td class="num">${r.dd}</td><td class="num">${r.mean.toFixed(1)}</td><td class="num">${r.pk}</td></tr>`).join('') + '</tbody></table>';
  }
}
let rt; new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(() => draw(), 120); }).observe(root);
draw();
})();
"""
