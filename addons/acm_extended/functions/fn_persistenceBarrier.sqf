/* Server-side ACME admission lease for a mission-controlled save boundary.
 * ["begin",units,[],timeout=30] -> lease ID or "" when busy.
 * ["validate",lease,[[unit,returnedExtendedLoadout],...]] -> bool.
 * ["end",lease] -> bool. A watchdog releases all flags after the bounded lease.
 * The mission MUST quiesce external ACE/native gameplay and physical transfers;
 * this lease fences ACME admissions, not the engine or other mods. */
if (canSuspend) exitWith {private _result = false; isNil {_result = _this call ACME_fnc_persistenceBarrier;}; _result};
params ["_mode","_value",["_captures",[]],["_timeout",30]];
if (!isServer) exitWith {if (_mode == "begin") then {""} else {false}};
private _all = missionNamespace getVariable ["ACME_persistenceBarriers",createHashMap];
if (_mode == "begin") exitWith {
    if !(call ACME_fnc_persistenceJournalsReady) exitWith {""};
    if !(_value isEqualType [] && {count _value > 0} && {count _value <= 128}
        && {_timeout isEqualType 0} && {finite _timeout} && {_timeout > 0} && {_timeout <= 300}) exitWith {""};
    private _units = _value arrayIntersect _value;
    if (count _units != count _value) exitWith {""};
    private _safe = true;
    private _baseline = [];
    {
        private _unit = _x;
        if (!(_unit isEqualType objNull) || {isNull _unit} || {!(_unit isKindOf "CAManBase")}
            || {_unit getVariable ["ACME_persistenceFrozen",false]} || {!([_unit,false] call ACME_fnc_persistenceReady)}) exitWith {_safe = false;};
        if ((["ACME_inventoryPending","ACME_inventoryEscrow","ACME_inventoryAdoptions"] findIf {count (_unit getVariable [_x,createHashMap]) > 0}) >= 0) exitWith {_safe = false;};
        _baseline pushBack [_unit,_unit getVariable ["ACME_equipmentKitEpoch",0],_unit getVariable ["ACME_providerLocalityEpoch",0],_unit getVariable ["ACME_clinicalEpoch",0],getUnitLoadout _unit];
    } forEach _units;
    if (!_safe) exitWith {""};
    private _sequence = 1 + (missionNamespace getVariable ["ACME_persistenceBarrierSequence",0]);
    missionNamespace setVariable ["ACME_persistenceBarrierSequence",_sequence];
    private _lease = format ["checkpoint:%1:%2",diag_tickTime,_sequence];
    private _deadline = diag_tickTime + _timeout;
    {
        _x setVariable ["ACME_persistenceLease",_lease,true];
        _x setVariable ["ACME_persistenceFrozen",true,true];
    } forEach _units;
    _all set [_lease,[_units,_baseline,_deadline]];
    missionNamespace setVariable ["ACME_persistenceBarriers",_all];
    [{
        params ["_args","_pfh"];
        _args params ["_lease"];
        private _all = missionNamespace getVariable ["ACME_persistenceBarriers",createHashMap];
        private _record = _all getOrDefault [_lease,[]];
        if (_record isEqualTo []) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
        if (diag_tickTime < (_record select 2)) exitWith {};
        ["end",_lease] call ACME_fnc_persistenceBarrier;
        [_pfh] call CBA_fnc_removePerFrameHandler;
    },0.25,[_lease]] call CBA_fnc_addPerFrameHandler;
    _lease
};
if !(_mode in ["validate","end"] && {_value isEqualType ""}) exitWith {false};
private _record = _all getOrDefault [_value,[]];
if (_record isEqualTo []) exitWith {false};
_record params ["_units","_baseline","_deadline"];
if (_mode == "end") exitWith {
    {
        if (!isNull _x && {(_x getVariable ["ACME_persistenceLease",""]) == _value}) then {
            _x setVariable ["ACME_persistenceFrozen",false,true];
            _x setVariable ["ACME_persistenceLease","",true];
        };
    } forEach _units;
    _all deleteAt _value;
    missionNamespace setVariable ["ACME_persistenceBarriers",_all];
    true
};
if !(call ACME_fnc_persistenceJournalsReady) exitWith {false};
if (diag_tickTime >= _deadline || {!(_captures isEqualType [])} || {count _captures != count _units}) exitWith {false};
private _seen = [];
private _safe = true;
{
    if (isNil "_x" || {!(_x isEqualType [])} || {count _x != 2} || {isNil {_x select 0}} || {isNil {_x select 1}}) exitWith {_safe = false;};
    _x params ["_unit","_extended"];
    if (!(_unit in _units) || {_unit in _seen} || {isNull _unit}
        || {!(_extended isEqualType [])} || {count _extended != 2} || {isNil {_extended select 0}} || {isNil {_extended select 1}}) exitWith {_safe = false;};
    _seen pushBack _unit;
    private _metadata = _extended select 1;
    if (!(_metadata isEqualType createHashMap) || {(_metadata getOrDefault ["ACME_checkpoint_v1",[]]) isNotEqualTo [1,true]}
        || {(_metadata getOrDefault ["ACME_checkpointLease_v1",""]) isNotEqualTo _value}) exitWith {_safe = false;};
    private _fingerprint = [_metadata] call ACME_fnc_persistenceFingerprint;
    if (_fingerprint == "" || {(_unit getVariable ["ACME_persistenceCaptureProof",[]]) isNotEqualTo [_value,_fingerprint]}) exitWith {_safe = false;};
    private _base = _baseline select (_units find _unit);
    if (!(_unit getVariable ["ACME_persistenceFrozen",false]) || {(_unit getVariable ["ACME_persistenceLease",""]) != _value}
        || {(_base select 1) != (_unit getVariable ["ACME_equipmentKitEpoch",0])}
        || {(_base select 2) != (_unit getVariable ["ACME_providerLocalityEpoch",0])}
        || {(_base select 3) != (_unit getVariable ["ACME_clinicalEpoch",0])}
        || {(_base select 4) isNotEqualTo (getUnitLoadout _unit)}
        || {(_extended select 0) isNotEqualTo (getUnitLoadout _unit)}
        || {!([_unit,false] call ACME_fnc_persistenceReady)}) exitWith {_safe = false;};
    if ((["ACME_inventoryPending","ACME_inventoryEscrow","ACME_inventoryAdoptions"] findIf {count (_unit getVariable [_x,createHashMap]) > 0}) >= 0) exitWith {_safe = false;};
} forEach _captures;
_safe
