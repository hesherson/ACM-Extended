"""Verify the exact reviewed AC-AD patch on full worktrees; never update main."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast, base64, gzip, hashlib, json, os, subprocess, sys, xml.etree.ElementTree as ET

BASE='bf745808d8e92c56af211a1b32d315174a155004'
BEFORE=Path('/tmp/acme-ac-ad-before'); AFTER=Path('/tmp/acme-ac-ad-after')
OUT=Path('/tmp/acme-ac-ad-results'); OUT.mkdir(exist_ok=True)
T='addons/acm_extended/tools/'
F='addons/acm_extended/functions/'
DOC='docs/audits/'
LEDGER=DOC+'historical-backlog-remaining-20260922.txt'
RUNTIME=[F+'fn_skConfirmInjection.sqf',F+'fn_skClose.sqf']
NEW=[T+'test_bounded_normal_push_lifetime.py',T+'test_bounded_staged_push_contracts.py']
HIST={T+'test_b68_syringe_tag_push_layout.py':'test_body_map_site_click_runs_locked_three_second_visual_push_before_commit',T+'test_b76_carousel_push_memory.py':'test_staged_push'}
SELECTED=[p+'::'+n for p,n in HIST.items()]
BRANCH='audit/bounded-backlog-ac-ad-validated-20260923'


def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=60)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()


def manifest(root):
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files','-z').split('\0') if p}


def run(name,root,args,timeout=450):
    with (OUT/(name+'.log')).open('w') as f:
        r=subprocess.run(args,cwd=root,stdout=f,stderr=subprocess.STDOUT,text=True,timeout=timeout)
    return r.returncode


def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--continue-on-collection-errors','--tb=short','--junitxml='+str(xml)])
    outcomes={}
    for c in ET.parse(xml).iter('testcase'):
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        key=(c.get('classname',''),c.get('name',''))
        outcomes.setdefault(key,Counter())[status]+=1
    counts=Counter()
    for x in outcomes.values():counts.update(x)
    print(name,'exit',rc,dict(counts),flush=True)
    return rc,outcomes,dict(counts)


def ledger(root):
    return {l.split()[0]:l for l in (root/LEDGER).read_text().splitlines() if l.startswith('H')}


def check_test_bodies():
    for path,name in HIST.items():
        def normalized(root):
            tree=ast.parse((root/path).read_text()); seen=[]
            for n in ast.walk(tree):
                if isinstance(n,ast.FunctionDef) and n.name==name:
                    seen.append(n.name);n.body=[ast.Pass()]
            assert seen==[name]
            return ast.dump(tree,include_attributes=False)
        assert normalized(BEFORE)==normalized(AFTER),'Unreviewed historical assertion edit: '+path


# Transport is byte-verified before any candidate worktree is changed.
expected=['b96c5d6ebd2c7f303005013675a4b6d0d8ed2e439d20e00f2944303055330575','f16e48341268c2de7a275ad4c1dd83b5a2a97bf93fad3b581bd693594e1d2dc3','6237224a7aa27bed2e5028a4b75169d514741d6274ab6ee3977c7ef19c8c9f98']
parts=[]
for i,h in enumerate(expected):
    raw=Path(f'.audit/ac-ad/part{i}.txt').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==h,('Transport segment changed',i)
    parts.append(raw)
raw=gzip.decompress(base64.b64decode(b''.join(parts),validate=True))
assert hashlib.sha256(raw).hexdigest()=='f0f971db056de5a8b2c970405b3bbc2c79426e02286c6595499dd67ba99477f4'
patch=OUT/'reviewed.patch';patch.write_bytes(raw)
git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE);(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert len(ledger(BEFORE))==76
assert tests('historical-before',BEFORE,SELECTED)[2]=={'failed':2}
git(AFTER,'apply','--check',str(patch));git(AFTER,'apply',str(patch))
check_test_bodies()
assert set(ledger(BEFORE))-set(ledger(AFTER))=={'H319','H380'}
assert len(ledger(AFTER))==74
assert all(v==ledger(AFTER).get(k) for k,v in ledger(BEFORE).items() if k not in {'H319','H380'})
changed={p for p,h in original.items() if hashlib.sha256((AFTER/p).read_bytes()).hexdigest()!=h}
assert changed==set(RUNTIME)|set(HIST)|{LEDGER},changed

# Run new cases against the original runtime, retaining executable helpers but no production changes.
for p in NEW:(BEFORE/p).write_bytes((AFTER/p).read_bytes())
old=tests('AC-original-runtime',BEFORE,[NEW[0]])
assert old[0]==1 and old[2]=={'failed':21,'passed':16},old[2]
log=(OUT/'AC-original-runtime.log').read_text()
assert '[ERR]' not in log and '[FAT]' not in log
staging=tests('AD-original-runtime',BEFORE,[NEW[1]])
assert staging[0]==0 and staging[2]=={'passed':11},staging[2]
for p in NEW:(BEFORE/p).unlink()
focused=tests('focused',AFTER,NEW+SELECTED+[T+'test_push_seconds_execution.py',T+'test_slow_push_ui_default.py',T+'test_historical_syringe_identity.py','tools/test_self_audit_20260922.py'])
assert focused[0]==0 and focused[2]=={'passed':199},focused[2]

with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'addon-before',BEFORE,[T]);b=pool.submit(tests,'addon-after',AFTER,[T])
    before=a.result();after=b.result()
assert before[0]==after[0]==1
assert before[2].get('error',0)==after[2].get('error',0)==0
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
assert not (set(before[1])-set(after[1])),'Missing previous identities'
fixed=[]
for k,v in before[1].items():
    if after[1][k]==v:continue
    assert v==Counter({'failed':1}) and after[1][k]==Counter({'passed':1}),(k,v,after[1][k])
    fixed.append(k)
assert {k[1] for k in fixed}==set(HIST.values()) and len(fixed)==2,fixed
added=set(after[1])-set(before[1])
assert len(added)==48 and all(after[1][k]==Counter({'passed':1}) for k in added)
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'root-before',BEFORE,['tools']);b=pool.submit(tests,'root-after',AFTER,['tools'])
    root_before=a.result();root_after=b.result()
assert root_before[0]==root_after[0]==1 and root_before[1]==root_after[1]
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],150)==0
assert run('diff-check',AFTER,['git','diff','--check'],30)==0
assert all(hashlib.sha256((AFTER/p).read_bytes()).hexdigest()==h for p,h in original.items() if p not in changed)
report={'base':BASE,'AC_original_runtime':old[2],'AD_original_runtime':staging[2],'focused':focused[2],
        'addon_before':before[2],'addon_after':after[2],'root_before':root_before[2],'root_after':root_after[2],
        'resolved_original_ids':['H319','H380'],'remaining_original_entries':74,'new_passing_cases':48,
        'newly_failing':[],'missing_previous':[],'runtime_files_changed':RUNTIME,'changed_existing':sorted(changed),
        'unchanged_existing_files':len(original)-len(changed),'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
# Only reviewed files enter the two candidate commits; staging workflow never enters deployment history.
git(AFTER,'add',*RUNTIME,NEW[0],DOC+'2026-09-23-bounded-backlog-AC.md')
git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m','Bounded AC bind normal medication push callbacks to their originating context')
report['AC']=git(AFTER,'rev-parse','HEAD')
with (AFTER/(DOC+'2026-09-23-bounded-backlog-AD.md')).open('a') as f:
    f.write('\n## Complete-checkout validation\n\n```json\n'+json.dumps(report,indent=2)+'\n```\n\nBoth broad suites remain failing overall. Root identities and outcomes are unchanged, with no new skip or xfail. Engine boundaries are explicit fixtures, not live Arma or release-package validation.\n')
git(AFTER,'add',*HIST,NEW[1],LEDGER,DOC+'2026-09-23-bounded-backlog-AD.md')
git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m','Bounded AD reconcile staged target and timed confirmation contracts')
assert not git(AFTER,'status','--porcelain')
report.update({'AD':git(AFTER,'rev-parse','HEAD'),'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(manifest(AFTER),indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('AC-AD: normal staged-push ownership and current confirmation tests. Includes separate Git patches, raw logs, JUnit identities, report and source-preservation manifests. Rebuild for live testing; no stable-release approval.\n')
git(AFTER,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
