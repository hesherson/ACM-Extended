/* Atomic local equipment checkpoint, compatible with CBA_fnc_setLoadout.
 * [] means retry. This captures one unit, not an atomic multi-owner world save. */
if (canSuspend) exitWith {private _result = []; isNil {_result = _this call ACME_fnc_persistenceSnapshot;}; _result};
params ["_unit"];
if (isNull _unit || {!local _unit} || {!(_unit isKindOf "CAManBase")}) exitWith {[]};
_unit setVariable ["ACME_persistenceBlockReason","",false];
if !([_unit] call ACME_fnc_persistenceReady) exitWith {[]};
private _lease = _unit getVariable ["ACME_persistenceLease",""];
if (_lease != "" && {!(_unit getVariable ["ACME_persistenceFrozen",false])}) exitWith {[]};
private _kit = _unit getVariable ["ACME_equipmentKitEpoch",0];
private _locality = _unit getVariable ["ACME_providerLocalityEpoch",0];
private _native = getUnitLoadout _unit;
private _coolers = [_unit,"holder"] call ACME_fnc_coolerSnapshot;
private _inventory = [_unit] call ACME_fnc_inventorySnapshot;
private _equipment = [_unit] call ACME_fnc_equipmentSnapshot;
private _blood = [_unit] call ACME_fnc_bloodExposureSnapshot;
// Native fresh-blood class IDs require a separate global donor-registry
// checkpoint. A local CBA kit cannot prove which donor a restarted ID names.
if (((str _native) find "ACM_FreshBloodBag_") >= 0 || {((str _coolers) find "ACM_FreshBloodBag_") >= 0}
    || {((str _equipment) find "ACM_FreshBloodBag_") >= 0}) exitWith {
    _unit setVariable ["ACME_persistenceBlockReason","native fresh blood requires the mission donor-registry adapter",false];
    []
};
_unit setVariable ["ACME_persistenceBlockReason","",false];
if (_coolers isEqualTo [] || {_inventory isEqualTo []} || {_equipment isEqualTo []} || {_blood isEqualTo []}) exitWith {[]};
if (_kit != (_unit getVariable ["ACME_equipmentKitEpoch",0]) || {_locality != (_unit getVariable ["ACME_providerLocalityEpoch",0])}
    || {_native isNotEqualTo (getUnitLoadout _unit)} || {!([_unit] call ACME_fnc_persistenceReady)}) exitWith {[]};
private _metadata = createHashMapFromArray [["ACME_coolers_v1",_coolers],["ACME_inventory_v1",_inventory],["ACME_equipment_v1",_equipment],["ACME_blood_v1",_blood],["ACME_checkpointLease_v1",_unit getVariable ["ACME_persistenceLease",""]],["ACME_checkpoint_v1",[1,true]]];
[_native,_metadata]
