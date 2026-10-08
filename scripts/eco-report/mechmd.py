"""Markdown to HTML for the code-review notes in data/eco-report/mech/*.md (rev 4): mdlite's inline rules and tables,
plus nested lists by indentation, fenced code blocks, and the file's own title dropped (the report gives each a heading).
Headings shift down two levels (## -> h4) so the notes sit under the report's section headings."""
import html
import re

from mdlite import inline

LIST = re.compile(r"^(\s*)([-*]|\d+\.) (\[[ x]\] )?(.*)")


def _list(lines, i):
    """Parse a (possibly nested) list starting at lines[i]; returns (html, next index)."""
    base = len(LIST.match(lines[i]).group(1))
    ordered = bool(re.match(r"^\s*\d+\.", lines[i]))
    items = []
    while i < len(lines):
        ln = lines[i]
        m = LIST.match(ln)
        if m and len(m.group(1)) == base:
            items.append([inline(m.group(4)), ""]); i += 1
        elif m and len(m.group(1)) > base and items:
            sub, i = _list(lines, i); items[-1][1] += sub
        elif ln.strip() and not m and items and (len(ln) - len(ln.lstrip())) > base and not ln.lstrip().startswith("|"):
            items[-1][0] += " " + inline(ln.strip()); i += 1   # a wrapped continuation line
        else:
            break
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{a}{b}</li>" for a, b in items) + f"</{tag}>", i


def convert(md):
    lines, out, i = md.splitlines(), [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip() or re.match(r"^# ", ln) or re.match(r"^-{3,}\s*$", ln):
            i += 1; continue
        if ln.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>")
            i = j + 1; continue
        m = re.match(r"^(#{2,5}) (.*)", ln)
        if m:
            lvl = min(6, len(m.group(1)) + 2)
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>"); i += 1; continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in re.split(r"(?<!\\)\|", lines[i].strip().strip("|"))]); i += 1
            head, body = rows[0], [r for r in rows[1:] if not set("".join(r)) <= set("-: ")]
            out.append('<div class="tbl"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table></div>")
            continue
        if LIST.match(ln):
            h, i = _list(lines, i); out.append(h); continue
        para = [ln]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||```)", lines[i]) and not LIST.match(lines[i]):
            para.append(lines[i]); i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)
