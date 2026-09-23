"""Publish two test-only review commits after complete-checkout verification."""
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import ast, hashlib, json, os, subprocess, sys, xml.etree.ElementTree as ET

BASE='585949bc1bf9047208119474a63f2d474b49f517'
STAGE=Path('.audit/wx').resolve()
BEFORE=Path('/tmp/acme-wx-before');AFTER=Path('/tmp/acme-wx-after')
OUT=Path('/tmp/acme-wx-results');OUT.mkdir(exist_ok=True)
BRANCH='audit/bounded-backlog-wx-validated-20260923'
T='addons/acm_extended/tools/'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
IDS={'W':['H253','H297','H322'],'X':['H256','H270','H298','H316','H323','H337','H346','H347','H360','H376','H383']}
NEW={'W':'test_bounded_selector_lifetime.py','X':'test_bounded_selector_geometry.py'}
HASH={'W':'0154a0a85736746b970741cc334a828d9968a43b84298c17abd1ea888173d236','X':'5544962a2581ab0166f97f2cf199e77389a2e38d6a28f3544a6434aa25264889'}
for k,n in NEW.items():
    raw=(STAGE/n).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==HASH[k], 'Staged test transport differs: '+n
    compile(raw,n,'exec')

def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,capture_output=True,text=True,timeout=60)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()

def manifest(root):
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files','-z').split('\0') if p}

def ledger(root):
    return {l.split()[0]:l.split(' ',1)[1] for l in (root/LEDGER).read_text().splitlines() if l.startswith('H')}

def run(name,root,args,timeout=450):
    with (OUT/(name+'.log')).open('w') as stream:
        r=subprocess.run(args,cwd=root,stdout=stream,stderr=subprocess.STDOUT,text=True,timeout=timeout)
    print(name,'exit',r.returncode,(OUT/(name+'.log')).read_text()[-1200:],flush=True)
    return r.returncode

def tests(name,root,paths):
    xml=OUT/(name+'.xml')
    rc=run(name,root,[sys.executable,'-m','pytest',*paths,'-q','--tb=short','--continue-on-collection-errors','--junitxml='+str(xml)])
    data={};counts=Counter()
    for c in ET.parse(xml).iter('testcase'):
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        key=(c.get('classname',''),c.get('name',''))
        data.setdefault(key,Counter())[status]+=1;counts[status]+=1
    return rc,data,dict(counts)

def commit(paths,label):
    git(AFTER,'add',*paths)
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m','Reconcile pending-selector contracts without runtime changes (bounded '+label+')')
    return git(AFTER,'rev-parse','HEAD')

def update_contracts(label):
    changed=[]
    for id in IDS[label]:
        path,name=ENTRIES[id].rsplit('::',1);p=AFTER/path;s=p.read_text()
        found=[n for n in ast.walk(ast.parse(s)) if isinstance(n,ast.FunctionDef) and n.name==name]
        assert len(found)==1;node=found[0];lines=s.splitlines(keepends=True)
        if label=='W':
            body='    from test_bounded_selector_lifetime import selector_contract\n    selector_contract()\n'
            if id=='H297':body+='    from test_bounded_tag_contracts import require\n    require(txt("functions/fn_skPendingTagRender.sqf"), "private _tagCenterX = _x + _w*0.36;")\n'
        else:
            body='    from test_bounded_selector_geometry import geometry_source_contract\n    geometry_source_contract()\n'
            if id in ['H256','H270','H316','H347']:body+='    from test_bounded_selector_lifetime import selector_contract\n    selector_contract()\n'
        lines[node.lineno-1:node.end_lineno]=['def '+name+'():\n    # Later B78 geometry/readiness supersedes this historical identifier\'s older implementation.\n'+body]
        p.write_text(''.join(lines));changed.append(path)
    (AFTER/T/NEW[label]).write_bytes((STAGE/NEW[label]).read_bytes())
    rest=[l for l in (AFTER/LEDGER).read_text().splitlines() if l.split(' ')[0] not in IDS[label]]
    rest[0]='Unresolved original source-contract outcomes after bounded '+label+': '+str(sum(l.startswith('H') for l in rest))
    rest[1]='Base: '+BASE;(AFTER/LEDGER).write_text('\n'.join(rest)+'\n')
    return sorted(set(changed+[T+NEW[label],LEDGER]))

DOC_W='''# Bounded W: current pending-selector creation and refresh

Parent: `585949bc1bf9047208119474a63f2d474b49f517` (U-V). Test-only changes.

H253, H297 and H322 retain their pytest identities. Their older expectations required retired captions, inline selector creation in skInject, and an earlier left-of-barrel position. Current skOpenDraw enables PendingTagReady only after injection, then calls the idempotent Ensure and Render paths. Artwork and three editors precede the selector, and the dropdown follows it. The current Select Syringe Tag caption, all thirteen purpose/None choices, click-only controls, deferred first repaint and 0.10-second later repaint cadence remain protected.

Twenty-one new cases execute the complete Ensure function or actual Render readiness/page-gating prefix, plus negative token contracts with comment decoys. Cases cover all four syringe sizes with native or captured rectangles, no duplicate creation/registration on repeated calls, exact event targets, no creation before readiness, missing displays, and preparation versus Body Map visibility independent of a stale infusion return. Registered event bodies are not invoked by the creation fixture; prior dropdown/color tests cover their separate behavior.

These cases pass on unchanged U-V runtime. This is not a gameplay change or a rendered-layout proof. Controls, positions, text metrics and event registration are explicit fixtures; live mouse events, late external callbacks and whole-dialog ownership remain unverified. Partial engine control-creation failures and malformed initial cached rectangles are not certified. No runtime/configuration/assets or snapshots change. Index 99 to 96. No tests are removed or skipped; unrelated historical test bodies and H entries remain intact.
'''
DOC_X='''# Bounded X: current native-tag anchor and canvas geometry

Builds on W from U-V. Test-only changes. H256, H270, H298, H316, H323, H337, H346, H347, H360, H376 and H383 retain their original identities.

The later B78 selector uses the native tag-face center (0.36 of barrel width), vertical 0.575 anchor, measured-caption padding and 0.090-0.145 safe-zone-height width limits. Older offsets, fixed widths, global safeZoneW menu sizing and hover-opening requirements are obsolete. Initial/pending selectors retain their two-pixel canvas margins; the stored editor deliberately retains its larger existing gap. The test does not force those edge rules to be identical. Dropdowns use the constrained canvas width and remain below the selector. Click-only registration, None and current caption checks are retained where the historical contract also covered those behaviors.

Sixty new cases execute the actual initial creation path or exact pending/stored selector and dropdown arithmetic blocks, and mutation-check wrong anchors, width caps, bounds and above-selector menus with comment decoys. They cover interior and both horizontal boundaries, several canvas/UI scales, short/long measured captions, and all four barrel sizes using native/captured rectangles. Each expected value is calculated independently of the extracted SQF expressions. New cases pass on unchanged runtime, so these are stale-test reconciliations, not eleven new gameplay fixes.

Numeric fixtures record layout requests, not pixels, text fitting, font availability, accessibility, actual screen clipping or modal lifetimes. Stored geometry is exercised in editing mode, not all ordinary Body Map behavior. Missing or malformed initial cached-rectangle handling and vertical extreme-screen clipping remain outside this review. No runtime/configuration/assets/protected snapshot change. Index 96 to 85; all unreviewed H entries remain verbatim. No skip/xfail introduced. No live Arma or stable-release approval.
'''

git(Path('.'),'fetch','--depth=1','origin',BASE)
for p in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(p),BASE)
original=manifest(BEFORE);ENTRIES=ledger(BEFORE);assert len(ENTRIES)==99
(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
all_ids=IDS['W']+IDS['X'];selected=[ENTRIES[id] for id in all_ids]
assert tests('selected-before',BEFORE,selected)[2]=={'failed':14}
# New cases must pass on unchanged runtime, before editing historical assertions.
for n in NEW.values():(BEFORE/T/n).write_bytes((STAGE/n).read_bytes())
control=tests('new-cases-original-runtime',BEFORE,[T+n for n in NEW.values()])
assert control[0]==0 and control[2]=={'passed':81},control[2]
for n in NEW.values():(BEFORE/T/n).unlink()
paths_w=update_contracts('W');doc_w='docs/audits/2026-09-23-bounded-backlog-W.md'
(AFTER/doc_w).write_text(DOC_W)
w=tests('batch-W',AFTER,[ENTRIES[id] for id in IDS['W']]+[T+NEW['W']]);assert w[0]==0 and w[2]=={'passed':24}
sha_w=commit(paths_w+[doc_w],'W')
paths_x=update_contracts('X')
# Only targeted historical function bodies may change, not other tests or imports.
reviewed={}
for id in all_ids:
    p,n=ENTRIES[id].rsplit('::',1);reviewed.setdefault(p,set()).add(n)
for path,names in reviewed.items():
    shapes=[]
    for root in (BEFORE,AFTER):
        tree=ast.parse((root/path).read_text());found=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.FunctionDef) and node.name in names:
                found.add(node.name);node.body=[ast.Pass()]
        assert found==names;shapes.append(ast.dump(tree,include_attributes=False))
    assert shapes[0]==shapes[1],'Unreviewed test body changed: '+path
assert ledger(AFTER)=={k:v for k,v in ENTRIES.items() if k not in all_ids}
assert len(ledger(AFTER))==85
focus_paths=selected+[T+NEW['W'],T+NEW['X']]+[T+'test_bounded_'+n+'.py' for n in ['tag_dropdowns','tag_color_focus','tag_focus','tag_line_layout']]+['tools/test_self_audit_20260922.py']
focused=tests('focused',AFTER,focus_paths);assert focused[0]==0 and set(focused[2])=={'passed'}
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'addon-before',BEFORE,[T]);b=pool.submit(tests,'addon-after',AFTER,[T]);before=a.result();after=b.result()
assert before[0]==after[0]==1
assert before[2].get('error',0)==after[2].get('error',0)==0
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
assert set(before[1]).issubset(after[1]),'Previous test identity disappeared'
fixed=[]
for key,outcome in before[1].items():
    if outcome==after[1][key]:continue
    assert outcome==Counter({'failed':1}) and after[1][key]==Counter({'passed':1}),(key,outcome,after[1][key])
    fixed.append(key)
assert len(fixed)==14 and {k[1] for k in fixed}=={s.rsplit('::',1)[1] for s in selected},fixed
added=set(after[1])-set(before[1]);assert len(added)==81 and all(after[1][k]==Counter({'passed':1}) for k in added)
root_before=tests('root-before',BEFORE,['tools']);root_after=tests('root-after',AFTER,['tools'])
assert root_before[0]==root_after[0]==1 and root_before[1]==root_after[1]
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
changed={p for p,h in original.items() if hashlib.sha256((AFTER/p).read_bytes()).hexdigest()!=h}
assert changed==set(reviewed)|{LEDGER},changed
report={'base':BASE,'W':sha_w,'original_controls':control[2],'focused':focused[2],
        'addon_before':before[2],'addon_after':after[2],'root_before':root_before[2],'root_after':root_after[2],
        'resolved_original_ids':all_ids,'remaining_original_entries':85,'new_passing_cases':81,
        'fixed_previous_identities':fixed,'missing_previous':[],'newly_failing':[],
        'runtime_files_changed':0,'changed_existing':sorted(changed),'unchanged_existing_files':len(original)-len(changed),
        'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
doc_x='docs/audits/2026-09-23-bounded-backlog-X.md'
validation='\n## Complete-checkout validation\n\n'+f'New cases on unchanged runtime: {control[2]}. Focused: {focused[2]}. Full addon before: {before[2]}; after: {after[2]}. Exactly fourteen retained historical identities now pass and all 81 new cases pass. No prior identity is missing or newly failing. Both addon commands still fail overall with four unchanged skips and zero collection/setup errors. Root before: {root_before[2]}; after: {root_after[2]}, with identical raw identities and outcomes. HEMTT check returns 0. No runtime/configuration/asset/snapshot edits; {len(original)-len(changed)} other existing tracked files retain their complete-checkout SHA256. No live Arma or stable-release approval.\n'
(AFTER/doc_x).write_text(DOC_X+validation)
sha_x=commit(paths_x+[doc_x],'X');assert not git(AFTER,'status','--porcelain')
report.update({'X':sha_x,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps(manifest(AFTER),indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('W-X test-only backlog continuation from U-V. Includes both patches, commands/logs, JUnit and manifests. No gameplay rebuild is necessary for W-X alone. No stable-release approval.\n')
git(AFTER,'push','origin',f'HEAD:refs/heads/{BRANCH}')
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
