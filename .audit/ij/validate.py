"""Validate the exact I-J patch payload on complete G-H worktrees, then publish review only."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast,base64,gzip,hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET

P=json.loads(Path('.audit/ij/payload.json').read_text())
BASE=P['base'];assert BASE=='29ed91cf1239b6bccb6c946d2b177b007cdd7318'
OUT=Path('/tmp/acme-ij-results');OUT.mkdir(exist_ok=True)
BEFORE=Path('/tmp/acme-ij-before');AFTER=Path('/tmp/acme-ij-after')
BRANCH='audit/bounded-backlog-ij-validated-20260923'
T='addons/acm_extended/tools/'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
RUNTIME=['addons/acm_extended/functions/fn_skTagEditOpen.sqf','addons/acm_extended/functions/fn_skTagEditDone.sqf']
IDS=['H259','H218','H225','H231','H248']
SELECTED=[P['resolved'][k].split(' ',1)[1] for k in IDS]
FOCUS=SELECTED+[T+'test_bounded_tag_focus.py',T+'test_bounded_page_navigation.py',T+'test_historical_carousel_input.py',T+'test_historical_syringe_identity.py','tools/test_self_audit_20260922.py']
REVIEWED={}
for selector in SELECTED:
    path,name=selector.split('::');REVIEWED.setdefault(path,[]).append(name)


def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=90)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()


def files(root):
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files','-z').split('\0') if p}


def run(name,root,args,timeout=540):
    print('START',name,flush=True)
    with (OUT/(name+'.log')).open('w') as stream:
        r=subprocess.run(args,cwd=root,stdout=stream,stderr=subprocess.STDOUT,text=True,timeout=timeout)
    print(name,'exit',r.returncode,(OUT/(name+'.log')).read_text()[-1800:],flush=True)
    return r.returncode


def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=short','--continue-on-collection-errors','--junitxml='+str(xml)])
    identities={}
    for case in ET.parse(xml).iter('testcase'):
        status='error' if case.find('error') is not None else 'failed' if case.find('failure') is not None else 'skipped' if case.find('skipped') is not None else 'passed'
        key=(case.get('classname',''),case.get('name',''))
        identities.setdefault(key,Counter())[status]+=1
    counts=Counter()
    for value in identities.values():counts.update(value)
    return rc,identities,dict(counts)


def unpack(label):
    wire=P[label]['patch_gzip_base64']
    # One identified transcription slip in the audit transport only. Fail closed on decoded SHA256.
    wire=wire.replace('YcqS6odrHe5NjfD6','YcqS6odrHeNjfD6')
    raw=gzip.decompress(base64.b64decode(wire,validate=True))
    assert hashlib.sha256(raw).hexdigest()==P[label]['patch_sha256'],'Unreviewed patch bytes: '+label
    path=OUT/('bounded-'+label+'.patch');path.write_bytes(raw)
    return path


def apply(label):
    path=unpack(label);git(AFTER,'apply','--check',str(path));git(AFTER,'apply',str(path))


def ledger(root):
    return {line.split()[0]:line for line in (root/LEDGER).read_text().splitlines() if line.startswith('H')}


def commit(label):
    git(AFTER,'add',*P[label]['paths'])
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',
        'Bounded I: prevent stale stored-tag autofocus' if label=='I' else 'Bounded J: reconcile current page navigation and typing contracts')
    return git(AFTER,'rev-parse','HEAD')


# Validate both transported patches before downloading or editing candidate files.
for label in ('I','J'):unpack(label)
git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=files(BEFORE);(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert len(ledger(BEFORE))==124
selected_before=tests('selected-before',BEFORE,SELECTED)
assert selected_before[2]=={'failed':5},selected_before[2]
apply('I')
# The new tests run against original runtime before accepting the correction.
saved={p:(AFTER/p).read_bytes() for p in RUNTIME}
try:
    for p in RUNTIME:(AFTER/p).write_bytes((BEFORE/p).read_bytes())
    red=tests('tag-focus-unchanged-source',AFTER,[T+'test_bounded_tag_focus.py'])
    assert red[0]==1 and red[2]=={'passed':15,'failed':8},red[2]
    redlog=(OUT/'tag-focus-unchanged-source.log').read_text()
    assert 'retired editor stole focus' in redlog and 'earlier editor generation stole focus' in redlog
    assert '[ERR]' not in redlog and '[FAT]' not in redlog
finally:
    for p,data in saved.items():(AFTER/p).write_bytes(data)
step_i=tests('batch-I',AFTER,[SELECTED[0],T+'test_bounded_tag_focus.py'])
assert step_i[0]==0 and step_i[2]=={'passed':24}
assert len(ledger(AFTER))==123
sha_i=commit('I')
apply('J')
# Every nonreviewed historical assertion body and declaration remains identical.
for path,names in REVIEWED.items():
    def unreviewed(root):
        tree=ast.parse((root/path).read_text());found=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.FunctionDef) and node.name in names:
                found.append(node.name);node.body=[ast.Pass()]
        assert sorted(found)==sorted(names)
        return ast.dump(tree,include_attributes=False)
    assert unreviewed(BEFORE)==unreviewed(AFTER),'Unreviewed test edit: '+path
assert set(ledger(BEFORE))-set(ledger(AFTER))==set(IDS)
assert len(ledger(AFTER))==119
assert all(ledger(AFTER).get(k)==v for k,v in ledger(BEFORE).items() if k not in IDS)
focused=tests('focused',AFTER,FOCUS)
assert focused[0]==0 and focused[2]=={'passed':282},focused[2]
# Full parent/candidate comparisons are bounded and recorded, including their failing exit codes.
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'addon-before',BEFORE,[T]);b=pool.submit(tests,'addon-after',AFTER,[T])
    before=a.result();after=b.result()
assert before[0]==after[0]==1
assert before[2].get('error',0)==after[2].get('error',0)==0
fixed=[];other=[]
missing=set(before[1])-set(after[1])
for key,old in before[1].items():
    if key not in after[1]:continue
    new=after[1][key]
    if new==old:continue
    if old==Counter({'failed':1}) and new==Counter({'passed':1}):fixed.append(key)
    else:other.append((key,dict(old),dict(new)))
assert not missing and not other,(missing,other)
assert len(fixed)==5 and {k[1] for k in fixed}=={s.split('::')[1] for s in SELECTED},fixed
added=set(after[1])-set(before[1])
assert len(added)==45 and all(after[1][k]==Counter({'passed':1}) for k in added)
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'root-before',BEFORE,['tools']);b=pool.submit(tests,'root-after',AFTER,['tools'])
    root_before=a.result();root_after=b.result()
assert root_before[1]==root_after[1],'Root regression'
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
current=files(AFTER)
changed={p for p in original if current.get(p)!=original[p]}
assert changed==set(REVIEWED)|set(RUNTIME)|{LEDGER},changed
assert set(original).issubset(current),'Deleted file'
report={'base':BASE,'I':sha_i,'focused':focused[2],'unchanged_runtime_control':red[2],
        'addon_before':before[2],'addon_after':after[2],'root_before':root_before[2],'root_after':root_after[2],
        'fixed_original_ids':IDS,'fixed_pytest_identities':fixed,'new_passing_cases':len(added),
        'newly_failing':[],'missing_previous':[],'remaining_original_entries':119,
        'runtime_files_changed':RUNTIME,'changed_existing_files':sorted(changed),
        'unchanged_existing_files':len(original)-len(changed),'hemtt_exit':0,
        'live_arma_tested':False,'stable_release_approved':False}
(OUT/'comparison.json').write_text(json.dumps(report,indent=2))
validation='\n## Complete-checkout validation\n\n'+f'Focused: {focused[2]}. Original-runtime focus controls: {red[2]}. Full addon before: {before[2]}; after: {after[2]}. Exactly five retained historical identities now pass and 45 new cases pass. No newly failing or missing prior identities. Both addon commands still return 1 with four unchanged skips and zero collection/setup errors. Whole root suite before: {root_before[2]}; after: {root_after[2]}, with identical identities/outcomes. Full-project HEMTT check returns 0. Only the two documented tag-editor runtime files change; {len(original)-len(changed)} other existing tracked files retain their complete-checkout SHA256, including all other runtime, configuration, assets and protected snapshots. No live Arma or stable-release approval.\n'
with (AFTER/'docs/audits/2026-09-23-bounded-backlog-J.md').open('a') as f:f.write(validation)
sha_j=commit('J')
assert not git(AFTER,'status','--porcelain')
final=files(AFTER)
expected_new={p for label in ('I','J') for p in P[label]['paths']} - set(original)
assert set(final)-set(original)==expected_new
report.update({'J':sha_j,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(final,indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('I-J layered on G-H. I fixes stale stored-tag autofocus; J is test-only. Includes separate patches, complete before/after logs, JUnit, identities and manifests. Runtime rebuild needed to test I. No stable-release approval.\n')
git(AFTER,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
