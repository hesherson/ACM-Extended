// B88 cancel/release for the provider-only head-position sequence.
// The patient head position is never changed here. Provider animation control returns to an unarmed idle in the provider's posture.
private _medic = ACE_player;
if (isNull _medic || {!local _medic}) exitWith {};
if !(_medic getVariable ["ACME_headElev_seqActive", false]) exitWith {};

_medic setVariable ["ACME_headElev_seqActive", false, false];
_medic setVariable ["ACME_headElev_seqToken", -1, false];
_medic setVariable ["ACME_headElev_medicAnimToken", -1, false];
_medic setVariable ["ACME_headElev_medicAnimStage", -1, false];
_medic setVariable ["ACME_headElev_seqMode", "", false];

private _dpPauseClass = _medic getVariable ["ACME_DP_PauseTreatmentClass", ""];
if ((_medic getVariable ["ACME_DP_Active", false]) && {_dpPauseClass in ["acme_elevatehead", "acme_lowerhead"]}) then {
    _medic setVariable ["ACME_DP_Paused", false, false];
    _medic setVariable ["ACME_DP_PauseTreatmentClass", "", false];
    _medic setVariable ["ACME_DP_TreatmentBusy", false, false];
    _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
    _medic setVariable ["ACME_DP_LastPoseAssert", 0, false];
};

private _kh = _medic getVariable ["ACME_headElev_seqKey", -1];
private _disp = findDisplay 46;
if (_kh >= 0 && {!isNull _disp}) then {
    _disp displayRemoveEventHandler ["KeyDown", _kh];
};
_medic setVariable ["ACME_headElev_seqKey", -1, false];

_medic setVariable ["ACME_headElev_pinToken", (_medic getVariable ["ACME_headElev_pinToken", 0]) + 1, false];
["ace_common_setAnimSpeedCoef", [_medic, 1]] call CBA_fnc_globalEvent;

if (alive _medic && {isNull objectParent _medic}) then {
    _medic selectWeapon "";
    private _prone = _medic getVariable ["ACME_headElev_providerProne", false];
    _prone = _prone || {([_medic, "AmovPknlMstpSnonWnonDnon"] call ACME_fnc_providerAnimation) == "AmovPpneMstpSnonWnonDnon"};
    _medic setUnitPos (["MIDDLE", "DOWN"] select (_prone || {stance _medic == "PRONE"}));
    [_medic, [_medic, "AmovPknlMstpSnonWnonDnon", _prone] call ACME_fnc_providerAnimation, 2] call ACME_fnc_doAnim;
    [{
        params ["_m"];
        if (isNull _m || {!local _m} || {!alive _m} || {!isNull objectParent _m}) exitWith {};
        if (_m getVariable ["ACME_headElev_seqActive", false]) exitWith {};
        if ([_m] call ACME_fnc_providerStanceOwned) exitWith {};
        _m setUnitPos "AUTO";
    }, [_medic], 0.25] call CBA_fnc_waitAndExecute;
};
