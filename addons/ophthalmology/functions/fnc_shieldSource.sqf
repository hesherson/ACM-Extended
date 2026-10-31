#include "..\script_component.hpp"
/* Funded eye-shield escrow. Only its original machine settles the real supply receipt.
 * Immutable provider bindings are pruned only by that provider's current owner; per-request
 * funding fields have one source writer, so a medic locality change cannot overwrite a new job.
 */
if (canSuspend) exitWith {
    private _result = false;
    isNil {_result = _this call FUNC(shieldSource);};
    _result
};
params ["_mode",["_args",[]]];
private _pending = missionNamespace getVariable [QGVAR(shieldPending),createHashMap];
private _fundingKey = {
    params ["_request"];
    QGVAR(shieldFunding_) + (((_request select 8) select 3) splitString ":" joinString "_")
};
private _cleanup = {
    params ["_medic"];
    if (isNull _medic || {!local _medic}) exitWith {};
    private _bindings = _medic getVariable [QGVAR(shieldBindings),[]];
    private _remaining = _bindings select {
        private _key = [_x] call _fundingKey;
        private _state = _medic getVariable [_key,[]];
        private _settled = _state isEqualTo [_x,"settled"];
        if (!_settled && {serverTime > (_x select 7)+30}) then {
            private _patient = _x select 0;
            if (isNull _patient) then {_settled=true;} else {
                private _terminal = (_patient getVariable [QGVAR(shieldTerminal),createHashMap]) getOrDefault [_x select 2,[]];
                if (count _terminal >= 2 && {(_terminal select 0) isEqualTo _x} && {(_terminal select 1)=="spent"}) then {
                    _settled=true;
                } else {[QGVAR(applyEyeShield),["retire",_x,0],_patient] call CBA_fnc_targetEvent;};
            };
        };
        if (_settled) then {_medic setVariable [_key,nil,true];};
        !_settled
    };
    if !(_remaining isEqualTo _bindings) then {_medic setVariable [QGVAR(shieldBindings),_remaining,true];};
    // Cleanup events can overtake public funding state. Keep one bounded-cadence local
    // reconciliation worker until the actual terminal publication arrives.
    if (count _remaining > 0) then {
        private _tracked = missionNamespace getVariable [QGVAR(shieldCleanupPatients),[]];
        _tracked pushBackUnique _medic;
        GVAR(shieldCleanupPatients) = _tracked;
        if (isNil QGVAR(shieldCleanupPFH)) then {
            GVAR(shieldCleanupPFH) = [{["cleanupTick",[]] call FUNC(shieldSource);},0.5,[]] call CBA_fnc_addPerFrameHandler;
        };
    };
};
if (_mode == "cleanup") exitWith {
    _args params ["_medic",["_hops",0]];
    if (!isNull _medic && {!local _medic}) then {
        if (_hops < 4) then {[QGVAR(shieldCleanup),[_medic,_hops+1],_medic] call CBA_fnc_targetEvent;};
    } else {[_medic] call _cleanup;};
};
if (_mode == "cleanupTick") exitWith {
    private _tracked = (missionNamespace getVariable [QGVAR(shieldCleanupPatients),[]]) select {!isNull _x && {local _x}};
    {[_x] call _cleanup;} forEach _tracked;
    _tracked = _tracked select {count (_x getVariable [QGVAR(shieldBindings),[]]) > 0};
    GVAR(shieldCleanupPatients) = _tracked;
    if (count _tracked == 0 && {!isNil QGVAR(shieldCleanupPFH)}) then {
        [GVAR(shieldCleanupPFH)] call CBA_fnc_removePerFrameHandler;
        GVAR(shieldCleanupPFH) = nil;
    };
};
private _send = {
    params ["_record",["_cancel",false]];
    private _request = _record select 0;
    private _patient = _request select 0;
    if (!isNull _patient) then {
        [QGVAR(applyEyeShield),[["apply","cancel"] select _cancel,_request,0],_patient] call CBA_fnc_targetEvent;
    };
    _record set [2,serverTime];
    _record set [3,(_record select 3)+1];
};
private _settle = {
    params ["_record","_accepted",["_clinicalSuccess",true]];
    private _request = _record select 0;
    _request params ["_patient","_medic","_id"];
    private _receipt = _request select 8;
    private _stock = missionNamespace getVariable ["ACME_supplyReceipts",createHashMap];
    if !((_stock getOrDefault [_receipt select 3,[]]) isEqualTo _receipt) exitWith {false};
    _record set [1,"settling"];
    _pending set [_id,_record];
    if (!isNull _medic) then {_medic setVariable [[_request] call _fundingKey,[_request,"settling"],true];};
    if (!([_receipt,!_accepted] call ACME_fnc_treatmentSupplyRefund)) exitWith {false};
    private _terminal = if (!_clinicalSuccess) then {"spent"} else {["refunded","applied"] select _accepted};
    _record set [1,"settled"];
    _record set [2,serverTime];
    _record set [4,_terminal];
    _pending set [_id,_record];
    if (!isNull _patient) then {[QGVAR(shieldSettled),[_request,_terminal],_patient] call CBA_fnc_targetEvent;};
    if (!isNull _medic) then {
        _medic setVariable [[_request] call _fundingKey,[_request,"settled"],true];
        [_medic] call _cleanup;
        [QGVAR(shieldCleanup),[_medic],_medic] call CBA_fnc_targetEvent;
    };
    if (_accepted && {_clinicalSuccess} && {!isNull _patient}) then {
        [_patient,LLSTRING(eyeshield_item)] call ACEFUNC(medical_treatment,addToTriageCard);
        [_patient,"activity",ACELSTRING(medical_treatment,Activity_usedItem),[[_medic] call ACEFUNC(common,getName),LLSTRING(eyeshield_item)]] call ACEFUNC(medical_treatment,addToLog);
    };
    true
};
if (_mode == "closed") exitWith {
    _args params ["_request","_terminal"];
    private _id = _request param [2,""];
    private _record = _pending getOrDefault [_id,[]];
    if (count _record == 5 && {(_record select 0) isEqualTo _request}
        && {(_record select 1)=="settled"} && {(_record select 4)==_terminal}) then {
        _pending deleteAt _id;
        missionNamespace setVariable [QGVAR(shieldPending),_pending];
        private _patient = _request select 0;
        if (!isNull _patient) then {[QGVAR(shieldTerminalClosed),[_request,_terminal],_patient] call CBA_fnc_targetEvent;};
    };
};
if (_mode == "start") exitWith {
    _args params ["_medic","_patient","_bodyPart","_classname"];
    if (isNull _medic || {!local _medic} || {!alive _medic} || {isNull _patient}
        || {(toLowerANSI _classname) != "eyeshield"} || {count _pending >= 64}
        || {!([_medic,_patient] call FUNC(eyeShieldCondition))}) exitWith {""};
    [_medic] call _cleanup;
    private _bindings = _medic getVariable [QGVAR(shieldBindings),[]];
    if (count _bindings >= 64) exitWith {""};
    // Reuse ACME's established patient-owner period. An unknown remote period is
    // not permission to debit inventory or guess who may certify a physical outcome.
    private _period = if (local _patient) then {[clientOwner,_patient getVariable ["ACME_providerLocalityEpoch",0]]}
        else {_patient getVariable ["ACME_vent_batterySwapOwnerPeriod",[]]};
    if (count _period != 2) exitWith {""};
    private _receipt = [_medic,_patient,["kat_eyecovers"]] call ACME_fnc_treatmentSupplyTake;
    if (count _receipt != 4) exitWith {""};
    private _stock = missionNamespace getVariable ["ACME_supplyReceipts",createHashMap];
    if ((_receipt select 1) != "kat_eyecovers"
        || {!((_stock getOrDefault [_receipt select 3,[]]) isEqualTo _receipt)}) exitWith {""};
    private _eyes = _patient getVariable [QGVAR(eyeInjuries),[1,1]];
    private _index = [1,0] select ((_eyes select 0) <= (_eyes select 1));
    private _id = "ocular-shield:" + (_receipt select 3);
    private _duration = missionNamespace getVariable [QGVAR(eyeshield_treatment_time),2];
    private _request = [_patient,_medic,_id,_patient getVariable ["ACME_clinicalEpoch",0],
        _patient getVariable ["ACME_equipmentKitEpoch",0],_medic getVariable ["ACME_equipmentKitEpoch",0],
        _medic getVariable ["ACME_providerLocalityEpoch",0],serverTime + (_duration max 1 min 30) + 30,
        _receipt,clientOwner,_index,_period];
    _bindings pushBack _request;
    _medic setVariable [[_request] call _fundingKey,[_request,"reserved"],true];
    _medic setVariable [QGVAR(shieldBindings),_bindings,true];
    _pending set [_id,[_request,"reserved",serverTime,0]];
    missionNamespace setVariable [QGVAR(shieldPending),_pending];
    if (isNil QGVAR(shieldSourcePFH)) then {
        GVAR(shieldSourcePFH) = [{["tick",[]] call FUNC(shieldSource);},0.5,[]] call CBA_fnc_addPerFrameHandler;
    };
    _id
};
private _valid = {
    params ["_request"];
    _request params ["_patient","_medic","_id","_epoch","_kit","_medicKit","_locality","_deadline"];
    !isNull _medic && {!isNull _patient} && {local _medic} && {alive _medic}
        && {!(_medic getVariable ["ACE_isUnconscious",false])}
        && {_epoch == (_patient getVariable ["ACME_clinicalEpoch",0])}
        && {_kit == (_patient getVariable ["ACME_equipmentKitEpoch",0])}
        && {_medicKit == (_medic getVariable ["ACME_equipmentKitEpoch",0])}
        && {_locality == (_medic getVariable ["ACME_providerLocalityEpoch",0])}
        && {serverTime <= _deadline}
        && {!(_medic getVariable ["ACME_persistenceFrozen",false])}
        && {!(_patient getVariable ["ACME_persistenceFrozen",false])}
        && {[_medic,_patient] call FUNC(eyeShieldCondition)}
};
if (_mode == "result") exitWith {
    _args params ["_request","_accepted"];
    if (count _request != 12 || {(_request select 9) != clientOwner}) exitWith {false};
    private _id = _request select 2;
    private _record = _pending getOrDefault [_id,[]];
    if (count _record != 4 || {!((_record select 0) isEqualTo _request)}
        || {(_record select 1) != "sent"}) exitWith {false};
    private _patient = _request select 0;
    if (isNull _patient) exitWith {false};
    if (((_patient getVariable [QGVAR(shieldTerminal),createHashMap]) getOrDefault [_id,[]]) isEqualTo [_request,"spent"]) exitWith {
        private _ok = [_record,true,false] call _settle;
        missionNamespace setVariable [QGVAR(shieldPending),_pending];
        _ok
    };
    private _proof = (_patient getVariable [QGVAR(shieldReceipts),createHashMap]) getOrDefault [_id,[]];
    if !(_proof isEqualTo [_request,_accepted]) exitWith {false};
    private _ok = [_record,_accepted] call _settle;
    missionNamespace setVariable [QGVAR(shieldPending),_pending];
    _ok
};
if (_mode == "tick") exitWith {
    {
        private _record = _pending get _x;
        private _request = _record select 0;
        private _phase = _record select 1;
        if (_phase == "reserved" && {!([_request] call _valid)}) then {[_record,false] call _settle;};
        if (_phase == "sent") then {
            private _patient = _request select 0;
            if (!isNull _patient) then {
                private _terminal = (_patient getVariable [QGVAR(shieldTerminal),createHashMap]) getOrDefault [_x,[]];
                private _proof = (_patient getVariable [QGVAR(shieldReceipts),createHashMap]) getOrDefault [_x,[]];
                if (_terminal isEqualTo [_request,"spent"]) then {[_record,true,false] call _settle;} else {
                if (count _proof == 2 && {(_proof select 0) isEqualTo _request}) then {
                    [_record,_proof select 1] call _settle;
                } else {
                    private _interval = [1,10] select ((_record select 3) >= 40);
                    if (serverTime - (_record select 2) >= _interval) then {
                        [_record,!([_request] call _valid)] call _send;
                        _pending set [_x,_record];
                    };
                };
                };
            } else {
                if (serverTime > (_request select 7)+30) then {[_record,true,false] call _settle;};
            };
        };
        if (_phase == "settled") then {
            private _patient = _request select 0;
            if (isNull _patient) then {_pending deleteAt _x;} else {
                private _terminal = (_patient getVariable [QGVAR(shieldTerminal),createHashMap]) getOrDefault [_x,[]];
                if ((_terminal select [0,2]) isEqualTo [_request,_record select 4]) then {
                    _pending deleteAt _x;
                    [QGVAR(shieldTerminalClosed),[_request,_record select 4],_patient] call CBA_fnc_targetEvent;
                } else {
                    if (serverTime-(_record select 2)>=1) then {
                        [QGVAR(shieldSettled),[_request,_record select 4],_patient] call CBA_fnc_targetEvent;
                        _record set [2,serverTime];_pending set [_x,_record];
                    };
                };
            };
        };
    } forEach +(keys _pending);
    missionNamespace setVariable [QGVAR(shieldPending),_pending];
    if (count _pending == 0 && {!isNil QGVAR(shieldSourcePFH)}) then {
        [GVAR(shieldSourcePFH)] call CBA_fnc_removePerFrameHandler;
        GVAR(shieldSourcePFH) = nil;
    };
};
private _id = _args param [7,""];
private _record = _pending getOrDefault [_id,[]];
if (count _record != 4) exitWith {false};
private _request = _record select 0;
if (!((_args param [0,objNull]) isEqualTo (_request select 1))
    || {!((_args param [1,objNull]) isEqualTo (_request select 0))}) exitWith {false};
if (_mode == "progress") exitWith {(_record select 1) == "reserved" && {[_request] call _valid}};
if (_mode == "cancel") exitWith {
    if ((_record select 1) == "reserved") then {[_record,false] call _settle;} else {
        if ((_record select 1) == "sent") then {[_record,true] call _send;_pending set [_id,_record];};
    };
    missionNamespace setVariable [QGVAR(shieldPending),_pending];
};
if (_mode == "finish" && {(_record select 1) == "reserved"}) then {
    if (!([_request] call _valid)) then {[_record,false] call _settle;} else {
        _record set [1,"sent"];
        private _medic = _request select 1;
        _medic setVariable [[_request] call _fundingKey,[_request,"sent"],true];
        _pending set [_id,_record];
        [_record] call _send;
    };
    missionNamespace setVariable [QGVAR(shieldPending),_pending];
};
