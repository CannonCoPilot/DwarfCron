#!/usr/bin/env python3
"""Build the stand-alone mechanics report (rev 4, 8 Oct 2026) from the same fragments the ECO report includes:
data/eco-report/parts/{mech-overview,plan}.html and the code-review notes data/eco-report/mech/*.md.
Output: data/eco-report/mechanics.html (no figures; the ECO page's template and styles).

    python3 scripts/eco-report/mech_page.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402
import mechmd  # noqa: E402

DATA = build.DATA

HERO = """<header class="hero" id="top">
  <div style="display:grid;gap:14px">
    <span class="eyebrow">seasonal-wildlife · v7.2-plugin @ 8185d85 (every branch merged) · DF 53.16 · DFHack 53.16-r2 · 8 October 2026</span>
    <h1>How Seasonal Wildlife works: roster, season casts, rotation and the food web</h1>
    <p class="lede">A line-by-line reading of the merged code, layer by layer (land, flying, ocean, lake, river and brook, pools, caverns, the deep), with the problems that stand between the code and its design ranked in fix order, and the rig runs that will check each fix.</p>
  </div>
  <div class="meta">
    <div>Read from the source only: the engine (<code>scripts/seasonal-wildlife.lua</code>, 18,778 lines), the C++ plugin, the control registry, the window and the web server. Nothing here was run for this review; every claim names its function and line, and the full notes are folded under each section. The same sections appear in the <a href="https://claude.ai/artifact/UY2KevMooCW4mRr5F19M26">ECO Wildlife Study</a> (rev 4) beside the evidence they rest on.</div>
  </div>
</header>
"""


def main():
    content = HERO + "{{include:mech-overview}}\n{{include:plan}}"
    content = re.sub(r"\{\{include:([\w-]+)\}\}", lambda m: (DATA / "parts" / f"{m.group(1)}.html").read_text(), content)
    content = re.sub(r"\{\{mechmd:([\w-]+)\}\}", lambda m: '<div class="mechnote">'
                     + mechmd.convert((DATA / "mech" / f"{m.group(1)}.md").read_text()) + "</div>", content)
    footer = ("<footer>Built 8 Oct 2026 by <code>DwarfCron/scripts/eco-report/mech_page.py</code> from "
              "<code>data/eco-report/parts/</code> and <code>data/eco-report/mech/*.md</code>.</footer>")
    tpl = (HERE / "template.html").read_text().replace("<title>ECO Wildlife Study</title>", "<title>Seasonal Wildlife Mechanics</title>")
    page = (tpl.replace("{{TOC}}", build.toc_html(content)).replace("{{CONTENT}}", content + footer)
               .replace("{{FIGS}}", "[]").replace("{{OPEN}}", "{}"))
    out = DATA / "mechanics.html"
    out.write_text(page)
    print(f"wrote {out} ({len(page) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
