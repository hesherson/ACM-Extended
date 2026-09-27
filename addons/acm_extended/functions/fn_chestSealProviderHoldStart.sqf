// Hold the provider in the chest-seal hands-on-chest pose for the lifetime of the minigame.
// Flip temporarily hands off to medic4 and returns directly here.
params [
    ["_medic", objNull, [objNull]],
    ["_patient", objNull, [objNull]],
    ["_forceImmediate", false, [false]]
];
if (isNull _medic || {!alive _medic} || {_medic isEqualTo _patient}) exitWith {-1};
if (!local _medic) exitWith {-1};
if (_medic getVariable ["ACE_isUnconscious", false] || {[_medic] call ACME_fnc_animBlocked}) exitWith {-1};

private _state = _medic getVariable ["ACME_treatmentPoseState", []];
if ((_state param [1, ""]) == "chestSealWorkspace") exitWith {_state param [0, -1]};

// Carrier access intentionally remains frozen in medic4 until the panel is genuinely ready. Consume that exact
// episode as a handoff, so the first frame after the 2.2 s freeze is hands-on-chest rather than a neutral crouch.
if ((_state param [1, ""]) == "chestAccess") then {
    private _accessEpoch = _state param [0, -1];
    if (_accessEpoch >= 0) then {
        [_medic, "chestAccess", _accessEpoch, true] call ACME_fnc_treatmentPoseStop;
    };
    private _providerEntry = _medic getVariable ["ACME_chestAccessProvider", []];
    if ((_providerEntry param [0,objNull]) isEqualTo _patient) then {
        _medic setVariable ["ACME_chestAccessProvider", [], false];
        _medic setVariable ["ACME_chestAccessProviderReady", [], true];
    };
};

private _epoch = [_medic, "chestSealWorkspace", -1, _patient, _forceImmediate] call ACME_fnc_treatmentPoseStart;
if (_epoch >= 0) then {
    _medic setVariable ["ACME_CS_providerHoldEpoch", _epoch, false];
};
_epoch
