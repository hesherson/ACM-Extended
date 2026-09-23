"""Validate two bounded test-only commits. Never update main or the release branch."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast, base64, gzip, hashlib, json, os, shutil, subprocess, sys
import xml.etree.ElementTree as ET

BASE='99da8584547c083c8a882c7786558885d6b8a5f7'
BRANCH='audit/bounded-backlog-gh-validated-20260923'
OUT=Path('/tmp/acme-gh-results'); OUT.mkdir(exist_ok=True)
BEFORE=Path('/tmp/acme-gh-before'); AFTER=Path('/tmp/acme-gh-after')
T='addons/acm_extended/tools/'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
IDS={'G':['H170','H171','H172','H430','H437'],'H':['H252','H265','H303']}
DIGEST={'G':'3ccbf4abb5e3e93b2aa2983861fb5be5bafe99673dc68eeccc71751514c1c909',
        'H':'7b5032f4540fa62eadb39bc7c93237948bf802639106f69e7e2cef60aa80c6c7'}
NEW={'G':T+'test_bounded_stock_columns.py','H':T+'test_bounded_syringe_tooltips.py'}
OLD={'G':[T+'test_b46_narcbox_medication_render.py',T+'test_na8_5_batch2.py',T+'test_na8_5_batch5.py'],
     'H':[T+'test_b61_carousel_bodymap_refinement.py',T+'test_b62_tag_editor_carousel_layout.py',T+'test_b66_syringe_carousel_main_tag.py']}
DOC={label:f'docs/audits/2026-09-23-bounded-backlog-{label}.md' for label in IDS}
PATHS={label:OLD[label]+[NEW[label],LEDGER,DOC[label]] for label in IDS}

def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=60)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()

def manifest(root):
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files','-z').split('\0') if p}

def run(name,root,args,timeout=450):
    with (OUT/(name+'.log')).open('w') as stream:
        r=subprocess.run(args,cwd=root,text=True,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
    print(name,'exit',r.returncode,(OUT/(name+'.log')).read_text()[-1400:],flush=True)
    return r.returncode

def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=short','--continue-on-collection-errors','--junitxml='+str(xml)])
    outcomes={}
    for c in ET.parse(xml).iter('testcase'):
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        key=(c.get('classname',''),c.get('name',''))
        outcomes.setdefault(key,Counter())[status]+=1
    counts=Counter()
    for v in outcomes.values():counts.update(v)
    return rc,outcomes,dict(counts)

def ledger(root):
    return {l.split()[0]:l for l in (root/LEDGER).read_text().splitlines() if l.startswith('H')}

def patch(label):
    wire=Path('.audit/gh/'+label+'.b64').read_text().strip()
    raw=gzip.decompress(base64.b64decode(wire,validate=True))
    assert hashlib.sha256(raw).hexdigest()==DIGEST[label],'Transport digest mismatch '+label
    p=OUT/('bounded-'+label+'.patch');p.write_bytes(raw)
    git(AFTER,'apply','--check',str(p));git(AFTER,'apply',str(p))

def commit(label):
    git(AFTER,'add',*PATHS[label])
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',f'Verify current stock and tooltip contracts without runtime changes (bounded {label})')
    assert not git(AFTER,'status','--porcelain')
    return git(AFTER,'rev-parse','HEAD')

# Verify payload integrity before expensive validation or source edits.
for label in IDS:
    raw=gzip.decompress(base64.b64decode(Path('.audit/gh/'+label+'.b64').read_text().strip(),validate=True))
    assert hashlib.sha256(raw).hexdigest()==DIGEST[label]
git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE)
(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
initial=ledger(BEFORE);assert len(initial)==132
selected={k:initial[k].split(' ',1)[1] for k in IDS['G']+IDS['H']}
assert tests('selected-before',BEFORE,list(selected.values()))[2]=={'failed':8}
patch('G')
g=tests('batch-G',AFTER,[selected[k] for k in IDS['G']]+[NEW['G']])
assert g[0]==0 and g[2]=={'passed':37},g[2]
assert len(ledger(AFTER))==127
sha_g=commit('G')
patch('H')
# Retain all unreviewed test ASTs, signatures, decorators, imports and assertions.
reviewed={}
for nodeid in selected.values():
    path,name=nodeid.split('::',1);reviewed.setdefault(path,[]).append(name.rsplit('::',1)[-1])
for path,names in reviewed.items():
    def normalized(root):
        tree=ast.parse((root/path).read_text());seen=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.FunctionDef) and node.name in names:
                seen.append(node.name);node.body=[ast.Pass()]
        assert sorted(seen)==sorted(names),(path,seen,names)
        return ast.dump(tree,include_attributes=False)
    assert normalized(BEFORE)==normalized(AFTER),'Unreviewed test change '+path
current=manifest(AFTER);changed={p for p,h in original.items() if current.get(p)!=h}
assert changed==set(reviewed)|{LEDGER},changed
assert all(current[p]==h for p,h in original.items() if p not in changed)
remaining=ledger(AFTER)
assert len(remaining)==124 and set(initial)-set(remaining)==set(selected)
assert all(initial[k]==v for k,v in remaining.items())
# New cases pass on the original runtime as well; these are stale contracts, not runtime fixes.
for path in NEW.values():
    assert not (BEFORE/path).exists();shutil.copyfile(AFTER/path,BEFORE/path)
control=tests('new-tests-unchanged-runtime',BEFORE,list(NEW.values()))
assert control[0]==0 and control[2]=={'passed':69},control[2]
for path in NEW.values():(BEFORE/path).unlink()
assert manifest(BEFORE)==original
focus=list(selected.values())+[T+n for n in [
 'test_bounded_stock_columns.py','test_bounded_syringe_tooltips.py',
 'test_historical_medication_rows.py','test_historical_vial_execution.py',
 'test_bounded_medication_presentation.py','test_historical_syringe_identity.py',
 'test_historical_carousel_input.py','test_bounded_tag_contracts.py',
 'test_bounded_stethoscope_exit_generation.py']]+['tools/test_self_audit_20260922.py']
f=tests('focused',AFTER,focus)
assert f[0]==0 and f[2]=={'passed':453},f[2]
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'addon-before',BEFORE,[T]);b=pool.submit(tests,'addon-after',AFTER,[T])
    before=a.result();after=b.result()
assert before[0]==after[0]==1
assert before[2].get('error',0)==after[2].get('error',0)==0
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
missing=set(before[1])-set(after[1]);fixed=[];regressions=[]
for key,old in before[1].items():
    if key not in after[1]:continue
    new=after[1][key]
    if old==new:continue
    if old==Counter({'failed':1}) and new==Counter({'passed':1}):fixed.append(key)
    else:regressions.append((key,dict(old),dict(new)))
assert not missing and not regressions,(missing,regressions)
assert len(fixed)==8 and {k[1] for k in fixed}=={s.rsplit('::',1)[1] for s in selected.values()},fixed
added=set(after[1])-set(before[1])
assert len(added)==69 and all(after[1][k]==Counter({'passed':1}) for k in added)
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
current=manifest(AFTER)
assert all(current[p]==h for p,h in original.items() if p not in changed)
report={'base':BASE,'G':sha_g,'focused':f[2],'unchanged_runtime_control':control[2],
        'addon_before':before[2],'addon_after':after[2],'fixed_original_ids':list(selected),
        'fixed_pytest_identities':fixed,'new_passing_cases':len(added),'newly_failing':[],
        'missing_previous':[],'remaining_original_entries':124,'runtime_files_changed':0,
        'unchanged_existing_files':len(original)-len(changed),'changed_existing_files':sorted(changed),
        'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
(OUT/'comparison.json').write_text(json.dumps(report,indent=2))
with (AFTER/DOC['H']).open('a') as out:
    out.write('\n## Complete-checkout validation\n\n'+f'Focused: {f[2]}. New cases on unchanged runtime: {control[2]}. Full addon before: {before[2]}. After: {after[2]}. Exactly eight retained historical identities now pass, 69 new cases pass, and no previous identity is missing or newly failing. Both full commands return 1, retaining four existing skips and zero collection/setup errors. Full-project HEMTT check returns 0. All {len(original)-len(changed)} other existing tracked files retain their SHA256, including every runtime/configuration/asset file and all protected snapshots. Root preservation is included; the entire root-tools suite was not rerun. No live Arma or stable-release approval.\n')
sha_h=commit('H')
report.update({'H':sha_h,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'final-manifest.json').write_text(json.dumps(manifest(AFTER),indent=2))
(OUT/'README.txt').write_text('Test-only backlog G-H, layered on E-F 99da8584. Includes separate git patches, logs, JUnit and exact preservation evidence. No gameplay rebuild required for G-H alone. No stable-release approval.\n')
git(AFTER,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
