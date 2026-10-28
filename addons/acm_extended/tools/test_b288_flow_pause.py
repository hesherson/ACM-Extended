"""Execute owner-local temporary mixing pauses and reordered UI cleanup."""
import re

import pytest

from test_b279_transfusion_ui import flow_setup
from test_b156_procedure_supplies import primitives
from test_menu_death_lifecycle import adapt, execute, read


def fixture():
    code=read('transfusionMixFlowLocal')
    code=code.replace('canSuspend','false').replace('serverTime','_nowTime')
    code=re.sub(r'finite (_\w+)',r'(\1 isEqualType 0)',code)
    code=re.sub(r'values (_\w+)',r'(keys \1 apply {\1 get _x})',code)
    return flow_setup()+r'''
        private _epochCurrent=4;private _generation=1;
        ACME_fnc_clinicalEpoch={_epochCurrent};
        ACME_fnc_medicationLineIdentity={[_generation]};
        _medic setVariable ["ACME_equipmentKitEpoch",0];
        _medic setVariable ["ACME_providerLocalityEpoch",0];
        private _bag=["Saline",500,1,1,true,-1,500,-1,"bag-one"];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[_bag]]]];
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    '''+'ACME_fnc_transfusionMixFlowLocal={'+primitives(adapt(code))+'};'+r'''
        ACME_fnc_ownerDispatch={_commands pushBack _this;(_this select 2) call ACME_fnc_transfusionMixFlowLocal;};
        private _pause=["pause",_patient,_medic,"mix-flow:7:10:1","leftarm",true,1,4,"bag-one",0,0];
        private _resume=+_pause;_resume set [0,"resume"];
        private _readFlow={((_patient getVariable ["ACM_circulation_FluidBagsFlow_IV",[[1,1,1],[1,1,1],[1,1,1]]]) select 2) select 1};
    '''


def test_pause_and_resume_edit_latest_owner_arrays_preserving_other_site_changes():
    execute(fixture()+r'''
        _pause call ACME_fnc_transfusionMixFlowLocal;
        [call _readFlow==0 && {count _publications==1},"owner pause did not stop exact access"] call _check;
        private _flow=+(_patient getVariable "ACM_circulation_FluidBagsFlow_IV");
        _flow set [0,[0,1,0]];_patient setVariable ["ACM_circulation_FluidBagsFlow_IV",_flow];
        _resume call ACME_fnc_transfusionMixFlowLocal;
        [call _readFlow==1 && {((_patient getVariable "ACM_circulation_FluidBagsFlow_IV") select 0) isEqualTo [0,1,0]},"cleanup overwrote latest unrelated flow"] call _check;
        _pause call ACME_fnc_transfusionMixFlowLocal;_resume call ACME_fnc_transfusionMixFlowLocal;
        [count _publications==2,"closed request replayed old flow mutation"] call _check;
    ''')


def test_resume_before_pause_tombstones_delayed_menu_request():
    execute(fixture()+r'''
        _resume call ACME_fnc_transfusionMixFlowLocal;
        _pause call ACME_fnc_transfusionMixFlowLocal;
        [count _publications==0,"reordered close left a newly paused line"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_epochCurrent=5;',
    '_generation=2;',
    '_patient setVariable ["ACM_circulation_IV_Bags",createHashMap];',
    '_bag set [8,"replacement-bag"];',
])
def test_cleanup_cannot_resume_changed_patient_line_or_bag(change):
    execute(fixture()+r'''
        _pause call ACME_fnc_transfusionMixFlowLocal;
    '''+change+r'''
        _resume call ACME_fnc_transfusionMixFlowLocal;
        [count _publications==1,"retired bag/access/patient was resumed"] call _check;
    ''')


def test_manual_toggle_retires_temporary_ownership_even_after_stop_start_cycle():
    execute(fixture()+r'''
        _pause call ACME_fnc_transfusionMixFlowLocal;
        [_patient,"leftarm",true,1,4,_medic] call ACME_fnc_transfusionFlowToggleCommit;
        [_patient,"leftarm",true,1,4,_medic] call ACME_fnc_transfusionFlowToggleCommit;
        [call _readFlow==0,"manual clinician Stop did not remain stopped"] call _check;
        _resume call ACME_fnc_transfusionMixFlowLocal;
        [call _readFlow==0 && {count _publications==3},"old menu close overwrote newer clinician Stop"] call _check;
    ''')


def test_concurrent_mixing_menus_keep_pause_until_last_exact_lease_closes():
    execute(fixture()+r'''
        _pause call ACME_fnc_transfusionMixFlowLocal;
        private _second=+_pause;_second set [3,"mix-flow:7:10:2"];
        _second call ACME_fnc_transfusionMixFlowLocal;
        _resume call ACME_fnc_transfusionMixFlowLocal;
        [call _readFlow==0 && {count _publications==1},"first close resumed another open mixing episode"] call _check;
        _second set [0,"resume"];_second call ACME_fnc_transfusionMixFlowLocal;
        [call _readFlow==1 && {count _publications==2},"last close lost original pre-pause flow"] call _check;
    ''')


@pytest.mark.parametrize('field', ['ACME_equipmentKitEpoch','ACME_providerLocalityEpoch'])
def test_pause_from_retired_provider_period_never_changes_flow(field):
    execute(fixture()+f'_medic setVariable ["{field}",1];'+r'''
        _pause call ACME_fnc_transfusionMixFlowLocal;
        [count _publications==0,"retired provider input paused patient flow"] call _check;
    ''')


def test_orphaned_provider_pause_expires_but_current_open_menu_renews_watchdog():
    execute(fixture()+r'''
        _medic setVariable ["ACME_infusionMixFlowInput",["mix-flow:7:10:1",_patient,4]];
        _pause call ACME_fnc_transfusionMixFlowLocal;
        private _watch=+(_waits select 0);(_watch select 1) call (_watch select 0);
        [call _readFlow==0 && {count _waits==2},"watchdog resumed a current mixing menu"] call _check;
        _medic setVariable ["ACME_infusionMixFlowInput",[]];
        _watch=+(_waits select 1);(_watch select 1) call (_watch select 0);
        [call _readFlow==1 && {count _publications==2},"orphan pause remained after confirmed input retirement"] call _check;
    ''')


def test_legacy_close_snapshot_is_inert_and_current_close_uses_owner_request():
    code=adapt(read('restorePausedFlow'))
    execute(fixture()+'ACME_fnc_restorePausedFlow={'+code+'};'+r'''
        ACME_infusion_pendingPausedFlow=[_patient,2,true,1,1];
        call ACME_fnc_restorePausedFlow;
        [count _commands==0 && {count _publications==0},"legacy stale array authorized remote flow write"] call _check;
        _pause call ACME_fnc_transfusionMixFlowLocal;
        ACME_infusion_pendingPausedFlow=+_pause;
        call ACME_fnc_restorePausedFlow;
        [call _readFlow==1 && {(_commands select 0 select 1)=="transfusionMixFlow"},"close did not resume through owner authority"] call _check;
    ''')


def test_io_pause_and_close_preserve_fractional_flow_and_other_body_parts():
    execute(fixture()+r'''
        _bag set [3,-1];_bag set [4,false];
        _pause set [5,false];_pause set [6,-1];
        _resume=+_pause;_resume set [0,"resume"];
        _patient setVariable ["ACM_circulation_FluidBagsFlow_IO",[1,0,.75,1,0,1]];
        _pause call ACME_fnc_transfusionMixFlowLocal;
        [(_patient getVariable "ACM_circulation_FluidBagsFlow_IO") isEqualTo [1,0,0,1,0,1],"IO pause changed wrong access or failed"] call _check;
        _resume call ACME_fnc_transfusionMixFlowLocal;
        [(_patient getVariable "ACM_circulation_FluidBagsFlow_IO") isEqualTo [1,0,.75,1,0,1],"IO close changed prior clamp setting or unrelated body parts"] call _check;
    ''')


def test_closed_lease_pruning_never_reopens_a_late_pause_request():
    execute(fixture()+r'''
        _pause call ACME_fnc_transfusionMixFlowLocal;
        _resume call ACME_fnc_transfusionMixFlowLocal;
        private _oldPause=+_pause;
        _nowTime=23;_pause set [3,"mix-flow:7:23:2"];
        _pause call ACME_fnc_transfusionMixFlowLocal;
        private _leases=_patient getVariable ["ACME_infusionMixFlowLeases",createHashMap];
        [count _leases==1 && {!("mix-flow:7:10:1" in _leases)},"expired closed request remained in replicated history"]call _check;
        private _before=count _publications;
        _oldPause call ACME_fnc_transfusionMixFlowLocal;
        [count _publications==_before && {call _readFlow==0},"forgotten request reopened/restored old flow"]call _check;
    ''')


def test_long_running_mixing_custody_has_bounded_history_without_losing_flow():
    execute(fixture()+r'''
        for "_i" from 1 to 256 do {
            _nowTime=10+13*_i;
            _pause set [3,format ["mix-flow:7:%1:%2",_nowTime,_i]];
            _resume=+_pause;_resume set [0,"resume"];
            _pause call ACME_fnc_transfusionMixFlowLocal;
            _resume call ACME_fnc_transfusionMixFlowLocal;
        };
        [count (_patient getVariable ["ACME_infusionMixFlowLeases",createHashMap])==1,"long mission accumulated closed request history"]call _check;
        [call _readFlow==1 && {count _publications==512},"bounded history lost a pause/restore decision"]call _check;
    ''')


def test_many_reordered_closes_cannot_grow_the_replicated_map_without_limit():
    execute(fixture()+r'''
        for "_i" from 1 to 300 do {
            _resume set[3,format ["mix-flow:7:10:%1",_i]];
            _resume call ACME_fnc_transfusionMixFlowLocal;
        };
        [count (_patient getVariable ["ACME_infusionMixFlowLeases",createHashMap])==128,"new-request replay fence failed its hard bound"]call _check;
        [count _publications==0,"reordered closes changed patient flow"]call _check;
        _nowTime=23;_pause set[3,"mix-flow:7:23:301"];
        [_pause call ACME_fnc_transfusionMixFlowLocal,"expired closed-request capacity was never recovered"]call _check;
    ''')


@pytest.mark.parametrize('request_id',[
    'mix-flow:7:0:1', 'mix-flow:7:15:1', 'mix-flow:7:10:0', 'old-opaque-request',
])
def test_unknown_expired_future_or_malformed_pause_is_inert(request_id):
    execute(fixture()+f'_pause set[3,"{request_id}"];'+r'''
        _nowTime=12;
        _pause call ACME_fnc_transfusionMixFlowLocal;
        [count _publications==0 && {count (_patient getVariable ["ACME_infusionMixFlowLeases",createHashMap])==0},"invalid request mutated or grew owner state"]call _check;
    ''')


def test_long_open_current_pause_can_close_after_new_request_window_expires():
    execute(fixture()+r'''
        _pause call ACME_fnc_transfusionMixFlowLocal;
        _nowTime=1000;
        _resume call ACME_fnc_transfusionMixFlowLocal;
        [call _readFlow==1 && {count _publications==2},"long-lived active lease lost its cleanup authority"]call _check;
    ''')
