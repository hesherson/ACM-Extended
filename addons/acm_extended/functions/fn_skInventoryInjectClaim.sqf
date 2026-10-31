/* An accepted custody claim has a server-funded journal before this private
 * continuation runs. BEGIN must be acknowledged before solution is debited. */
params ["_accepted","_args"];
_args params ["_medic","_patient","_bodyPart","_doses","_site","_row","_remaining","_refundRow","_request",["_successItems",[]],["_journal",[]]];
private _sid = _row param [11,"",[""]];
if (isNull _medic || {!local _medic}) exitWith {};
private _rows = +(_medic getVariable ["ACME_narcStore",[]]);
private _idx = _rows findIf {(_x param [11,"",[""]]) == _sid};
if (!_accepted || {_idx < 0} || {!alive _medic} || {isNull _patient}) exitWith {
    if (!_accepted && {_journal isEqualTo []}) then {[_medic,_request,false,[_sid,+_row]] call ACME_fnc_inventoryLedgerSettle;}
    else {["recover",_medic,_request,[]] call ACME_fnc_syringeDeliveryRequest;};
};
private _current = _rows select _idx;
private _unchanged = (_current param [0,""]) == (_row param [0,""])
    && {(_current param [1,0]) == (_row param [1,0])}
    && {(_current param [2,0]) == (_row param [2,0])}
    && {(_current param [4,0]) == (_row param [4,0])}
    && {(_current param [5,[]]) isEqualTo (_row param [5,[]])};
if (!_unchanged) exitWith {["recover",_medic,_request,[]] call ACME_fnc_syringeDeliveryRequest;};
_bodyPart = toLowerANSI _bodyPart;
if (_bodyPart == "ej") then {_bodyPart = "head";};
private _iv = (_doses findIf {_x param [2,false]}) >= 0;
private _identity = if (_iv) then {[_patient,_bodyPart,_site] call ACME_fnc_medicationLineIdentity} else {[]};
if (_iv && {_identity isEqualTo []}) exitWith {["recover",_medic,_request,[]] call ACME_fnc_syringeDeliveryRequest;};
if (_iv) then {_site = _identity select 0;};
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
if (_journal isEqualTo []) exitWith {
    private _capture = +_args;
    while {count _capture < 10} do {_capture pushBack [];};
    _capture set [2,_bodyPart]; _capture set [4,_site];
    _capture set [10,[+_identity,_epoch]];
    ["begin",_medic,_request,[_request,"inject",_patient,_bodyPart,_site,_identity,_epoch],ACME_fnc_skInventoryInjectClaim,_capture] call ACME_fnc_syringeDeliveryRequest;
};
// Revalidation may stop this request, but cannot change the exact BEGIN binding.
if (_journal isNotEqualTo [_identity,_epoch]
    || {_medic getVariable ["ACE_isUnconscious",false]}
    || {_medic distance _patient > 5 && {isNull objectParent _medic || {objectParent _medic != objectParent _patient}}}
    || {_iv && {[_patient,_bodyPart,_site] call ACME_fnc_medicationLineBloodBusy}}) exitWith {
    ["stop",_medic,_request,[_request,"pre-dispatch-validation"]] call ACME_fnc_syringeDeliveryRequest;
};
private _delta = [(_row param [2,0])-(_remaining param [2,0]),(_row param [4,0])-(_remaining param [4,0]),[]];
private _parts = _row param [5,[]];
private _remainingParts = _remaining param [5,[]];
private _components = [];
{
    private _source = _x param [0,""];
    private _left = if (_remaining isEqualTo []) then {0} else {(_remainingParts param [_forEachIndex,[]]) param [1,0]};
    _components pushBack [_forEachIndex,_source,(_x param [1,0])-_left];
} forEach _parts;
_delta set [2,_components];
private _hidden = _medic getVariable ["ACME_syringeInventoryHidden",[]];
_hidden pushBackUnique _sid;
_medic setVariable ["ACME_syringeInventoryHidden",_hidden,false];
if (_remaining isEqualTo []) then {_rows deleteAt _idx;} else {_rows set [_idx,+_remaining];};
if !([_medic,_rows,false] call ACME_fnc_narcStoreCommit) exitWith {
    ["stop",_medic,_request,[_request,"provider-store-unavailable"]] call ACME_fnc_syringeDeliveryRequest;
};
private _batch = _request + ":inject";
private _meta = ["syringeB279",_request,_sid];
private _wire = [_patient,_medic,_epoch,_batch,"administer",_bodyPart,_doses,_site,_identity,_meta];
["batch",_medic,_request,[_request,_batch,_wire,_delta]] call ACME_fnc_syringeDeliveryRequest;
["stop",_medic,_request,[_request,"inject-complete"]] call ACME_fnc_syringeDeliveryRequest;
if (hasInterface && {_medic isEqualTo ACE_player} && {!isNull findDisplay 84000}) then {
    call ACME_fnc_skRefreshDrawn;
    call ACME_fnc_skBuildHotspots;
};
