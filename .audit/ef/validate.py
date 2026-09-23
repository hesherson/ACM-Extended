"""Publish only the reviewed test-only E-F candidate after bounded verification."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast,base64,gzip,hashlib,json,os,re,subprocess,sys,xml.etree.ElementTree as ET
BASE='390820d37fbb477451b720aa2f7c91214d3519f3'
OUT=Path('/tmp/acme-ef-results');OUT.mkdir(exist_ok=True)
BEFORE=Path('/tmp/acme-ef-before');AFTER=Path('/tmp/acme-ef-after')
BRANCH='audit/bounded-backlog-ef-validated-20260923'
T='addons/acm_extended/tools/'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
IDS={'E':['H213','H374','H220'],'F':['H044','H165','H175','H186','H188','H203']}
REVIEWED={
 T+'test_b57_pose_rules_narcbox_cohesion.py':['test_final_syringe_name_is_25_char_unicode_metadata'],
 T+'test_b75_direct_pressure_tag_flush.py':['test_tag_limit_is_exactly_17_and_commits_are_defensive'],
 T+'test_b58_syringe_carousel_tags.py':['test_tags_have_three_editors_and_all_colors'],
 T+'test_b22_narc_revert.py':['test_infusion_inherits_same_original_row_overlay'],
 T+'test_b45_medication_steth_io_logs.py':['test_medication_column_visible_in_body_and_infusion_views'],
 T+'test_b46_narcbox_medication_render.py':['test_medication_group_stays_visible_in_body_and_infusion_paths'],
 T+'test_b48_medication_animation_orientation.py':['test_native_medication_list_is_the_only_renderer','test_prep_infusion_uses_same_medication_list'],
 T+'test_b50_animation_medication_prepared.py':['test_medication_three_column_overlay_is_restored_and_direct_data_driven']}
NEW={'E':T+'test_bounded_tag_contracts.py','F':T+'test_bounded_medication_presentation.py'}
DOC={x:f'docs/audits/2026-09-23-bounded-backlog-{x}.md' for x in IDS}
P=json.loads(Path('.audit/ef/patches.json').read_text());assert P['base']==BASE
# Exact local patch hashes fail closed before checkout or production writes.
PATCH={}
for label in IDS:
 wire=''.join(Path('.audit/ef/E.b64').read_text().split()) if label=='E' else P[label]['gzip']
 raw=gzip.decompress(base64.b64decode(wire,validate=True))
 assert hashlib.sha256(raw).hexdigest()==P[label]['sha256'],label+' patch transport mismatch'
 p=OUT/f'bounded-{label}.patch';p.write_bytes(raw);PATCH[label]=p
print('BOTH_PATCH_HASHES_VERIFIED',flush=True)

def git(root,*args):
 r=subprocess.run(['git',*args],cwd=root,capture_output=True,text=True,timeout=60)
 assert r.returncode==0,(args,r.stdout,r.stderr)
 return r.stdout.strip()

def manifest(root):
 return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files','-z').split('\0') if p}

def ledger(root):
 return {l.split()[0]:l.split(' ',1)[1] for l in (root/LEDGER).read_text().splitlines() if re.match(r'^H\d+ ',l)}

def run(name,root,args,timeout=420):
 with (OUT/(name+'.log')).open('w') as f:
  r=subprocess.run(args,cwd=root,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,text=True)
 print(name,'exit',r.returncode,(OUT/(name+'.log')).read_text()[-1600:],flush=True)
 return r.returncode

def tests(name,root,paths):
 xml=OUT/(name+'.xml')
 rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=no','--continue-on-collection-errors','--junitxml='+str(xml)])
 outcomes={}
 for c in ET.parse(xml).iter('testcase'):
  status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
  key=(c.get('classname',''),c.get('name',''));outcomes.setdefault(key,Counter())[status]+=1
 counts=Counter()
 for v in outcomes.values():counts.update(v)
 return rc,outcomes,dict(counts)

def scope_check():
 for path,names in REVIEWED.items():
  def normalized(root):
   tree=ast.parse((root/path).read_text());seen=[]
   for n in ast.walk(tree):
    if isinstance(n,ast.FunctionDef) and n.name in names:seen.append(n.name);n.body=[ast.Pass()]
   assert sorted(seen)==sorted(names)
   return ast.dump(tree,include_attributes=False)
  assert normalized(BEFORE)==normalized(AFTER),'unreviewed test statements: '+path

def commit(label,paths):
 git(AFTER,'add',*paths)
 git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',f'Reconcile current tag and medication UI contracts (bounded {label})')
 return git(AFTER,'rev-parse','HEAD')

git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE);oldledger=ledger(BEFORE);assert len(oldledger)==141
(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
selected=[oldledger[k] for label in IDS for k in IDS[label]]
assert tests('selected-before',BEFORE,selected)[2]=={'failed':9}
paths={}
for label in IDS:
 git(AFTER,'apply','--check',str(PATCH[label]));git(AFTER,'apply',str(PATCH[label]))
 diff=git(AFTER,'diff','--name-only');
 paths[label]=sorted(set(diff.splitlines())|{NEW[label],DOC[label]})
 if label=='E':
  c=tests('batch-E',AFTER,[oldledger[k] for k in IDS['E']]+[NEW['E']])
  assert c[0]==0 and c[2]=={'passed':22},c[2]
  assert len(ledger(AFTER))==138
  sha_e=commit('E',paths[label])
scope_check()
current=manifest(AFTER)
changed={p for p in original if current.get(p)!=original[p]}
assert changed==set(REVIEWED)|{LEDGER},changed
newledger=ledger(AFTER)
assert len(newledger)==132 and set(oldledger)-set(newledger)==set(IDS['E']+IDS['F'])
assert all(v==newledger.get(k) for k,v in oldledger.items() if k not in IDS['E']+IDS['F'])
focused=tests('focused',AFTER,selected+list(NEW.values())+[T+x for x in ['test_historical_syringe_identity.py','test_historical_medication_rows.py','test_historical_carousel_input.py']]+['tools/test_self_audit_20260922.py'])
assert focused[0]==0 and focused[2]=={'passed':330},focused[2]
# All 50 added checks execute unchanged production source: the complete runtime hashes are identical.
with ThreadPoolExecutor(max_workers=2) as pool:
 a=pool.submit(tests,'addon-before',BEFORE,[T]);b=pool.submit(tests,'addon-after',AFTER,[T]);before=a.result();after=b.result()
assert before[0]==after[0]==1
assert before[2].get('error',0)==after[2].get('error',0)==0
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
missing=set(before[1])-set(after[1]);assert not missing,missing
fixed=[];regressed=[]
for k,v in before[1].items():
 if v==after[1][k]:continue
 if v==Counter({'failed':1}) and after[1][k]==Counter({'passed':1}):fixed.append(k)
 else:regressed.append((k,dict(v),dict(after[1][k])))
assert not regressed,regressed
assert len(fixed)==9 and {k[1] for k in fixed}=={s.rsplit('::',1)[1] for s in selected},fixed
added=set(after[1])-set(before[1]);assert len(added)==50
assert all(after[1][k]==Counter({'passed':1}) for k in added)
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
current=manifest(AFTER)
assert all(current[p]==h for p,h in original.items() if p not in changed)
report={'base':BASE,'E':sha_e,'focused':focused[2],'addon_before':before[2],'addon_after':after[2],
 'fixed_original_ids':IDS['E']+IDS['F'],'fixed_pytest_identities':fixed,'new_passing_cases':50,
 'newly_failing':[],'missing_previous':[],'remaining_original_entries':132,
 'runtime_files_changed':0,'unchanged_existing_files':len(original)-len(changed),
 'changed_existing_files':sorted(changed),'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
(OUT/'comparison.json').write_text(json.dumps(report,indent=2))
with (AFTER/DOC['F']).open('a') as f:
 f.write('\n## Complete-checkout validation\n\n'+f'Focused: {focused[2]}. Full historical addon before: {before[2]}. After: {after[2]}. Exactly nine historical identities now pass, all 50 new cases pass, and no prior identity is missing or newly failing. Both full-suite commands still return 1 with four existing skips and zero collection/setup errors. Full-project HEMTT check returns 0. All {len(original)-len(changed)} other existing tracked files retain their complete-checkout SHA256, including every runtime/configuration/asset file. The root preservation module is included; the entire root-tools suite was not rerun. No live Arma or stable-release approval.\n')
sha_f=commit('F',paths['F'])
assert not git(AFTER,'status','--porcelain')
final=manifest(AFTER);assert set(final)-set(original)==set(NEW.values())|set(DOC.values())
report.update({'F':sha_f,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(final,indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('Test-only E-F, layered on 390820d3. No PBO rebuild required for E-F alone. Patches, logs, JUnit and complete-checkout preservation manifests included. No stable-release approval.\n')
git(AFTER,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
