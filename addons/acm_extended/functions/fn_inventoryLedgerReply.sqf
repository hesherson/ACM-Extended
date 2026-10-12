params ["_mode","_owner","_kind","_sid","_token","_request","_ok",["_attempt",0],["_requiredRevision",0]];
if (isNull _owner || {!local _owner}) exitWith {};
private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
// CBA reply may precede public state replication. Wait for the exact certificate, never infer failure.
private _proof = count _record >= 7 && {(_record select 0) == _kind} && {(_record select 1) == _sid} && {(_record select 6) >= _requiredRevision};
private _terminal = _mode in ["return","consume"];
if (_ok && {!_proof || {_mode == "claim" && {(_record select 4) != _request || {(_record select 5) != "reserved"}}} || {_terminal && {(_record select 4) != _request || {!((_record select 5) in ["held","spent"])}}}}) exitWith {
    if (_attempt < 40) then {[{_this call ACME_fnc_inventoryLedgerReply;},[_mode,_owner,_kind,_sid,_token,_request,_ok,_attempt+1,_requiredRevision],0.1] call CBA_fnc_waitAndExecute;};
};
private _class = ["ACME_PreparedIVSet","ACME_PreparedSyringe"] select (_kind == "syringe");
private _add = {
    if ((([_owner,_kind] call ACME_fnc_inventoryLedgerNative) findIf {(_x select 0) == _token}) >= 0) exitWith {};
    if (_owner canAdd [_class,1]) then {_owner addMagazine [_class,_token];};
    if ((([_owner,_kind] call ACME_fnc_inventoryLedgerNative) findIf {(_x select 0) == _token}) < 0) then {
        // Capacity can change between canAdd and addition. Spill the SAME identity, never default ammo.
        private _destination = createVehicle ["GroundWeaponHolder",getPosATL _owner,[],0,"CAN_COLLIDE"];
        _destination addMagazineAmmoCargo [_class,1,_token];
    };
};
if (_mode == "register") exitWith {
    private _pending = _owner getVariable ["ACME_inventoryPending",createHashMap];
    private _key = _kind + ":" + _sid;
    private _row = _pending getOrDefault [_key,[]];
    if (_row isEqualTo []) exitWith {}; // duplicate allocation ACK never adds a second magazine.
    if (!_ok) exitWith {_row set [6,"blocked"]; _pending set [_key,_row]; _owner setVariable ["ACME_inventoryPending",_pending,true]; diag_log format ["[ACME INVENTORY] Allocation unavailable for %1; funded payload remains pending.",_key];};
    if ((_row select 3) != (_owner getVariable ["ACME_equipmentKitEpoch",0])) exitWith {_pending deleteAt _key; _owner setVariable ["ACME_inventoryPending",_pending,true];};
    if ((_record select 2) isNotEqualTo (_row select 2)) exitWith {}; // pending registration retries retain latest funded payload.
    if ((_record select 3) isNotEqualTo _owner || {(_record select 5) != "held"}) exitWith {};
    call _add;
    _pending deleteAt _key; _owner setVariable ["ACME_inventoryPending",_pending,true];
    [_owner] call ACME_fnc_inventoryLedgerReconcile;
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
    [_ok,_callback select 2] call (_callback select 1);
};
if (_mode in ["return","consume"] && {_ok}) then {
    private _escrow = _owner getVariable ["ACME_inventoryEscrow",createHashMap];
    private _held = _escrow getOrDefault [_request,[]];
    if (_held isEqualTo []) exitWith {};
    private _requests = _owner getVariable ["ACME_inventoryRequests",createHashMap]; _requests deleteAt _request; _owner setVariable ["ACME_inventoryRequests",_requests,true];
    private _mutations = _owner getVariable ["ACME_inventoryMutations",createHashMap];
    private _latestDesired = _mutations getOrDefault [_request,[]];
    private _followup = _mode == "return" && {(_record select 5) == "held"} && {!(_latestDesired isEqualTo [])} && {_latestDesired isNotEqualTo (_record select 2)};
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
    } else {
        if (_mode == "return" && {(_record select 5) == "held"} && {(_held select 4) == (_owner getVariable ["ACME_equipmentKitEpoch",0])}) then {call _add;};
    };
    [_owner] call ACME_fnc_inventoryLedgerReconcile;
};
