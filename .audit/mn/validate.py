"""Validate exactly scoped M-N changes on complete pinned checkouts; never push main."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast, base64, gzip, hashlib, json, os, subprocess, sys
import xml.etree.ElementTree as ET

P=json.loads(Path('.audit/mn/patches.json').read_text())
BASE=P['base']; assert BASE=='2fcd3e987eba4b7fd8a2ff5ba25d236983777431'
OUT=Path('/tmp/acme-mn-results');OUT.mkdir(exist_ok=True)
BEFORE=Path('/tmp/acme-mn-before');AFTER=Path('/tmp/acme-mn-after')
BRANCH='audit/bounded-backlog-mn-validated-20260923'
T='addons/acm_extended/tools/'
MTEST=T+'test_bounded_head_completion.py';NTEST=T+'test_bounded_head_pose_contracts.py'
SNAP='tools/test_self_audit_20260922.py'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
PATCHES={}
(OUT/'transport-payload.json').write_text(json.dumps(P,indent=2))
for label in ('M','N'):
    wire=P[label]['gzip_base64']
    # Remove one identified duplicated transport syllable; the original decoded hash must still match.
    wire=wire.replace('KEy/yvSySy7','KEy/yvSy7')
    raw=gzip.decompress(base64.b64decode(wire,validate=True))
    assert hashlib.sha256(raw).hexdigest()==P[label]['sha256'],label+' patch checksum mismatch'
    path=OUT/(label+'.patch');path.write_bytes(raw);PATCHES[label]=path
if '--transport-only' in sys.argv:
    print('Both decoded patch hashes verified.');sys.exit(0)


def git(root,*args):
    p=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=60)
    assert p.returncode==0,(args,p.stdout,p.stderr)
    return p.stdout.strip()


def digest(root,path):return hashlib.sha256((root/path).read_bytes()).hexdigest()

def manifest(root):
    return {p:digest(root,p) for p in git(root,'ls-files','-z').split('\0') if p}


def run(name,root,args,timeout=450):
    with (OUT/(name+'.log')).open('w') as stream:
        r=subprocess.run(args,cwd=root,text=True,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
    print(name,'exit',r.returncode,(OUT/(name+'.log')).read_text()[-2200:],flush=True)
    return r.returncode


def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=no','--continue-on-collection-errors','--junitxml='+str(xml)])
    result={}
    for case in ET.parse(xml).iter('testcase'):
        cname=case.get('name','')
        # Only reviewed digest-valued parameter labels are normalized for comparison.
        # The retained XML preserves original labels and every individual outcome.
        for path,hashes in P['snapshots'].items():
            for value in hashes.values():
                full=f'test_prior_fix_restored_without_rewrite[{path}-{value}]'
                if cname==full:cname=f'test_prior_fix_restored_without_rewrite[{path}-reviewed]'
        key=(case.get('classname',''),cname)
        status='error' if case.find('error') is not None else 'failed' if case.find('failure') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
        result.setdefault(key,Counter())[status]+=1
    counts=Counter()
    for value in result.values():counts.update(value)
    return rc,result,dict(counts)


def apply(label):
    git(AFTER,'apply','--check',str(PATCHES[label]));git(AFTER,'apply',str(PATCHES[label]))


def update_snapshots():
    original=(BEFORE/SNAP).read_text();text=original
    for path,hashes in P['snapshots'].items():
        assert digest(BEFORE,path)==hashes['before']
        assert digest(AFTER,path)==hashes['after']
        old=f"'{path}': '{hashes['before']}'";new=f"'{path}': '{hashes['after']}'"
        assert text.count(old)==1
        text=text.replace(old,new)
    (AFTER/SNAP).write_text(text)


def commit(label):
    git(AFTER,'add',*P[label]['paths'])
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com',
        'commit','-m',{'M':'Bounded M: guard head-position collision completion ordering',
                       'N':'Bounded N: reconcile connected patient pose and no-teleport contracts'}[label])
    return git(AFTER,'rev-parse','HEAD')


def ledger(root):
    return {l.split()[0]:l for l in (root/LEDGER).read_text().splitlines() if l.startswith('H')}


def check_test_bodies():
    for path,names in P['reviewed'].items():
        def normalized(root):
            tree=ast.parse((root/path).read_text());seen=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.FunctionDef) and node.name in names:
                    seen.append(node.name);node.body=[ast.Pass()]
            assert sorted(seen)==sorted(names)
            return ast.dump(tree,include_attributes=False)
        assert normalized(BEFORE)==normalized(AFTER),'Unreviewed test edit: '+path


git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE);(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert len(ledger(BEFORE))==115
selected_before=tests('selected-before',BEFORE,P['selected'])
assert selected_before[0]==1 and selected_before[2]=={'failed':6},selected_before[2]
apply('M');update_snapshots()
# Run the new M cases against the old runtime before accepting the runtime correction.
(BEFORE/MTEST).write_bytes((AFTER/MTEST).read_bytes())
old_m=tests('M-original-runtime',BEFORE,[MTEST])
assert old_m[0]==1 and old_m[2]=={'failed':6,'passed':14},old_m[2]
(BEFORE/MTEST).unlink()
m=tests('batch-M',AFTER,[MTEST,SNAP])
assert m[0]==0 and m[2]=={'passed':97},m[2]
sha_m=commit('M')
apply('N');check_test_bodies()
# N validates existing behavior and must also pass on unchanged K-L source.
for path in (MTEST,NTEST):(BEFORE/path).write_bytes((AFTER/path).read_bytes())
old_n=tests('N-original-runtime',BEFORE,[NTEST])
assert old_n[0]==0 and old_n[2]=={'passed':30},old_n[2]
for path in (MTEST,NTEST):(BEFORE/path).unlink()
assert manifest(BEFORE)==original
assert len(ledger(AFTER))==109
assert set(ledger(BEFORE))-set(ledger(AFTER))==set(P['resolved'])
assert all(ledger(AFTER).get(k)==v for k,v in ledger(BEFORE).items() if k not in P['resolved'])
focused=tests('focused',AFTER,P['selected']+[MTEST,NTEST,T+'test_historical_chest_workspace.py',T+'test_historical_pose_lifecycle.py',SNAP])
assert focused[0]==0 and set(focused[2])=={'passed'},focused[2]
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'addon-before',BEFORE,[T]);b=pool.submit(tests,'addon-after',AFTER,[T])
    left=a.result();right=b.result()
assert left[0]==right[0]==1
assert left[2].get('error',0)==right[2].get('error',0)==0
missing=set(left[1])-set(right[1]);changes=[];unexpected=[]
for key,old in left[1].items():
    if key not in right[1] or old==right[1][key]:continue
    if old==Counter({'failed':1}) and right[1][key]==Counter({'passed':1}):changes.append(key)
    else:unexpected.append((key,dict(old),dict(right[1][key])))
assert not missing and not unexpected,(missing,unexpected)
assert len(changes)==6,changes
assert {k[1] for k in changes}=={s.rsplit('::',1)[1] for s in P['selected']},changes
added=set(right[1])-set(left[1]);assert len(added)==50
assert all(right[1][k]==Counter({'passed':1}) for k in added)
assert left[2].get('skipped',0)==right[2].get('skipped',0)==4
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'root-before',BEFORE,['tools']);b=pool.submit(tests,'root-after',AFTER,['tools'])
    root_before=a.result();root_after=b.result()
assert root_before[0]==root_after[0]==1 and root_before[1]==root_after[1]
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
current=manifest(AFTER)
changed={p for p,h in original.items() if current.get(p)!=h}
expected=set(P['reviewed'])|set(P['snapshots'])|{LEDGER,SNAP}
assert changed==expected,changed
new_paths={p for label in ('M','N') for p in P[label]['paths']}-set(original)
assert set(original).issubset(current)
# Reversing just the reviewed digest replacements must recover the exact snapshot file.
back=(AFTER/SNAP).read_text()
for path,hashes in P['snapshots'].items():
    new=f"'{path}': '{hashes['after']}'";old=f"'{path}': '{hashes['before']}'"
    assert back.count(new)==1;back=back.replace(new,old)
assert back==(BEFORE/SNAP).read_text()
report={'base':BASE,'M':sha_m,'focused':focused[2],'old_runtime_M':old_m[2],
 'old_runtime_N':old_n[2],'addon_before':left[2],'addon_after':right[2],
 'root_before':root_before[2],'root_after':root_after[2],
 'resolved':P['resolved'],'remaining_original_entries':109,'new_tests':50,
 'newly_failing':[],'missing_previous':[],'runtime_files_changed':list(P['snapshots']),
 'unchanged_existing_files':len(original)-len(changed),'changed_existing_files':sorted(changed),
 'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
validation=f"\n## Complete-checkout validation\n\nFocused: {focused[2]}. M controls on original runtime: {old_m[2]}; N checks on original runtime: {old_n[2]}. Full addon before: {left[2]}; after: {right[2]}. Exactly six retained historical identities now pass and 50 new cases pass. No new failure or missing prior identity. Both full addon commands remain failing overall with four unchanged skips and zero collection/setup errors. Root before: {root_before[2]}; after: {root_after[2]}, with identical normalized identities and outcomes. Only the two reviewed digest-valued snapshot labels are normalized; raw JUnit remains in evidence. HEMTT check returns 0. Only the two documented collision-order runtime edits are present; {len(original)-len(changed)} other existing tracked files retain their SHA256. No live Arma or stable-release approval.\n"
with (AFTER/'docs/audits/2026-09-23-bounded-backlog-N.md').open('a') as f:f.write(validation)
sha_n=commit('N')
assert not git(AFTER,'status','--porcelain')
assert set(manifest(AFTER))-set(original)==new_paths
report.update({'N':sha_n,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(manifest(AFTER),indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('Bounded M-N on K-L. M changes collision-restore ordering in two head-position callbacks. N reconciles six old contracts. Source patches, complete test logs/JUnit and preservation evidence are included. No live Arma or stable-release approval.\n')
git(AFTER,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
