"""Publish two bounded commits only after source, execution and preservation checks."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast, hashlib, json, os, shutil, subprocess, sys
import xml.etree.ElementTree as ET
BASE='f611ac7cf346da659534b47f34d79cdb3eab4bd2'
STAGE=Path(__file__).resolve().parent
BEFORE=Path('/tmp/acme-ai-aj-before'); AFTER=Path('/tmp/acme-ai-aj-after')
OUT=Path('/tmp/acme-ai-aj-results'); OUT.mkdir(exist_ok=True)
BRANCH='audit/bounded-backlog-ai-aj-validated-20260923'
T='addons/acm_extended/tools/'
R=['addons/acm_extended/functions/fn_skConfirmInjection.sqf','addons/acm_extended/functions/fn_skInjectSite.sqf']
API=T+'test_b68_syringe_tag_push_layout.py'
HIST=T+'test_b69_narcbox_carousel_visibility.py'
NAME='test_b68_three_second_push_and_b67_cardiac_safety_still_present'
N1=T+'test_bounded_confirmed_epi_volume.py'; N2=T+'test_bounded_push_native_contract.py'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
D1='docs/audits/2026-09-23-bounded-backlog-AI.md'; D2='docs/audits/2026-09-23-bounded-backlog-AJ.md'

def command(root,args,timeout=60):
 r=subprocess.run(args,cwd=root,text=True,capture_output=True,timeout=timeout)
 assert r.returncode==0,(args,r.stdout[-4000:],r.stderr[-4000:])
 return r.stdout.strip()

def git(root,*args):return command(root,['git',*args])

def manifest(root):
 return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files','-z').split('\0') if p}

def run(name,root,args,timeout=450):
 with (OUT/(name+'.log')).open('w') as f:
  r=subprocess.run(args,cwd=root,stdout=f,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 print(name,'exit',r.returncode,flush=True)
 return r.returncode

def tests(name,root,paths):
 xml=OUT/(name+'.xml')
 rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=short','--continue-on-collection-errors','--junitxml='+str(xml)])
 data={}
 for c in ET.parse(xml).iter('testcase'):
  k=(c.get('classname',''),c.get('name',''))
  status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
  data.setdefault(k,Counter())[status]+=1
 counts=Counter()
 for v in data.values():counts.update(v)
 print(name,dict(counts),flush=True)
 return rc,data,dict(counts)

def once(path,old,new):
 text=(AFTER/path).read_text();assert text.count(old)==1,(path,old)
 (AFTER/path).write_text(text.replace(old,new))

def same_other_test_bodies(path,allowed):
 def normalized(root):
  tree=ast.parse((root/path).read_text());seen=[]
  for n in ast.walk(tree):
   if isinstance(n,ast.FunctionDef) and n.name in allowed:seen.append(n.name);n.body=[ast.Pass()]
  assert set(seen)==set(allowed)
  return ast.dump(tree,include_attributes=False)
 assert normalized(BEFORE)==normalized(AFTER),'unreviewed test edit '+path

git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in [BEFORE,AFTER]:git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE)
(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert tests('historical-before',BEFORE,[HIST+'::'+NAME])[2]=={'failed':1}
for root in [BEFORE,AFTER]:
 for src,dst in [('epi.py',N1),('contracts.py',N2)]:shutil.copyfile(STAGE/src,root/dst)
ai_original=tests('AI-original-runtime',BEFORE,[N1]);assert ai_original[2]=={'failed':13,'passed':21}
aj_original=tests('AJ-original-runtime',BEFORE,[N2]);assert aj_original[2]=={'passed':9}
for p in [N1,N2]:(BEFORE/p).unlink()
assert manifest(BEFORE)==original
command(AFTER,[sys.executable,str(STAGE/'modify.py')])
# API-contract assertion acknowledges the new optional measured-volume argument.
once(API,'assert contains(inject, \'params ["_bodyPart", ["_pushSec", 3]];\')',
     'assert contains(inject, \'params ["_bodyPart", ["_pushSec", 3], ["_confirmedEpiMl", -1, [0]]];\')')
s=(AFTER/HIST).read_text();lines=s.splitlines(keepends=True)
n=next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name==NAME)
replacement='def '+NAME+'():\n    # Current timed confirmation and native ACM rhythm authority supersede the old inline push/floor.\n    from test_bounded_push_native_contract import historical_combined_check\n    historical_combined_check()\n'
(AFTER/HIST).write_text(''.join(lines[:n.lineno-1])+replacement+''.join(lines[n.end_lineno:]))
same_other_test_bodies(HIST,[NAME]);same_other_test_bodies(API,['test_body_map_site_click_runs_locked_three_second_visual_push_before_commit'])
old_ledger=(BEFORE/LEDGER).read_text();old_lines=[l for l in old_ledger.splitlines() if l.startswith('H')]
resolved=[l for l in old_lines if l.startswith('H327 ')];assert len(resolved)==1 and NAME in resolved[0]
left=[l for l in old_lines if not l.startswith('H327 ')];assert len(old_lines)==70 and len(left)==69
(AFTER/LEDGER).write_text('Unresolved original source-contract outcomes after bounded AJ: 69\nBase: '+BASE+'\nNot a waiver, skip list, or expected-failure list. Each ID retains its original identity.\n\n'+'\n'.join(left)+'\n')
focused=tests('focused',AFTER,[N1,N2,API+'::test_body_map_site_click_runs_locked_three_second_visual_push_before_commit',HIST+'::'+NAME,
 T+'test_bounded_normal_push_lifetime.py',T+'test_bounded_staged_push_contracts.py',T+'test_bounded_site_click_handoff.py',
 T+'test_historical_airway_execution.py','tools/test_self_audit_20260922.py'])
assert focused[0]==0 and set(focused[2])=={'passed'},focused[2]
with ThreadPoolExecutor(max_workers=2) as pool:
 a=pool.submit(tests,'addon-before',BEFORE,[T]);b=pool.submit(tests,'addon-after',AFTER,[T])
 before=a.result();after=b.result()
assert before[0]==after[0]==1
assert before[2].get('error',0)==after[2].get('error',0)==0
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
assert set(before[1]).issubset(after[1]),'missing prior identity'
changed=[k for k in before[1] if before[1][k]!=after[1][k]]
assert len(changed)==1 and changed[0][1]==NAME,changed
assert before[1][changed[0]]==Counter({'failed':1}) and after[1][changed[0]]==Counter({'passed':1})
new=set(after[1])-set(before[1]);assert len(new)==43 and all(after[1][k]==Counter({'passed':1}) for k in new)
with ThreadPoolExecutor(max_workers=2) as pool:
 a=pool.submit(tests,'root-before',BEFORE,['tools']);b=pool.submit(tests,'root-after',AFTER,['tools'])
 rb=a.result();ra=b.result()
assert rb[0]==ra[0]==1 and rb[1]==ra[1]
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
assert run('diff-check',AFTER,['git','diff','--check'],30)==0
current=manifest(AFTER);changed_files={p for p in original if current.get(p)!=original[p]}
assert changed_files==set(R+[API,HIST,LEDGER]),changed_files
assert set(current)==set(original),'unreviewed existing file added/deleted'
report={'base':BASE,'AI_original_runtime':ai_original[2],'AJ_original_runtime':aj_original[2],
 'focused':focused[2],'addon_before':before[2],'addon_after':after[2],'root_before':rb[2],'root_after':ra[2],
 'resolved_original_ids':['H327'],'remaining_original_entries':69,'new_passing_cases':43,
 'missing_previous':[],'newly_failing':[],'runtime_files_changed':R,'changed_existing':sorted(changed_files),
 'unchanged_existing_files':len(original)-len(changed_files),'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
(AFTER/D1).write_text('''# Bounded AI: confirmation owns its measured epinephrine aliquot

Parent: `'''+BASE+'''` (AG-AH).

The normal push animation captured the epinephrine selector at confirmation, but skInjectSite read the mutable selector again at completion. A later choice could alter the amount administered despite the already-authored stroke. The normal confirmation now carries the measured mL through both existing callbacks and supplies that amount to skInjectSite. The measured worker still validates sufficient remaining volume, exact access and distance before debit/request. It is not modified. Legacy direct two-argument calls retain their live-selector behavior. Other prepared syringes retain the two-argument handoff; Hardcore delegation remains unchanged.

Only skConfirmInjection and skInjectSite change runtime. No new timer, PFH, state key, network operation, kinetic model or inventory transaction is added. The existing dose arithmetic, refund construction, timings, default duration, UI selector and provider/patient/workspace ownership remain. A passing API-contract assertion is updated solely for the new optional third argument; no prior assertion is removed.

Thirty-four new cases execute the complete confirmation, skInjectSite and measured epinephrine worker with explicit engine boundaries. Unchanged AG-AH: 13 failures and 21 passes. Candidate: all 34 pass. Coverage includes all dose-selector changes at settle/completion, stroke-versus-request volume, exact remainder/refund, partial/full solutions, dead casualties, typed IO timing, access/distance rejection, legacy direct calls, duplicate completion and reduced remaining solution rejection.

The tests execute store arithmetic and request construction, not an Arma inventory transaction, actual clinical effect, render, network transport or live input. The UI selector itself remains changeable and its later value is not overwritten. Changes to concentration/components under the same stable ID, arbitrary external context resets, malformed nonnumeric values/NaN, same-context round trips and engine scheduling remain outside this fix. No H entry is closed by AI alone. No stable-release approval.
''')
git(AFTER,'add',*R,API,N1,D1)
git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m','Bounded AI preserve confirmed epinephrine amount through timed handoff')
report['AI']=git(AFTER,'rev-parse','HEAD')
(AFTER/D2).write_text('''# Bounded AJ: timed push and native cardiac authority contract

Builds on AI. H327 retains its historical identity. Its obsolete assertions demanded a three-second ctrlCommit inside BeginInjection and the retired Extended minimum-HR floor. The check now follows explicit staging, timed confirmation and the native cardiac state-machine authority. It executes normal IV/IO/IM timing and the existing observer noninterference cases rather than restoring a retired floor or direct arrest dispatch.

Nine new cases pass on unchanged AG-AH runtime: five execute the actual observer using the existing full-source fixture; four mutation checks reject early administration, direct arrest dispatch, an observer heart-rate write or restoring the retired floor. The previous cardiac machinery and every clinical threshold are untouched. No runtime change in AJ. The ledger moves 70 to 69; every other H entry and historical body remains intact. No skip/xfail added.

These fixtures do not certify clinical calibration, actual ECG pixels or live multiplayer; both broad suites remain failing overall. No stable-release approval.

## Complete-checkout validation

```json
'''+json.dumps(report,indent=2)+'''\n```

The same full checkout and pinned toolchain were used for both sides. Every previous raw JUnit identity is retained. Protected snapshots are unchanged. HEMTT is not a release-package or live-engine acceptance test.
''')
git(AFTER,'add',HIST,N2,LEDGER,D2)
git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m','Bounded AJ reconcile timed push and native cardiac authority contract')
assert not git(AFTER,'status','--porcelain')
assert run('committed-diff-check',AFTER,['git','diff','--check',BASE,'HEAD'],30)==0
final=manifest(AFTER);assert set(final)-set(original)=={N1,N2,D1,D2}
assert all(final[p]==h for p,h in original.items() if p not in changed_files)
report.update({'AJ':git(AFTER,'rev-parse','HEAD'),'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(final,indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('AI-AJ layers on AG-AH. Two scoped source commits, before/after execution evidence, complete manifests and full-suite logs. No stable-release approval.\n')
git(AFTER,'push','origin','HEAD:refs/heads/'+BRANCH)
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
