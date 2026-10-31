"""Current clinical contracts behind historical source-text failures.

Runs actual SQF functions or exact transaction fragments. UI, item and transport
boundaries are mocked; this does not certify Arma graphics or multiplayer delivery.
"""
from pathlib import Path
import re
import pytest
from test_menu_death_lifecycle import adapt, execute
from source_scan import lex, matching

F=Path(__file__).resolve().parents[1]/'functions'

def source(name):return (F/('fn_'+name+'.sqf')).read_text()

def unique_slice(text,start,end):
    assert text.count(start)==1,start
    a=text.index(start); b=text.index(end,a)
    assert b>a
    return text[a:b]

def thora_setup():
    return '''
        private _permission = true;
        private _kit = "ACM_ThoracostomyKit";
        private _writes = [];
        private _renders = 0;
        ACME_fnc_minigameInputMouse = {false};
        ACME_fnc_procedureAllowed = {_permission};
        ACME_fnc_thoraKitItem = {_kit};
        ACME_fnc_thoraSideStateCommit = {_writes pushBack _this;};
        ACME_fnc_thoraRender = {_renders = _renders + 1;};
        ACME_fnc_thoraRenderOpen = {};
        ACME_fnc_thoraBumpVer = {};
        uiNamespace setVariable ["ACME_Thora_Medic",_medic];
        uiNamespace setVariable ["ACME_Thora_Patient",_patient];
        uiNamespace setVariable ["ACME_Thora_Side","right"];
        _patient setVariable ["ACME_thora_open_right","split"];
    '''

@pytest.mark.parametrize('tool',['Cutting','KellyArmed'])
@pytest.mark.parametrize('permission,kit',[(False,True),(True,False),(False,False)])
def test_lost_permission_or_kit_cancels_inflight_thoracostomy_before_commit(tool,permission,kit):
    execute(thora_setup() + f'_permission={str(permission).lower()}; _kit="'+('ACM_ThoracostomyKit' if kit else '')+'";' +
            f'uiNamespace setVariable ["ACME_Thora_{tool}",true];' +
            'private _release = {'+adapt(source('thoraMouseUp'))+'};' + '''
        [objNull,0] call _release;
        [count _writes==0,"denied release changed patient state"] call _check;
        [!(uiNamespace getVariable ["ACME_Thora_Cutting",false]),"cutting still armed"] call _check;
        [!(uiNamespace getVariable ["ACME_Thora_KellyArmed",false]),"clamp still armed"] call _check;
        [_renders==1,"cancel did not repaint UI"] call _check;
    ''')


def test_accepted_kelly_release_still_commits_existing_tract():
    execute(thora_setup() + 'uiNamespace setVariable ["ACME_Thora_KellyArmed",true];' +
            'private _release = {'+adapt(source('thoraMouseUp'))+'};' + '''
        [objNull,0] call _release;
        [count _writes==1,"valid clamp release failed"] call _check;
        [(_writes select 0) isEqualTo [_patient,"right","open","kelly"],"wrong side/state committed"] call _check;
    ''')

@pytest.mark.parametrize('kit,receipt,expected',[
    ('ACM_ThoracostomyKit','ACM_ThoracostomyKit',True),
    ('ACM_ThoracostomyKit','',False),
    ('ACE_surgicalKit','',True),('', '',False)])
def test_finger_tract_consumes_only_disposable_and_requires_verified_receipt(kit,receipt,expected):
    text=source('thoraMouseDown')
    body=unique_slice(text,'    private _kit = [_medic, _patient] call ACME_fnc_thoraKitItem;',
                      '\n    false\n};\n\nif (_held in ["seal", "tube"])')
    execute(thora_setup() + f'_kit="{kit}"; private _receipt="{receipt}";' + '''
        private _uses = 0; private _requests = [];
        private _side = "right";
        ACME_fnc_treatmentSupplyTake = {_uses=_uses+1; if (_receipt=="ACM_ThoracostomyKit") then {[_medic,_receipt,objNull,"receipt1"]} else {[]}};
        ACME_fnc_thoraAftercareRequest = {_requests pushBack _this;};
    ''' + 'private _commit = {'+adapt(body)+'}; call _commit;' +
            f'[count _requests=={int(expected)},"unverified or missing kit requested tract"] call _check;' +
            '[count _writes==0,"provider changed owner tract before acceptance"] call _check;' +
            f'[_uses=={int(kit=="ACM_ThoracostomyKit")},"reusable/absent kit was consumed"] call _check;')

@pytest.mark.parametrize('allowed,consumed',[(False,False),(True,False),(True,True)])
def test_tube_requires_permission_and_actual_inventory_debit_before_projection(allowed,consumed):
    text=source('thoraMouseDown')
    body=unique_slice(text,'    private _tubeMedic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];',
                      '    // register the chest tube with ACM')
    execute(thora_setup()+f'private _allowed={str(allowed).lower()}; private _consumed={str(consumed).lower()};' + '''
        private _side="right"; private _takes=0; private _refunds=0;
        ACME_fnc_thoraClosureMode = {["tube","",_allowed]};
        ACME_fnc_treatmentSupplyTake = {
            _takes=_takes+1;
            if (_consumed) then {[_tubeMedic,"ACM_ChestTubeKit",objNull,"tube-receipt"]} else {[]}
        };
        ACME_fnc_treatmentSupplyRefund = {_refunds=_refunds+1; true};
    '''+'private _commit={'+adapt(body)+'}; call _commit;'+
            f'[count _writes=={3 if allowed and consumed else 0},"invalid tube projection"] call _check;'+
            f'[_takes=={int(allowed)},"denied tube attempted debit"] call _check;'+
            f'[_refunds=={int(allowed and consumed)},"accepted receipt was not finalized exactly once"] call _check;')


def difficulty_setup():
    # Blood pressure and site catalog are engine/config boundaries. The full SQF
    # pressure, BOA, gauge and EJ algorithms execute; generic site omits anatomy multipliers.
    # SQF-VM does not implement finite. All pressures in these cases are finite;
    # substitute only this engine predicate, not the pressure calculation. NaN/Inf rejection is not exercised.
    body=source('ivSiteDifficulty').replace('finite _d','(_d call _finite)').replace('finite _s','(_s call _finite)')
    # linearConversion is another unsupported engine primitive. Replace that
    # call only with a bounded affine-map mock; retain all production arguments.
    ts=lex(body); pairs=matching(ts); edits=[]
    for i,t in enumerate(ts):
        if t.kind=='ident' and t.value=='linearConversion':
            assert ts[i+1].value=='[' and i+1 in pairs
            j=pairs[i+1]; start=t.offset; end=ts[j].offset+1
            edits.append((start,end,'('+body[ts[i+1].offset:end]+' call _linear)'))
    for start,end,replacement in reversed(edits):body=body[:start]+replacement+body[end:]
    return '''
        private _linear = {
            params ["_lo","_hi","_x","_start","_end","_clamp"];
            private _f=(_x-_lo)/(_hi-_lo);
            if (_clamp) then {_f=(_f max 0) min 1;};
            _start+(_f*(_end-_start))
        };
        private _finite = {_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
        private _pressure = [80,120];
        ace_medical_status_fnc_getBloodPressure = {_pressure};
        ACME_fnc_ivVeinCatalog = {[]};
        uiNamespace setVariable ["ACME_IV_BandOn",false];
        uiNamespace setVariable ["ACME_IV_Site",""];
    ''' + 'private _difficulty={'+adapt(body)+'};'


def verify_pressure_difficulty():
    execute(difficulty_setup()+'''
        {
            private _part = _x;
            _pressure=[80,120]; private _normal=[_patient,_part,18,"middle"] call _difficulty;
            _pressure=[55,85]; private _low=[_patient,_part,18,"middle"] call _difficulty;
            _pressure=[25,45]; private _severe=[_patient,_part,18,"middle"] call _difficulty;
            {[_severe select _x < (_low select _x) && {(_low select _x) < (_normal select _x)},"pressure no longer reduces patency/feel/hit"] call _check;} forEach [0,1,2,3];
            [(_severe select 2)>0,"severe shock removed all placement tolerance"] call _check;
        } forEach ["leftarm","rightarm","leftleg","rightleg","ej"];
    ''')


def verify_gauge_precision():
    execute(difficulty_setup()+'''
        private _g18=[_patient,"leftarm",18,"middle"] call _difficulty;
        private _g20=[_patient,"leftarm",20,"middle"] call _difficulty;
        [abs (((_g20 select 2)/(_g18 select 2))-(1.35/1.15))<0.00001,"18G/20G precision relationship lost"] call _check;
        [(_g18 select 0)==(_g20 select 0) && {(_g18 select 1)==(_g20 select 1)},"gauge changed venous filling or palpation"] call _check;
    ''')


def test_boa_improves_same_or_distal_sites_but_never_creates_absent_perfusion():
    execute(difficulty_setup()+'''
        _pressure=[60,90];
        private _bare=[_patient,"leftarm",18,"middle"] call _difficulty;
        uiNamespace setVariable ["ACME_IV_BandOn",true];
        uiNamespace setVariable ["ACME_IV_Site","middle"];
        private _same=[_patient,"leftarm",18,"middle"] call _difficulty;
        private _distal=[_patient,"leftarm",18,"lower"] call _difficulty;
        private _proximal=[_patient,"leftarm",18,"upper"] call _difficulty;
        [(_same select 0)>(_distal select 0) && {(_distal select 0)>(_bare select 0)},"BOA distal ordering wrong"] call _check;
        [(_proximal select 0)==(_bare select 0),"distal band created proximal benefit"] call _check;
        _pressure=[0,0];
        private _empty=[_patient,"leftarm",18,"middle"] call _difficulty;
        [(_empty select 0)==0,"BOA manufactured perfusion"] call _check;
    ''')
