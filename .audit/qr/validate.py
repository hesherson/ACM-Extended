"""Build two reviewed commits from O-P; never modify or push main."""
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import ast, hashlib, json, os, re, subprocess, sys
import xml.etree.ElementTree as ET

BASE='ee3f54143c5be163727f4c8b575c520be180f640'
BEFORE=Path('/tmp/acme-qr-before'); AFTER=Path('/tmp/acme-qr-after')
OUT=Path('/tmp/acme-qr-results'); OUT.mkdir(exist_ok=True)
BRANCH='audit/bounded-backlog-qr-validated-20260923'
T='addons/acm_extended/tools/'
RUNTIME='addons/acm_extended/functions/fn_headElevateStart.sqf'
SNAP='tools/test_self_audit_20260922.py'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
NEWQ=T+'test_bounded_head_start_retry.py'
NEWR=T+'test_bounded_head_provider_sequence.py'
DOCQ='docs/audits/2026-09-23-bounded-backlog-Q.md'
DOCR='docs/audits/2026-09-23-bounded-backlog-R.md'
REVIEWED={
 T+'test_na8_5_batch9.py':['test_old_pose_callback_owns_token'],
 T+'test_b70_semifowler_bvm_thora_syringe.py':['test_semifowler_provider_runs_requested_full_duration_sequence_and_finishes_unarmed'],
 T+'test_b71_tag_head_intubation.py':['test_exact_semifowler_patient_and_provider_animations_retained'],
 T+'test_b72_chest_tag_head_provider.py':['test_head_provider_stands_only_for_draggerbase_then_returns_crouched'],
}
CHECKED_HASHES={
 NEWQ:'53de220e7c2a12467a1463076f3e3c2543f5b32f16e1ca8eb6b1479231e8ff9a',
 NEWR:'7d02140b73db306012c3f6e561028c37d4da6dc98cbf24aa8734dbdd2aeae874',
 RUNTIME:'3fc226020d4ec3a900802438aeb583c7e99a505fd8aec6919a48e051b23a2309',
 T+'test_na8_5_batch9.py':'158e91f4296a9b8edb73c4402059f3cfb6eb4b326030403ed1669b9d2a6e2d3e',
 T+'test_b70_semifowler_bvm_thora_syringe.py':'d1f4f5685b597d44fc386b785bcbdd91fe23afc3f485f25bc95ab1bd8ad188f3',
 T+'test_b71_tag_head_intubation.py':'c7392208fddb0f3ccc1ac1376f6c5f36dc9d7ab7c48c785c4c37f97647401c19',
 T+'test_b72_chest_tag_head_provider.py':'e5a9f0ae4a50f873820b92e8ae39205dc88771256221290e310acb291143b45a',
}

def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=60)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def manifest(root): return {p:digest(root/p) for p in git(root,'ls-files','-z').split('\0') if p}

def run(name,root,args,limit=450):
    with (OUT/(name+'.log')).open('w') as stream:
        r=subprocess.run(args,cwd=root,stdout=stream,stderr=subprocess.STDOUT,text=True,timeout=limit)
    print(name,'exit',r.returncode,(OUT/(name+'.log')).read_text()[-1800:],flush=True)
    return r.returncode

def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=short','--continue-on-collection-errors','--junitxml='+str(xml)])
    outcomes={}; counts=Counter()
    for c in ET.parse(xml).iter('testcase'):
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        name=c.get('name','')
        prefix='test_prior_fix_restored_without_rewrite['+RUNTIME+'-'
        if name.startswith(prefix):
            assert re.fullmatch('[a-f0-9]{64}\\]',name[len(prefix):])
            name=prefix+'<reviewed-digest>]'
        key=(c.get('classname',''),name)
        outcomes.setdefault(key,Counter())[status]+=1
        counts[status]+=1
    return rc,outcomes,dict(counts)

def replace(path,old,new):
    p=AFTER/path;s=p.read_text();assert s.count(old)==1,(path,old)
    p.write_text(s.replace(old,new))

def ledger(root): return {s.split()[0]:s for s in (root/LEDGER).read_text().splitlines() if s.startswith('H')}

def update_ledger(label,closed):
    lines=(BEFORE/LEDGER).read_text().splitlines()
    lines=[s for s in lines if not(s.startswith('H') and s.split()[0] in closed)]
    lines[0]=f'Unresolved original source-contract outcomes after bounded {label}: {107-len(closed)}'
    lines[1]='Base: '+BASE
    (AFTER/LEDGER).write_text('\n'.join(lines)+'\n')
    assert set(ledger(BEFORE))-set(ledger(AFTER))==set(closed)
    assert all(v==ledger(AFTER).get(k) for k,v in ledger(BEFORE).items() if k not in closed)

def commit(paths,message):
    git(AFTER,'add',*paths)
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',message)
    return git(AFTER,'rev-parse','HEAD')

def replace_body(path,name,body):
    p=AFTER/path;s=p.read_text();tree=ast.parse(s)
    n=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    lines=s.splitlines(keepends=True);lines[n.body[0].lineno-1:n.end_lineno]=[body];p.write_text(''.join(lines))

git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE)
(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert len(ledger(BEFORE))==107
ids=['H452','H330','H342','H352']
selected=[ledger(BEFORE)[k].split(' ',1)[1] for k in ids]
assert tests('selected-before',BEFORE,selected)[2]=={'failed':4}
for name,path in [('test_q.txt',NEWQ),('test_r.txt',NEWR)]:
    text=Path('.audit/qr',name).read_text();compile(text,path,'exec')
    (BEFORE/path).write_text(text);(AFTER/path).write_text(text)
    assert digest(BEFORE/path)==CHECKED_HASHES[path]
qold=tests('Q-original-runtime',BEFORE,[NEWQ])
rold=tests('R-original-runtime',BEFORE,[NEWR])
assert qold[2]=={'failed':16,'passed':4},qold[2]
assert rold[2]=={'passed':19},rold[2]
assert '[ERR]' not in (OUT/'Q-original-runtime.log').read_text()
assert '[FAT]' not in (OUT/'Q-original-runtime.log').read_text()
for path in (NEWQ,NEWR):(BEFORE/path).unlink()
# R is staged but not tracked until its own commit.
replace(RUNTIME,'if (_needFrontFirst) exitWith {\n    private _delay = 0.08;',
'''if (_needFrontFirst) exitWith {
    // A delayed normalization belongs to the placement state that accepted this request.
    private _startPoseToken = _patient getVariable ["ACME_headElev_poseToken", ""];
    private _delay = 0.08;''')
replace(RUNTIME,
'''        params ["_m","_p","_body","_auto"];
        if (!isNull _p && {local _p} && {alive _p}) then {
            _p setVariable ["ACME_CS_facing","front",true];
            [_m,_p,_body,_auto,true] call ACME_fnc_headElevateStart;
        };
    }, [_medic,_patient,_bodyPart,_auto], _delay] call CBA_fnc_waitAndExecute;''',
'''        params ["_m","_p","_body","_auto","_startPoseToken"];
        if (!isNull _p && {local _p} && {alive _p}) then {
            if ((_p getVariable ["ACME_headElev_poseToken", ""]) != _startPoseToken) exitWith {};
            // Startup revalidates eligibility before setting facing or touching gear. Do not write ahead of it.
            [_m,_p,_body,_auto,true] call ACME_fnc_headElevateStart;
        };
    }, [_medic,_patient,_bodyPart,_auto,_startPoseToken], _delay] call CBA_fnc_waitAndExecute;''')
assert original[RUNTIME]=='a2540fac29dbead3657a34d726dcbc08559cad69e770c5453e5de86a0666e129'
replace(SNAP,original[RUNTIME],digest(AFTER/RUNTIME))
replace(T+'test_na8_5_batch9.py',
'''        t=src("headElevateStart")
        self.assertGreaterEqual(t.count('getVariable ["ACME_headElev_poseToken", ""]'),2)
        self.assertGreaterEqual(t.count("!alive _patient"),3)''',
'''        from test_bounded_head_start_retry import retry_contract
        from test_bounded_head_pose_contracts import contains
        retry_contract()
        t=src("headElevateStart")
        # The carrier-creation callback also keeps its existing placement/life gate.
        self.assertTrue(contains(t, 'params ["_patient", "_vestClass", "_poseToken"];'))
        self.assertTrue(contains(t, '|| {(_patient getVariable ["ACME_headElev_poseToken", ""]) != _poseToken}'))
        self.assertTrue(contains(t, 'if (isNull _patient || {!local _patient} || {!alive _patient}'))''')
update_ledger('Q',['H452'])
q=tests('batch-Q',AFTER,[NEWQ,selected[0],SNAP]);assert q[0]==0
(AFTER/DOCQ).write_text(f'''# Bounded Q: initial Elevate Head retry placement ownership

Parent: `{BASE}` (O-P).

The initial Elevate Head normalization retry wrote facing before re-entering startup. Rejected or duplicate retries could therefore change the cached side of a later placement; a changed inactive placement could still run startup/gear work. Capture the existing placement token before normalization and reject mismatch before recursive startup. Remove the duplicate delayed facing write: normal startup already writes front after owner, life, active-placement and eligibility validation.

Only headElevateStart changes runtime. Roll dispatch, physical/fallback branches, delay, support handling, patient/provider choreography, owner dispatch and clinical rules remain. No new state key, timer, event handler or network operation. The one affected preservation hash is reviewed.

Twenty full-startup SQF cases: unchanged O-P {qold[2]}; candidate all twenty pass. They cover physical/fallback normalization, replacement and rejection, locality/life/medic loss, duplicate delivery, current auto/manual flags and supersession by another actual startup call. Engine boundaries are fixtures, not RTM rendering or inventory transactions.

H452 retains its identity but checks actual retry token capture, validation and no pre-validation facing write, plus the carrier callback's existing guards, instead of counting spellings. Index 107 to 106. No unreviewed historical test body or H entry changes.

Empty-token ABA/reuse, owner-away-and-back with the same token, concurrent pending starts before either places the patient, later physical-orientation changes within the same retry and live multiplayer behavior remain open. No complete lifecycle redesign or stable-release approval.
''')
sha_q=commit([RUNTIME,SNAP,T+'test_na8_5_batch9.py',NEWQ,LEDGER,DOCQ], 'Bounded Q: guard initial Elevate Head retry before delayed writes')
for path in list(REVIEWED)[1:]:
    body='    from test_bounded_head_provider_sequence import provider_contract\n    provider_contract()\n'
    if 'test_b71_' in path:body='    from test_bounded_head_provider_sequence import provider_contract\n    from test_bounded_head_pose_contracts import assert_connected_patient_states\n    provider_contract()\n    assert_connected_patient_states()\n'
    replace_body(path,REVIEWED[path][0],body)
update_ledger('R',ids)
for path,h in CHECKED_HASHES.items():assert digest(AFTER/path)==h,('unexpected reviewed file',path)
# Retain every other statement and identity in existing tests.
for path,names in REVIEWED.items():
    def normalized(root):
        tree=ast.parse((root/path).read_text());seen=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.FunctionDef) and n.name in names:seen.append(n.name);n.body=[ast.Pass()]
        assert sorted(seen)==sorted(names)
        return ast.dump(tree,include_attributes=False)
    assert normalized(BEFORE)==normalized(AFTER),path
focus=[NEWQ,NEWR,T+'test_bounded_head_start_contracts.py',T+'test_bounded_head_completion.py',T+'test_bounded_head_pose_contracts.py',*selected,SNAP]
focused=tests('focused',AFTER,focus);assert focused[0]==0 and focused[2]=={'passed':191},focused[2]
with ThreadPoolExecutor(max_workers=2) as pool:
    x=pool.submit(tests,'addon-before',BEFORE,[T]);y=pool.submit(tests,'addon-after',AFTER,[T])
    before=x.result();after=y.result()
assert before[0]==after[0]==1
assert before[2]=={'passed':4134,'failed':135,'skipped':4},before[2]
assert after[2]=={'passed':4177,'failed':131,'skipped':4},after[2]
fixed=[]
assert set(before[1]).issubset(after[1])
for k,v in before[1].items():
    if v==after[1][k]:continue
    assert v==Counter({'failed':1}) and after[1][k]==Counter({'passed':1}),(k,v,after[1][k])
    fixed.append(k)
assert len(fixed)==4 and {k[1] for k in fixed}=={s.rsplit('::',1)[1] for s in selected},fixed
added=set(after[1])-set(before[1]);assert len(added)==39
assert all(after[1][k]==Counter({'passed':1}) for k in added)
with ThreadPoolExecutor(max_workers=2) as pool:
    x=pool.submit(tests,'root-before',BEFORE,['tools']);y=pool.submit(tests,'root-after',AFTER,['tools'])
    rb=x.result();ra=y.result()
assert rb[0]==ra[0]==1 and rb[1]==ra[1],(rb[2],ra[2])
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
changed={p for p,h in original.items() if digest(AFTER/p)!=h}
assert changed==set(REVIEWED)|{RUNTIME,SNAP,LEDGER},changed
snap=(AFTER/SNAP).read_text().replace(digest(AFTER/RUNTIME),original[RUNTIME])
assert snap==(BEFORE/SNAP).read_text(),'unreviewed snapshot change'
report={'baseline':BASE,'Q':sha_q,'focused':focused[2],'Q_original_runtime':qold[2],
        'R_original_runtime':rold[2],'addon_before':before[2],'addon_after':after[2],
        'root_before':rb[2],'root_after':ra[2],'resolved':{k:ledger(BEFORE)[k] for k in ids},
        'remaining_original_entries':103,'new_cases':39,'new_failures':[],
        'missing_previous_identities':[],'runtime_files_changed':[RUNTIME],
        'changed_existing_files':sorted(changed),'unchanged_existing_files':len(original)-len(changed),
        'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
(AFTER/DOCR).write_text(f'''# Bounded R: current provider Putdown sequence and patient wrappers

Builds on Q from O-P. No runtime change in R.

H330, H342 and H352 retain their identities. They demanded retired DraggerBase/AnimDone provider choreography and raw patient state names. B89 intentionally uses the same unarmed crouch -> Putdown entry -> Putdown exit -> crouch sequence for Elevate and Lower Head. It adopts an already-running exit without replaying it, then releases temporary stance control. Connected patient wrappers retain BI grab/release inheritance verified by bounded N. No obsolete sequence is restored.

Nineteen new cases pass on unchanged provider code. They execute the complete controller with animation/clock fixtures or reject mutations with comment decoys. Coverage: both modes, exit adoption, no repeated requests while states stay visible, weapon-preflight grace, unseen-state timeouts, superseded PFHs, final crouch and invalid/newly-owned delayed stance release. The existing logical empty-weapon fallback is retained. No automatic weapon re-selection is introduced.

These fixtures do not certify movement/menu cancellation, physical RTM blending, actual scheduler order, patient rendering or multiplayer delivery. H343/H344 remain open. No runtime, configuration, asset or protected snapshot changes in R. No skip/xfail added. Index 106 to 103; all unreviewed test bodies and H entries unchanged.

## Complete-checkout validation

Focused: {focused[2]}. Q on original runtime: {qold[2]}; R on original runtime: {rold[2]}. Full addon before: {before[2]}; after: {after[2]}. Exactly four retained historical identities pass and all 39 new cases pass. No new failure or missing prior identity. Both full addon commands still fail overall, with four unchanged skips and zero collection/setup errors. Root before: {rb[2]}; after: {ra[2]}, with identical normalized identities/outcomes. Only one reviewed digest-valued snapshot label is normalized; raw JUnit is retained. HEMTT check returns 0. Only headElevateStart changes runtime. All {len(original)-len(changed)} other existing tracked files retain SHA256. No live Arma or stable-release approval.
''')
sha_r=commit([*list(REVIEWED)[1:],NEWR,LEDGER,DOCR], 'Bounded R: reconcile provider Putdown and connected patient contracts')
assert not git(AFTER,'status','--porcelain')
assert set(manifest(AFTER))-set(original)=={NEWQ,NEWR,DOCQ,DOCR}
report.update({'R':sha_r,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(manifest(AFTER),indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('Q-R cumulative source checkpoint on O-P. Q changes initial Elevate Head retry ownership; R reconciles provider/patient test contracts. Includes separate patches, exact manifests, logs and JUnit. No live Arma or stable-release approval.\n')
git(AFTER,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
