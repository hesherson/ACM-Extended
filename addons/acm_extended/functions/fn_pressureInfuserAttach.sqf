params [["_pane", "transfusion"]];
/* Select the physical bag with fn_getSelectedActiveBagContext.sqf's full layout.
   The pressure infuser is reusable: possession is required for a new cuff application, but the item is never consumed.
   The patient owner validates and commits the per-bag cuff state. */
if (!hasInterface) exitWith {};
private _display = findDisplay 86000;
if (isNull _display || {(_display getVariable ["ACME_txActivePane", "transfusion"]) != _pane}) exitWith {};
private _ctx = [_pane] call ACME_fnc_getSelectedActiveBagContext;
if !([_ctx, _pane == "infusion"] call ACME_fnc_pressureInfuserCan) exitWith {};
if (count _ctx < 11) exitWith {
    ["Select a running bag first.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
_ctx params ["_patient", "_part", "_index", "_type", "_accessType", "_site", "_iv", "_bloodType", "_volume", "_freshId", "_remaining"];
if (isNull _patient || {_index < 0}) exitWith {};
private _bags = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_part, []];
private _bag = _bags param [_index, []];
if (count _bag < 8 || {(_bag select 0) != _type} || {(_bag select 3) != _site}
    || {(_bag select 4) != _iv} || {(_bag select 5) != _bloodType}
    || {(_bag select 6) != _volume} || {(_bag select 7) != _freshId}) exitWith {
    ["The selected bag changed. Refresh the selection before applying a cuff.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
private _bagId = _bag param [8, ""];
if (_bagId == "") exitWith {
    ["Bag state is synchronizing. Select it again after the next medical update.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
private _pending = missionNamespace getVariable ["ACME_piPending", createHashMap];
if (((values _pending) findIf { !(_x select 3) && {(_x select 0) isEqualTo _patient} && {((_x select 1) select 2) == _bagId} }) >= 0) exitWith {};
private _isNewCuff = !(_bagId in (_patient getVariable ["ACME_piCuffs", createHashMap]));
if (_isNewCuff && {([ACE_player, _patient, "ACME_PressureInfuser"] call ACME_fnc_treatmentSupplyCount) < 1}) exitWith {
    ["No pressure infuser carried.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
private _seq = (missionNamespace getVariable ["ACME_piSequence", 0]) + 1;
missionNamespace setVariable ["ACME_piSequence", _seq];
private _id = format ["cuff:%1:%2:%3", clientOwner, netId ACE_player, _seq];
private _args = [_patient, ACE_player, _bagId, [_patient] call ACME_fnc_clinicalEpoch, _id, CBA_missionTime, _isNewCuff, _pane == "infusion"];
_pending set [_id, [_patient, _args, CBA_missionTime, false]];
missionNamespace setVariable ["ACME_piPending", _pending];
[_patient, "pressureCuff", _args] call ACME_fnc_ownerDispatch;
