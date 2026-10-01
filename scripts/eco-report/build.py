#!/usr/bin/env python3
"""Build the ECO report page: content.html (prose with {{fig:ID}}, {{gallery:SECTION}}, {{openitems}} markers)
+ data/eco-report/{experiments,raws,open-items}.json -> data/eco-report/eco-report.html (one self-contained page).

  python3 scripts/eco-report/build.py            # writes data/eco-report/eco-report.html, prints placement stats
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATA = ROOT / "data" / "eco-report"


def load(name):
    p = DATA / name
    return json.loads(p.read_text()) if p.exists() else {}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def table_html(rows, limit=200):
    if not rows:
        return ""
    keys = [k for k in rows[0].keys() if not str(k).startswith("_")]
    if len(rows) > limit:
        return f'<p class="fn">{len(rows):,} rows; the full set is in the data file.</p>'
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)
    head = "".join(f'<th{" class=n" if num(rows[0].get(k)) else ""}>{esc(k)}</th>' for k in keys)
    body = "".join("<tr>" + "".join(
        f'<td{" class=n" if num(r.get(k)) else ""}>{esc(r.get(k))}</td>' for k in keys) + "</tr>" for r in rows)
    return f'<div class="tbl"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def fig_card(f):
    cap = " · ".join(x for x in [f.get("caption"), f.get("notes")] if x)
    return (f'<figure class="fig" data-fig="{esc(f["id"])}" id="fig-{esc(f["id"])}">'
            f'<div class="ft">{esc(f.get("title"))}</div>'
            + (f'<div class="fs">{esc(f.get("subtitle"))}</div>' if f.get("subtitle") else "")
            + '<div class="plot"></div>'
            + (f'<div class="fc">{esc(cap)}</div>' if cap else "")
            + f'<details><summary>Data ({len(f.get("rows") or [])} rows)</summary>{table_html(f.get("rows") or [])}</details>'
            + '</figure>')


def _you(t):
    t = str(t or "")
    for a, b in (("Ask the user for the rule", "Decide the rule"), ("Ask the user;", "Your call;"), ("Ask the user", "Your call"),
                 ("Get the user's choice", "Your choice"), ("the user's", "your"), ("The user's", "Your"),
                 ("the user", "you"), ("The user", "You"),
                 ("eco-report.md (scratchpad export, 1 Oct)", "doc rev 326"), ("/Users/nathanielcannon/Claude/Projects/", "")):
        t = t.replace(a, b)
    return t


def open_items_html(oi):
    for i in oi.get("items") or []:
        for k in ("title", "detail", "next"):
            i[k] = _you(i.get(k))
        src = i.get("source") or []
        i["source"] = [_you(x) for x in (src if isinstance(src, list) else [src])]
    cats = oi.get("categories") or []
    items = oi.get("items") or []
    order = {"high": 0, "medium": 1, "low": 2}
    out = ['<div class="oi-bar" role="group" aria-label="Filter by priority">'
           '<span style="color:var(--ink3)">Show</span>'
           '<button type="button" data-p="all" aria-pressed="true">All</button>'
           '<button type="button" data-p="high" aria-pressed="false">High</button>'
           '<button type="button" data-p="medium" aria-pressed="false">Medium</button>'
           '<button type="button" data-p="low" aria-pressed="false">Low</button></div>']
    for c in cats:
        its = sorted([i for i in items if i.get("category") == c["id"]], key=lambda i: order.get(i.get("priority"), 3))
        if not its:
            continue
        out.append(f'<div class="oi-cat" id="oi-{esc(c["id"])}"><h3>{esc(c["title"])}<span class="count">{len(its)}</span></h3><div class="oi-grid">')
        for i in its:
            src = i.get("source") or []
            src = src if isinstance(src, list) else [src]
            out.append(
                f'<article class="oi" data-p="{esc(i.get("priority","low"))}">'
                f'<div class="h"><span class="t">{esc(i.get("title"))}</span>'
                f'<span class="chip {esc(i.get("priority","low"))}">{esc(i.get("priority",""))}</span></div>'
                f'<p class="d">{esc(i.get("detail"))}</p>'
                + (f'<div class="nx"><b>Next:</b> {esc(i.get("next"))}</div>' if i.get("next") else "")
                + f'<div class="src">{esc(i.get("status",""))}{" · effort " + esc(i.get("effort")) if i.get("effort") else ""}'
                + (f' · {esc("; ".join(map(str, src[:3])))}' if src else "") + '</div></article>')
        out.append('</div></div>')
    return "\n".join(out)


def toc_html(content):
    # sections: <section class="sec" id="X" data-toc="Label">; subsections: <div class="subsec" id="Y" data-toc="Label">
    out, cur = ["<ol>"], None
    for m in re.finditer(r'<(section|div) class="(sec|subsec)[^"]*" id="([^"]+)" data-toc="([^"]+)"', content):
        tag, kind, sid, label = m.groups()
        if kind == "sec":
            if cur:
                out.append("</ol></li>" if cur == "open-sub" else "</li>")
            out.append(f'<li><a href="#{sid}">{esc(label)}</a>')
            cur = "sec"
        else:
            if cur == "sec":
                out.append("<ol>")
                cur = "open-sub"
            out.append(f'<li><a href="#{sid}">{esc(label)}</a></li>')
    if cur:
        out.append("</ol></li>" if cur == "open-sub" else "</li>")
    out.append("</ol>")
    return "".join(out)


GUILD_ORDER = ["AL", "AW", "RP", "ML", "MW", "GZ", "PL", "SH", "PE", "FC", "FF", "WB", "LB", "VG", "VC", "VI", "VB", "VF"]


def median(xs):
    xs = sorted(x for x in xs if isinstance(x, (int, float)))
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def normalize_raw(f):
    """Adapt the raws agent's specs to the page renderer: split facets into separate figures, count per-species rows,
    aggregate per-species ranges to per-guild medians, turn shares into percents, and add guild ordering."""
    out = []
    rows = f.get("rows") or []
    base = {k: v for k, v in f.items() if k != "rows"}
    base["id"] = "raw-" + str(f["id"])
    base["section"] = "raws"
    for rl in f.get("refLines") or []:
        base.setdefault("reference", []).append({"value": rl["y"], "label": rl["label"]})
    base.pop("refLines", None)

    def guild_order(spec, rs):
        if spec.get("x") == "guild":
            present = {r.get("guild") for r in rs}
            spec["categoryOrder"] = [g for g in GUILD_ORDER if g in present] + sorted(p for p in present if p not in GUILD_ORDER and p)
        return spec
    fid = str(f["id"])
    if f["form"] == "heatmap":
        b = dict(base, value="pct", valueLabel="share of the guild", unit="%")
        b["rows"] = [dict(r, pct=round(100 * r["share"], 1)) for r in rows]
        b["yOrder"] = [g for g in GUILD_ORDER if g in {r["guild"] for r in rows}]
        b.pop("series", None)
        out.append(b)
    elif fid in ("6", "13"):
        key = "dimension" if fid == "6" else "panel"
        for i, val in enumerate(dict.fromkeys(r[key] for r in rows)):
            sub = [r for r in rows if r[key] == val]
            b = dict(base, id=f"{base['id']}-{i+1}", form="bar", x="category", y="count", series=None,
                     title=(base["title"] if i == 0 else f"{val[:1].upper()}{val[1:]}"), subtitle=f"{val}" + (f" · {base.get('subtitle')}" if i == 0 and base.get("subtitle") else ""))
            if all("count" in r for r in sub):
                b["rows"] = [{"category": r["category"], "count": r["count"]} for r in sub]
            else:   # a per-species panel: list it as a table instead of a duplicate count chart
                b.update(form="table", title=f"{val[:1].upper()}{val[1:]}: the list")
                b["rows"] = [{k: v for k, v in r.items() if k != key} for r in sub]
            out.append(b)
    elif fid == "9":
        c = {}
        for r in rows:
            k = (r["locomotion"], r["layer"])
            c[k] = c.get(k, 0) + 1
        b = dict(base, form="stackedBar", x="locomotion", y="count", series="layer")
        b["rows"] = [{"locomotion": k[0], "layer": k[1], "count": v} for k, v in c.items()]
        out.append(b)
        t = dict(base, id=base["id"] + "-list", form="table", title="The 90 species the scavenging rule accepts", subtitle="guild, layer, locomotion and why each qualifies")
        t["rows"] = [{"species": r["id"], "guild": r["guild"], "layer": r["layer"], "moves": r["locomotion"], "why": r["why"]} for r in rows]
        out.append(t)
    elif fid == "4":
        for i, meas in enumerate(dict.fromkeys(r["measure"] for r in rows)):
            g = {}
            for r in rows:
                if r["measure"] == meas:
                    g.setdefault(r["guild"], []).append(r)
            agg = [{"guild": k, "lo": median([r["min"] for r in v]), "hi": median([r["max"] for r in v]), "species": len(v)} for k, v in g.items()]
            b = dict(base, id=f"{base['id']}-{i+1}", form="range", x="guild", lo="lo", hi="hi", y=None, series=None,
                     yLabel=f"{meas}, median min to median max", title=(base["title"] if i == 0 else f"{meas}: what DF draws per population, by guild"),
                     subtitle=f"{meas} · median of each species' min and max")
            b["rows"] = agg
            out.append(guild_order(b, agg))
    elif fid == "15c":
        g = {}
        for r in rows:
            g.setdefault(r["guild"], []).append(r)
        agg = [{"guild": k, "lo": median([r["clutch_min"] for r in v]), "hi": median([r["clutch_max"] for r in v]), "species": len(v)} for k, v in g.items()]
        b = dict(base, form="range", x="guild", lo="lo", hi="hi", y=None, yLabel="eggs per clutch, median min to max", series=None, log=False)
        b["rows"] = agg
        out.append(guild_order(b, agg))
    elif f["form"] == "dot" and len(rows) > 60:
        b = dict(base, form="strip")
        b["rows"] = rows
        out.append(guild_order(b, rows))
    elif fid == "10":
        for i, mode in enumerate(["WALK", "FLY", "SWIM"]):
            sub = [r for r in rows if r["mode"] == mode]
            b = dict(base, id=f"{base['id']}-{mode.lower()}", title=(base["title"] if i == 0 else f"{mode.title()}: top speed against mass"), subtitle=f"{mode.lower()} gait · ticks per 100 tiles, lower is faster")
            b["rows"] = sub
            out.append(b)
    else:
        b = dict(base)
        b["rows"] = rows
        out.append(guild_order(b, rows))
    return out


def main():
    exp, raws, oi = load("experiments.json"), load("raws.json"), load("open-items.json")
    figs = []
    for f in exp.get("figures", []):
        f.setdefault("section", "other")
        figs.append(f)
    for f in raws.get("figures", []):
        figs.extend(normalize_raw(f))
    extra = DATA / "extra-figures.json"
    if extra.exists():
        for f in json.loads(extra.read_text()).get("figures", []):
            figs.append(f)
    byid = {}
    for f in figs:
        if f["id"] in byid:
            f["id"] = f["id"] + "-2"
        byid[f["id"]] = f
    content = (HERE / "content.html").read_text()
    placed = set()

    def put(m):
        fid = m.group(1)
        if fid not in byid:
            print(f"  ! missing figure {fid}", file=sys.stderr)
            return ""
        placed.add(fid)
        return fig_card(byid[fid])
    content = re.sub(r"\{\{fig:([\w.\-]+)\}\}", put, content)

    def gallery(m):
        sec, cls = m.group(1), (m.group(2) or "").strip()
        limit = None
        if cls and cls.split()[-1].isdigit():
            limit = int(cls.split()[-1]); cls = " ".join(cls.split()[:-1])
        rest = [f for f in figs if (f["section"] == sec or f["section"].startswith(sec + ":")) and f["id"] not in placed]
        if limit is not None:
            rest = rest[:limit]
        for f in rest:
            placed.add(f["id"])
        if not rest:
            return ""
        return f'<div class="gallery {esc(cls)}">' + "".join(fig_card(f) for f in rest) + "</div>"
    content = re.sub(r"\{\{gallery:([\w:\-]+)( [\w ]+)?\}\}", gallery, content)
    sys.path.insert(0, str(HERE))
    import appendix, recs
    content = content.replace("{{openitems}}", open_items_html(oi))
    content = content.replace("{{rectable}}", recs.table()).replace("{{appendix}}", appendix.build())
    blocks = set()
    for f in exp.get("figures", []):
        for t in re.split(r"[,/+ ]+", f.get("block", "")):
            if re.match(r"^[A-Z][A-Za-z0-9_\-]*$", t.strip()) and t.strip() not in ("CTRL", "BOATS", "BUILDER", "T0", "VALIDATE"):
                blocks.add(t.strip())
    content = content.replace("{{blockcount}}", str(len(blocks)))
    open_n = sum(1 for i in (oi.get("items") or []) if i.get("status") != "done")   # done items show, but are not open
    content = content.replace("{{oicount}}", str(open_n))
    content = content.replace("{{figcount}}", str(len(placed)))
    unplaced = [f["id"] for f in figs if f["id"] not in placed]
    if unplaced:
        print(f"  unplaced figures ({len(unplaced)}): {', '.join(unplaced)}", file=sys.stderr)
    used = [byid[i] for i in placed]
    tpl = (HERE / "template.html").read_text()
    page = (tpl.replace("{{TOC}}", toc_html(content)).replace("{{CONTENT}}", content)
               .replace("{{FIGS}}", json.dumps(used, separators=(",", ":")).replace("</", "<\\/"))
               .replace("{{OPEN}}", "{}"))
    out = DATA / "eco-report.html"
    out.write_text(page)
    print(f"wrote {out} ({len(page)/1024:.0f} KB): {len(placed)} figures placed, {len(unplaced)} unplaced, "
          f"{open_n} open items ({len(oi.get('items') or [])} listed)")


if __name__ == "__main__":
    main()
