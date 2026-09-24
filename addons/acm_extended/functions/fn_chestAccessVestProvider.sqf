// Provider-side owner for temporary chest-access carrier handling.
// The provider fully holsters/crouches through treatmentPoseStart, enters literal medic4, then publishes a
// presentation-ready token. Patient lift waits for that exact state when possible, with a bounded fail-open.
params [
    ["_medic", objNull, [objNull]],
    ["_patient", objNull, [objNull]],
    ["_op", "start", [""]],
    ["_handoff", false, [false]],
    ["_episodeToken", "", [""]]
];
if (isNull _medic) exitWith {-1};
_op = toLowerANSI _op;

if (!local _medic) exitWith {
    [_medic, "chestAccessVestProvider", [_medic, _patient, _op, _handoff, _episodeToken]] call ACME_fnc_ownerDispatch;
    -1
};

if (_op == "stop") exitWith {
    private _entry = _medic getVariable ["ACME_chestAccessProvider", []];
    private _entryPatient = _entry param [0, objNull];
    private _epoch = _entry param [1, -1];
    private _token = _entry param [2, ""];
    private _pose = _medic getVariable ["ACME_treatmentPoseState", []];

    private _speedToken = _medic getVariable ["ACME_chestAccessProviderSpeedToken", ""];
    if (_speedToken != "" && {_speedToken == _token}) then {
        _medic setVariable ["ACME_chestAccessProviderSpeedToken", "", false];
        ["ace_common_setAnimSpeedCoef", [_medic, 1]] call CBA_fnc_globalEvent;
    };

    if ((_entryPatient isEqualTo _patient)
        && {_epoch >= 0}
        && {(_pose param [0, -2]) == _epoch}
        && {(_pose param [1, ""]) == "chestAccess"}) then {
        [_medic, "chestAccess", _epoch, _handoff] call ACME_fnc_treatmentPoseStop;
    };

    if (_entryPatient isEqualTo _patient) then {
        _medic setVariable ["ACME_chestAccessProvider", [], false];
    };

    private _ready = _medic getVariable ["ACME_chestAccessProviderReady", []];
    if ((_ready param [0,""]) == _token) then {
        _medic setVariable ["ACME_chestAccessProviderReady", [], true];
    };
    _epoch
};

if (!alive _medic
    || {_medic getVariable ["ACE_isUnconscious", false]}
    || {[_medic] call ACME_fnc_animBlocked}
    || {_medic isEqualTo _patient}) exitWith {-1};

private _armReadyProbe = {
    params ["_m","_epoch","_token"];
    if (_token == "") exitWith {};

    _m setVariable ["ACME_chestAccessProviderReady", [_token, -1], true];

    [{
        params ["_m","_epoch","_token"];
        if (isNull _m || {!local _m} || {!alive _m}) exitWith {true};

        private _entry = _m getVariable ["ACME_chestAccessProvider", []];
        if ((_entry param [2,""]) != _token) exitWith {true};

        private _state = _m getVariable ["ACME_treatmentPoseState", []];
        (_state param [0,-2]) == _epoch
            && {(_state param [1,""]) == "chestAccess"}
            && {(_state param [3,-2]) >= 1}
            && {(toLowerANSI animationState _m) == "ainvpknlmstpsnonwnondnon_medic4"}
    }, {
        params ["_m","_epoch","_token"];
        private _entry = _m getVariable ["ACME_chestAccessProvider", []];
        if ((_entry param [2,""]) == _token) then {
            _m setVariable ["ACME_chestAccessProviderReady", [_token, serverTime], true];
        };
    }, [_m,_epoch,_token], 4.5, {
        params ["_m","_epoch","_token"];
        private _entry = _m getVariable ["ACME_chestAccessProvider", []];
        if ((_entry param [2,""]) == _token) then {
            // -2 means the provider presentation timed out. The patient transaction may proceed fail-open.
            _m setVariable ["ACME_chestAccessProviderReady", [_token, -2], true];
        };
    }] call CBA_fnc_waitUntilAndExecute;
};

private _entry = _medic getVariable ["ACME_chestAccessProvider", []];
private _existingPatient = _entry param [0, objNull];
private _existingEpoch = _entry param [1, -1];
private _pose = _medic getVariable ["ACME_treatmentPoseState", []];

if ((_existingPatient isEqualTo _patient)
    && {_existingEpoch >= 0}
    && {(_pose param [0, -2]) == _existingEpoch}
    && {(_pose param [1, ""]) == "chestAccess"}) exitWith {
    if (_episodeToken != "") then {
        _medic setVariable ["ACME_chestAccessProvider", [_patient, _existingEpoch, _episodeToken], false];
        if ((_episodeToken find "vest:access:") == 0) then {
            private _speed = missionNamespace getVariable ["ACME_chestAccess_providerAnimSpeed", 1.50];
            if (!(_speed isEqualType 0) || {!finite _speed} || {_speed < 1}) then {_speed = 1.50;};
            _medic setVariable ["ACME_chestAccessProviderSpeedToken", _episodeToken, false];
            ["ace_common_setAnimSpeedCoef", [_medic, _speed]] call CBA_fnc_globalEvent;
        };
        [_medic,_existingEpoch,_episodeToken] call _armReadyProbe;
    };
    _existingEpoch
};

// A finished chest action may still own a frozen provider pose. Retire only known chest presentation owners
// as a handoff, so reverse carrier handling starts from the current work frame instead of inserting a neutral crouch.
private _prior = _medic getVariable ["ACME_treatmentPoseState", []];
private _priorMode = _prior param [1, ""];
private _priorEpoch = _prior param [0, -1];
if (_priorMode in ["stethoscope","inspect","chestSealWorkspace","roll"]
    && {_priorEpoch >= 0}) then {
    [_medic, _priorMode, _priorEpoch, true] call ACME_fnc_treatmentPoseStop;
};

private _epoch = [_medic, "chestAccess", -1, _patient] call ACME_fnc_treatmentPoseStart;
if (_epoch >= 0) then {
    _medic setVariable ["ACME_chestAccessProvider", [_patient, _epoch, _episodeToken], false];

    // Only ordinary chest-access preparation is accelerated here. Chest Seal owns its own workspace handoff.
    if ((_episodeToken find "vest:access:") == 0) then {
        private _speed = missionNamespace getVariable ["ACME_chestAccess_providerAnimSpeed", 1.50];
        if (!(_speed isEqualType 0) || {!finite _speed} || {_speed < 1}) then {_speed = 1.50;};
        _medic setVariable ["ACME_chestAccessProviderSpeedToken", _episodeToken, false];
        ["ace_common_setAnimSpeedCoef", [_medic, _speed]] call CBA_fnc_globalEvent;

        [{
            params ["_m","_tok"];
            if (isNull _m || {!local _m}) exitWith {};
            if ((_m getVariable ["ACME_chestAccessProviderSpeedToken",""]) == _tok) then {
                _m setVariable ["ACME_chestAccessProviderSpeedToken", "", false];
                ["ace_common_setAnimSpeedCoef", [_m, 1]] call CBA_fnc_globalEvent;
            };
        }, [_medic,_episodeToken], 8] call CBA_fnc_waitAndExecute;
    };

    [_medic,_epoch,_episodeToken] call _armReadyProbe;
};
_epoch
