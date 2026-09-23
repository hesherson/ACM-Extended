"""Bounded, test-only continuation C-D. Publish only an exactly scoped, checked tree."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast, base64, gzip, hashlib, json, os, subprocess, sys, xml.etree.ElementTree as ET

PAYLOAD = json.loads(Path('.audit/cd/patches.json').read_text())
BASE = PAYLOAD['base']
assert BASE == '7c031508124ea1b431207faf3bda0eeb7e2fbbdf'
OUT = Path('/tmp/acme-cd-results'); OUT.mkdir(exist_ok=True)
BEFORE = Path('/tmp/acme-cd-before'); AFTER = Path('/tmp/acme-cd-after')
BRANCH = 'audit/bounded-backlog-cd-validated-20260923'
T = 'addons/acm_extended/tools/'
LEDGER = 'docs/audits/historical-backlog-remaining-20260922.txt'
C_IDS = ['H131','H372','H373']; D_IDS = ['H428','H436']
SELECTED = [PAYLOAD['resolved'][k].split(' ',1)[1] for k in C_IDS + D_IDS]
REVIEWED = {
 T+'test_b40_animation_audit.py': ['test_direct_pressure_entry_exit_are_priority_one'],
 T+'test_b75_direct_pressure_tag_flush.py': ['test_only_torso_direct_pressure_owns_continuous_action','test_non_torso_pressure_is_not_cancelled_by_other_maneuvers'],
 T+'test_na8_5_batch2.py': ['test_existing_state_keys_are_retained'],
 T+'test_na8_5_batch5.py': ['test_debug_propofol_separate'],
}

def git(cwd,*args):
    r=subprocess.run(['git',*args],cwd=cwd,text=True,capture_output=True,timeout=60)
    assert r.returncode == 0, (args,r.stdout,r.stderr)
    return r.stdout.strip()

def manifest(root):
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest()
            for p in git(root,'ls-files','-z').split('\0') if p}

def run(name,root,args,timeout=450):
    with (OUT/(name+'.log')).open('w') as stream:
        r=subprocess.run(args,cwd=root,stdout=stream,stderr=subprocess.STDOUT,text=True,timeout=timeout)
    tail=(OUT/(name+'.log')).read_text()[-2200:]
    print(name,'exit',r.returncode,tail,flush=True)
    return r.returncode

def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=no','--continue-on-collection-errors','--junitxml='+str(xml)])
    outcomes={}
    for c in ET.parse(xml).iter('testcase'):
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        key=(c.get('classname',''),c.get('name',''))
        outcomes.setdefault(key,Counter())[status]+=1
    counts=Counter()
    for v in outcomes.values(): counts.update(v)
    return rc,outcomes,dict(counts)

def patch(label):
    part=PAYLOAD[label]
    # Repair two identified text-transport transcription slips; decoded patch hash is authoritative.
    wire=part['patch_gzip_base64']
    wire=wire.replace('S1suElY9FULGU','S1suElY9ULGU')
    wire=wire.replace('IMkg2pcCxS6a1Ls6','IMkg2pcCxS6S1aLs6')
    raw=gzip.decompress(base64.b64decode(wire,validate=True))
    assert hashlib.sha256(raw).hexdigest()==part['patch_sha256'], 'Patch transport changed'
    p=OUT/('bounded-'+label+'.patch');p.write_bytes(raw)
    git(AFTER,'apply','--check',str(p));git(AFTER,'apply',str(p))

def check_test_bodies():
    for path,names in REVIEWED.items():
        def normalized(root):
            tree=ast.parse((root/path).read_text())
            seen=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.FunctionDef) and node.name in names:
                    seen.append(node.name);node.body=[ast.Pass()]
            assert sorted(seen)==sorted(names)
            return ast.dump(tree,include_attributes=False)
        assert normalized(BEFORE)==normalized(AFTER), 'Unreviewed test body edit: '+path

def ledger(root):
    return {l.split()[0]:l for l in (root/LEDGER).read_text().splitlines() if l.startswith('H')}

def commit(label):
    git(AFTER,'add',*PAYLOAD[label]['paths'])
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com',
        'commit','-m',f'Reconcile historical contracts without runtime changes (bounded {label})')
    return git(AFTER,'rev-parse','HEAD')

# Isolated complete checkouts; audit workflow/payload never enters candidate history.
git(Path('.'),'fetch','--depth=1','origin',BASE)
for path in (BEFORE,AFTER): git(Path('.'),'worktree','add','--detach',str(path),BASE)
original=manifest(BEFORE);(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert len(ledger(BEFORE))==146
assert tests('selected-before',BEFORE,SELECTED)[2]=={'failed':5}
patch('C')
c=tests('batch-C',AFTER,SELECTED[:3]+[T+'test_bounded_pressure_contracts.py',T+'test_native_bvm_dp.py',T+'test_bvm_startup.py'])
assert c[0]==0 and set(c[2])=={'passed'},c[2]
assert len(ledger(AFTER))==143
sha_c=commit('C')
patch('D');check_test_bodies()
current=manifest(AFTER)
changed={p for p in original if current.get(p)!=original[p]}
assert changed==set(REVIEWED)|{LEDGER},changed
newfiles={p for v in (PAYLOAD['C'],PAYLOAD['D']) for p in v['paths']} - set(original)
assert all(p.endswith('.py') or p.startswith('docs/audits/') for p in newfiles)
assert all(v==ledger(AFTER).get(k) for k,v in ledger(BEFORE).items() if k not in C_IDS+D_IDS)
assert set(ledger(BEFORE))-set(ledger(AFTER))==set(C_IDS+D_IDS)
assert len(ledger(AFTER))==141
focused=tests('focused',AFTER,SELECTED+[T+'test_bounded_pressure_contracts.py',T+'test_bounded_assessment_contracts.py',T+'test_native_bvm_dp.py',T+'test_bvm_startup.py','tools/test_self_audit_20260922.py'])
assert focused[0]==0 and focused[2]=={'passed':157},focused[2]
# Bound the full before/after comparison and keep both nonzero exits visible.
with ThreadPoolExecutor(max_workers=2) as pool:
    left=pool.submit(tests,'addon-before',BEFORE,[T]);right=pool.submit(tests,'addon-after',AFTER,[T])
    before=left.result();after=right.result()
assert before[0]==after[0]==1
assert before[2].get('error',0)==after[2].get('error',0)==0
fixed=[];regressed=[];missing=set(before[1])-set(after[1])
for k,v in before[1].items():
    if k not in after[1]:continue
    if v==after[1][k]:continue
    if v==Counter({'failed':1}) and after[1][k]==Counter({'passed':1}):fixed.append(k)
    else:regressed.append((k,dict(v),dict(after[1][k])))
assert not missing and not regressed,(missing,regressed)
assert len(fixed)==5,fixed
assert {k[1] for k in fixed}=={s.rsplit('::',1)[1] for s in SELECTED},fixed
added=set(after[1])-set(before[1])
assert len(added)==46 and all(after[1][k]==Counter({'passed':1}) for k in added)
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
# No runtime edit exists anywhere in the complete tracked tree.
current=manifest(AFTER)
assert all(current[p]==h for p,h in original.items() if p not in changed)
report={'base':BASE,'C':sha_c,'focused':focused[2],'batch_C':c[2],
        'addon_before':before[2],'addon_after':after[2],
        'fixed_original_ids':C_IDS+D_IDS,'fixed_pytest_identities':fixed,
        'new_passing_cases':len(added),'newly_failing':[],'missing_previous':[],
        'remaining_original_entries':141,'runtime_files_changed':0,
        'unchanged_existing_files':len(original)-len(changed),
        'changed_existing_files':sorted(changed),'hemtt_exit':0,
        'live_arma_tested':False,'stable_release_approved':False}
(OUT/'comparison.json').write_text(json.dumps(report,indent=2))
validation='\n## Complete-checkout validation\n\n'+f'Focused: {focused[2]}. Full addon before: {before[2]}. Full addon after: {after[2]}. Exactly five retained historical identities move from failing to passing; 46 new cases pass. No newly failing or missing prior identities. Both full addon commands return 1 and retain the same four skips. Full-project HEMTT check returns 0. All {len(original)-len(changed)} other existing tracked files retain their complete-checkout SHA256; runtime/configuration/assets are unchanged. Root preservation tests are included, but the entire root-tools suite was not rerun. No live Arma or release approval. Evidence is retained by this workflow run.\n'
with (AFTER/'docs/audits/2026-09-23-bounded-backlog-D.md').open('a') as f:f.write(validation)
sha_d=commit('D')
assert not git(AFTER,'status','--porcelain')
report.update({'D':sha_d,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'final-manifest.json').write_text(json.dumps(manifest(AFTER),indent=2))
(OUT/'README.txt').write_text('Test-only backlog C-D, layered on A-B 7c031508. No PBO rebuild required for these changes alone. Includes separate git patches, test logs, JUnit and source-preservation evidence. No stable-release approval.\n')
git(AFTER,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
