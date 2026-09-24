from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import base64, gzip, hashlib, json, os, subprocess, sys, xml.etree.ElementTree as ET

ROOT=Path.cwd()
BASE='8df66dfb5f9701c960bf352ba1f41d16dcd77fc8'
BEFORE=Path('/tmp/acme-amap-before')
AFTER=Path('/tmp/acme-amar-after')
OUT=Path('/tmp/acme-am-ar-results'); OUT.mkdir(exist_ok=True)
T='addons/acm_extended/tools/'
LEDGER='docs/audits/historical-backlog-remaining-20260922.txt'
BRANCH='audit/bounded-backlog-am-ar-validated-20260923'

def cmd(args,cwd=ROOT,timeout=180,check=True):
    r=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    if check and r.returncode: raise RuntimeError(f"{args} -> {r.returncode}\n{r.stdout[-12000:]}")
    return r

def run(name,cwd,args,timeout=180):
    r=cmd(args,cwd,timeout,False)
    (OUT/(name+'.log')).write_text(r.stdout)
    print(name,'exit',r.returncode,r.stdout[-2200:],flush=True)
    return r.returncode

def outcomes(xml):
    d={}
    for c in ET.parse(xml).iter('testcase'):
        k=(c.get('classname',''),c.get('name',''))
        s='error' if c.find('error') is not None else 'failed' if c.find('failure') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
        d[k]=s
    return d

def tests(name,cwd,paths,timeout=240):
    xml=OUT/(name+'.xml')
    rc=run(name,cwd,[sys.executable,'-m','pytest',*paths,'-q','--tb=no','--continue-on-collection-errors','--junitxml='+str(xml)],timeout)
    d=outcomes(xml); counts=dict(Counter(d.values())); print(name,counts,flush=True); return rc,d,counts

def replace_once(path,old,new):
    p=AFTER/path; s=p.read_text(); assert s.count(old)==1,(path,s.count(old),old); p.write_text(s.replace(old,new))

def ledger(root):
    lines=(root/LEDGER).read_text().splitlines()
    return {x.split()[0]:x for x in lines if x.startswith('H')}

def manifest(root):
    names=cmd(['git','ls-files','-z'],root).stdout.split('\0')
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in names if p}

# Materialize two complete source checkouts from the published AK-AL base.
cmd(['git','fetch','--depth=1','origin',BASE])
for p in (BEFORE,AFTER):
    cmd(['git','worktree','add','--detach',str(p),BASE])
assert cmd(['git','rev-parse','HEAD'],BEFORE).stdout.strip()==BASE

# Apply the retained local AM-AP candidate to both sides, now on full checkouts.
payload=json.loads((ROOT/'.audit/am-ar/cumulative.json').read_text())
raw=gzip.decompress(base64.b64decode(payload['gzip_base64'],validate=True))
assert hashlib.sha256(raw).hexdigest()==payload['sha256']
patch=OUT/'AM-AP.patch'; patch.write_bytes(raw)
for root in (BEFORE,AFTER):
    cmd(['git','apply','--check',str(patch)],root)
    cmd(['git','apply',str(patch)],root)
assert len(ledger(BEFORE))==65 and 'H264' not in ledger(BEFORE) and 'H361' not in ledger(BEFORE)

# AQ regression tests: same stable identity must not authorize changed dosing contents.
AQ=AFTER/(T+'test_bounded_push_content_identity.py')
AQ.write_text(r"""# Timed normal push owns dosing-relevant syringe contents captured at confirmation.
import pytest
from test_bounded_normal_push_lifetime import setup
from test_menu_death_lifecycle import execute

MUTATIONS={
    "med": '_r set [0,"Propofol"];',
    "size": '_r set [1,5];',
    "drug_ml": '_r set [2,1.5];',
    "diluent_ml": '_r set [4,0.5];',
    "components": '_r set [5,[["Ketamine",1],["Propofol",1]]];',
    "recipe": '_r set [6,"dilutionB13"];',
}

@pytest.mark.parametrize("boundary",["settle","complete"])
@pytest.mark.parametrize("mutation",list(MUTATIONS))
def test_same_id_changed_dose_content_cannot_complete_old_push(boundary,mutation):
    execute(setup()+'''[call ACME_fnc_skConfirmInjection,"start failed"] call _check;'''+
        ('0 call _runWait;' if boundary=="complete" else '')+'''
        private _s=+(_medic getVariable ["ACME_narcStore",[]]);
        private _r=+(_s select 0);
    '''+MUTATIONS[mutation]+'''
        _s set [0,_r]; [_medic,_s] call ACME_fnc_narcStoreCommit;
    '''+f'''{1 if boundary=="complete" else 0} call _runWait;
        [count _delivered==0,"changed contents were administered by old push"] call _check;
        [(uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo [],"changed-content job did not retire"] call _check;
    ''')

@pytest.mark.parametrize("boundary",["settle","complete"])
def test_cosmetic_label_change_does_not_cancel_confirmed_dose(boundary):
    execute(setup()+'''call ACME_fnc_skConfirmInjection;'''+
        ('0 call _runWait;' if boundary=="complete" else '')+'''
        private _s=+(_medic getVariable ["ACME_narcStore",[]]);
        private _r=+(_s select 0); _r set [3,"renamed label"]; _s set [0,_r];
        [_medic,_s] call ACME_fnc_narcStoreCommit;
    '''+f'''{1 if boundary=="complete" else 0} call _runWait;
    '''+('''
        [count _delivered==0 && {count _waits==2},"settle did not continue after cosmetic change"] call _check;
        1 call _runWait;
    ''' if boundary=="settle" else '')+'''
        [count _delivered==1,"cosmetic label incorrectly cancelled dose"] call _check;
    ''')
""")

# Show the defect on the cumulative AM-AP runtime before changing production source.
(BEFORE/(T+'test_bounded_push_content_identity.py')).write_text(AQ.read_text())
aq_before=tests('AQ-original-AMAP',BEFORE,[T+'test_bounded_push_content_identity.py'])
assert aq_before[0]==1 and aq_before[2].get('failed')==12 and aq_before[2].get('passed')==2,aq_before[2]

# AQ runtime correction: capture only dosing-relevant row fields, and recheck at settle and completion.
CONF=Path('addons/acm_extended/functions/fn_skConfirmInjection.sqf')
replace_once(CONF,
'''private _stableId = _entry param [11,"",[""]];
if (_stableId == "") exitWith {''',
'''private _stableId = _entry param [11,"",[""]];
private _doseSignature = [
    _entry param [0,"",[""]],
    _entry param [1,10,[0]],
    _entry param [2,0,[0]],
    _entry param [4,0,[0]],
    +(_entry param [5,[],[[]]]),
    _entry param [6,"",[""]]
];
if (_stableId == "") exitWith {''')
replace_once(CONF,
'private _job = [_d,ACE_player,_patient,_stableId,_epoch,_closeEpoch];',
'private _job = [_d,ACE_player,_patient,_stableId,_epoch,_closeEpoch,_doseSignature];')
needle='''    private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
    if (([_stableId,_store] call ACME_fnc_skSelectStored) < 0) exitWith {
        [_job] call _retire;
    };
'''
replacement='''    private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
    private _selectedIdx = [_stableId,_store] call ACME_fnc_skSelectStored;
    if (_selectedIdx < 0) exitWith {[_job] call _retire;};
    private _currentEntry = _store select _selectedIdx;
    private _currentDoseSignature = [
        _currentEntry param [0,"",[""]],
        _currentEntry param [1,10,[0]],
        _currentEntry param [2,0,[0]],
        _currentEntry param [4,0,[0]],
        +(_currentEntry param [5,[],[[]]]),
        _currentEntry param [6,"",[""]]
    ];
    if !(_currentDoseSignature isEqualTo (_job select 6)) exitWith {[_job] call _retire;};
'''
s=(AFTER/CONF).read_text()
assert s.count(needle)==2,s.count(needle)
(AFTER/CONF).write_text(s.replace(needle,replacement))

# AR reconciles H051 with the current circulation-green selector backing.
H051=Path(T+'test_b23_narc_route_dead.py')
replace_once(H051,
"self.assertIn('private _green = [0.12,0.62,0.24,0.92]', s)",
"self.assertIn('private _green = [0.20,0.65,0.20,0.92]', s)")
route_test=AFTER/(T+'test_bounded_route_selector_backing.py')
route_test.write_text(r'''"""Protect current split-route backing colors and flush-forced vascular selection."""
import pytest
from source_scan import lex
from test_menu_death_lifecycle import ROOT

P=ROOT/'addons/acm_extended/functions/fn_skBuildHotspots.sqf'

def require(text,snippet):
    a=[x.value for x in lex(text)]; b=[x.value for x in lex(snippet)]
    assert any(a[i:i+len(b)]==b for i in range(len(a)-len(b)+1)),snippet

def contract(text):
    for s in (
        'private _green = [0.20,0.65,0.20,0.92];',
        'private _gray = [0.20,0.20,0.20,0.72];',
        'if (_flush != "") then {_route = "vascular"; uiNamespace setVariable ["ACME_SK_Route", _route];};',
        'if (_route == "vascular") then {_green} else {_gray}',
        'if (_route == "im") then {_green} else {_gray}',
        '_imBtn ctrlEnable (_flush == "");',
    ): require(text,s)

def test_current_route_selector_contract():
    contract(P.read_text())

@pytest.mark.parametrize('old,new',[
    ('[0.20,0.65,0.20,0.92]','[0.12,0.62,0.24,0.92]'),
    ('_route = "vascular"; uiNamespace setVariable ["ACME_SK_Route", _route];','_route = "vascular";'),
    ('_imBtn ctrlEnable (_flush == "");','_imBtn ctrlEnable true;'),
])
def test_contract_rejects_regression_despite_comment(old,new):
    t=P.read_text(); assert old in t
    with pytest.raises(AssertionError): contract(t.replace(old,new,1)+'\n/* '+old+' */\n')
''')

# Ledger: cumulative AM-AP already closed H264/H361. AR closes H051 only.
lp=AFTER/LEDGER
lines=lp.read_text().splitlines()
assert lines[0].startswith('Unresolved original source-contract outcomes after local candidate AP: 65')
assert any(x.startswith('H051 ') for x in lines)
lines=[x for x in lines if not x.startswith('H051 ')]
lines[0]='Unresolved original source-contract outcomes after bounded AR: 64'
lp.write_text('\n'.join(lines)+'\n')
assert len(ledger(AFTER))==64

# Audit notes.
(AFTER/'docs/audits/2026-09-23-bounded-backlog-AQ.md').write_text('''# Bounded AQ: timed push owns dosing-relevant syringe contents

Parent is the retained cumulative AM-AP candidate on published AK-AL. A stable syringe ID prevented index drift, but an external same-ID row mutation could still replace medication, size, drug/diluent volume, component plan or recipe marker between confirmation and completion. The authored plunger would then describe the old row while completion handed off the changed row.

Confirmation now captures only dosing-relevant row fields and rechecks them at the existing settle and completion boundaries. Cosmetic label/tag text is deliberately excluded. A mismatch retires the old normal job without administering or rewriting the changed syringe. No per-frame store scan is added, so animation performance is unchanged. Existing stable-ID, patient/provider/workspace, timing, Hardcore and epinephrine-volume ownership remain.

Fourteen new execution cases: cumulative AM-AP runtime produces twelve intended failures and two passing cosmetic controls; candidate passes all fourteen. This does not prevent arbitrary memory corruption, mutation after the final check has entered the authoritative handoff, or changes outside the normal display-bound push path. No H entry closes in AQ.
''')
(AFTER/'docs/audits/2026-09-23-bounded-backlog-AR.md').write_text('''# Bounded AR: current split-route backing color

H051 retains its historical identity. The old assertion demanded an earlier green backing value. Current Body Map route selection intentionally uses the same circulation green family as vascular access, while IM retains its blue anatomical aura. The historical test now checks the current selector backing rather than restoring the retired color.

A new source-contract module protects the current selected green, unselected gray, flush-forced vascular route and IM disable while a flush is selected, with mutation controls that reject regression despite comment decoys. No runtime, configuration or asset changes in AR. The original ledger moves 65 to 64 after the retained AM-AP closures.
''')

# Focused validation.
focused=[
 T+'test_bounded_push_content_identity.py',
 T+'test_bounded_normal_push_lifetime.py',
 T+'test_bounded_push_display_patient.py',
 T+'test_bounded_site_click_ownership.py',
 T+'test_bounded_flush_patient_context.py',
 T+'test_b23_narc_route_dead.py',
 T+'test_bounded_route_selector_backing.py',
 T+'test_b62_tag_editor_carousel_layout.py',
 T+'test_b73_syringe_tag_vial_carousel_anim.py',
]
focus=tests('focused-AM-AR',AFTER,focused,300)
assert focus[0]==0 and not ({'failed','error','skipped'} & set(focus[2])),focus[2]
assert run('hemtt',AFTER,[os.environ['HEMTT'],'check'],180)==0
assert run('diff-check',AFTER,['git','diff','--check'],60)==0

# Full before/after addon and root comparisons, using cumulative AM-AP as the before side.
with ThreadPoolExecutor(max_workers=2) as ex:
    fb=ex.submit(tests,'addon-AMAP',BEFORE,[T],420)
    fa=ex.submit(tests,'addon-AMAR',AFTER,[T],420)
    before=fb.result(); after=fa.result()
assert before[0]==after[0]==1
assert before[2].get('error',0)==after[2].get('error',0)==0
missing=set(before[1])-set(after[1]); newly=[]
fixed=[]
for k,v in before[1].items():
    if k not in after[1]: continue
    if v=='failed' and after[1][k]=='passed': fixed.append(k)
    elif v!=after[1][k]: newly.append((k,v,after[1][k]))
assert not missing and not newly,(missing,newly)
assert len(fixed)==1 and fixed[0][1]=='test_selected_route_has_green_backing',fixed

with ThreadPoolExecutor(max_workers=2) as ex:
    rb=ex.submit(tests,'root-AMAP',BEFORE,['tools'],240)
    ra=ex.submit(tests,'root-AMAR',AFTER,['tools'],240)
    rbefore=rb.result(); rafter=ra.result()
assert rbefore[2]==rafter[2]
assert rbefore[1]==rafter[1]

# Preserve every untouched tracked byte from cumulative AM-AP to final candidate.
base_manifest=manifest(BEFORE); final_manifest=manifest(AFTER)
changed={p for p in base_manifest if base_manifest[p]!=final_manifest.get(p)}
allowed={
 'addons/acm_extended/functions/fn_skConfirmInjection.sqf',
 T+'test_b23_narc_route_dead.py',
 LEDGER,
}
assert changed==allowed,changed
assert set(base_manifest).issubset(final_manifest)
added=set(final_manifest)-set(base_manifest)
expected_added={
 T+'test_bounded_push_content_identity.py',
 T+'test_bounded_route_selector_backing.py',
 'docs/audits/2026-09-23-bounded-backlog-AQ.md',
 'docs/audits/2026-09-23-bounded-backlog-AR.md',
}
assert added==expected_added,added

# Commit two bounded batches and publish review branch.
def commit(paths,msg):
    cmd(['git','add',*paths],AFTER)
    cmd(['git','-c','user.name=ACME Audit','-c','user.email=acme-audit@users.noreply.github.com','commit','-m',msg],AFTER)
    return cmd(['git','rev-parse','HEAD'],AFTER).stdout.strip()

# We need split commits from final tree: commit AQ runtime/test/doc first, then AR.
# Reset AR files temporarily, commit AQ, then restore them from saved bytes.
saved={p:(AFTER/p).read_bytes() for p in [H051,Path(LEDGER),route_test,Path('docs/audits/2026-09-23-bounded-backlog-AR.md')]}
cmd(['git','checkout','--',str(H051),LEDGER],AFTER)
for p in [route_test,Path('docs/audits/2026-09-23-bounded-backlog-AR.md')]:
    (AFTER/p).unlink()
# Ledger after AQ remains AM-AP's 65.
aq=commit([str(CONF),T+'test_bounded_push_content_identity.py','docs/audits/2026-09-23-bounded-backlog-AQ.md'],'Guard timed push against same-ID content mutation (bounded AQ)')
for p,b in saved.items():
    (AFTER/p).parent.mkdir(parents=True,exist_ok=True); (AFTER/p).write_bytes(b)
ar=commit([str(H051),LEDGER,T+'test_bounded_route_selector_backing.py','docs/audits/2026-09-23-bounded-backlog-AR.md'],'Align route selector contract with current vascular backing (bounded AR)')
assert not cmd(['git','status','--porcelain'],AFTER).stdout.strip()

report={
 'published_base':BASE,
 'retained_AM_AP_full_checkout_validated':True,
 'AQ':aq,'AR':ar,
 'focused':focus[2],
 'AQ_original_AMAP':aq_before[2],
 'addon_before_AMAP':before[2],
 'addon_after_AMAR':after[2],
 'root_before':rbefore[2],'root_after':rafter[2],
 'fixed_original_ids':['H051'],
 'remaining_original_entries':64,
 'runtime_files_changed':['addons/acm_extended/functions/fn_skConfirmInjection.sqf'],
 'newly_failing':[],'missing_previous':[],
 'hemtt_exit':0,'live_arma_tested':False,'stable_release_approved':False,
 'branch':BRANCH
}
(OUT/'report.json').write_text(json.dumps(report,indent=2))
(OUT/'final.patch').write_text(cmd(['git','diff',BASE,'HEAD'],AFTER).stdout)
cmd(['git','format-patch','--output-directory',str(OUT),BASE+'..HEAD'],AFTER)
cmd(['git','push','origin',f'HEAD:refs/heads/{BRANCH}'],AFTER)
print('PUBLISHED',json.dumps(report,indent=2),flush=True)
