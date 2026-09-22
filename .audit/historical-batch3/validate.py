"""Validate exact reviewed source, retain raw failures, publish audit candidate only."""
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

ROOT=Path.cwd()
INFRA=ROOT/'.audit/historical-batch3'
BASE='539c7e802261b78247a74f1208b3170a75a4734a'
TREE='fda7f899236857bc228d8ddea6c9c6e2da450fce'
CANDIDATE=Path('/tmp/acme-backlog3-candidate')
BASELINE=Path('/tmp/acme-backlog3-baseline')
RESULTS=Path('/tmp/acme-backlog3-results')
RESULTS.mkdir(exist_ok=True)
RUNTIME={
 'addons/acm_extended/functions/fn_epinephrineTakeSource.sqf',
 'addons/acm_extended/functions/fn_infusionRefundSupplies.sqf',
 'addons/acm_extended/functions/fn_medicationTakeSources.sqf',
 'addons/acm_extended/functions/fn_vialLeaseEnsure.sqf',
 'addons/acm_extended/functions/fn_vialRefund.sqf',
 'addons/acm_extended/functions/fn_vialTake.sqf',
 'addons/circulation/functions/fnc_Syringe_PrepareFinish.sqf'}

def git(*args,cwd=ROOT):
    return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()

def run(command,cwd,log,env=None):
    with (RESULTS/log).open('w') as stream:
        cp=subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=360)
    (RESULTS/(log+'.command.json')).write_text(json.dumps({'command':command,'returncode':cp.returncode},indent=2))
    print(log,'exit',cp.returncode,flush=True)
    print((RESULTS/log).read_text()[-2500:],flush=True)
    return cp.returncode

subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
for path in (CANDIDATE,BASELINE):
    subprocess.run(['git','worktree','add','--detach',str(path),BASE],check=True)
compressed=b''.join((INFRA/f'payload{i}.bin').read_bytes() for i in range(3))
assert hashlib.sha256(compressed).hexdigest()=='b57a02b039f8383b52e0e1f21891323f50810dd4317c701523a1635691c3ccb0'
patch=lzma.decompress(compressed)
assert hashlib.sha256(patch).hexdigest()=='4131cf8bd3c98aeef8f8c7d66aa99724341445abbc45f663c33adb177bf28fb2'
patchfile=RESULTS/'reviewed.patch';patchfile.write_bytes(patch)
subprocess.run(['git','apply','--check',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','apply',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','add','-A'],cwd=CANDIDATE,check=True)
actual=git('write-tree',cwd=CANDIDATE)
assert actual==TREE,(actual,TREE)
changes=git('diff','--cached','--name-status',cwd=CANDIDATE).splitlines()
assert len(changes)==18,len(changes)
production=[]
for line in changes:
    status,path=line.split('\t')
    assert status in ('A','M'),line
    if path in RUNTIME:production.append(path)
    else:
        assert path.startswith('addons/acm_extended/tools/') or path in (
            'docs/audits/2026-09-22-historical-backlog-batch3.md',
            'docs/audits/historical-backlog-remaining-20260922.txt'),line
assert set(production)==RUNTIME
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)
(RESULTS/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime_changes':production,'other_runtime_or_asset_changes':[],'deleted_files':[]},indent=2))
print('Complete reviewed tree matches; unrelated runtime source and assets unchanged.',flush=True)

focused=json.loads((INFRA/'focused-paths.json').read_text())
shutil.copyfile(INFRA/'focused-paths.json',RESULTS/'focused-paths.json')
assert run([sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(RESULTS/'focused.xml')],CANDIDATE,'focused.log')==0
suite=ET.parse(RESULTS/'focused.xml').getroot().find('testsuite')
assert suite is not None and suite.attrib['tests']=='1093',suite.attrib if suite is not None else None
assert all(suite.attrib[k]=='0' for k in ('errors','failures','skipped'))
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
assert len(fixed)==10,len(fixed)
assert skips=={'before':4,'after':4},skips

# Copy only the new test module onto the unchanged source after the baseline run.
# The old runtime must reproduce the failures, while the same candidate cases pass.
name='addons/acm_extended/tools/test_historical_vial_execution.py'
shutil.copyfile(CANDIDATE/name,BASELINE/name)
selected='pending_lease_waits_for_ack or unleased_shared_source or original_provider_self_inventory'
try:
    assert run([sys.executable,'-m','pytest',name,'-k',selected,'-q','--tb=short','--junitxml='+str(RESULTS/'vial-before.xml')],BASELINE,'vial-before.log')==1
    red=ET.parse(RESULTS/'vial-before.xml').getroot().find('testsuite')
    assert red.attrib['tests']=='14' and red.attrib['failures']=='12' and red.attrib['errors']=='0' and red.attrib['skipped']=='0',red.attrib
finally:
    (BASELINE/name).unlink()
assert run([sys.executable,'-m','pytest',name,'-k',selected,'-q','--tb=short','--junitxml='+str(RESULTS/'vial-after.xml')],CANDIDATE,'vial-after.log')==0
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE

# Never advance main or include audit infrastructure in the candidate tree.
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Fix shared vial scope guards and verify medication preparation backlog (batch 3)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch3-validated'],cwd=ROOT,check=True)
(RESULTS/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Verified isolated candidate:',commit,flush=True)
