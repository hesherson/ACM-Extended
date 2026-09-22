"""Hash-gated, test-only reconciliation and independent validation.

The complete patch is plaintext. Only twelve explicitly reviewed test/doc paths
are allowed. This script never updates main. A validated candidate is published
only to a new audit branch after both full runs and preservation checks complete.
"""
from pathlib import Path
import collections
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path.cwd()
BASE='5e134975242f182ebbed1225c96709eb7b2cce96'
TREE='e5711330234b5b966557b9fb21274738623ba0e6'
PATCH_SHA='895cb85b9d4da6bdcbca189f2e08017debff4a60fc2f541818c2f0b29da7a732'
DEST=Path('/tmp/additional-backlog-candidate')
BEFORE=Path('/tmp/additional-backlog-base')
OUT=Path('/tmp/additional-backlog-results'); OUT.mkdir(exist_ok=True)
ALLOWED={
 'addons/acm_extended/tools/backlog_clinical_probes.py',
 'addons/acm_extended/tools/backlog_contract_expression.py',
 'addons/acm_extended/tools/test_b17_release.py',
 'addons/acm_extended/tools/test_b18_ventway.py',
 'addons/acm_extended/tools/test_b19_vials_pea_artifact.py',
 'addons/acm_extended/tools/test_b21_rhythm_sync.py',
 'addons/acm_extended/tools/test_b35_lifecycle.py',
 'addons/acm_extended/tools/test_b35_treatments.py',
 'addons/acm_extended/tools/test_backlog_contract_expression.py',
 'docs/audits/2026-09-22-historical-backlog-batch2.json',
 'docs/audits/2026-09-22-historical-backlog-batch2.md',
 'docs/audits/historical-backlog-remaining-20260922.txt',
}

def git(*args,cwd=ROOT):
 return subprocess.check_output(['git',*args],cwd=cwd)

def run(args,cwd,label,expected=0,timeout=480):
 p=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 (OUT/(label+'.log')).write_text(p.stdout)
 print(label,'exit',p.returncode,flush=True); print(p.stdout[-1600:],flush=True)
 assert p.returncode==expected,(label,p.returncode)
 return p

def stats(path):
 suites=list(ET.parse(path).getroot().iter('testsuite'))
 return {key:sum(int(s.get(key,'0')) for s in suites) for key in ('tests','failures','errors','skipped')}

def outcomes(path):
 result=collections.defaultdict(set)
 for c in ET.parse(path).getroot().iter('testcase'):
  state='failure' if c.find('failure') is not None else 'error' if c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
  result[c.get('classname',''),c.get('name','')].add(state)
 return result

parts=[]
for i in range(6):
 data=(ROOT/f'.audit/additional-backlog-{i:02d}.patch').read_bytes()
 if i==1:
  # Correct only a known transfer-format mistake: this chunk acquired one extra
  # '+' from its first file boundary onward. The complete corrected plaintext
  # MUST still match the independently prepared SHA below, before any application.
  marker=b'\n+diff --git '
  if marker in data:
   start=data.index(marker)+1
   lines=data[start:].splitlines(keepends=True)
   assert all(line.startswith(b'+') for line in lines)
   data=data[:start]+b''.join(line[1:] for line in lines)
   print('Removed the known extra transfer prefix in chunk 1; exact patch SHA remains mandatory.',flush=True)
 parts.append(data)
payload=b''.join(parts)
actual=hashlib.sha256(payload).hexdigest()
print('Complete reviewed patch SHA:',actual,flush=True)
assert actual==PATCH_SHA,'Transferred content differs from reviewed candidate'
patch=OUT/'reviewed.patch';patch.write_bytes(payload)
rows=git('apply','--numstat',str(patch)).decode().splitlines()
assert len(rows)==len(ALLOWED)
assert {r.split('\t',2)[2] for r in rows}==ALLOWED
assert all(r.split('\t')[0].isdecimal() and r.split('\t')[1].isdecimal() for r in rows)
subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
subprocess.run(['git','worktree','add','--detach',str(DEST),BASE],check=True)
subprocess.run(['git','worktree','add','--detach',str(BEFORE),BASE],check=True)
subprocess.run(['git','apply','--check',str(patch)],cwd=DEST,check=True)
subprocess.run(['git','apply','--index',str(patch)],cwd=DEST,check=True)
assert git('write-tree',cwd=DEST).decode().strip()==TREE
changed=git('diff','--cached','--name-status',cwd=DEST).decode().splitlines()
assert {r.split('\t',1)[1] for r in changed}==ALLOWED
assert all(r.split('\t',1)[0] in ('A','M') for r in changed)
subprocess.run(['git','diff','--cached','--check'],cwd=DEST,check=True)
(OUT/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'production_changes':0,'asset_changes':0,'deleted_files':0,'changed_paths':changed,'patch_sha256':actual},indent=2))

modules=['test_b17_release.py','test_b18_ventway.py','test_b19_vials_pea_artifact.py',
 'test_b21_rhythm_sync.py','test_b27_junctional_cpr_bvm.py','test_b29_narc_plunger.py',
 'test_b29_svt_contract.py','test_b34_procedure_access.py','test_b35_lifecycle.py',
 'test_b35_treatments.py','test_b91_ace_interaction_postinit.py','test_backlog_contract_expression.py',
 'test_burp_carry_repeat.py','test_bvm_startup.py','test_config_compile.py',
 'test_confirmed_lifecycle_20260922.py','test_consciousness_wake_latch_20260921.py',
 'test_debug_seizure_action.py','test_historical_clinical_execution.py','test_historical_source.py',
 'test_iv_ui_followup_patch.py','test_menu_death_lifecycle.py','test_na8_5_batch8.py',
 'test_native_bvm_dp.py','test_push_seconds_execution.py','test_seizure_gesture_unification.py',
 'test_seizure_paralysis_suppression.py','test_wake_execution_20260922.py']
focused=['addons/acm_extended/tools/'+m for m in modules]+['tools/test_self_audit_20260922.py']
run(['python3','-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(OUT/'focused.xml')],DEST,'focused')
assert stats(OUT/'focused.xml')=={'tests':946,'failures':0,'errors':0,'skipped':0}
common=['python3','-m','pytest','addons/acm_extended/tools','--continue-on-collection-errors','-q','--tb=line']
run([*common,'--junitxml='+str(OUT/'before.xml')],BEFORE,'before',expected=1)
run([*common,'--junitxml='+str(OUT/'after.xml')],DEST,'after',expected=1)
before,after=stats(OUT/'before.xml'),stats(OUT/'after.xml')
assert before=={'tests':8326,'failures':299,'errors':0,'skipped':4},before
assert after=={'tests':8331,'failures':286,'errors':0,'skipped':4},after
b,a=outcomes(OUT/'before.xml'),outcomes(OUT/'after.xml')
regressions=[key for key,states in a.items() if 'failure' in states and b.get(key)=={'passed'}]
assert not regressions,regressions
ledger=json.loads((DEST/'docs/audits/2026-09-22-historical-backlog-batch2.json').read_text())
assert len(ledger['resolved_source_contracts'])==11
for row in ledger['resolved_source_contracts']:
 pieces=row['verified_nodeid'].split('::')
 key=('.'.join([pieces[0].removesuffix('.py').replace('/','.'),*pieces[1:-1]]),pieces[-1])
 assert a.get(key)=={'passed'},(row['id'],key,a.get(key))
run([os.environ['HEMTT'],'check'],DEST,'hemtt',timeout=240)
assert git('write-tree',cwd=DEST).decode().strip()==TREE
assert not git('diff','--name-only',cwd=DEST).strip(),'Validation changed tracked source'
summary={'base':BASE,'candidate_tree':TREE,'focused':stats(OUT/'focused.xml'),'before':before,'after':after,'previous_passes_newly_failing':regressions,'resolved_source_contract_ids':[r['id'] for r in ledger['resolved_source_contracts']],'remaining_source_contracts':238,'production_changes':0,'asset_changes':0,'hemtt_check_exit':0,'full_historical_suite_clean':False}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
branch='audit/historical-backlog-additional-20260922'
assert not git('ls-remote','--heads','origin','refs/heads/'+branch).strip(),'Candidate branch already exists'
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Verify additional historical contracts without altering production behavior'],cwd=DEST,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/'+branch],cwd=ROOT,check=True)
(OUT/'candidate-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'branch':branch},indent=2))
print('Published isolated test-only candidate:',commit,'main untouched',flush=True)
