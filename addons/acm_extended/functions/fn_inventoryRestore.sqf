/* Restore native cargo first, then metadata on its owner. Every saved carrier
 * funds ONE fresh identity; a replay cannot mint another. Explicit old-netId to
 * object bindings are optional; otherwise patient ties use stable object IDs. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_inventoryRestore;}; _ok};
params ["_holder","_snapshot",["_rebind",createHashMap]];
if (isNull _holder || {!local _holder} || {!([_snapshot] call ACME_fnc_inventorySnapshotValid)}
    || {!(_rebind isEqualType createHashMap)}) exitWith {false};
private _records = _snapshot select 1;
private _key = str _snapshot;
private _journal = _holder getVariable ["ACME_inventoryRestoreJournal",[]];
private _kit = _holder getVariable ["ACME_equipmentKitEpoch",0];
private _locality = _holder getVariable ["ACME_providerLocalityEpoch",0];
private _same = count _journal == 6 && {(_journal select 0) == _key};
if (_same && {!(_journal select 3)} && {(_journal select 4) != _kit || {(_journal select 5) != _locality}}) exitWith {false};
if (!_same && {count _journal == 6} && {!(_journal select 3)}) exitWith {false};
private _containers = if (_holder isKindOf "CAManBase") then {[uniformContainer _holder,vestContainer _holder,backpackContainer _holder]} else {[_holder]};
private _native = [];
{if (!isNull _x) then {_native append (magazinesAmmoCargo _x);};} forEach _containers;
private _plan = if (_same) then {_journal select 2} else {[]};
private _present = 0;
private _bound = true;
{
    private _tuple = [_x select 2,_x select 1];
    private _count = {_x isEqualTo _tuple} count _native;
    if (_count > 1) exitWith {_bound = false;};
    if (_count == 1) then {_present = _present + 1;};
    if (_count == 0 && {!_same || {((_plan select _forEachIndex) select 2) == "source"}}) exitWith {_bound = false;};
} forEach _records;
if (!_bound) exitWith {false};
if (_same && {_journal select 3} && {_present == 0}) exitWith {true};
if (_same && {_journal select 3} && {_present != count _records}) exitWith {false};
if (!_same || {_journal select 3}) then {
    _plan = [];
    {
        private _serial = (missionNamespace getVariable ["ACME_inventoryRestoreSerial",0])+1;
        missionNamespace setVariable ["ACME_inventoryRestoreSerial",_serial];
        private _sid = format ["inventory-restore:%1:%2:%3:%4",clientOwner,diag_tickTime,random 1e9,_serial];
        _plan pushBack [+_x,_sid,"source",[]];
    } forEach _records;
    _journal = [_key,1,_plan,false,_kit,_locality];
    _holder setVariable ["ACME_inventoryRestoreJournal",_journal,true];
};
private _avoid = _holder getVariable ["ACME_inventoryImportAvoid",[]];
{_avoid pushBackUnique (_x select 1);} forEach _records;
_holder setVariable ["ACME_inventoryImportAvoid",_avoid,true];
private _complete = true;
{
    _x params ["_saved","_sid","_phase"];
    if (_kit != (_holder getVariable ["ACME_equipmentKitEpoch",0]) || {_locality != (_holder getVariable ["ACME_providerLocalityEpoch",0])}) exitWith {_complete = false;};
    if (_phase == "issued") then {continue;};
    _saved params ["_kind","_token","_class","_raw","_tie"];
    if (_phase == "source") then {
        if !([_holder,_class,_token] call ace_common_fnc_removeSpecificMagazine) then {_complete = false;} else {
            private _still = false;
            {if (!isNull _x && {[_class,_token] in magazinesAmmoCargo _x}) exitWith {_still = true;};} forEach _containers;
            if (_still) then {_complete = false;} else {
                _x set [2,"funded"];
                _holder setVariable ["ACME_inventoryRestoreJournal",_journal,true];
            };
        };
    };
    if ((_x select 2) == "funded") then {
        private _payload = +(_x select 3);
        if (_payload isEqualTo []) then {
            _payload = +_raw;
            _payload set [0,_sid];
            private _body = +(_raw select 1);
            if (_kind == "syringe") then {_body set [11,_sid];} else {
                _body set [0,_sid];
                private _fresh = _body param [11,[]];
                if (_fresh isNotEqualTo [] && {_fresh isNotEqualTo ["freshMissingV1"]}) then {
                    _body set [11,["freshV1",_fresh select 1,CBA_missionTime - (_fresh select 2),_fresh select 3]];
                };
                if (_tie isNotEqualTo []) then {
                    private _patient = _rebind getOrDefault [_tie select 0,objNull];
                    if (isNull _patient) then {_patient = ["decode",_tie] call ACME_fnc_clinicalObjectRef;};
                    _body set [5,if (isNull _patient) then {"ACME_unresolved:" + str _tie} else {netId _patient}];
                    private _ties = _holder getVariable ["ACME_inventoryPersistenceTies",createHashMap];
                    _ties set [_sid,+_tie]; _holder setVariable ["ACME_inventoryPersistenceTies",_ties,true];
                };
                private _med = +(_raw select 2);
                if (_med isNotEqualTo []) then {
                    _med set [0,_sid]; _med set [9,CBA_missionTime]; _med set [12,_holder]; _med set [13,objNull]; _med set [15,_sid];
                    _payload set [2,_med];
                };
            };
            _payload set [1,_body];
            _x set [3,_payload];
            _holder setVariable ["ACME_inventoryRestoreJournal",_journal,true];
        };
        if !([_holder,_kind,[_payload]] call ACME_fnc_inventoryLedgerCommit) then {_complete = false;} else {
            _x set [2,"issued"];
            _holder setVariable ["ACME_inventoryRestoreJournal",_journal,true];
        };
    };
} forEach _plan;
_journal set [3,_complete];
_holder setVariable ["ACME_inventoryRestoreJournal",_journal,true];
_complete
