/* Cached decoration only. No patient, inventory, selection or treatment work; uses the existing UI worker. */
params ["_display"];
if (isNull _display || {!isNull (findDisplay 86200)} || {!isNull (findDisplay 84000)}) exitWith {};
private _now = diag_tickTime;
private _fresh = _now - (_display getVariable ["ACME_txVisualRefresh",-10]) <= 0.75;
{
    _x params ["_idc","_width","_height"];
    private _group = _display displayCtrl _idc;
    private _mask = _group controlsGroupCtrl 40;
    if (!_fresh) then {[_mask,"show",false] call ACME_fnc_transfusionUiSet;} else {
        if (ctrlShown _group && {ctrlShown _mask}) then {
            // One spare motif covers the edge throughout the phase. The mask clips at the real fill endpoint.
            private _tile = _width / 31;
            private _offset = (((_now / 0.8) mod 1) - 1) * _tile;
            [(_mask controlsGroupCtrl 41),"position",[_offset,0,_tile * 32,_height]] call ACME_fnc_transfusionUiSet;
        };
    };
} forEach (_display getVariable ["ACME_txVisualCards",[]]);
private _fade = if (_fresh) then {0.04 + 0.16 * (0.5 + 0.5 * sin (_now * 360))} else {0};
{
    private _frame = _display displayCtrl _x;
    if (!isNull _frame && {ctrlShown _frame}) then {
        // Only the decorative rounded frame breathes. The label, focus, hit rectangle and visibility stay fixed.
        _frame ctrlSetFade _fade;_frame ctrlCommit 0;
    };
} forEach (_display getVariable ["ACME_txPulseFrames",[]]);
