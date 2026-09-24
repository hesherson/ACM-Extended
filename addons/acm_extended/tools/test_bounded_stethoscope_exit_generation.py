"""Execute the complete stethoscope Unload function with explicit engine stand-ins.

This verifies requested handoffs and callback ownership, not rendered animation,
real displays, networking, hearing gain or the contents of inventory restores.
"""
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute


def setup():
    text = (ROOT / 'addons/acm_extended/functions/fn_stethoscopeClose.sqf').read_text()
    for old, new in [
        ('local _medic', '_medicLocal'),
        ('objectParent _medic', '_medicParent'),
        ('getAnimSpeedCoef _medic', '_speed'),
        ('_medic setAnimSpeedCoef 1;', '_speed = 1;'),
    ]:
        text = text.replace(old, new)
    return r"""
        private _display = missionNamespace;
        private _medicLocal = true; private _medicParent = objNull;
        private _speed = 0; private _lower = []; private _stops = [];
        private _restore = []; private _vestEvents = []; private _released = [];
        private _providerCancels = []; private _patientCancels = [];
        CBA_fnc_removePerFrameHandler = {_removed pushBack (_this select 0);};
        ACME_fnc_treatmentPoseStop = {_stops pushBack _this;};
        ACME_fnc_headElevMedicSeq = {_lower pushBack _this;};
        ACME_fnc_chestAccessVestRestore = {_restore pushBack _this;};
        ACME_fnc_chestAccessVestEvent = {_vestEvents pushBack _this;};
        ACME_fnc_patientAnimRelease = {_released pushBack _this;};
        ACME_fnc_rollProviderCancel = {_providerCancels pushBack _this;};
        ACME_fnc_patientRollCancel = {_patientCancels pushBack _this;};
        ace_hearing_fnc_updateHearingProtection = {};
        _display setVariable ["ACME_stethMedic", _medic];
        _display setVariable ["ACME_stethPatient", _patient];
        _display setVariable ["ACME_stethPoseEpoch", 5];
        _display setVariable ["ACME_continuousEpoch", 10];
        _display setVariable ["ACME_stethTickPFH", 21];
        _display setVariable ["ACME_stethFlipPFH", 22];
        _display setVariable ["ACME_stethFlipActive", false];
        _display setVariable ["ACME_stethChannels", []];
        _medic setVariable ["ACME_treatmentPoseEpoch", 5];
        _medic setVariable ["ACM_core_ContinuousAction_Session", [_patient, 10]];
        missionNamespace setVariable ["ACM_core_ContinuousAction_Epoch", 10];
        ACM_core_ContinuousAction_Active = true;
        ACM_core_ContinuousAction_IsDialog = true;
        uiNamespace setVariable ["ACM_breathing_Stethoscope_DLG", _display];
    """ + 'private _close = {' + adapt(text) + '};\n'


@pytest.mark.parametrize('current', [10, 11, 0])
@pytest.mark.parametrize('captured', [10, -1])
@pytest.mark.parametrize('pose', [5, 6])
def test_final_provider_handoff_requires_the_display_continuous_generation(current, captured, pose):
    owns = captured >= 0 and captured == current
    execute(setup() + f'''
        missionNamespace setVariable ["ACM_core_ContinuousAction_Epoch", {current}];
        _display setVariable ["ACME_continuousEpoch", {captured}];
        _medic setVariable ["ACME_treatmentPoseEpoch", {pose}];
        [_display] call _close;
        [count _lower == {int(owns)}, "wrong-generation provider exit"] call _check;
        [ACM_core_ContinuousAction_Active isEqualTo {str(not owns).lower()}, "wrong controller retirement"] call _check;
        [(_removed isEqualTo [21,22]), "display PFHs not retired"] call _check;
    ''')


@pytest.mark.parametrize('state', [
    '_alive = false;',
    '_medic setVariable ["ACE_isUnconscious", true];',
    '_medicParent = profileNamespace;',
    '_medicLocal = false;',
    '_medic setVariable ["ACME_headElev_seqActive", true];',
])
def test_matching_generation_keeps_existing_exit_eligibility(state):
    execute(setup() + state + '''
        [_display] call _close;
        [count _lower == 0, "ineligible provider received lower sequence"] call _check;
        [!ACM_core_ContinuousAction_Active, "own controller left active"] call _check;
    ''')


@pytest.mark.parametrize('flip', [False, True])
@pytest.mark.parametrize('carrier', [False, True])
@pytest.mark.parametrize('patient_alive', [False, True])
def test_ordinary_exit_and_active_flip_keep_supine_and_carrier_handoffs(flip, carrier, patient_alive):
    execute(setup() + f'''
        _patientAlive = {str(patient_alive).lower()};
        _display setVariable ["ACME_stethFlipActive", {str(flip).lower()}];
        // A live Flip legitimately advances the pose epoch without changing the scope generation.
        _medic setVariable ["ACME_treatmentPoseEpoch", {6 if flip else 5}];
    ''' + ('''
        _medic setVariable ["ACME_chestAccess_treatment", [_patient, "usestethoscope", "carrier:one"]];
    ''' if carrier else '') + '''
        [_display] call _close;
        [count _lower == 1 && {(_lower select 0) isEqualTo [_medic,"lower"]}, "authored exit lost"] call _check;
        [!ACM_core_ContinuousAction_Active, "scope reservation survived"] call _check;
    ''' + f'''
        [count _patientCancels == {int(flip)}, "wrong physical flip cancellation"] call _check;
        [count _providerCancels == {int(flip)}, "wrong provider flip cancellation"] call _check;
        [count _vestEvents == {int(carrier)} && {{count _restore == {int(not carrier)}}}, "carrier handoff changed"] call _check;
    ''' + ('''
        [(_patientCancels select 0) isEqualTo [_patient,"front"], "cancel no longer requests anterior up"] call _check;
    ''' if flip else '''
        [(_stops select 0) isEqualTo [_medic,"stethoscope",5,true], "pose handoff changed"] call _check;
        [_speed == 1, "frozen provider not released"] call _check;
    '''))
