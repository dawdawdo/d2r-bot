import csv
X='xl/'
def rd(f): return list(csv.DictReader(open(X+f,encoding='latin-1'),delimiter='\t'))
TABS={0:'Bow',1:'Passive',2:'Javelin',8:'Fire',9:'Lightning',10:'Cold',16:'Curses',17:'Poison & Bone',18:'Summoning',24:'Combat (Pal)',25:'Offensive Auras',26:'Defensive Auras',32:'Combat (Barb)',33:'Masteries',34:'Warcries',40:'Summoning (Dru)',41:'Shape Shifting',42:'Elemental',48:'Traps',49:'Shadow Disciplines',50:'Martial Arts'}
# D2R skilltab param numbering: class*3 + tab  (ama 0-2, sor 3-5, nec 6-8, pal 9-11, bar 12-14, dru 15-17, ass 18-20, war 21-23)
TABP={}
for c,(cn,tabs) in enumerate([('Amazon',['Bow & Crossbow','Passive & Magic','Javelin & Spear']),('Sorceress',['Fire','Lightning','Cold']),('Necromancer',['Curses','Poison & Bone','Summoning']),('Paladin',['Combat','Offensive Auras','Defensive Auras']),('Barbarian',['Combat','Masteries','Warcries']),('Druid',['Summoning','Shape Shifting','Elemental']),('Assassin',['Traps','Shadow Disciplines','Martial Arts']),('Warlock',['Tab 1','Tab 2','Tab 3'])]):
  for i,t in enumerate(tabs): TABP[c*3+i]=f'{t} ({cn})'
CLS={'ama':'Amazon','sor':'Sorceress','nec':'Necromancer','pal':'Paladin','bar':'Barbarian','dru':'Druid','ass':'Assassin','war':'Warlock'}
S={'ac':'+{} defense','ac%':'+{}% enhanced defense','dmg%':'+{}% enhanced damage','dmg-min':'+{} minimum damage','dmg-max':'+{} maximum damage','dmg':'+{} damage',
'allskills':'+{} to all skills','swing1':'+{}% increased attack speed','swing2':'+{}% increased attack speed','swing3':'+{}% increased attack speed',
'cast1':'+{}% faster cast rate','cast2':'+{}% faster cast rate','cast3':'+{}% faster cast rate','balance1':'+{}% faster hit recovery','balance2':'+{}% faster hit recovery','balance3':'+{}% faster hit recovery',
'block1':'+{}% faster block rate','block2':'+{}% faster block rate','block3':'+{}% faster block rate','block':'+{}% chance to block','move1':'+{}% faster run/walk','move2':'+{}% faster run/walk','move3':'+{}% faster run/walk',
'res-all':'All resistances +{}','res-fire':'Fire resist +{}%','res-cold':'Cold resist +{}%','res-ltng':'Lightning resist +{}%','res-pois':'Poison resist +{}%',
'res-fire-max':'+{}% max fire resist','res-cold-max':'+{}% max cold resist','res-ltng-max':'+{}% max lightning resist','res-pois-max':'+{}% max poison resist','res-all-max':'+{}% to all max resists',
'lifesteal':'{}% life stolen per hit','manasteal':'{}% mana stolen per hit','mana':'+{} to mana','mana%':'Increase max mana {}%','hp':'+{} to life','hp%':'Increase max life {}%',
'str':'+{} to strength','dex':'+{} to dexterity','vit':'+{} to vitality','enr':'+{} to energy','all-stats':'+{} to all attributes','regen':'Replenish life +{}','regen-mana':'Regenerate mana {}%',
'red-dmg%':'Damage reduced by {}%','red-dmg':'Damage reduced by {}','red-mag':'Magic damage reduced by {}','mag%':'{}% better chance of getting magic items','gold%':'{}% extra gold',
'crush':'{}% chance of crushing blow','deadly':'{}% deadly strike','openwounds':'{}% chance of open wounds','nofreeze':'Cannot be frozen','light':'+{} to light radius',
'pierce-fire':'-{}% to enemy fire resistance','pierce-cold':'-{}% to enemy cold resistance','pierce-ltng':'-{}% to enemy lightning resistance','pierce-pois':'-{}% to enemy poison resistance',
'extra-fire':'+{}% to fire skill damage','extra-cold':'+{}% to cold skill damage','extra-ltng':'+{}% to lightning skill damage','extra-pois':'+{}% to poison skill damage',
'abs-fire%':'+{}% fire absorb','abs-cold%':'+{}% cold absorb','abs-ltng%':'+{}% lightning absorb','abs-fire':'+{} fire absorb','abs-cold':'+{} cold absorb','abs-ltng':'+{} lightning absorb',
'dmg-undead':'+{}% damage to undead','dmg-demon':'+{}% damage to demons','att':'+{} attack rating','att%':'+{}% attack rating','att-demon':'+{} AR vs demons','att-undead':'+{} AR vs undead',
'ease':'Requirements {}%','noheal':'Prevent monster heal','knock':'Knockback','howl':'Hit causes monster to flee {}%','stupidity':'Hit blinds target +{}','reduce-ac':'-{}% target defense',
'dur%':'+{}% durability','indestruct':'Indestructible','ignore-ac':'Ignore target\'s defense','slow':'Slows target by {}%','mana-kill':'+{} mana after each kill','heal-kill':'+{} life after each kill',
'demon-heal':'+{} life after each demon kill','rep-dur':'Repairs durability','thorns':'Attacker takes damage of {}','half-freeze':'Half freeze duration','cheap':'Reduces vendor prices {}%',
'charge-noconsume':'{}% chance finishing moves don\'t consume charges','dmg-to-mana':'{}% damage taken goes to mana','freeze':'Freezes target +{}','addxp':'+{}% experience gained',
'res-mag':'Magic resist +{}%','red-dmg-pct':'Damage reduced by {}%','cold-len':'Cold duration {}','fireskill':'+{} to fire skills','sock':'Socketed ({})','dmg-norm':'+{} damage','manarecov':'{}% mana regen','stamdrain':'{}% slower stamina drain','stam':'+{} max stamina','bloody':'','splash':'Melee attacks deal splash damage','kill-skill':'','gethit-skill':''}
def rng(a,b):
  a=a or b; b=b or a
  return a if a==b else f'{a}-{b}'
def fmt(code,param,mn,mx):
  if not code: return None
  c=code
  if c in CLS: return f'+{rng(mn,mx)} to {CLS[c]} skills'
  if c=='skilltab': return f'+{rng(mn,mx)} to {TABP.get(int(param or 0),"skill tab "+str(param))} skills'
  if c in('skill','oskill'): return f'+{rng(mn,mx)} to {param}'+(' (any class)' if c=='oskill' else '')
  if c=='aura': return f'Level {rng(mn,mx)} {param} aura when equipped'
  if c=='hit-skill': return f'{mn}% chance to cast level {mx} {param} on striking'
  if c=='att-skill': return f'{mn}% chance to cast level {mx} {param} on attack'
  if c=='gethit-skill': return f'{mn}% chance to cast level {mx} {param} when struck'
  if c=='kill-skill': return f'{mn}% chance to cast level {mx} {param} when you kill'
  if c=='levelup-skill': return f'Cast level {mx} {param} on level-up'
  if c=='charged': return f'Level {mx} {param} ({mn} charges)'
  if c.endswith('/lvl'):
    base={'vit/lvl':'vitality','str/lvl':'strength','dex/lvl':'dexterity','enr/lvl':'energy','hp/lvl':'life','mana/lvl':'mana','mag%/lvl':'% magic find','gold%/lvl':'% extra gold','ac/lvl':'defense','dmg/lvl':'max damage','deadly/lvl':'% deadly strike','att/lvl':'attack rating','res-fire/lvl':'% fire resist','res-cold/lvl':'% cold resist','res-ltng/lvl':'% lightning resist','res-pois/lvl':'% poison resist','abs-fire/lvl':'fire absorb','abs-cold/lvl':'cold absorb','dmg%/lvl':'% enhanced damage','crush/lvl':'% crushing blow','thorns/lvl':'thorns'}.get(c,c)
    try: return f'+{int(param)/8:g} {base} per character level'
    except: return f'{c} {param}'
  for el in('fire','cold','ltng','pois','mag'):
    if c==f'dmg-{el}': return f'Adds {rng(mn,mx)} {dict(fire="fire",cold="cold",ltng="lightning",pois="poison",mag="magic")[el]} damage'
  if c in S:
    t=S[c]; v=rng(mn,mx)
    if c=='ease': v=mn
    return t.format(v) if '{}' in t else t
  return f'[{c} {param} {rng(mn,mx)}]'
