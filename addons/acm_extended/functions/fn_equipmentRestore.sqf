/* Explicit equipment restore after native loadout replacement; fresh-kit reset remains intentional.
 * A repeat in one kit never refills already spent virtual contents. Native restored cargo is
 * staged/read back once; a failed ledger enqueue retries its retained source-funding journal. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_equipmentRestore;}; _ok};
params ["_holder","_snapshot"];
if (isNull _holder || {!local _holder} || {!([_snapshot] call ACME_fnc_equipmentSnapshotValid)}) exitWith {false};
private _key = str _snapshot;
private _kit = _holder getVariable ["ACME_equipmentKitEpoch",0];
private _receipt = _holder getVariable ["ACME_equipmentRestoreReceipt",[]];
if (_receipt isEqualTo [_key,_kit]) exitWith {true};
_snapshot params ["","_vials","_bags","_vent","_carrier"];
if (_vent isNotEqualTo [] && {([_holder,"ACME_Ventilator"] call ace_common_fnc_getCountOfItem) < 1 || {_holder getVariable ["ACME_vent_connected",false]}}) exitWith {false};
private _journal = _holder getVariable ["ACME_equipmentRestoreJournal",[]];
if (count _journal > 0 && {(_journal param [1,-1]) == _kit} && {_journal isNotEqualTo [_key,_kit]}) exitWith {false};
private _cargo = _holder getVariable ["ACME_carrierCargo",objNull];
if (_carrier isNotEqualTo [] && {vest _holder != ""}) exitWith {false};
if (!isNull _cargo && {_journal isNotEqualTo [_key,_kit]}) exitWith {false};
// Match the saved nested children to existing restored native cargo BEFORE any
// metadata exchange. Never populate a child on retry: its import journal owns
// removed source tuples until the replacement grants are physically settled.
private _nested = _snapshot param [5,[]];
private _roots = [uniformContainer _holder,vestContainer _holder,backpackContainer _holder];
private _available = [];
{
    private _slot = _forEachIndex;
    if (!isNull _x) then {{_available pushBack [_slot,_x select 0,_x select 1];} forEach everyContainer _x;};
} forEach _roots;
private _nestedPlan = [];
private _bound = true;
{
    _x params ["_slot","_class","_tree"];
    private _index = _available findIf {(_x select 0) == _slot && {(_x select 1) == _class} && {
        [_tree select 0,[_x select 2] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual
        || {((_x select 2) getVariable ["ACME_equipmentCargoRestoreKey",""]) == str _tree}
    }};
    if (_index < 0) exitWith {_bound = false;};
    _nestedPlan pushBack [(_available deleteAt _index) select 2,_tree];
} forEach _nested;
if (!_bound || {_available isNotEqualTo []}) exitWith {false};
_holder setVariable ["ACME_equipmentRestoreJournal",[_key,_kit],true];
private _nestedDone = true;
{if !(_x call ACME_fnc_equipmentCargoRestore) then {_nestedDone = false;};} forEach _nestedPlan;
if (!_nestedDone) exitWith {false};
if (_carrier isNotEqualTo []) then {
    _carrier params ["_savedVar","_class","_tree"];
    if (isNull _cargo) then {
        _cargo = createVehicle ["ACME_RemovedCarrierCargo",getPosATL _holder,[],0,"CAN_COLLIDE"];
        if (isNull _cargo) exitWith {};
        [_cargo,_tree select 0] call ACME_fnc_carrierCargoPopulate;
        if !([_tree select 0,[_cargo] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual) exitWith {deleteVehicle _cargo; _cargo = objNull;};
        _cargo allowDamage false;
        _cargo setVariable ["ACME_carrierClosing",true,true];
        _cargo setVariable ["ACME_carrierPatient",_holder,true];
        _cargo setVariable ["ACME_carrierSavedVar",_savedVar,true];
        [_cargo,false,false,true] call ACM_core_fnc_setDraggingCapability;
        [_cargo,false,true] call ACM_core_fnc_setCargoLoadCapability;
        _holder setVariable ["ACME_carrierCargo",_cargo,true];
        _holder setVariable [_savedVar,[_class,[]],true];
        _holder setVariable [_savedVar + "Live",true,true];
        _holder setVariable [_savedVar + "Settled",false,true];
        _holder setVariable [_savedVar + "KitEpoch",_kit,true];
    };
};
if (_carrier isNotEqualTo [] && {isNull _cargo}) exitWith {false};
if (_carrier isNotEqualTo [] && {!([_cargo,_carrier select 2] call ACME_fnc_equipmentCargoRestore)}) exitWith {false};
if (!isNull _cargo) then {_cargo setVariable ["ACME_carrierClosing",false,true];};
// Human-held removal/elevation controllers do not resume across restart. Return
// the exact current holder contents through normal readback, rather than create
// a synthetic session. An engine refusal retains the live holder for retry.
private _returned = true;
if (_carrier isNotEqualTo []) then {
    private _savedVar = _carrier select 0;
    private _saved = _holder getVariable [_savedVar,[]];
    _returned = [_holder,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore;
    if (_returned) then {
        _holder setVariable [_savedVar,[],true];
        // Native transfer moved the same opaque magazines out of the temporary
        // holder. Nested native containers are recreated by that transfer too;
        // their ledger records still name the deleted source children. Enroll
        // each descendant so its exact native carrier can certify new custody.
        private _tracked = missionNamespace getVariable ["ACME_inventoryTracked",[]];
        _tracked pushBackUnique _holder;
        private _descendants = [];
        private _walk = {
            params ["_container",["_depth",0]];
            if (isNull _container || {_depth > 8}) exitWith {};
            {
                private _child = _x select 1;
                _descendants pushBackUnique _child;
                [_child,_depth+1] call _walk;
            } forEach everyContainer _container;
        };
        [vestContainer _holder] call _walk;
        {_tracked pushBackUnique _x;} forEach _descendants;
        missionNamespace setVariable ["ACME_inventoryTracked",_tracked];
        [_holder] call ACME_fnc_inventoryLedgerReconcile;
        {[_x] call ACME_fnc_inventoryLedgerReconcile;} forEach _descendants;
        if (_savedVar == "ACME_headElev_vestLoadout") then {
            _holder setVariable ["ACME_headElev_vestRemoved",false,true];
            _holder setVariable ["ACME_headElev_propVest","",true];
            _holder setVariable ["ACME_headElev_propVestItems",[],true];
        };
    };
};
if (!_returned) exitWith {false};
// All fallible native operations finished. Replace, never append, the virtual stores.
private _map = createHashMapFromArray (_vials apply {+_x});
[_holder,_map] call ACME_fnc_openVialStoreCommit;
private _liveBags = _bags apply {
    private _row = +_x;
    if ((_row select 1) == "FreshBlood") then {
        private _meta = _row select 8;
        _row set [7,-1];
        _row set [8,if (_meta isEqualTo ["freshMissingV1"]) then {+_meta} else {["freshV1",_meta select 1,CBA_missionTime - (_meta select 2),_meta select 3]}];
    };
    _row
};
_holder setVariable ["ACME_usedBags",_liveBags,true];
if !(_holder getVariable ["ACME_vent_connected",false]) then {
    {_holder setVariable [_x,nil,true];} forEach ([] call ACME_fnc_ventDeviceFields);
    {_holder setVariable [_x select 0,_x select 1,true];} forEach _vent;
    _holder setVariable ["ACME_vent_battLastT",-1,false];
    _holder setVariable ["ACME_vent_powerOn",false,true];
    _holder setVariable ["ACME_vent_hasBooted",false,true];
};
_holder setVariable ["ACME_equipmentRestoreReceipt",[_key,_kit],true];
_holder setVariable ["ACME_equipmentRestoreJournal",[],true];
true
