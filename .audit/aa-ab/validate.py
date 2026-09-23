"""Validate two targeted provider fixes; never modify main or merge audit scaffolding."""
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import ast, hashlib, json, os, subprocess, sys, xml.etree.ElementTree as ET
BASE='436075c2c93d6f808993f6ad24e55e0328a617dd'
STAGE=Path('.audit/aa-ab').resolve()
BEFORE=Path('/tmp/acme-aa-ab-before'); AFTER=Path('/tmp/acme-aa-ab-after')
OUT=Path('/tmp/acme-aa-ab-results');OUT.mkdir(exist_ok=True)
BRANCH='audit/bounded-backlog-aa-ab-validated-20260923'
T='addons/acm_extended/tools/'
SOURCE='addons/acm_extended/functions/fn_headElevMedicSeq.sqf'
FIXTURE=T+'test_bounded_head_provider_sequence.py'
HIST=T+'test_b71_tag_head_intubation.py'
HNAME='test_provider_sequence_releases_on_finish_movement_or_menu_exit_without_lowering_head'
SELECTED=HIST+'::'+HNAME
NEWAA=T+'test_bounded_head_movement_menu.py';NEWAB=T+'test_bounded_head_locality_retirement.py'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
DOC_AA='docs/audits/2026-09-23-bounded-backlog-AA.md'
DOC_AB='docs/audits/2026-09-23-bounded-backlog-AB.md'


def git(root,*args):
    r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True,timeout=60)
    assert r.returncode==0,(args,r.stdout,r.stderr)
    return r.stdout.strip()


def digest(root,p):return hashlib.sha256((root/p).read_bytes()).hexdigest()


def replace(path,old,new):
    s=(AFTER/path).read_text();assert s.count(old)==1,path
    (AFTER/path).write_text(s.replace(old,new))


def tests(name,root,paths,extra=()):
    xml=OUT/(name+'.xml')
    with (OUT/(name+'.log')).open('w') as out:
        r=subprocess.run([sys.executable,'-m','pytest',*paths,*extra,'-q','--tb=short','--continue-on-collection-errors','--junitxml='+str(xml)],cwd=root,stdout=out,stderr=subprocess.STDOUT,timeout=450)
    data={}
    for c in ET.parse(xml).iter('testcase'):
        status='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        data.setdefault((c.get('classname',''),c.get('name','')),Counter())[status]+=1
    counts=Counter()
    for v in data.values():counts.update(v)
    print(name,r.returncode,dict(counts),flush=True)
    return r.returncode,data,dict(counts)


def commit(paths,message):
    git(AFTER,'add',*paths)
    git(AFTER,'-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',message)
    assert not git(AFTER,'status','--porcelain')
    return git(AFTER,'rev-parse','HEAD')


def ast_preserved(path,edited_function):
    def normalized(root):
        tree=ast.parse((root/path).read_text());found=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.FunctionDef) and n.name==edited_function:found.append(n);n.body=[ast.Pass()]
        assert len(found)==1
        return ast.dump(tree,include_attributes=False)
    assert normalized(BEFORE)==normalized(AFTER),path


git(Path('.'),'fetch','--depth=1','origin',BASE)
for root in (BEFORE,AFTER):git(Path('.'),'worktree','add','--detach',str(root),BASE)
original={p:digest(BEFORE,p) for p in git(BEFORE,'ls-files','-z').split('\0') if p}
(OUT/'baseline-manifest.json').write_text(json.dumps(original,indent=2))
original_source=(BEFORE/SOURCE).read_text()
assert tests('historical-before',BEFORE,[SELECTED])[2]=={'failed':1}
# Extend only the engine-boundary fixture, not any existing assertion.
replace(FIXTURE,"    return r'''\n        private _local=true;", "    s=s.replace('hasInterface', '_interfacePresent').replace('inputAction _x', '(_input getVariable [_x,0])')\n    return r'''\n        private _interfacePresent=true; private _input=missionNamespace;\n        private _local=true;")
assert digest(AFTER,FIXTURE)=='080ae470510afa754a1909cc11da94d4f6274b35dc0e6753eaaae84a24e9d126'
for staged,target in [('movement.py',NEWAA),('locality.py',NEWAB)]:
    text=(STAGE/staged).read_text();compile(text,target,'exec');(AFTER/target).write_text(text)
aa_original=tests('AA-original-runtime',AFTER,[NEWAA],['-k','not contract_rejects'])
ab_original=tests('AB-original-runtime',AFTER,[NEWAB])
assert aa_original[2]=={'failed':32,'passed':8}
assert ab_original[2]=={'failed':8,'passed':2}
for n in ['AA-original-runtime','AB-original-runtime']:
    log=(OUT/(n+'.log')).read_text();assert '[ERR]' not in log and '[FAT]' not in log
ab_text=(AFTER/NEWAB).read_text();(AFTER/NEWAB).unlink()
# AA: captured medical display and owner-only remappable movement input.
old='private _prepUntil = CBA_missionTime + ((_prepDelay max 0) max 0.05);\n'
replace(SOURCE,old,old+'''
// Bind cancellation only to this local player's input and the menu present at entry.
// Chest-minigame exits also call this controller without a medical menu; do not make
// those menu-less sequences depend on a later, unrelated display.
disableSerialization;
private _menu = displayNull;
if (hasInterface && {!isNil "ACE_player"} && {_medic isEqualTo ACE_player}) then {
    _menu = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
};
private _watchMenu = !isNull _menu;
''')
replace(SOURCE,'"_stageAt", "_prepUntil"];','"_stageAt", "_prepUntil", "_menu", "_watchMenu"];\n    disableSerialization;')
replace(SOURCE,'    private _now = CBA_missionTime;','''    // Check token/life/locality above before cancellation can retire any controller.
    // Input from the player must never cancel another locally owned (AI) provider.
    private _cancel = false;
    if (hasInterface && {!isNil "ACE_player"} && {_u isEqualTo ACE_player}) then {
        _cancel = ["MoveForward", "MoveBack", "TurnLeft", "TurnRight", "MoveLeft", "MoveRight", "MoveFastForward", "MoveSlowForward"] findIf {
            (inputAction _x) > 0.05
        } >= 0;
        if (_watchMenu && {isNull _menu || {!(_menu isEqualTo (uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull]))}}) then {
            _cancel = true;
        };
    };
    if (_cancel) exitWith {
        call ACME_fnc_headElevateCancelSeq;
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };

    private _now = CBA_missionTime;''')
replace(SOURCE,'CBA_missionTime, _prepUntil]] call CBA_fnc_addPerFrameHandler;','CBA_missionTime, _prepUntil, _menu, _watchMenu]] call CBA_fnc_addPerFrameHandler;')
s=(AFTER/HIST).read_text();a=s.index('def '+HNAME+'():');b=s.index('\ndef ',a+5)
s=s[:a]+'def '+HNAME+'():\n    from test_bounded_head_movement_menu import movement_menu_contract\n    movement_menu_contract()\n\n'+s[b:];(AFTER/HIST).write_text(s)
ast_preserved(HIST,HNAME);ast_preserved(FIXTURE,'setup')
ledger=(AFTER/LEDGER).read_text();assert ledger.count('\nH343 ')==1
remaining='\n'.join(l for l in ledger.split('\n') if not l.startswith('H343 '))
remaining=remaining.replace('after bounded Z: 77','after bounded AA: 76').replace('Base: 40efb4b6871844dd30aea56da96096b336ba9d23','Base: '+BASE)
(AFTER/LEDGER).write_text(remaining)
adjacent=[FIXTURE,T+'test_bounded_head_provider_consciousness.py',T+'test_bounded_head_cancel_generation.py',T+'test_bounded_head_weapon_contract.py']
aa=tests('AA-focused',AFTER,[NEWAA,SELECTED,*adjacent]);assert aa[0]==0 and aa[2]=={'passed':125}
(AFTER/DOC_AA).write_text('''# Bounded AA: provider movement and originating-menu cancellation

Parent: `436075c2c93d6f808993f6ad24e55e0328a617dd` (Y-Z).

The head-position provider controller had no movement or medical-menu closure check. Its existing registered cancel routine was not called by this controller on either boundary. The existing PFH now checks eight remappable movement actions for its current local player only, and cancellation when the medical display captured at entry closes or is replaced. No menu present at entry means no menu binding, preserving menu-less chest-minigame exits and ignoring later unrelated menus. It checks the current animation token, life, consciousness and locality before considering input cancellation.

Cancellation uses the existing registered routine, preserves its exact unarmed crouch and 0.25-second stance release, and removes this PFH. It does not lower the casualty or write the casualty placement token. No new timer, event handler, state key, network operation, animation name, timing, medication or equipment algorithm is introduced. One existing shared test setup gains explicit hasInterface/inputAction fixtures; no existing assertion is weakened there.

H343 retains its historical function identity and now checks the executable owner/menu/movement contract rather than retired helper names. The original ledger moves 77 to 76, with every unreviewed H line verbatim. The actual full-controller tests cover both modes, four stages, eight input actions, closed/replaced menus, idle and threshold controls, AI/headless isolation, no-menu origins and superseded tokens. Unchanged runtime: 32 failing and 8 passing execution cases. Four new mutation controls reject lost guards even with comment decoys. Candidate AA selection: 125 pass.

Input/control/scheduler/network commands are explicit fixtures. This does not certify key propagation inside live dialogs, full patient animation/gear teardown, provider movement while a physical roll is still in progress, actual rendered blending, owner-away-and-back token reuse, post-wake recovery or cross-controller takeover. No physical displacement fallback is added. Real movement behavior and menu timing need locally hosted and dedicated-server testing. Remappable action names follow Bohemia's inputAction/actions reference: https://community.bistudio.com/wiki/inputAction/actions . No stable-release approval.
''')
sha_aa=commit([SOURCE,FIXTURE,HIST,NEWAA,LEDGER,DOC_AA],'Bounded AA: cancel provider theatre on movement or originating-menu exit')
# AB: a former owner may retire its local PFH but not mutate provider state.
replace(SOURCE,'        if (isNull _u) exitWith {};\n        // A newer provider sequence','        // Local PFH retirement is always safe; provider cleanup belongs only to its current owner.\n        if (isNull _u || {!local _u}) exitWith {};\n        // A newer provider sequence')
assert digest(AFTER,SOURCE)=='f9025fa419cb916e183906537625e09c65677b8097609aeebd2aeeff09ab8589'
(AFTER/NEWAB).write_text(ab_text)
focused=tests('focused',AFTER,[NEWAA,NEWAB,SELECTED,*adjacent]);assert focused[0]==0 and focused[2]=={'passed':135}
with ThreadPoolExecutor(max_workers=2) as pool:
    l=pool.submit(tests,'addon-before',BEFORE,[T]);r=pool.submit(tests,'addon-after',AFTER,[T])
    before=l.result();after=r.result()
assert before[0]==after[0]==1
assert before[2]=={'passed':4415,'failed':105,'skipped':4},before[2]
assert after[2]=={'passed':4470,'failed':104,'skipped':4},after[2]
missing=set(before[1])-set(after[1]);assert not missing,missing
fixed=[]
for k,v in before[1].items():
    if after[1][k]==v:continue
    assert k[1]==HNAME and v==Counter({'failed':1}) and after[1][k]==Counter({'passed':1}),(k,v,after[1][k])
    fixed.append(k)
assert len(fixed)==1
added=set(after[1])-set(before[1]);assert len(added)==54 and all(after[1][k]==Counter({'passed':1}) for k in added)
with ThreadPoolExecutor(max_workers=2) as pool:
    l=pool.submit(tests,'root-before',BEFORE,['tools']);r=pool.submit(tests,'root-after',AFTER,['tools'])
    rb=l.result();ra=r.result()
assert rb[0]==ra[0]==1 and rb[1]==ra[1]
with (OUT/'hemtt.log').open('w') as log:
    check=subprocess.run([os.environ['HEMTT'],'check'],cwd=AFTER,stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert check.returncode==0
changed={p for p in original if digest(AFTER,p)!=original[p]}
assert changed=={SOURCE,FIXTURE,HIST,LEDGER},changed
before_ids={l for l in ledger.splitlines() if l.startswith('H')}
after_ids={l for l in (AFTER/LEDGER).read_text().splitlines() if l.startswith('H')}
assert len(after_ids)==76 and len(before_ids-after_ids)==1 and not after_ids-before_ids
assert all(l.startswith('H343 ') for l in before_ids-after_ids)
report={'base':BASE,'AA':sha_aa,'AA_original':aa_original[2],'AB_original':ab_original[2],'focused':focused[2],'addon_before':before[2],'addon_after':after[2],'root_before':rb[2],'root_after':ra[2],'resolved_original_ids':['H343'],'remaining_original_entries':76,'new_passing_cases':54,'missing_previous':[],'newly_failing':[],'runtime_files_changed':[SOURCE],'changed_existing':sorted(changed),'unchanged_existing_files':len(original)-len(changed),'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False}
(AFTER/DOC_AB).write_text('''# Bounded AB: former-owner provider cleanup

Builds on bounded AA. The existing controller called its finalizer when provider locality was lost, but that finalizer only checked nullness and token before clearing active/mode/stage, resuming a head-owned DP pause, incrementing a pin token and broadcasting animation speed. It now retires the local PFH first and checks locality before any provider cleanup. A still-local invalid provider retains existing cleanup. Only headElevMedicSeq changes runtime; no new timer/state/network operation or patient rule.

Ten full-source execution cases use explicit locality/animation/network fixtures: 8 fail and 2 pass on original Y-Z runtime, all pass after correction. They cover both modes, all four provider stages, global-event suppression, provider flags/tokens and DP pause preservation, plus still-local unconscious retirement. This does not migrate the controller, clear stale private state on the former owner, establish new-owner recovery, or handle locality away and back between ticks. Those remain open. No live Arma or stable-release approval.

## Complete-checkout verification

'''+json.dumps(report,indent=2)+'\n\nThe full addon and root suites remain failing overall. No new skip or xfail was added. The input/locality fixtures record requests, not live UI, RTM, PhysX, multiplayer scheduling or gear behavior. All protected snapshots remain unchanged.\n')
sha_ab=commit([SOURCE,NEWAB,DOC_AB],'Bounded AB: retire former-owner provider PFH without cleanup writes')
report.update({'AB':sha_ab,'tree':git(AFTER,'rev-parse','HEAD^{tree}'),'branch':BRANCH})
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final-manifest.json').write_text(json.dumps({p:digest(AFTER,p) for p in git(AFTER,'ls-files','-z').split('\0') if p},indent=2))
git(AFTER,'format-patch','--output-directory',str(OUT),BASE+'..HEAD')
(OUT/'README.txt').write_text('AA-AB source patches and complete before/after evidence. Rebuild needed for provider cancellation/locality corrections. No live Arma or stable release approval.\n')
git(AFTER,'push','origin','HEAD:refs/heads/'+BRANCH)
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
