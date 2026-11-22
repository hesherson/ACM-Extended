// the confirm handler for ACME_BloodFridge_Dialog. it reads the count sliders, the restock toggle and the regen
// interval, then spawns the fridge at the stashed placement, from the uinamespace ACME_bf_placePos and placedir,
// routed to the server.
disableSerialization;
private _display = findDisplay 87600;
if (isNull _display) exitWith {};

private _pos = uiNamespace getVariable ["ACME_bf_placePos", []];
private _dir = uiNamespace getVariable ["ACME_bf_placeDir", 0];
if (_pos isEqualTo []) exitWith { _display closeDisplay 2; };

private _oPos  = round (sliderPosition 87601);
private _oNeg  = round (sliderPosition 87602);
private _other = round (sliderPosition 87603);
private _hours = round (sliderPosition 87605);
private _mins  = round (sliderPosition 87606);
private _restock = (_display displayCtrl 87604) getVariable ["on", true];

// build the stock spec, skipping zero counts.
private _pairs = [
    ["ACME_BloodBag_O_500",   _oPos],
    ["ACME_BloodBag_ON_500",  _oNeg],
    ["ACME_BloodBag_A_500",   _other],
    ["ACME_BloodBag_AN_500",  _other],
    ["ACME_BloodBag_B_500",   _other],
    ["ACME_BloodBag_BN_500",  _other],
    ["ACME_BloodBag_AB_500",  _other],
    ["ACME_BloodBag_ABN_500", _other]
];
private _stock = [];
{
    _x params ["_class", "_n"];
    if (_n > 0) then { _stock pushBack [_class, _n]; };
} forEach _pairs;

private _regenMins = (_hours * 60) + _mins;  // 0 = never regenerate

_display closeDisplay 1;

[_pos, _dir, _stock, _restock, _regenMins] remoteExec ["ACME_fnc_bloodFridgeSpawn", 2];

private _kept = _stock apply { _x select 1 };
private _total = 0; { _total = _total + _x } forEach _kept;
[format ["Blood fridge placed: %1 units, regen %2h %3m%4.", _total, _hours, _mins, (["", " (off)"] select (!_restock || _regenMins == 0))], 2.5] call ace_common_fnc_displayTextStructured;
