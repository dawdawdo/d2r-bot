import sys,re
p=sys.argv[1];s=open(p,encoding='utf8').read()
rows=re.findall(r'<tr><td>1 \w+ Rune \+ 1 Perfect \w+ \+ 1 Act \d Ancient statue \+ 1 [^<]+</td><td>.*?</tr>',s)
assert len(rows)==6,len(rows)
new='<tr><td>1 Latent Sunder charm (Herald drop only) + 1 Perfect gem + 1 Rune + 1 Worldstone Shard <span class="small">(gem/rune/shard depend on the charm, e.g. Flame Rift: Perfect Ruby + Fal + Southern Shard)</span></td><td><b>Renewed Sunder charm</b> <span class=chip>Patch 3.2</span></td></tr>'
s=s.replace(rows[0],new,1)
for r in rows[1:]: s=s.replace(r,'',1)
open(p,'w',encoding='utf8').write(s);print('ok')
