"""Validate two narrow patches against I-J before publishing a review branch."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast, base64, gzip, hashlib, json, os, shutil, subprocess, sys
import xml.etree.ElementTree as ET

BASE='8ceec1ce08bd16af28064e3914f7277da010c6b1'
OUT=Path('/tmp/acme-kl-results'); OUT.mkdir(exist_ok=True)
P=json.loads(Path('.audit/kl/payload.json').read_text())
assert P['base']==BASE
shutil.copy('.audit/kl/payload.json',OUT/'transport-payload.json')
for label in ('K','L'):
    raw=gzip.decompress(base64.b64decode(P[label]['gzip'],validate=True))
    assert hashlib.sha256(raw).hexdigest()==P[label]['sha256'], label+' patch transport changed'
    (OUT/(label+'.patch')).write_bytes(raw)
if '--transport-only' in sys.argv:
    print('Both patch payloads verified.');sys.exit(0)
BEFORE=Path('/tmp/acme-kl-before'); AFTER=Path('/tmp/acme-kl-after')
BRANCH='audit/bounded-backlog-kl-validated-20260923'
T='addons/acm_extended/tools/'
NEW=[T+'test_bounded_tag_color_focus.py',T+'test_bounded_tag_dropdowns.py']
RUNTIME=['addons/acm_extended/functions/fn_skTagColor.sqf','addons/acm_extended/functions/fn_skPendingTagColor.sqf']
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'


def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=90)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()


def manifest(root):
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest()
            for p in git(root,'ls-files','-z').split('\0') if p}


def run(name,root,args,timeout=440):
    with (OUT/(name+'.log')).open('w') as out:
        r=subprocess.run(args,cwd=root,stdout=out,stderr=subprocess.STDOUT,text=True,timeout=timeout)
    print(name,'exit',r.returncode,(OUT/(name+'.log')).read_text()[-1800:],flush=True)
    return r.returncode


def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=short',
                     '--continue-on-collection-errors','--junitxml='+str(xml)])
    outcomes={}
    for c in ET.parse(xml).iter('testcase'):
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        key=(c.get('classname',''),c.get('name',''))
        outcomes.setdefault(key,Counter())[status]+=1
    count=Counter()
    for value in outcomes.values(): count.update(value)
    print(name,json.dumps(dict(count)),flush=True)
    return rc,outcomes,dict(count)


def commit(label):
    git(AFTER,'add',*P[label]['paths'])
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com',
        'commit','-m',{'K':'Bounded K: scope delayed tag-color focus to originating context',
                       'L':'Bounded L: reconcile click-only tag dropdown contracts'}[label])
    return git(AFTER,'rev-parse','HEAD')


def ledger(root):
    return {line.split()[0]:line for line in (root/LEDGER).read_text().splitlines() if line.startswith('H')}


def compare_test_bodies():
    for path,names in P['reviewed'].items():
        def normalized(root):
            tree=ast.parse((root/path).read_text());seen=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.FunctionDef) and node.name in names:
                    seen.append(node.name); node.body=[ast.Pass()]
            assert sorted(seen)==sorted(names)
            return ast.dump(tree,include_attributes=False)
        assert normalized(BEFORE)==normalized(AFTER),'Unreviewed test edit '+path


git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE)
(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert len(ledger(BEFORE))==119
selected=tests('selected-before',BEFORE,list(P['selected'].values()))
assert selected[0]==1 and selected[2]=={'failed':4}
git(AFTER,'apply','--check',str(OUT/'K.patch'));git(AFTER,'apply',str(OUT/'K.patch'))
k=tests('batch-K',AFTER,[NEW[0],T+'test_bounded_tag_focus.py',T+'test_historical_syringe_identity.py'])
assert k[0]==0 and k[2]=={'passed':109},k[2]
sha_k=commit('K')
git(AFTER,'apply','--check',str(OUT/'L.patch'));git(AFTER,'apply',str(OUT/'L.patch'))
compare_test_bodies()
for path in NEW:shutil.copy(AFTER/path,BEFORE/path)
old=tests('new-tests-original-runtime',BEFORE,NEW)
assert old[0]==1 and old[2]=={'failed':14,'passed':40},old[2]
oldlog=(OUT/'new-tests-original-runtime.log').read_text()
assert '[ERR]' not in oldlog and '[FAT]' not in oldlog
for path in NEW:(BEFORE/path).unlink()
assert set(ledger(BEFORE))-set(ledger(AFTER))==set(P['selected'])
assert len(ledger(AFTER))==115
assert all(value==ledger(AFTER).get(key) for key,value in ledger(BEFORE).items() if key not in P['selected'])
for path in RUNTIME:
    # Immediate color/record updates are unchanged; only deferred focus ownership is revised.
    marker='call ACME_fnc_skCarouselRender;' if path.endswith('/fn_skTagColor.sqf') else 'call ACME_fnc_skPendingTagRender;'
    left=(BEFORE/path).read_text().split(marker,1)[0]
    right=(AFTER/path).read_text().split(marker,1)[0]
    assert left==right,'Immediate writer changed '+path
focus=tests('focused',AFTER,P['focused'])
assert focus[0]==0 and set(focus[2])=={'passed'},focus[2]
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'addon-before',BEFORE,[T]); b=pool.submit(tests,'addon-after',AFTER,[T])
    before=a.result(); after=b.result()
assert before[0]==after[0]==1
assert before[2].get('error',0)==after[2].get('error',0)==0
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
missing=set(before[1])-set(after[1]);fixed=[];regressions=[]
for key,value in before[1].items():
    if key not in after[1] or value==after[1][key]:continue
    if value==Counter({'failed':1}) and after[1][key]==Counter({'passed':1}):fixed.append(key)
    else:regressions.append((key,dict(value),dict(after[1][key])))
added=set(after[1])-set(before[1])
assert not missing and not regressions,(missing,regressions)
assert len(fixed)==4 and {key[1] for key in fixed}=={value.rsplit('::',1)[1] for value in P['selected'].values()},fixed
assert len(added)==54 and all(after[1][key]==Counter({'passed':1}) for key in added)
root_before=tests('root-before',BEFORE,['tools']);root_after=tests('root-after',AFTER,['tools'])
assert root_before[1]==root_after[1],'Root test identities/outcomes changed'
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
current=manifest(AFTER)
changed={path for path,digest in original.items() if current.get(path)!=digest}
expected=set(RUNTIME)|set(P['reviewed'])|{LEDGER}
assert changed==expected,changed
allowed_additions={path for label in ('K','L') for path in P[label]['paths']} - set(original)
# Files from L are untracked until its final commit; filesystem hashes still checked below.
assert all((AFTER/path).is_file() for path in allowed_additions)
report={'base':BASE,'K':sha_k,'batch_K':k[2],'original_runtime_controls':old[2],'focused':focus[2],
        'addon_before':before[2],'addon_after':after[2],'root_before':root_before[2],'root_after':root_after[2],
        'fixed_original_ids':list(P['selected']),'fixed_test_identities':fixed,'new_passing_cases':54,
        'newly_failing':[],'missing_previous':[],'original_backlog_remaining':115,
        'runtime_files_changed':RUNTIME,'changed_existing':sorted(changed),
        'unchanged_existing_files':len(original)-len(changed),'hemtt_exit':0,
        'live_arma_tested':False,'stable_release_approved':False}
(OUT/'comparison.json').write_text(json.dumps(report,indent=2))
with (AFTER/'docs/audits/2026-09-23-bounded-backlog-L.md').open('a') as doc:
    doc.write('\n## Complete-checkout validation\n\n'+f'Focused: {focus[2]}. New cases on original I-J runtime: {old[2]}; failures reproduce the color-focus defect. Full addon before: {before[2]}; after: {after[2]}. Exactly four retained historical identities now pass and all 54 new cases pass. No prior identity is missing or newly failing. Both addon commands remain failing overall with the same four skips and zero collection/setup errors. Root before: {root_before[2]}; after: {root_after[2]}, with identical identities/outcomes. Full-project HEMTT check returns 0. Only the two documented color-focus runtime files change. All {len(original)-len(changed)} other existing tracked files retain their complete-checkout SHA256, including every other runtime, configuration, asset and protected snapshot. No live Arma or stable-release approval.\n')
sha_l=commit('L')
assert not git(AFTER,'status','--porcelain')
final=manifest(AFTER)
assert set(original).issubset(final) and set(final)-set(original)==allowed_additions
assert {path for path,digest in original.items() if final.get(path)!=digest}==expected
report.update({'L':sha_l,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(final,indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('K-L layered on I-J. K changes two tag-color focus callbacks; rebuild to test it. L reconciles four historical contracts. Includes separate git patches, JUnit, logs and complete source-preservation manifests. No stable-release approval.\n')
git(AFTER,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
