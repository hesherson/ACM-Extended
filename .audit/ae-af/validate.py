"""Validate reviewed teardown/selection changes, then publish two isolated commits."""
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import ast, base64, gzip, hashlib, json, os, subprocess, sys
import xml.etree.ElementTree as ET

BASE='a0f065f64952143015341bf818eb8061994f2e37'
BEFORE=Path('/tmp/acme-ae-af-before'); AFTER=Path('/tmp/acme-ae-af-after')
OUT=Path('/tmp/acme-ae-af-results'); OUT.mkdir(exist_ok=True)
T='addons/acm_extended/tools/'; F='addons/acm_extended/functions/'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
AE=T+'test_bounded_narc_close_generation.py'
AF=T+'test_bounded_site_click_handoff.py'
FIXTURE=T+'test_bounded_normal_push_lifetime.py'
STAGED=T+'test_bounded_staged_push_contracts.py'
DOC_AE='docs/audits/2026-09-23-bounded-backlog-AE.md'
DOC_AF='docs/audits/2026-09-23-bounded-backlog-AF.md'
REVIEWED={T+'test_b63_tag_carousel_interaction.py':'test_access_click_is_immediate_selected_syringe_administration',T+'test_b64_syringe_tag_carousel_refinement.py':'test_body_map_current_syringe_remains_immediate_administration_source'}
SELECTED=[p+'::'+n for p,n in REVIEWED.items()]
CHANGED=set(REVIEWED)|{F+'fn_skInject.sqf',F+'fn_skClose.sqf',FIXTURE,LEDGER}
ADDED={AE,AF,DOC_AE,DOC_AF}
BRANCH='audit/bounded-backlog-ae-af-validated-20260923'


def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=90)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()


def manifest(root):
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files','-z').split('\0') if p}


def run(name,root,args,timeout=420):
    with (OUT/(name+'.log')).open('w') as stream:
        r=subprocess.run(args,cwd=root,text=True,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
    print(name,'exit',r.returncode,flush=True)
    return r.returncode


def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=short','--continue-on-collection-errors','--junitxml='+str(xml)])
    result={}
    for c in ET.parse(xml).iter('testcase'):
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        key=(c.get('classname',''),c.get('name',''))
        result.setdefault(key,Counter())[status]+=1
    total=Counter()
    for value in result.values():total.update(value)
    print(name,dict(total),flush=True)
    return rc,result,dict(total)


def ledger(root):
    return {l.split()[0]:l for l in (root/LEDGER).read_text().splitlines() if l.startswith('H')}


def commit(paths,message):
    git(AFTER,'add',*paths)
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',message)
    return git(AFTER,'rev-parse','HEAD')


payload=json.loads(Path('.audit/ae-af/patch.json').read_text())
assert payload['base']==BASE
raw=gzip.decompress(base64.b64decode(payload['gzip_base64'],validate=True))
assert hashlib.sha256(raw).hexdigest()==payload['sha256'],'Patch transport mismatch'
patch=OUT/'reviewed.patch';patch.write_bytes(raw)
git(Path('.'),'fetch','--depth=1','origin',BASE)
for r in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(r),BASE)
original=manifest(BEFORE)
(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert len(ledger(BEFORE))==74
assert tests('historical-before',BEFORE,SELECTED)[2]=={'failed':2}
git(AFTER,'apply','--check',str(patch));git(AFTER,'apply',str(patch))
for p in ADDED:
    if p.endswith('.py'):
        compile((AFTER/p).read_text(),p,'exec')
        (BEFORE/p).write_bytes((AFTER/p).read_bytes())
ae_before=tests('AE-original-runtime',BEFORE,[AE])
af_before=tests('AF-original-runtime',BEFORE,[AF])
assert ae_before[2]=={'failed':16,'passed':6},ae_before[2]
assert af_before[2]=={'passed':14},af_before[2]
# Original full-suite accounting excludes candidate-only tests.
for p in (AE,AF):(BEFORE/p).unlink()
focused=tests('focused',AFTER,[AE,AF,FIXTURE,STAGED,*SELECTED])
assert focused[0]==0 and focused[2]=={'passed':86},focused[2]
# Existing historical bodies outside the reviewed two functions are unchanged.
for p,name in REVIEWED.items():
    def norm(text):
        tree=ast.parse(text)
        nodes=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name]
        assert len(nodes)==1
        nodes[0].body=[ast.Pass()]
        return ast.dump(tree,include_attributes=False)
    assert norm((BEFORE/p).read_text())==norm((AFTER/p).read_text()),p
expected_fixture=(BEFORE/FIXTURE).read_text().replace('private _drawDisplay=missionNamespace;', 'private _drawDisplay=missionNamespace;\n        // These push fixtures enter an already-injected draw display.\n        uiNamespace setVariable ["ACME_SK_CloseEpoch",1];\n        _drawDisplay setVariable ["ACME_SK_CloseEpoch",1];')
assert (AFTER/FIXTURE).read_text()==expected_fixture,'Unreviewed fixture change'
assert set(ledger(BEFORE))-set(ledger(AFTER))=={'H276','H292'}
assert len(ledger(AFTER))==72
assert all(v==ledger(AFTER).get(k) for k,v in ledger(BEFORE).items() if k not in {'H276','H292'})
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'addon-before',BEFORE,[T]); b=pool.submit(tests,'addon-after',AFTER,[T])
    before=a.result();after=b.result()
assert before[0]==after[0]==1
fixed=[];regressed=[]
for k,v in before[1].items():
    new=after[1].get(k)
    if new==v:continue
    if v==Counter({'failed':1}) and new==Counter({'passed':1}):fixed.append(k)
    else:regressed.append((k,dict(v),dict(new or {})))
assert not regressed,regressed
assert len(fixed)==2 and {x[1] for x in fixed}==set(REVIEWED.values()),fixed
added=set(after[1])-set(before[1])
assert len(added)==36 and all(after[1][k]==Counter({'passed':1}) for k in added)
assert before[2].get('error',0)==after[2].get('error',0)==0
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'root-before',BEFORE,['tools']);b=pool.submit(tests,'root-after',AFTER,['tools'])
    root_before=a.result();root_after=b.result()
assert root_before[1]==root_after[1]
assert root_before[0]==root_after[0]==1
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
assert run('diff-check',AFTER,['git','diff','--check'],30)==0
current=manifest(AFTER)
actual_changes={p for p in original if original[p]!=current.get(p)}
assert actual_changes==CHANGED,actual_changes
untracked=set(filter(None,git(AFTER,'ls-files','--others','--exclude-standard','-z').split('\0')))
assert untracked==ADDED,untracked
assert all((AFTER/p).is_file() for p in original),'Deleted original file'
report={'base':BASE,'AE_original_runtime':ae_before[2],'AF_original_runtime':af_before[2],'focused':focused[2],
        'addon_before':before[2],'addon_after':after[2],'root_before':root_before[2],'root_after':root_after[2],
        'resolved_original_ids':['H276','H292'],'remaining_original_entries':72,'new_passing_cases':36,
        'newly_failing':[],'missing_previous':[], 'changed_existing':sorted(CHANGED),
        'runtime_files_changed':[F+'fn_skInject.sqf',F+'fn_skClose.sqf'],
        'unchanged_existing_files':len(original)-len(CHANGED),'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
sha_ae=commit([F+'fn_skInject.sqf',F+'fn_skClose.sqf',FIXTURE,AE,DOC_AE], 'Bounded AE: bind Narc Box teardown to its injected display generation')
report['AE']=sha_ae
with (AFTER/DOC_AF).open('a') as stream:
    stream.write('\n## Complete-checkout validation\n\n```json\n'+json.dumps(report,indent=2)+'\n```\n\nBoth broad suites remain failing overall. All previous raw JUnit identities remain comparable, with no new skip or xfail. Protected snapshots are unchanged.\n')
sha_af=commit([*REVIEWED,AF,LEDGER,DOC_AF], 'Bounded AF: verify exact site staging and current-syringe confirmation')
assert not git(AFTER,'status','--porcelain')
report.update({'AF':sha_af,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(manifest(AFTER),indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('AE-AF builds on AC-AD. Two source patches, complete test logs/JUnit and preservation manifests. Runtime changes require a rebuilt testing package. No live Arma or stable-release approval.\n')
git(AFTER,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
