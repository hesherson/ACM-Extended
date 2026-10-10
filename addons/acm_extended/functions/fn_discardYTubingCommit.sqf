// Owner-authoritative teardown of one Y-line access. Salvage is returned to the requesting medic only after commit.
params [["_patient",objNull,[objNull]],["_medic",objNull,[objNull]],["_part","",[""]],["_iv",true,[true]],["_site",-1,[0]],["_epoch",-1,[0]],["_requestId","",[""]],["_issued",-1,[0]],["_identity",[],[[]]]];
if (isNull _patient || {!local _patient} || {_requestId == ""}) exitWith {false};
if (count _requestId > 128 || {!finite _issued} || {_issued < 0}
    || {serverTime - _issued > 10} || {_issued > serverTime + 2}) exitWith {false};
private _receipts = _patient getVariable ["ACME_yDiscardReceipts", createHashMap];
private _prior = _receipts getOrDefault [_requestId, []];
if !(_prior isEqualTo []) exitWith {if (!isNull _medic) then {["ACME_discardYTubingResult",_prior,_medic] call CBA_fnc_targetEvent;}; _prior param [2,false]};
private _times=_patient getVariable ["ACME_yDiscardReceiptsTimes",createHashMap];
{if (serverTime - (_times get _x) > 12) then {_receipts deleteAt _x;_times deleteAt _x;};} forEach keys _times;
if (count _receipts >= 512) exitWith {false};
private _reply = {
    params ["_ok",["_salvage",[],[[]]],["_reason","",[""]]];
    private _payload=[_patient,_requestId,_ok,_salvage,_part,_iv,_site,_reason];
    _receipts set [_requestId,_payload]; _times set [_requestId,serverTime]; [_patient,"ACME_yDiscardReceipts",_receipts] call ACME_fnc_setVarNet; [_patient,"ACME_yDiscardReceiptsTimes",_times] call ACME_fnc_setVarNet;
    if (!isNull _medic) then {["ACME_discardYTubingResult",_payload,_medic] call CBA_fnc_targetEvent;};
    _ok
};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {[false,[],"Patient state changed. Reopen the transfusion menu."] call _reply};
if (isNull _medic || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)} || {(_medic distance _patient)>ace_medical_gui_maxDistance}) exitWith {[false,[],"Provider can no longer discard that Y tubing."] call _reply};
if !([_patient,_part,_iv,_site] call ACME_fnc_isYLineAccess) exitWith {[false,[],"That access no longer has Y tubing."] call _reply};
private _map=_patient getVariable ["ACM_circulation_IV_Bags",createHashMap];
private _arr=+(_map getOrDefault [_part,[]]);
private _currentIdentity=[];
{if ((_x param [3,-1]) == _site && {(_x param [4,true]) isEqualTo _iv}) then {_currentIdentity pushBack (_x param [8,""]);};} forEach _arr;
_currentIdentity sort true;
if !(_currentIdentity isEqualTo _identity) exitWith {[false,[],"The bags on this tubing changed. Select it again."] call _reply};
private _drugIds=(_patient getVariable ["ACME_infusion_BagMedications",[]]) apply {_x param [23,""]};
private _salvage=[];
for "_i" from ((count _arr)-1) to 0 step -1 do {
    private _e=_arr select _i;
    if ((_e param [3,-1]) == _site && {(_e param [4,true]) == _iv}) then {
        if ((_e param [1,0]) > 0.5 && {!((_e param [0,""]) in ["ACME_Empty","ACME_EmptySaline"])} && {!((_e param [8,""]) in _drugIds)}) then {_salvage pushBack (+_e);};
        _arr deleteAt _i;
    };
};
_map set [_part,_arr]; [_patient,_map,true] call ACME_fnc_ivBagsCommit; [_patient,_part] call ACM_circulation_fnc_updateActiveFluidBags;
private _key=toLowerANSI format ["%1#%2#%3",_part,_iv,_site];
private _yl=(_patient getVariable ["ACME_YLines",[]]) select {toLowerANSI _x != _key};
[_patient,_yl] call ACME_fnc_yLinesCommit;
private _dirty=_patient getVariable ["ACME_YLineDirty",createHashMap]; if (_key in _dirty) then {_dirty deleteAt _key; _patient setVariable ["ACME_YLineDirty",_dirty,true];};
private _entries=+(_patient getVariable ["ACME_infusion_BagMedications",[]]);
private _kept=_entries select {!(((_x param [1,""])==_part) && {(_x param [4,-1])==_site} && {(_x param [5,true])==_iv})};
if (count _kept != count _entries) then {[_patient,_kept] call ACME_fnc_infusionMedicationStateCommit;};
private _pi=ACME_infusion_bodyParts find toLowerANSI _part; if (_pi>=0) then {_patient setVariable [format ["ACME_clampRate_%1_%2_%3",_pi,_iv,_site],-1,false];};
if (!isNil "ace_medical_treatment_fnc_addToLog") then {[_patient,"activity","%1 discarded Y tubing",[[_medic,false,true] call ace_common_fnc_getName]] call ace_medical_treatment_fnc_addToLog;};
[true,_salvage,""] call _reply
