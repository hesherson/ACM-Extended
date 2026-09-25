"""Execute the current one-shot holster helper and native treatment bridge.

Weapon/animation/stance, configuration, inventory eligibility and CBA callback
scheduling are explicit engine boundaries. Real branch order, reservations,
readiness checks, delegation and callback payloads execute from source. Callbacks
are delivered only after their actual condition succeeds, or as an explicit timeout.
No Arma weapon-model rendering or automatic timing simulation is claimed.
"""
import re
import pytest
from source_scan import lex
from test_menu_death_lifecycle import ROOT, adapt, execute

F = ROOT / 'addons/acm_extended/functions'
TREATMENT = ROOT / 'addons/core/overrides/fnc_treatment.sqf'


def source(name):
    return (F / ('fn_' + name + '.sqf')).read_text()


def engine(text):
    """Replace engine reads before the shared adapter's default object mocks."""
    for unit in ('_medic', '_m', '_u', '_unit'):
        for prefix, replacement in [
            ('local ', '_localProvider'), ('alive ', '_alive'),
            ('currentWeapon ', '_weaponNow'), ('handgunWeapon ', '"pistol"'),
            ('animationState ', '_animNowFixture'), ('stance ', '_stanceNow'),
            ('objectParent ', '_providerParent'), ('netId ', '"medic"'),
        ]:
            text = re.sub(re.escape(prefix + unit) + r'\b', lambda _: replacement, text)
        text = re.sub(re.escape(unit) + r' setUnitPos ([^;]+);',
                      r'_positions pushBack \1;', text)
    text = text.replace('objectParent _patient', '_patientParent')
    text = text.replace('vest _patient', '""')
    text = text.replace('_medic action ["SwitchWeapon", _medic, _medic, 299];',
                        '_engineHolsters pushBack ["SwitchWeapon", _medic, _medic, 299];')
    return adapt(text)


def setup(ace=True):
    # Config read values select ordinary limb dressing, not head/chest-prep paths.
    # All treatment branches remain in the compiled function.
    bridge = TREATMENT.read_text()
    bridge = bridge.replace('configFile >> "ace_medical_treatment_actions" >> _classname', 'configNull')
    bridge = bridge.replace('getText (_cfg >> "category")', '_categoryFixture')
    bridge = bridge.replace('getNumber (_cfg >> "ACM_rollToBack")', '0')
    bridge = bridge.replace('getNumber (_cfg >> "ACM_cancelRecovery")', '0')
    body = r'''
        private _localProvider = true;
        private _weaponNow = "rifle";
        private _animNowFixture = "AmovPercMstpSrasWrflDnon";
        private _stanceNow = "STAND";
        private _providerParent = objNull;
        private _patientParent = objNull;
        private _positions = [];
        private _holsters = [];
        private _engineHolsters = [];
        private _timers = [];
        private _nativeCalls = [];
        private _nativeAccepted = true;
        private _categoryFixture = "bandage";
        private _permitted = true;
        private _interactable = true;
        private _actualSide = "front";
        private _clock = 10;
        ACME_fnc_animBlocked = {!(_providerParent isEqualTo objNull)};
        ACME_fnc_treatmentPoseStop = {};
        ACME_fnc_menuPoseStop = {};
        ACME_fnc_providerStanceOwned = {false};
        CBA_fnc_waitUntilAndExecute = {_timers pushBack _this;};
        CBA_fnc_execNextFrame = {_waits pushBack _this;};
        ACME_fnc_procedureActionAllowed = {_permitted};
        ACME_fnc_chestSealCanPhysicalRoll = {false};
        ACME_fnc_chestSealActualSide = {"front"};
        ACME_fnc_doAnim = {_moves pushBack _this;};
        ace_common_fnc_canInteractWith = {_interactable};
        ace_medical_treatment_fnc_canTreatCached = {true};
        ACM_core_fnc_treatmentNative = {
            _nativeCalls pushBack [_this,
                (_this select 0) getVariable ["ACME_treatmentPreflightBypass",[]]];
            _nativeAccepted
        };
        ace_medical_gui_pendingReopen = false;
        // Native availability is toggled per test. No hidden sling integration.
        tsp_fnc_animate_sling = {_ok=false;};
        tsp_fnc_animate_sling_get = {_ok=false;};
        private _condition = {private _j=_timers select _this; (_j select 2) call (_j select 0)};
        private _deliver = {
            private _j=_timers select _this;
            private _ready=(_j select 2) call (_j select 0);
            [_ready,"test delivered an unready success callback"] call _check;
            if (_ready) then {(_j select 2) call (_j select 1);};
        };
        private _timeout = {private _j=_timers select _this; (_j select 2) call (_j select 4);};
    '''
    if ace:
        body += 'ace_weaponselect_fnc_putWeaponAway = {_holsters pushBack (_this select 0);};'
    else:
        body += 'ace_weaponselect_fnc_putWeaponAway = nil;'
    body += 'ACME_fnc_medicAnimationPrep = {' + engine(source('medicAnimationPrep')) + '};'
    body += 'ace_medical_treatment_fnc_treatment = {' + engine(bridge) + '};'
    return body


@pytest.mark.parametrize('weapon,delay', [('pistol', .95), ('rifle', .70), ('launcher', .70)])
@pytest.mark.parametrize('ace', [True, False])
def test_one_engine_holster_request_is_retained_across_repeated_controllers(weapon, delay, ace):
    execute(setup(ace) + f'_weaponNow="{weapon}"; private _minimum={delay};' + r'''
        private _first=[_medic] call ACME_fnc_medicAnimationPrep;
        [_first==_minimum,"initial settle changed"] call _check;
        private _record=+(_medic getVariable ["ACME_medicAnimationPrep",[]]);
        {
            CBA_missionTime=10+_x;
            private _remaining=[_medic] call ACME_fnc_medicAnimationPrep;
            [abs (_remaining-((_minimum-_x) max 0.05))<0.000001,"pending settle was restarted"] call _check;
            [(_medic getVariable ["ACME_medicAnimationPrep",[]]) isEqualTo _record,"pending holster token replaced"] call _check;
        } forEach [0,0.1,0.5,0.9,1.5,3.19];
        [count _holsters+count _engineHolsters==1,"another controller queued another holster"] call _check;
    ''')


@pytest.mark.parametrize('elapsed', [3.2, 4, -1])
def test_expired_or_time_reversed_reservation_allows_one_fresh_request(elapsed):
    execute(setup() + 'CBA_missionTime=0; [_medic] call ACME_fnc_medicAnimationPrep;' +
            f'CBA_missionTime={elapsed};' + r'''
        [_medic] call ACME_fnc_medicAnimationPrep;
        [count _holsters==2,"fresh episode did not issue one request"] call _check;
        [(_medic getVariable ["ACME_medicAnimationPrep",[]]) select 1==CBA_missionTime,"new request timestamp wrong"] call _check;
    ''')


@pytest.mark.parametrize('record', ['[]', '["other",10]', '["empty_hands_once"]', 'false'])
def test_unrelated_or_short_reservation_does_not_block_initial_request(record):
    execute(setup() + f'_medic setVariable ["ACME_medicAnimationPrep",{record}];' + r'''
        [_medic] call ACME_fnc_medicAnimationPrep;
        [count _holsters==1,"unrelated reservation blocked prep"] call _check;
    ''')


@pytest.mark.parametrize('animation', [
    'AmovPknlMstpSnonWnonDnon', 'ACME_ChestSealWorkspace',
    'ACME_StethoscopeWork', 'ACME_DirectPressureHold', 'ACM_GenericContinuous', 'ACM_ProneContinuous',
])
def test_logical_and_visible_empty_hands_finish_without_another_holster(animation):
    execute(setup() + r'''
        [_medic] call ACME_fnc_medicAnimationPrep;
        _weaponNow="";
    ''' + f'_animNowFixture="{animation}";' + r'''
        private _delay=[_medic] call ACME_fnc_medicAnimationPrep;
        [_delay==0 && {count _holsters==1},"settled hands kept holstering"] call _check;
        [(_medic getVariable ["ACME_medicAnimationPrep",[]]) select 0=="empty_hands_ready","ready state absent"] call _check;
    ''')


@pytest.mark.parametrize('previous', [False, True])
def test_logical_clear_during_visible_holster_waits_without_reissuing(previous):
    execute(setup() + ('[_medic] call ACME_fnc_medicAnimationPrep;' if previous else '') + r'''
        _weaponNow=""; CBA_missionTime=10.1;
        private _delay=[_medic] call ACME_fnc_medicAnimationPrep;
    ''' + f'[_delay>0 && {{count _holsters=={int(previous)}}},"logical clear caused another weapon switch"] call _check;')


@pytest.mark.parametrize('change', ['_localProvider=false;', '_alive=false;', '_providerParent=missionNamespace;'])
def test_ineligible_provider_does_not_request_or_rewrite_holster(change):
    execute(setup() + r'''
        _medic setVariable ["ACME_medicAnimationPrep",["keep",5,"pistol"]];
    ''' + change + r'''
        private _result=[_medic] call ACME_fnc_medicAnimationPrep;
        [_result==0 && {count _holsters==0} && {count _engineHolsters==0},"ineligible holster request"] call _check;
        [(_medic getVariable ["ACME_medicAnimationPrep",[]]) isEqualTo ["keep",5,"pistol"],"ineligible call changed reservation"] call _check;
    ''')


def test_engine_fallback_has_same_provider_and_switchweapon_contract():
    execute(setup(False) + r'''
        [_medic] call ACME_fnc_medicAnimationPrep;
        [_engineHolsters isEqualTo [["SwitchWeapon",_medic,_medic,299]],"wrong fallback command"] call _check;
        [count _holsters==0,"fallback also called ACE"] call _check;
    ''')


@pytest.mark.parametrize('stance', ['STAND', 'PRONE', 'CROUCH'])
def test_native_treatment_waits_for_logical_and_visible_holster_then_crouch(stance):
    execute(setup() + f'_stanceNow="{stance}";' + r'''
        private _args=[_medic,_patient,"LeftArm","FieldDressing"];
        [_args call ace_medical_treatment_fnc_treatment,"preflight not accepted"] call _check;
        [count _holsters==1 && {count _timers==1} && {count _nativeCalls==0},"preflight did not defer native treatment"] call _check;
        [! (0 call _condition),"armed holster considered ready"] call _check;
        _weaponNow="";
        [! (0 call _condition),"logical clear bypassed visible holster"] call _check;
        _animNowFixture="AmovPercMstpSnonWnonDnon";
        0 call _deliver;
        [count _nativeCalls==0 && {count _timers==2},"phase1 launched treatment early"] call _check;
        [_positions isEqualTo ["MIDDLE"],"crouch entry guard changed"] call _check;
        private _transition=switch (_stanceNow) do {
            case "STAND": {"AmovPercMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon"};
            case "PRONE": {"AmovPpneMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon"};
            default {""};
        };
        private _expectedMoves=if (_transition=="") then {[]} else {[[_medic,_transition,1]]};
        [_moves isEqualTo _expectedMoves,"wrong or repeated crouch transition"] call _check;
        [(_timers select 0) select 3==3 && {(_timers select 1) select 3==1.8},"preflight timeouts changed"] call _check;
        _stanceNow="CROUCH"; _animNowFixture="AmovPknlMstpSnonWnonDnon";
        1 call _deliver;
        [count _nativeCalls==1,"ready preflight did not launch exactly once"] call _check;
        private _call=_nativeCalls select 0;
        [(_call select 0) isEqualTo _args,"preflight changed target/site/action"] call _check;
        [(_call select 1) isEqualTo [_patient,"LeftArm","FieldDressing"],"scoped bypass missing"] call _check;
        [!(_medic getVariable ["ACME_treatmentPreflightActive",true]),"preflight stayed active"] call _check;
        [(_medic getVariable ["ACME_treatmentPreflightBypass",[1]]) isEqualTo [],"bypass not cleared"] call _check;
        [(_medic getVariable ["ACME_treatmentPreflightToken","bad"])=="","token not cleared"] call _check;
        [count _holsters==1 && {ace_medical_gui_pendingReopen},"recursive launch reholstered or lost menu handoff"] call _check;
    ''')


@pytest.mark.parametrize('phase', [0, 1])
def test_preflight_timeout_releases_its_own_reservation_without_starting_treatment(phase):
    execute(setup() + r'''
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
    ''' + (r'''
        _weaponNow=""; _animNowFixture="AmovPercMstpSnonWnonDnon"; 0 call _deliver;
    ''' if phase else '') + f'{phase} call _timeout;' + r'''
        [count _nativeCalls==0,"timeout launched treatment"] call _check;
        [!(_medic getVariable ["ACME_treatmentPreflightActive",true]),"timeout kept active reservation"] call _check;
        [(_medic getVariable ["ACME_treatmentPreflightToken","bad"])=="","timeout kept token"] call _check;
        [(_positions select (count _positions-1))=="AUTO","timeout left stance locked"] call _check;
        [!ace_medical_gui_pendingReopen,"timeout armed menu reopen"] call _check;
    ''')


@pytest.mark.parametrize('phase', [0, 1])
@pytest.mark.parametrize('delivery', ['_deliver', '_timeout'])
def test_superseded_preflight_callback_cannot_clear_new_reservation(phase, delivery):
    execute(setup() + r'''
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
    ''' + ('_weaponNow=""; _animNowFixture="AmovPercMstpSnonWnonDnon"; 0 call _deliver;' if phase else '') + r'''
        _medic setVariable ["ACME_treatmentPreflightToken","new-token"];
        _medic setVariable ["ACME_treatmentPreflightActive",true];
        _moves=[]; _positions=[];
    ''' + f'{phase} call {delivery};' + r'''
        [count _nativeCalls==0 && {count _moves==0} && {count _positions==0},"superseded callback had side effects"] call _check;
        [(_medic getVariable ["ACME_treatmentPreflightToken",""])=="new-token","superseded callback cleared replacement"] call _check;
        [_medic getVariable ["ACME_treatmentPreflightActive",false],"replacement deactivated"] call _check;
    ''')


@pytest.mark.parametrize('phase', [0, 1])
@pytest.mark.parametrize('change', ['_alive=false;', '_localProvider=false;'])
def test_pending_preflight_rechecks_provider_life_and_locality(phase, change):
    execute(setup() + r'''
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
    ''' + ('_weaponNow=""; _animNowFixture="AmovPercMstpSnonWnonDnon"; 0 call _deliver;' if phase else '') + change +
            f'{phase} call _deliver;' + '[count _nativeCalls==0,"invalid provider started native treatment"] call _check;')


@pytest.mark.parametrize('classname', ['UseBVM','UseBVM_Oxygen','UseBVM_VehicleOxygen','UseBVM_PortableOxygen','UseStethoscope','BeginHeadTiltChinLift','CPR'])
def test_native_continuous_launchers_do_not_enter_generic_holster_preflight(classname):
    execute(setup() + f'[_medic,_patient,"Head","{classname}"] call ace_medical_treatment_fnc_treatment;' + r'''
        [count _nativeCalls==1 && {count _timers==0} && {count _holsters==0},"launcher acquired generic preflight"] call _check;
    ''')


@pytest.mark.parametrize('alive', [True, False])
def test_genuinely_empty_crouch_fast_path_keeps_dead_patient_treatment_available(alive):
    execute(setup() + f'_patientAlive={str(alive).lower()};' + r'''
        _weaponNow=""; _animNowFixture="AmovPknlMstpSnonWnonDnon"; _stanceNow="CROUCH";
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        [count _nativeCalls==1 && {count _timers==0} && {count _holsters==0},"ready/dead-patient path was blocked"] call _check;
    ''')


def test_repeated_click_cannot_queue_a_second_generic_preflight():
    execute(setup() + r'''
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        private _again=[_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        [!_again && {count _timers==1} && {count _holsters==1},"duplicate click queued preflight"] call _check;
    ''')


def test_active_direct_pressure_remains_a_native_handoff_without_reholstering():
    execute(setup() + r'''
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_Patient",_patient];
        _medic setVariable ["ACME_DP_InPose",true];
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        [count _nativeCalls==1 && {count _timers==0} && {count _holsters==0},"DP handoff reholstered"] call _check;
        [_medic getVariable ["ACME_DP_Active",false],"ordinary dressing stopped clinical DP"] call _check;
        [!(_medic getVariable ["ACME_DP_InPose",true]),"old visual loop was not retired"] call _check;
        [_medic getVariable ["ACME_DP_TreatmentBusy",false],"native treatment did not own handoff"] call _check;
    ''')


def test_current_weapon_paths_do_not_invoke_optional_sling_or_direct_reselection():
    for path in [F/'fn_medicAnimationPrep.sqf',F/'fn_treatmentPoseStop.sqf',TREATMENT]:
        identifiers={t.value for t in lex(path.read_text()) if t.kind=='ident'}
        assert not {'tsp_fnc_animate_sling','tsp_fnc_animate_sling_get','selectWeapon'} & identifiers,path
    assert 'class medicAnimationPrep {};' in (F.parent/'config.cpp').read_text()


@pytest.mark.parametrize('weapon', ['pistol', 'rifle', 'launcher'])
def test_real_pose_handoff_shares_pending_holster_instead_of_restarting_it(weapon):
    from test_historical_pose_lifecycle import setup as pose_setup
    helper=engine(source('medicAnimationPrep'))
    for old,new in [('_localProvider','_isLocal'),('_weaponNow','_weapon'),('_animNowFixture','_animation'),('_providerParent','_parent')]:
        helper=helper.replace(old,new)
    execute(pose_setup()+r'''
        private _holsters=[];
        ace_weaponselect_fnc_putWeaponAway={_holsters pushBack (_this select 0);};
    '''+f'_weapon="{weapon}"; _animation="AmovPercMstpSrasWrflDnon";'+
        'ACME_fnc_medicAnimationPrep={'+helper+'};'+r'''
        private _first=[_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _record=+(_medic getVariable ["ACME_medicAnimationPrep",[]]);
        CBA_missionTime=CBA_missionTime+0.1;
        private _second=[_medic,"pulse",-1,_patient] call ACME_fnc_treatmentPoseStart;
        [_second>_first && {count _holsters==1},"pose handoff repeated holster"] call _check;
        [(_medic getVariable ["ACME_medicAnimationPrep",[]]) isEqualTo _record,"pose handoff replaced holster reservation"] call _check;
        [_weapon!="","pose handoff forced logical weapon clear"] call _check;
    ''')


def test_pose_direct_pressure_exception_stays_scoped_and_does_not_restore_a_weapon():
    # This already-established empty-hands DP hold has a deliberate selectWeapon ""
    # exception. Do not remove it to satisfy an obsolete whole-file string ban.
    from test_historical_pose_lifecycle import setup as pose_setup
    execute(pose_setup()+r'''
        _weapon="rifle";
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_TreatmentBusy",true];
        [_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        [_preps==0 && {_weapon==""},"DP handoff reholstered or retained logical weapon"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_weaponNow="rifle"; _stanceNow="CROUCH";',
    '_animNowFixture="AmovPknlMstpSrasWpstDnon"; _stanceNow="CROUCH";',
    '_stanceNow="STAND";',
])
def test_second_phase_does_not_bypass_readiness_after_weapon_or_stance_changes(change):
    execute(setup()+r'''
        [_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        _weaponNow=""; _animNowFixture="AmovPercMstpSnonWnonDnon"; 0 call _deliver;
    '''+change+r'''
        [!(1 call _condition),"second phase accepted incorrect logical/visual/stance state"] call _check;
        1 call _timeout;
        [count _nativeCalls==0,"unready second phase launched treatment"] call _check;
    ''')


def test_one_providers_pending_holster_does_not_block_another_provider():
    execute(setup()+r'''
        [_medic] call ACME_fnc_medicAnimationPrep;
        [_patient] call ACME_fnc_medicAnimationPrep;
        [_holsters isEqualTo [_medic,_patient],"holster reservation leaked across providers"] call _check;
    ''')


def test_true_empty_crouch_fast_path_preserves_native_rejection():
    execute(setup()+r'''
        _weaponNow=""; _animNowFixture="AmovPknlMstpSnonWnonDnon"; _stanceNow="CROUCH";
        _nativeAccepted=false;
        private _result=[_medic,_patient,"LeftArm","FieldDressing"] call ace_medical_treatment_fnc_treatment;
        [!_result && {count _nativeCalls==1},"bridge swallowed native rejection"] call _check;
        [count _timers==0 && {count _holsters==0},"rejection queued presentation"] call _check;
    ''')
