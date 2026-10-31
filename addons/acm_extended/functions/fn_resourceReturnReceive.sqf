/* One server-certified return attempt on a captured machine incarnation.
 * Private outcomes precede every native/virtual write. Partial and uncertain
 * outcomes cannot be retargeted by the server's cross-owner query protocol. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_resourceReturnReceive;};};
params ["_provider","_patient","_request","_products","_capturedOwner","_nonce","_attempt"];
if (isNull _provider || {!local _provider} || {clientOwner != _capturedOwner}
    || {_nonce != (missionNamespace getVariable ["ACME_syringeDeliveryMachineNonce",""])}
    || {!([_products] call ACME_fnc_resourceReturnProductsValid)}) exitWith {};
_products = [_products] call ACME_fnc_syringeDeliveryCopy;
private _key = format ["%1:%2",_request,_attempt];
private _fingerprint = [_provider,_patient,_products,_nonce];
private _decisions = missionNamespace getVariable ["ACME_resourceReturnDecisions",createHashMap];
private _decision = _decisions getOrDefault [_key,[]];
if (_decision isNotEqualTo [] && {(_decision select 0) isNotEqualTo _fingerprint}) exitWith {};
private _ack = {
    ["ACME_resourceReturn",["ack",[_provider,_patient,_request,_products,clientOwner,_nonce,_attempt]]] call CBA_fnc_serverEvent;
};
private _fridgeNotice={
    params ["_status"];
    if ((_request find "fridge:")!=0 || {count _products!=1} || {((_products select 0) select 0)!="item"}) exitWith {};
    private _parts=_request splitString ":";
    if (count _parts<4) exitWith {};
    private _token=[parseNumber (_parts select (count _parts-2)),parseNumber (_parts select (count _parts-1))];
    [_patient,(_products select 0) select 1,_provider,_token,_status,_request] call ACME_fnc_bloodFridgeReceive;
};
if (_decision isNotEqualTo [] && {(_decision select 1) == "delivered"}) exitWith {call _ack;["delivered"] call _fridgeNotice;};
if (_decision isNotEqualTo [] && {(_decision select 1) == "cancelled"}) exitWith {};
private _allProgress = missionNamespace getVariable ["ACME_resourceReturnProgress",createHashMap];
private _progress = _allProgress getOrDefault [_key,[]];
if (_progress isEqualTo []) then {_progress = _products apply {["pending",[]]};};
_decisions set [_key,[_fingerprint,"applying"]];
missionNamespace setVariable ["ACME_resourceReturnDecisions",_decisions];
private _received = _provider getVariable ["ACME_resourceReturnReceived",createHashMap];
private _prior = _received getOrDefault [_request,[]];
if (_prior isEqualTo [_products,"delivered"]) exitWith {
    // A complete public receipt may have arrived before this retry on the SAME
    // machine. A new attempt still requires the old incarnation's disposition.
    _decisions set [_key,[_fingerprint,"delivered"]];
    missionNamespace setVariable ["ACME_resourceReturnDecisions",_decisions]; call _ack;["delivered"] call _fridgeNotice;
};
_received set [_request,[_products,"uncertain"]];
_provider setVariable ["ACME_resourceReturnReceived",_received,true];
private _allDone = true;
private _hasEffects = false;
private _uncertain = false;
{
    private _index = _forEachIndex;
    private _state = _progress select _index;
    private _phase = _state select 0;
    if (_phase == "delivered") then {_hasEffects = true; continue;};
    if (_phase in ["applying","uncertain"]) then {_allDone = false; _uncertain = true; continue;};
    if (!local _provider || {clientOwner != _capturedOwner}
        || {_nonce != (missionNamespace getVariable ["ACME_syringeDeliveryMachineNonce",""])}) exitWith {_allDone = false; _uncertain = true;};
    _x params ["_kind","_value"];
    _state set [0,"applying"];
    _progress set [_index,_state]; _allProgress set [_key,_progress];
    missionNamespace setVariable ["ACME_resourceReturnProgress",_allProgress];
    private _placed = false;
    private _unplaced = false;
    private _evidence = [];
    if (_kind == "used") then {
        private _used = _provider getVariable ["ACME_usedBags",[]];
        private _id = _value select 0;
        private _found = _used findIf {(_x param [0,""]) == _id};
        if (_found < 0) then {
            _used pushBack ([_value] call ACME_fnc_syringeDeliveryCopy);
            _provider setVariable ["ACME_usedBags",_used,true];
        };
        private _actual = _provider getVariable ["ACME_usedBags",[]];
        private _matches = _actual select {(_x param [0,""]) == _id};
        _placed = count _matches == 1 && {(_matches select 0) isEqualTo _value};
        if (_placed) then {uiNamespace setVariable ["ACME_usedRowSig","__force__"];};
        _evidence = [_id,+_matches];
    };
    if (_kind == "item") then {
        // ACE's false return already means a ground spill. Its boolean alone
        // must never fund a second copy or a second fallback holder.
        private _before = {_x == _value} count ((uniformItems _provider)+(vestItems _provider)+(backpackItems _provider));
        private _near = nearestObject [_provider,"WeaponHolder"];
        private _groundBefore = if (isNull _near) then {0} else {{_x == _value} count itemCargo _near};
        private _placement = [_provider,_value] call ace_common_fnc_addToInventory;
        private _after = {_x == _value} count ((uniformItems _provider)+(vestItems _provider)+(backpackItems _provider));
        _placed = _after == _before + 1;
        if (!_placed && {!isNil "_placement"} && {_placement isEqualType []} && {count _placement == 2}
            && {(_placement select 0) isEqualType true} && {(_placement select 1) isEqualType objNull}) then {
            private _holder = _placement select 1;
            _unplaced = _after == _before;
            if (!isNull _holder && {_holder isNotEqualTo _provider}) then {
                private _expected = if (_holder isEqualTo _near) then {_groundBefore + 1} else {1};
                private _groundAfter = {_x == _value} count itemCargo _holder;
                _placed = _groundAfter == _expected;
                _unplaced = _unplaced && {_groundAfter == _expected - 1};
            };
        };
        _evidence = [_value,_before,_after,_near,_groundBefore,if (isNil "_placement") then {[]} else {_placement}];
    };
    private _status = if (_placed) then {"delivered"} else {if (_unplaced) then {"unplaced"} else {"uncertain"}};
    _progress set [_index,[_status,_evidence]];
    _allProgress set [_key,_progress]; missionNamespace setVariable ["ACME_resourceReturnProgress",_allProgress];
    if (_placed) then {_hasEffects = true;} else {_allDone = false; if (!_unplaced) then {_uncertain = true;};};
} forEach _products;
private _status = if (_allDone) then {"delivered"} else {if (!_hasEffects && {!_uncertain}) then {"unplaced"} else {"uncertain"}};
_decisions set [_key,[_fingerprint,_status]];
missionNamespace setVariable ["ACME_resourceReturnDecisions",_decisions];
if (_allDone) then {
    _received set [_request,[_products,"delivered"]];
    _provider setVariable ["ACME_resourceReturnReceived",_received,true]; call _ack;
    ["delivered"] call _fridgeNotice;
} else {
    if (_status=="uncertain") then {["uncertain"] call _fridgeNotice;};
};
