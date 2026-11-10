import sys
p,ref=sys.argv[1],open(sys.argv[2]).read()
s=open(p,encoding='utf8').read()
def rep(a,b):
  global s
  assert s.count(a)==1,(a,s.count(a)); s=s.replace(a,b)
rep('<a href="#inventory">Inventory</a></nav>','<a href="#inventory">Inventory</a><a href="#ref">Reference</a></nav>')
i=s.index('<section id="v-inventory"'); j=s.index('</section>',i)+len('</section>')
s=s[:j]+'\n\n'+ref+s[j:]
css='''<style>
table.cube td:first-child{max-width:60ch}
table.craft td{white-space:nowrap}table.craft th{white-space:nowrap}
</style>
'''
rep('<div class="wrap">',css+'<div class="wrap">')
rep("if (h.startsWith('farm')) v = 'farm'; else if (h === 'inventory') v = 'inventory';","if (h.startsWith('farm')) v = 'farm'; else if (h === 'inventory') v = 'inventory'; else if (h === 'ref') v = 'ref';")
rep("['goals', 'farm', 'inventory'].forEach(","['goals', 'farm', 'inventory', 'ref'].forEach(")
js='''
// ---------- cube filter ----------
function cubeFilter(){const q=$('#cq').value.trim().toLowerCase();let n=0;
 document.querySelectorAll('#v-ref table.cube').forEach(t=>{let k=0;t.querySelectorAll('tbody tr').forEach(r=>{const m=!q||r.textContent.toLowerCase().includes(q);r.hidden=!m;if(m)k++});n+=k;
  const w=t.closest('.tbl');w.hidden=!k;let h=w.previousElementSibling;while(h&&h.tagName!=='H2')h=h.previousElementSibling;if(h)h.hidden=!k;
  const l=w.previousElementSibling;if(l&&l.classList.contains('lede'))l.hidden=!k;});
 $('#ccnt').textContent=q?n+' match'+(n===1?'':'es'):'';}
$('#cq').addEventListener('input',cubeFilter);
addEventListener('hashchange', show); show();'''
rep("\naddEventListener('hashchange', show); show();",js)
open(p,'w',encoding='utf8').write(s)
print('ok',len(s))
