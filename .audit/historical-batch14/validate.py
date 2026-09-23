"""Validate a pinned chest-cleanup patch; never update main or hide failures."""
import ast
from collections import Counter
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

ROOT=Path.cwd(); INFRA=ROOT/'.audit/historical-batch14'
BASE='ac215faa83917e38518b270d44e4d6f96366dad7'
TREE='4b0909bbe18643ec24aef8152549367af75e286b'
CANDIDATE=Path('/tmp/acme-backlog14-candidate'); BASELINE=Path('/tmp/acme-backlog14-baseline')
RESULTS=Path('/tmp/acme-backlog14-results'); RESULTS.mkdir(exist_ok=True)
NEW_TEST='addons/acm_extended/tools/test_historical_chest_workspace.py'
RUNTIME={'addons/acm_extended/functions/fn_chestAccessVestRestore.sqf','addons/acm_extended/functions/fn_chestSealPatientEnd.sqf'}
SNAPSHOT='tools/test_self_audit_20260922.py'
UPDATED_DIGESTS=RUNTIME|{'tools/test_fork_phase168_supine_patient_invariant.py'}
DOCS={'docs/audits/2026-09-22-historical-backlog-batch14.md','docs/audits/historical-backlog-remaining-20260922.txt'}

def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()

def run(cmd,cwd,name,env=None):
    p=subprocess.run(cmd,cwd=cwd,env=env,stdout=(RESULTS/(name+'.log')).open('w'),stderr=subprocess.STDOUT,timeout=540)
    (RESULTS/(name+'.command.json')).write_text(json.dumps({'command':cmd,'returncode':p.returncode},indent=2))
    print(name,'exit',p.returncode,flush=True);print((RESULTS/(name+'.log')).read_text()[-1800:],flush=True)
    return p.returncode

def test_bodies(text):
    out={}
    def visit(nodes,prefix=''):
        for n in nodes:
            if isinstance(n,ast.ClassDef):visit(n.body,prefix+n.name+'.')
            elif isinstance(n,ast.FunctionDef) and n.name.startswith('test_'):
                assert prefix+n.name not in out
                out[prefix+n.name]=ast.dump(n,include_attributes=False)
    visit(ast.parse(text).body);return out

def protected(text):
    for n in ast.parse(text).body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROTECTED' for t in n.targets):return ast.literal_eval(n.value)
    raise AssertionError('protected snapshots missing')

def identity(row):
    c=row.get('context','')
    if c in ('',"''",'""'):c=''
    m=re.fullmatch(r'SubtestContext\(msg=(.*?), kwargs=(.*)\)',c)
    if m:
        try:c=json.dumps([ast.literal_eval(m[1]),ast.literal_eval(m[2])],sort_keys=True,default=str)
        except (ValueError,SyntaxError):pass
    return (row['nodeid'],row['kind'],row.get('when'),row.get('type'),c)

def compare(before,after):
    a={identity(r):r for r in before};b={identity(r):r for r in after}
    fixed=[k for k in a.keys()&b.keys() if a[k]['outcome']=='failed' and b[k]['outcome']=='passed']
    regress=[k for k in a.keys()&b.keys() if a[k]['outcome']=='passed' and b[k]['outcome']!='passed']
    new=[k for k in b.keys()-a.keys() if b[k]['outcome']=='failed'];missing=list(a.keys()-b.keys())
    errors={key:[r for r in rows if r['kind']=='collection' or (r.get('when') in ('setup','teardown') and r['outcome']=='failed')] for key,rows in [('before',before),('after',after)]}
    skips={key:sum(r['outcome']=='skipped' for r in rows) for key,rows in [('before',before),('after',after)]}
    return {'fixed_count':len(fixed),'fixed':sorted(k[0] for k in fixed),'regressions':regress,'newly_failing':new,'missing_previous_outcomes':missing,'errors':errors,'skips':skips}

subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
for p in (BASELINE,CANDIDATE):subprocess.run(['git','worktree','add','--detach',str(p),BASE],check=True)
packed=b''.join((INFRA/f'payload{i}.bin').read_bytes() for i in range(3))
assert hashlib.sha256(packed).hexdigest()=='a7185d7396abb3990177b9e51364ff94cdfb3d2425bcaaa3cce6accc76b7b182'
payload=json.loads(lzma.decompress(packed));patch=payload['patch'].encode()
assert hashlib.sha256(patch).hexdigest()=='4c67d2cb2e7485b2a21dd3e3e1909b23bbd7eb19b84b23f3f4e8aa8809f94076'
(RESULTS/'reviewed.patch').write_bytes(patch)
for opts in [('--check',),()]:subprocess.run(['git','apply',*opts,str(RESULTS/'reviewed.patch')],cwd=CANDIDATE,check=True)
subprocess.run(['git','add','-A'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE
changes=git('diff','--cached','--name-status',cwd=CANDIDATE).splitlines();assert len(changes)==12
expected=RUNTIME|{NEW_TEST,SNAPSHOT}|set(payload['test_scope'])|DOCS
assert len(expected)==12
assert {s.split('\t')[1] for s in changes}==expected
assert all(s.split('\t')[0] in ('A','M') for s in changes)
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)
scope={}
for path,names in payload['test_scope'].items():
    a=test_bodies((BASELINE/path).read_text());b=test_bodies((CANDIDATE/path).read_text());assert a.keys()==b.keys(),path
    changed={k for k in a if a[k]!=b[k]};assert {k.split('.')[-1] for k in changed}==set(names),(path,changed)
    scope[path]=sorted(changed)
assert sum(map(len,scope.values()))==6
old=protected((BASELINE/SNAPSHOT).read_text());new=protected((CANDIDATE/SNAPSHOT).read_text());assert old.keys()==new.keys()
assert {k for k in old if old[k]!=new[k]}==UPDATED_DIGESTS
for p in UPDATED_DIGESTS:assert hashlib.sha256((CANDIDATE/p).read_bytes()).hexdigest()==new[p]
assert test_bodies((BASELINE/SNAPSHOT).read_text())==test_bodies((CANDIDATE/SNAPSHOT).read_text())
basefiles=set(git('ls-tree','-r','--name-only',BASE,cwd=CANDIDATE).splitlines())
assert len(basefiles-expected)==4035
(RESULTS/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime_changes':sorted(RUNTIME),'updated_preservation_digests':sorted(UPDATED_DIGESTS),'unchanged_existing_paths':4035,'deleted_files':[]},indent=2))
(RESULTS/'test-edit-scope.json').write_text(json.dumps(scope,indent=2))
print('Exact candidate and preserved source/test scope verified.',flush=True)

focused=payload['focused'];assert len(focused)==177
(RESULTS/'focused-paths.json').write_text(json.dumps(focused,indent=2))
assert run([sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(RESULTS/'focused.xml')],CANDIDATE,'focused')==0
suite=ET.parse(RESULTS/'focused.xml').getroot().find('testsuite');assert suite.attrib['tests']=='2130',suite.attrib
assert all(suite.attrib[k]=='0' for k in ('failures','errors','skipped'))
assert run([os.environ['HEMTT'],'check'],CANDIDATE,'hemtt')==0
reports={}
for label,cwd in [('before',BASELINE),('after',CANDIDATE)]:
    events=RESULTS/(label+'.jsonl');events.write_text('')
    env={**os.environ,'PYTHONPATH':str(INFRA),'AUDIT_EVENTS':str(events)}
    assert run([sys.executable,'-m','pytest','addons/acm_extended/tools','-q','--continue-on-collection-errors','--tb=short','-p','auditrecorder'],cwd,label,env)==1
    reports[label]=[json.loads(l) for l in events.read_text().splitlines()]
c=compare(reports['before'],reports['after']);c['broad_suite_still_failing']=True
(RESULTS/'comparison.json').write_text(json.dumps(c,indent=2));print(json.dumps(c,indent=2),flush=True)
assert c['fixed_count']==5 and not c['regressions'] and not c['newly_failing'] and not c['missing_previous_outcomes'] and not any(c['errors'].values())
assert c['skips']=={'before':4,'after':4}
# Record, do not hide, the separate root-suite's pre-existing collection error.
roots={}
for label,cwd in [('before',BASELINE),('after',CANDIDATE)]:
    events=RESULTS/('root-'+label+'.jsonl');events.write_text('')
    env={**os.environ,'PYTHONPATH':str(INFRA),'AUDIT_EVENTS':str(events)}
    assert run([sys.executable,'-m','pytest',*payload['root_chest'],'-q','--continue-on-collection-errors','--tb=short','-p','auditrecorder'],cwd,'root-'+label,env)==1
    roots[label]=[json.loads(l) for l in events.read_text().splitlines()]
c=compare(roots['before'],roots['after']);(RESULTS/'root-comparison.json').write_text(json.dumps(c,indent=2))
assert not c['regressions'] and not c['newly_failing'] and not c['missing_previous_outcomes']
for label in ('before','after'):
    assert len(c['errors'][label])==1 and c['errors'][label][0]['nodeid']=='tools/test_fork_phase150_flip_cancel.py'

shutil.copyfile(CANDIDATE/NEW_TEST,BASELINE/NEW_TEST)
try:
    assert run([sys.executable,'-m','pytest',NEW_TEST,'-q','--tb=short','--junitxml='+str(RESULTS/'old-control.xml')],BASELINE,'old-control')==1
    red=ET.parse(RESULTS/'old-control.xml').getroot().find('testsuite')
    assert red.attrib['tests']=='74' and red.attrib['failures']=='17' and red.attrib['errors']=='0' and red.attrib['skipped']=='0',red.attrib
finally:(BASELINE/NEW_TEST).unlink()
assert run([sys.executable,'-m','pytest',NEW_TEST,'-q','--tb=short','--junitxml='+str(RESULTS/'new-green.xml')],CANDIDATE,'new-green')==0
assert git('write-tree',cwd=CANDIDATE)==TREE
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Guard chest cleanup by physical permission and viewer generation (backlog batch 14)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch14-validated'],cwd=ROOT,check=True)
(RESULTS/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Validated isolated candidate:',commit,flush=True)
