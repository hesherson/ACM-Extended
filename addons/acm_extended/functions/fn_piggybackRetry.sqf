/* Unknown delivery is not rejection: retain exact escrow until an owner-authored terminal receipt arrives. */
params ["_id"];
private _requests = missionNamespace getVariable ["ACME_piggybackRequests",createHashMap];
private _pending = _requests getOrDefault [_id,[]];
if (_pending isEqualTo [] || {_pending param [2,false]}) exitWith {};
private _args = _pending select 0;
private _provider = _args select 0;
private _patient = _args select 1;
if (isNull _provider || {!local _provider}) exitWith {};
if (isNull _patient) exitWith {};
[_patient,"piggybackAttach",_args] call ACME_fnc_ownerDispatch;
// Keep reconciliation active but bounded. A later menu reopening can retry retained requests.
if (CBA_missionTime - (_pending select 1) <= 120) then {
    [{_this call ACME_fnc_piggybackRetry;},[_id],1] call CBA_fnc_waitAndExecute;
} else {
    [ACE_player,"Piggyback connection is awaiting owner confirmation. The prepared bag remains reserved; reopen the menu to reconcile."] call ACME_fnc_clinicalNotice;
};
