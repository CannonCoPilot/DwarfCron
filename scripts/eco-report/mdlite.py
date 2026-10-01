"""A minimal Markdown-to-HTML converter for the report's appendix: headings, paragraphs, bullet and numbered lists,
check lists, pipe tables, **bold**, *italic*, `code`, [links](url). Enough for the exported doc's text, nothing more."""
import html
import re


def inline(s):
    s = html.unescape(s).replace("\\_", "_").replace("\\<", "<").replace("\\*", "*").replace("\\|", "|").replace("\\[", "[").replace("\\]", "]")
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def convert(md):
    lines, out, i = md.splitlines(), [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip() or ln.startswith("&#91;embedded content"):
            i += 1; continue
        m = re.match(r"^(#{2,4}) (.*)", ln)
        if m:
            lvl = min(4, len(m.group(1)) + 1)
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>"); i += 1; continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split(" | ")]); i += 1
            head, body = rows[0], [r for r in rows[1:] if not set("".join(r)) <= set("-: ")]
            out.append('<div class="tbl"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table></div>")
            continue
        if re.match(r"^\s*([-*]|\d+\.) ", ln):
            ordered = bool(re.match(r"^\s*\d+\. ", ln))
            items = []
            while i < len(lines) and (re.match(r"^\s*([-*]|\d+\.) ", lines[i]) or (lines[i].startswith("   ") and lines[i].strip())):
                t = lines[i]
                if re.match(r"^\s*([-*]|\d+\.) ", t) and not t.startswith("   "):
                    items.append(re.sub(r"^\s*([-*]|\d+\.) (\[[ x]\] )?", "", t))
                else:
                    items[-1] += " " + re.sub(r"^\s*([-*]|\d+\.) ", "", t.strip())
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        para = [ln]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||\s*([-*]|\d+\.) )", lines[i]):
            para.append(lines[i]); i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)
