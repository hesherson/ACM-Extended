/* Import CBA metadata after its native kit setter/reset boundary. Retry only
 * immutable metadata, never reapply the native loadout. true accepts the job;
 * ACME_persistenceLastRestoreOK becomes true only after custody has settled. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_persistenceRestoreExtended;}; _ok};
params ["_unit","_metadata",["_timeout",30],["_tick",false]];
if (isNull _unit || {!local _unit} || {!(_metadata isEqualType createHashMap)}
    || {!(_timeout isEqualType 0)} || {!finite _timeout} || {_timeout < 0} || {_timeout > 3600}) exitWith {false};
private _marked = "ACME_checkpoint_v1" in _metadata;
private _ok = !_marked || {(_metadata get "ACME_checkpoint_v1") isEqualTo [1,true]};
if (_marked) then {
    {if !(_x in _metadata) exitWith {_ok = false;};} forEach ["ACME_coolers_v1","ACME_inventory_v1","ACME_equipment_v1","ACME_blood_v1"];
};
if ("ACME_coolers_v1" in _metadata) then {_ok = _ok && {[_metadata get "ACME_coolers_v1"] call ACME_fnc_coolerSnapshotValid};};
if ("ACME_inventory_v1" in _metadata) then {_ok = _ok && {[_metadata get "ACME_inventory_v1"] call ACME_fnc_inventorySnapshotValid};};
if ("ACME_equipment_v1" in _metadata) then {_ok = _ok && {[_metadata get "ACME_equipment_v1"] call ACME_fnc_equipmentSnapshotValid};};
if ("ACME_blood_v1" in _metadata) then {_ok = _ok && {[_metadata get "ACME_blood_v1"] call ACME_fnc_bloodExposureSnapshotValid};};
if (!_ok) exitWith {_unit setVariable ["ACME_persistenceLastRestoreOK",false,false]; _unit setVariable ["ACME_coolerLastRestoreOK",false,false]; false};
if (_tick) exitWith {
    if ("ACME_inventory_v1" in _metadata) then {_ok = [_unit,_metadata get "ACME_inventory_v1"] call ACME_fnc_inventoryRestore;};
    if (_ok && {"ACME_coolers_v1" in _metadata}) then {
        _ok = [_unit,_metadata get "ACME_coolers_v1",0] call ACME_fnc_coolerRestore;
        _unit setVariable ["ACME_coolerLastRestoreOK",_ok,false];
    };
    if (_ok && {"ACME_equipment_v1" in _metadata}) then {_ok = [_unit,_metadata get "ACME_equipment_v1"] call ACME_fnc_equipmentRestore;};
    if (_ok && {"ACME_blood_v1" in _metadata}) then {
        private _bloodOK = _unit getVariable ["ACME_bloodLastRestoreOK",false];
        if (!_bloodOK) then {_ok = [_unit,_metadata get "ACME_blood_v1"] call ACME_fnc_bloodPersistenceRequest;};
    };
    private _settled = _ok && {[_unit] call ACME_fnc_persistenceReady}
        && {([_unit,"holder"] call ACME_fnc_coolerSnapshot) isNotEqualTo []}
        && {([_unit] call ACME_fnc_inventorySnapshot) isNotEqualTo []}
        && {([_unit] call ACME_fnc_equipmentSnapshot) isNotEqualTo []};
    _unit setVariable ["ACME_persistenceLastRestoreOK",_settled,false];
    _settled
};
private _kit = _unit getVariable ["ACME_equipmentKitEpoch",0];
private _locality = _unit getVariable ["ACME_providerLocalityEpoch",0];
private _pending = _unit getVariable ["ACME_persistenceRestorePending",[]];
private _key = str _metadata;
if (_pending isNotEqualTo [] && {(_pending select 2) != _kit || {(_pending select 3) != _locality}}) then {
    if ((_pending select 5) >= 0) then {[_pending select 5] call CBA_fnc_removePerFrameHandler;};
    _unit setVariable ["ACME_persistenceRestoreRetired",_pending,false];
    _unit setVariable ["ACME_persistenceRestorePending",[],false];
    _pending = [];
};
if (_pending isNotEqualTo [] && {(_pending select 0) != _key}) exitWith {false};
if (_pending isNotEqualTo [] && {(_pending select 5) >= 0}) exitWith {true};
private _copy = {if (_this isEqualType []) exitWith {_this apply {_x call _copy}}; _this};
private _frozen = createHashMap;
{if (_x in _metadata) then {_frozen set [_x,(_metadata get _x) call _copy];};} forEach ["ACME_checkpoint_v1","ACME_coolers_v1","ACME_inventory_v1","ACME_equipment_v1","ACME_blood_v1"];
_pending = [_key,_frozen,_kit,_locality,diag_tickTime + _timeout,-1];
_unit setVariable ["ACME_persistenceRestorePending",_pending,false];
_unit setVariable ["ACME_persistenceLastRestoreOK",false,false];
_unit setVariable ["ACME_bloodLastRestoreOK",false,false];
if ([_unit,_frozen,0,true] call ACME_fnc_persistenceRestoreExtended) exitWith {_unit setVariable ["ACME_persistenceRestorePending",[],false]; true};
private _pfh = [{
    params ["_args","_pfh"];
    _args params ["_unit","_key","_kit","_locality"];
    if (isNull _unit) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
    private _pending = _unit getVariable ["ACME_persistenceRestorePending",[]];
    if (_pending isEqualTo [] || {(_pending select 0) != _key}) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
    if (!local _unit || {_kit != (_unit getVariable ["ACME_equipmentKitEpoch",0])} || {_locality != (_unit getVariable ["ACME_providerLocalityEpoch",0])}) exitWith {
        _unit setVariable ["ACME_persistenceRestoreRetired",_pending,false];
        _unit setVariable ["ACME_persistenceRestorePending",[],false];
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    private _done = [_unit,_pending select 1,0,true] call ACME_fnc_persistenceRestoreExtended;
    if (_done || {diag_tickTime >= (_pending select 4)}) then {
        if (_done) then {_unit setVariable ["ACME_persistenceRestorePending",[],false];} else {
            _pending set [5,-1]; _unit setVariable ["ACME_persistenceRestorePending",_pending,false];
        };
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
},0.25,[_unit,_key,_kit,_locality]] call CBA_fnc_addPerFrameHandler;
_pending set [5,_pfh]; _unit setVariable ["ACME_persistenceRestorePending",_pending,false];
true
