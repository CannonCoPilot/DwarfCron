"""Build water-graphics-v2.html from water-graphics-v2.src.html.

{{CHECKLIST}} <- checklist.part.html; {{IMG:path}} <- data URI of aquarium-run/sampler/<path>;
{{VARIANTS}} <- aquarium-run/sampler/out/meta.json with each variant's out/<id>.png inlined as 'src'.
Usage: python3 build_water_page.py
"""
import base64, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLER = os.path.join(HERE, '..', 'aquarium-run', 'sampler')

def uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif'}[ext]
    return 'data:%s;base64,%s' % (mime, base64.b64encode(open(path, 'rb').read()).decode())

s = open(os.path.join(HERE, 'water-graphics-v2.src.html')).read()
s = s.replace('{{CHECKLIST}}', open(os.path.join(HERE, 'checklist.part.html')).read())
s = re.sub(r'\{\{IMG:([^}]+)\}\}', lambda m: uri(os.path.join(SAMPLER, m.group(1))), s)
meta = json.load(open(os.path.join(SAMPLER, 'out', 'meta.json')))
for v in meta:
    v['src'] = uri(os.path.join(SAMPLER, 'out', v['id'] + '.png'))
s = s.replace('{{VARIANTS}}', json.dumps(meta))
assert '{{' not in s, re.findall(r'\{\{[^}]*\}\}', s)[:5]
open(os.path.join(HERE, 'water-graphics-v2.html'), 'w').write(s)
print('wrote water-graphics-v2.html', len(s), 'bytes')
