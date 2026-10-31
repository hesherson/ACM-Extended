// Install one MouseButtonDown handler per mission/medical-menu display.
// RMB releases Direct Pressure or lowers Hang Bag. MMB remains a compatible DP release input.
// The cancel is fired one frame later so the display handler can consume only the matching physical click.
if (!hasInterface) exitWith {};
disableSerialization;
params [["_disp", displayNull, [displayNull]]];

if (isNull _disp) then {_disp = findDisplay 46;};
if (isNull _disp) exitWith {
    // the mission display is not up yet, so retry shortly.
    [{ [] call ACME_fnc_installRmbCancelGuard }, [], 1] call CBA_fnc_waitAndExecute;
};

// Display-local ownership also permits closing/reopening the medical menu without retaining an old handle.
if (_disp getVariable ["ACME_RmbGuard_Installed", false]) exitWith {};
_disp setVariable ["ACME_RmbGuard_Installed", true];

private _eh = _disp displayAddEventHandler ["MouseButtonDown", {
    params ["_d", "_button"];
    if (call ACME_fnc_transfusionInputOwned) exitWith {false};
    private _u = ACE_player;
    if (isNull _u || {!local _u} || {!alive _u}) exitWith { false };

    // Pressure stays registered while CPR/BVM or another treatment borrows the provider. Those actions own
    // their mouse controls until they end; neither this handler nor its deferred callback may consume them.
    private _canCancelDP = {
        params ["_unit"];
        (_unit getVariable ["ACME_DP_Active", false])
            && {!(_unit getVariable ["ACME_DP_Paused", false])}
            && {!(_unit getVariable ["ACME_DP_TreatmentBusy", false])}
            && {!(_unit getVariable ["ACME_treatmentPreflightActive", false])}
            && {!(_unit getVariable ["ACME_chestAccessPreflightActive", false])}
            && {(_unit getVariable ["ACME_chestAccessProvider", []]) isEqualTo []}
            && {!(_unit getVariable ["ACME_headElev_seqActive", false])}
            && {!(_unit getVariable ["ACM_circulation_isPerformingCPR", false])}
            && {!(_unit getVariable ["ACM_breathing_isUsingBVM", false])}
            && {!(missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false])}
    };

    private _hang = _u getVariable ["ACME_hang_Active", false];
    private _cancelHang = (_button isEqualTo 1) && {_hang};
    private _cancelDP = (_button in [1, 2]) && {!_hang} && {[_u] call _canCancelDP};
    if !(_cancelHang || {_cancelDP}) exitWith { false };

    // B127: capture the exact hold episode before deferring. Without this, an RMB from an ending hold could execute
    // one frame later after a new hold started and cancel the new episode instead.
    private _hangStart = _u getVariable ["ACME_hang_Start", -1];
    private _dpToken = _u getVariable ["ACME_DP_PoseToken", -1];
    private _claimToken = _u getVariable ["ACME_DP_ClaimToken", ""];
    private _claimEpoch = _u getVariable ["ACME_DP_ClaimEpoch", -1];
    private _localityEpoch = _u getVariable ["ACME_providerLocalityEpoch", 0];

    // fire the matching cancel next frame, so this handler returns, and swallows the RMB, cleanly first.
    [{
        params ["_u", "_hangStart", "_dpToken", "_cancelHang", "_cancelDP", "_claimToken", "_claimEpoch", "_localityEpoch", "_canCancelDP"];
        if (isNull _u || {!local _u} || {!(_u isEqualTo ACE_player)}
            || {(_u getVariable ["ACME_providerLocalityEpoch", 0]) != _localityEpoch}) exitWith {};
        if (call ACME_fnc_transfusionInputOwned) exitWith {};
        if (_cancelHang && {_u getVariable ["ACME_hang_Active", false]}
            && {(_u getVariable ["ACME_hang_Start", -2]) == _hangStart}) exitWith {
            [false] call ACME_fnc_hangBagStop;
        };
        if (_cancelDP && {[_u] call _canCancelDP}
            && {!(_u getVariable ["ACME_hang_Active", false])}
            && {(_u getVariable ["ACME_DP_PoseToken", -2]) == _dpToken}
            && {(_u getVariable ["ACME_DP_ClaimToken", ""]) == _claimToken}
            && {(_u getVariable ["ACME_DP_ClaimEpoch", -1]) == _claimEpoch}) exitWith {
            [false, _u] call ACME_fnc_directPressureStop;
        };
    }, [_u, _hangStart, _dpToken, _cancelHang, _cancelDP, _claimToken, _claimEpoch, _localityEpoch, _canCancelDP]] call CBA_fnc_execNextFrame;

    true
}];

_disp setVariable ["ACME_RmbGuard_EH", _eh];
