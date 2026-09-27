// Refresh the IV/EJ tray counts and stationary silhouettes. A removed item leaves
// its original logo blacked out; the band remains out while applied to the limb.
// it is called on init and after every grab, return, stick and miss. the name is kept for the existing call
// sites.
private _dlg = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (isNull _dlg) exitWith {};

private _medic  = uiNamespace getVariable ["ACME_IV_Medic", objNull];
private _held   = uiNamespace getVariable ["ACME_IV_Held", "none"];
private _gauge  = uiNamespace getVariable ["ACME_IV_Gauge", 16];
private _bandOn = uiNamespace getVariable ["ACME_IV_BandOn", false];

private _count = {
    params ["_item"];
    if (isNull _medic) exitWith {0};
    [_medic, uiNamespace getVariable ["ACME_IV_Patient", objNull], _item] call ACME_fnc_treatmentSupplyCount
};
private _nBand = ["ACME_NARBOA"] call _count;
private _n14   = ["ACM_IV_14g"]  call _count;
private _n16   = ["ACM_IV_16g"]  call _count;
private _n18   = ["ACM_IV_18g"]  call _count;
private _n20   = ["ACM_IV_20g"]  call _count;

// the labels are "<name> xN", dimmed to 0.30 alpha when empty.
private _setLbl = {
    params ["_idc", "_base", "_n", "_col"];
    private _c = _dlg displayCtrl _idc;
    _c ctrlSetText (format ["%1  x%2", _base, _n]);
    _c ctrlSetTextColor (if (_n > 0) then {_col} else {[_col select 0, _col select 1, _col select 2, 0.30]});
};
[86533, "BAND", _nBand, [0.95, 0.80, 0.80, 1]] call _setLbl;
[86542, "14g",  _n14,   [0.85, 0.92, 1, 1]]    call _setLbl;
[86546, "16g",  _n16,   [0.90, 0.95, 1, 1]]    call _setLbl;
[86550, "18g",  _n18,   [0.75, 0.90, 1, 1]]    call _setLbl;
[86558, "20g",  _n20,   [0.70, 0.88, 1, 1]]    call _setLbl;
// the pad: alcohol prep is cosmetic and optional, with no consumable item, so no count is shown.

// Keep the independent slot buttons unchanged; silhouettes never become new items.
[_dlg displayCtrl 86531, _bandOn || {_held == "band"}, _nBand,
    !(uiNamespace getVariable ["ACME_IV_EJMode", false])] call ACME_fnc_traySlotState;
[_dlg displayCtrl 86536, _held == "pad"] call ACME_fnc_traySlotState;
{
    _x params ["_idc", "_g", "_stock"];
    [_dlg displayCtrl _idc, _held == "needle" && {_gauge == _g}, _stock] call ACME_fnc_traySlotState;
} forEach [[86541, 14, _n14], [86545, 16, _n16], [86549, 18, _n18], [86557, 20, _n20]];
[_dlg displayCtrl 86553, _held == "line", 1,
    missionNamespace getVariable ["ACME_iv_lineSlot", false]] call ACME_fnc_traySlotState;

// the ej uses no band. keep the whole band slot hidden regardless of bandon, because this refresh runs from many
// call sites and would otherwise re-show the band icon when bandon flips.
if (uiNamespace getVariable ["ACME_IV_EJMode", false]) then {
    { (_dlg displayCtrl _x) ctrlShow false; } forEach [86530, 86531, 86532, 86533];
};
