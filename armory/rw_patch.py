import sys
p=sys.argv[1]; s=open(p,encoding='utf8').read()
def rep(a,b):
  global s; assert s.count(a)==1,(a[:70],s.count(a)); s=s.replace(a,b)
html='''<h2>Runewords I'm after</h2>
<p class="lede">Rune counts come from the page snapshot (stash may have changed since). Missing runes show the cube step that makes them.</p>
<div class="farmlist" id="rwwant"></div>
'''
rep('<div class="filters"><input type="search" id="cq"', html+'<h2>Cube recipes</h2>\n<div class="filters"><input type="search" id="cq"')
css='''.rwc .rl{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.rwc .rl span{font-family:var(--mono);font-size:13px;border:1px solid var(--line);border-radius:4px;padding:2px 8px;background:var(--bg)}
.rwc .rl span b{font-family:var(--display);color:var(--rune)}
.rwc .short{font-size:14px;color:var(--bad)}.rwc .ready{font-size:14px;color:var(--ok);font-weight:700}
</style>'''
rep('table.craft td{white-space:nowrap}table.craft th{white-space:nowrap}\n</style>','table.craft td{white-space:nowrap}table.craft th{white-space:nowrap}\n'+css)
js='''
// ---------- wanted runewords ----------
(function(){
 const WANT=[['Call to Arms','Switch weapon for everyone (Battle Orders)'],['Infinity','ThroatCutter merc'],['Enigma','Teleport for non-sorcs'],['Chains of Honor','Body armor alternative'],['Smoke','ThroatCutter (replaces Vipermagi)']];
 const LAD='El Eld Tir Nef Eth Ith Tal Ral Ort Thul Amn Sol Shael Dol Hel Io Lum Ko Fal Lem Pul Um Mal Ist Gul Vex Ohm Lo Sur Ber Jah Cham Zod'.split(' ');
 const LVL=[11,11,13,13,15,15,17,19,21,23,25,27,29,31,0,35,37,39,41,43,45,47,49,51,53,55,57,59,61,63,65,67,69];
 const GEM=[,,,,,,,,,,'Chipped Topaz','Chipped Amethyst','Chipped Sapphire','Chipped Ruby','Chipped Emerald','Chipped Diamond','Flawed Topaz','Flawed Amethyst','Flawed Sapphire','Flawed Ruby','Flawed Emerald','Flawed Diamond','Topaz','Amethyst','Sapphire','Ruby','Emerald','Diamond','Flawless Topaz','Flawless Amethyst','Flawless Sapphire','Flawless Ruby','Flawless Emerald'];
 const TY={weap:'Any weapon',pole:'Polearm',spea:'Spear',tors:'Body armor',shld:'Shield',helm:'Helm',swor:'Sword'};
 const how=r=>{const i=LAD.indexOf(r);if(i<1)return '';const n=i<=20?3:2,g=GEM[i];return `${n} ${LAD[i-1]}${g?' + '+g:''}`;};
 $('#rwwant').innerHTML=WANT.map(([n,why])=>{const w=D.rwdb[n];if(!w)return '';const rs=w.runes.split(' ');const need={};rs.forEach(r=>need[r]=(need[r]||0)+1);
  const lvl=Math.max(...rs.map(r=>LVL[LAD.indexOf(r)]));
  const chips=rs.map(r=>`<span><b>${r}</b> ${D.runes[r]??0}</span>`).join('');
  const short=Object.entries(need).filter(([r,c])=>(D.runes[r]??0)<c).map(([r,c])=>`${r} ×${c-(D.runes[r]??0)} (cube: ${how(r)})`);
  const done=typeof rw==='function'&&rw(n);
  return `<div class="farmcard rwc"><h3><span class="q-RW">${esc(n)}</span> <span class="small">· ${rs.length} sockets · level ${lvl}</span></h3><div class="need">${esc(why)} · Base: ${w.types.map(t=>TY[t]||t).join(' / ')}${w.patch&&/Ladder/.test(w.patch)?' · formerly ladder-only':''}</div><div class="rl">${chips}</div>${done?'<div class="ready">Already made</div>':short.length?`<div class="short">Short: ${esc(short.join(' · '))}</div>`:'<div class="ready">You have every rune for this</div>'}<div class="stats">${esc(w.mods.join(' · '))}</div></div>`;}).join('');
})();
'''
rep("\n// ---------- cube filter ----------",js+"\n// ---------- cube filter ----------")
open(p,'w',encoding='utf8').write(s);print('ok')
