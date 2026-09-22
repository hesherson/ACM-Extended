"""Verify the reviewed batch-4 tree and raw outcomes; publish an isolated candidate only.

The broad suite is deliberately not a green gate. Its original failure exit and
all outcomes remain recorded. No workflow, assertion override or audit payload is
included in the candidate, and main is never updated here.
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
INFRA=ROOT/'.audit/historical-batch4'
BASE='d1b4cd550a7f93d7aa9536c731edcc4958387e45'
TREE='a944bf8bc497b10ecb8428bb0bf798e61fec7a94'
CANDIDATE=Path('/tmp/acme-backlog4-candidate')
BASELINE=Path('/tmp/acme-backlog4-baseline')
RESULTS=Path('/tmp/acme-backlog4-results')
RESULTS.mkdir(exist_ok=True)
RUNTIME={'addons/breathing/functions/fnc_inspectChestLocal.sqf','addons/acm_extended/functions/fn_obtundedTick.sqf'}


def git(*args,cwd=ROOT):
    return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()


def run(command,cwd,log,env=None):
    with (RESULTS/log).open('w') as stream:
        cp=subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=360)
    (RESULTS/(log+'.command.json')).write_text(json.dumps({'command':command,'returncode':cp.returncode},indent=2))
    print(log,'exit',cp.returncode,flush=True)
    print((RESULTS/log).read_text()[-2500:],flush=True)
    return cp.returncode


def junit(name,tests,failures=0):
    suite=ET.parse(RESULTS/name).getroot().find('testsuite')
    assert suite is not None,name
    assert suite.attrib['tests']==str(tests),suite.attrib
    assert suite.attrib['failures']==str(failures),suite.attrib
    assert suite.attrib['errors']=='0' and suite.attrib['skipped']=='0',suite.attrib


subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
for path in (CANDIDATE,BASELINE):
    subprocess.run(['git','worktree','add','--detach',str(path),BASE],check=True)
compressed=b''.join((INFRA/f'payload{i}.bin').read_bytes() for i in range(3))
assert hashlib.sha256(compressed).hexdigest()=='2f6c8a651e169b0d36d6f0ad3ed56bb3e363f3ed466871556fe44809e4c6954b'
payload=json.loads(lzma.decompress(compressed))
patch=payload['patch'].encode('utf-8')
assert hashlib.sha256(patch).hexdigest()=='35dca9a370faf70b6bb576c4a8df753b7af6a4c5f2513cfa6ea08dd8c01f7b84'
assert payload['meta']['base']==BASE and payload['meta']['tree']==TREE
patchfile=RESULTS/'reviewed.patch';patchfile.write_bytes(patch)
subprocess.run(['git','apply','--check',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','apply',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','add','-A'],cwd=CANDIDATE,check=True)
actual=git('write-tree',cwd=CANDIDATE)
assert actual==TREE,(actual,TREE)
changes=git('diff','--cached','--name-status',cwd=CANDIDATE).splitlines()
assert changes==payload['meta']['changes'] and len(changes)==11,changes
production=[]
for line in changes:
    status,path=line.split('\t')
    assert status in ('A','M'),line
    if path in RUNTIME:production.append(path)
    else:
        assert path.startswith('addons/acm_extended/tools/') or path in (
            'docs/audits/2026-09-22-historical-backlog-batch4.md',
            'docs/audits/historical-backlog-remaining-20260922.txt'),line
assert set(production)==RUNTIME
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)
(RESULTS/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime_changes':production,'other_runtime_or_asset_changes':[],'deleted_files':[]},indent=2))
print('Complete reviewed tree matches; unrelated runtime files and assets preserved.',flush=True)

focused=payload['focused_paths']
(RESULTS/'focused-paths.json').write_text(json.dumps(focused,indent=2))
assert run([sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(RESULTS/'focused.xml')],CANDIDATE,'focused.log')==0
junit('focused.xml',1191)
assert run([os.environ['HEMTT'],'check'],CANDIDATE,'hemtt.log')==0

reports={}
for label,root in [('before',BASELINE),('after',CANDIDATE)]:
    events=RESULTS/(label+'.jsonl');events.write_text('')
    env={**os.environ,'PYTHONPATH':str(INFRA),'AUDIT_EVENTS':str(events)}
    command=[sys.executable,'-m','pytest','addons/acm_extended/tools','-q','--continue-on-collection-errors','--tb=short','-p','auditrecorder']
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
errors={label:[row for row in rows if row['kind']=='collection' or (row.get('when') in ('setup','teardown') and row['outcome']=='failed')] for label,rows in reports.items()}
skips={label:sum(row['outcome']=='skipped' for row in rows) for label,rows in reports.items()}
summary={'fixed_previous_failures':len(fixed),'newly_failing_identities':len(exposed),'regressions':regressions,'errors':errors,'skips':skips,'known_broad_suite_remains_failing':True,'resolved_nodeids':sorted(key[0] for key in fixed)}
(RESULTS/'comparison.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2),flush=True)
assert not regressions and not any(errors.values()) and not exposed
assert len(fixed)==12,len(fixed)
assert skips=={'before':4,'after':4},skips

# Only new regression tests are copied to the unchanged baseline AFTER its broad run.
# The real old runtime must fail; the same tests pass against the corrected source.
redfiles=['addons/acm_extended/tools/test_historical_assessment_execution.py','addons/acm_extended/tools/test_historical_state_cleanup.py']
for name in redfiles:shutil.copyfile(CANDIDATE/name,BASELINE/name)
try:
    assert run([sys.executable,'-m','pytest',*redfiles,'-q','--tb=short','--junitxml='+str(RESULTS/'regression-before.xml')],BASELINE,'regression-before.log')==1
    junit('regression-before.xml',48,22)
finally:
    for name in redfiles:(BASELINE/name).unlink()
assert run([sys.executable,'-m','pytest',*redfiles,'-q','--tb=short','--junitxml='+str(RESULTS/'regression-after.xml')],CANDIDATE,'regression-after.log')==0
junit('regression-after.xml',48)
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE

# Publish only a new review branch. No main update, force push, audit files or workflows.
env={**os.environ,'GIT_AUTHOR_NAME':'github-actions[bot]','GIT_AUTHOR_EMAIL':'41898282+github-actions[bot]@users.noreply.github.com','GIT_COMMITTER_NAME':'github-actions[bot]','GIT_COMMITTER_EMAIL':'41898282+github-actions[bot]@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Fix chest assessment output and verify menu/state cleanup backlog (batch 4)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch4-validated'],cwd=ROOT,check=True)
(RESULTS/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Verified isolated candidate:',commit,flush=True)
