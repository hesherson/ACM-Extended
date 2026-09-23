"""Validate test-only changes against a complete pinned checkout. Never update main.

Keep raw broad-suite failure outcomes. Publish an isolated candidate only after
exact-tree, allowed-scope, old-test AST, focused, baseline-control and HEMTT checks.
"""
import ast
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path.cwd()
INFRA=ROOT/'.audit/historical-batch8'
BASE='f5f2c3b436a3462103256f78596df1fcf9653d7d'
TREE='f5aad244197d2d442d3dc9c30e6db1830bed986c'
CANDIDATE=Path('/tmp/acme-backlog8-candidate')
BASELINE=Path('/tmp/acme-backlog8-baseline')
RESULTS=Path('/tmp/acme-backlog8-results')
RESULTS.mkdir(exist_ok=True)
PREFIX='addons/acm_extended/tools/'
NEW=[PREFIX+'test_historical_syringe_identity.py',PREFIX+'test_historical_dogtag_identity.py']
DOCS={'docs/audits/2026-09-22-historical-backlog-batch8.md','docs/audits/historical-backlog-remaining-20260922.txt'}

def git(*args,cwd=ROOT):
    return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()

def run(command,cwd,log,env=None):
    with (RESULTS/log).open('w') as stream:
        cp=subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=360)
    (RESULTS/(log+'.command.json')).write_text(json.dumps({'command':command,'returncode':cp.returncode},indent=2))
    print(log,'exit',cp.returncode,flush=True)
    print((RESULTS/log).read_text()[-2000:],flush=True)
    return cp.returncode

subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
for path in (CANDIDATE,BASELINE):
    subprocess.run(['git','worktree','add','--detach',str(path),BASE],check=True)
compressed=b''.join((INFRA/f'payload{i}.bin').read_bytes() for i in range(4))
assert hashlib.sha256(compressed).hexdigest()=='53511a9704649e0ed5f2eae45586c6c25a2e345d15ef4f1d514ca9fa5fd342e9'
patch=lzma.decompress(compressed)
assert hashlib.sha256(patch).hexdigest()=='99b0f445ff4f63b89db93a2e9d8d1f52f977c68a0cbdf010811d88b9bfe83893'
settings=(INFRA/'settings.bin').read_bytes()
assert hashlib.sha256(settings).hexdigest()=='46151e2c2d2eab928db5686b3021da69b65934c329ae42f2ef4b3068cfb9e5d0'
settings=json.loads(lzma.decompress(settings))
allowed=settings['allowed_tests']
patchfile=RESULTS/'reviewed.patch';patchfile.write_bytes(patch)
subprocess.run(['git','apply','--check',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','apply',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','add','-A'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE
changes=git('diff','--cached','--name-status',cwd=CANDIDATE).splitlines()
assert len(changes)==8,changes
for line in changes:
    status,path=line.split('\t')
    assert status in ('A','M'),line
    assert path in DOCS or path in NEW or path in {PREFIX+n for n in allowed},line
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)
scope={}
for name,permitted in allowed.items():
    def functions(path):
        tree=ast.parse(path.read_text())
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
    a,b=functions(BASELINE/PREFIX/name),functions(CANDIDATE/PREFIX/name)
    assert a.keys()==b.keys(),name
    changed={key for key in a if a[key]!=b[key]}
    assert changed==set(permitted),(name,changed)
    scope[name]=sorted(changed)
assert sum(map(len,scope.values()))==9
(RESULTS/'test-edit-scope.json').write_text(json.dumps(scope,indent=2))
(RESULTS/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime_changes':[],'asset_changes':[],'deleted_files':[],'unchanged_existing_paths':4025},indent=2))
print('Exact reviewed tree verified; all production and assets unchanged.',flush=True)

focused=settings['focused']
(RESULTS/'focused-paths.json').write_text(json.dumps(focused,indent=2))
assert run([sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(RESULTS/'focused.xml')],CANDIDATE,'focused.log')==0
suite=ET.parse(RESULTS/'focused.xml').getroot().find('testsuite')
assert suite is not None and suite.attrib['tests']=='1500',suite.attrib if suite is not None else None
assert all(suite.attrib[k]=='0' for k in ('errors','failures','skipped'))
assert run([os.environ['HEMTT'],'check'],CANDIDATE,'hemtt.log')==0

reports={}
for label,root in [('before',BASELINE),('after',CANDIDATE)]:
    events=RESULTS/(label+'.jsonl');events.write_text('')
    env={**os.environ,'PYTHONPATH':str(INFRA),'AUDIT_EVENTS':str(events)}
    command=[sys.executable,'-m','pytest',PREFIX.rstrip('/'),'-q','--continue-on-collection-errors','--tb=short','-p','auditrecorder']
    assert run(command,root,label+'.log',env)==1
    reports[label]=[json.loads(line) for line in events.read_text().splitlines()]

def identity(row):
    context=row.get('context','')
    if context in ('',"''",'""'):context=''
    match=re.fullmatch(r'SubtestContext\(msg=(.*?), kwargs=(.*)\)',context)
    if match:
        try:context=json.dumps([ast.literal_eval(match[1]),ast.literal_eval(match[2])],sort_keys=True,default=str)
        except (ValueError,SyntaxError):pass
    return (row['nodeid'],row['kind'],row.get('when'),row.get('type'),context)
before={identity(row):row for row in reports['before']}
after={identity(row):row for row in reports['after']}
regressions=[key for key in before.keys() & after.keys() if before[key]['outcome']=='passed' and after[key]['outcome']!='passed']
fixed=[key for key in before.keys() & after.keys() if before[key]['outcome']=='failed' and after[key]['outcome']=='passed']
exposed=[key for key in after if after[key]['outcome']=='failed' and (key not in before or before[key]['outcome']!='failed')]
missing=list(before.keys()-after.keys())
errors={label:[row for row in rows if row['kind']=='collection' or (row.get('when')!='call' and row['outcome']=='failed')] for label,rows in reports.items()}
skips={label:sum(row['outcome']=='skipped' for row in rows) for label,rows in reports.items()}
summary={'fixed_count':len(fixed),'fixed':sorted(key[0] for key in fixed),'newly_failing':exposed,'regressions':regressions,'missing_previous_outcomes':missing,'errors':errors,'skips':skips,'known_broad_suite_remains_failing':True}
(RESULTS/'comparison.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2),flush=True)
assert len(fixed)==9 and not regressions and not any(errors.values()) and not exposed and not missing
assert skips=={'before':4,'after':4}
for label,expected in [('before',(232,3055)),('after',(223,3136))]:
    text=(RESULTS/(label+'.log')).read_text()
    assert f'{expected[0]} failed, {expected[1]} passed, 4 skipped, 5518 subtests passed' in text,label

# The same new cases must pass with unchanged runtime. Not a red-green production fix.
for name in NEW:shutil.copyfile(CANDIDATE/name,BASELINE/name)
try:
    assert run([sys.executable,'-m','pytest',*NEW,'-q','--tb=short','--junitxml='+str(RESULTS/'unchanged-runtime.xml')],BASELINE,'unchanged-runtime.log')==0
    control=ET.parse(RESULTS/'unchanged-runtime.xml').getroot().find('testsuite')
    assert control.attrib['tests']=='72' and all(control.attrib[k]=='0' for k in ('errors','failures','skipped')),control.attrib
finally:
    for name in NEW:(BASELINE/name).unlink()
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
subprocess.run(['git','diff','--exit-code'],cwd=BASELINE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE

# Publish only this isolated source branch. No workflow/payload enters its tree.
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Verify stored-syringe and patient identity contracts (historical backlog batch 8)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch8-validated'],cwd=ROOT,check=True)
(RESULTS/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Verified isolated candidate:',commit,flush=True)
