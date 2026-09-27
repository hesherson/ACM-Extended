"""Execute first-contact, true GUI close, rejected handoff and interpolation dispatch."""
import re
from pathlib import Path

import pytest

from test_b156_menu_pose import setup
from test_menu_death_lifecycle import adapt, core, execute

ROOT = Path(__file__).resolve().parents[3]


def test_first_contact_keeps_weapon_and_only_uses_native_kneel():
    execute(setup() + '''
        _medic setVariable ["ACME_menuPoseAfterTreatment",objNull];
        _menuStance="STAND"; _primaryWeapon="rifle"; _currentWeapon="rifle";
        [_medic,_patient,_display] call (_runtimeHandlers get "ace_medicalMenuOpened");
        [_moves isEqualTo ["AmovPknlMstpSlowWrflDnon"] && {_priorities isEqualTo [0]},"first contact did not preserve the native weapon kneel"] call _check;
        [count _waits==0 && {_testAnimationSpeed==1} && {_currentWeapon=="rifle"},"first contact started generic prep or changed animation rate/weapon"] call _check;
        [_display] call (_display getVariable "Unload");
        [_stanceFreed && {count _moves==1} && {_testAnimationSpeed==1},"first-contact close forced an empty-handed exit or kept stance"] call _check;
    ''')


def test_started_care_enables_only_that_patient_until_manual_menu_close():
    execute(setup() + '''
        _medic setVariable ["ACME_menuPoseAfterTreatment",objNull];
        [_medic,_patient] call (_runtimeHandlers get "ace_treatmentStarted");
        [_medic,_patient,_display] call (_runtimeHandlers get "ace_medicalMenuOpened");
        0 call _runWait; 1 call _runWait;
        [_moves isEqualTo ["ACM_GenericContinuous"] && {_priorities isEqualTo [1]},"actual care did not enable interpolated generic menu"] call _check;
        [_display] call (_display getVariable "Unload");
        [(_medic getVariable "ACME_menuPoseAfterTreatment") isEqualTo objNull,"manual close retained care eligibility"] call _check;
        [_medic,_patient,profileNamespace] call ACME_fnc_menuPoseStart;
        [count _waits==3,"fresh contact inherited the previous generic menu"] call _check;
    ''')


def test_changing_patient_does_not_carry_generic_eligibility():
    execute(setup() + '''
        private _other=missionNamespace;
        [_medic,_other,_display] call ACME_fnc_menuPoseStart;
        [count _waits==0 && {count _moves==0},"different patient inherited generic eligibility"] call _check;
        [(_medic getVariable "ACME_menuPoseAfterTreatment") isEqualTo objNull,"different patient retained previous eligibility"] call _check;
    ''')


def test_watchdog_recovers_missed_unload_without_replaying_exit():
    execute(setup() + '''
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        0 call _runWait; 1 call _runWait;
        private _h=_handlers select 0;
        (_h select 1) set [2,objNull];
        [_h select 1,0] call (_h select 0);
        [_stanceFreed && {(_medic getVariable "ACME_menuPose") isEqualTo []},"destroyed display retained pose owner"] call _check;
        [_moves isEqualTo ["ACM_GenericContinuous","AmovPknlMstpSnonWnonDnon"],"missed Unload did not release generic pose"] call _check;
        [_display] call (_display getVariable "Unload");
        [_h select 1,0] call (_h select 0);
        [count _moves==2 && {!((_handlers select 0) select 2)},"duplicate close replayed exit or watchdog persisted"] call _check;
    ''')


def test_silent_failed_handoff_cannot_leave_an_unowned_continuous_pose():
    execute(setup() + '''
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        0 call _runWait; 1 call _runWait;
        [_medic,true] call ACME_fnc_menuPoseStop;
        private _h=_handlers select 0;
        [_h select 1,0] call (_h select 0);
        [_stanceFreed && {count _moves==2},"rejected takeover left unowned generic pose"] call _check;
        2 call _runWait;
        [_testAnimationSpeed==1,"rejected takeover left accelerated rate"] call _check;
    ''')


def test_successful_handoff_retires_old_watchdog_without_changing_new_pose():
    execute(setup() + '''
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        0 call _runWait; 1 call _runWait;
        [_medic,true] call ACME_fnc_menuPoseStop;
        _medic setVariable ["ACME_treatmentPoseState",[2,"inspect"]];
        _testAnimationSpeed=0;
        private _h=_handlers select 0;
        [_h select 1,0] call (_h select 0);
        [!((_handlers select 0) select 2) && {count _moves==1} && {_testAnimationSpeed==0},"retired menu reset frozen successor"] call _check;
        [(_medic getVariable "ACME_menuPoseAfterTreatment") isEqualTo _patient,"handoff lost care eligibility before reopen"] call _check;
    ''')


def test_stale_ace_end_hint_does_not_trap_closed_menu_but_native_reservation_does():
    execute(setup() + '''
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        0 call _runWait; 1 call _runWait;
        _medic setVariable ["ace_medical_treatment_endInAnim","AmovPknlMstpSnonWnonDnon"];
        _medic setVariable ["ACME_nativeTreatmentRate",[1,_patient,"head","x",0]];
        [_medic,false,_medic getVariable "ACME_menuPoseEpoch"] call ACME_fnc_menuPoseStop;
        [!_stanceFreed && {count _moves==1},"close overrode real native treatment startup"] call _check;
        _medic setVariable ["ACME_nativeTreatmentRate",[]];
        private _h=_handlers select 0;
        [_h select 1,0] call (_h select 0);
        [_stanceFreed && {count _moves==2},"orphan ACE end hint permanently blocked menu exit"] call _check;
        2 call _runWait;
        [_testAnimationSpeed==1,"stale ACE end hint blocked final speed reset"] call _check;
    ''')


def test_actual_gui_close_releases_before_runtime_unload_even_if_other_handler_is_missing():
    source = adapt((ROOT/'addons/gui/overrides/fnc_onMenuClose.sqf').read_text(), 'gui')
    execute(setup() + 'private _actualClose={' + source + '};' + '''
        CBA_fnc_removePerFrameHandler={private _id=if (_this isEqualType 0) then {_this} else {_this select 0}; (_handlers select _id) set [2,false];};
        ace_interact_menu_menuBackground=0;
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        ace_medical_gui_menuPFH=0;
        0 call _runWait; 1 call _runWait;
        [_display,0] call _actualClose;
        [_stanceFreed && {count _moves==2} && {ace_medical_gui_menuPFH == -1},"actual GUI close omitted pose release"] call _check;
        [_medic,false,_medic getVariable "ACME_menuPoseEpoch"] call ACME_fnc_menuPoseStop;
        [count _moves==2,"late runtime Unload replayed GUI exit"] call _check;
    ''')


def ace_dispatch_fixture():
    # Execute supplied ACE's exact priority switch; engine animationState intentionally
    # stays unchanged while targetEvent is queued, reproducing priority-2's switchMove.
    paths=list((ROOT.parent/'references').glob('ACE3-master/**/addons/common/functions/fnc_doAnimation.sqf'))
    if len(paths)!=1:
        pytest.skip("supplied ACE3 source reference required for exact dependency dispatch")
    source=paths[0].read_text()
    source=re.sub(r'^\s*TRACE_\d.*$', '', source, flags=re.M)
    source=source.replace('objectParent _unit','objNull').replace('animationState _unit','"AmovPknlMstpSnonWnonDnon"')
    source=adapt(source,'common').replace('ACM_common_', 'ace_common_')
    return 'ace_common_fnc_doAnimation={'+source+'}; ACME_fnc_doAnim=ace_common_fnc_doAnimation;'


def test_generic_entry_dispatch_never_requests_switchmove_on_delayed_owner_event():
    execute(setup()+ace_dispatch_fixture()+'''
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        0 call _runWait; 1 call _runWait;
        private _animationEvents=_events select {(_x select 0) in ["ace_common_playMoveNow","ace_common_switchMove"]};
        [count _animationEvents==1 && {((_animationEvents select 0) select 0)=="ace_common_playMoveNow"},"generic menu entry fell back to an instantaneous switchMove"] call _check;
    ''')


def test_native_continuous_entry_uses_interpolated_owner_dispatch():
    execute(setup()+ace_dispatch_fixture()+'ACM_core_fnc_beginContinuousAction={'+core('beginContinuousAction')+'};'+'''
        [[_medic,_patient,"head"],{},{},{}] call ACM_core_fnc_beginContinuousAction;
        private _animationEvents=_events select {(_x select 0) in ["ace_common_playMoveNow","ace_common_switchMove"]};
        [count _animationEvents==1 && {((_animationEvents select 0) select 0)=="ace_common_playMoveNow"},"continuous action snapped generic entry"] call _check;
        [(_medic getVariable "ACME_menuPoseAfterTreatment") isEqualTo _patient,"accepted continuous care did not enable reopen eligibility"] call _check;
    ''')


def test_switching_from_generic_to_new_patient_releases_inherited_loop_and_rate():
    execute(setup()+'''
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        0 call _runWait; 1 call _runWait;
        _menuAnimation="ACM_GenericContinuous";
        [_medic,missionNamespace,profileNamespace] call ACME_fnc_menuPoseStart;
        [_moves isEqualTo ["ACM_GenericContinuous","AmovPknlMstpSnonWnonDnon"] && {_priorities isEqualTo [1,1]},"new patient's first-contact menu inherited generic loop"] call _check;
        [_testAnimationSpeed==1,"new patient inherited generic animation rate"] call _check;
        [_medic,false,_medic getVariable "ACME_menuPoseEpoch"] call ACME_fnc_menuPoseStop;
        [_stanceFreed && {count _moves==2},"new patient close left stance or replayed generic exit"] call _check;
    ''')


def test_next_frame_pose_completion_restores_eligibility_only_for_matching_started_care():
    execute(setup()+'''
        _medic setVariable ["ACME_menuPoseAfterTreatment",objNull];
        [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
        [_medic,_patient,"body","FieldDressing"] call (_runtimeHandlers get "ace_treatmentStarted");
        [_medic,false,_medic getVariable "ACME_menuPoseEpoch"] call ACME_fnc_menuPoseStop;
        [_medic,missionNamespace,"body","FieldDressing"] call (_runtimeHandlers get "ace_treatmentSucceded");
        [(_medic getVariable "ACME_menuPoseAfterTreatment") isEqualTo objNull,"unmatched completion enabled generic care"] call _check;
        [_medic,_patient,"body","FieldDressing"] call (_runtimeHandlers get "ace_treatmentSucceded");
        [(_medic getVariable "ACME_menuPoseAfterTreatment") isEqualTo _patient,"completed next-frame treatment lost eligibility"] call _check;
    ''')


def test_accepted_physical_preparation_marks_care_and_accepts_generic_empty_hands():
    from test_historical_pose_lifecycle import setup as pose_setup
    execute(pose_setup()+'''
        _animation="acm_genericcontinuous"; _testPrepDelay=.2;
        [_medic,"chestAccess",-1,_patient] call ACME_fnc_treatmentPoseStart;
        [(_medic getVariable "ACME_menuPoseAfterTreatment") isEqualTo _patient,"accepted physical preparation did not enable care eligibility"] call _check;
        private _state=_medic getVariable "ACME_treatmentPoseState";
        CBA_missionTime=10.3; [_state select 5] call _poseTick;
        [(_state select 3)==1,"native continuous empty hands remained blocked in weapon preparation"] call _check;
    ''')
