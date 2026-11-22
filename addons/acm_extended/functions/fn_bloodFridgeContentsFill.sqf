// fill the blood fridge contents screen.
// call ACME_fnc_bloodFridgeContentsFill, from the onload of the dialog.
// it reads the live stock off the fridge rather than a snapshot, so what is on screen is what is in the box.
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_bfc_dlg", displayNull];
private _fridge = uiNamespace getVariable ["ACME_bfc_fridge", objNull];
if (isNull _dlg) exitWith {};

private _stock = if (isNull _fridge) then { [] } else { _fridge getVariable ["ACME_bf_stock", []] };

// the display names, in the order a medic thinks about them: the universal donor first, then the rest.
private _names = createHashMapFromArray [
    ["ACME_BloodBag_ON_500",  ["O NEG", "universal donor"]],
    ["ACME_BloodBag_O_500",   ["O POS", ""]],
    ["ACME_BloodBag_AN_500",  ["A NEG", ""]],
    ["ACME_BloodBag_A_500",   ["A POS", ""]],
    ["ACME_BloodBag_BN_500",  ["B NEG", ""]],
    ["ACME_BloodBag_B_500",   ["B POS", ""]],
    ["ACME_BloodBag_ABN_500", ["AB NEG", ""]],
    ["ACME_BloodBag_AB_500",  ["AB POS", "universal recipient"]]
];
private _order = ["ACME_BloodBag_ON_500","ACME_BloodBag_O_500","ACME_BloodBag_AN_500","ACME_BloodBag_A_500",
                  "ACME_BloodBag_BN_500","ACME_BloodBag_B_500","ACME_BloodBag_ABN_500","ACME_BloodBag_AB_500"];

private _have = createHashMap;
{ _x params ["_cls", "_n"]; _have set [_cls, ((_have getOrDefault [_cls, 0]) + _n)]; } forEach _stock;

private _txt = "";
private _total = 0;
{
    private _n = _have getOrDefault [_x, 0];
    _total = _total + _n;
    (_names getOrDefault [_x, [_x, ""]]) params ["_label", "_note"];
    // empty rows stay on the list, grayed. a medic needs to see that o neg is out, rather than only that it is
    // absent.
    private _col = if (_n > 0) then { "#e8e2d6" } else { "#4a4d55" };
    private _qty = if (_n > 0) then { str _n } else { "0" };
    private _vol = if (_n > 0) then { format ["%1 mL", _n * 500] } else { "" };
    _txt = _txt + format [
        "<t color='%1' size='1.0'>%2</t><t color='%1' size='0.85'>   %3</t><br/>",
        _col, _label, _note
    ];
    _txt = _txt + format [
        "<t color='%1' align='right' size='1.0'>%2 units    %3</t><br/>", _col, _qty, _vol
    ];
} forEach _order;
(_dlg displayCtrl 87622) ctrlSetStructuredText parseText _txt;

private _restock = if (isNull _fridge) then { false } else { _fridge getVariable ["ACME_bf_restock", false] };
private _mins = if (isNull _fridge) then { 0 } else { _fridge getVariable ["ACME_bf_regenMins", 1440] };
private _sub = format ["%1 units on hand, %2 mL total", _total, _total * 500];
(_dlg displayCtrl 87621) ctrlSetText _sub;

private _foot = if ((["real"] call ACME_fnc_bloodTiming) && {["spoil"] call ACME_fnc_bloodTiming}) then {
    private _remaining = ((["fridge"] call ACME_fnc_bloodTiming) - (([] call ACME_fnc_clinicalClock) - (_fridge getVariable ["ACME_bf_lotStart",([] call ACME_fnc_clinicalClock)]))) max 0;
    format ["<t color='#8a9099' size='0.9'>Refrigerated stock expires in %1 hours. Time outside controlled storage counts against the unit's use window.</t><br/>",ceil (_remaining/3600)]
} else {""};
if (_restock) then {
    private _h = floor (_mins / 60);
    private _m = _mins - (_h * 60);
    _foot = _foot + format ["<t color='#6f9a6f' size='0.9'>Restocks to its configured load every %1 h %2 min.</t>", _h, _m];
} else {
    _foot = _foot + "<t color='#9a6f6f' size='0.9'>No restock. What is in here is what there is.</t>";
};
(_dlg displayCtrl 87623) ctrlSetStructuredText parseText _foot;
