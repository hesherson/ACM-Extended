/* Select from the treating provider, not the casualty or the last menu action.
   ACCUVAC takes priority. A consumed manual bag belongs to this local airway session.
   Call with true for an input event; the existing render loop checks at most 4 Hz. */
disableSerialization;
params [["_force", false, [false]]];
private _dlg = uiNamespace getVariable ["ACME_laryngo_dlg", displayNull];
if (isNull _dlg) exitWith {-1};
private _now = diag_tickTime;
if (!_force && {_now < (_dlg getVariable ["ACME_suctionNextInventory", -1])}) exitWith {
    uiNamespace getVariable ["ACME_suction_type", -1]
};
_dlg setVariable ["ACME_suctionNextInventory", _now + 0.25];
private _medic = uiNamespace getVariable ["ACME_laryngo_medic", objNull];
private _patient = uiNamespace getVariable ["ACME_laryngo_patient", objNull];
private _opened = !isNull _medic && {!isNull _patient} && {
    (uiNamespace getVariable ["ACME_suction_bagOwner", []]) isEqualTo [_medic, _patient]
};
private _accuN = if (isNull _medic) then {0} else {[_medic, "ACM_ACCUVAC"] call ACME_fnc_itemCount};
private _bagN = if (isNull _medic) then {0} else {[_medic, "ACM_SuctionBag"] call ACME_fnc_itemCount};
private _type = -1;
if (!isNull _medic && {!isNull _patient}) then {
    if (_accuN > 0) then {_type = 1;} else {
        if (_opened || {_bagN > 0}) then {_type = 0;};
    };
};
private _old = uiNamespace getVariable ["ACME_suction_type", -2];
if (_type != _old) then {
    // Stop the previous pump before changing device models. Keep a used bag's fill.
    if (uiNamespace getVariable ["ACME_laryngo_sucOn", false]) then {
        [_medic] call ACME_fnc_suctionSfxStop;
    };
    uiNamespace setVariable ["ACME_laryngo_sucOn", false];
    uiNamespace setVariable ["ACME_laryngo_sucPinned", false];
    uiNamespace setVariable ["ACME_laryngo_sucMode", "clear"];
    uiNamespace setVariable ["ACME_laryngo_sucFrame", 0];
    uiNamespace setVariable ["ACME_laryngo_sucNext", 0];
    uiNamespace setVariable ["ACME_suction_sqT0", -1];
    if (_type >= 0 && {uiNamespace getVariable ["ACME_suction_standalone", false]}
        && {_old < 0}) then {uiNamespace setVariable ["ACME_laryngo_held", "suction"];};
};
if (_type < 0) then {
    // A restored pin is not equipment when this provider has no usable device.
    uiNamespace setVariable ["ACME_laryngo_sucPinned", false];
    if ((uiNamespace getVariable ["ACME_laryngo_held", ""]) == "suction") then {
        uiNamespace setVariable ["ACME_laryngo_held", ""];
    };
    (_dlg displayCtrl 87916) ctrlSetTextColor [1,1,1,0];
};
private _dev = [_type] call ACME_fnc_suctionDevice;
uiNamespace setVariable ["ACME_suction_type", _type];
uiNamespace setVariable ["ACME_suction_device", _dev];
(_dlg displayCtrl 87881) ctrlSetText (_dev getOrDefault ["tray", ""]);
private _stock = switch (_type) do {case 1: {_accuN}; case 0: {_bagN + ([0,1] select _opened)}; default {0};};
(_dlg displayCtrl 87882) ctrlSetText (if (_stock > 0) then {format ["x%1", _stock]} else {""});
// This inventory refresh also runs while a different tool is held. A pinned
// Yankauer remains out of the tray and must not regain its full-color logo.
[_dlg displayCtrl 87881,
    (uiNamespace getVariable ["ACME_laryngo_held", ""]) == "suction"
        || {uiNamespace getVariable ["ACME_laryngo_sucPinned", false]},
    _stock, !(uiNamespace getVariable ["ACME_suction_standalone", false])] call ACME_fnc_traySlotState;
(_dlg displayCtrl 87883) ctrlEnable (_stock > 0);
(_dlg displayCtrl 87883) ctrlSetTooltip (if (_stock > 0) then {
    format ["Pick up / return %1", _dev getOrDefault ["name", "suction"]]
} else {"No suction device carried"});
_type
