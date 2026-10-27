params ["_mode","_owner","_kind","_sid","_token","_request","_ok",["_attempt",0],["_requiredRevision",0]];
if (isNull _owner || {!local _owner}) exitWith {};
private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
// CBA reply may precede public state replication. Wait for the exact certificate, never infer failure.
private _proof = count _record >= 7 && {(_record select 0) == _kind} && {(_record select 1) == _sid} && {(_record select 6) >= _requiredRevision};
private _terminal = _mode in ["return","consume"];
if (_ok && {!_proof || {_mode == "claim" && {(_record select 4) != _request || {(_record select 5) != "reserved"}}} || {_terminal && {(_record select 4) != _request || {!((_record select 5) in ["held","spent"])}}}}) exitWith {
    if (_attempt < 40) then {[{_this call ACME_fnc_inventoryLedgerReply;},[_mode,_owner,_kind,_sid,_token,_request,_ok,_attempt+1,_requiredRevision],0.1] call CBA_fnc_waitAndExecute;};
};
private _class = _record param [8,["ACME_PreparedIVSet","ACME_PreparedSyringe"] select (_kind == "syringe")];
private _firstFailure = false;
private _add = {
    private _placements = _owner getVariable ["ACME_inventoryPlacement",createHashMap];
    private _key = str _token;
    private _newAttempt = !(_key in _placements);
    private _contains = {params ["_destination"]; !isNull _destination && {(([_destination,_kind] call ACME_fnc_inventoryLedgerNative) findIf {(_x select 0) == _token}) >= 0}};
    private _done = {
        params ["_destination"];
        _placements deleteAt _key;
        _owner setVariable ["ACME_inventoryPlacement",_placements,true];
        _destination
    };
    if ([_owner] call _contains) exitWith {[_owner] call _done};
    private _destination = _placements getOrDefault [_key,objNull];
    if (!isNull _destination) exitWith {
        if !([_destination] call _contains) then {_destination addMagazineAmmoCargo [_class,1,_token];};
        if ([_destination] call _contains) then {[_destination] call _done} else {objNull}
    };
    if (_kind == "cooler" && {!(_owner isKindOf "CAManBase")}) exitWith {
        _owner addMagazineAmmoCargo [_class,1,_token];
        if ([_owner] call _contains) then {[_owner] call _done} else {objNull}
    };
    // ACE ignores soldierMaxLoad while retaining each container's actual capacity.
    if (_owner canAdd [_class,1,true]) then {_owner addMagazine [_class,_token];};
    if ([_owner] call _contains) exitWith {[_owner] call _done};
    _destination = createVehicle ["GroundWeaponHolder",getPosATL _owner,[],0,"CAN_COLLIDE"];
    _placements set [_key,_destination];
    _owner setVariable ["ACME_inventoryPlacement",_placements,true];
    if (!isNull _destination) then {
        // Retain this exact destination until native readback proves placement.
        // A replay cannot create a second holder or discard funded contents.
        _destination addMagazineAmmoCargo [_class,1,_token];
    };
    if ([_destination] call _contains) exitWith {[_destination] call _done};
    _firstFailure = _newAttempt;
    objNull
};
private _notice = {
    params ["_destination",["_ready",false]];
    if (!hasInterface || {_owner isNotEqualTo ACE_player}) exitWith {};
    if (isNull _destination) exitWith {
        if (_firstFailure) then {["Prepared item is waiting for inventory placement.",3,_owner] call ace_common_fnc_displayTextStructured;};
    };
    if (_destination isNotEqualTo _owner) then {
        ["Prepared item placed on the ground. Pick it up through Gear.",4,_owner] call ace_common_fnc_displayTextStructured;
    } else {
        if (_ready && {_kind == "prepared"}) then {["Prepared IV set is ready.",2,_owner] call ace_common_fnc_displayTextStructured;};
    };
};
if (_mode == "register") exitWith {
    private _pending = _owner getVariable ["ACME_inventoryPending",createHashMap];
    private _key = _kind + ":" + _sid;
    private _row = _pending getOrDefault [_key,[]];
    if (_row isEqualTo []) exitWith {}; // duplicate allocation ACK never adds a second magazine.
    if (!_ok) exitWith {
        if ((_row param [6,"pending"]) == "blocked") exitWith {}; // duplicate failure ACK is inert.
        _row set [6,"blocked"]; _pending set [_key,_row]; _owner setVariable ["ACME_inventoryPending",_pending,true];
    };
    if ((_row select 3) != (_owner getVariable ["ACME_equipmentKitEpoch",0])) exitWith {_pending deleteAt _key; _owner setVariable ["ACME_inventoryPending",_pending,true];};
    if ((_record select 2) isNotEqualTo (_row select 2)) exitWith {}; // pending registration retries retain latest funded payload.
    if ((_record select 3) isNotEqualTo _owner || {(_record select 5) != "held"}) exitWith {};
    private _destination = call _add;
    [_destination,true] call _notice;
    if (isNull _destination) exitWith {}; // funded registration remains retryable until placement is real.
    _pending deleteAt _key; _owner setVariable ["ACME_inventoryPending",_pending,true];
    [_owner] call ACME_fnc_inventoryLedgerReconcile;
    if (hasInterface && {_owner isEqualTo ACE_player} && {!isNil "ACME_fnc_updateTransfusionControls"}) then {
        uiNamespace setVariable ["ACME_preparedRowSig","__force__"];
        call ACME_fnc_updateTransfusionControls;
    };
};
if (_mode == "claim") exitWith {
    private _requests = _owner getVariable ["ACME_inventoryRequests",createHashMap];
    _requests deleteAt _request; _owner setVariable ["ACME_inventoryRequests",_requests,true];
    private _escrow = _owner getVariable ["ACME_inventoryEscrow",createHashMap];
    private _held = _escrow getOrDefault [_request,[]];
    if (_ok && {!(_held isEqualTo [])}) then {_held set [5,true]; _escrow set [_request,_held]; _owner setVariable ["ACME_inventoryEscrow",_escrow,true];};
    private _callbacks = missionNamespace getVariable ["ACME_inventoryCallbacks",createHashMap];
    private _callback = _callbacks getOrDefault [_request,[]];
    if (_callback isEqualTo []) exitWith {
        private _latest = (_owner getVariable ["ACME_inventoryMutations",createHashMap]) getOrDefault [_request,[]];
        if (!_ok || {!(_latest isEqualTo [])} || {_request in (_owner getVariable ["ACME_inventoryAdoptions",createHashMap])}) then {[_owner,_request,false,if (_ok) then {_latest} else {[]}] call ACME_fnc_inventoryLedgerSettle;};
    };
    _callbacks deleteAt _request; missionNamespace setVariable ["ACME_inventoryCallbacks",_callbacks];
    if ((_callback param [3,_owner getVariable ["ACME_providerLocalityEpoch",0]]) != (_owner getVariable ["ACME_providerLocalityEpoch",0])) exitWith {
        // Even rapid away/back transfers retire the originating input session.
        // Its journal can return the source, but its old UI must never restart.
        if (((_held param [6,[]]) param [0,""]) == "syringeDeliveryB285") then {
            [_owner,true] call ACME_fnc_syringeDeliveryRecover;
        } else {[_owner,_request,false] call ACME_fnc_inventoryLedgerSettle;};
    };
    [_ok,_callback select 2] call (_callback select 1);
};
if (_mode in ["return","consume"] && {_ok}) then {
    private _escrow = _owner getVariable ["ACME_inventoryEscrow",createHashMap];
    private _held = _escrow getOrDefault [_request,[]];
    if (_held isEqualTo []) exitWith {};
    private _requests = _owner getVariable ["ACME_inventoryRequests",createHashMap];
    private _mutations = _owner getVariable ["ACME_inventoryMutations",createHashMap];
    private _latestDesired = _mutations getOrDefault [_request,[]];
    private _followup = _mode == "return" && {(_record select 5) == "held"} && {!(_latestDesired isEqualTo [])} && {_latestDesired isNotEqualTo (_record select 2)};
    private _destination = objNull;
    private _needsPlacement = !_followup && {_mode == "return"} && {(_record select 5) == "held"}
        && {(_held select 4) == (_owner getVariable ["ACME_equipmentKitEpoch",0])};
    if (_needsPlacement) then {_destination = call _add; [_destination] call _notice;};
    if (_needsPlacement && {isNull _destination}) exitWith {}; // retain escrow and durable terminal retry.
    _requests deleteAt _request; _owner setVariable ["ACME_inventoryRequests",_requests,true];
    _mutations deleteAt _request; _owner setVariable ["ACME_inventoryMutations",_mutations,true];
    private _cache = _owner getVariable ["ACME_inventoryPayloadCache",createHashMap]; _cache deleteAt (_kind + ":" + _sid); _owner setVariable ["ACME_inventoryPayloadCache",_cache,false];
    if (_kind == "syringe") then {private _hidden = _owner getVariable ["ACME_syringeInventoryHidden",[]]; _hidden = _hidden select {_x != _sid}; _owner setVariable ["ACME_syringeInventoryHidden",_hidden,false];};
    private _adoptions = _owner getVariable ["ACME_inventoryAdoptions",createHashMap];
    if (_request in _adoptions) then {private _incoming = _owner getVariable ["ACME_inventoryIncoming",createHashMap]; _incoming deleteAt (str _token); _owner setVariable ["ACME_inventoryIncoming",_incoming,true];};
    _adoptions deleteAt _request; _owner setVariable ["ACME_inventoryAdoptions",_adoptions,true];
    _escrow deleteAt _request; _owner setVariable ["ACME_inventoryEscrow",_escrow,true];
    if (_followup) then {
        // Rearm logical custody from the certified return before materializing anything.
        // A kit that filled while waiting cannot spill an intermediate stale payload.
        private _serial = (missionNamespace getVariable ["ACME_inventoryEditSerial",0])+1; missionNamespace setVariable ["ACME_inventoryEditSerial",_serial];
        private _nextRequest = format ["inventory-edit:%1:%2:%3",clientOwner,_token,_serial];
        _escrow set [_nextRequest,[_token,+(_record select 2),_kind,_nextRequest,_held select 4,false]];
        _owner setVariable ["ACME_inventoryEscrow",_escrow,true];
        _mutations set [_nextRequest,_latestDesired]; _owner setVariable ["ACME_inventoryMutations",_mutations,true];
        [_owner,_nextRequest,{
            params ["_accepted","_args"]; _args params ["_owner","_request"];
            private _latest = (_owner getVariable ["ACME_inventoryMutations",createHashMap]) getOrDefault [_request,[]];
            [_owner,_request,false,if (_accepted) then {_latest} else {[]}] call ACME_fnc_inventoryLedgerSettle;
        },[_owner,_nextRequest]] call ACME_fnc_inventoryLedgerClaim;
    };
    [_owner] call ACME_fnc_inventoryLedgerReconcile;
};
