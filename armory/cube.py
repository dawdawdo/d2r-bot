import csv,re,sys,html
src=sys.argv[1]
r=[x for x in csv.DictReader(open(src),delimiter='\t') if x['enabled']=='1']
e=html.escape
def clean(s): return re.sub(r'\s+',' ',s).strip()
groups={k:[] for k in ['Runes','Gems','Sockets & upgrades','Rerolls & rares','Repair & recharge','Reign of the Warlock','Portals & quests','Potions & misc']}
craft={}
for x in r:
  d=clean(x['description']); a,b=[clean(t) for t in d.split('->')]
  a=re.sub(r'Uber Ancient Summon Material ?(?:from )?Act ?(\d)',r'Act \1 Ancient statue',a).replace('1 Act 1 Ancient statue + Act2 + Act3 + Act 4 + Act 5','All 5 Ancient statues (Acts 1–5)')
  m=re.match(r'1 Magic (.+?) \+ 1 Jewel \+ (?:1 )?(\w+) Rune \+ 1 Perfect (\w+)$',a)
  if m:
    kind,slot=b.rsplit(' ',1); craft.setdefault(slot,{})[kind]=(m[1],m[2]); craft.setdefault('_gem',{})[kind]=m[3]; continue
  note=''
  if x['firstLadderSeason']: note='Ladder (works offline)'
  if x['min diff']=='2': note='Hell only'
  if 'Portal' in b or "Khalim" in b or 'Horadric' in b: g='Portals & quests'
  elif 'Ancient' in a or 'Token' in b: g='Reign of the Warlock'
  elif b.endswith('Rune'): g='Runes'
  elif re.search(r'(Amethyst|Ruby|Rubies|Sapphire|Topaz|Emerald|Diamond|Skull)s?$',b) and 'Magic' not in a: g='Gems'
  elif 'Repaired' in b: g='Repair & recharge'
  elif 'Rare' in b or 'Re-rolled' in b: g='Rerolls & rares'
  elif 'Socket' in b or 'Exceptional' in b or 'Elite' in b or 'Normal ' in b: g='Sockets & upgrades'
  else: g='Potions & misc'
  groups[g].append((a,b,note))
if 'Ancient' in str(groups): pass
groups['Reign of the Warlock'].insert(0,('Latent Sunder charm (Herald drop) + matching recipe below','Upgraded Sunder charm',''))
groups['Reign of the Warlock'].pop(0)  # keep data-only
def rows(items):
  return ''.join(f'<tr><td>{e(a)}</td><td><b>{e(b)}</b>{f" <span class=chip>{e(n)}</span>" if n else ""}</td></tr>' for a,b,n in items)
# compact gem table: one row per gem type
out=['<section id="v-ref" hidden>','<p class="lede">Horadric Cube recipes from the 3.0 game tables (cubemain.txt). Type to filter, e.g. <span class="mono">Ber</span>, <span class="mono">socket</span>, <span class="mono">Ral</span>.</p>',
'<div class="note"><b>Quick answer · lowest-requirement Call to Arms base:</b> a <b>War Staff</b> has no Str/Dex requirement, but Larzuk gives it 6 sockets, so it needs a natural 5-socket drop. The lowest you can make with Larzuk is a <b>Long Bow</b> (22 Str / 19 Dex, item level 41+ gets exactly 5). Lowest one-hander: <b>Double Axe</b> (43 Str, 5 from Larzuk). Your plan’s Flail (41 Str / 35 Dex) works too. Call to Arms itself needs level 57.</div>',
'<div class="filters"><input type="search" id="cq" placeholder="Filter recipes…" aria-label="Filter cube recipes"><span class="small" id="ccnt"></span></div>']
for g,items in groups.items():
  if not items: continue
  if g=='Gems':
    items=[i for i in items]
  if g=='Gems': continue
  out.append(f'<h2 class="cg">{e(g)}</h2><div class="tbl cg"><table class="cube"><thead><tr><th>Put in</th><th>Get</th></tr></thead><tbody>{rows(items)}</tbody></table></div>')
gem=craft.pop('_gem'); kinds=['Hit Power','Blood','Caster','Safety']
hdr=''.join(f'<th>{k}<br><span class="small">Perfect {gem[k]}</span></th>' for k in kinds)
body=''.join('<tr><td><b>'+e(s)+'</b></td>'+''.join(f'<td>{e(craft[s][k][0])} <span class="rw-runes">+ {e(craft[s][k][1])}</span></td>' if k in craft[s] else '<td></td>' for k in kinds)+'</tr>' for s in ['Helm','Body','Shield','Gloves','Boots','Belt','Amulet','Ring','Weapon'])
out.append(f'<h2 class="cg">Crafting</h2><p class="lede cg">Each craft = magic base + jewel + rune + the column’s perfect gem.</p><div class="tbl cg"><table class="cube craft"><thead><tr><th>Slot</th>{hdr}</tr></thead><tbody>{body}</tbody></table></div>')
out.append('</section>')
print('\n'.join(out))
