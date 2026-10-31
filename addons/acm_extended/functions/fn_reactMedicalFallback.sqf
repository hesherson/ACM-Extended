/* Restore the original card pool in this display; never navigate, reopen or close a menu. */
params ["_display"];
if (isNull _display) exitWith {false};
_display setVariable ["ACME_reactActive",false];
_display setVariable ["ACME_reactReady",false];
_display setVariable ["ACME_reactPainted",false];
_display setVariable ["ACME_reactFailed",true];
_display setVariable ["ACME_reactSession",""];
_display setVariable ["ACME_reactRows",createHashMap];
private _browser = _display displayCtrl 89301;
if (!isNull _browser) then {_browser ctrlShow false;_browser ctrlEnable false;};
// The normal card refresh paints these again immediately on its next pass.
private _shown = ((_display getVariable ["ACME_txCardLayout",createHashMap]) getOrDefault [86004,[]]) param [4,false];
for "_slot" from 0 to 1 do {
    private _group = _display displayCtrl (86500 + _slot);
    if (!isNull _group) then {
        private _hit = _group controlsGroupCtrl 9;
        [_group,"show",_shown && {(_hit getVariable ["ACME_txIdentity",[]]) isNotEqualTo []}] call ACME_fnc_transfusionUiSet;
    };
};
true
