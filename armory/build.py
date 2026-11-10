"""Finish a scan: merge chron.json into pagedata.json, work out what changed since the
previous snapshot (prev.json), and write armory_built.html from armory.html.
Run from the scan folder after inv.py, gen.py and chron.py."""
import json, os, time, collections
D = json.load(open('pagedata.json'))
prev = json.load(open('prev.json')) if os.path.exists('prev.json') else {}
ch = json.load(open('chron.json')) if os.path.exists('chron.json') else None
if ch:
  if ch.get('unk'): print('WARNING chronicle ids not decoded:', ch['unk'])
  D['chron'] = {k: ch.get(k, []) for k in ('u', 's', 'rw', 'rwn', 'mu', 'ms', 'mug', 'msg', 'fug', 'fsg')}

# ---- what changed: only recomputed when the saves actually changed ----
if prev and prev.get('snap') and prev.get('snap') != D.get('snap'):
  sig = lambda i: (i['n'], i['b'], i['q'], i.get('il'), i.get('e'))
  before = collections.Counter(sig(i) for i in prev.get('items', []))
  new = []
  for ix, i in enumerate(D['items']):
    k = sig(i)
    if before[k] > 0: before[k] -= 1
    else: new.append(ix)
  runes = {r: D['runes'][r] - prev.get('runes', {}).get(r, 0) for r in D['runes'] if D['runes'][r] != prev.get('runes', {}).get(r, 0)}
  pc, nc = prev.get('chron', {}), D.get('chron', {})
  found = lambda key: sorted(set(pc.get(key, [])) - set(nc.get(key, [])))
  D['delta'] = dict(since=prev.get('snap'), items=new, runes=runes, u=found('mu'), s=found('ms'),
                    rw=sorted(set(nc.get('rw', [])) - set(pc.get('rw', []))))
elif prev.get('delta') and 'delta' not in D:
  D['delta'] = prev['delta']
D['built'] = int(time.time() * 1000)
json.dump(D, open('pagedata.json', 'w'), separators=(',', ':'))
data = json.dumps(D, separators=(',', ':')).replace('</', '<\\/')
html = open('armory.html', encoding='utf-8').read().replace('__DATA__', data, 1)
open('armory_built.html', 'w', encoding='utf-8').write(html)
d = D.get('delta') or {}
print(f"built armory_built.html ({len(html)//1024} KB) · {len(D['items'])} items · chronicle U {D['chron']['u'][0]}/{D['chron']['u'][1]} "
      f"S {D['chron']['s'][0]}/{D['chron']['s'][1]} RW {len(D['chron']['rw'])}/{D['chron']['rwn']} · new items {len(d.get('items', []))}")
