// Client presentation/input runtime only. Dedicated servers must not register UI PFHs, controls or keybinds.
if (!hasInterface) exitWith {};

// UI refreshers are presentation-only. Never register duplicate PFHs on client re-init/hot reload.
if (missionNamespace getVariable ["ACME_transfusionUiRuntimeRegistered", false]) exitWith {};
missionNamespace setVariable ["ACME_transfusionUiRuntimeRegistered", true];

private _txPFH = [{
    private _display = findDisplay 86000;
    if (!isNull _display) then {
        // Keep data/workflow refresh at 4 Hz; animate only cached decoration at 20 Hz.
        if (diag_tickTime >= (_display getVariable ["ACME_txNextRefresh",0])) then {
            _display setVariable ["ACME_txNextRefresh",diag_tickTime + 0.25];
            call ACME_fnc_updateTransfusionControls;
        };
        [_display] call ACME_fnc_transfusionVisualTick;
    };
}, 0.05, []] call CBA_fnc_addPerFrameHandler;
missionNamespace setVariable ["ACME_transfusionUiPFH", _txPFH];

private _clampPFH = [{
    if (!isNull (findDisplay 86200)) then {call ACME_fnc_updateClampDialog;};
}, 0.20, []] call CBA_fnc_addPerFrameHandler;
missionNamespace setVariable ["ACME_clampUiPFH", _clampPFH];
