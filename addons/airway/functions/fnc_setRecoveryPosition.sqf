#include "..\script_component.hpp"
/* B215: fixed patient-owner recovery endpoint. The visual blend is provisional until
 * the treatment succeeds AND the owner observes the recovery pose settling.
 * Optional phase/token arguments belong only to the scoped treatment transaction.
 */
params ["_medic", "_patient", "_state", ["_noLog", false], ["_phase", ""], ["_token", ""], ["_expectedProviderEpoch", -1], ["_expectedClinicalEpoch", -1], ["_hops", 0]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    if (_hops < 4) then {
        [QGVAR(setRecoveryPosition), [_medic, _patient, _state, _noLog, _phase, _token, _expectedProviderEpoch, _expectedClinicalEpoch, _hops + 1], _patient] call CBA_fnc_targetEvent;
    };
};
if !(_phase in ["", "begin", "commit", "cancel", "apply", "interrupt"]) exitWith {};
private _pending = _patient getVariable [QGVAR(RecoveryPosition_Pending), []];
private _pendingToken = _pending param [0, ""];

// B220: a successful body roll permanently replaces recovery; it is not a suspension.
// This owner-only phase retires both provisional and committed episodes WITHOUT
// issuing a lying/supine animation over the roll that has just won the patient.
if (_phase == "interrupt") exitWith {
    private _episode = _patient getVariable [QGVAR(RecoveryPosition_Episode), ""];
    private _active = _patient getVariable [QGVAR(RecoveryPosition_State), false];
    if (!_active && {_pendingToken == ""} && {_episode == ""}) exitWith {};
    _patient setVariable [QGVAR(RecoveryPosition_Pending), [], true];
    _patient setVariable [QGVAR(RecoveryPosition_Episode), "", true];
    _patient setVariable [QGVAR(RecoveryPosition_State), false, true];
    // A provisional placement has not established head tilt. Do not clear an
    // independent airway hold when cancelling only that pending attempt.
    if (_active || {_episode != ""}) then {
        _patient setVariable [QGVAR(HeadTilt_State), false, true];
    };
    {
        if (_x != "") then {[_patient, _x] call ACME_fnc_patientAnimRelease;};
    } forEach ([_pendingToken, _episode] arrayIntersect [_pendingToken, _episode]);
};

if (_phase == "cancel" || {!_state}) exitWith {
    private _ownedToken = (_patient getVariable ["ACME_patientAnimLock", []]) param [0, ""];
    // A cancelled remote begin may still be in flight. Retire even an as-yet unseen token.
    if (_token != "") then {[_patient, _token] call ACME_fnc_patientAnimRelease;};
    if (_pendingToken != "" && {_token == "" || {_pendingToken == _token}}) then {
        private _owns = _ownedToken == _pendingToken;
        _patient setVariable [QGVAR(RecoveryPosition_Pending), [], true];
        [_patient, _pendingToken] call ACME_fnc_patientAnimRelease;
        // Cancel only our provisional body pose. Never interrupt a successor, wake, vehicle or drag/carry.
        if (_owns && {alive _patient} && {IS_UNCONSCIOUS(_patient)} && {isNull objectParent _patient}
            && {!([_patient] call ACEFUNC(common,isBeingDragged))} && {!([_patient] call ACEFUNC(common,isBeingCarried))}
            && {(toLowerANSI animationState _patient) == "acm_recoveryposition"}) then {
            _patient switchMove ["ACM_LyingState", 0, 0, false];
        };
    };
    // Token-scoped provisional cancellation never tears down an already committed/new recovery episode.
    if (_phase == "cancel") exitWith {};
    if (_token != "" && {(_patient getVariable [QGVAR(RecoveryPosition_Episode), ""]) != _token}) exitWith {};
    if !(_patient getVariable [QGVAR(RecoveryPosition_State), false]) exitWith {};
    _patient setVariable [QGVAR(RecoveryPosition_State), false, true];
    _patient setVariable [QGVAR(HeadTilt_State), false, true];
    _patient setVariable [QGVAR(RecoveryPosition_Episode), "", true];
    if (!_noLog) then {
        [LSTRING(RecoveryPosition_Cancelled), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
        [_patient, "quick_view", LSTRING(RecoveryPosition_Cancelled_ActionLog), [[_medic, false, true] call ACEFUNC(common,getName)]] call ACEFUNC(medical_treatment,addToLog);
    };
};
if (!alive _patient || {!(IS_UNCONSCIOUS(_patient))} || {!isNull objectParent _patient}) exitWith {};
// B216: fitted adjuncts do not prevent side positioning. Active respiratory support
// does; recheck on the casualty owner as well as the provider's menu/progress path.
if (_patient getVariable ["ACME_vent_driving", false]
    || {[_patient] call EFUNC(core,cprActive)}
    || {alive (_patient getVariable ["ACM_breathing_BVM_Medic", objNull])}) exitWith {
    if (_token != "" && {_pendingToken == _token}) then {
        [_medic, _patient, false, true, "cancel", _token] call FUNC(setRecoveryPosition);
    };
};
if (_patient getVariable [QGVAR(RecoveryPosition_State), false]) exitWith {};

if (_phase == "commit") exitWith {
    if (_pendingToken == _token && {_token != ""}) then {
        _pending set [3, true];
        _patient setVariable [QGVAR(RecoveryPosition_Pending), _pending, true];
    };
};
if (_phase == "apply") exitWith {
    // The local worker is the only path which proves that the blend actually entered and settled.
    if (_token == "" || {_pendingToken != _token} || {!(_pending param [3, false])}
        || {!(_pending param [5, false])} || {(_pending param [4, -1]) < 0}
        || {serverTime < ((_pending select 4) + 0.5)}
        || {((_patient getVariable ["ACME_patientAnimLock", []]) param [0, ""]) != _token}
        || {(toLowerANSI animationState _patient) != "acm_recoveryposition"}
        || {(_pending param [8, -1]) != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {};
    private _moveBlend = _patient getUnitMovesInfo 3;
    if (!(_moveBlend isEqualType 0) || {!finite _moveBlend} || {_moveBlend < 0.99}) exitWith {};
    _patient setVariable [QGVAR(RecoveryPosition_Pending), [], true];
    _patient setVariable [QGVAR(RecoveryPosition_State), true, true];
    _patient setVariable [QGVAR(HeadTilt_State), true, true];
    _patient setVariable [QGVAR(RecoveryPosition_Episode), _token, true];
    if (_patient getVariable [QGVAR(AirwayObstructionVomit_State), 0] == 1) then {
        _patient setVariable [QGVAR(AirwayObstructionVomit_State), 0, true];
    };
    if (_patient getVariable [QGVAR(AirwayObstructionBlood_State), 0] == 1) then {
        _patient setVariable [QGVAR(AirwayObstructionBlood_State), 0, true];
    };
    [_patient, _token] call ACME_fnc_patientAnimRelease;
    if (!_noLog) then {
        [LSTRING(RecoveryPosition_Established), 1.5, _medic] call ACEFUNC(common,displayTextStructured);
        [_patient, "quick_view", LSTRING(RecoveryPosition_Established_ActionLog), [[_medic, false, true] call ACEFUNC(common,getName)]] call ACEFUNC(medical_treatment,addToLog);
    };
};

// Legacy callers still use the same smooth owner transaction, with success already supplied by their action.
if (_token == "") then {_token = format ["recovery:%1:%2:%3", clientOwner, netId _patient, diag_tickTime];};
if (_token in (_patient getVariable ["ACME_patientAnimRetired", []])) exitWith {};
if (_pendingToken != "") exitWith {}; // simultaneous providers cannot replace an in-flight recovery
private _providerEpoch = _expectedProviderEpoch;
if (_providerEpoch < 0 && {!isNull _medic}) then {_providerEpoch = _medic getVariable ["ACME_treatmentPoseEpoch", -1];};
private _clinicalEpoch = [_patient] call ACME_fnc_clinicalEpoch;
if (_expectedClinicalEpoch >= 0 && {_expectedClinicalEpoch != _clinicalEpoch}) exitWith {};
_patient setVariable [QGVAR(RecoveryPosition_Pending), [_token, _medic, serverTime + 5, _phase == "", -1, false, _noLog, _providerEpoch, _clinicalEpoch], true];
[_medic, _patient, _token] call FUNC(handleRecoveryPosition);
