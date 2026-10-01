#!/bin/bash
# shot.sh page.html out.png WIDTHxHEIGHT  -> screenshot + diag dump
C="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$C" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files --virtual-time-budget=4000 --window-size=${3:-1100,2400} --screenshot="$2" "file://$1" >/dev/null 2>&1
"$C" --headless=new --disable-gpu --allow-file-access-from-files --virtual-time-budget=4000 --window-size=${3:-1100,2400} --dump-dom "file://$1" 2>/dev/null | python3 -c "import sys,re,html;d=sys.stdin.read();m=re.search(r'<pre id=\"diag\">(.*?)</pre>',d,re.S);print(html.unescape(m.group(1)) if m else 'NO DIAG')"
