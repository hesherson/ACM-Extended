"""Build and validate two scoped commits from M-N; do not write main."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast, hashlib, json, os, subprocess, sys, xml.etree.ElementTree as ET

BASE='df076b8b136ebf011f594d1c9529ea89de0e79ac'
BEFORE=Path('/tmp/acme-op-before'); AFTER=Path('/tmp/acme-op-after')
OUT=Path('/tmp/acme-op-results'); OUT.mkdir(exist_ok=True)
STAGE=Path('.audit/op').resolve()
BRANCH='audit/bounded-backlog-op-validated-20260923'
T='addons/acm_extended/tools/'
SOURCE='addons/acm_extended/functions/fn_headElevateStop.sqf'
SNAP='tools/test_self_audit_20260922.py'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
TEST_O=T+'test_bounded_lower_roll_retry.py'
TEST_P=T+'test_bounded_head_start_contracts.py'
DOC_O='docs/audits/2026-09-23-bounded-backlog-O.md'
DOC_P='docs/audits/2026-09-23-bounded-backlog-P.md'
REVIEWED={
 T+'test_b71_tag_head_intubation.py':'test_head_elevation_rolls_only_actual_prone_patient_to_supine',
 T+'test_b72_chest_tag_head_provider.py':'test_head_elevation_only_rolls_patient_when_actually_prone',
}
SELECTED=[p+'::'+n for p,n in REVIEWED.items()]

def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,capture_output=True,text=True,timeout=90)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()

def digest(root,path): return hashlib.sha256((root/path).read_bytes()).hexdigest()
def manifest(root): return {p:digest(root,p) for p in git(root,'ls-files','-z').split('\0') if p}

def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    with (OUT/(name+'.log')).open('w') as log:
        r=subprocess.run([sys.executable,'-m','pytest',*paths,'-q','--tb=short','--continue-on-collection-errors','--junitxml='+str(xml)],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=440)
    result={}
    for c in ET.parse(xml).iter('testcase'):
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        name_id=c.get('name','')
        prefix='test_prior_fix_restored_without_rewrite['+SOURCE+'-'
        if name_id.startswith(prefix): name_id=prefix+'<reviewed-sha256>]'
        key=(c.get('classname',''),name_id)
        result.setdefault(key,Counter())[status]+=1
    counts=Counter()
    for v in result.values(): counts.update(v)
    print(name,'exit',r.returncode,dict(counts),flush=True)
    if r.returncode: print((OUT/(name+'.log')).read_text()[-1400:],flush=True)
    return r.returncode,result,dict(counts)

def replace(path,old,new):
    p=AFTER/path;s=p.read_text();assert s.count(old)==1,path;p.write_text(s.replace(old,new))

def copy_test(filename,path,root):
    text=(STAGE/filename).read_text();compile(text,path,'exec');(root/path).write_text(text)

def entries(root):return {l.split()[0]:l for l in (root/LEDGER).read_text().splitlines() if l.startswith('H')}

def commit(paths,message):
    git(AFTER,'add',*paths)
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',message)
    return git(AFTER,'rev-parse','HEAD')

git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE);(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert len(entries(BEFORE))==109
assert tests('selected-before',BEFORE,SELECTED)[2]=={'failed':2}
# Run newly added execution controls on the unmodified production source.
copy_test('lower_retry.txt',TEST_O,BEFORE)
copy_test('head_start.txt',TEST_P,BEFORE)
old_o=tests('O-original-runtime',BEFORE,[TEST_O]);old_p=tests('P-original-runtime',BEFORE,[TEST_P])
assert old_o[0]==1 and old_o[2]=={'failed':12,'passed':2},old_o[2]
assert old_p[0]==0 and old_p[2]=={'passed':21},old_p[2]
old_output=(OUT/'O-original-runtime.log').read_text()
assert '[ERR]' not in old_output and '[FAT]' not in old_output
for p in (TEST_O,TEST_P):(BEFORE/p).unlink()
assert manifest(BEFORE)==original and not git(BEFORE,'status','--porcelain')

copy_test('lower_retry.txt',TEST_O,AFTER)
old='''    [{
        params ["_m","_p","_quiet"];
        if (!isNull _p && {local _p}) then {
            _p setVariable ["ACME_CS_facing","front",true];
            [_m,_p,_quiet,true] call ACME_fnc_headElevateStop;
        };
    }, [_medic,_patient,_quiet], _delay] call CBA_fnc_waitAndExecute;'''
new='''    // The roll belongs to this placement. A later elevation or a completed lower
    // must not be retired by this old retry, even when the patient is local again.
    private _poseToken = _patient getVariable ["ACME_headElev_poseToken", ""];
    [{
        params ["_m","_p","_quiet","_poseToken"];
        if (isNull _p || {!local _p}) exitWith {};
        if ((_p getVariable ["ACME_headElev_poseToken", ""]) != _poseToken) exitWith {};
        _p setVariable ["ACME_CS_facing","front",true];
        [_m,_p,_quiet,true] call ACME_fnc_headElevateStop;
    }, [_medic,_patient,_quiet,_poseToken], _delay] call CBA_fnc_waitAndExecute;'''
replace(SOURCE,old,new)
assert digest(AFTER,SOURCE)=='bbec41dfd8a1a2aa18dca1c94cec760d3cbd48463881619e77051e263e38c09b'
old_digest=original[SOURCE];new_digest=digest(AFTER,SOURCE)
replace(SNAP,f"'{SOURCE}': '{old_digest}'",f"'{SOURCE}': '{new_digest}'")
o_result=tests('batch-O',AFTER,[TEST_O,T+'test_bounded_head_completion.py',SNAP])
assert o_result[0]==0 and set(o_result[2])=={'passed'}
(AFTER/DOC_O).write_text(f'''# Bounded O: Lower Head pre-roll retry ownership

Parent: `{BASE}` (M-N).

A Lower Head retry after supine normalization previously resumed against whichever elevation existed at delivery. It could clear a newer placement, rewrite facing, or repeat gear-recovery calls after the first retry had already completed. The retry now captures the existing placement token and checks it before any delayed write or recursive Lower Head call. Only headElevateStop changes runtime, with its one explicitly reviewed preservation digest. No new state key, timer, network operation, animation, delay, gear algorithm or clinical rule is added.

Fourteen new cases execute the complete Lower Head function with explicit engine fixtures. On unchanged M-N runtime: {old_o[2]}. All fourteen pass with this change. Cases include replacement/cleared placement tokens, logical elevation on/off, physical-roll and existing fallback branches, quiet and visible lowering, repeated delivery, loss of locality, and a current dead placement delegating to existing death recovery. Existing completion/lift tests remain included. finite is a declared fixture for finite default durations, not NaN coverage.

This is not a general lifecycle solution. Token reuse, owner-away-and-back with the same token, empty-token legacy placements, initial Elevate Head retries, late incoming external actions, actual RTM/PhysX/network scheduling and live inventory effects remain unverified. No original H entry is closed by O; the index remains 109. No live Arma or stable-release approval.
''')
paths_o=[SOURCE,SNAP,TEST_O,DOC_O]
sha_o=commit(paths_o,'Bounded O: scope Lower Head pre-roll retries to their placement')

copy_test('head_start.txt',TEST_P,AFTER)
for path,name in REVIEWED.items():
    text=(AFTER/path).read_text();tree=ast.parse(text)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    lines=text.splitlines(keepends=True)
    lines[node.body[0].lineno-1:node.end_lineno]=['    from test_bounded_head_start_contracts import start_contract\n    start_contract()\n']
    (AFTER/path).write_text(''.join(lines))
    def normalize(s):
        tr=ast.parse(s)
        targets=[n for n in tr.body if isinstance(n,ast.FunctionDef) and n.name==name]
        assert len(targets)==1;targets[0].body=[ast.Pass()]
        return ast.dump(tr,include_attributes=False)
    assert normalize((BEFORE/path).read_text())==normalize((AFTER/path).read_text()),path
remaining=entries(BEFORE);resolved={k:remaining[k] for k in ('H340','H353')}
replace(LEDGER,'after bounded N: 109','after bounded P: 107')
replace(LEDGER,'Base: 2fcd3e987eba4b7fd8a2ff5ba25d236983777431','Base: '+BASE)
for line in resolved.values():replace(LEDGER,line+'\n','')
assert entries(AFTER)=={k:v for k,v in remaining.items() if k not in resolved}
focus=tests('focused',AFTER,SELECTED+[TEST_O,TEST_P,T+'test_bounded_head_completion.py',T+'test_bounded_head_pose_contracts.py',SNAP])
assert focus[0]==0 and focus[2]=={'passed':164}
# Full-suite comparison uses complete independent checkouts, not the local text export.
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'addon-before',BEFORE,[T]);b=pool.submit(tests,'addon-after',AFTER,[T])
    before=a.result();after=b.result()
assert before[0]==after[0]==1
assert before[2].get('error',0)==after[2].get('error',0)==0
fixed=[]
assert set(before[1]).issubset(after[1])
for key,outcome in before[1].items():
    if outcome==after[1][key]:continue
    assert outcome==Counter({'failed':1}) and after[1][key]==Counter({'passed':1}), (key,outcome,after[1][key])
    fixed.append(key)
assert len(fixed)==2 and {k[1] for k in fixed}==set(REVIEWED.values())
added=set(after[1])-set(before[1]);assert len(added)==35
assert all(after[1][k]==Counter({'passed':1}) for k in added)
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
root_before=tests('root-before',BEFORE,['tools']);root_after=tests('root-after',AFTER,['tools'])
assert root_before[0]==root_after[0]==1 and root_before[1]==root_after[1]
with (OUT/'hemtt.log').open('w') as log:
    h=subprocess.run([os.environ['HEMTT'],'check'],cwd=AFTER,stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert h.returncode==0
changed={p for p,v in original.items() if digest(AFTER,p)!=v}
assert changed=={SOURCE,SNAP,LEDGER,*REVIEWED}
restored=(AFTER/SNAP).read_text().replace(f"'{SOURCE}': '{new_digest}'",f"'{SOURCE}': '{old_digest}'")
assert restored==(BEFORE/SNAP).read_text()
report={'baseline':BASE,'O':sha_o,'focused':focus[2],'old_runtime_O':old_o[2],'old_runtime_P':old_p[2],
 'addon_before':before[2],'addon_after':after[2],'root_before':root_before[2],'root_after':root_after[2],
 'resolved':resolved,'remaining_original_entries':107,'new_cases':35,'new_failures':[],'missing_previous_identities':[],
 'runtime_files_changed':[SOURCE],'changed_existing_files':sorted(changed),'unchanged_existing_files':len(original)-len(changed),
 'hemtt_exit':h.returncode,'live_arma_tested':False,'stable_release_approved':False}
(AFTER/DOC_P).write_text(f'''# Bounded P: actual-side Semi-Fowler startup contract

Builds on O from M-N parent `{BASE}`. Test-only changes.

H340 and H353 retain their original pytest identities. The old assertions demanded the retired mustRollSupine variable and a two-argument roll call. Current startup resolves actual side, revalidates eligibility on the patient owner, normalizes a posterior-up patient to front before lifting, passes provider and head-preservation arguments, and uses its existing retry flag. Already-front casualties do not take a roll detour. The rewritten assertions check executable tokens, not comments; they do not restore obsolete calls.

Twenty-one new cases pass against unchanged startup runtime. They execute the complete start function with explicit equipment, actual-side, eligibility and animation fixtures, and mutation-check four critical guard/target regressions despite comment decoys. Coverage includes actual-versus-cached side in both directions, physical and fallback normalization, normal retry, owner/life/eligibility denial, backpack-supported startup and timing bounded by the longer patient/provider move. These tests record requests, not actual body orientation, animation, inventory, NaN handling or multiplayer behavior.

No startup runtime, configuration or asset changes. Initial Elevate Head retry generation handling remains open; this test reconciliation does not certify it. All other historical test bodies and remaining H entries are retained. The original index moves 109 to 107. No new skip or xfail, and no live Arma or stable-release approval.

## Complete-checkout validation

Focused: {focus[2]}. O checks on original runtime: {old_o[2]}; P checks on original runtime: {old_p[2]}. Full addon before: {before[2]}; after: {after[2]}. Exactly two retained historical identities now pass and all 35 new cases pass. No newly failing or missing prior identity. Both addon commands remain failing overall, with the same four skips and zero collection/setup errors. Root before: {root_before[2]}; after: {root_after[2]}, with identical outcomes and normalized identities. Only the one reviewed digest-valued snapshot label is normalized; raw JUnit remains in evidence. HEMTT check returns 0. Only headElevateStop changes runtime; {len(original)-len(changed)} other existing tracked files retain their complete-checkout SHA256. No live Arma or stable-release approval.
''')
paths_p=[*REVIEWED,TEST_P,LEDGER,DOC_P]
sha_p=commit(paths_p,'Bounded P: reconcile actual-side head-start contracts')
assert not git(AFTER,'status','--porcelain')
final=manifest(AFTER)
assert set(final)-set(original)=={TEST_O,TEST_P,DOC_O,DOC_P}
report.update({'P':sha_p,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(final,indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('O-P on M-N df076b8. Runtime Lower Head retry guard plus two historical test reconciliations. Rebuild for testing; not stable-release approval. Contains separate git patches, complete logs, raw JUnit and source-preservation manifests.\n')
git(AFTER,'push','origin','HEAD:refs/heads/'+BRANCH)
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
