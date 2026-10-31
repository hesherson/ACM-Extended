#include "..\script_component.hpp"
/* A removed collection remains one funded product until verified delivery.
 * Request replay cannot allocate another donor ID or resample donor facts. */
if (!isServer) exitWith {};
if (canSuspend) exitWith {isNil {_this call FUNC(freshBloodGrant);};};
if !(_this isEqualType [] && {count _this in [2,3]} && {(_this select 0) isEqualType ""}
    && {(_this select 1) isEqualType []}) exitWith {};
params ["_mode",["_args",[]],["_fromWait",false]];
private _all=missionNamespace getVariable [QGVAR(FreshBloodGrants),createHashMap];
if (_mode=="ack") exitWith {
    if (count _args!=7) exitWith {};
    if (([0,1,2,3,4,5,6] findIf {isNil {_args select _x}})>=0) exitWith {};
    _args params ["_medic","_request","_id","_facts","_sender","_nonce","_attempt"];
    if !(_medic isEqualType objNull && {_request isEqualType ""} && {_id isEqualType 0} && {finite _id}
        && {_facts isEqualType []} && {_sender isEqualType 0} && {finite _sender}
        && {_nonce isEqualType ""} && {_attempt isEqualType 0} && {finite _attempt}) exitWith {};
    private _j=_all getOrDefault [_request,[]];
    if (count _j!=14 || {(_j select 0) isNotEqualTo _medic} || {(_j select 6)!=_id}
        || {(_j select 4) isNotEqualTo _facts} || {(_j select 11)!=_nonce} || {(_j select 13)!=_attempt}) exitWith {};
    private _proof=if (isNull _medic) then {[]} else {(_medic getVariable [QGVAR(freshBloodReceived),createHashMap]) getOrDefault [_request,[]]};
    if ((_sender!=(_j select 10) || {_nonce==""})
        && {_sender!=owner _medic || {_proof isNotEqualTo [_j select 2,_id,_facts,"delivered"]}}) exitWith {};
    _j set [5,"delivered"];_all set [_request,_j];missionNamespace setVariable [QGVAR(FreshBloodGrants),_all];
    private _donor=_j select 1;
    if (!isNull _donor) then {
        private _resolved=_donor getVariable ["ACME_txRemoveResolved",createHashMap];
        _resolved set [_request,true];_donor setVariable ["ACME_txRemoveResolved",_resolved,true];
    };
    private _pending=_medic getVariable [QGVAR(freshBloodPending),createHashMap];
    _pending deleteAt _request;_medic setVariable [QGVAR(freshBloodPending),_pending,true];
};
if (_mode=="decision") exitWith {
    if (count _args!=8) exitWith {};
    if (([0,1,2,3,4,5,6,7] findIf {isNil {_args select _x}})>=0) exitWith {};
    _args params ["_medic","_request","_id","_facts","_sender","_nonce","_attempt","_decision"];
    if !(_medic isEqualType objNull && {_request isEqualType ""} && {_id isEqualType 0} && {finite _id}
        && {_facts isEqualType []} && {_sender isEqualType 0} && {finite _sender}
        && {_nonce isEqualType ""} && {_attempt isEqualType 0} && {finite _attempt} && {_decision isEqualType ""}) exitWith {};
    private _j=_all getOrDefault [_request,[]];
    if (count _j!=14 || {(_j select 0) isNotEqualTo _medic} || {(_j select 6)!=_id}
        || {(_j select 4) isNotEqualTo _facts} || {(_j select 10)!=_sender}
        || {(_j select 11)!=_nonce} || {_nonce==""} || {(_j select 13)!=_attempt}
        || {(_j select 5)!="ready"}) exitWith {};
    if (_decision=="delivered") exitWith {["ack",_args select [0,7]] call FUNC(freshBloodGrant);};
    if (_decision=="cancelled") then {
        _j set [12,false];_j set [13,_attempt+1];_j set [8,0];
        _all set [_request,_j];missionNamespace setVariable [QGVAR(FreshBloodGrants),_all];
    };
};
if (_mode=="recover") exitWith {
    private _source=_args param [0,objNull];
    if (isNull _source) exitWith {};
    private _proofs=_source getVariable ["ACME_txRemoveFunded",createHashMap];
    {
        private _j=_all getOrDefault [_x,[]];
        if (_j isEqualTo []) then {private _proof=_proofs get _x;["request",[_proof select 0,_source,_proof select 1,_x,_proof select 2],true] call FUNC(freshBloodGrant);};
    } forEach keys _proofs;
};
if (_mode=="request") then {
    if (count _args!=5) exitWith {};
    if (([0,1,2,3,4] findIf {isNil {_args select _x}})>=0) exitWith {};
    _args params ["_medic","_donor","_volume","_request","_facts"];
    if (!(_medic isEqualType objNull) || {!(_donor isEqualType objNull)} || {!(_request isEqualType "")}
        || {!(_volume isEqualType 0)}) exitWith {};
    if (isNull _medic || {_request==""} || {count _request>128} || {!(_volume in [250,500])}
        || {!(_facts isEqualType [])} || {count _facts!=4}) exitWith {};
    if (([0,1,2,3] findIf {isNil {_facts select _x}})>=0) exitWith {};
    if !((_facts select 0) isEqualTo "freshV1" && {(_facts select 1) isEqualType true}
        && {(_facts select 2) isEqualType 0} && {finite (_facts select 2)}
        && {(_facts select 2)<=CBA_missionTime+5}
        && {(_facts select 3) isEqualType 0} && {finite (_facts select 3)}
        && {(_facts select 3)>=0} && {(_facts select 3)<=7} && {(_facts select 3)==floor (_facts select 3)}) exitWith {};
    private _sourceProof=if (isNull _donor) then {[]} else {(_donor getVariable ["ACME_txRemoveFunded",createHashMap]) getOrDefault [_request,[]]};
    private _existing=_all getOrDefault [_request,[]];
    if (_existing isEqualTo [] && {_sourceProof isNotEqualTo [_medic,_volume,_facts]}) exitWith {
        // Object publication can follow its event. Bound these unproven hints;
        // they cannot create authoritative custody, public busy state or cancel
        // a checkpoint. Actual funded evidence stays on the source for recovery.
        private _waiting=missionNamespace getVariable ["ACM_circulation_FreshBloodGrantWaiters",createHashMap];
        if (!(_request in _waiting) && {count _waiting<128}) then {
            _waiting set [_request,[[[_medic,_donor,_volume,_request,_facts]] call ACME_fnc_syringeDeliveryCopy,CBA_missionTime+30]];
            missionNamespace setVariable ["ACM_circulation_FreshBloodGrantWaiters",_waiting];
        };
        if ((missionNamespace getVariable ["ACM_circulation_FreshBloodGrantPFH",-1])<0 && {count _waiting>0}) then {
            missionNamespace setVariable ["ACM_circulation_FreshBloodGrantPFH",[{["tick",[]] call FUNC(freshBloodGrant);},0.5,[]] call CBA_fnc_addPerFrameHandler];
        };
    };
    private _j=_all getOrDefault [_request,[]];
    if (_j isEqualTo []) then {
        _j=[_medic,_donor,_volume,_request,+_facts,"awaitProof",-1,[],0,"",-1,"",false,1];
        _all set [_request,_j];missionNamespace setVariable [QGVAR(FreshBloodGrants),_all];
        private _active=missionNamespace getVariable [QGVAR(FreshBloodGrantActive),[]];
        _active pushBackUnique _request;missionNamespace setVariable [QGVAR(FreshBloodGrantActive),_active];
        private _pending=_medic getVariable [QGVAR(freshBloodPending),createHashMap];
        _pending set [_request,[_donor,_volume,+_facts]];_medic setVariable [QGVAR(freshBloodPending),_pending,true];
        // A delayed completion can overtake checkpoint admission. Retire that
        // barrier; never drop already removed blood because a save began.
        {_x setVariable ["ACME_persistenceFrozen",false,true];} forEach ([_medic,_donor] select {!isNull _x});
    } else {
        if ((_j select [0,5]) isNotEqualTo _args) exitWith {};
        if ((_j select 5)=="ready") then {_j set [8,0];};
    };
    if ((missionNamespace getVariable [QGVAR(FreshBloodGrantPFH),-1])<0) then {
        missionNamespace setVariable [QGVAR(FreshBloodGrantPFH),[{["tick",[]] call FUNC(freshBloodGrant);},0.5,[]] call CBA_fnc_addPerFrameHandler];
    };
};
if !(_mode in ["request","tick"]) exitWith {};
if (!_fromWait) then {
    private _waiting=missionNamespace getVariable ["ACM_circulation_FreshBloodGrantWaiters",createHashMap];
    {
        private _hint=_waiting get _x;private _wire=_hint select 0;
        private _source=_wire select 1;
        private _proof=if (isNull _source) then {[]} else {(_source getVariable ["ACME_txRemoveFunded",createHashMap]) getOrDefault [_x,[]]};
        if (_proof isEqualTo [_wire select 0,_wire select 2,_wire select 4]) then {
            _waiting deleteAt _x;missionNamespace setVariable ["ACM_circulation_FreshBloodGrantWaiters",_waiting];
            ["request",_wire,true] call FUNC(freshBloodGrant);
            _all=missionNamespace getVariable ["ACM_circulation_FreshBloodGrants",createHashMap];
        } else {if (CBA_missionTime>(_hint select 1)) then {_waiting deleteAt _x;};};
    } forEach (+(keys _waiting));
    missionNamespace setVariable ["ACM_circulation_FreshBloodGrantWaiters",_waiting];
};
private _kept=[];
{
    private _request=_x;
    private _j=_all get _request;
    if ((_j select 5)=="delivered") then {continue;};
    private _recipient=_j select 0;
    if (!isNull _recipient && {_j select 12}
        && {((_recipient getVariable [QGVAR(freshBloodReceived),createHashMap]) getOrDefault [_request,[]]) isEqualTo [_j select 2,_j select 6,_j select 4,"delivered"]}) then {
        ["ack",[_recipient,_request,_j select 6,_j select 4,owner _recipient,_j select 11,_j select 13]] call FUNC(freshBloodGrant);
        continue;
    };
    _kept pushBack _request;
    _j params ["_medic","_donor","_volume","","_facts","_phase"];
    if (_phase=="awaitProof") then {
        private _proof=if (isNull _donor) then {[]} else {(_donor getVariable ["ACME_txRemoveFunded",createHashMap]) getOrDefault [_request,[]]};
        if (_proof isEqualTo [_medic,_volume,_facts]) then {
            private _id=[_donor,_volume,_facts] call FUNC(generateFreshBloodEntry);
            private _entry=[_donor,_volume,_facts select 3,_facts select 1,_facts select 2];
            // Exhaustion keeps a full-volume virtual bag with immutable donor
            // metadata. It can be rehung and saved without a reused native ID.
            _id=_id max 0;
            _j set [5,"ready"];_j set [6,_id];_j set [7,_entry];_j set [8,0];
            if (_id==0) then {_j set [9,"Donor ID space is full; the blood is retained in the used-bag inventory."];};
            _all set [_request,_j];missionNamespace setVariable [QGVAR(FreshBloodGrants),_all];
            if (_id>0) then {[QGVAR(updateFreshBloodBagName),[_volume,_id,_facts select 3]] call CBA_fnc_globalEvent;};
        };
    };
    if ((_j select 5)=="ready" && {CBA_missionTime>=(_j select 8)} && {!isNull _medic}) then {
        private _machines=missionNamespace getVariable ["ACME_syringeDeliveryMachines",createHashMap];
        if !(_j select 12) then {
            private _owner=owner _medic;
            private _nonce=_machines getOrDefault [str _owner,""];
            if (_nonce!="") then {_j set [10,_owner];_j set [11,_nonce];_j set [12,true];};
        };
        _j set [8,CBA_missionTime+2];_all set [_request,_j];missionNamespace setVariable [QGVAR(FreshBloodGrants),_all];
        if (_j select 12) then {
            if (owner _medic==(_j select 10) && {(_machines getOrDefault [str (_j select 10),""])==(_j select 11)}) then {
                [QGVAR(receiveFreshBloodBag),[_medic,_volume,_j select 6,_j select 7,_request,_facts,_j select 10,_j select 11,_j select 13],_medic] call CBA_fnc_targetEvent;
            } else {
                [QGVAR(freshBloodGrantQuery),[_medic,_volume,_j select 6,_request,_facts,_j select 10,_j select 11,_j select 13],_j select 10] call CBA_fnc_ownerEvent;
            };
        };
    };
} forEach (missionNamespace getVariable [QGVAR(FreshBloodGrantActive),[]]);
missionNamespace setVariable [QGVAR(FreshBloodGrantActive),_kept];
if (_kept isEqualTo [] && {count (missionNamespace getVariable ["ACM_circulation_FreshBloodGrantWaiters",createHashMap])==0}) then {
    private _pfh=missionNamespace getVariable [QGVAR(FreshBloodGrantPFH),-1];
    if (_pfh>=0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
    missionNamespace setVariable [QGVAR(FreshBloodGrantPFH),-1];
};
