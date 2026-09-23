"""Verify exact carousel candidate and preserve raw historical failures.

Publish only the isolated validated branch. No main update, forced push,
assertion rewriting or failure suppression occurs here.
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
INFRA=ROOT/'.audit/historical-batch10'
BASE='125dd48d6a4d463ce9e5fe87368385a5fdf52c2d'
TREE='8f549e5dd6e6eeecc9202e374c32d227e5b9a91e'
CANDIDATE=Path('/tmp/acme-backlog10-candidate')
BASELINE=Path('/tmp/acme-backlog10-baseline')
RESULTS=Path('/tmp/acme-backlog10-results')
RESULTS.mkdir(exist_ok=True)
PREFIX='addons/acm_extended/tools/'
RUNTIME={'addons/acm_extended/functions/fn_'+name+'.sqf' for name in (
    'skCarouselPick','skCarouselMove','skInject','skUiTick')}
NEW_TEST=PREFIX+'test_historical_carousel_input.py'
DOCS={'docs/audits/2026-09-22-historical-backlog-batch10.md',
      'docs/audits/historical-backlog-remaining-20260922.txt'}

def git(*args,cwd=ROOT):
    return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()

def run(command,cwd,log,env=None):
    with (RESULTS/log).open('w') as stream:
        cp=subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=420)
    (RESULTS/(log+'.command.json')).write_text(json.dumps({'command':command,'returncode':cp.returncode},indent=2))
    print(log,'exit',cp.returncode,flush=True)
    print((RESULTS/log).read_text()[-2500:],flush=True)
    return cp.returncode

subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
for path in (CANDIDATE,BASELINE):
    subprocess.run(['git','worktree','add','--detach',str(path),BASE],check=True)
compressed=b''.join((INFRA/f'payload{i}.bin').read_bytes() for i in range(2))
assert hashlib.sha256(compressed).hexdigest()=='8ad661a2ae3b3163223c4040f27893f0131cd371e41d04f682f1e06a3944a20c'
payload=json.loads(lzma.decompress(compressed))
patch=payload['patch'].encode('utf-8')
assert hashlib.sha256(patch).hexdigest()=='bbb7bb5793b53d5f5fd2c44a9a9037de370c4ec627a5d13b42c227fda06995dd'
patchfile=RESULTS/'reviewed.patch';patchfile.write_bytes(patch)
subprocess.run(['git','apply','--check',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','apply',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','add','-A'],cwd=CANDIDATE,check=True)
actual=git('write-tree',cwd=CANDIDATE)
assert actual==TREE,(actual,TREE)
changes=git('diff','--cached','--name-status',cwd=CANDIDATE).splitlines()
assert len(changes)==16,len(changes)
expected=RUNTIME|DOCS|{NEW_TEST}|{PREFIX+n for n in payload['test_scope']}
assert len(expected)==16
paths=set()
for line in changes:
    status,path=line.split('\t')
    assert status in ('A','M') and path in expected,line
    paths.add(path)
assert paths==expected
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)

# Preserve all old test identities and restrict edits to the reviewed twelve bodies.
def functions(tree):
    result={}
    def visit(nodes,prefix=''):
        for node in nodes:
            if isinstance(node,ast.ClassDef):visit(node.body,prefix+node.name+'.')
            elif isinstance(node,ast.FunctionDef) and node.name.startswith('test_'):
                assert prefix+node.name not in result
                result[prefix+node.name]=ast.dump(node,include_attributes=False)
    visit(tree.body)
    return result
scope={}
for name,allowed in payload['test_scope'].items():
    a=functions(ast.parse((BASELINE/PREFIX/name).read_text()))
    b=functions(ast.parse((CANDIDATE/PREFIX/name).read_text()))
    assert a.keys()==b.keys(),name
    changed={key for key in a if a[key]!=b[key]}
    assert {key.split('.')[-1] for key in changed}==set(allowed),(name,changed,allowed)
    scope[name]=sorted(changed)
assert sum(map(len,scope.values()))==12
(RESULTS/'test-edit-scope.json').write_text(json.dumps(scope,indent=2))
base_paths=set(git('ls-tree','-r','--name-only',BASE,cwd=CANDIDATE).splitlines())
unchanged=len(base_paths-paths)
assert unchanged==4022,unchanged
(RESULTS/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime_changes':sorted(RUNTIME),'unchanged_existing_paths':unchanged,'deleted_files':[]},indent=2))
print('Exact reviewed tree, runtime scope and preserved historical test bodies verified.',flush=True)

focused=payload['focused']
(RESULTS/'focused-paths.json').write_text(json.dumps(focused,indent=2))
assert len(focused)==136,len(focused)
assert run([sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(RESULTS/'focused.xml')],CANDIDATE,'focused.log')==0
suite=ET.parse(RESULTS/'focused.xml').getroot().find('testsuite')
assert suite is not None and suite.attrib['tests']=='1688',suite.attrib if suite is not None else None
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
exposed=[key for key in after.keys()-before.keys() if after[key]['outcome']=='failed']
missing=list(before.keys()-after.keys())
errors={label:[row for row in rows if row['kind']=='collection' or (row.get('when') in ('setup','teardown') and row['outcome']=='failed')] for label,rows in reports.items()}
skips={label:sum(row['outcome']=='skipped' for row in rows) for label,rows in reports.items()}
summary={'fixed_count':len(fixed),'newly_failing':exposed,'regressions':regressions,'errors':errors,'missing_previous_outcomes':missing,'skips':skips,'broad_suite_still_failing':True,'fixed':sorted(key[0] for key in fixed)}
(RESULTS/'comparison.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2),flush=True)
assert not regressions and not any(errors.values()) and not exposed and not missing
assert len(fixed)==12,len(fixed)
assert skips=={'before':4,'after':4},skips

# Add only new tests to the old runtime, after its unchanged broad baseline run.
shutil.copyfile(CANDIDATE/NEW_TEST,BASELINE/NEW_TEST)
try:
    assert run([sys.executable,'-m','pytest',NEW_TEST,'-q','--tb=short','--junitxml='+str(RESULTS/'red-control.xml')],BASELINE,'red-control.log')==1
    red=ET.parse(RESULTS/'red-control.xml').getroot().find('testsuite')
    assert red.attrib['tests']=='97' and red.attrib['failures']=='31' and red.attrib['errors']=='0' and red.attrib['skipped']=='0',red.attrib
finally:
    (BASELINE/NEW_TEST).unlink()
assert run([sys.executable,'-m','pytest',NEW_TEST,'-q','--tb=short','--junitxml='+str(RESULTS/'new-green.xml')],CANDIDATE,'new-green.log')==0
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE

# This publishes only the isolated candidate, not main or the temporary workflow.
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Fix carousel callback and held-key lifecycle; verify historical navigation contracts (batch 10)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch10-validated'],cwd=ROOT,check=True)
(RESULTS/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Verified isolated candidate:',commit,flush=True)
