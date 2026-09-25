/* B121 acknowledged owner request. Inventory/source reservation stays provider-local. Hardcore incremental
   syringe pushes add opaque settlement metadata at field 7; ordinary callers keep the historical contract. */
params ["_medic","_patient","_bodyPart",["_doses",[]],["_operation","administer"],["_site",-2],["_refund",[]],["_meta",[]]];
private _hcPush = _meta isEqualType [] && {(_meta param [0,""]) == "hcPush"};
private _fail = {
    if (!isNull _medic && {local _medic}) then {
        [_medic,_refund,false] call ACME_fnc_medicationRefund;
        if (_hcPush) then {[_medic,_meta,false,"local validation failed"] call ACME_fnc_hardcorePushAck;};
    };
    false
};
if (isNull _medic || {!local _medic} || {!alive _medic} || {isNull _patient}) exitWith {call _fail};
private _outOfRange = if (_hcPush) then {
    private _leash = missionNamespace getVariable ["ACM_circulation_AEDDistanceLimit",5];
    ((objectParent _medic) isNotEqualTo (objectParent _patient)) || {_medic distance _patient > _leash}
} else {
    _medic distance _patient > 5 && {isNull objectParent _medic || {objectParent _medic != objectParent _patient}}
};
if (_outOfRange) exitWith {call _fail};
if !(_operation in ["administer","flush"] && {_doses isEqualType []} && {_bodyPart isEqualType ""} && {_site in [-2,-1,0,1,2]}) exitWith {call _fail};
if (_operation == "administer" && {_doses isEqualTo []}) exitWith {call _fail};
if ((_doses findIf {!(_x isEqualType []) || {count _x < 4} || {!((_x select 1) isEqualType 0)}
    || {!finite (_x select 1)} || {(_x select 1) <= 0}
    || {!([_x select 0,_x select 2,true,_x param [5,false]] call ACME_fnc_medicationRouteAllowed)}}) >= 0) exitWith {call _fail};
_bodyPart = toLowerANSI _bodyPart;
if (_bodyPart == "ej") then {_bodyPart = "head";};
private _iv = _operation == "flush" || {(_doses findIf {_x select 2}) >= 0};
private _identity = if (_iv) then {[_patient,_bodyPart,_site] call ACME_fnc_medicationLineIdentity} else {[]};
if (_iv && {_identity isEqualTo []}) exitWith {call _fail};
if (_iv) then {_site = _identity select 0;};
// Never inject medication into an access while blood is actively traversing that exact line.
// Empty bags, stopped lines and blood on another access do not block the request.
if (_operation == "administer" && {_iv} && {[_patient,_bodyPart,_site] call ACME_fnc_medicationLineBloodBusy}) exitWith {call _fail};
private _serial = (missionNamespace getVariable ["ACME_medicationRequestSerial",0]) + 1;
missionNamespace setVariable ["ACME_medicationRequestSerial",_serial];
private _id = format ["medicationB14:%1:%2:%3:%4",netId _medic,clientOwner,diag_tickTime,_serial];
private _args = [_patient,_medic,[_patient] call ACME_fnc_clinicalEpoch,_id,_operation,_bodyPart,_doses,_site,_identity,_meta];
private _escrow = _medic getVariable ["ACME_medicationEscrow",createHashMap];
_escrow set [_id,[_patient,_args,_refund,0,0,_meta]];
[_medic,_escrow] call ACME_fnc_medicationEscrowCommit;
[_medic] call ACME_fnc_ownerRegister;
[_patient,"medicationLine",_args] call ACME_fnc_ownerDispatch;
true
