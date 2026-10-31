// cancel the pre-raise animation if the treatment or progress bar is interrupted before the bag is up.
params ["_medic"];
if (isNull _medic || {!local _medic}) exitWith {};
private _kitEpoch = _medic getVariable ["ACME_equipmentKitEpoch", 0];
if ((_medic getVariable ["ACME_hang_weaponKitEpoch", _kitEpoch]) != _kitEpoch) exitWith {};
_medic setVariable ["ACME_hang_Raising", false];
_medic setVariable ["ACME_hang_PrepToken", (_medic getVariable ["ACME_hang_PrepToken", 0]) + 1];
private _prone = _medic getVariable ["ACME_hang_Prone", false];
if !(_medic getVariable ["ACME_hang_Active", false]) then {
    [_medic, ""] call ACME_fnc_doAnimHeld;
    [_medic] call ACME_fnc_hangBagRestoreWeapons;
    // A cancelled/failed holster never entered our medical pose. Do not interrupt that native weapon motion
    // with an invented crouch exit or another logical weapon change.
    if (_medic getVariable ["ACME_hang_PrepPoseEntered", false]) then {
        _medic enableAI "ANIM";
        _medic selectWeapon "";
        _medic setUnitPos "AUTO";
        [_medic, [_medic, "AmovPknlMstpSnonWnonDnon", _prone] call ACME_fnc_providerAnimation, 1] call ACME_fnc_doAnim;
    };
    _medic setVariable ["ACME_hang_PrepPoseEntered", false];
    _medic setVariable ["ACME_hang_PrepComplete", false];

    if ((_medic getVariable ["ACME_DP_PauseTreatmentClass", ""]) == "hangbag") then {
        _medic setVariable ["ACME_DP_Paused", false, false];
        _medic setVariable ["ACME_DP_PauseTreatmentClass", "", false];
        _medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
    };
};
