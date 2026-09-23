"""Bounded S-T validation: exact diffs, original-code controls, no main writes."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast, base64, gzip, hashlib, json, os, subprocess, sys
import xml.etree.ElementTree as ET

P=json.loads(Path('.audit/st/payload.json').read_text())
BASE='fce7d83f742b51b037a7d252bda3d132950580e8'
assert P['base']==BASE
OUT=Path('/tmp/acme-st-results');OUT.mkdir(exist_ok=True)
B=Path('/tmp/acme-st-before');A=Path('/tmp/acme-st-after')
BRANCH='audit/bounded-backlog-st-validated-20260923'
T='addons/acm_extended/tools/'
NEW_S=T+'test_bounded_head_provider_consciousness.py'
NEW_T=T+'test_bounded_head_weapon_contract.py'
OLD=T+'test_b71_tag_head_intubation.py'
SELECTED=OLD+'::test_one_time_weapon_stow_no_restore_retained'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
RUNTIME={'addons/acm_extended/functions/fn_headElevMedicSeq.sqf','addons/acm_extended/functions/fn_headElevateCancelSeq.sqf'}

def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=60)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()

def manifest(root):
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files','-z').split('\0') if p}

def run(name,root,args,timeout=440):
    with (OUT/(name+'.log')).open('w') as f:
        r=subprocess.run(args,cwd=root,text=True,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    text=(OUT/(name+'.log')).read_text()
    print(name,'exit',r.returncode,text[-1800:],flush=True)
    return r.returncode

def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=no','--continue-on-collection-errors','--junitxml='+str(xml)])
    data={}
    for c in ET.parse(xml).iter('testcase'):
        key=(c.get('classname',''),c.get('name',''))
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        data.setdefault(key,Counter())[status]+=1
    counts=Counter()
    for v in data.values():counts.update(v)
    return rc,data,dict(counts)

def patch(label):
    wire=P[label]['patch_gzip_base64']
    # Exact text-transport repairs only. Original decompressed SHA256 is mandatory.
    for old,new in [('ANhUuFl6f6zLcHa','ANhUuFl6zLcHa'),('Jgfe6Pb0dTjB','Jgfe6PD0dTjB'),('0Xj0eX9LY','0Xj9LY'),('jgfh+Sdjcfw','jgfh+Djcfw')]:
        wire=wire.replace(old,new)
    (OUT/(label+'-wire.txt')).write_text(wire)
    raw=gzip.decompress(base64.b64decode(wire,validate=True))
    assert hashlib.sha256(raw).hexdigest()==P[label]['sha256'], 'Patch checksum mismatch: '+label
    dest=OUT/(label+'.patch');dest.write_bytes(raw)
    return dest

patches={label:patch(label) for label in ['S','T']}
if '--transport-only' in sys.argv:
    print('Both original patch SHA256 digests verified',flush=True);sys.exit(0)

git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in [B,A]:git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(B)
(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert tests('selected-before',B,[SELECTED])[2]=={'failed':1}
for label in ['S','T']:
    git(A,'apply','--check',str(patches[label]));git(A,'apply',str(patches[label]))
for file in [NEW_S,NEW_T]:(B/file).write_bytes((A/file).read_bytes())
old_s=tests('S-original-runtime',B,[NEW_S]);old_t=tests('T-original-runtime',B,[NEW_T])
assert old_s[2]=={'failed':18,'passed':6},old_s[2]
assert old_t[0]==0 and old_t[2]=={'passed':15},old_t[2]
for file in [NEW_S,NEW_T]:(B/file).unlink()
# Preserve every other statement in the one reconciled historical module.
def normalized(root):
    tree=ast.parse((root/OLD).read_text());seen=0
    for n in ast.walk(tree):
        if isinstance(n,ast.FunctionDef) and n.name=='test_one_time_weapon_stow_no_restore_retained':
            seen+=1;n.body=[ast.Pass()]
    assert seen==1
    return ast.dump(tree,include_attributes=False)
assert normalized(B)==normalized(A)
def ledger(root):return {l.split()[0]:l for l in (root/LEDGER).read_text().splitlines() if l.startswith('H')}
old_index=ledger(B);new_index=ledger(A)
assert len(old_index)==103 and len(new_index)==102
assert set(old_index)-set(new_index)=={'H344'}
assert all(new_index[k]==v for k,v in old_index.items() if k!='H344')
changed={p for p,v in original.items() if hashlib.sha256((A/p).read_bytes()).hexdigest()!=v}
assert changed==RUNTIME|{OLD,LEDGER},changed
focused=[NEW_S,NEW_T,T+'test_bounded_head_provider_sequence.py',T+'test_historical_weapon_preflight.py',T+'test_bug_audit_batch07_animation_ownership.py','tools/test_self_audit_20260922.py',SELECTED]
focus=tests('focused',A,focused)
assert focus[0]==0 and focus[2]=={'passed':198},focus[2]
with ThreadPoolExecutor(max_workers=2) as pool:
    fb=pool.submit(tests,'addon-before',B,[T]);fa=pool.submit(tests,'addon-after',A,[T])
    before=fb.result();after=fa.result()
assert before[0]==after[0]==1
fixed=[];regressed=[]
assert not set(before[1])-set(after[1]),'missing original identity'
for k,v in before[1].items():
    if after[1][k]==v:continue
    if v==Counter({'failed':1}) and after[1][k]==Counter({'passed':1}):fixed.append(k)
    else:regressed.append((k,dict(v),dict(after[1][k])))
assert not regressed,regressed
assert len(fixed)==1 and fixed[0][1]=='test_one_time_weapon_stow_no_restore_retained',fixed
added=set(after[1])-set(before[1])
assert len(added)==39 and all(after[1][k]==Counter({'passed':1}) for k in added)
assert before[2].get('error',0)==after[2].get('error',0)==0
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
rb=tests('root-before',B,['tools']);ra=tests('root-after',A,['tools'])
assert rb[0]==ra[0]==1 and rb[1]==ra[1],(rb[2],ra[2])
assert run('hemtt',A,[os.environ['HEMTT'],'check'],120)==0
report={'base':BASE,'focused':focus[2],'S_original':old_s[2],'T_original':old_t[2],
 'addon_before':before[2],'addon_after':after[2],'root_before':rb[2],'root_after':ra[2],
 'new_cases':39,'resolved_original_ids':['H344'],'remaining_original_entries':102,
 'newly_failing':[],'missing_identities':[],'runtime_files_changed':sorted(RUNTIME),
 'changed_existing':sorted(changed),'unchanged_existing':len(original)-len(changed),
 'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
# Commit S and T independently; only publish after the complete checked result exists.
def commit(label):
    git(A,'add',*P[label]['paths'])
    git(A,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',
        'Bounded '+label+(': protect head-provider unconsciousness boundaries' if label=='S' else ': reconcile one-shot weapon preflight contract'))
    return git(A,'rev-parse','HEAD')
sha_s=commit('S')
validation='\n## Complete-checkout validation\n\n'+f'Focused: {focus[2]}. S controls on unchanged Q-R: {old_s[2]}; T controls: {old_t[2]}. Full addon before: {before[2]}; after: {after[2]}. Exactly H344 changes from failing to passing and all 39 new cases pass. No previous identity is missing or newly failing. Both full addon commands still fail overall with four unchanged skips and no collection/setup errors. Whole root before: {rb[2]}; after: {ra[2]}, with identical raw identities/outcomes. HEMTT check returns 0. Only the two documented provider runtime files change. All {len(original)-len(changed)} other existing tracked files retain their SHA256, including every protected snapshot. No live Arma or stable-release approval.\n'
with (A/'docs/audits/2026-09-23-bounded-backlog-T.md').open('a') as f:f.write(validation)
sha_t=commit('T')
assert not git(A,'status','--porcelain')
final=manifest(A)
assert all(final.get(p)==v for p,v in original.items() if p not in changed)
assert set(final)-set(original)=={NEW_S,NEW_T,'docs/audits/2026-09-23-bounded-backlog-S.md','docs/audits/2026-09-23-bounded-backlog-T.md'}
report.update({'S':sha_s,'T':sha_t,'tree':git(A,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(final,indent=2))
git(A,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('S-T cumulative continuation from Q-R. Includes two git patches, tests, logs and exact preservation manifests. Runtime change is provider-consciousness exclusion only. H344 is a test-contract reconciliation. Rebuild for the runtime change. No stable-release approval.\n')
git(A,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
