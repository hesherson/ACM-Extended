"""Validate the exact reviewed batch; retain failures; publish an audit candidate only.

Only three one-line native UI-writer call corrections are authorized. The broad
historical suite remains failing. This workflow never modifies main or suppresses
pytest outcomes, and its own infrastructure does not enter the candidate tree.
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
INFRA=ROOT/'.audit/historical-batch5'
BASE='156adfb6c0486af0cd2861062e9d40c6574bd030'
TREE='d56e0df51f8697587f45f9ec233bd9395705fd3c'
CANDIDATE=Path('/tmp/acme-backlog5-candidate')
BASELINE=Path('/tmp/acme-backlog5-baseline')
RESULTS=Path('/tmp/acme-backlog5-results')
RESULTS.mkdir(exist_ok=True)
RUNTIME={
 'addons/acm_extended/functions/fn_initMedicationRegistry.sqf',
 'addons/acm_extended/functions/fn_restoreMedicationList.sqf',
 'addons/acm_extended/functions/fn_vialHolder.sqf'}
NEW_TESTS=[
 'addons/acm_extended/tools/test_historical_medication_rows.py',
 'addons/acm_extended/tools/test_vial_holder_fallback_20260922.py']

def git(*args,cwd=ROOT):
    return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()

def run(command,cwd,log,env=None):
    with (RESULTS/log).open('w') as stream:
        cp=subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=360)
    (RESULTS/(log+'.command.json')).write_text(json.dumps({'command':command,'returncode':cp.returncode},indent=2))
    print(log,'exit',cp.returncode,flush=True)
    print((RESULTS/log).read_text()[-2500:],flush=True)
    return cp.returncode

def junit(path,count,failures):
    suite=ET.parse(path).getroot().find('testsuite')
    assert suite is not None
    assert suite.attrib['tests']==str(count),suite.attrib
    assert suite.attrib['failures']==str(failures),suite.attrib
    assert suite.attrib['errors']=='0' and suite.attrib['skipped']=='0',suite.attrib

subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
for path in (CANDIDATE,BASELINE):
    subprocess.run(['git','worktree','add','--detach',str(path),BASE],check=True)
compressed=b''.join((INFRA/f'payload{i}.bin').read_bytes() for i in range(2))
assert hashlib.sha256(compressed).hexdigest()=='81651c11e94464647b633938cacafdcdf0e0df02ea10914e66db2009b0487b04'
payload=json.loads(lzma.decompress(compressed))
patch=payload['patch'].encode('utf-8')
assert hashlib.sha256(patch).hexdigest()=='99db1acbb35305c5761f60a9fefd4b0ed4311bfc1998c7dedb1ec79177c41333'
patchfile=RESULTS/'reviewed.patch';patchfile.write_bytes(patch)
subprocess.run(['git','apply','--check',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','apply',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','add','-A'],cwd=CANDIDATE,check=True)
actual=git('write-tree',cwd=CANDIDATE)
assert actual==TREE,(actual,TREE)
changes=git('diff','--cached','--name-status',cwd=CANDIDATE).splitlines()
assert len(changes)==14,len(changes)
production=[]
for line in changes:
    status,path=line.split('\t')
    assert status in ('A','M'),line
    if path in RUNTIME:production.append(path)
    else:
        assert path.startswith('addons/acm_extended/tools/') or path in (
            'docs/audits/2026-09-22-historical-backlog-batch5.md',
            'docs/audits/historical-backlog-remaining-20260922.txt'),line
assert set(production)==RUNTIME
for line in git('diff','--cached','--numstat',cwd=CANDIDATE).splitlines():
    add,remove,path=line.split('\t')
    if path in RUNTIME:assert (add,remove)==('1','1'),line
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)
(RESULTS/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime_changes':production,'runtime_lines_added':3,'runtime_lines_removed':3,'other_runtime_or_asset_changes':[],'deleted_files':[]},indent=2))
print('Exact reviewed tree verified; all unrelated runtime source/assets preserved.',flush=True)

focused=payload['focused']
(RESULTS/'focused-paths.json').write_text(json.dumps(focused,indent=2))
assert run([sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(RESULTS/'focused.xml')],CANDIDATE,'focused.log')==0
junit(RESULTS/'focused.xml',1249,0)
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
assert len(fixed)==15 and set(key[0] for key in fixed)==set(payload['resolved'])
assert skips=={'before':4,'after':4},skips

# Same new tests on unchanged runtime. Copy only new test modules AFTER the
# baseline run, so the broad baseline population remains strictly unchanged.
try:
    for path in NEW_TESTS:shutil.copyfile(CANDIDATE/path,BASELINE/path)
    assert run([sys.executable,'-m','pytest',*NEW_TESTS,'-q','--tb=short','--junitxml='+str(RESULTS/'red-control.xml')],BASELINE,'red-control.log')==1
    junit(RESULTS/'red-control.xml',43,8)
finally:
    for path in NEW_TESTS:(BASELINE/path).unlink(missing_ok=True)
assert run([sys.executable,'-m','pytest',*NEW_TESTS,'-q','--tb=short','--junitxml='+str(RESULTS/'green-control.xml')],CANDIDATE,'green-control.log')==0
junit(RESULTS/'green-control.xml',43,0)
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE

# Publish only the verified candidate, not audit infrastructure or main.
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Fix medication catalog and source-selector writes; verify historical row contracts (batch 5)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch5-validated'],cwd=ROOT,check=True)
(RESULTS/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Verified isolated candidate:',commit,flush=True)
