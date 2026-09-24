// refresh the five tray slots: the item counts, which slot is enabled for the current step, and a highlight on the
// held tool. the scope is usable before insertion, and the tube only once the airway is locked open.
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_laryngo_dlg", displayNull];
if (isNull _dlg) exitWith {};
private _medic = uiNamespace getVariable ["ACME_laryngo_medic", ACE_player];
private _state = uiNamespace getVariable ["ACME_laryngo_state", "idle"];
private _held  = uiNamespace getVariable ["ACME_laryngo_held", ""];
private _patient = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
private _trayVisible = !(uiNamespace getVariable ["ACME_suction_standalone", false]);

private _scopeN = [_medic, "ACME_Laryngoscope"] call ACME_fnc_itemCount;
private _tubeN  = [_medic, "ACME_ETTube"] call ACME_fnc_itemCount;
(_dlg displayCtrl 87862) ctrlSetText format ["x%1", _scopeN];
(_dlg displayCtrl 87866) ctrlSetText format ["x%1", _tubeN];

// every slot is always clickable. there is no graying out: if you want to pick a thing up, pick it up. whether it
// does anything useful yet is decided when you try to use it, rather than by the tray refusing to hand it over.
{
    (_dlg displayCtrl _x) ctrlEnable true;
} forEach [87863, 87867, 87873, 87877];
// the counts reflect what is left. a consumable that has been used shows nothing and dims, so the tray is an honest
// picture of what is still available rather than a fixed row of x1s.
private _syrLeft = if (uiNamespace getVariable ["ACME_laryngo_syringeUsed", false]) then {0} else {1};
private _colLeft = if (uiNamespace getVariable ["ACME_laryngo_collarUsed", false]) then {0} else {1};
(_dlg displayCtrl 87872) ctrlSetText (if (_syrLeft > 0) then {"x1"} else {""});
(_dlg displayCtrl 87876) ctrlSetText (if (_colLeft > 0) then {"x1"} else {""});
// Refresh the shared selection, tray artwork, count and availability together.
[true] call ACME_fnc_suctionSelectDevice;

// Pinned/placed instruments are still out of the tray when the hand changes tools.
// Read the actual patient on reopen; these are visual reads, never treatment writes.
private _tubePlaced = !isNull _patient && {_patient getVariable ["ACME_ETT_Inserted", false]};
private _collarPlaced = !isNull _patient && {_patient getVariable ["ACME_ETT_Secured", false]};
[_dlg displayCtrl 87861, _held == "scope" || {uiNamespace getVariable ["ACME_laryngo_bladeLocked", false]},
    _scopeN, _trayVisible] call ACME_fnc_traySlotState;
[_dlg displayCtrl 87865, _held == "tube" || {_tubePlaced}
    || {uiNamespace getVariable ["ACME_laryngo_tubeIn", false]}
    || {(uiNamespace getVariable ["ACME_laryngo_tubeDepth", 0]) > 0.001},
    _tubeN, _trayVisible] call ACME_fnc_traySlotState;
[_dlg displayCtrl 87871, _held == "syringe" || {_syrLeft == 0}, _syrLeft, _trayVisible] call ACME_fnc_traySlotState;
[_dlg displayCtrl 87875, _held == "collar" || {_colLeft == 0} || {_collarPlaced},
    _colLeft, _trayVisible] call ACME_fnc_traySlotState;

// the held-tool highlight, a blue box like the vent selection model, and otherwise the plain dark slot.
(_dlg displayCtrl 87860) ctrlSetBackgroundColor (if (_held == "scope") then {[0.16, 0.42, 0.58, 0.90]} else {[0, 0, 0, 0.85]});
(_dlg displayCtrl 87864) ctrlSetBackgroundColor (if (_held == "tube")  then {[0.16, 0.42, 0.58, 0.90]} else {[0, 0, 0, 0.85]});
(_dlg displayCtrl 87874) ctrlSetBackgroundColor (if (_held == "collar")  then {[0.16, 0.42, 0.58, 0.90]} else {[0, 0, 0, 0.85]});
(_dlg displayCtrl 87870) ctrlSetBackgroundColor (if (_held == "syringe") then {[0.16, 0.42, 0.58, 0.90]} else {[0, 0, 0, 0.85]});
(_dlg displayCtrl 87880) ctrlSetBackgroundColor (
    if (uiNamespace getVariable ["ACME_laryngo_sucPinned", false]) then {[0.20, 0.55, 0.32, 0.90]}
    else { if (_held == "suction") then {[0.16, 0.42, 0.58, 0.90]} else {[0, 0, 0, 0.85]} }
);
