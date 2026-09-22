"""Independent exact-tree validation; publish an isolated candidate, never main.

Raw broad-suite failures remain visible. Focused/red-green checks, source scope,
old test body preservation and full outcome identity comparisons gate publication.
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
INFRA=ROOT/'.audit/historical-batch6'
BASE='f44efd601cad1f0f47c5f0bb28a37a9d42731ace'
TREE='d5c450ec3f2a393ff9c1ca26edfcd76cf7485917'
CANDIDATE=Path('/tmp/acme-backlog6-candidate')
BASELINE=Path('/tmp/acme-backlog6-baseline')
RESULTS=Path('/tmp/acme-backlog6-results')
RESULTS.mkdir(exist_ok=True)
PREFIX='addons/acm_extended/tools/'
RUNTIME={'addons/acm_extended/functions/fn_'+name+'.sqf' for name in (
 'thoraSelectTool','thoraSlotHover','laryngoPassTube','laryngoConsequenceLocal')}
ALLOWED_TESTS={
 'test_b34_tray_silhouettes.py':{'test_existing_thoracostomy_shadow_survives_hover_and_inventory_refresh'},
 'test_b44_requested_fixes.py':{'test_airway_patent_suffix'},
 'test_na8_5_batch4.py':{'test_captured_medic_used_for_inventory','test_held_tool_does_not_change_with_inventory','test_hover_selects_shared_slot'},
 'test_na8_5_batch12.py':{'test_delayed_callbacks_check_display_patient','test_no_two_way_mouth_dissolve','test_success_resets_streak'}}
NEW_TESTS=[PREFIX+'test_historical_procedure_trays.py',PREFIX+'test_historical_laryngoscopy_execution.py']

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
compressed=b''.join((INFRA/f'payload{i}.bin').read_bytes() for i in range(2))
assert hashlib.sha256(compressed).hexdigest()=='05cdf4a438121b97c8946d71536cc5863f5d0771bfa5d174c1058d703d106441'
patch=lzma.decompress(compressed)
assert hashlib.sha256(patch).hexdigest()=='1031de20e0f68a49ed489583bea28b1d36a50b110ab40b1c35faaa2fda091913'
patchfile=RESULTS/'reviewed.patch';patchfile.write_bytes(patch)
subprocess.run(['git','apply','--check',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','apply',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','add','-A'],cwd=CANDIDATE,check=True)
actual=git('write-tree',cwd=CANDIDATE)
assert actual==TREE,(actual,TREE)
changes=git('diff','--cached','--name-status',cwd=CANDIDATE).splitlines()
assert len(changes)==12,len(changes)
production=[]
for line in changes:
    status,path=line.split('\t')
    assert status in ('A','M'),line
    if path in RUNTIME:production.append(path)
    else:
        assert path.startswith(PREFIX) or path in (
            'docs/audits/2026-09-22-historical-backlog-batch6.md',
            'docs/audits/historical-backlog-remaining-20260922.txt'),line
assert set(production)==RUNTIME
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)
# Parse complete modules so renamed/deleted unrelated tests cannot disappear silently.
scope={}
for name,allowed in ALLOWED_TESTS.items():
    old=ast.parse((BASELINE/PREFIX/name).read_text())
    new=ast.parse((CANDIDATE/PREFIX/name).read_text())
    def functions(tree):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
    a,b=functions(old),functions(new)
    assert a.keys()==b.keys(),name
    changed={key for key in a if a[key]!=b[key]}
    assert changed==allowed,(name,changed,allowed)
    scope[name]=sorted(changed)
(RESULTS/'test-edit-scope.json').write_text(json.dumps(scope,indent=2))
(RESULTS/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime_changes':sorted(production),'other_runtime_or_asset_changes':[],'deleted_files':[]},indent=2))
print('Complete reviewed tree matches; unrelated runtime source, assets and test bodies preserved.',flush=True)

focused=json.loads((INFRA/'focused-paths.json').read_text())
shutil.copyfile(INFRA/'focused-paths.json',RESULTS/'focused-paths.json')
assert len(focused)==96
assert run([sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(RESULTS/'focused.xml')],CANDIDATE,'focused.log')==0
suite=ET.parse(RESULTS/'focused.xml').getroot().find('testsuite')
assert suite is not None and suite.attrib['tests']=='1330',suite.attrib if suite is not None else None
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
summary={'fixed_count':len(fixed),'newly_failing':exposed,'regressions':regressions,'errors':errors,'missing_previous_outcomes':missing,'skips':skips,'known_broad_suite_remains_failing':True,'fixed':sorted(key[0] for key in fixed)}
(RESULTS/'comparison.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2),flush=True)
assert not regressions and not any(errors.values()) and not exposed and not missing
assert len(fixed)==7,len(fixed)
assert skips=={'before':4,'after':4},skips

# Red control copies only the new tests onto unchanged runtime source, after the baseline run.
for name in NEW_TESTS:shutil.copyfile(CANDIDATE/name,BASELINE/name)
try:
    assert run([sys.executable,'-m','pytest',*NEW_TESTS,'-q','--tb=short','--junitxml='+str(RESULTS/'red-control.xml')],BASELINE,'red-control.log')==1
    red=ET.parse(RESULTS/'red-control.xml').getroot().find('testsuite')
    assert red.attrib['tests']=='73' and red.attrib['failures']=='16' and red.attrib['errors']=='0' and red.attrib['skipped']=='0',red.attrib
finally:
    for name in NEW_TESTS:(BASELINE/name).unlink()
assert run([sys.executable,'-m','pytest',*NEW_TESTS,'-q','--tb=short','--junitxml='+str(RESULTS/'new-green.xml')],CANDIDATE,'new-green.log')==0
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE

# Only an isolated candidate is written. Main publication requires a separate reviewed fast-forward.
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Fix procedure-selection scope and laryngoscopy reflex boundaries (backlog batch 6)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch6-validated'],cwd=ROOT,check=True)
(RESULTS/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Verified isolated candidate:',commit,flush=True)
