"""Validate two bounded commits from S-T and publish only an exactly scoped tree."""
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import ast, hashlib, json, os, subprocess, sys, xml.etree.ElementTree as ET

BASE='b937ac3a10ca4d33aa4a1c6f3aef7cb03941e1b4'
BEFORE=Path('/tmp/acme-uv-before');AFTER=Path('/tmp/acme-uv-after')
OUT=Path('/tmp/acme-uv-results');OUT.mkdir(exist_ok=True)
BRANCH='audit/bounded-backlog-uv-validated-20260923'
T='addons/acm_extended/tools/'
RUNTIME='addons/acm_extended/functions/fn_headElevateCancelSeq.sqf'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
U=T+'test_bounded_head_cancel_generation.py';V=T+'test_bounded_tag_line_layout.py'
DOC_U='docs/audits/2026-09-23-bounded-backlog-U.md'
DOC_V='docs/audits/2026-09-23-bounded-backlog-V.md'
EDITS=[
 ('H241',T+'test_b60_dynamic_syringe_body_tandem.py','test_preparation_has_optional_none_tag_and_three_invisible_editors','    from test_bounded_tag_line_layout import pending_contract\n    pending_contract()'),
 ('H375',T+'test_b75_direct_pressure_tag_flush.py','test_tag_edit_boxes_are_tall_enough_for_ascenders_and_descenders','    from test_bounded_tag_line_layout import layout_contract\n    layout_contract()'),
 ('H378',T+'test_b76_carousel_push_memory.py','test_tag_25','    from test_bounded_tag_contracts import tag_limits\n    from test_bounded_tag_line_layout import layout_contract\n    tag_limits()\n    layout_contract()'),
]
SELECTED=[p+'::'+n for _,p,n,_ in EDITS]
NEW={U:('head_cancel.txt','e605648ffe04586a80ec3b4ab365d1e2efcfc3c4c7ba64a545b0f861fd9ceb72'),V:('tag_layout.txt','d1f585979f056b4d513d0b697ded68f58e9b2707fca669e82ae1c25dc0836a9b')}
STAGED={}
for dest,(name,digest) in NEW.items():
    data=Path('.audit/uv',name).read_bytes()
    assert hashlib.sha256(data).hexdigest()==digest,('staged bytes changed',name)
    compile(data,dest,'exec');STAGED[dest]=data


def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=60)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()


def manifest(root):
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files','-z').split('\0') if p}


def run(name,root,args,timeout=450):
    with (OUT/(name+'.log')).open('w') as f:
        r=subprocess.run(args,cwd=root,text=True,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
    print(name,'exit',r.returncode,(OUT/(name+'.log')).read_text()[-1800:],flush=True)
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
    return rc,data,dict(counts)


def replace_once(path,old,new):
    p=AFTER/path;s=p.read_text();assert s.count(old)==1,(path,old)
    p.write_text(s.replace(old,new))


def commit(paths,message):
    git(AFTER,'add',*paths)
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',message)
    assert not git(AFTER,'status','--porcelain')
    return git(AFTER,'rev-parse','HEAD')


git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original=manifest(BEFORE);(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
assert tests('selected-before',BEFORE,SELECTED)[2]=={'failed':3}
for dest,data in STAGED.items():(BEFORE/dest).write_bytes(data)
uold=tests('U-original-runtime',BEFORE,[U]);vold=tests('V-original-runtime',BEFORE,[V])
assert uold[0]==1 and uold[2]=={'failed':20,'passed':2},uold[2]
assert vold[0]==0 and vold[2]=={'passed':24},vold[2]
for dest in STAGED:(BEFORE/dest).unlink()
assert not git(BEFORE,'status','--porcelain')

# U: never reset the active controller's counter to a reusable sentinel.
(AFTER/U).write_bytes(STAGED[U])
replace_once(RUNTIME,'_medic setVariable ["ACME_headElev_medicAnimToken", -1, false];',
    '// Advance the existing generation; resetting it would let a later restart reuse an old PFH token.\n'
    'private _cancelToken = (_medic getVariable ["ACME_headElev_medicAnimToken", 0]) + 1;\n'
    '_medic setVariable ["ACME_headElev_medicAnimToken", _cancelToken, false];')
replace_once(RUNTIME,'params ["_m"];','params ["_m", "_cancelToken"];')
replace_once(RUNTIME,'        if (_m getVariable ["ACME_headElev_seqActive", false]) exitWith {};',
    '        if ((_m getVariable ["ACME_headElev_medicAnimToken", -1]) != _cancelToken) exitWith {};\n'
    '        if (_m getVariable ["ACME_headElev_seqActive", false]) exitWith {};')
replace_once(RUNTIME,'}, [_medic], 0.25] call CBA_fnc_waitAndExecute;','}, [_medic, _cancelToken], 0.25] call CBA_fnc_waitAndExecute;')
u_paths=[U,T+'test_bounded_head_provider_consciousness.py',T+'test_bounded_head_provider_sequence.py',T+'test_bounded_head_weapon_contract.py']
u=tests('batch-U',AFTER,u_paths);assert u[0]==0 and u[2]=={'passed':80},u[2]
(AFTER/DOC_U).write_text('''# Bounded U: repeated provider cancellation generations

Parent: `b937ac3a10ca4d33aa4a1c6f3aef7cb03941e1b4` (S-T).

The registered headElevateCancelSeq reset medicAnimToken to -1. Each later start therefore reused 0, allowing a still-pending controller from an earlier cancel/restart cycle to match a new sequence. Cancellation now advances the existing counter instead of resetting it. Its delayed AUTO stance release captures and checks that cancellation generation, including when a newer sequence has already finished or been cancelled before delivery.

Only headElevateCancelSeq changes runtime. No new counter, state key, timer, PFH, network operation, animation, delay or patient/gear rule is added. The exact unarmed crouch, 0.25-second release, direct-pressure pause cleanup, duplicate-cancel no-op, and provider consciousness/locality/vehicle guards remain. The patient is not excluded because they are dead. No original H-index entry is closed by U.

Twenty-two full-source execution cases reproduce 20 failures and two passing controls on S-T. All 22 pass with the correction; the 80-test U selection includes the existing provider choreography, unconsciousness and weapon-preflight tests. Pending CBA handles are distinct fixtures. Tests cover both modes, four old-controller stages, repeated cancellation, negative/positive starting counters, delayed releases after another completion or cancellation, intact patient placement, and preserved current cleanup.

This does not certify live CBA scheduling, input, animation, multiplayer ownership migration, counter precision exhaustion, full-heal resets or calls to the unregistered legacy headElevCancelSeq file. It prevents generation reuse through the reviewed registered cancel path, not arbitrary external resets or all cross-controller races. Movement/menu cancellation remains open. No live Arma or stable-release approval.
''')
sha_u=commit([RUNTIME,U,DOC_U],'Bounded U preserve head-provider generation across cancellation')

# V: change only the three reviewed historical test bodies.
(AFTER/V).write_bytes(STAGED[V])
for ident,path,name,body in EDITS:
    p=AFTER/path;s=p.read_text();tree=ast.parse(s)
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
    lines=s.splitlines(keepends=True);lines[node.body[0].lineno-1:node.end_lineno]=[body+'\n'];p.write_text(''.join(lines))
    def normalized(text):
        tree=ast.parse(text)
        found=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name]
        assert len(found)==1
        found[0].body=[ast.Pass()]
        return ast.dump(tree,include_attributes=False)
    assert normalized(s)==normalized(p.read_text()),path
old_ledger=(BEFORE/LEDGER).read_text();entries={l.split()[0]:l for l in old_ledger.splitlines() if l.startswith('H')}
assert len(entries)==102 and all(i in entries for i,_,_,_ in EDITS)
resolved={i for i,_,_,_ in EDITS}
lines=old_ledger.splitlines();lines[0]='Unresolved original source-contract outcomes after bounded V: 99';lines[1]='Base: '+BASE
(AFTER/LEDGER).write_text('\n'.join(l for l in lines if not (l.startswith('H') and l.split()[0] in resolved))+'\n')
remaining={l.split()[0]:l for l in (AFTER/LEDGER).read_text().splitlines() if l.startswith('H')}
assert len(remaining)==99 and remaining=={k:v for k,v in entries.items() if k not in resolved}
focused=tests('focused',AFTER,SELECTED+u_paths+[V,T+'test_bounded_tag_contracts.py',T+'test_bounded_tag_dropdowns.py','tools/test_self_audit_20260922.py'])
assert focused[0]==0 and set(focused[2])=={'passed'},focused[2]
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'addon-before',BEFORE,[T]);b=pool.submit(tests,'addon-after',AFTER,[T])
    before=a.result();after=b.result()
assert before[0]==after[0]==1
fixed=[];regressed=[]
assert set(before[1]).issubset(after[1])
for k,v in before[1].items():
    if v==after[1][k]:continue
    if v==Counter({'failed':1}) and after[1][k]==Counter({'passed':1}):fixed.append(k)
    else:regressed.append((k,dict(v),dict(after[1][k])))
assert not regressed,regressed
assert len(fixed)==3 and {k[1] for k in fixed}=={n for _,_,n,_ in EDITS},fixed
added=set(after[1])-set(before[1])
assert len(added)==46 and all(after[1][k]==Counter({'passed':1}) for k in added)
assert before[2].get('error',0)==after[2].get('error',0)==0
assert before[2].get('skipped',0)==after[2].get('skipped',0)==4
with ThreadPoolExecutor(max_workers=2) as pool:
    a=pool.submit(tests,'root-before',BEFORE,['tools']);b=pool.submit(tests,'root-after',AFTER,['tools'])
    root_before=a.result();root_after=b.result()
assert root_before[1]==root_after[1]
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],120)==0
current=manifest(AFTER)
changed={p for p in original if current.get(p)!=original[p]}
allowed={RUNTIME,LEDGER}|{p for _,p,_,_ in EDITS}
assert changed==allowed,changed
assert all(current[p]==digest for p,digest in original.items() if p not in allowed)
report={'base':BASE,'U':sha_u,'focused':focused[2],'U_original':uold[2],'V_original':vold[2],
 'addon_before':before[2],'addon_after':after[2],'root_before':root_before[2],'root_after':root_after[2],
 'resolved_original_ids':sorted(resolved),'remaining_original_entries':99,'new_cases':46,
 'newly_failing':[],'missing_previous':[],'runtime_files_changed':[RUNTIME],
 'changed_existing':sorted(changed),'unchanged_existing':len(original)-len(changed),
 'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
(AFTER/DOC_V).write_text('''# Bounded V: current tag-line layout and optional-editor contracts

Builds on U from S-T. No runtime, configuration, font or asset change in V.

H241, H375 and H378 retain their original pytest identities. H241 now follows the pending selector and three editor registrations in skPendingTagEnsure rather than demanding the retired Tag: None caption in skInject. H375 and H378 verify the current 0.038-height editor rectangles, 0.031 font scale, native-barrel-relative placement and three 25-character lines. They no longer demand retired 0.030/0.024 or 0.0185 sizing or duplicate old geometry inside skCarouselMove, which delegates to the renderer.

Twenty-four new cases pass on unchanged rendering runtime. The actual pending/stored editor loops run with numeric control-command fixtures at three positive rectangle sizes, tag present/absent, stored edit-mode exclusion, and focused pending fields. Mutation controls reject old height/font/length values and missing third-editor registration despite comment decoys. Existing writer, identity, optional None, dropdown and preservation tests remain in the focused selection. All other historical test bodies and H entries remain unchanged. The original index moves 102 to 99; no skip/xfail is added.

These checks record geometry, text, visibility and input-enable requests, not pixels, glyph fitting, font availability, Unicode graphemes, live focus or whole-dialog lifetimes. Their passing does not prove that every long tag fits visually. No live Arma or stable-release approval.

## Complete-checkout validation

'''+f'Focused: {focused[2]}. U original: {uold[2]}; V original: {vold[2]}. Full addon before: {before[2]}; after: {after[2]}. Exactly three retained historical identities now pass and all 46 new cases pass. No prior identity is missing or newly failing. Both addon commands still fail overall with four unchanged skips and no collection/setup errors. Root before: {root_before[2]}; after: {root_after[2]}, with identical raw identities/outcomes. HEMTT check returns 0. Only the documented cancellation-generation runtime file changes; {len(original)-len(changed)} other existing tracked files retain their SHA256, including every protected snapshot. No live Arma or stable-release approval.\n')
sha_v=commit([V,DOC_V,LEDGER,*[p for _,p,_,_ in EDITS]],'Bounded V reconcile current tag-line layout contracts')
final=manifest(AFTER)
assert set(final)-set(original)=={U,V,DOC_U,DOC_V}
assert set(original).issubset(final)
report.update({'V':sha_v,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2));(OUT/'final-manifest.json').write_text(json.dumps(final,indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('Bounded U-V on S-T. One registered cancellation runtime function changes. Includes exact git patches, logs, JUnit and full-file preservation manifests. Rebuild for gameplay testing. No stable-release approval.\n')
git(AFTER,'push','origin','HEAD:refs/heads/'+BRANCH)
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
