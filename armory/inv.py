import json,csv,glob,struct,sys,os
S=sys.argv[1]; T=S+'/txt105/' if os.path.isdir(S+'/txt105') else glob.glob('/root/.cargo/registry/src/*/d2s-0.1.1/data/txt/105/')[0]
def tsv(f): return list(csv.DictReader(open(T+f,encoding='latin-1'),delimiter='\t'))
base={}
for f,kind in (('weapons.txt','weapon'),('armor.txt','armor'),('misc.txt','misc')):
    for r in tsv(f):
        if r.get('code'): base[r['code']]=dict(name=r['name'],kind=kind,type=r.get('type',''),req=r.get('levelreq',''),tier=('elite' if r.get('code')==r.get('ultracode') else 'exc' if r.get('code')==r.get('ubercode') else 'norm') if kind!='misc' else '')
isc={int(r['*ID']):r['Stat'] for r in tsv('itemstatcost.txt') if r.get('*ID','').isdigit()}
X=S+'/xl/'
def xr(f): return list(csv.DictReader(open(X+f,encoding='latin-1'),delimiter='\t'))
U={int(v['*ID']):v['index'] for v in xr('uniqueitems.txt') if v.get('*ID','').isdigit()}
SI={int(v['*ID']):(v['index'],v.get('set','')) for v in xr('setitems.txt') if v.get('*ID','').isdigit()}
RWT={}
for v in xr('runes.txt'):
    if v.get('complete')!='1': continue
    rs=tuple(v.get(f'Rune{i}') for i in range(1,7) if v.get(f'Rune{i}'))
    RWT.setdefault(rs,[]).append(v['*Rune Name'])
RW={k:v[0] for k,v in RWT.items()}
def code(c): return struct.pack('<I',c).decode('latin-1').strip()
def stats(st): return [ (isc.get(s['id'],str(s['id'])), s['layer'], s['value']) for s in st]
out=[]
def walk(it,loc):
    c=code(it['code']); b=base.get(c,dict(name=c,kind='?',type='',req='',tier=''))
    q=it['quality']; qd=it.get('quality_data') or {}; nm=b['name']; extra=''
    if q=='Unique' and 'SetUnique' in qd: nm=U.get(qd['SetUnique']['file_index'],nm); nm={'Unique Warlock Helm':"Hellwarden's Will"}.get(nm,nm)
    if q=='Set' and 'SetUnique' in qd: nm,extra=SI.get(qd['SetUnique']['file_index'],(nm,''))
    socks=[code(s['code']) for s in it.get('sockets',[]) if s]
    rw=RWT.get(tuple(socks)) if it.get('runeword_id') is not None else None
    if rw: rw=next((n for n in rw if ('weapon' in n)==(b['kind']=='weapon') ), rw[0]) if len(rw)>1 else rw[0]
    out.append(dict(loc=loc,code=c,base=b['name'],kind=b['kind'],type=b['type'],tier=b['tier'],quality=q,name=rw or nm,set=extra,
        runeword=rw,eth='ETHEREAL' in it['flags'],socketed=socks,nsock=sum(1 for s in it['stats'] if False),qty=it.get('quantity'),
        ilvl=it['level'],defense=it.get('defense'),stats=stats(it['stats'])+stats(it.get('runeword_stats') or []),
        pos=it['position']))
# every saves/<Name>.json except the shared stash (char.json is a legacy duplicate of Blizzaga)
CH=[(os.path.basename(f)[:-5],)*2 for f in sorted(glob.glob(S+'/saves/*.json')) if os.path.basename(f) not in ('stash.json','char.json')]
for CN,CF in CH:
  d=json.load(open(S+f'/saves/{CF}.json'))
  for it in d['items']:
    p=it['position']; loc={'Equipped':CN+':equipped','InBelt':CN+':belt'}.get(p['mode'],CN+':'+str(p['store_page']).lower())
    walk(it,loc)
  mi=d.get('merc_items') or {}
  for it in (mi.get('items',[]) if isinstance(mi,dict) else mi) or []:
    if isinstance(it,dict) and 'code' in it: walk(it,CN+' merc:equipped')
st=json.load(open(S+'/saves/stash.json'))
for n,tab in enumerate(st,1):
    for it in tab['items']: walk(it,f'Shared:tab{n}' + ('' if tab['tab_type']=='Normal' else f"({tab['tab_type']})"))
json.dump(out,open(S+'/inventory.json','w'))
from collections import Counter
print(len(out),Counter(o['loc'] for o in out)); print(Counter(o['quality'] for o in out))
print([ (t['tab_type'],t['gold']) for t in st]); print('merc keys', list(mi.keys()) if isinstance(mi,dict) else type(mi))
