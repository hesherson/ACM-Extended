// pull the selected hung bag off its access without tearing down the y tube. the bag is moved into the used bags
// store of the medic, ACME_usedBags on ACE_player, carrying its exact remaining volume, and it shows up in the
// available list, 86005, as a colored [Used] row that can be re-hung later, because fn_transfusionspikeoradd
// recognizes the |USED marker.
// on y structure persistence: pulling a bag from a y'd access does not delete its slot. the entry is retagged in
// place to the matching empty marker, [empty blood bag] as ACME_Empty and [empty saline bag] as
// ACME_EmptySaline, exactly as when a bag runs dry. that keeps the structure of the y line, and the index of
// every other bag, stable however many bags are pulled, and only discard y tubing tears the line down. on a
// plain, non-y access the slot is simply removed as before.
// it works from the transfusion list only. pull bag must never resolve to a drug infusion, because pulling the
// carrier out from under a running infusion is exactly the cross-contamination we are eliminating. so the target
// is taken solely from the transfusion list selection, 86004, rather than the infusions sub-list or a stale
// tracked pick that might have come from it.
// this is the exact-volume replacement of the mod for ACM's native remove bag, which rounds the return to 250,
// 500 or 1000 and discards anything under 250 ml. the action of the remove bag button is redirected here in
// config.
// call it as [] call ACME_fnc_transfusionPullBag.
private _display = findDisplay 86000;
if (isNull _display) exitWith {};
private _ctrlActive = _display displayCtrl 86004;
private _target = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
if (isNull _target || {_part == ""}) exitWith {};
private _map = _target getVariable ["ACM_circulation_IV_Bags", createHashMap];
private _arr = _map getOrDefault [_part, []];
private _idx = -1;
if (!isNull _ctrlActive) then {
    private _sel = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags", []];
    private _row = lbCurSel _ctrlActive;
    private _value = if (_row >= 0) then {_ctrlActive lbValue _row} else {-1};
    if (_value >= 0 && {_value < count _sel}) then {_idx = (_sel select _value) param [8,-1];};
};
if (_idx < 0 || {_idx >= count _arr}) exitWith {["Select a hung bag to pull.",2,ACE_player,13] call ace_common_fnc_displayTextStructured;};
private _bag = +(_arr select _idx);
private _type = _bag param [0,""];
if (_type == "FBTK") exitWith {call ACM_circulation_fnc_TransfusionMenu_RemoveBag;};
private _uid = _bag param [8,"",[""]];
private _sig = +(_bag select [0,8]);
private _requestId = format ["txpull:%1:%2:%3",clientOwner,diag_frameNo,floor(diag_tickTime*1000)];
private _pending=uiNamespace getVariable ["ACME_txPullPending",createHashMap];
_pending set [_requestId,[ACE_player,_target]];
uiNamespace setVariable ["ACME_txPullPending",_pending];
[_target,"transfusionPull",[_target,ACE_player,_part,_uid,_idx,_sig,[_target] call ACME_fnc_clinicalEpoch,_requestId,serverTime]] call ACME_fnc_ownerDispatch;
