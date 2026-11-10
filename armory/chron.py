import struct,csv,json,glob,sys
D=open(sys.argv[1],'rb').read(); m=D.rfind(b'\xc0\xed\xea\xc0')
ver,h1,h2,h3=struct.unpack('<HHHH',D[m+4:m+12]); p=m+14
R=[struct.unpack('<HII',D[p+10*i:p+10*i+10]) for i in range(h1+h2+h3)]
S=R[:h1];U=R[h1:h1+h2];W=R[h1+h2:]
xr=lambda f: list(csv.DictReader(open('xl/'+f,encoding='latin-1'),delimiter='\t'))
el=lambda v: v['*ID'].isdigit() and v.get('disableChronicle')!='1' and v.get('spawnable')=='1'
us=[v for v in xr('uniqueitems.txt') if el(v)]; ss=[v for v in xr('setitems.txt') if el(v)]
rws=[v for v in xr('runes.txt') if v['complete']=='1']
fs={r[2] for r in S if r[1]}; fu={r[2] for r in U if r[1]}
# runeword id -> name from owned items
RWT={}
for v in rws: RWT.setdefault(tuple(v.get(f'Rune{i}') for i in range(1,7) if v.get(f'Rune{i}')),[]).append(v['*Rune Name'])
code=lambda c: struct.pack('<I',c).decode('latin-1').strip()
idn={}
def walk(o):
  if isinstance(o,dict):
    if o.get('runeword_id') is not None:
      n=RWT.get(tuple(code(s['code']) for s in o.get('sockets',[]) if s))
      if n: idn.setdefault(o['runeword_id'],n)
    for v in o.values(): walk(v)
  elif isinstance(o,list): [walk(v) for v in o]
for f in glob.glob('saves/*.json'): walk(json.load(open(f)))
idn.setdefault(20519,['Call to Arms'])
RN={v['Name']:v['*Rune Name'] for v in rws}
def rwname(i):
  n=i-27189 if i>27000 else (i-20506 if i-20506<80 else i-20505)
  return RN.get(f'Runeword{n}')
rwf=[];unk=[]
for r in W:
  n=rwname(r[2])
  (rwf.append(n) if n else unk.append(r[2]))
for i,n in idn.items():
  if rwname(i) not in n: unk.append(('MISMATCH',i,n,rwname(i)))
names={v['*Rune Name'] for v in rws}

# group missing items for display: uniques by slot (with base name), set items by set
def tsv(p): return list(csv.DictReader(open(p,encoding='latin-1'),delimiter='\t'))
BASE={}
for f in ('weapons.txt','armor.txt','misc.txt'):
  for r in tsv('txt105/'+f):
    if r.get('code'): BASE[r['code']]=(r['name'],r.get('type',''))
EQ={r['Code']:[r.get('Equiv1',''),r.get('Equiv2','')] for r in tsv('txt105/itemtypes.txt') if r.get('Code')}
SLOT=[('ring','Rings'),('amul','Amulets'),('char','Charms'),('jewl','Jewels'),('helm','Helms'),('tors','Body armor'),('shld','Shields'),('glov','Gloves'),('boot','Boots'),('belt','Belts'),('weap','Weapons')]
def slot(t):
  seen,q=set(),[t]
  while q:
    x=q.pop(0)
    if not x or x in seen: continue
    seen.add(x); q+=EQ.get(x,[])
  return next((lab for k,lab in SLOT if k in seen),'Other')
mug=[[v['index'],slot(BASE.get(v.get('code',''),('',''))[1]),BASE.get(v.get('code',''),('',''))[0]] for v in us if int(v['*ID']) not in fu]
msg=[[v['index'],v.get('set','')] for v in ss if int(v['*ID']) not in fs]
fug=[[v['index'],slot(BASE.get(v.get('code',''),('',''))[1]),BASE.get(v.get('code',''),('',''))[0]] for v in us if int(v['*ID']) in fu]
fsg=[[v['index'],v.get('set','')] for v in ss if int(v['*ID']) in fs]
out=dict(mug=mug,msg=msg,fug=fug,fsg=fsg,u=[sum(int(v['*ID']) in fu for v in us),len(us)], s=[sum(int(v['*ID']) in fs for v in ss),len(ss)], rw=sorted(set(rwf)), rwn=len(rws),hust=[n for n in RN.values() if n.startswith('Hustle')], counts=[h1,h2,h3],
  mu=sorted(v['index'] for v in us if int(v['*ID']) not in fu), ms=sorted(v['index'] for v in ss if int(v['*ID']) not in fs), unk=unk)
print(json.dumps(out))
