import sys
p=sys.argv[1]; s=open(p,encoding='utf8').read()
def rep(a,b):
  global s; assert s.count(a)==1,(a[:60],s.count(a)); s=s.replace(a,b)
anchor="  ['torch', 'Hellfire Torch',"
card="""  ['ctabase', 'Call to Arms base: plain Flail', 'Call to Arms (switch weapon for everyone)', [], ['Needs a plain white Flail at item level 41+ so it can take 5 sockets. Anything that drops in Hell qualifies', 'Easy finds: Hell Cows, Act 1 Hell, or check Hell vendors (Charsi, Fara) for one', 'Socket it with the Larzuk quest (exactly 5). Check which characters still have it unused', 'No quest left? Ral + Amn + Perfect Amethyst gives random sockets (1-5); retry with another Flail', 'Requirements: 41 Str / 35 Dex. Double Axe (43 Str, no Dex) or Long Bow (22 Str / 19 Dex) also get exactly 5 from Larzuk']],
"""
rep(anchor,card+anchor)
rep("needs one more Ohm (or two Vex) after the Infinity cube. Larzuk gives a Flail exactly 5 sockets.', () => rw('Call to Arms') ? 'done' : 'farm', 'runes']".replace('needs','Needs'),
    "Needs one more Ohm (or two Vex) after the Infinity cube. Base: a plain Flail (see the farm guide).', () => rw('Call to Arms') ? 'done' : 'farm', 'ctabase']")
rep("Lowest one-hander: <b>Double Axe</b> (43 Str, 5 from Larzuk). Your plan’s Flail (41 Str / 35 Dex) works too.",
    "Among one-handers, the <b>Flail</b> needs the least Strength (41 Str / 35 Dex) and the <b>Double Axe</b> needs no Dex (43 Str). Both get exactly 5 from Larzuk.")
open(p,'w',encoding='utf8').write(s); print('ok')
