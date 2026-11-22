// the zeus and eden module entry point for "Place Blood Fridge". there are two paths.
// eden or scripted: the logic carries the per-type count arguments, ONeg, OPos and so on, plus restock and
// RegenMins. resolve them, falling back to the addon-option defaults, and spawn on the server immediately.
// zeus live placement: open a popup on the machine of the placing curator to choose the unit counts, then spawn on
// confirm. it is detected by a live zeus display, 312, on this machine when the function runs.
// _this is [_logic, _units, _activated], the Module_F convention. isglobal is 0, so it runs on the machine of the
// placer.
params ["_logic"];
if (isNull _logic) exitWith {};

private _pos = getPosATL _logic;
private _dir = getDir _logic;

// resolve the count spec from the arguments of the logic, using the addon-option defaults as fallbacks.
private _resolveStock = {
    params ["_logic"];
    private _defOPos  = missionNamespace getVariable ["ACME_bf_defOPos", 6];
    private _defONeg  = missionNamespace getVariable ["ACME_bf_defONeg", 2];
    private _defOther = missionNamespace getVariable ["ACME_bf_defOther", 0];
    private _types = [
        ["ONeg",  "ACME_BloodBag_ON_500",  _defONeg],
        ["OPos",  "ACME_BloodBag_O_500",   _defOPos],
        ["ANeg",  "ACME_BloodBag_AN_500",  _defOther],
        ["APos",  "ACME_BloodBag_A_500",   _defOther],
        ["BNeg",  "ACME_BloodBag_BN_500",  _defOther],
        ["BPos",  "ACME_BloodBag_B_500",   _defOther],
        ["ABNeg", "ACME_BloodBag_ABN_500", _defOther],
        ["ABPos", "ACME_BloodBag_AB_500",  _defOther]
    ];
    private _stock = [];
    {
        _x params ["_arg", "_class", "_def"];
        private _n = round (_logic getVariable [_arg, _def]);
        if (_n > 0) then { _stock pushBack [_class, _n]; };
    } forEach _types;
    _stock
};

// zeus live placement gives a popup. stash the placement, delete the logic and open the dialog on this client.
if (!isNull (findDisplay 312)) exitWith {
    uiNamespace setVariable ["ACME_bf_placePos", _pos];
    uiNamespace setVariable ["ACME_bf_placeDir", _dir];
    if (!isNull _logic) then { deleteVehicle _logic; };
    [{ createDialog "ACME_BloodFridge_Dialog"; }, [], 0.05] call CBA_fnc_waitAndExecute;
};

// eden or scripted spawns immediately on the server with the resolved arguments of the logic.
private _stock    = [_logic] call _resolveStock;
private _restock  = _logic getVariable ["Restock", true];
private _regenMins = _logic getVariable ["RegenMins", -1];
[_pos, _dir, _stock, _restock, _regenMins] remoteExec ["ACME_fnc_bloodFridgeSpawn", 2];

if (!isNull _logic) then { deleteVehicle _logic; };
