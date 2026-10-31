#!/usr/bin/env python3
"""Phase 91: offline repository-local build/preprocessor gate (not HEMTT/Arma)."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]; ADDONS=ROOT/'addons'
CARD_PREFIXES={'card':'z\\DD1380\\addons\\card','card_main':'z\\DD1380\\addons\\main'}

def validate_prefix(addon):
 pf=addon/'$PBOPREFIX$'; assert pf.is_file(),addon
 got=pf.read_text(errors='replace').strip().replace('/','\\')
 exp=CARD_PREFIXES.get(addon.name,'acm_extended' if addon.name=='acm_extended' else 'x\\ACM\\addons\\'+addon.name)
 assert got.lower()==exp.lower(),f'{addon.name}: {got!r} != {exp!r}'
 if addon.name in CARD_PREFIXES:
  options=addon/'addon.toml'; assert options.is_file(),f'{addon.name}: missing addon-scoped prefix declaration'
  flags=re.findall(r'^\s*ignore_pboprefix\s*=\s*(true|false)\s*(?:#.*)?$',options.read_text(),re.M)
  assert flags==['true'],f'{addon.name}: retained DD1380 prefix must declare ignore_pboprefix = true exactly once'

addons=sorted(p for p in ADDONS.iterdir() if p.is_dir() and (p/'config.cpp').is_file()); assert addons
for a in addons: validate_prefix(a)
inc_re=re.compile(r'^\s*#\s*include\s*["<]([^">]+)[">]',re.M); external=('\\a3\\','\\x\\cba\\','\\z\\ace\\'); seen=set(); missing=[]; unknown=[]
def virtual(s):
 n=s.replace('/','\\'); lo=n.lower(); pref='\\x\\acm\\addons\\'
 if lo.startswith(pref): return ADDONS.joinpath(*[x for x in n[len(pref):].split('\\') if x])
 for folder,prefix in CARD_PREFIXES.items():
  pref='\\'+prefix+'\\'
  if lo.startswith(pref.lower()): return (ADDONS/folder).joinpath(*[x for x in n[len(pref):].split('\\') if x])
 if any(lo.startswith(x) for x in external): return None
 if n.startswith('\\'): unknown.append(n); return None
 raise AssertionError(n)
def walk(p):
 p=p.resolve()
 if p in seen:return
 seen.add(p); t=p.read_text(errors='replace')
 for i in inc_re.findall(t):
  n=i.replace('/','\\'); target=virtual(n) if n.startswith('\\') else p.parent.joinpath(*[x for x in n.split('\\') if x])
  if target is None: continue
  if not target.is_file(): missing.append((p.relative_to(ROOT),i,target)); continue
  walk(target)
for a in addons: walk(a/'config.cpp')
assert not unknown,'unknown rooted includes:\n'+'\n'.join(sorted(set(unknown)))
assert not missing,'missing local includes:\n'+'\n'.join(f'{s}: {i} -> {d}' for s,i,d in missing)
def block(t,mark):
 st=t.find(mark); assert st>=0,mark; b=t.find('{',st); assert b>=0; dep=0;i=b;state='code';q=''
 while i<len(t):
  c=t[i];n=t[i+1] if i+1<len(t) else ''
  if state=='line':
   if c=='\n':state='code'
  elif state=='block':
   if c=='*' and n=='/':state='code';i+=1
  elif state=='str':
   if c=='\\':i+=1
   elif c==q:state='code'
  else:
   if c=='/' and n=='/':state='line';i+=1
   elif c=='/' and n=='*':state='block';i+=1
   elif c in ('"',"'"):state='str';q=c
   elif c=='{':dep+=1
   elif c=='}':
    dep-=1
    if dep==0:return t[b+1:i]
  i+=1
 raise AssertionError('unterminated '+mark)
conf=(ADDONS/'acm_extended/config.cpp').read_text(errors='replace'); inf=block(block(block(conf,'class CfgFunctions'),'class ACME'),'class infusion')
m=re.search(r'\bfile\s*=\s*["\']([^"\']+)["\']\s*;',inf); assert m and m.group(1).lower()=='\\acm_extended\\functions'
regs=re.findall(r'\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{\s*\}\s*;',inf); assert regs
miss=[n for n in regs if not (ADDONS/'acm_extended/functions'/f'fn_{n}.sqf').is_file()]; assert not miss,miss
for v in re.findall(r"preprocessFileLineNumbers\s+['\"](\\acm_extended\\[^'\"]+)['\"]",conf):
 src=ADDONS/'acm_extended'/v[len('\\acm_extended\\'):].replace('\\','/'); assert src.is_file(),v
print(f'fork phase 91 offline build gate: PASS ({len(addons)} addons, {len(seen)} local preprocessor files, {len(regs)} ACME functions)')
