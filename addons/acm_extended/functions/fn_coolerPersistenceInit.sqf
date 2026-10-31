/* CBA extended metadata. Synchronous hooks cannot cancel an arbitrary external
 * writer. ACME_checkpoint_v1 explicitly marks readiness; unattended adapters
 * should use persistenceCheckpoint and retain its native+metadata pair. */
if (missionNamespace getVariable ["ACME_coolerPersistenceInstalled",false]) exitWith {};
missionNamespace setVariable ["ACME_coolerPersistenceInstalled",true];
["CBA_loadoutGet",{
    params ["_unit","_native","_extendedInfo"];
    private _snapshot = [_unit] call ACME_fnc_persistenceSnapshot;
    private _ok = _snapshot isNotEqualTo [] && {(_snapshot select 0) isEqualTo _native};
    _extendedInfo set ["ACME_checkpoint_v1",[1,_ok]];
    _extendedInfo set ["ACME_checkpointLease_v1",if (_ok) then {(_snapshot select 1) get "ACME_checkpointLease_v1"} else {""}];
    {
        _extendedInfo set [_x,if (_ok) then {(_snapshot select 1) get _x} else {[]}];
    } forEach ["ACME_coolers_v1","ACME_inventory_v1","ACME_equipment_v1","ACME_blood_v1"];
}] call CBA_fnc_addEventHandler;
["CBA_loadoutSet",{
    params ["_unit","","_extendedInfo"];
    [_unit,_extendedInfo] call ACME_fnc_persistenceRestoreExtended;
}] call CBA_fnc_addEventHandler;

// Native inventory and kit/locality metadata may replicate after the CBA import.
// The owner retries the immutable request; success is acknowledged only after
// the server verifies its class counts and seeds the authoritative ledger.
["ACME_bloodPersistenceImport",{
    params ["_holder","_snapshot","_kit","_locality","_machine","_request"];
    if (!isServer || {isNull _holder} || {_machine != owner _holder}
        || {!(_request isEqualType [])} || {count _request != 2}
        || {(_request select 0) isNotEqualTo _machine}
        || {!((_request select 1) isEqualType 0)} || {!finite (_request select 1)}
        || {(_request select 1) < 1} || {(_request select 1) != floor (_request select 1)}
        || {_kit != (_holder getVariable ["ACME_equipmentKitEpoch",0])}
        || {_locality != (_holder getVariable ["ACME_providerLocalityEpoch",0])}) exitWith {};
    if ([_holder,_snapshot] call ACME_fnc_bloodExposureRestore) then {
        ["ACME_bloodPersistenceImported",[_holder,_request],_holder] call CBA_fnc_targetEvent;
    };
}] call CBA_fnc_addEventHandler;
["ACME_bloodPersistenceImported",{
    params ["_holder","_request"];
    if (isNull _holder || {!local _holder}) exitWith {};
    private _state = _holder getVariable ["ACME_bloodRestoreOutbox",[]];
    if (_state isEqualTo [] || {(_state select 4) isNotEqualTo _request}
        || {(_state select 1) != (_holder getVariable ["ACME_equipmentKitEpoch",0])}
        || {(_state select 2) != (_holder getVariable ["ACME_providerLocalityEpoch",0])}) exitWith {};
    _holder setVariable ["ACME_bloodRestoreOutbox",[],false];
    _holder setVariable ["ACME_bloodRestoreUnresolved",[],true];
    _holder setVariable ["ACME_bloodLastRestoreOK",true,false];
}] call CBA_fnc_addEventHandler;
