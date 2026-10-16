"""Execute B212 provider posture/menu/pose ownership using production SQF.

The historical pose harness supplies explicit Arma stance, animation, locality,
config-duration and CBA scheduling boundaries. These tests do not render RTMs.
"""
import pytest

from source_scan import lex, matching, split_args
from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_historical_pose_lifecycle import setup as pose_setup, pose_source
from test_b161_flip_and_breathing import flip_setup, flip_tick


def setup():
    source = pose_setup() + r'''
        private _display=missionNamespace;
        ace_common_fnc_isSwimming={false};
    '''
    for name in ('menuPoseStart', 'menuPoseStop'):
        code = pose_source(name)
        for command, value in [('primaryWeapon','rifle'), ('secondaryWeapon','launcher'),
                               ('handgunWeapon','pistol'), ('binocular','binocular')]:
            code = code.replace(command + ' _medic', '"' + value + '"')
        source += 'ACME_fnc_' + name + '={' + code + '};'
    return source


MODES = ['response','airway','assessmentAirway','assessmentBreathing','roll','chestAccess',
         'inspect','chestSealWorkspace','junctional','stethoscope','chestSeal','ncdSeat','pulse',
         'torsoBandage','headBandageLeft','headBandageRight','directPressureAction']


@pytest.mark.parametrize('mode', MODES)
def test_every_shared_work_mode_preserves_prone_entry_and_exit(mode):
    execute(setup() + f'''
        _stance="PRONE";
        private _epoch=[_medic,"{mode}",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        [_epoch>0 && {{(_state select 20)}} && {{(_state select 2)=="ACM_ProneContinuous"}},
            "shared work mode lost prone entry"] call _check;
        [_positions isEqualTo ["DOWN"] && {{_moves isEqualTo [[_medic,"ACM_ProneContinuous",1]]}},
            "prone work requested kneeling animation or stance"] call _check;
        _animation="acm_pronecontinuous";
        private _id=_state select 5;
        [_id] call _poseTick;
        [_medic,"{mode}",_epoch] call ACME_fnc_treatmentPoseStop;
        [(_positions find "MIDDLE")==-1,"prone cleanup forced crouch"] call _check;
        [((_moves select (count _moves-1)) select 1)=="AmovPpneMstpSnonWnonDnon",
            "prone work did not exit to supported prone idle"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseState",[1]]) isEqualTo [] && {{_id in _removed}},
            "prone work retained its episode or worker"] call _check;
        {{[_x] call _deliver;}} forEach +_speedWaits;
        [_speed==1,"prone cleanup left accelerated/frozen animation speed"] call _check;
        [count _waits==0,"prone cleanup scheduled a deferred crouch correction"] call _check;
    ''')


@pytest.mark.parametrize('mode', ['roll','chestAccess','inspect','pulse','stethoscope'])
def test_prone_hold_never_seeks_a_kneeling_rtm_timestamp(mode):
    execute(setup() + f'''
        _stance="PRONE";
        private _epoch=[_medic,"{mode}",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_state select 5;
        _animation="acm_pronecontinuous";
        [_id] call _poseTick;
        [_id] call _poseTick;
        [(_state select 3)==3 && {{(_state select 11)==0}} && {{_speed==0}},
            "prone work did not expose the held-stage contract"] call _check;
        [(_seeks findIf {{(_x select 0)!="ACM_ProneContinuous" || {{(_x select 1)!=0}}}})==-1,
            "prone work sought a kneeling frame"] call _check;
        _seeks=[]; _speed=1;
        [_id] call _poseTick;
        [_speed==0 && {{count _seeks==0}},"speed-only repair restarted prone work"] call _check;
    ''')


@pytest.mark.parametrize('animation,expected', [
    ('ACME_ChestInspectWork','ACM_ProneContinuous'),
    ('AinvPknlMstpSnonWnonDr_medic4','ACM_ProneContinuous'),
    ('AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown','ACM_ProneContinuous'),
    ('AmovPknlMstpSnonWnonDnon','AmovPpneMstpSnonWnonDnon'),
    ('AidlPknlMstpSnonWnonDnon','AmovPpneMstpSnonWnonDnon'),
    ('ACM_ProneContinuous','ACM_ProneContinuous'),
    ('AinvPpneMstpSnonWnonDnon_medicOther','AinvPpneMstpSnonWnonDnon_medicOther'),
    ('',''),
])
def test_provider_mapping_preserves_supported_prone_and_distinguishes_idle_from_work(animation, expected):
    execute(setup() + f'''
        _stance="PRONE";
        [([_medic,"{animation}"] call ACME_fnc_providerAnimation)=="{expected}",
            "incorrect prone provider animation mapping"] call _check;
        _stance="CROUCH";
        [([_medic,"{animation}",true] call ACME_fnc_providerAnimation)=="{expected}",
            "delayed callback discarded captured prone entry"] call _check;
    ''')


@pytest.mark.parametrize('stance', ['STAND','CROUCH'])
def test_provider_mapping_leaves_nonprone_authored_states_unchanged(stance):
    execute(setup() + f'_stance="{stance}";' + r'''
        { [([_medic,_x] call ACME_fnc_providerAnimation)==_x,"nonprone mapping changed authored state"] call _check; }
            forEach ["ACME_ChestInspectWork","AinvPknlMstpSnonWnonDr_medic4","AmovPknlMstpSnonWnonDnon"];
    ''')


def test_provider_going_prone_during_weapon_preparation_is_not_raised_by_delayed_entry():
    execute(setup() + r'''
        _stance="STAND"; _testPrepDelay=0.5;
        [_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        _stance="PRONE"; _animation="amovppnemstpsnonwnondnon"; CBA_missionTime=10.6;
        [_state select 5] call _poseTick;
        [(_state select 20) && {(_state select 2)=="ACM_ProneContinuous"},"delayed entry lost new prone posture"] call _check;
        [_positions isEqualTo ["DOWN"] && {_moves isEqualTo [[_medic,"ACM_ProneContinuous",1]]},
            "delayed holster callback requested kneeling"] call _check;
    ''')


def test_provider_going_prone_during_standing_transition_is_not_raised_by_main_entry():
    execute(setup() + r'''
        _stance="STAND";
        [_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        [(_state select 3)==-2,"test did not reach standing-transition stage"] call _check;
        _stance="PRONE"; _animation="amovppnemstpsnonwnondnon"; CBA_missionTime=10.6;
        _moves=[]; _positions=[];
        [_state select 5] call _poseTick;
        [(_state select 20) && {(_state select 2)=="ACM_ProneContinuous"},"main entry lost new prone posture"] call _check;
        [_positions isEqualTo ["DOWN"] && {_moves isEqualTo [[_medic,"ACM_ProneContinuous",1]]},
            "standing-transition callback raised newly prone provider"] call _check;
    ''')


@pytest.mark.parametrize('animation', ['ACM_ProneContinuous','AinvPpneMstpSnonWnonDnon_medicOther'])
def test_custom_prone_animation_preserves_entry_when_engine_stance_is_undefined(animation):
    execute(setup() + f'_stance="UNDEFINED";_animation="{animation}";' + r'''
        private _epoch=[_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        [_epoch>0 && {(_state select 20)} && {(_state select 2)=="ACM_ProneContinuous"},
            "undefined engine stance hid existing prone medical animation"] call _check;
        [_positions isEqualTo ["DOWN"] && {_moves isEqualTo [[_medic,"ACM_ProneContinuous",1]]},
            "undefined custom prone entry raised provider"] call _check;
        _animation="ACM_ProneContinuous";
        [_medic,"inspect",_epoch] call ACME_fnc_treatmentPoseStop;
        [((_moves select (count _moves-1)) select 1)=="AmovPpneMstpSnonWnonDnon",
            "undefined custom prone exit raised provider"] call _check;
    ''')


@pytest.mark.parametrize('stage', [-1,-2])
def test_deferred_entry_adopts_custom_prone_animation_with_undefined_stance(stage):
    execute(setup() + '_stance="STAND";' + ('_testPrepDelay=0.5;' if stage==-1 else '') + f'''
        [_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        [(_state select 3)=={stage},"test did not reach requested deferred stage"] call _check;
        _stance="UNDEFINED";_animation="ACM_ProneContinuous";CBA_missionTime=10.6;
        _moves=[];_positions=[];
        [_state select 5] call _poseTick;
        [(_state select 20) && {{(_state select 2)=="ACM_ProneContinuous"}},
            "deferred boundary failed to recognize custom prone animation"] call _check;
        [_positions isEqualTo ["DOWN"] && {{_moves isEqualTo [[_medic,"ACM_ProneContinuous",1]]}},
            "deferred boundary raised custom prone provider"] call _check;
    ''')


@pytest.mark.parametrize('animation', ['ACM_ProneContinuous','AmovPpneMstpSnonWnonDnon'])
def test_provider_mapper_recognizes_custom_prone_animation_with_undefined_stance(animation):
    execute(setup() + f'_stance="UNDEFINED";_animation="{animation}";' + r'''
        [([_medic,"ACME_ChestInspectWork"] call ACME_fnc_providerAnimation)=="ACM_ProneContinuous",
            "provider mapper ignored custom prone work"] call _check;
        [([_medic,"AmovPknlMstpSnonWnonDnon"] call ACME_fnc_providerAnimation)=="AmovPpneMstpSnonWnonDnon",
            "provider mapper chose crouched exit for custom prone work"] call _check;
    ''')


def test_matching_pose_stop_adopts_mid_action_custom_prone_without_captured_entry_flag():
    execute(setup() + r'''
        private _epoch=[_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable "ACME_treatmentPoseState";
        [!(_state select 20),"test unexpectedly started prone"] call _check;
        _animation=toLower (_state select 2);[_state select 5] call _poseTick;
        _stance="UNDEFINED";_animation="ACM_ProneContinuous";
        _moves=[];_positions=[];
        [_medic,"inspect",_epoch] call ACME_fnc_treatmentPoseStop;
        [_positions isEqualTo ["AUTO"] && {_moves isEqualTo [[_medic,"AmovPpneMstpSnonWnonDnon",1]]},
            "matching stop raised provider after mid-action custom prone change"] call _check;
        [count _waits==0,"matching stop queued crouch correction for current prone animation"] call _check;
        {[_x] call _deliver;} forEach +_speedWaits;
        [_speed==1,"matching stop failed to release animation rate"] call _check;
    ''')


def test_hard_roll_cancel_adopts_mid_action_custom_prone_without_blank_reset():
    cancel=pose_source('rollProviderCancel').replace('_medic switchMove "";','_blankResets=_blankResets+1;')
    execute(setup() + 'ACME_fnc_rollProviderCancel={' + cancel + '};' + r'''
        private _blankResets=0;
        private _epoch=[_medic,"roll",2.2,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable "ACME_treatmentPoseState";
        [!(_state select 20),"test unexpectedly started prone"] call _check;
        _medic setVariable ["ACME_rollProviderToken","cancel:roll"];
        _medic setVariable ["ACME_rollProviderSource","stethoscopeFlip"];
        _animation=toLower (_state select 2);[_state select 5] call _poseTick;
        _stance="UNDEFINED";_animation="ACM_ProneContinuous";
        _moves=[];_positions=[];_events=[];
        [([_medic,"stethoscopeFlip"] call ACME_fnc_rollProviderCancel),"matching roll cancellation was rejected"] call _check;
        [_positions isEqualTo ["AUTO"] && {_moves isEqualTo [[_medic,"AmovPpneMstpSnonWnonDnon",1]]},
            "hard roll cancel raised current custom prone provider"] call _check;
        [_blankResets==0 && {(_events findIf {(_x select 0)=="ace_common_switchMove"})==-1},
            "hard roll cancel issued blank reset despite recognized prone animation"] call _check;
        [(_medic getVariable "ACME_treatmentPoseState") isEqualTo [] && {_speed==1},
            "hard roll cancel retained work state or altered animation rate"] call _check;
    ''')


def test_old_prone_owner_and_stale_stop_cannot_clear_a_newer_action():
    execute(setup() + r'''
        _stance="PRONE";
        private _oldEpoch=[_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _old=+(_medic getVariable "ACME_treatmentPoseState");
        private _newEpoch=[_medic,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;
        private _new=+(_medic getVariable "ACME_treatmentPoseState");
        _moves=[]; _positions=[]; _events=[];
        [_old select 5] call _poseTick;
        [_medic,"inspect",_oldEpoch] call ACME_fnc_treatmentPoseStop;
        [(_medic getVariable "ACME_treatmentPoseState") isEqualTo _new,"stale prone owner cleared successor"] call _check;
        [count _moves==0 && {count _positions==0} && {count _events==0},"stale prone cleanup affected successor"] call _check;
    ''')


def test_prone_owner_locality_loss_releases_without_moving_a_remote_unit():
    execute(setup() + r'''
        _stance="PRONE";
        [_medic,"inspect",6,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=+(_medic getVariable "ACME_treatmentPoseState");
        _animation="acm_pronecontinuous"; _isLocal=false;
        _moves=[]; _positions=[]; _events=[];
        [_state select 5] call _poseTick;
        [(_medic getVariable "ACME_treatmentPoseState") isEqualTo [],"departed owner retained worker state"] call _check;
        [count _moves==0 && {count _positions==0} && {count _events==0},"departed owner animated or broadcast for remote provider"] call _check;
    ''')


def test_new_owner_releases_exact_remote_prone_hold_without_kneeling():
    execute(setup() + r'''
        _isLocal=false; _server=false; _client=8; _stance="PRONE";
        _medic setVariable ["ACME_treatmentPoseEpisode",[12,true]];
        [_medic,12,"hold","ACM_ProneContinuous",0,7] call ACME_fnc_treatmentPoseSync;
        private _id=(_medic getVariable "ACME_treatmentPoseRemote") select 2;
        _animation="acm_pronecontinuous"; _isLocal=true; _moves=[]; _positions=[];
        [_id] call _poseTick;
        [_moves isEqualTo [[_medic,"AmovPpneMstpSnonWnonDnon",1]],"ownership transfer raised prone provider"] call _check;
        [_speed==1 && {_id in _removed} && {count _positions==0},"ownership transfer retained hold or changed stance"] call _check;
    ''')


@pytest.mark.parametrize('after_treatment', [False,True])
def test_prone_menu_open_never_acquires_pose_even_after_treatment(after_treatment):
    execute(setup() + '_stance="PRONE";' + (
        '_medic setVariable ["ACME_menuPoseAfterTreatment",_patient];' if after_treatment else '') + r'''
        [!([_medic,_patient,_display] call ACME_fnc_menuPoseStart),"prone menu acquired pose"] call _check;
        [count _moves==0 && {count _positions==0} && {count _waits==0} && {count _handlers==0},
            "prone menu changed stance or scheduled theatre"] call _check;
    ''')


@pytest.mark.parametrize('after_treatment', [False,True])
def test_custom_prone_menu_open_with_undefined_stance_never_acquires_pose(after_treatment):
    execute(setup() + '_stance="UNDEFINED";_animation="ACM_ProneContinuous";' + (
        '_medic setVariable ["ACME_menuPoseAfterTreatment",_patient];' if after_treatment else '') + r'''
        [!([_medic,_patient,_display] call ACME_fnc_menuPoseStart),"undefined custom prone menu acquired pose"] call _check;
        [count _moves==0 && {count _positions==0} && {count _waits==0} && {count _handlers==0},
            "undefined custom prone menu scheduled crouch theatre"] call _check;
    ''')


@pytest.mark.parametrize('pending_stage', [0,1])
def test_queued_menu_callbacks_reject_new_custom_prone_with_undefined_stance(pending_stage):
    execute(setup() + r'''
        _stance="STAND"; _medic setVariable ["ACME_menuPoseAfterTreatment",_patient];
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
    ''' + ('[_waits select 0] call _deliver;' if pending_stage else '') + f'''
        _stance="UNDEFINED";_animation="ACM_ProneContinuous";
        _moves=[];_positions=[];
        [_waits select {pending_stage}] call _deliver;
        [count _moves==0 && {{count _positions==0}},"queued menu callback raised custom prone provider"] call _check;
    ''')


def test_menu_watchdog_releases_custom_prone_with_undefined_stance_into_prone_idle():
    execute(setup() + r'''
        _medic setVariable ["ACME_menuPoseAfterTreatment",_patient];
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        [_waits select 0] call _deliver;[_waits select 1] call _deliver;
        _stance="UNDEFINED";_animation="ACM_ProneContinuous";
        _moves=[];_positions=[];
        [0] call _poseTick;
        [_positions isEqualTo ["AUTO"] && {_moves isEqualTo [[_medic,"AmovPpneMstpSnonWnonDnon",1]]},
            "menu watchdog raised provider whose prone animation reports undefined stance"] call _check;
        [(_medic getVariable "ACME_menuPose") isEqualTo [],"undefined stance retained menu pose"] call _check;
    ''')


def test_existing_generic_crouch_reporting_undefined_keeps_menu_lifecycle():
    execute(setup() + r'''
        _stance="UNDEFINED";_animation="ACM_GenericContinuous";
        _medic setVariable ["ACME_menuPoseAfterTreatment",_patient];
        [([_medic,_patient,_display] call ACME_fnc_menuPoseStart),
            "supported generic crouch with undefined stance was rejected"] call _check;
        private _state=+(_medic getVariable "ACME_menuPose");
        [_waits select 0] call _deliver;[_waits select 1] call _deliver;
        [_moves isEqualTo [[_medic,"ACM_GenericContinuous",1]],
            "generic crouch changed into unrelated work or stance transition"] call _check;
        [0] call _poseTick;
        [(_medic getVariable "ACME_menuPose") isEqualTo _state && {count _moves==1},
            "menu watchdog retired valid generic crouch because stance was undefined"] call _check;
    ''')


@pytest.mark.parametrize('stance', ['STAND','CROUCH','PRONE'])
def test_disabled_menu_setting_does_not_start_any_menu_theatre(stance):
    execute(setup() + f'_stance="{stance}";' + r'''
        missionNamespace setVariable ["ACME_menuPoseEnabled",false];
        _medic setVariable ["ACME_menuPoseAfterTreatment",_patient];
        [!([_medic,_patient,_display] call ACME_fnc_menuPoseStart),"disabled setting acquired menu pose"] call _check;
        [count _moves==0 && {count _positions==0} && {count _waits==0} && {count _handlers==0},
            "disabled setting scheduled menu posture work"] call _check;
    ''')


@pytest.mark.parametrize('change', ['_stance="PRONE";', 'missionNamespace setVariable ["ACME_menuPoseEnabled",false];'])
@pytest.mark.parametrize('pending_stage', [0,1])
def test_queued_menu_callbacks_recheck_posture_and_setting(change,pending_stage):
    execute(setup() + r'''
        _stance="STAND"; _medic setVariable ["ACME_menuPoseAfterTreatment",_patient];
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
    ''' + ('[_waits select 0] call _deliver;' if pending_stage else '') + change + f'''
        _moves=[]; _positions=[];
        [_waits select {pending_stage}] call _deliver;
        [count _moves==0 && {{count _positions==0}},"queued menu callback ignored current prone/disabled state"] call _check;
    ''')


def test_active_menu_watchdog_releases_into_prone_without_a_kneeling_exit():
    execute(setup() + r'''
        _medic setVariable ["ACME_menuPoseAfterTreatment",_patient];
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        [_waits select 0] call _deliver; [_waits select 1] call _deliver;
        _stance="PRONE"; _animation="amovppnemstpsnonwnondnon";
        _moves=[]; _positions=[];
        [0] call _poseTick;
        [_positions isEqualTo ["AUTO"] && {_moves isEqualTo [[_medic,"AmovPpneMstpSnonWnonDnon",1]]},
            "menu watchdog raised a newly prone provider"] call _check;
        [(_medic getVariable "ACME_menuPose") isEqualTo [],"menu watchdog retained menu pose"] call _check;
        [_waits select 2] call _deliver;
        [_speed==1,"prone menu exit leaked animation rate"] call _check;
    ''')


def setting_expression():
    source = (ROOT/'addons/acm_extended/XEH_preInit.sqf').read_text()
    tokens = lex(source); pairs = matching(tokens)
    index = next(i for i,t in enumerate(tokens) if t.kind=='string' and t.value=='ACME_menuPoseEnabled')
    assert tokens[index-1].value=='['
    return source[tokens[index-1].offset:tokens[pairs[index-1]].offset+1]


def test_actual_personal_checkbox_callback_releases_existing_menu_pose():
    execute(setup() + 'private _cSys="ACM Extended";private _setting=' + adapt(setting_expression()) + r''';
        [(_setting select 1)=="CHECKBOX" && {(_setting select 4)} && {(_setting select 5)==2},
            "menu option is not enabled by default/personal non-overridable checkbox"] call _check;
        _medic setVariable ["ACME_menuPoseAfterTreatment",_patient];
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        [_waits select 0] call _deliver; [_waits select 1] call _deliver;
        missionNamespace setVariable ["ACME_menuPoseEnabled",false];
        false call (_setting select 6);
        [(_medic getVariable "ACME_menuPose") isEqualTo [] && {(_positions select (count _positions-1))=="AUTO"},
            "disabling option did not release live menu stance"] call _check;
        [_waits select 2] call _deliver;
        [_speed==1,"disabling option left menu speed override"] call _check;
    ''')


def test_provider_resolver_is_not_called_for_patient_animation_targets():
    calls = []
    for path in (ROOT/'addons').rglob('*.sqf'):
        source = path.read_text()
        if 'call ACME_fnc_providerAnimation' not in source:
            continue
        tokens=lex(source); pairs=matching(tokens)
        for index, token in enumerate(tokens):
            if token.kind=='ident' and token.value=='ACME_fnc_providerAnimation' and tokens[index-1].value=='call':
                end=index-2
                assert tokens[end].value==']',path
                args=split_args(tokens,pairs[end]+1,end,pairs)
                first=[t.value for t in args[0]]
                calls.append((str(path.relative_to(ROOT)),first))
                assert first in [['_medic'],['_m'],['_provider'],['_unit'],['_u']],(path,first)
    assert calls


@pytest.mark.parametrize('check_breathing', [False,True])
def test_carrier_provider_ready_probe_accepts_the_actual_prone_main(check_breathing):
    code=pose_source('chestAccessVestProvider').replace('animationState _m','_animation').replace('serverTime','CBA_missionTime')
    execute(setup() + 'ACME_fnc_chestAccessVestProvider={' + code + '};' + r'''
        _stance="PRONE";
        private _condition=[];
        CBA_fnc_waitUntilAndExecute={_condition=_this;};
    ''' + ('_medic setVariable ["ACME_chestAccess_treatment",[_patient,"checkbreathing"]];' if check_breathing else '') + r'''
        private _epoch=[_medic,_patient,"start",false,"vest:test",""] call ACME_fnc_chestAccessVestProvider;
        private _state=_medic getVariable "ACME_treatmentPoseState";
        _animation="acm_pronecontinuous";
        [_state select 5] call _poseTick; [_state select 5] call _poseTick;
        [(_condition select 2) call (_condition select 0),"prone main never satisfied carrier ready probe"] call _check;
        (_condition select 2) call (_condition select 1);
        [(_medic getVariable "ACME_chestAccessProviderReady") isEqualTo ["vest:test",CBA_missionTime],
            "carrier readiness fell back to timeout despite supported prone hold"] call _check;
        [(_positions find "MIDDLE")==-1,"carrier preparation raised provider"] call _check;
    ''')


@pytest.mark.parametrize('name', ['chestSealFlipTick','stethoscopeFlipTick'])
def test_flip_waiters_start_patient_roll_from_the_actual_supported_prone_main(name):
    source=flip_setup(name,'back').replace('private _ep=[_medic,"roll"','_stance="PRONE";private _ep=[_medic,"roll"')
    index=9 if name=='chestSealFlipTick' else 8
    execute(source + f'_flipArgs set [{index},-1];' + r'''
        [_flipArgs,99] call _flipTick;
        [count _rolls==1 && {((_rolls select 0) select 1)=="back"},
            "prone roll entry waited for unavailable kneeling medic4"] call _check;
        [(_positions find "MIDDLE")==-1,"flip waiter raised provider"] call _check;
    ''')


def test_pre_scope_roll_completes_after_patient_motion_even_when_prone_hold_has_retired():
    execute(setup() + flip_tick('stethoscopeEntryFlipTick') + r'''
        _stance="PRONE";
        private _opened=[]; private _rolls=[];
        ACM_breathing_fnc_useStethoscope={_opened pushBack _this;};
        ACME_fnc_chestSealCanPhysicalRoll={true};
        ACME_fnc_chestSealRoll={_rolls pushBack _this;};
        private _epoch=[_medic,"roll",2.2,_patient] call ACME_fnc_treatmentPoseStart;
        private _state=_medic getVariable "ACME_treatmentPoseState";
        private _id=_state select 5;
        _medic setVariable ["ACME_rollProviderToken","prone:roll"];
        _animation="acm_pronecontinuous";
        private _args=[_medic,_patient,"body",_epoch,"prone:roll",1.23,-1,15.5];
        [_args,99] call _flipTick;
        [count _rolls==1,"prone entry never started patient roll"] call _check;
        [_id] call _poseTick; [_id] call _poseTick;
        CBA_missionTime=10.3; [_id] call _poseTick;
        [(_medic getVariable ["ACME_rollProviderCompletedEpoch",-1])==_epoch,
            "test did not complete the actual prone provider roll"] call _check;
        _nowTime=11.4;
        [_args,99] call _flipTick;
        [count _opened==1 && {99 in _removed},"finished prone entry waited for the failure deadline"] call _check;
    ''')
