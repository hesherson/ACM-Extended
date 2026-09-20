"""Execute BVM startup through the real continuous action controller."""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, core, execute


def breathing(name):
    source = (ROOT / 'addons/breathing/functions' / f'fnc_{name}.sqf').read_text()
    source = source.replace('_medic distance2D _patient', '_distance')
    source = source.replace('GET_AIRWAYSTATE(_patient)', '1')
    source = re.sub(r'alive (\(_patient getVariable \[[^;\n]+?\]\))', r'(\1 isNotEqualTo objNull)', source)
    source = re.sub(r'playSound3D \[[^;]+;', '_squeezes = _squeezes + 1;', source)
    source = adapt(source, 'breathing')
    return source


def setup():
    code = '''
        private _squeezes = 0;
        private _cprActive = false;
        private _patientAwake = false;
        ace_common_fnc_isAwake = {
            private _unit = if (_this isEqualType []) then {_this select 0} else {_this};
            if (_unit isEqualTo _patient) then {_patientAwake} else {!_unconscious}
        };
        ace_interaction_fnc_hideMouseHint = {};
        ACM_core_fnc_cprActive = {_cprActive};
        ACM_core_fnc_bvmActive = {((_this select 0) getVariable ["ACM_breathing_BVM_provider",objNull]) isNotEqualTo objNull};
        ACM_circulation_SwapToBVM = false;
        ACM_breathing_fnc_useOxygenTankReserve = {true};
    '''
    code += 'ACM_core_fnc_beginContinuousAction = {' + core('beginContinuousAction') + '};'
    for name in ('bvmSessionValid', 'bvmRelease', 'bvmCleanupLocal', 'canUseBVM', 'useBVM'):
        code += f'ACM_breathing_fnc_{name} = {{' + breathing(name) + '};'
    return code


@pytest.mark.parametrize("oxygen,portable", [(False, False), (True, False), (True, True)])
@pytest.mark.parametrize("cpr", [False, True])
def test_startup_survives_first_frames_and_delivers_breaths(oxygen, portable, cpr):
    execute(setup() + f"_cprActive = {str(cpr).lower()}; private _oxygen = {str(oxygen).lower()}; private _portable = {str(portable).lower()};" + '''
        [_medic,_patient,_oxygen,_portable] call ACM_breathing_fnc_useBVM;
        [ACM_core_ContinuousAction_Active,"startup rejected"] call _check;
        for "_i" from 1 to 4 do {call _tick;};
        [ACM_core_ContinuousAction_Active,"BVM cancelled on first frames"] call _check;
        CBA_missionTime = 13; call _tick;
        CBA_missionTime = 20; call _tick;
        [_squeezes == 2,"BVM did not deliver breaths"] call _check;
        [(_patient getVariable ["ACM_breathing_BVM_lastBreath",-1]) == 20,"breath was not recorded"] call _check;
    ''')


def completion_setup():
    source = (ROOT / 'addons/acm_extended/functions/fn_registerProviderStanceReleaseRuntime.sqf').read_text()
    source = re.sub(r'objectParent _m\b', 'objNull', source).replace('isPlayer _patient', 'false').replace('_m setUnitPos "AUTO";', '_stanceFreed = true;')
    return '''
        private _completionEvents = [];
        CBA_fnc_addEventHandler = {_completionEvents pushBack _this;};
        CBA_fnc_localEvent = {if ((_this select 0) == "ACM_core_openMedicalMenu") then {_dialog = true;};};
    ''' + adapt(source) + '''
        private _completed = {
            private _args = [_medic,_patient,"head",_this];
            {_args call (_x select 1);} forEach (_completionEvents select {(_x select 0) == "ace_treatmentSucceded"});
        };
        private _finishWaits = {
            private _pending = +_waits; _waits = [];
            {(_x select 1) call (_x select 0);} forEach _pending;
        };
        _medic setVariable ["ACME_DP_Active",true];
        _medic setVariable ["ACME_DP_PoseToken",1];
        _medic setVariable ["ACME_DP_Patient",_patient];
        _medic setVariable ["ACME_DP_Paused",true];
        _medic setVariable ["ACME_DP_PauseTreatmentClass","usebvm"];
        _medic setVariable ["ACME_DP_TreatmentBusy",true];
    '''


def test_direct_pressure_completion_does_not_reopen_menu_and_cancel_bvm():
    execute(setup() + completion_setup() + '''
        [_medic,_patient] call ACM_breathing_fnc_useBVM;
        "UseBVM" call _completed;
        call _finishWaits;
        call _tick;
        [!_dialog,"treatment completion reopened medical menu over BVM"] call _check;
        [ACM_core_ContinuousAction_Active,"DP completion cancelled new BVM"] call _check;
    ''')



def test_queued_completion_from_previous_treatment_cannot_cancel_new_bvm():
    execute(setup() + completion_setup() + '''
        "FieldDressing" call _completed;
        [count _waits > 0,"no delayed completion callback captured"] call _check;
        [_medic,_patient] call ACM_breathing_fnc_useBVM;
        call _finishWaits; call _tick;
        [!_dialog && {ACM_core_ContinuousAction_Active},"old completion cancelled new BVM"] call _check;
    ''')


def test_ordinary_treatment_still_reopens_direct_pressure_menu():
    execute(setup() + completion_setup() + '''
        "FieldDressing" call _completed;
        call _finishWaits;
        [_dialog,"ordinary treatment did not reopen medical menu"] call _check;
        [!(_medic getVariable ["ACME_DP_TreatmentBusy",true]),"ordinary completion retained busy state"] call _check;
    ''')


def test_bvm_cancel_releases_direct_pressure_completion_and_allows_restart():
    execute(setup() + completion_setup() + '''
        [_medic,_patient] call ACM_breathing_fnc_useBVM;
        "UseBVM" call _completed;
        private _cancel = (_keys select {(_x select 0) == ACM_breathing_BVMCancel_MouseID}) select 0;
        call (_cancel select 1); call _tick;
        "ACM_ContinuousAction" call _completed; call _finishWaits;
        [!ACM_core_ContinuousAction_Active,"cancel did not release controller"] call _check;
        [(_patient getVariable ["ACM_breathing_BVM_Medic",objNull]) isEqualTo objNull,"cancel retained patient"] call _check;
        [!(_medic getVariable ["ACME_DP_TreatmentBusy",true]),"real BVM completion retained pressure busy state"] call _check;
        [_medic,_patient] call ACM_breathing_fnc_useBVM; call _tick;
        [ACM_core_ContinuousAction_Active,"BVM could not restart after cancellation"] call _check;
    ''')
