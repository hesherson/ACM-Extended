/* Source-funded native Remove/Pull/Y salvage delivery. Only the captured
 * machine outcome can release an in-flight product to another owner. */
if (!isServer) exitWith {};
if (canSuspend) exitWith {isNil {_this call ACME_fnc_resourceReturnBroker;};};
if !(_this isEqualType [] && {count _this in [2,3,4]} && {(_this select 0) isEqualType ""}
    && {(_this select 1) isEqualType []}) exitWith {};
params ["_mode",["_args",[]],["_fromWait",false],["_sourceCertified",false]];
if !(_fromWait isEqualType true && {_sourceCertified isEqualType true}) exitWith {};
private _all=missionNamespace getVariable ["ACME_resourceReturns",createHashMap];
// Direct server-only bridge for a read-back virtual fridge stock debit. Public
// event modes exclude this entry; its canonical server record is still checked.
if (_mode=="fridgeStock") exitWith {
    if (count _args!=4) exitWith {};
    _args params ["_provider","_source","_request","_products"];
    if !(_request isEqualType "" && {(_request find "fridge:")==0}
        && {[_products] call ACME_fnc_resourceReturnProductsValid}) exitWith {};
    private _key=_request select [7];
    private _grant=(missionNamespace getVariable ["ACME_bf_serverGrants",createHashMap]) getOrDefault [_key,[]];
    if (count _grant<7 || {(_grant select 0) isNotEqualTo _provider} || {(_grant select 5) isNotEqualTo _source}
        || {(_grant select 3)!="pending"} || {(_grant select 6)!=_request}
        || {_products isNotEqualTo [["item",_grant select 2]]}) exitWith {};
    ["request",[_provider,_source,_request,_products],false,true] call ACME_fnc_resourceReturnBroker;
};
if (_mode in ["ack","decision"]) exitWith {
    if !(count _args in [7,8]) exitWith {};
    if (([0,1,2,3,4,5,6] findIf {isNil {_args select _x}})>=0) exitWith {};
    _args params ["_provider","_patient","_request","_products","_sender","_nonce","_attempt",["_decision","delivered"]];
    if !(_provider isEqualType objNull && {_patient isEqualType objNull} && {_request isEqualType ""}
        && {_sender isEqualType 0} && {finite _sender} && {_sender>=2} && {_sender==floor _sender}
        && {_nonce isEqualType ""} && {_attempt isEqualType 0} && {finite _attempt} && {_attempt>=1}
        && {_attempt==floor _attempt} && {_decision isEqualType ""} && {[_products] call ACME_fnc_resourceReturnProductsValid}) exitWith {};
    private _j=_all getOrDefault [_request,[]];
    if (count _j!=11 || {(_j select [0,4]) isNotEqualTo [_provider,_patient,_request,_products]}
        || {(_j select 7)!=_nonce} || {_nonce==""} || {(_j select 9)!=_attempt}
        || {(_j select 4)!="ready"}) exitWith {};
    private _captured=_sender==(_j select 6);
    private _proof=if (isNull _provider) then {[]} else {(_provider getVariable ["ACME_resourceReturnReceived",createHashMap]) getOrDefault [_request,[]]};
    if (!_captured && {_sender!=owner _provider || {_proof isNotEqualTo [_products,"delivered"]}}) exitWith {};
    if (_decision=="cancelled" && {_captured}) exitWith {
        _j set [8,false];_j set [9,_attempt+1];_j set [5,0];
        if (isNull _provider) then {_j set [4,"orphaned"];};
        _all set [_request,_j];missionNamespace setVariable ["ACME_resourceReturns",_all];
    };
    if (_decision!="delivered") exitWith {};
    _j set [4,"delivered"];_all set [_request,_j];missionNamespace setVariable ["ACME_resourceReturns",_all];
    if (!isNull _patient && {(_request find "fridge:")!=0}) then {
        private _resolved=_patient getVariable ["ACME_resourceReturnResolved",createHashMap];
        _resolved set [_request,true];_patient setVariable ["ACME_resourceReturnResolved",_resolved,true];
    };
    private _certificate=_j select 10;
    if (count _certificate==2) then {
        ["ACME_resourceReturnSourceDelivered",[_request,_certificate],_certificate select 0] call CBA_fnc_ownerEvent;
    };
    if (!isNull _provider) then {
        private _pending=_provider getVariable ["ACME_resourceReturnPending",createHashMap];
        _pending deleteAt _request;_provider setVariable ["ACME_resourceReturnPending",_pending,true];
    };
};
if (_mode=="sourceProof") exitWith {
    if (count _args!=5) exitWith {};
    if (([0,1,2,3,4] findIf {isNil {_args select _x}})>=0) exitWith {};
    _args params ["_provider","_patient","_request","_products","_certificate"];
    if !(_provider isEqualType objNull && {_patient isEqualType objNull} && {_request isEqualType ""}
        && {[_products] call ACME_fnc_resourceReturnProductsValid}
        && {_certificate isEqualType []} && {count _certificate==2}
        && {(_certificate select 0) isEqualType 0} && {finite (_certificate select 0)} && {(_certificate select 0)>=2}
        && {(_certificate select 0)==floor (_certificate select 0)} && {(_certificate select 1) isEqualType ""}) exitWith {};
    private _waiting=missionNamespace getVariable ["ACME_resourceReturnWaiters",createHashMap];
    private _hint=_waiting getOrDefault [_request,[]];
    private _machines=missionNamespace getVariable ["ACME_syringeDeliveryMachines",createHashMap];
    if (_hint isEqualTo [] || {(_hint select 0) isNotEqualTo _args}
        || {(_certificate select 1)==""} || {(_machines getOrDefault [str (_certificate select 0),""])!=(_certificate select 1)}) exitWith {};
    _waiting deleteAt _request;missionNamespace setVariable ["ACME_resourceReturnWaiters",_waiting];
    ["request",_args,true,true] call ACME_fnc_resourceReturnBroker;
};
if (_mode=="recover") exitWith {
    private _source=_args param [0,objNull];
    if (isNull _source) exitWith {};
    private _proofs=_source getVariable ["ACME_resourceReturnFunded",createHashMap];
    {
        private _j=_all getOrDefault [_x,[]];
        if (_j isEqualTo []) then {private _proof=_proofs get _x;["request",[_proof select 0,_source,_x,_proof select 1],true] call ACME_fnc_resourceReturnBroker;};
    } forEach keys _proofs;
};
if (_mode=="request") then {
    if !(count _args in [4,5]) exitWith {};
    if (([0,1,2,3] findIf {isNil {_args select _x}})>=0) exitWith {};
    _args params ["_provider","_patient","_request","_products",["_certificate",[]]];
    _args=[_provider,_patient,_request,_products,_certificate];
    if (!(_provider isEqualType objNull) || {!(_patient isEqualType objNull)} || {!(_request isEqualType "")} || {_request==""} || {count _request>128}
        || {!(_products isEqualType [])} || {count _products>32}) exitWith {};
    if !([_products] call ACME_fnc_resourceReturnProductsValid) exitWith {};
    if !(_certificate isEqualType [] && {count _certificate in [0,2]}) exitWith {};
    if (count _certificate==2 && {!((_certificate select 0) isEqualType 0)
        || {!finite (_certificate select 0)} || {(_certificate select 0)<2}
        || {(_certificate select 0)!=floor (_certificate select 0)}
        || {!((_certificate select 1) isEqualType "")} || {(_certificate select 1)==""}}) exitWith {};
    private _sourceProof=if (isNull _patient) then {[]} else {(_patient getVariable ["ACME_resourceReturnFunded",createHashMap]) getOrDefault [_request,[]]};
    private _existing=_all getOrDefault [_request,[]];
    if (_existing isEqualTo [] && {!_sourceCertified} && {_sourceProof isNotEqualTo [_provider,_products]}) exitWith {
        // Object publication can follow its event. Bound these unproven hints;
        // they cannot create authoritative custody, public busy state or cancel
        // a checkpoint. Actual funded evidence stays on the source for recovery.
        private _waiting=missionNamespace getVariable ["ACME_resourceReturnWaiters",createHashMap];
        if (!(_request in _waiting) && {count _waiting<128}) then {
            _waiting set [_request,[[[_provider,_patient,_request,_products,_certificate]] call ACME_fnc_syringeDeliveryCopy,CBA_missionTime+30]];
            missionNamespace setVariable ["ACME_resourceReturnWaiters",_waiting];
        };
        if ((missionNamespace getVariable ["ACME_resourceReturnPFH",-1])<0 && {count _waiting>0}) then {
            missionNamespace setVariable ["ACME_resourceReturnPFH",[{["tick",[]] call ACME_fnc_resourceReturnBroker;},0.5,[]] call CBA_fnc_addPerFrameHandler];
        };
    };
    private _j=_all getOrDefault [_request,[]];
    if (_j isEqualTo []) then {
        _products=[_products] call ACME_fnc_syringeDeliveryCopy;
        _j=[_provider,_patient,_request,_products,["ready","orphaned"] select (isNull _provider),0,-1,"",false,1,+_certificate];
        _all set [_request,_j];missionNamespace setVariable ["ACME_resourceReturns",_all];
        private _active=missionNamespace getVariable ["ACME_resourceReturnActive",[]];_active pushBackUnique _request;
        missionNamespace setVariable ["ACME_resourceReturnActive",_active];
        if (!isNull _provider) then {
            private _pending=_provider getVariable ["ACME_resourceReturnPending",createHashMap];
            _pending set [_request,[_patient,_products]];_provider setVariable ["ACME_resourceReturnPending",_pending,true];
        };
        {_x setVariable ["ACME_persistenceFrozen",false,true];} forEach ([_provider,_patient] select {!isNull _x});
    } else {
        if ((_j select [0,4]) isNotEqualTo (_args select [0,4])) exitWith {};
        if ((_j select 10) isEqualTo [] && {_certificate isNotEqualTo []}) then {_j set [10,+_certificate];};
        if ((_j select 10) isNotEqualTo _certificate) exitWith {};
        if ((_j select 4)=="ready") then {_j set [5,0];};
    };
    if ((missionNamespace getVariable ["ACME_resourceReturnPFH",-1])<0) then {
        missionNamespace setVariable ["ACME_resourceReturnPFH",[{["tick",[]] call ACME_fnc_resourceReturnBroker;},0.5,[]] call CBA_fnc_addPerFrameHandler];
    };
};
if (_mode=="request" && {count _args==5}) then {
    private _certificate=_args select 4;
    private _admitted=_all getOrDefault [_args select 2,[]];
    if (count _certificate==2 && {count _admitted==11} && {(_admitted select [0,4]) isEqualTo (_args select [0,4])}
        && {(_admitted select 10) isEqualTo _certificate}) then {
        ["ACME_resourceReturnSourceAdmitted",[_args select 2,_certificate],_certificate select 0] call CBA_fnc_ownerEvent;
    };
};
if !(_mode in ["request","tick"]) exitWith {};
if (!_fromWait) then {
    private _waiting=missionNamespace getVariable ["ACME_resourceReturnWaiters",createHashMap];
    {
        private _hint=_waiting get _x;private _wire=_hint select 0;
        private _source=_wire select 1;
        private _proof=if (isNull _source) then {[]} else {(_source getVariable ["ACME_resourceReturnFunded",createHashMap]) getOrDefault [_x,[]]};
        if (_proof isEqualTo [_wire select 0,_wire select 3]) then {
            _waiting deleteAt _x;missionNamespace setVariable ["ACME_resourceReturnWaiters",_waiting];
            ["request",_wire,true] call ACME_fnc_resourceReturnBroker;
            _all=missionNamespace getVariable ["ACME_resourceReturns",createHashMap];
        } else {
            private _certificate=_wire param [4,[]];
            if (count _certificate==2) then {
                private _machines=missionNamespace getVariable ["ACME_syringeDeliveryMachines",createHashMap];
                if ((_machines getOrDefault [str (_certificate select 0),""])==(_certificate select 1) && {(_certificate select 1)!=""}) then {
                    ["ACME_resourceReturnSourceQuery",_wire,_certificate select 0] call CBA_fnc_ownerEvent;
                };
            };
            if (CBA_missionTime>(_hint select 1)) then {_waiting deleteAt _x;};
        };
    } forEach (+(keys _waiting));
    missionNamespace setVariable ["ACME_resourceReturnWaiters",_waiting];
};
private _kept=[];
{
    private _request=_x;private _j=_all get _request;
    if ((_j select 4) in ["delivered","orphaned"]) then {continue;};
    private _recipient=_j select 0;
    if (!isNull _recipient && {_j select 8}
        && {((_recipient getVariable ["ACME_resourceReturnReceived",createHashMap]) getOrDefault [_request,[]]) isEqualTo [_j select 3,"delivered"]}) then {
        // The positive owner-published receipt can outlive its ACK and original
        // connection. Consume known success before querying an unavailable peer.
        ["ack",[_recipient,_j select 1,_request,_j select 3,owner _recipient,_j select 7,_j select 9]] call ACME_fnc_resourceReturnBroker;
        continue;
    };
    _kept pushBack _request;
    _j params ["_provider","_patient","","_products","_state"];
    if (_state=="awaitProof") then {
        private _proof=if (isNull _patient) then {[]} else {(_patient getVariable ["ACME_resourceReturnFunded",createHashMap]) getOrDefault [_request,[]]};
        if (_proof isEqualTo [_provider,_products]) then {_j set [4,"ready"];};
    };
    if ((_j select 4)=="ready" && {CBA_missionTime>=(_j select 5)}) then {
        private _machines=missionNamespace getVariable ["ACME_syringeDeliveryMachines",createHashMap];
        if (!(_j select 8) && {!isNull _provider}) then {
            private _owner=owner _provider;private _nonce=_machines getOrDefault [str _owner,""];
            if (_nonce!="") then {_j set [6,_owner];_j set [7,_nonce];_j set [8,true];};
        };
        _j set [5,CBA_missionTime+2];_all set [_request,_j];missionNamespace setVariable ["ACME_resourceReturns",_all];
        if (_j select 8) then {
            private _wire=[_provider,_patient,_request,[_products] call ACME_fnc_syringeDeliveryCopy,_j select 6,_j select 7,_j select 9];
            if (!isNull _provider && {owner _provider==(_j select 6)} && {(_machines getOrDefault [str (_j select 6),""])==(_j select 7)}) then {
                ["ACME_resourceReturnDelivery",_wire,_provider] call CBA_fnc_targetEvent;
            } else {["ACME_resourceReturnQuery",_wire,_j select 6] call CBA_fnc_ownerEvent;};
        } else {if (isNull _provider) then {_j set [4,"orphaned"];_all set [_request,_j];missionNamespace setVariable ["ACME_resourceReturns",_all];};};
    };
} forEach (missionNamespace getVariable ["ACME_resourceReturnActive",[]]);
missionNamespace setVariable ["ACME_resourceReturnActive",_kept];
if (_kept isEqualTo [] && {count (missionNamespace getVariable ["ACME_resourceReturnWaiters",createHashMap])==0}) then {
    private _pfh=missionNamespace getVariable ["ACME_resourceReturnPFH",-1];
    if (_pfh>=0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
    missionNamespace setVariable ["ACME_resourceReturnPFH",-1];
};
