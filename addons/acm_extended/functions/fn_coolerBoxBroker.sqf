/* The server moves one token between native inventory and one deployed box.
 * A packing carrier is unusable until placement is proved and real cargo has
 * been reconciled. No timeout refreshes coolant or manufactures contents. */
if (!isServer) exitWith {};
if (canSuspend) exitWith {isNil {_this call ACME_fnc_coolerBoxBroker;};};
params ["_mode","_owner","_sid","_box","_request",["_kit",-1],["_locality",-1]];
if (isNull _owner || {_request == ""}) exitWith {};
private _receipts=missionNamespace getVariable ["ACME_coolerBoxReceipts",createHashMap];
private _past=_receipts getOrDefault [_request,[]];
private _index=missionNamespace getVariable ["ACME_inventoryLedgerIndex",createHashMap];
private _token=_index getOrDefault ["cooler:"+_sid,0];
private _record=missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
private _reply={
    params ["_ok",["_reason",""],["_entry",[]]];
    ["ACME_coolerBoxReply",[_mode,_owner,_sid,_token,_request,_ok,_box,_record param [6,0],_reason,_entry],_owner] call CBA_fnc_targetEvent;
};
if (_past isNotEqualTo []) exitWith {
    _past params ["_oldMode","_originalOwner","_oldSid","_oldToken","_oldBox"];
    if (_oldMode == "packAbort") exitWith {
        if (_owner isEqualTo _originalOwner) then {_mode="pack"; _sid=_oldSid; _token=_oldToken; _box=_oldBox; [false,"The cooler pickup was cancelled; its contents remain in the box."] call _reply;};
    };
    if (_oldMode == "draw") exitWith {
        if (_owner isNotEqualTo _originalOwner || {!(_mode in ["draw","drawAck"])}) exitWith {};
        _sid=_oldSid; _token=0; _box=_oldBox;
        if (_mode == "drawAck") then {
            _past set [7,true]; _receipts set [_request,_past]; missionNamespace setVariable ["ACME_coolerBoxReceipts",_receipts];
        };
        if (_past param [7,false]) then {_mode="drawDone"; [true] call _reply;}
        else {
            _mode="draw";
            private _entry=+(_past select 5);
            _entry set [1,(_entry select 1)+((serverTime-(_past select 6)) max 0)];
            [true,"",_entry] call _reply;
        };
    };
    if (_owner isEqualTo _originalOwner && {_mode in [_oldMode,"placed"]}) then {
        _mode=_oldMode; _sid=_oldSid; _token=_oldToken; _box=_oldBox;
        if (_mode == "pack") then {_mode="packDone";};
        _record=missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
        [true] call _reply;
    };
};
if (_mode == "draw") exitWith {
    if (isNull _box || {!alive _owner} || {_owner distance _box > 4.5}
        || {_box getVariable ["ACME_coolerPacking",false]} || {_box getVariable ["ACME_coolerRetired",false]}) exitWith {[false,"This cooler is unavailable."] call _reply;};
    private _bagClass=_sid;
    private _state=[_box,serverTime] call ACME_fnc_coolerBoxReconcile;
    if (_state isEqualTo []) exitWith {[false,"The cooler state is unavailable."] call _reply;};
    private _entries=+(_state select 2);
    private _selected=_entries findIf {(_x select 0) == _bagClass};
    private _cargo=itemCargo _box;
    private _nativeIndex=_cargo find _bagClass;
    if (_selected < 0 || {_nativeIndex < 0}) exitWith {[false,"That blood unit is no longer available."] call _reply;};
    private _entry=_entries deleteAt _selected;
    if ((_entry select 1) >= (missionNamespace getVariable ["ACME_bloodLooseSpoilTime",1800]) && {missionNamespace getVariable ["ACME_bloodSpoilEnabled",true]}) exitWith {
        _box addItemCargoGlobal [_bagClass,-1]; _box addItemCargoGlobal ["ACME_SpoiledBlood",1];
        _state set [2,_entries]; _box setVariable ["ACME_boxCoolerState",_state,true];
        [false,"That blood unit has spoiled."] call _reply;
    };
    // Remove the source once and retain its exact freshness in a durable receipt.
    // Failed client placement retries this receipt and cannot debit the box again.
    _box addItemCargoGlobal [_bagClass,-1];
    if (({_x == _bagClass} count (itemCargo _box)) != ({_x == _bagClass} count _cargo)-1) exitWith {[false,"The blood unit could not be moved."] call _reply;};
    _state set [2,_entries]; _box setVariable ["ACME_boxCoolerState",_state,true];
    _receipts set [_request,["draw",_owner,_bagClass,0,_box,_entry,serverTime,false]];
    missionNamespace setVariable ["ACME_coolerBoxReceipts",_receipts];
    _token=0; [true,"",_entry] call _reply;
};
if (_mode == "deploy") exitWith {
    private _payload=[_owner,"cooler",_sid,_request] call ACME_fnc_inventoryLedgerCertificate;
    if (_payload isEqualTo [] || {!alive _owner}) exitWith {[false,"The cooler could not be set down."] call _reply;};
    private _state=[_payload select 1,serverTime] call ACME_fnc_coolerAdvance;
    private _base=_state select 0;
    private _boxClass=switch (_base) do {
        case "ACME_BloodCooler_CSWB1U":{"ACME_BloodCoolerBox_CSWB1U"};
        case "ACME_BloodCooler_CSWB2U":{"ACME_BloodCoolerBox_CSWB2U"};
        case "ACME_BloodCooler_CSWB4U":{"ACME_BloodCoolerBox_CSWB4U"};
        default {""};
    };
    if (_boxClass == "") exitWith {[false,"Unknown blood cooler."] call _reply;};
    _box=createVehicle [_boxClass,_owner getRelPos [1.1,0],[],0,"CAN_COLLIDE"];
    if (isNull _box) exitWith {[false,"The cooler box could not be created."] call _reply;};
    _box setDir getDir _owner;
    clearWeaponCargoGlobal _box; clearMagazineCargoGlobal _box; clearItemCargoGlobal _box; clearBackpackCargoGlobal _box;
    _box setVariable ["ACME_boxCoolerClass",_base,true];
    _box setVariable ["ACME_boxCoolerState",_state,true];
    _box setVariable ["ACME_boxCoolantStart",_state select 1,true];
    _box setVariable ["ACME_boxCoolerSID",_sid,true];
    _box setVariable ["ACME_boxCoolerId",_sid,true];
    _box setVariable ["ACME_boxCoolerToken",_token,true];
    {_box addItemCargoGlobal [_x select 0,1];} forEach (_state select 2);
    private _expected=(_state select 2) apply {_x select 0}; _expected sort true;
    private _observed=itemCargo _box; _observed sort true;
    if (_expected isNotEqualTo _observed) exitWith {deleteVehicle _box; _box=objNull; [false,"The cooler contents could not be placed. The carried cooler is retained."] call _reply;};
    [_box,true,true,true] call ACM_core_fnc_setDraggingCapability;
    { _box setObjectTextureGlobal [_x,"#(argb,8,8,3)color(0.62,0.10,0.10,1.0,co)"]; } forEach [0,1,2];
    private _scale=missionNamespace getVariable ["ACME_coolerBoxScale",0.65];
    if (_scale != 1) then {
        [{params ["_box","_scale"]; if (isNull _box) exitWith {}; _box enableSimulation false; _box setObjectScale _scale;
            [_box, _scale] remoteExec ["ACME_fnc_coolerBoxApplyScale", 0, _box];},[_box,_scale],0.5] call CBA_fnc_waitAndExecute;
    };
    _record set [2,[_sid,_state]]; _record set [3,_box]; _record set [4,_request]; _record set [5,"deployed"]; _record set [6,(_record select 6)+1];
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
    _receipts set [_request,["deploy",_owner,_sid,_token,_box]];
    missionNamespace setVariable ["ACME_coolerBoxReceipts",_receipts];
    [true] call _reply;
};
if !(_mode in ["pack","placed","cancel","unplaced"]) exitWith {};
if (isNull _box) exitWith {[false,"The cooler box is no longer present."] call _reply;};
_token=_box getVariable ["ACME_boxCoolerToken",0];
_sid=_box getVariable ["ACME_boxCoolerSID",""];
_record=missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
private _finishAbort={
    private _rollback=_box getVariable ["ACME_coolerPackRollbackState",[]];
    if (_rollback isNotEqualTo []) then {
        private _cargo=itemCargo _box;
        private _expected=createHashMap;
        {_expected set [_x select 0,(_expected getOrDefault [_x select 0,0])+1];} forEach (_rollback select 2);
        {
            private _class=_x; private _need=(_expected get _class)-({_x == _class} count _cargo);
            if (_need>0) then {_box addItemCargoGlobal [_class,_need];};
        } forEach (keys _expected);
        private _restored=true;
        {private _class=_x; if (({_x == _class} count (itemCargo _box)) < (_expected get _class)) then {_restored=false;};} forEach (keys _expected);
        if (!_restored) exitWith {};
        _box setVariable ["ACME_boxCoolerState",_rollback,true];
        _box setVariable ["ACME_coolerPackRollbackState",[],false];
    };
    if ((_box getVariable ["ACME_coolerPackRollbackState",[]]) isNotEqualTo []) exitWith {};
    _box setVariable ["ACME_coolerPacking",false,false];
    private _restoredState=[_box,serverTime] call ACME_fnc_coolerBoxReconcile;
    if (_restoredState isEqualTo []) exitWith {_box setVariable ["ACME_coolerPacking",true,false];};
    _record set [2,[_sid,_restoredState]]; _record set [3,_box]; _record set [5,"deployed"]; _record set [6,(_record select 6)+1];
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
    _box setVariable ["ACME_coolerPacking",false,true];
    ["ACME_coolerBoxLock",[_box,false]] call CBA_fnc_globalEvent;
    private _origin=_box getVariable ["ACME_coolerPackOwner",_owner];
    _receipts set [_request,["packAbort",_origin,_sid,_token,_box]]; missionNamespace setVariable ["ACME_coolerBoxReceipts",_receipts];
    _mode="pack"; _owner=_origin;
    [false,_box getVariable ["ACME_coolerPackFailure","The cooler pickup was cancelled."]] call _reply;
};
private _abort={
    params ["_reason"];
    _box setVariable ["ACME_coolerPackFailure",_reason,false];
    _record set [3,_owner]; _record set [5,"packingAbort"]; _record set [6,(_record select 6)+1];
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
    private _hasToken=(([_owner,"cooler"] call ACME_fnc_inventoryLedgerNative) findIf {(_x select 0) == _token}) >= 0;
    private _wasPlaced=_request in (_owner getVariable ["ACME_coolerPackPlaced",createHashMap]);
    if (!_hasToken && {!_wasPlaced}) exitWith {call _finishAbort;};
    // A proven replacement kit retires the original input transaction. If its
    // placed carrier has since moved or vanished, fence that old physical alias
    // permanently before unlocking the real source. Mere absence never does so.
    private _origin=_box getVariable ["ACME_coolerPackOwner",objNull];
    private _admission=_record param [9,[]];
    private _originPlaced=!isNull _origin && {_request in (_origin getVariable ["ACME_coolerPackPlaced",createHashMap])};
    private _retiredKit=_originPlaced && {_admission isNotEqualTo []}
        && {(_admission select 0) != (_origin getVariable ["ACME_equipmentKitEpoch",0])};
    private _sequence=missionNamespace getVariable ["ACME_inventoryTokenSequence",0];
    if (!_hasToken && {_retiredKit} && {_sequence<65534}) exitWith {
        private _oldToken=_token;
        private _replacement=+_record;
        _record set [5,"spent"]; _record set [6,(_record select 6)+1]; _record set [10,"coolerKitRetirement"];
        missionNamespace setVariable [format ["ACME_inventoryToken_%1",_oldToken],_record,true];
        _token=_sequence+1; missionNamespace setVariable ["ACME_inventoryTokenSequence",_token];
        _replacement set [3,_box]; _replacement set [5,"deployed"]; _replacement set [6,0]; _replacement set [7,createHashMap];
        _record=_replacement;
        _index set ["cooler:"+_sid,_token]; missionNamespace setVariable ["ACME_inventoryLedgerIndex",_index,true];
        missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
        _box setVariable ["ACME_boxCoolerToken",_token,true];
        call _finishAbort;
    };
    _mode="packAbort"; [true,_reason] call _reply;
};
if (_mode == "unplaced") exitWith {
    private _removed=(_owner getVariable ["ACME_coolerPackRemoved",createHashMap]) getOrDefault [_request,0];
    if (count _record >= 9 && {(_record select 5) == "packingAbort"} && {(_record select 4) == _request} && {_removed == _token}
        && {(([_owner,"cooler"] call ACME_fnc_inventoryLedgerNative) findIf {(_x select 0) == _token}) < 0}) then {call _finishAbort;};
};
if (_mode == "cancel") exitWith {
    if (count _record >= 9 && {(_record select 5) == "packing"} && {(_record select 4) == _request} && {(_record select 3) isEqualTo _owner}) then {
        ["The cooler pickup was cancelled because control or equipment changed."] call _abort;
    };
};
if (_mode == "pack") exitWith {
    if (!alive _owner || {_owner distance _box > 4.5}) exitWith {[false,"Move closer to the cooler."] call _reply;};
    if (_box getVariable ["ACME_coolerRetired",false]) exitWith {[false,"This cooler has already been picked up."] call _reply;};
    if (isNull (uniformContainer _owner) && {isNull (vestContainer _owner)} && {isNull (backpackContainer _owner)}) exitWith {[false,"Wear a container before picking up the cooler."] call _reply;};
    private _packing=_box getVariable ["ACME_coolerPacking",false];
    if (_packing) exitWith {
        if (count _record >= 9 && {(_record select 4) == _request} && {(_record select 3) isEqualTo _owner}) then {
            if ((_record select 5) == "packingAbort") then {_mode="packAbort"; [true] call _reply;} else {[true] call _reply;};
        }
        else {[false,"Someone is already picking up this cooler."] call _reply;};
    };
    if ((_kit>=0 && {_kit != (_owner getVariable ["ACME_equipmentKitEpoch",0])})
        || {_locality>=0 && {_locality != (_owner getVariable ["ACME_providerLocalityEpoch",0])}}) exitWith {[false,"The cooler pickup was cancelled because control or equipment changed."] call _reply;};
    // Leave unrelated cargo untouched. Packing is available after it is removed.
    private _other=(itemCargo _box) select {((_x find "ACM_BloodBag_") != 0) && {(_x find "ACM_FreshBloodBag_") != 0}};
    if (_other isNotEqualTo [] || {weaponCargo _box isNotEqualTo []} || {magazineCargo _box isNotEqualTo []} || {backpackCargo _box isNotEqualTo []}) exitWith {
        [false,"Remove spoiled blood and other cargo before picking up the cooler."] call _reply;
    };
    private _state=[_box,serverTime] call ACME_fnc_coolerBoxReconcile;
    if (_state isEqualTo []) exitWith {[false,"The cooler state is unavailable."] call _reply;};
    private _usedMl=0; {_usedMl=_usedMl+([_x select 0] call ACME_fnc_coolerBagVolume);} forEach (_state select 2);
    private _capacity=getNumber (configFile >> "CfgWeapons" >> (_state select 0) >> "ACME_coolerCapacityMl");
    if (_capacity <= 0 || {_usedMl > _capacity}) exitWith {[false,"This cooler contains more blood than its rated capacity. Remove the excess before picking it up."] call _reply;};
    private _limit=missionNamespace getVariable ["ACME_bloodLooseSpoilTime",1800];
    if (missionNamespace getVariable ["ACME_bloodSpoilEnabled",true] && {((_state select 2) findIf {(_x select 1) >= _limit}) >= 0}) exitWith {
        [false,"Some blood has spoiled. Remove it before picking up the cooler."] call _reply;
    };
    if (_token == 0) then {
        private _sequence=missionNamespace getVariable ["ACME_inventoryTokenSequence",0];
        if (_sequence < 65534) then {
            _token=_sequence+1; missionNamespace setVariable ["ACME_inventoryTokenSequence",_token];
            _sid=format ["cooler:box:%1:%2",netId _box,_token];
            _index set ["cooler:"+_sid,_token]; missionNamespace setVariable ["ACME_inventoryLedgerIndex",_index,true];
            _record=["cooler",_sid,[_sid,_state],_box,"","deployed",0,createHashMap,["cooler",[_sid,_state]] call ACME_fnc_inventoryLedgerClass];
            _box setVariable ["ACME_boxCoolerSID",_sid,true]; _box setVariable ["ACME_boxCoolerId",_sid,true]; _box setVariable ["ACME_boxCoolerToken",_token,true];
        };
    };
    if (_token == 0 || {count _record < 9} || {(_record select 5) != "deployed"} || {(_record select 3) isNotEqualTo _box}) exitWith {
        [false,"This cooler cannot be claimed; its identity is unavailable."] call _reply;
    };
    _record set [2,[_sid,_state]]; _record set [3,_owner]; _record set [4,_request]; _record set [5,"packing"]; _record set [6,(_record select 6)+1];
    _record set [9,[_owner getVariable ["ACME_equipmentKitEpoch",0],_owner getVariable ["ACME_providerLocalityEpoch",0]]];
    missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
    _box setVariable ["ACME_coolerPacking",true,true];
    _box setVariable ["ACME_coolerPackOwner",_owner,true];
    private _boxMap=missionNamespace getVariable ["ACME_coolerPackingBoxes",createHashMap]; _boxMap set [str _token,_box];
    missionNamespace setVariable ["ACME_coolerPackingBoxes",_boxMap,true];
    ["ACME_coolerBoxLock",[_box,true]] call CBA_fnc_globalEvent;
    [true] call _reply;
};
if (count _record < 9 || {!((_record select 5) in ["packing","packingAbort"])} || {(_record select 4) != _request}) exitWith {};
if ((([_owner,"cooler"] call ACME_fnc_inventoryLedgerNative) findIf {(_x select 0) == _token}) < 0) exitWith {};
if ((_record select 5) == "packingAbort") exitWith {[_box getVariable ["ACME_coolerPackFailure","The cooler pickup was cancelled."]] call _abort;};
// The proof names the current holder, including an intervening native Gear handoff.
private _originalOwner=_record select 3;
_box setVariable ["ACME_coolerPacking",false,false];
private _state=[_box,serverTime] call ACME_fnc_coolerBoxReconcile;
_box setVariable ["ACME_coolerPacking",true,false];
if (_state isEqualTo []) exitWith {["The cooler state changed during pickup. Its contents remain in the box."] call _abort;};
private _usedMl=0; {_usedMl=_usedMl+([_x select 0] call ACME_fnc_coolerBagVolume);} forEach (_state select 2);
private _capacity=getNumber (configFile >> "CfgWeapons" >> (_state select 0) >> "ACME_coolerCapacityMl");
private _limit=missionNamespace getVariable ["ACME_bloodLooseSpoilTime",1800];
if (_capacity<=0 || {_usedMl>_capacity} || {missionNamespace getVariable ["ACME_bloodSpoilEnabled",true] && {((_state select 2) findIf {(_x select 1)>=_limit})>=0}}) exitWith {
    ["The cooler contents changed during pickup. Remove excess or spoiled blood before trying again."] call _abort;
};
private _cargo=itemCargo _box;
private _other=_cargo select {((_x find "ACM_BloodBag_") != 0) && {(_x find "ACM_FreshBloodBag_") != 0}};
// If external code inserted unrelated cargo during the handshake, retain that
// real container. Its cooler shell is retired and cannot issue another token.
{_box addItemCargoGlobal [_x select 0,-1];} forEach (_state select 2);
if (((itemCargo _box) findIf {([_x] call ACME_fnc_coolerBagVolume)>0}) >= 0) exitWith {
    _box setVariable ["ACME_coolerPackRollbackState",_state,false];
    ["The blood could not be moved safely. The cooler remains in the box."] call _abort;
};
_record set [2,[_sid,_state]]; _record set [3,_owner]; _record set [5,"held"]; _record set [6,(_record select 6)+1];
missionNamespace setVariable [format ["ACME_inventoryToken_%1",_token],_record,true];
_receipts set [_request,["pack",_originalOwner,_sid,_token,_box]];
missionNamespace setVariable ["ACME_coolerBoxReceipts",_receipts];
_box setVariable ["ACME_coolerRetired",true,true];
_box setVariable ["ACME_coolerPacking",false,true];
["ACME_coolerBoxLock",[_box,false]] call CBA_fnc_globalEvent;
if (_other isEqualTo [] && {weaponCargo _box isEqualTo []} && {magazineCargo _box isEqualTo []} && {backpackCargo _box isEqualTo []}) then {deleteVehicle _box;};
_mode="packDone";
[true] call _reply;
if (_originalOwner isNotEqualTo _owner && {!isNull _originalOwner}) then {
    ["ACME_coolerBoxReply",["packDone",_originalOwner,_sid,_token,_request,true,_box,_record select 6,""],_originalOwner] call CBA_fnc_targetEvent;
};
