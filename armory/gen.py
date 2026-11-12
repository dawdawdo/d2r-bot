"""inventory.json + saves/*.json -> pagedata.json (items, runes, gems, mats, chars, snap).
Keeps rwdb / farm text from the previous pagedata.json. Run from the scan folder (needs xl/skills.txt)."""
import json, struct, csv, glob, os
o = json.load(open('inventory.json')); st = json.load(open('saves/stash.json')); old = json.load(open('pagedata.json'))
c = lambda x: struct.pack('<I', x).decode('latin-1').strip()
RUNES = "El Eld Tir Nef Eth Ith Tal Ral Ort Thul Amn Sol Shael Dol Hel Io Lum Ko Fal Lem Pul Um Mal Ist Gul Vex Ohm Lo Sur Ber Jah Cham Zod".split()
MATS = ('mbr','dhn','bey','pk1','pk2','pk3','toa','tes','ceh','bet','fed','ua1','ua2','ua3','ua4','ua5','xa1','xa2','xa3','xa4','xa5','rvl')
GEMP = ('gc','gf','gs','gl','gz','gp')
GEMN = {'v':'Amethyst','y':'Topaz','b':'Sapphire','r':'Ruby','g':'Emerald','w':'Diamond'}
GRADE = {'gc':'Chipped ','gf':'Flawed ','gs':'','gl':'Flawless ','gz':'Flawless ','gp':'Perfect '}
SK = {int(r['*Id']): r['skill'] for r in csv.DictReader(open('xl/skills.txt', encoding='latin-1'), delimiter='\t') if r.get('*Id','').isdigit()}
runes = {r: 0 for r in RUNES}; gems = {}; mats = {}
for t in st:
  for it in t['items']:
    k = c(it['code']); n = it.get('advanced_stash_stack_size'); n = 1 if n is None else n
    if k[0] == 'r' and k[1:].isdigit(): runes[RUNES[int(k[1:]) - 1]] += n
    elif k[:2] in GEMP and k[2:] in GEMN: gems[k] = gems.get(k, 0) + n
    elif k in MATS: mats[k] = mats.get(k, 0) + n
for x in o:
  if x['loc'].startswith('Shared'): continue
  if x['type'] == 'rune': runes[x['name'].replace(' Rune', '')] += 1
  elif x['code'][:2] in GEMP and x['code'][2:] in GEMN: gems[x['code']] = gems.get(x['code'], 0) + 1
  elif x['code'] in MATS: mats[x['code']] = mats.get(x['code'], 0) + 1

# ---------- readable stat lines ----------
CLS = ['Amazon','Sorceress','Necromancer','Paladin','Barbarian','Druid','Assassin','Warlock']
TABN = {0:'Bow',1:'Passive & Magic',2:'Javelin & Spear',8:'Fire',9:'Lightning',10:'Cold',16:'Curses',17:'Poison & Bone',18:'Summoning',
        24:'Combat (Paladin)',25:'Offensive Auras',26:'Defensive Auras',32:'Combat (Barbarian)',33:'Masteries',34:'Warcries',
        40:'Summoning (Druid)',41:'Shape Shifting',42:'Elemental',48:'Traps',49:'Shadow Disciplines',50:'Martial Arts'}
ELEM = {1:'fire',2:'lightning',3:'cold',4:'poison',5:'magic'}
T = {  # stat -> template ({v} value). None = hide (base-item noise)
 'strength':'+{v} Strength','dexterity':'+{v} Dexterity','vitality':'+{v} Vitality','energy':'+{v} Energy',
 'maxhp':'+{v} Life','maxmana':'+{v} Mana','item_maxhp_percent':'+{v}% max Life','item_maxmana_percent':'+{v}% max Mana',
 'fireresist':'Fire res +{v}%','coldresist':'Cold res +{v}%','lightresist':'Lightning res +{v}%','poisonresist':'Poison res +{v}%','magicresist':'Magic res +{v}%',
 'maxfireresist':'+{v}% max Fire res','maxcoldresist':'+{v}% max Cold res','maxlightresist':'+{v}% max Lightning res','maxpoisonresist':'+{v}% max Poison res',
 'item_magicbonus':'{v}% Magic Find','item_goldbonus':'{v}% extra Gold','item_fastercastrate':'{v}% FCR','item_fasterattackrate':'{v}% IAS',
 'item_fastermovevelocity':'{v}% FRW','item_fastergethitrate':'{v}% FHR','item_fasterblockrate':'{v}% faster block','toblock':'{v}% chance to block',
 'item_allskills':'+{v} all skills','item_cannotbefrozen':'Cannot be frozen','item_absorbcold_percent':'{v}% Cold absorb','item_absorbfire_percent':'{v}% Fire absorb',
 'item_absorblight_percent':'{v}% Lightning absorb','item_absorblight':'+{v} Lightning absorb','item_absorbmagic':'+{v} Magic absorb',
 'normal_damage_reduction':'Damage reduced by {v}','magic_damage_reduction':'Magic damage reduced by {v}','damageresist':'Damage reduced by {v}%',
 'item_pierce_cold_immunity':'Sunder: cold immunity','item_pierce_fire_immunity':'Sunder: fire immunity','item_pierce_damage_immunity':'Sunder: physical immunity',
 'item_pierce_light_immunity':'Sunder: lightning immunity','tohit':'+{v} Attack rating','item_tohit_percent':'+{v}% Attack rating','armorclass':'+{v} Defense',
 'armorclass_vs_missile':'+{v} Defense vs missiles','item_armor_percent':'+{v}% enhanced Defense','item_maxdamage_percent':'+{v}% enhanced damage',
 'item_mindamage_percent':None,'lifedrainmindam':'{v}% Life leech','manadrainmindam':'{v}% Mana leech','item_crushingblow':'{v}% Crushing blow',
 'item_openwounds':'{v}% Open wounds','item_deadlystrike':'{v}% Deadly strike','item_reducedprices':'Vendor prices -{v}%','hpregen':'Replenish life +{v}',
 'manarecoverybonus':'Regenerate mana {v}%','item_attackertakesdamage':'Attacker takes damage of {v}','item_attackertakeslightdamage':'Attacker takes lightning damage of {v}',
 'item_damagetomana':'{v}% damage taken goes to mana','item_healafterkill':'+{v} Life after each kill','item_manaafterkill':'+{v} Mana after each kill',
 'item_demondamage_percent':'+{v}% damage to demons','item_undeaddamage_percent':'+{v}% damage to undead','item_slow':'Slows target by {v}%',
 'item_freeze':'Freezes target +{v}','item_halffreezeduration':'Half freeze duration','item_knockback':'Knockback','item_preventheal':'Prevent monster heal',
 'item_ignoretargetac':"Ignore target's defense",'item_indesctructible':'Indestructible','item_replenish_durability':'Repairs durability',
 'item_req_percent':'Requirements {v}%','item_poisonlengthresist':'Poison length reduced by {v}%','item_charge_noconsume':'{v}% chance not to consume charges',
 'item_pierce':'{v}% Pierce','item_magicarrow':'Fires magic arrows','passive_fire_mastery':'+{v}% fire skill damage','passive_cold_mastery':'+{v}% cold skill damage',
 'passive_ltng_mastery':'+{v}% lightning skill damage','passive_pois_mastery':'+{v}% poison skill damage','passive_fire_pierce':'-{v}% enemy Fire res',
 'passive_cold_pierce':'-{v}% enemy Cold res','passive_ltng_pierce':'-{v}% enemy Lightning res','passive_pois_pierce':'-{v}% enemy Poison res',
 'passive_mag_pierce':'-{v}% enemy Magic res','item_maxdurability_percent':None,'maxdurability':None,'item_lightradius':None,'maxstamina':None,
 'staminarecoverybonus':None,'secondary_mindamage':None,'secondary_maxdamage':None,'item_throw_mindamage':None,'item_throw_maxdamage':None,
 'questitemdifficulty':None,'item_extra_stack':None,'item_replenish_quantity':None,'item_levelreq':None,'item_regenstamina_perlevel':None,
 'coldlength':None,'poisonlength':None,'poison_count':None,
}
PERLVL = {'item_hp_perlevel':('Life',2048),'item_mana_perlevel':('Mana',2048),'item_armor_perlevel':('Defense',8),'item_find_magic_perlevel':('% Magic Find',8),
 'item_find_gold_perlevel':('% extra Gold',8),'item_deadlystrike_perlevel':('% Deadly strike',8),'item_tohitpercent_perlevel':('% Attack rating',8),
 'item_absorb_cold_perlevel':('Cold absorb',8),'item_absorb_fire_perlevel':('Fire absorb',8),'item_vitality_perlevel':('Vitality',8),
 'item_maxdamage_perlevel':('max damage',8),'item_tohit_demon_perlevel':('AR vs demons',8)}
PROC = {'item_skillonhit':'on striking','item_skillongethit':'when struck','item_skillonattack':'on attack','item_skillonkill':'when you kill',
        'item_skillondeath':'when you die','item_skillonlevelup':'on level-up'}

def lines(stats):
  d = {}; out = []
  for n, l, v in stats: d.setdefault(n, (l, v))
  def g(k): return d.get(k, (0, 0))[1]
  for n, l, v in stats:
    if n in ('maxhp', 'maxmana') and v >= 256: v //= 256
    if n in PERLVL:
      lab, div = PERLVL[n]; out.append(f'+{v/div:g} {lab} per level'); continue
    if n in PROC: out.append(f'{v}% chance to cast level {l & 63} {SK.get(l >> 6, "skill")} {PROC[n]}'); continue
    if n == 'item_singleskill': out.append(f'+{v} {SK.get(l, "skill")}'); continue
    if n == 'item_nonclassskill': out.append(f'+{v} {SK.get(l, "skill")} (any class)'); continue
    if n == 'item_charged_skill': out.append(f'Level {l & 63} {SK.get(l >> 6, "skill")} ({v & 255}/{v >> 8} charges)'); continue
    if n == 'item_aura': out.append(f'Level {v} {SK.get(l, "skill")} aura'); continue
    if n == 'item_addskill_tab': out.append(f'+{v} {TABN.get(l, CLS[l // 8] + " tab " + str(l % 8 + 1) if l // 8 < 8 else "skill tab")} skills'); continue
    if n == 'item_addclassskills': out.append(f'+{v} {CLS[l] if l < 8 else "class"} skills'); continue
    if n == 'item_elemskill': out.append(f'+{v} {ELEM.get(l, "elemental")} skills'); continue
    for el, nm in (('fire', 'fire'), ('cold', 'cold'), ('light', 'lightning'), ('poison', 'poison')):
      if n == el + 'mindam':
        lo, hi = v, g(el + 'maxdam')
        if el == 'poison':
          ln = g('poisonlength') or 1; lo, hi = round(lo * ln / 256), round(hi * ln / 256)
          out.append(f'Adds {lo}-{hi} poison damage over {ln/25:g}s')
        else: out.append(f'Adds {lo}-{hi} {nm} damage' if hi and hi != lo else f'Adds {lo} {nm} damage')
        break
      if n == el + 'maxdam': break
    else:
      if n == 'mindamage': out.append(f'+{v}-{g("maxdamage") or v} damage'); continue
      if n == 'maxdamage':
        if 'mindamage' not in d: out.append(f'+{v} max damage')
        continue
      if n in T:
        if T[n]: out.append(T[n].format(v=v))
        continue
      out.append(f'{n.replace("item_", "").replace("_", " ")} {v}')  # unknown: keep, readable-ish
  return out

GEMNAME = lambda k: GRADE[k[:2]] + GEMN[k[2:]]
def sockname(s):
  if s[0] == 'r' and s[1:].isdigit(): return RUNES[int(s[1:]) - 1]
  if s[:2] in GEMP and s[2:] in GEMN: return GEMNAME(s)
  return {'jew': 'Jewel'}.get(s, s)

items = []
for x in o:
  if x['type'] in ('rune','book','rpot','ques','key','hpot','mpot','spot','apot','wpot','scro','tpot') or (x['code'][:2] in GEMP and x['type'].startswith('gem')) or x['code'] in ('skz','skl','skc','skf','sku') or x['code'] in MATS: continue
  items.append(dict(l=x['loc'], q=x['quality'], n=x['name'], b=x['base'], t=x['tier'], e=x['eth'], s=[sockname(s) for s in x['socketed']], k=x['kind'], ty=x['type'],
                    il=x['ilvl'], st=lines(x['stats']), rw=bool(x['runeword']), set=x.get('set', ''), eq=x['pos']['mode'] == 'Equipped',
                    **({'sl': x['pos'].get('body_location')} if x['pos']['mode'] == 'Equipped' else {})))

chars = []; snap = 0
for f in sorted(glob.glob('saves/*.json')):
  b = os.path.basename(f)
  if b in ('stash.json', 'char.json'): continue
  ch = json.load(open(f)).get('character', {})
  chars.append(dict(n=b[:-5], c=ch.get('class', ''), lv=ch.get('level', 0)))
  snap = max(snap, ch.get('last_save_time') or 0)
old.update(items=items, runes=runes, gems=gems, mats=mats, chars=chars, snap=snap * 1000)
old['farm']['Stone of Jordan'] = ['+1 to all skills', 'Adds 1-12 lightning damage', '+20 to mana', 'Increase max mana 25%']
json.dump(old, open('pagedata.json', 'w'), separators=(',', ':'))
print(len(items), 'items ·', {k: v for k, v in runes.items() if v}, '·', len(chars), 'characters')
