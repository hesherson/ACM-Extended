"""Independently verify the exact reviewed candidate; never advance main.

The broad suite must retain its genuine failures. Publication to an isolated
branch requires preservation checks, focused execution, HEMTT and red controls.
"""
import ast, hashlib, json, lzma, os, re, shutil, subprocess, sys
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path.cwd(); INFRA=ROOT/'.audit/historical-batch7'
BASE='0b583737f8542a56fb66ad739c587aaadf3deefd'
TREE='f06ae5fb92dcb6ae39516cac6f8fac68f7249868'
OUT=Path('/tmp/acme-backlog7-results'); OUT.mkdir(exist_ok=True)
CANDIDATE=Path('/tmp/acme-backlog7-candidate'); BASELINE=Path('/tmp/acme-backlog7-baseline')
PREFIX='addons/acm_extended/tools/'
NEW=[PREFIX+'test_historical_ecg_artifact_execution.py',PREFIX+'test_historical_junctional_execution.py']
RUNTIME={'addons/acm_extended/functions/fn_ecgArtifactStrength.sqf','addons/acm_extended/functions/fn_junctionalStartBleed.sqf'}
CHANGED_FUNCTIONS={
 'test_b19_vials_pea_artifact.py':{'test_ace_timer_events_drive_artifact','test_monitor_generators_apply_artifact','test_pea_morphology_distinct_from_sinus'},
 'test_b21_rhythm_sync.py':{'test_threshold_forced_vt_can_recover_but_true_vt_is_not_blanket_cleared'},
 'test_b31_junctional_balance.py':{'configured_norm','test_active_and_fallback_balance_match','test_corpse_render_keeps_evidence_without_rebleed_progression'}}
EXTRA=[
 'test_b19_vials_pea_artifact.py::B19Source::test_ace_timer_events_drive_artifact',
 'test_b19_vials_pea_artifact.py::B19Source::test_monitor_generators_apply_artifact',
 'test_b19_vials_pea_artifact.py::B19Source::test_pea_morphology_distinct_from_sinus',
 'test_b21_rhythm_sync.py::B21RhythmRegression::test_threshold_forced_vt_can_recover_but_true_vt_is_not_blanket_cleared',
 'test_b31_junctional_balance.py::JunctionalB31::test_active_and_fallback_balance_match',
 'test_b31_junctional_balance.py::JunctionalB31::test_compensated_two_junction_window_is_materially_longer',
 'test_b31_junctional_balance.py::JunctionalB31::test_corpse_render_keeps_evidence_without_rebleed_progression']
def git(*args,cwd=ROOT):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def run(args,cwd,label,env=None):
    with (OUT/(label+'.log')).open('w') as f:
        cp=subprocess.run(args,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=360)
    (OUT/(label+'-command.json')).write_text(json.dumps({'command':args,'returncode':cp.returncode},indent=2))
    print(label,'exit',cp.returncode,flush=True);print((OUT/(label+'.log')).read_text()[-2200:],flush=True)
    return cp.returncode
subprocess.run(['git','fetch','--no-tags','--depth=1','origin',BASE],check=True)
for p in (CANDIDATE,BASELINE):subprocess.run(['git','worktree','add','--detach',str(p),BASE],check=True)
compressed=b''.join((INFRA/f'payload{i}.bin').read_bytes() for i in range(2))
assert hashlib.sha256(compressed).hexdigest()=='0f589f0f697ac635eeeeb4baada132efeee2a59ff2ab36d5e9cf5854041f1bfe'
patch=lzma.decompress(compressed)
assert hashlib.sha256(patch).hexdigest()=='4be98c4caae13b1e01c05265a9e13cc05525a760da6f9c7e1c79a51e2339ce04'
p=OUT/'reviewed.patch';p.write_bytes(patch)
for args in (['git','apply','--check',str(p)],['git','apply',str(p)],['git','add','-A']):subprocess.run(args,cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE
changes=git('diff','--cached','--name-status',cwd=CANDIDATE).splitlines();assert len(changes)==9
actual_runtime=[]
for row in changes:
    status,name=row.split('\t');assert status in ('A','M'),row
    if name in RUNTIME:actual_runtime.append(name)
    else:assert name.startswith(PREFIX) or name in ('docs/audits/2026-09-22-historical-backlog-batch7.md','docs/audits/historical-backlog-remaining-20260922.txt'),row
assert set(actual_runtime)==RUNTIME
scope={}
for name,allowed in CHANGED_FUNCTIONS.items():
    def funcs(root):return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse((root/PREFIX/name).read_text())) if isinstance(n,ast.FunctionDef)}
    a,b=funcs(BASELINE),funcs(CANDIDATE);assert a.keys()==b.keys(),name
    actual={k for k in a if a[k]!=b[k]};assert actual==allowed,(name,actual)
    scope[name]=sorted(actual)
subprocess.run(['git','diff','--cached','--check'],cwd=CANDIDATE,check=True)
(OUT/'preservation.json').write_text(json.dumps({'base':BASE,'tree':TREE,'changes':changes,'runtime_changes':sorted(actual_runtime),'other_runtime_or_asset_changes':[],'deleted_files':[],'unrelated_existing_paths_unchanged':4021},indent=2))
(OUT/'test-edit-scope.json').write_text(json.dumps(scope,indent=2))
focused=json.loads((INFRA/'focused-base.json').read_text())+NEW+[PREFIX+n for n in EXTRA]
assert len(focused)==105
(OUT/'focused-paths.json').write_text(json.dumps(focused,indent=2))
assert run([sys.executable,'-m','pytest',*focused,'-q','--tb=short','--junitxml='+str(OUT/'focused.xml')],CANDIDATE,'focused')==0
s=ET.parse(OUT/'focused.xml').getroot().find('testsuite')
assert s.attrib['tests']=='1419' and all(s.attrib[k]=='0' for k in ('errors','failures','skipped')),s.attrib
assert run([os.environ['HEMTT'],'check'],CANDIDATE,'hemtt')==0
reports={}
for label,root in [('before',BASELINE),('after',CANDIDATE)]:
    events=OUT/(label+'.jsonl');events.write_text('')
    env={**os.environ,'PYTHONPATH':str(INFRA),'AUDIT_EVENTS':str(events)}
    assert run([sys.executable,'-m','pytest',PREFIX.rstrip('/'),'-q','--continue-on-collection-errors','--tb=short','-p','auditrecorder'],root,label,env)==1
    reports[label]=[json.loads(v) for v in events.read_text().splitlines()]
def identity(r):
    c=r.get('context','')
    if c in ("''",'""'):c=''
    m=re.fullmatch(r'SubtestContext\(msg=(.*?), kwargs=(.*)\)',c)
    if m:
        try:c=json.dumps([ast.literal_eval(m[1]),ast.literal_eval(m[2])],sort_keys=True,default=str)
        except (ValueError,SyntaxError):pass
    return (r['nodeid'],r['kind'],r.get('when'),r.get('type'),c)
a,b=({identity(r):r for r in reports[label]} for label in ('before','after'))
fixed=[k for k in a.keys()&b.keys() if a[k]['outcome']=='failed' and b[k]['outcome']=='passed']
new=[k for k in b if b[k]['outcome']=='failed' and (k not in a or a[k]['outcome']!='failed')]
regressions=[k for k in a.keys()&b.keys() if a[k]['outcome']=='passed' and b[k]['outcome']!='passed']
missing=list(a.keys()-b.keys())
errors={label:[r for r in rows if r['kind']=='collection' or (r.get('when')!='call' and r['outcome']=='failed')] for label,rows in reports.items()}
skips={label:sum(r['outcome']=='skipped' for r in rows) for label,rows in reports.items()}
comparison={'fixed':sorted(k[0] for k in fixed),'fixed_count':len(fixed),'newly_failing':new,'regressions':regressions,'missing_previous_outcomes':missing,'errors':errors,'skips':skips,'broad_suite_remains_failing':True}
(OUT/'comparison.json').write_text(json.dumps(comparison,indent=2));print(json.dumps(comparison,indent=2),flush=True)
assert len(fixed)==7 and not new and not regressions and not missing and not any(errors.values()) and skips=={'before':4,'after':4}
for name in NEW:shutil.copyfile(CANDIDATE/name,BASELINE/name)
try:
    assert run([sys.executable,'-m','pytest',*NEW,'-q','--tb=short','--junitxml='+str(OUT/'red-control.xml')],BASELINE,'red-control')==1
    red=ET.parse(OUT/'red-control.xml').getroot().find('testsuite')
    assert red.attrib['tests']=='82' and red.attrib['failures']=='18' and red.attrib['errors']=='0' and red.attrib['skipped']=='0',red.attrib
finally:
    for name in NEW:(BASELINE/name).unlink()
assert run([sys.executable,'-m','pytest',*NEW,'-q','--tb=short','--junitxml='+str(OUT/'new-green.xml')],CANDIDATE,'new-green')==0
subprocess.run(['git','diff','--exit-code'],cwd=CANDIDATE,check=True)
assert git('write-tree',cwd=CANDIDATE)==TREE
# Publish only a new isolated candidate branch. Main requires a separate reviewed fast-forward.
env={**os.environ,'GIT_AUTHOR_NAME':'mavis','GIT_AUTHOR_EMAIL':'47053238+hesherson@users.noreply.github.com','GIT_COMMITTER_NAME':'mavis','GIT_COMMITTER_EMAIL':'47053238+hesherson@users.noreply.github.com'}
commit=subprocess.check_output(['git','commit-tree',TREE,'-p',BASE,'-m','Fix suction artifact expiry and junctional packing progress (backlog batch 7)'],cwd=CANDIDATE,env=env,text=True).strip()
subprocess.run(['git','push','origin',commit+':refs/heads/audit/historical-backlog-batch7-validated'],cwd=ROOT,check=True)
(OUT/'verified-commit.json').write_text(json.dumps({'commit':commit,'tree':TREE,'parent':BASE,'main_updated':False},indent=2))
print('Verified isolated candidate:',commit,flush=True)
