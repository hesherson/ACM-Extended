// Owner-authoritative placement of one provider-owned used bag onto the selected access.
params [
    ["_patient",objNull,[objNull]],["_medic",objNull,[objNull]],["_part","",[""]],["_iv",true,[true]],["_site",-1,[0]],
    ["_usedId","",[""]],["_record",[],[[]]],["_epoch",-1,[0]],["_requestId","",[""]],["_warmer",false,[false]],["_issued",-1,[0]]
];
if (isNull _patient || {!local _patient} || {_requestId==""}) exitWith {false};
if (count _requestId > 128 || {_usedId == ""} || {count _usedId > 128}
    || {!finite _issued} || {_issued < 0} || {serverTime - _issued > 10} || {_issued > serverTime + 2}) exitWith {false};
private _receiptTimes = _patient getVariable ["ACME_usedRehangReceiptTimes",createHashMap];
private _receipts=_patient getVariable ["ACME_usedRehangReceipts",createHashMap];
private _prior=_receipts getOrDefault [_requestId,[]];
if !(_prior isEqualTo []) exitWith {if (!isNull _medic) then {["ACME_rehangUsedBagResult",_prior,_medic] call CBA_fnc_targetEvent;}; _prior param [2,false]};
{if (serverTime - (_receiptTimes get _x) > 12) then {_receipts deleteAt _x; _receiptTimes deleteAt _x;};} forEach keys _receiptTimes;
if (count _receipts >= 512) exitWith {false};
private _reply={params ["_ok",["_reason","",[""]],["_bagUid","",[""]]]; private _payload=[_patient,_requestId,_ok,_usedId,_record,_part,_reason,_bagUid]; _receipts set [_requestId,_payload]; _receiptTimes set [_requestId,serverTime]; [_patient,"ACME_usedRehangReceipts",_receipts] call ACME_fnc_setVarNet; [_patient,"ACME_usedRehangReceiptTimes",_receiptTimes] call ACME_fnc_setVarNet; if (!isNull _medic) then {["ACME_rehangUsedBagResult",_payload,_medic] call CBA_fnc_targetEvent;}; _ok};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {[false,"Patient state changed. Reopen the transfusion menu."] call _reply};
if (isNull _medic || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)} || {(_medic distance _patient)>ace_medical_gui_maxDistance}) exitWith {[false,"Provider can no longer hang that used bag."] call _reply};
if (count _record < 7 || {(_record param [0,""]) != _usedId} || {!(_site in (if (_iv) then {[0,1,2]} else {[0]}))}) exitWith {[false,"Used-bag record is invalid."] call _reply};
private _hasAccess=if (_iv) then {[_patient,_part,0,_site] call ACM_circulation_fnc_hasIV}else{[_patient,_part,0] call ACM_circulation_fnc_hasIO};
if (!_hasAccess) exitWith {[false,"That access is no longer available."] call _reply};

_record params ["",["_type","",[""]],["_remVol",0,[0]],["_oldAccessType",0,[0]],["_bloodType",-1,[0]],["_origVol",1000,[0]],["_name","",[""]],["_freshBloodID",-1,[0]]];
if (!finite _remVol || {!finite _origVol} || {_origVol <= 0} || {_remVol > _origVol} || {_remVol <= 0} || {_type in ["","ACME_Empty","ACME_EmptySaline"]}) exitWith {[false,"That used bag is empty."] call _reply};
private _serviceKey=toLowerANSI format ["%1#%2#%3",_part,_iv,_site];
if ((_patient getVariable ["ACME_yFlushJobs",createHashMap]) getOrDefault [_serviceKey,[]] isNotEqualTo []) exitWith {[false,"Finish priming/flushing this line first."] call _reply;};
// A pulled/used bag must not bypass the same post-two-unit Y flush gate as a new blood bag.
if (_type in ["Blood","FreshBlood"] && {[_patient,_part,_iv,_site] call ACME_fnc_isYLineAccess}
    && {(_patient getVariable ["ACME_YLineDirty",createHashMap]) getOrDefault [_serviceKey,false]}) exitWith {
    [false,"Flush this Y line before hanging more blood."] call _reply
};
private _occupied = false;
if ([_patient,_part,_iv,_site] call ACME_fnc_isYLineAccess) then {
    private _sameTypes = if (_type in ["Blood","FreshBlood"]) then {["Blood","FreshBlood"]} else {["Saline","ACME_SalineY"]};
    private _rows = (_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]];
    if ((_rows findIf {(_x param [0,""]) in _sameTypes && {(_x param [1,0]) > 0.01} && {(_x param [3,-1]) == _site} && {(_x param [4,true]) isEqualTo _iv}}) >= 0) exitWith {
        // The result is returned below from the parent scope, not merely from this inner if block.
        _occupied = true;
    };
};
if (_occupied) exitWith {[false,"A live bag already occupies that Y limb."] call _reply};
private _pi=ACME_infusion_bodyParts find toLowerANSI _part;
if (_pi<0) exitWith {[false,"Invalid access location."] call _reply};

// A provider can have only one pending copy of this valid local used record. Claim only after every rejectable
// record/access check above, so a malformed/stale request can never leave a permanent patient-side claim behind.
private _claimKey=format ["%1:%2",netId _medic,_usedId];
private _claims=_patient getVariable ["ACME_usedRehangClaims",createHashMap];
{private _c = _claims get _x; if (_c isEqualType [] && {serverTime - (_c param [1,serverTime]) > 12}) then {_claims deleteAt _x;};} forEach keys _claims;
if (count _claims >= 512) exitWith {[false,"Used-bag queue is busy. Try again shortly."] call _reply};
if (_claimKey in _claims) exitWith {[false,"That used bag is already being hung."] call _reply};
_claims set [_claimKey,[_requestId,serverTime]]; [_patient,"ACME_usedRehangClaims",_claims] call ACME_fnc_setVarNet;
private _accessType=[_patient,_iv,_pi,_site] call ACM_circulation_fnc_getAccessType;
private _seq=(_patient getVariable ["ACME_bagSequence",0])+1; _patient setVariable ["ACME_bagSequence",_seq,true];
private _bagUid=format ["%1:%2:%3:%4",netId _patient,_epoch,clientOwner,_seq];
private _entry=[_type,_remVol,_accessType,_site,_iv,_bloodType,_origVol,_freshBloodID,_bagUid];
private _map=_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]; private _arr=+(_map getOrDefault [_part,[]]);
private _wantMarker=["ACME_EmptySaline","ACME_Empty"] select (_type in ["Blood","FreshBlood","FBTK"]);
private _slot=_arr findIf {(_x param [0,""])==_wantMarker && {(_x param [3,-1])==_site} && {(_x param [4,true])==_iv}};
if (_slot>=0) then {_arr set [_slot,_entry]} else {_arr pushBack _entry};
_map set [_part,_arr]; [_patient,_map,true] call ACME_fnc_ivBagsCommit; [_patient,_part] call ACM_circulation_fnc_updateActiveFluidBags; [_patient,_part,_iv,_site] call ACME_fnc_resumeSiteFlow;
if (_type in ["Blood","FreshBlood"]) then {_warmer = [_patient,_part,_iv,_site,_warmer,_medic] call ACME_fnc_lineWarmer;};
if (_type in ["Blood","FreshBlood"] && {_warmer}) then {[_patient,true,false,objNull,CBA_missionTime+15,true] call ACME_fnc_bloodThermalStateCommit;};
if (!isNil "ace_medical_treatment_fnc_addToLog") then {[_patient,"activity","%1 re-hung a used %2 (%3 mL)",[[_medic,false,true] call ace_common_fnc_getName,_name,round _remVol]] call ace_medical_treatment_fnc_addToLog;};
[true,"",_bagUid] call _reply
