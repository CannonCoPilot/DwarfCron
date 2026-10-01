
(function(){
const FIGS = JSON.parse(document.getElementById('figdata').textContent);
const BYID = Object.fromEntries(FIGS.map(f => [f.id, f]));
const css = () => { const s = getComputedStyle(document.documentElement); const g = n => s.getPropertyValue(n).trim();
  return {ink:g('--ink'), ink2:g('--ink2'), ink3:g('--ink3'), grid:g('--grid'), axis:g('--axis'), muted:g('--muted'), panel:g('--panel'),
          pal:[g('--s1'),g('--s2'),g('--s3'),g('--s4'),g('--s5'),g('--s6'),g('--s7'),g('--s8')], mono:g('--mono'), ui:g('--ui')}; };
const num = v => typeof v === 'number' ? v : (v != null && v !== '' && !isNaN(+v) ? +v : v);
const fmt = v => typeof v === 'number' ? (Math.abs(v) >= 1000 ? v.toLocaleString('en-US', {maximumFractionDigits:0}) : (Number.isInteger(v) ? String(v) : v.toLocaleString('en-US', {maximumFractionDigits:2}))) : String(v);
const uniq = (rows, k) => k ? [...new Set(rows.map(r => r[k]).filter(v => v != null))] : [];
const longest = arr => arr.reduce((m, s) => Math.max(m, String(s).length), 0);
function logOf(spec, axis){ const l = spec.log; if (!l) return false; if (l === true) return axis === (spec.form === 'scatter' ? 'both' : 'value') || l === true; return l === axis || l === 'both'; }
function colorScale(spec, rows, C){
  const s = spec.series; if (!s) return null;
  const dom = spec.seriesOrder || uniq(rows, s);
  if (dom.length > 8) return {type:'ordinal', domain:dom, range:dom.map((d,i) => i < 7 ? C.pal[i] : C.muted)};
  return {type:'ordinal', domain:dom, range:C.pal.slice(0, dom.length), legend:true};
}
function tipText(spec, r){ const keys = Object.keys(r).filter(k => !k.startsWith('_')).slice(0, 8); return keys.map(k => `${k}: ${fmt(r[k])}`).join('\n'); }

function build(spec, width){
  const C = css(); const rows = (spec.rows || []).map(r => { const o = {}; for (const k in r) o[k] = num(r[k]); return o; });
  let x = spec.x, y = spec.y; const s = spec.series || null, fct = spec.facet || null, form = spec.form;
  // Categorical forms read spec.x as the category and spec.y as the value. A spec written the other way round
  // (numeric x, text y) used to plot text on a linear scale: every mark NaN, an empty frame. Swap it and say so.
  if (['bar','dot','dumbbell','box','strip','stackedBar','groupedBar','range'].includes(form) && rows.length && x && y
      && rows.every(r => typeof r[x] === 'number') && rows.some(r => typeof r[y] === 'string')){
    console.warn('figure', spec.id, ': x/y swapped (x must be the category)'); [x, y] = [y, x]; }
  const color = colorScale(spec, rows, C);
  const hi = spec.highlight;
  const base = {width, style:{background:'transparent', color:C.ink2, fontFamily:C.ui, fontSize:'12px', overflow:'visible'},
                marginTop:16, marginRight:28, marginBottom:40, grid:false};
  const accent = C.pal[0];
  const single = r => (hi != null && (r[x] === hi || r[s] === hi)) ? accent : (hi != null ? C.muted : accent);
  const refs = (spec.reference || []).map(rf => rf);
  const cats = uniq(rows, x);
  const lm = Math.min(280, 18 + 7.6 * longest(cats));
  const T = r => tipText(spec, r);
  const unit = spec.unit && !String(spec.yLabel || spec.y || '').includes(spec.unit) ? ` (${spec.unit})` : '';
  let marks = [], opt = {};
  const valueLog = spec.log === true || spec.log === 'value' || spec.log === 'x' && ['bar','dot','box','range','dumbbell'].includes(form);
  switch(form){
    case 'bar': {
      const horiz = cats.length > 5 || longest(cats) > 9;
      if (horiz){
        marks = [Plot.barX(rows, {x:y, y:x, fill: s ? s : single, sort: spec.sort === false ? undefined : {y:'-x'}, title:T, rx:2}),
                 Plot.text(rows, {x:y, y:x, text:d => fmt(d[y]), dx:4, textAnchor:'start', fill:C.ink2, fontSize:11}),
                 Plot.ruleX([0], {stroke:C.axis})];
        opt = {marginLeft:lm, height:Math.max(110, 26 * cats.length + 50), x:{label:(spec.yLabel || y) + unit, grid:true, type: valueLog ? 'log' : 'linear'}, y:{label:null}};
      } else {
        marks = [Plot.barY(rows, {x:x, y:y, fill: s ? s : single, title:T, rx:2}),
                 Plot.text(rows, {x:x, y:y, text:d => fmt(d[y]), dy:-7, fill:C.ink2, fontSize:11}), Plot.ruleY([0], {stroke:C.axis})];
        opt = {height:280, x:{label:null, domain:cats}, y:{label:(spec.yLabel || y) + unit, grid:true}};
      }
      break; }
    case 'groupedBar': {
      const ser = uniq(rows, s);
      if (cats.length * ser.length > 10 || longest(cats) > 9){
        marks = [Plot.barX(rows, {x:y, y:s, fy:x, fill:s, title:T, rx:2}), Plot.text(rows, {x:y, y:s, fy:x, text:d => fmt(d[y]), dx:4, textAnchor:'start', fill:C.ink2, fontSize:10.5}), Plot.ruleX([0], {stroke:C.axis})];
        opt = {marginLeft:Math.min(260, 18 + 7.4*longest(cats)), height:Math.max(140, cats.length * (ser.length*15 + 12) + 50), x:{label:(spec.yLabel || y) + unit, grid:true}, y:{axis:null, domain:ser}, fy:{label:null, domain:cats, padding:.18}};
      } else {
        marks = [Plot.barY(rows, {fx:x, x:s, y:y, fill:s, title:T, rx:2}), Plot.text(rows, {fx:x, x:s, y:y, text:d => fmt(d[y]), dy:-7, fill:C.ink2, fontSize:10.5}), Plot.ruleY([0], {stroke:C.axis})];
        opt = {height:290, x:{axis:null, domain:ser}, fx:{label:null, domain:cats}, y:{label:(spec.yLabel || y) + unit, grid:true}};
      }
      break; }
    case 'stackedBar': {
      marks = [Plot.barX(rows, {x:y, y:x, fill:s, title:T, inset:0.5}), Plot.ruleX([0], {stroke:C.axis})];
      opt = {marginLeft:lm, height:Math.max(120, 28 * cats.length + 60), x:{label:(spec.yLabel || y) + unit, grid:true, type: valueLog ? 'log':'linear'}, y:{label:null, domain:spec.categoryOrder || cats}};
      break; }
    case 'dot': {
      const hasRep = rows.some(r => r.rep != null);
      marks = [Plot.ruleY(cats, {stroke:C.grid}),
               Plot.dot(rows, {x:y, y:x, fill: s ? s : accent, r:5, stroke:C.panel, strokeWidth:1, title:T})];
      // replicate mean: one tick per category AND series (one tick pooled over both arms meant nothing)
      if (hasRep) marks.push(Plot.tickX(rows, Plot.groupY({x:'mean'}, s ? {x:y, y:x, z:s, stroke:s, strokeWidth:2} : {x:y, y:x, stroke:C.ink, strokeWidth:2})));
      opt = {marginLeft:lm, height:Math.max(110, 26 * cats.length + 54), x:{label:(spec.yLabel || y) + unit, grid:true, type: valueLog ? 'log':'linear'}, y:{label:null, domain:spec.categoryOrder || cats}};
      break; }
    case 'dumbbell': {
      const ser = uniq(rows, s).slice(0, 2);
      const byCat = d3.rollups(rows, v => v, d => d[x]);
      const links = byCat.map(([k, v]) => { const a = d3.mean(v.filter(r => r[s] === ser[0]), r => r[y]), b = d3.mean(v.filter(r => r[s] === ser[1]), r => r[y]); return {k, a, b}; });
      marks = [Plot.link(links, {x1:'a', x2:'b', y1:'k', y2:'k', stroke:C.axis, strokeWidth:2}),
               Plot.dot(rows, {x:y, y:x, fill:s, r:5.5, stroke:C.panel, strokeWidth:1, title:T})];
      opt = {marginLeft:lm, height:Math.max(110, 30 * cats.length + 54), x:{label:(spec.yLabel || y) + unit, grid:true, type: valueLog ? 'log':'linear'}, y:{label:null, domain:spec.categoryOrder || cats}};
      break; }
    case 'heatmap': {
      const v = spec.value || spec.z || (rows[0] && ('value' in rows[0] ? 'value' : (s && typeof rows[0][s] === 'number' ? s : y)));
      const xs = uniq(rows, x), ys = uniq(rows, y === v ? (s || y) : y);
      const yk = y === v ? s : y;
      const vmax = d3.max(rows, d => +d[v] || 0) || 1;
      const big = spec.cellText === false || xs.length > 24;
      const xd = spec.xOrder || xs, yd = spec.yOrder || ys;
      marks = [Plot.cell(rows, {x:x, y:yk, fill:v, title:T, inset: big ? 0.5 : 1})];
      if (!big) marks.push(Plot.text(rows, {x:x, y:yk, text:d => d[v] == null ? '' : fmt(d[v]), fill:d => ((+d[v] || 0) / vmax > 0.5 ? '#ffffff' : '#17201C'), fontSize:10.5, fontWeight:500}));
      const ml = Math.min(260, 18 + 7.4*longest(ys)), mb = big ? Math.min(200, 18 + 7.4*longest(xs)) : Math.min(150, 24 + 6.4*longest(xs));
      const side = big ? Math.max(9, Math.floor((width - ml - 20) / xd.length)) : 26;    // square cells for a big matrix
      opt = {marginLeft:ml, marginBottom:mb, marginRight: big ? 20 : 28,
             width: big ? ml + side * xd.length + 20 : width,
             height: big ? side * yd.length + mb + 16 : Math.max(160, 26 * ys.length + 110),
             x:{label:null, tickRotate: big ? -90 : (longest(xs) > 5 ? -40 : 0), domain:xd}, y:{label:null, domain:yd},
             color:{type: spec.colorType || 'linear', scheme:'blues', legend:true, label:(spec.valueLabel || v) + (spec.unit && !(spec.valueLabel || v).includes(spec.unit) ? ` (${spec.unit})` : '')}};
      const node = Plot.plot({...base, ...opt, marks});
      if (big && spec.blocks){   // outline each block on the diagonal; a block is {from, to, label}, first and last token in the order
        const sx = node.scale('x'), sy = node.scale('y');
        const svg = node.tagName.toLowerCase() === 'svg' ? node : [...node.querySelectorAll('svg')].pop();
        const g = d3.select(svg).append('g').attr('aria-label', 'blocks');
        for (const bk of spec.blocks){
          const i = xd.indexOf(bk.from), j = xd.indexOf(bk.to); if (i < 0 || j < 0) continue;
          const x0 = sx.apply(xd[i]), x1 = sx.apply(xd[j]) + sx.bandwidth, y0 = sy.apply(yd[yd.indexOf(bk.from)]), y1 = sy.apply(yd[yd.indexOf(bk.to)]) + sy.bandwidth;
          g.append('rect').attr('x', x0).attr('y', y0).attr('width', x1 - x0).attr('height', y1 - y0).attr('fill', 'none').attr('stroke', C.ink).attr('stroke-width', 1.6)
           .append('title').text(bk.label);
          if (bk.tag) g.append('text').attr('x', x1 + 3).attr('y', y0 - 3).attr('font-size', 11.5).attr('font-weight', 700).attr('fill', C.ink)
             .attr('stroke', C.panel).attr('stroke-width', 3).attr('paint-order', 'stroke').text(bk.tag);
        }
      }
      return node;
    }
    case 'line': {
      marks = [Plot.line(rows, {x:x, y:y, stroke: s || accent, strokeWidth:2, curve: spec.curve || 'monotone-x'}),   // cumulative counts: curve 'step-after' Plot.dot(rows, {x:x, y:y, fill: s || accent, r:3, title:T})];
      opt = {height:280, x:{label:(spec.xLabel || x), grid:false}, y:{label:(spec.yLabel || y) + unit, grid:true, type: valueLog ? 'log':'linear'}};
      break; }
    case 'scatter': {
      const lx = spec.log === true || spec.log === 'x' || spec.log === 'both', ly = spec.log === 'y' || spec.log === 'both';
      marks = [Plot.dot(rows, {x:x, y:y, fill: s || accent, r:4, fillOpacity:.8, stroke:C.panel, strokeWidth:.6, title:T})];
      if (spec.labelField) marks.push(Plot.text(rows.filter(r => r._label || r.label), {x:x, y:y, text: spec.labelField, dx:6, textAnchor:'start', fontSize:10.5, fill:C.ink2}));
      opt = {height:340, x:{label:(spec.xLabel || x), type: lx ? 'log':'linear', grid:true}, y:{label:(spec.yLabel || y) + unit, type: ly ? 'log':'linear', grid:true}};
      break; }
    case 'box': {
      marks = [Plot.boxX(rows, {x:y, y:x, fill:C.pal[0], fillOpacity:.25, stroke:C.ink2})];
      opt = {marginLeft:lm, height:Math.max(130, 30 * cats.length + 54), x:{label:(spec.yLabel || y) + unit, grid:true, type: valueLog ? 'log':'linear'}, y:{label:null, domain:spec.categoryOrder || cats}};
      break; }
    case 'strip': {
      marks = [Plot.dot(rows, {x:y, y:x, fill: s || accent, r:2.6, fillOpacity:.55, title:T}),
               Plot.tickX(rows, Plot.groupY({x:'median'}, {x:y, y:x, stroke:C.ink, strokeWidth:2}))];
      opt = {marginLeft:lm, height:Math.max(130, 28 * cats.length + 54), x:{label:(spec.yLabel || y) + unit, grid:true, type: valueLog ? 'log':'linear'}, y:{label:null, domain:spec.categoryOrder || cats}};
      break; }
    case 'histogram': {
      const lx = valueLog;
      marks = [Plot.rectY(rows, Plot.binX({y:'count'}, {x:x, fill: s || accent, title: d => '', thresholds: spec.bins || 'auto'})), Plot.ruleY([0], {stroke:C.axis})];
      opt = {height:260, x:{label:(spec.xLabel || x) + unit, type: lx ? 'log':'linear'}, y:{label:'species', grid:true}};
      break; }
    case 'range': {
      const lo = spec.lo || ('min' in (rows[0]||{}) ? 'min' : 'lo'), hi2 = spec.hi || ('max' in (rows[0]||{}) ? 'max' : 'hi');
      marks = [Plot.ruleY(cats, {stroke:C.grid}), Plot.link(rows, {x1:lo, x2:hi2, y1:x, y2:x, stroke: s || accent, strokeWidth:5, strokeLinecap:'round', title:T})];
      if (y && y !== lo) marks.push(Plot.dot(rows, {x:y, y:x, fill:C.ink, r:3}));
      opt = {marginLeft:lm, height:Math.max(110, 24 * cats.length + 54), x:{label:(spec.yLabel || 'range') + unit, grid:true, type: valueLog ? 'log':'linear'}, y:{label:null, domain:spec.categoryOrder || cats}};
      break; }
    default: return null;
  }
  refs.forEach((rf, ri) => { const vv = rf.value; const horizontal = rf.axis === 'x' && ['line','scatter','histogram'].includes(form) ? true :
      ['bar','dot','dumbbell','box','strip','stackedBar','range'].includes(form) && (form !== 'bar' || cats.length > 5 || longest(cats) > 9);
    if (horizontal){ marks.push(Plot.ruleX([vv], {stroke:C.ink3, strokeDasharray:'4,3'}), Plot.text([vv], {x:d => d, frameAnchor:'top', dy:-2 + ri * 12, text:() => rf.label, fill:C.ink3, fontSize:10.5, textAnchor:'start', dx:4})); }
    else { marks.push(Plot.ruleY([vv], {stroke:C.ink3, strokeDasharray:'4,3'}), Plot.text([vv], {y:d => d, frameAnchor:'right', dy:-6, text:() => rf.label, fill:C.ink3, fontSize:10.5, textAnchor:'end'})); } });
  if (fct){ opt.fy = undefined; }
  return Plot.plot({...base, ...opt, color: color || undefined, marks});
}

function tableOf(spec){
  const rows = spec.rows || []; if (!rows.length) return '<p>No rows.</p>';
  const keys = Object.keys(rows[0]).filter(k => !k.startsWith('_'));
  const esc = v => String(v == null ? '' : v).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  return '<table><thead><tr>' + keys.map(k => `<th${typeof rows[0][k] === 'number' ? ' class="n"' : ''}>${esc(k)}</th>`).join('') + '</tr></thead><tbody>' +
    rows.map(r => '<tr>' + keys.map(k => `<td${typeof r[k] === 'number' ? ' class="n"' : ''}>${esc(typeof r[k] === 'number' ? fmt(r[k]) : r[k])}</td>`).join('') + '</tr>').join('') + '</tbody></table>';
}

function render(el){
  const spec = BYID[el.dataset.fig]; if (!spec) { el.remove(); return; }
  const plot = el.querySelector('.plot'); if (!plot) return;
  const w = Math.max(280, Math.floor(plot.clientWidth || el.clientWidth - 32));
  if (el._w === w && el._theme === document.documentElement.dataset.theme + matchMedia('(prefers-color-scheme: dark)').matches) return;
  el._w = w; el._theme = document.documentElement.dataset.theme + matchMedia('(prefers-color-scheme: dark)').matches;
  plot.innerHTML = '';
  if (spec.form === 'table' || typeof Plot === 'undefined'){ plot.innerHTML = '<div class="tbl">' + tableOf(spec) + '</div>'; return; }
  try {
    const fv = spec.facet ? [...new Set((spec.rows || []).map(r => r[spec.facet]))] : [];
    if (fv.length > 1 && fv.length <= 6){
      // one small panel per facet value, same scales' domains for the categories
      for (const v of fv){
        const h = document.createElement('div'); h.className = 'facet-h'; h.textContent = v; plot.appendChild(h);
        const sub = Object.assign({}, spec, {rows: spec.rows.filter(r => r[spec.facet] === v), facet: null,
                                              seriesOrder: spec.series ? [...new Set(spec.rows.map(r => r[spec.series]))] : undefined});
        const node = build(sub, w); if (node){ node.setAttribute('role','img'); node.setAttribute('aria-label', (spec.title || '') + ' — ' + v); plot.appendChild(node); }
      }
    } else {
      const node = build(spec, w); if (node){ node.setAttribute('role','img'); node.setAttribute('aria-label', spec.title || ''); plot.appendChild(node); } else plot.innerHTML = '<div class="tbl">' + tableOf(spec) + '</div>';
    }
  }
  catch(e){ el.classList.add('err'); plot.innerHTML = '<div class="tbl">' + tableOf(spec) + '</div>'; console.warn('figure', spec.id, e); }
}
const all = () => document.querySelectorAll('.fig[data-fig]');
function renderAll(force){ all().forEach(el => { if (force) el._w = 0; render(el); }); }
if (typeof ResizeObserver !== 'undefined'){ const ro = new ResizeObserver(es => es.forEach(e => render(e.target.closest('.fig')))); all().forEach(el => ro.observe(el.querySelector('.plot') || el)); }
renderAll(true);
try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => renderAll(true));
      new MutationObserver(() => renderAll(true)).observe(document.documentElement, {attributes:true, attributeFilter:['data-theme']}); } catch(e){}

/* open items filter */
const bar = document.querySelector('.oi-bar');
if (bar){
  const items = [...document.querySelectorAll('.oi')];
  let pr = 'all';
  bar.addEventListener('click', ev => { const b = ev.target.closest('button'); if (!b) return;
    pr = b.dataset.p; bar.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
    items.forEach(it => { it.hidden = !(pr === 'all' || it.dataset.p === pr); });
    document.querySelectorAll('.oi-cat').forEach(c => { c.hidden = !c.querySelector('.oi:not([hidden])'); });
  });
}
/* toc highlight */
const links = [...document.querySelectorAll('nav.toc a')]; const map = new Map(links.map(a => [a.getAttribute('href').slice(1), a]));
if ('IntersectionObserver' in window){ const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting){ links.forEach(a => a.classList.remove('on')); const a = map.get(e.target.id); if (a) a.classList.add('on'); } }), {rootMargin:'-10% 0px -80% 0px'});
  document.querySelectorAll('section.sec[id], .subsec[id]').forEach(s => io.observe(s)); }
})();
