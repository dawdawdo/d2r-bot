import sys,re
p=sys.argv[1];s=open(p,encoding='utf8').read()
n=len(s)
s,k=re.subn(r'<h2 class="cg">Gems</h2><div class="tbl cg">.*?</table></div>\n?','',s,flags=re.S)
assert k==1,k
open(p,'w',encoding='utf8').write(s);print('removed',n-len(s))
