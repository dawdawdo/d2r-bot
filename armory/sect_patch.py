import sys,re
p=sys.argv[1];s=open(p,encoding='utf8').read()
for h in ['Portals &amp; quests','Potions &amp; misc']:
  s,k=re.subn(r'<h2 class="cg">'+re.escape(h)+r'</h2><div class="tbl cg">.*?</table></div>\n?','',s,flags=re.S); assert k==1,(h,k)
open(p,'w',encoding='utf8').write(s);print('ok')
