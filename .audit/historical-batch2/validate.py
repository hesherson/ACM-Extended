"""Validate a pinned, reviewable patch before publishing an isolated candidate.

The broad suite remains failing. Raw exit codes/outcomes are retained. Only two
explicit pulse runtime paths may differ; all other production/assets are unchanged.
This script never advances main, force-pushes, or changes test outcomes.
"""
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path.cwd()
INFRA=ROOT/'.audit/historical-batch2'
BASE='5e134975242f182ebbed1225c96709eb7b2cce96'
TREE='3fd0ddb07dc760897d159129322aba9cacf4fad7'
CANDIDATE=Path('/tmp/acme-backlog2-candidate')
BASELINE=Path('/tmp/acme-backlog2-baseline')
RESULTS=Path('/tmp/acme-backlog2-results')
RESULTS.mkdir(exist_ok=True)
RUNTIME={'addons/acm_extended/functions/fn_pulsePerfusionProfile.sqf','addons/core/overrides/fnc_checkPulseLocal.sqf'}

def git(*args,cwd=ROOT):
    return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()

def run(command,cwd,log,env=None):
    with (RESULTS/log).open('w') as stream:
        cp=subprocess.run(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
    (RESULTS/(log+'.command.json')).write_text(json.dumps({'command':command,'returncode':cp.returncode},indent=2))
    print(log,'exit',cp.returncode,flush=True)
    print((RESULTS/log).read_text()[-2500:],flush=True)
    return cp.returncode

subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
for path in (CANDIDATE,BASELINE):
    subprocess.run(['git','worktree','add','--detach',str(path),BASE],check=True)
parts=sorted(INFRA.glob('part??.patch'))
assert len(parts)==6
patch=b''.join(p.read_bytes() for p in parts)
for p in parts:print(p.name,len(p.read_bytes()),hashlib.sha256(p.read_bytes()).hexdigest(),flush=True)
assert hashlib.sha256(patch).hexdigest()=='9b32ec89d4e40955eab8bf56af01ade3cae1767e855c59ba5c15ca8d4e81cb2f'
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
            'docs/audits/2026-09-22-historical-backlog-batch2.md',
            'docs/audits/historical-backlog-remaining-20260922.txt'),line
assert set(production)==RUNTIME
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)
(RESULTS/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime_changes':production,'other_runtime_or_asset_changes':[],'deleted_files':[]},indent=2))
print('Complete reviewed tree matches; unrelated production and all assets preserved.',flush=True)

prefix='addons/acm_extended/tools/'
focused=['tools/test_self_audit_20260922.py']
focused += [prefix+n for n in (
 'test_consciousness_wake_latch_20260921.py','test_seizure_paralysis_suppression.py',
 'test_seizure_gesture_unification.py','test_debug_seizure_action.py','test_bvm_startup.py',
 'test_iv_ui_followup_patch.py','test_wake_execution_20260922.py','test_config_compile.py',
 'test_confirmed_lifecycle_20260922.py','test_historical_source.py','test_historical_clinical_execution.py',
 'test_b27_junctional_cpr_bvm.py','test_b34_procedure_access.py','test_na8_5_batch8.py',
 'test_b29_narc_plunger.py','test_b29_svt_contract.py','test_b91_ace_interaction_postinit.py',
 'test_menu_death_lifecycle.py','test_native_bvm_dp.py','test_push_seconds_execution.py','test_burp_carry_repeat.py',
 'test_b17_release.py::B17Release::test_custom_rhythm_does_not_override_cpr_postshock',
 'test_b18_ventway.py::B18Source::test_rocuronium_cannot_bank_arrest_stress',
 'test_b67_cardiac_rosc_audit.py::test_b67_build_stamp_and_single_rosc_registration',
 'test_b67_cardiac_rosc_audit.py::test_all_rosc_paths_share_one_eligibility_gate',
 'test_b67_cardiac_rosc_audit.py::test_acme_no_longer_has_second_native_rate_arrest_authority',
 'test_b67_cardiac_rosc_audit.py::test_direct_arrest_call_sites_are_intentional_only',
 'test_b67_cardiac_rosc_audit.py::test_monitor_rhythm_change_is_forced_into_active_sweep',
 'test_b65_zone3_reboa_smart_bandage.py::test_aajt_occlusion_is_anatomically_scoped',
 'test_b65_zone3_reboa_smart_bandage.py::test_whole_limb_physiology_uses_single_occlusion_authority',
 'test_na8_5_batch12.py::SharedSuctionSource::test_native_clear_on_owner',
 'test_na8_5_batch12.py::EpinephrineSource::test_inventory_consumed_before_medication_event',
 'test_transfusion_thoracostomy_aftercare.py::test_aftercare_is_owner_routed_and_epoch_guarded',
 'test_b35_lifecycle.py::PtxLifecycle::test_instructor_clear_retires_model_without_touching_equipment',
 'test_b35_treatments.py::TreatmentProgressionContracts::test_callbacks_are_registered_and_old_ncd_wrapper_cannot_override_them',
 'test_b35_treatments.py::TreatmentProgressionContracts::test_seal_removal_cannot_become_a_new_injury',
 'test_b35_treatments.py::TreatmentProgressionContracts::test_sealed_surgical_tract_cannot_cover_external_chest_wounds',
 'test_historical_cardiac_execution.py','test_historical_airway_execution.py')]
(RESULTS/'focused-paths.json').write_text(json.dumps(focused,indent=2))
assert run([sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(RESULTS/'focused.xml')],CANDIDATE,'focused.log')==0
suite=ET.parse(RESULTS/'focused.xml').getroot().find('testsuite')
assert suite is not None and suite.attrib['tests']=='975',suite.attrib if suite is not None else None
assert all(suite.attrib[k]=='0' for k in ('errors','failures','skipped'))
assert run([os.environ['HEMTT'],'check'],CANDIDATE,'hemtt.log')==0

reports={}
for label,root in [('before',BASELINE),('after',CANDIDATE)]:
    events=RESULTS/(label+'.jsonl');events.write_text('')
    env={**os.environ,'PYTHONPATH':str(INFRA),'AUDIT_EVENTS':str(events)}
    command=[sys.executable,'-m','pytest',prefix.rstrip('/'),'-q','--continue-on-collection-errors','--tb=short','-p','auditrecorder']
    assert run(command,root,label+'.log',env)==1
    reports[label]=[json.loads(line) for line in events.read_text().splitlines()]

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
errors={label:[row for row in rows if row['kind']=='collection' or (row.get('when') in ('setup','teardown') and row['outcome']=='failed')] for label,rows in reports.items()}
skips={label:sum(row['outcome']=='skipped' for row in rows) for label,rows in reports.items()}
summary={'fixed_previous_failures':len(fixed),'newly_exposed_failures':len(exposed),'regressions':regressions,'errors':errors,'skips':skips,'known_broad_suite_remains_failing':True,'resolved_nodeids':[key[0] for key in fixed]}
(RESULTS/'comparison.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2),flush=True)
assert not regressions and not any(errors.values()) and not exposed
assert len(fixed)==16,len(fixed)
assert skips=={'before':4,'after':4},skips

# Independent red-green proof: add only the new test to the old source, AFTER its
# unchanged broad baseline run. No production source is edited in that worktree.
name=prefix+'test_historical_cardiac_execution.py'
shutil.copyfile(CANDIDATE/name,BASELINE/name)
selected='aajt_pulse_occlusion_is_site_specific or pulse_restores_when_the_aajt_is_removed or compression_generated_pulses_do_not_bypass'
try:
    assert run([sys.executable,'-m','pytest',name,'-k',selected,'-q','--tb=short','--junitxml='+str(RESULTS/'pulse-before.xml')],BASELINE,'pulse-before.log')==1
    red=ET.parse(RESULTS/'pulse-before.xml').getroot().find('testsuite')
    assert red.attrib['tests']=='14' and red.attrib['failures']=='10' and red.attrib['errors']=='0' and red.attrib['skipped']=='0',red.attrib
finally:
    (BASELINE/name).unlink()
assert run([sys.executable,'-m','pytest',name,'-k',selected,'-q','--tb=short'],CANDIDATE,'pulse-after.log')==0
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE

# Publish only a new isolated reviewable candidate. Main advancement is separate.
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Fix AAJT pulse occlusion and verify historical cardiac and airway contracts (batch 2)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch2-validated'],cwd=ROOT,check=True)
(RESULTS/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Verified isolated candidate:',commit,flush=True)
