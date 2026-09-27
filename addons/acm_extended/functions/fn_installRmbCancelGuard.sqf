// Install one persistent MouseButtonDown handler on mission display 46.
// Hang Bag keeps RMB as its dedicated lower/cancel input. Direct Pressure uses MMB exclusively, matching the
// project's interaction contract: aiming (RMB), Escape and H must never silently release hemorrhage control.
// The cancel is fired one frame later so the display handler can consume only the matching physical click.
if (!hasInterface) exitWith {};

private _disp = findDisplay 46;
if (isNull _disp) exitWith {
    // the mission display is not up yet, so retry shortly.
    [{ call ACME_fnc_installRmbCancelGuard }, [], 1] call CBA_fnc_waitAndExecute;
};

// do not double-install.
if (uiNamespace getVariable ["ACME_RmbGuard_Installed", false]) exitWith {};
uiNamespace setVariable ["ACME_RmbGuard_Installed", true];

private _eh = _disp displayAddEventHandler ["MouseButtonDown", {
    params ["_d", "_button"];
    private _u = ACE_player;
    if (isNull _u || {!alive _u}) exitWith { false };

    private _hang = _u getVariable ["ACME_hang_Active", false];
    private _dp   = _u getVariable ["ACME_DP_Active", false];
    private _cancelHang = (_button isEqualTo 1) && {_hang};
    private _cancelDP = (_button isEqualTo 2) && {_dp};
    if !(_cancelHang || {_cancelDP}) exitWith { false };

    // B127: capture the exact hold episode before deferring. Without this, an RMB from an ending hold could execute
    // one frame later after a new hold started and cancel the new episode instead.
    private _hangStart = _u getVariable ["ACME_hang_Start", -1];
    private _dpToken = _u getVariable ["ACME_DP_PoseToken", -1];

    // fire the matching cancel next frame, so this handler returns, and swallows the RMB, cleanly first.
    [{
        params ["_hangStart", "_dpToken", "_cancelHang", "_cancelDP"];
        private _u = ACE_player;
        if (isNull _u) exitWith {};
        if (_cancelHang && {_u getVariable ["ACME_hang_Active", false]}
            && {(_u getVariable ["ACME_hang_Start", -2]) == _hangStart}) exitWith {
            [false] call ACME_fnc_hangBagStop;
        };
        if (_cancelDP && {_u getVariable ["ACME_DP_Active", false]}
            && {(_u getVariable ["ACME_DP_PoseToken", -2]) == _dpToken}) exitWith {
            [false, _u] call ACME_fnc_directPressureStop;
        };
    }, [_hangStart, _dpToken, _cancelHang, _cancelDP]] call CBA_fnc_execNextFrame;

    true  // consume only RMB-for-Hang-Bag or MMB-for-Direct-Pressure
}];

uiNamespace setVariable ["ACME_RmbGuard_EH", _eh];
