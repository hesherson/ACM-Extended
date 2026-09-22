"""Independent test-only validation. Never updates main or suppresses test failures.

The broad suite is expected to remain failing. Its raw exit codes and every report
are retained. Publication requires exact reviewed tree identity, no runtime/asset
changes, passing focused tests/HEMTT, and no comparable passing outcome regressing.
"""
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path.cwd()
INFRA=ROOT/'.audit/historical-batch1'
BASE='19d01b8b27fd53bb9d3c381c7445add589336159'
TREE='28a46689ec00280c88576728338e6acc37b4a84d'
CANDIDATE=Path('/tmp/acme-backlog-candidate')
BASELINE=Path('/tmp/acme-backlog-baseline')
RESULTS=Path('/tmp/acme-backlog-results')
RESULTS.mkdir(exist_ok=True)

def git(*args,cwd=ROOT):
    return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()

def run(command,cwd,log,env=None):
    with (RESULTS/log).open('w') as stream:
        cp=subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
    print(log,'exit',cp.returncode,flush=True)
    print((RESULTS/log).read_text()[-4000:],flush=True)
    return cp.returncode

subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
subprocess.run(['git','worktree','add','--detach',str(CANDIDATE),BASE],check=True)
subprocess.run(['git','worktree','add','--detach',str(BASELINE),BASE],check=True)
parts=sorted(INFRA.glob('part??.patch'))
assert len(parts)==13
patch=b''.join(p.read_bytes() for p in parts)
assert hashlib.sha256(patch).hexdigest()=='3272bcd0e9aa2c96d5940ca5c1134ce98d3da4e5c694eedc06a3b7ddf73f283d'
patchfile=RESULTS/'reviewed.patch';patchfile.write_bytes(patch)
subprocess.run([sys.executable,str(INFRA/'prepare.py'),str(CANDIDATE)],check=True)
subprocess.run(['git','apply','--check',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','apply',str(patchfile)],cwd=CANDIDATE,check=True)
subprocess.run(['git','add','-A'],cwd=CANDIDATE,check=True)
actual=git('write-tree',cwd=CANDIDATE)
assert actual==TREE,(actual,TREE)
changes=git('diff','--cached','--name-status',cwd=CANDIDATE).splitlines()
assert len(changes)==89,len(changes)
for line in changes:
    status,path=line.split('\t')
    assert status in ('A','M'),line
    assert path.startswith('addons/acm_extended/tools/') or path in (
        'docs/audits/2026-09-22-historical-backlog-batch1.md',
        'docs/audits/historical-backlog-remaining-20260922.txt'),line
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)
(RESULTS/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime_or_asset_changes':[],'deleted_files':[]},indent=2))
print('Complete reviewed tree matches; all runtime source and assets preserved.',flush=True)

focused=['tools/test_self_audit_20260922.py']
focused+=['addons/acm_extended/tools/'+n for n in (
 'test_consciousness_wake_latch_20260921.py','test_seizure_paralysis_suppression.py',
 'test_seizure_gesture_unification.py','test_debug_seizure_action.py','test_bvm_startup.py',
 'test_iv_ui_followup_patch.py','test_wake_execution_20260922.py','test_config_compile.py',
 'test_confirmed_lifecycle_20260922.py','test_historical_source.py','test_historical_clinical_execution.py',
 'test_b27_junctional_cpr_bvm.py','test_b34_procedure_access.py','test_na8_5_batch8.py',
 'test_b29_narc_plunger.py','test_b29_svt_contract.py','test_b91_ace_interaction_postinit.py',
 'test_menu_death_lifecycle.py','test_native_bvm_dp.py','test_push_seconds_execution.py','test_burp_carry_repeat.py')]
assert run([sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(RESULTS/'focused.xml')],CANDIDATE,'focused.log')==0
assert run([os.environ['HEMTT'],'check'],CANDIDATE,'hemtt.log')==0

reports={}
for label,root in [('before',BASELINE),('after',CANDIDATE)]:
    events=RESULTS/(label+'.jsonl');events.write_text('')
    env={**os.environ,'PYTHONPATH':str(INFRA),'AUDIT_EVENTS':str(events)}
    command=[sys.executable,'-m','pytest','addons/acm_extended/tools','-q','--continue-on-collection-errors','--tb=short','-p','auditrecorder']
    if label=='before':command.append('--ignore=addons/acm_extended/tools/test_b77_branding_authors.py')
    code=run(command,root,label+'.log',env)
    assert code==1,(label,code)
    reports[label]=[json.loads(line) for line in events.read_text().splitlines()]
    (RESULTS/(label+'-command.json')).write_text(json.dumps({'command':command,'returncode':code},indent=2))

# Normalize rendering only. Never change an assertion or pytest outcome.
def identity(row):
    context=row.get('context','')
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
errors=[row for row in reports['after'] if row['kind']=='collection' or (row.get('when') in ('setup','teardown') and row['outcome']=='failed')]
skips={label:sum(row['outcome']=='skipped' for row in rows) for label,rows in reports.items()}
summary={'fixed_previous_failures':len(fixed),'newly_exposed_failures':len(exposed),'regressions':regressions,'errors':errors,'skips':skips,'known_broad_suite_remains_failing':True}
(RESULTS/'comparison.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2),flush=True)
assert not regressions and not errors
assert len(fixed)==183 and len(exposed)==22,(len(fixed),len(exposed))
assert skips=={'before':4,'after':4},skips
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE

# Only this new isolated candidate branch is written. No workflow or audit staging
# files enter its tree, and main must be reviewed/advanced separately.
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Resolve historical test infrastructure and verify current clinical contracts (batch 1)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch1-validated'],cwd=ROOT,check=True)
(RESULTS/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Verified isolated candidate:',commit,flush=True)
