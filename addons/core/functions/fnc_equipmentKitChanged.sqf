#include "..\script_component.hpp"
/* B266: an explicit, completed loadout replacement retires the old kit's
 * temporary weapon custody. This is NOT an ordinary inventory-change hook.
 * Call on the unit owner after a successful external setter. No full-loadout
 * write, guessed inventory delta, or arbitrary addon metadata is performed.
 * Medical-kit reset is separately owned by the calling lifecycle adapter.
 */
params [["_unit", objNull, [objNull]]];
if (isNull _unit || {!local _unit}) exitWith {false};
if (canSuspend) exitWith {isNil {[_unit] call ACM_core_fnc_equipmentKitChanged;}; true};

// Every queued Hang Bag exit carries the old kit generation. Advancing this
// before teardown prevents an old exit/reopen from touching the replacement.
private _epoch = (_unit getVariable ["ACME_equipmentKitEpoch", 0]) + 1;
_unit setVariable ["ACME_equipmentKitEpoch", _epoch, true];
private _raising = _unit getVariable ["ACME_hang_Raising", false];
_unit setVariable ["ACME_hang_PrepToken", (_unit getVariable ["ACME_hang_PrepToken", 0]) + 1, false];
_unit setVariable ["ACME_hang_savedWeaponSlots", nil, true];
_unit setVariable ["ACME_hang_weaponRestoreOwned", nil, true];
_unit setVariable ["ACME_hang_restoreWarningAt", -1000, false];

// A not-yet-acknowledged claim also has a preparation reassert worker.
// Its fast cancellation branch deliberately skips normal prepStop, so retire
// that old hold here without starting a replacement pose.
private _active = _unit getVariable ["ACME_hang_Active", false];
if (_raising && {!_active || {!(_unit getVariable ["ACME_hang_Claimed", false])}}) then {
    [_unit, ""] call ACME_fnc_doAnimHeld;
};
if (_active) then {
    // Release precisely the former patient claim and its captured visuals.
    // Do not lower the medic, select a weapon, restore equipment, or reopen UI
    // after an Arsenal/mission script has already applied the new kit.
    [true, _unit, true] call ACME_fnc_hangBagStop;
};
// Invalidate the ended episode only AFTER its exact patient release. A late
// restore packet carries that older episode, not a captured kit generation.
// A new preparation can already own new-kit snapshots before hangBagStart
// assigns its next episode; do not let that old packet restore those weapons.
private _previousEpisode = _unit getVariable ["ACME_hang_Start", -1];
if (_previousEpisode >= 0) then {
    private _step = 0.001 max (abs _previousEpisode * 0.0000002);
    _unit setVariable ["ACME_hang_Start", _previousEpisode + _step, true];
};
_unit setVariable ["ACME_hang_Raising", false, false];
if ((_unit getVariable ["ACME_DP_PauseTreatmentClass", ""]) == "hangbag") then {
    _unit setVariable ["ACME_DP_Paused", false, false];
    _unit setVariable ["ACME_DP_PauseTreatmentClass", "", false];
    _unit setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
    _unit setVariable ["ACME_DP_LastPoseAssert", 0, false];
};
true
