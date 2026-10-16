/* Each click captures the visible saline UID and active service identity, not just a reusable site number. */
params [["_mode", "auto", [""]]];
private _p = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
if (isNull _p || {isNull (findDisplay 86000)} || {isNull ACE_player}) exitWith {false};
private _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _iv = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _site = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
([_p,_part,_iv,_site] call ACME_fnc_yServiceState) params ["_reserve","_reserved","_blood","_dirty","_primed","_kind","_reserveId","_job"];
if (_reserveId == "") exitWith {false};
if (_mode == "auto") then {_mode = ["prime", "flush"] select _primed;};
// Flush and right-click cancellation belong to the selected reserve bag. Prime
// remains available from either unprimed Y branch.
if (_mode in ["flush","cancel"]) then {
    private _context = ["transfusion"] call ACME_fnc_getSelectedActiveBagContext;
    private _bags = (_p getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]];
    private _selectedId = if (count _context >= 13 && {(_context select 0) isEqualTo _p}
        && {(_context select 1) == _part} && {(_context select 5) == _site}
        && {(_context select 6) isEqualTo _iv} && {(_context select 3) in ["Saline","ACME_SalineY"]}) then {
        (_bags param [_context select 2,[]]) param [8,""]
    } else {""};
    if (_selectedId != _reserveId) then {_mode = "";};
};
if (_mode == "") exitWith {false};
private _eligible = if (_mode == "cancel") then {_kind == "flush" && {count (_job param [9,[]]) > 0}} else {
    ([_mode,_reserve,_reserved,_blood,_dirty,_primed,_kind] call ACME_fnc_yServicePlan) select 0
};
if (!_eligible) exitWith {false};
private _seq = (missionNamespace getVariable ["ACME_yServiceSequence", 0]) + 1;
missionNamespace setVariable ["ACME_yServiceSequence", _seq];
private _id = format ["ys:%1:%2:%3", clientOwner, netId ACE_player, _seq];
[_p, "yFlush", [_p, ACE_player, _part, _iv, _site, [_p] call ACME_fnc_clinicalEpoch, _mode, _id, serverTime, _reserveId, _job param [13, ""]]] call ACME_fnc_ownerDispatch;
true
