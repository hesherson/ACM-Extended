"""Validate two scoped batches against an exact complete checkout before publishing."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import ast, hashlib, json, os, shutil, subprocess, sys
import xml.etree.ElementTree as ET

BASE='dd294e53c7fb850c31dde42454adbbd92c4e1bb3'
BRANCH='audit/bounded-backlog-ag-ah-validated-20260923'
STAGE=Path(__file__).resolve().parent
OUT=Path('/tmp/acme-ag-ah-results'); OUT.mkdir(exist_ok=True)
BEFORE=Path('/tmp/acme-ag-ah-before'); AFTER=Path('/tmp/acme-ag-ah-after')
T='addons/acm_extended/tools/'
RUNTIME='addons/acm_extended/functions/fn_skConfirmInjection.sqf'
FIXTURE=T+'test_bounded_normal_push_lifetime.py'
NEW_G=T+'test_bounded_push_workspace_generation.py'
NEW_H=T+'test_bounded_draw_endpoints.py'
OLD_G=T+'test_b70_semifowler_bvm_thora_syringe.py'
OLD_H=T+'test_b73_syringe_tag_vial_carousel_anim.py'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
DOC_G='docs/audits/2026-09-23-bounded-backlog-AG.md'
DOC_H='docs/audits/2026-09-23-bounded-backlog-AH.md'
SELECTED=[OLD_G+'::test_syringe_can_return_last_hundredth_to_exact_endpoint',OLD_H+'::test_plain_draw_snaps_final_hundredth_to_hard_max']
FOCUSED=[NEW_G,NEW_H,FIXTURE,T+'test_bounded_narc_close_generation.py',T+'test_bounded_site_click_handoff.py',T+'test_bounded_staged_push_contracts.py',T+'test_infusion_syringe_vial_clamp_hotfix_20260920.py',*SELECTED]
EXPECTED={
 NEW_G:'75434a2483b75a09661722ea744d73f07590ea45fcb8d608ea28a1e83a4b27bd',
 NEW_H:'817b96111da13ec9475c75aaf65cabf825fc979005a453b467ee28e0a90017b7',
 RUNTIME:'fa40684ea5eeb60a876d1da88af099a8711e77c10137df773831b2656966c494',
 FIXTURE:'cb0c457a8c11cc27cc2e26b870889e149ced4008daedd233aee60178f4dc77af',
 OLD_G:'e274938176e5a9fddec3c0ae97632c27e2f98e3c3d7c928076433f1bb5c8c436',
 OLD_H:'ea9f93bd3950bcce3f6e30c822c03c948ccc17b9a8d3d218295bd3a8b963e23c'}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=60)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()

def manifest(root):return {p:digest(root/p) for p in git(root,'ls-files','-z').split('\0') if p}

def run(name,root,args,timeout=440):
    with (OUT/(name+'.log')).open('w') as stream:
        r=subprocess.run(args,cwd=root,stdout=stream,stderr=subprocess.STDOUT,text=True,timeout=timeout)
    print(name,'exit',r.returncode,flush=True)
    return r.returncode

def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=short','--continue-on-collection-errors','--junitxml='+str(xml)])
    data={}
    for c in ET.parse(xml).iter('testcase'):
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        key=(c.get('classname',''),c.get('name',''))
        data.setdefault(key,Counter())[status]+=1
    counts=Counter()
    for v in data.values():counts.update(v)
    print(name,dict(counts),flush=True)
    return rc,data,dict(counts)

def entries(root):return {l.split()[0]:l for l in (root/LEDGER).read_text().splitlines() if l.startswith('H')}

def commit(paths,message):
    git(AFTER,'add',*paths)
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',message)
    return git(AFTER,'rev-parse','HEAD')

# Fail before toolchain or suite time is spent if transport altered reviewed bytes.
assert digest(STAGE/'reviewed.patch')=='7e05bb3297bfebc0645c438ff5cbfad7660077e99e92b5ea88e3dd6f52704b98'
for src,dest in [('workspace.py',NEW_G),('endpoints.py',NEW_H)]:
    assert digest(STAGE/src)==EXPECTED[dest],src
    compile((STAGE/src).read_text(),src,'exec')
git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE)
(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert len(entries(BEFORE))==72
assert tests('historical-before',BEFORE,SELECTED)[2]=={'failed':2}
for root in (BEFORE,AFTER):
    for src,dest in [('workspace.py',NEW_G),('endpoints.py',NEW_H)]:shutil.copyfile(STAGE/src,root/dest)
g=tests('AG-original-runtime',BEFORE,[NEW_G]);h=tests('AH-original-runtime',BEFORE,[NEW_H])
assert g[2]=={'failed':11,'passed':8} and h[2]=={'passed':35},(g[2],h[2])
for p in (NEW_G,NEW_H):(BEFORE/p).unlink()
git(AFTER,'apply','--check',str(STAGE/'reviewed.patch'))
git(AFTER,'apply',str(STAGE/'reviewed.patch'))
for p,hsh in EXPECTED.items():assert digest(AFTER/p)==hsh,p
# Preserve every unreviewed historical body, not just the list of pytest names.
for p,name in [(OLD_G,SELECTED[0].rsplit('::',1)[1]),(OLD_H,SELECTED[1].rsplit('::',1)[1])]:
    def normalized(root):
        tree=ast.parse((root/p).read_text());seen=0
        for node in ast.walk(tree):
            if isinstance(node,ast.FunctionDef) and node.name==name:node.body=[ast.Pass()];seen+=1
        assert seen==1
        return ast.dump(tree,include_attributes=False)
    assert normalized(BEFORE)==normalized(AFTER),p
focused=tests('focused',AFTER,FOCUSED)
assert focused[0]==0 and focused[2]=={'passed':150},focused[2]
with ThreadPoolExecutor(max_workers=2) as pool:
    b=pool.submit(tests,'addon-before',BEFORE,[T]);a=pool.submit(tests,'addon-after',AFTER,[T])
    before=b.result();after=a.result()
assert before[0]==after[0]==1
assert set(before[1]).issubset(after[1]),'prior test identity missing'
fixed=[]
for k,v in before[1].items():
    if v==after[1][k]:continue
    assert v==Counter({'failed':1}) and after[1][k]==Counter({'passed':1}),(k,v,after[1][k])
    fixed.append(k)
assert len(fixed)==2 and {k[1] for k in fixed}=={p.rsplit('::',1)[1] for p in SELECTED}
added=set(after[1])-set(before[1])
assert len(added)==54 and all(after[1][k]==Counter({'passed':1}) for k in added)
assert before[2].get('error',0)==after[2].get('error',0)==0
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
with ThreadPoolExecutor(max_workers=2) as pool:
    b=pool.submit(tests,'root-before',BEFORE,['tools']);a=pool.submit(tests,'root-after',AFTER,['tools'])
    root_before=b.result();root_after=a.result()
assert root_before[0]==root_after[0]==1 and root_before[1]==root_after[1]
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
# Close only the two reviewed H entries; every remaining entry stays verbatim.
old=(AFTER/LEDGER).read_text()
lines=old.splitlines(keepends=True)
lines=[l for l in lines if not l.startswith(('H334 ','H363 '))]
lines[0]='Unresolved original source-contract outcomes after bounded AH: 70\n'
lines[1]='Base: '+BASE+'\n'
(AFTER/LEDGER).write_text(''.join(lines))
assert set(entries(BEFORE))-set(entries(AFTER))=={'H334','H363'}
assert len(entries(AFTER))==70
assert all(v==entries(AFTER)[k] for k,v in entries(BEFORE).items() if k not in ('H334','H363'))
current=manifest(AFTER)
changed={p for p,hsh in original.items() if current.get(p)!=hsh}
assert changed=={RUNTIME,FIXTURE,OLD_G,OLD_H,LEDGER},changed
report={'base':BASE,'AG_original_runtime':g[2],'AH_original_runtime':h[2],'focused':focused[2],
        'addon_before':before[2],'addon_after':after[2],'root_before':root_before[2],'root_after':root_after[2],
        'resolved_original_ids':['H334','H363'],'remaining_original_entries':70,'new_passing_cases':54,
        'newly_failing':[],'missing_previous':[],'runtime_files_changed':[RUNTIME],
        'changed_existing':sorted(changed),'unchanged_existing_files':len(original)-len(changed),
        'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
(AFTER/DOC_G).write_text('''# Bounded AG: normal-push retirement retains workspace ownership

Parent: `'''+BASE+'''` (AE-AF).

The normal-push job guard prevented an old callback from touching a newer normal push, but not a newer injected workspace before that workspace had a replacement job. Its retirement could clear a later target and shared locks. Reinitialization using the same display handle could also pass the old context test.

Only skConfirmInjection changes runtime. It captures the existing injected-display CloseEpoch in its existing job record. Normal entry, deferred context validation and shared cleanup now require that workspace generation. Retirement still removes the matching obsolete job record, but does not unlock or clear another workspace/provider. The plunger retains its existing own-handle retirement. Existing current-session cancellation, exact handoff, normal timing and persistent Hardcore delegation remain. No new state key, counter, timer, PFH, network operation, dose algorithm or inventory transaction is introduced.

Nineteen actual confirmation/registration/Unload execution cases produce eleven failures and eight passes on unchanged AE-AF runtime, then all pass on the candidate. Coverage includes a successor without a new push, changed providers, same-display re-registration, delivery after successor close, old-plunger retirement, still-owned cancellation, normal IV/IO/IM handoffs with live/dead casualties, duplicate completion and unowned registration rejection. The prior replacement-display fixture now supplies the registration epoch for its injected display; no assertion is weakened.

The tests record boundary requests rather than live inventory, drug delivery, rendering or scheduling. Arbitrary epoch resets, provider-away-and-back within a generation, same-context page/patient round trips, a replacement created inside an already-running handoff, and changes to syringe contents under an unchanged stable ID remain outside this fix. No original H entry is closed by AG. No live Arma or stable-release approval.
''')
(AFTER/DOC_H).write_text('''# Bounded AH: native draw endpoints and non-competing UI repair

Builds on AG. H334 and H363 retain their original pytest identities. They demanded exact-endpoint writes from the old UI tick. Current native drag owns the zero/vial-ceiling snap; the UI tick supplies stock bounds and delegates staged overage to syringeDrawSetAmount instead of acting as a competing plunger writer. Existing compound-floor assertions are retained.

Thirty-five new checks pass on unchanged native runtime: twenty execute the actual moving block across four syringe sizes and five hand positions; four verify that both volume and pixel proximity are needed before rounding to an endpoint; six exercise the actual UI repair branch at/below/above its tolerance; five reject mutated limits, endpoint values, guards or direct-write regressions despite comment decoys. Same-frame vial-limit lookup, bounded hit-control geometry and the visual plunger offset remain checked.

Engine controls, mouse input, resolution and linearConversion use explicit numeric fixtures. VialSession and stock-repair calls are recorded, not real inventory transactions. The tests verify exact numeric amount endpoints and bounded geometry, not pixel-perfect rendering, glyphs, arbitrary malformed values, live regrab/input scheduling or a full compound-drug transaction. No native draw, UI tick, dose, configuration or asset changes in AH. The ledger moves 72 to 70; every other H entry remains verbatim. No new skip or xfail. No stable-release approval.

## Complete-checkout validation

```json\n'''+json.dumps(report,indent=2)+'''\n```

Both broad suites remain failing overall. Full before/after JUnit retains all previous identities with no new failures. Root identities/outcomes and protected snapshots are unchanged. HEMTT is a source/build check, not a live Arma or release-package acceptance test.
''')
assert run('diff-check',AFTER,['git','diff','--check'],30)==0
sha_g=commit([RUNTIME,FIXTURE,NEW_G,DOC_G],'Bounded AG retain workspace generation during normal push retirement')
sha_h=commit([OLD_G,OLD_H,NEW_H,LEDGER,DOC_H],'Bounded AH reconcile native draw endpoints without a competing UI writer')
assert not git(AFTER,'status','--porcelain')
tracked=set(manifest(AFTER));assert tracked-set(original)=={NEW_G,NEW_H,DOC_G,DOC_H}
assert set(original).issubset(tracked)
assert run('committed-diff-check',AFTER,['git','diff','--check',BASE,'HEAD'],30)==0
report.update({'AG':sha_g,'AH':sha_h,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(manifest(AFTER),indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
shutil.copyfile(STAGE/'reviewed.patch',OUT/'reviewed.patch')
(OUT/'README.txt').write_text('AG-AH is cumulative on AE-AF. AG changes normal push workspace ownership; AH is test-only. Includes separate git patches, complete logs/JUnit and preservation manifests. Rebuild for AG. No live Arma or stable-release approval.\n')
git(AFTER,'push','origin','HEAD:refs/heads/'+BRANCH)
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
