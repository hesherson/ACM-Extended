/* Source-machine certificate/outbox. Stage BEFORE source mutation, fund only
 * AFTER its native clinical readback. A public variable is never the proof of
 * a completed debit; the server queries this private incarnation's decision. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_resourceReturnSource;}; _ok};
params ["_mode","_args"];
if (_mode == "cleanup") exitWith {
    _args params ["_patient","_request"];
    if (isNull _patient || {!local _patient}) exitWith {false};
    private _resolved = _patient getVariable ["ACME_resourceReturnResolved",createHashMap];
    if !(_resolved getOrDefault [_request,false]) exitWith {false};
    private _proof = _patient getVariable ["ACME_resourceReturnFunded",createHashMap];
    _proof deleteAt _request; _resolved deleteAt _request;
    _patient setVariable ["ACME_resourceReturnFunded",_proof,true];
    _patient setVariable ["ACME_resourceReturnResolved",_resolved,true];
    true
};
private _all = missionNamespace getVariable ["ACME_resourceReturnSources",createHashMap];
private _active = missionNamespace getVariable ["ACME_resourceReturnSourceActive",[]];
if (_mode in ["admitted","delivered"]) exitWith {
    _args params ["_request","_certificate"];
    private _record = _all getOrDefault [_request,[]];
    if (count _record != 3 || {(_record select 2) isNotEqualTo _certificate} || {!((_record select 1) in ["funded","admitted","delivered"])}) exitWith {false};
    _record set [1,if (_mode == "delivered" || {(_record select 1) == "delivered"}) then {"delivered"} else {"admitted"}]; _all set [_request,_record]; missionNamespace setVariable ["ACME_resourceReturnSources",_all];
    _active = _active - [_request]; missionNamespace setVariable ["ACME_resourceReturnSourceActive",_active];
    private _fingerprint = _record select 0;
    {
        if (!isNull _x) then {
            private _pending = _x getVariable ["ACME_resourceReturnSourcePending",createHashMap];
            _pending deleteAt _request; _x setVariable ["ACME_resourceReturnSourcePending",_pending,true];
        };
    } forEach [_fingerprint select 0,_fingerprint select 1];
    if (_mode == "delivered" && {!isNull (_fingerprint select 1)}) then {
        private _patient = _fingerprint select 1;
        [_patient,"resourceReturnCleanup",[_patient,_request]] call ACME_fnc_ownerDispatch;
    };
    true
};
_args params ["_provider","_patient","_request","_products"];
private _nonce = missionNamespace getVariable ["ACME_syringeDeliveryMachineNonce",""];
if !(_mode in ["stage","funded","cancel","uncertain"] && {_request isEqualType ""} && {_request != ""} && {count _request <= 128}
    && {_nonce != ""} && {[_products] call ACME_fnc_resourceReturnProductsValid}) exitWith {false};
private _record = _all getOrDefault [_request,[]];
private _fingerprint = [_provider,_patient,[_products] call ACME_fnc_syringeDeliveryCopy,_nonce];
private _certificate = [clientOwner,_nonce];
if (_record isNotEqualTo [] && {(_record select 0) isNotEqualTo _fingerprint}) exitWith {false};
if (_mode == "stage") exitWith {
    if (isNull _patient || {!local _patient} || {isNull _provider}) exitWith {false};
    if (_record isNotEqualTo []) exitWith {(_record select 1) == "applying"};
    _all set [_request,[_fingerprint,"applying",_certificate]];
    missionNamespace setVariable ["ACME_resourceReturnSources",_all];
    {
        private _pending = _x getVariable ["ACME_resourceReturnSourcePending",createHashMap];
        _pending set [_request,+_certificate]; _x setVariable ["ACME_resourceReturnSourcePending",_pending,true];
    } forEach [_provider,_patient];
    true
};
if (count _record != 3 || {(_record select 2) isNotEqualTo _certificate}) exitWith {false};
if (_mode == "cancel") exitWith {
    if ((_record select 1) != "applying") exitWith {false};
    _record set [1,"cancelled"]; _all set [_request,_record]; missionNamespace setVariable ["ACME_resourceReturnSources",_all];
    {
        if (!isNull _x) then {private _pending = _x getVariable ["ACME_resourceReturnSourcePending",createHashMap]; _pending deleteAt _request; _x setVariable ["ACME_resourceReturnSourcePending",_pending,true];};
    } forEach [_provider,_patient];
    true
};
if (_mode == "uncertain") exitWith {
    if ((_record select 1) == "admitted") exitWith {false};
    _record set [1,"uncertain"]; _all set [_request,_record]; missionNamespace setVariable ["ACME_resourceReturnSources",_all];
    true
};
if !((_record select 1) in ["applying","funded","admitted","delivered"]) exitWith {false};
if ((_record select 1) in ["admitted","delivered"]) exitWith {true};
_record set [1,"funded"]; _all set [_request,_record]; missionNamespace setVariable ["ACME_resourceReturnSources",_all];
if (!isNull _patient) then {
    private _proof = _patient getVariable ["ACME_resourceReturnFunded",createHashMap];
    _proof set [_request,[_provider,[_products] call ACME_fnc_syringeDeliveryCopy]];
    _patient setVariable ["ACME_resourceReturnFunded",_proof,true];
};
_active pushBackUnique _request; missionNamespace setVariable ["ACME_resourceReturnSourceActive",_active];
["ACME_resourceReturn",["request",[_provider,_patient,_request,[_products] call ACME_fnc_syringeDeliveryCopy,_certificate]]] call CBA_fnc_serverEvent;
if ((missionNamespace getVariable ["ACME_resourceReturnSourcePFH",-1]) < 0) then {
    private _id = [{
        params ["","_id"];
        private _active = missionNamespace getVariable ["ACME_resourceReturnSourceActive",[]];
        private _all = missionNamespace getVariable ["ACME_resourceReturnSources",createHashMap];
        private _keep = [];
        {
            private _request = _x;
            private _record = _all getOrDefault [_request,[]];
            if (count _record == 3 && {(_record select 1) == "funded"}) then {
                private _fingerprint = _record select 0;
                _keep pushBack _request;
                ["ACME_resourceReturn",["request",[_fingerprint select 0,_fingerprint select 1,_request,[_fingerprint select 2] call ACME_fnc_syringeDeliveryCopy,_record select 2]]] call CBA_fnc_serverEvent;
            };
        } forEach _active;
        missionNamespace setVariable ["ACME_resourceReturnSourceActive",_keep];
        if (_keep isEqualTo []) then {[_id] call CBA_fnc_removePerFrameHandler; missionNamespace setVariable ["ACME_resourceReturnSourcePFH",-1];};
    },1,[]] call CBA_fnc_addPerFrameHandler;
    missionNamespace setVariable ["ACME_resourceReturnSourcePFH",_id];
};
true
