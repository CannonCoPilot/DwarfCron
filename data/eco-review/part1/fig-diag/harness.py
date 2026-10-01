#!/usr/bin/env python3
"""Mini page with selected figures, rendered by the template's own renderer, local d3/Plot.
usage: harness.py OUT.html [--width W] fid1 fid2 ...   (reads ./scripts/eco-report, ./data/eco-report)"""
import json, sys, re
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H / "scripts/eco-report"))
import build
args = sys.argv[1:]; out = args.pop(0); width = None; full = False
if args and args[0] == "--width": args.pop(0); width = int(args.pop(0))
if args and args[0] == "--full": args.pop(0); full = True
exp, raws = build.load("experiments.json"), build.load("raws.json")
figs = list(exp["figures"])
for f in raws.get("figures", []): figs.extend(build.normalize_raw(f))
byid = {f["id"]: f for f in figs}
sel = [byid[i] for i in args]
cards = "".join(build.fig_card(f) for f in sel)
if full: cards = cards.replace('class="fig"', 'class="fig figwide"')
tpl = (H / "scripts/eco-report/template.html").read_text()
tpl = tpl.replace("https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js", str(H / "lib/d3.min.js"))
tpl = tpl.replace("https://cdn.jsdelivr.net/npm/@observablehq/plot@0.6.16/dist/plot.umd.min.js", str(H / "lib/plot.umd.min.js"))
tpl = re.sub(r'<link rel="(preconnect|stylesheet)"[^>]*>', '', tpl)
style = f'<style>main{{max-width:{width}px}}</style>' if width else ''
page = (tpl.replace("{{TOC}}", "").replace("{{CONTENT}}", style + '<div class="figs" style="display:grid;gap:16px">' + cards + '</div>')
        .replace("{{FIGS}}", json.dumps(sel).replace("</", "<\\/")).replace("{{OPEN}}", "{}"))
page += """<script>setTimeout(()=>{const o=[];document.querySelectorAll('.fig').forEach(el=>{const sv=el.querySelector('.plot svg');
o.push(el.dataset.fig+' err='+el.classList.contains('err')+' svgs='+el.querySelectorAll('.plot svg').length+' circles='+el.querySelectorAll('.plot circle').length+' rects='+el.querySelectorAll('.plot rect').length+' paths='+el.querySelectorAll('.plot path').length+' table='+!!el.querySelector('.plot table')+(sv?' w='+sv.getAttribute('width')+' h='+sv.getAttribute('height'):'')+' yticks='+[...el.querySelectorAll('[aria-label="y-axis tick label"] text')].map(t=>t.textContent).slice(0,12).join('|')+' xticks='+[...el.querySelectorAll('[aria-label="x-axis tick label"] text')].map(t=>t.textContent).slice(0,12).join('|'))});
const p=document.createElement('pre');p.id='diag';p.textContent=o.join('\\n');document.body.appendChild(p);},300);</script>"""
Path(out).write_text(page)
