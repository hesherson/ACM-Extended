// Immediately cancel an in-progress chest-seal roll primitive.
// Clearing ACME_CS_rollToken invalidates both delayed callbacks in fn_chestSealRoll. A grounded casualty is snapped
// to a stable rest side rather than being allowed to finish the cancelled roll.
params [
    ["_patient", objNull, [objNull]],
    ["_stableSide", "", [""]]
];
if (isNull _patient) exitWith {false};
if (!local _patient) exitWith {
    [_patient, "patientRollCancel", [_patient, _stableSide]] call ACME_fnc_ownerDispatch;
    true
};

private _token = _patient getVariable ["ACME_CS_rollToken", ""];
private _until = _patient getVariable ["ACME_CS_rollUntil", -1];
private _active = (_token != "") || {(_until isEqualType 0) && {_until > CBA_missionTime}};
if (!_active) exitWith {false};

if !(_stableSide in ["front", "back"]) then {
    _stableSide = _patient getVariable ["ACME_CS_facing", "front"];
};
if !(_stableSide in ["front", "back"]) then {_stableSide = "front";};

_patient setVariable ["ACME_CS_rollToken", "", false];
_patient setVariable ["ACME_CS_rollUntil", -1, false];
if (_token != "") then {[_patient, _token] call ACME_fnc_patientAnimRelease;};

if (alive _patient && {isNull objectParent _patient}) then {
    private _unconscious = (_patient getVariable ["ACE_isUnconscious", false])
        || {_patient getVariable ["ace_medical_unconscious", false]};
    private _lyingRaw = _patient getVariable ["ACM_core_Lying_State", false];
    private _lying = if (_lyingRaw isEqualType true) then {_lyingRaw} else {_lyingRaw > 0};

    if (_unconscious || {_lying}) then {
        private _hold = if (_stableSide == "back") then {
            missionNamespace getVariable ["ACME_uncon_faceDown", "ace_medical_engine_uncon_anim_1"]
        } else {
            missionNamespace getVariable ["ACME_uncon_faceUp", "ACM_LyingState"]
        };
        _patient setVariable ["ACME_CS_facing", _stableSide, true];
        if (missionNamespace getVariable ["ACME_interventionAnimations", true]) then {
            _patient switchMove _hold;
            ["ace_common_switchMove", [_patient, _hold]] call CBA_fnc_globalEvent;
        };
    } else {
        // If the casualty woke during the roll, do not seize them into an unconscious hold just to satisfy a cancel.
        if (missionNamespace getVariable ["ACME_interventionAnimations", true]) then {
            _patient switchMove "";
            ["ace_common_switchMove", [_patient, ""]] call CBA_fnc_globalEvent;
        };
    };
};
true
