/* [holder, snapshot, offlineSeconds=0] -> bool.
 * Restore native cargo/loadout FIRST, then call this on its owner (boxes: server).
 * Imported magazine IDs are funding evidence, never reused as live server IDs.
 * A local journal retains removed funding across a failed enqueue; repeating the
 * same application retries it without taking a second item or applying offline time twice. */
if (canSuspend) exitWith {private _ok = false; isNil {_ok = _this call ACME_fnc_coolerRestore;}; _ok};
params ["_holder","_snapshot",["_offline",0]];
if (isNull _holder || {!([_snapshot] call ACME_fnc_coolerSnapshotValid)}) exitWith {false};
if !(_offline isEqualType 0 && {finite _offline} && {_offline >= 0} && {_offline <= 1e9}) exitWith {false};
private _scope = _snapshot select 1;
private _records = _snapshot select 2;
private _now = serverTime;
private _key = str _snapshot;
private _decode = {
    params ["_row"];
    _row params ["","","_base","_age","_entries"];
    private _state = [_base,_now - _age - _offline,_entries apply {+_x},_now - _offline];
    [_state,_now] call ACME_fnc_coolerAdvance
};
if (_scope == "box") exitWith {
    if (!isServer) exitWith {false};
    private _boxIndex = ["ACME_BloodCoolerBox_CSWB1U","ACME_BloodCoolerBox_CSWB2U","ACME_BloodCoolerBox_CSWB4U"] find (typeOf _holder);
    if (_boxIndex < 0) exitWith {false};
    private _row = _records select 0;
    private _expected = ["ACME_BloodCooler_CSWB1U","ACME_BloodCooler_CSWB2U","ACME_BloodCooler_CSWB4U"] select _boxIndex;
    if ((_row select 2) != _expected) exitWith {false};
    // This API imports into a newly recreated object. Never overwrite a live deployed ledger identity.
    if ((_holder getVariable ["ACME_boxCoolerToken",0]) > 0) exitWith {false};
    private _receipt = _holder getVariable ["ACME_coolerBoxRestoreReceipt",[]];
    if (_receipt isEqualTo [_key,_offline]) exitWith {true};
    private _state = [_row] call _decode;
    if (count _state != 4) exitWith {false};
    private _oldCargo = itemCargo _holder;
    private _kept = _oldCargo select {(_x find "ACM_BloodBag_") != 0 && {(_x find "ACM_FreshBloodBag_") != 0}};
    clearItemCargoGlobal _holder;
    {_holder addItemCargoGlobal [_x,1];} forEach _kept;
    {_holder addItemCargoGlobal [_x select 0,1];} forEach (_state select 2);
    private _wanted = +_kept;
    {_wanted pushBack (_x select 0);} forEach (_state select 2);
    private _actual = +(itemCargo _holder);
    _wanted sort true;
    _actual sort true;
    if (_actual isNotEqualTo _wanted) exitWith {
        // Do not publish successful state if native cargo placement was refused.
        clearItemCargoGlobal _holder;
        {_holder addItemCargoGlobal [_x,1];} forEach _oldCargo;
        false
    };
    _holder setVariable ["ACME_boxCoolerState",_state,true];
    _holder setVariable ["ACME_boxCoolerClass",_expected,true];
    _holder setVariable ["ACME_boxCoolantStart",_state select 1,true];
    _holder setVariable ["ACME_boxCoolerSID","",true];
    _holder setVariable ["ACME_boxCoolerId",_row select 0,true];
    _holder setVariable ["ACME_coolerBoxRestoreReceipt",[_key,_offline],true];
    [_holder,_now] call ACME_fnc_coolerBoxReconcile;
    true
};
if (!local _holder) exitWith {false};
private _containers = if (_holder isKindOf "CAManBase") then {[uniformContainer _holder,vestContainer _holder,backpackContainer _holder]} else {[_holder]};
private _native = [];
{if (!isNull _x) then {_native append (magazinesAmmoCargo _x);};} forEach _containers;
private _classes = ["ACME_CoolerCarrier_CSWB1U","ACME_CoolerCarrier_CSWB2U","ACME_CoolerCarrier_CSWB4U"];
private _bases = ["ACME_BloodCooler_CSWB1U","ACME_BloodCooler_CSWB2U","ACME_BloodCooler_CSWB4U"];
private _journal = _holder getVariable ["ACME_coolerRestoreJournal",[]];
private _kit = _holder getVariable ["ACME_equipmentKitEpoch",0];
private _locality = _holder getVariable ["ACME_providerLocalityEpoch",0];
private _same = count _journal == 6 && {(_journal select 0) == _key} && {(_journal select 1) == _offline};
// Removed funding belongs to the kit and locality period that admitted it.
// Retain its evidence across retirement, but never inject it into a later kit.
if (_same && {!(_journal select 3)}
    && {(_journal select 4) != _kit || {(_journal select 5) != _locality}}) exitWith {false};
private _plan = if (_same) then {_journal select 2} else {[]};
private _present = 0;
private _bound = true;
{
    private _row = _x;
    private _tuple = [_classes select (_bases find (_row select 2)),_row select 1];
    private _count = {_x isEqualTo _tuple} count _native;
    if (_count > 1) exitWith {_bound = false;};
    if (_count == 1) then {_present = _present + 1;};
    if (_count == 0 && {!_same || {((_plan select _forEachIndex) select 4) == "source"}}) exitWith {_bound = false;};
} forEach _records;
if (!_bound) exitWith {false};
// A replay without restored source magazines is already applied. A genuinely
// reapplied saved loadout supplies all source tuples again and funds a new application.
if (_same && {_journal select 3} && {_present == 0}) exitWith {true};
if (_same && {_journal select 3} && {_present != count _records}) exitWith {false};
if (!_same && {count _journal == 6} && {!(_journal select 3)}) exitWith {false};
if (!_same || {_journal select 3}) then {
    _plan = [];
    {
        private _state = [_x] call _decode;
        if (count _state != 4) exitWith {_bound = false;};
        _plan pushBack [_x select 0,_x select 1,_x select 2,_state,"source",""];
    } forEach _records;
    if (!_bound) exitWith {};
    _journal = [_key,_offline,_plan,false,_kit,_locality];
    _holder setVariable ["ACME_coolerRestoreJournal",_journal,true];
};
if (!_bound) exitWith {false};
private _complete = true;
{
    private _row = _x;
    if (_kit != (_holder getVariable ["ACME_equipmentKitEpoch",0])
        || {_locality != (_holder getVariable ["ACME_providerLocalityEpoch",0])}) exitWith {_complete = false;};
    if ((_row select 4) == "issued") then {continue;};
    if ((_row select 4) == "source") then {
        private _class = _classes select (_bases find (_row select 2));
        if !([_holder,_class,_row select 1] call ace_common_fnc_removeSpecificMagazine) then {
            _complete = false;
        } else {
            private _stillPresent = false;
            {if (!isNull _x && {([_class,_row select 1] in (magazinesAmmoCargo _x))}) exitWith {_stillPresent = true;};} forEach _containers;
            if (_stillPresent) then {_complete = false;} else {
                _row set [4,"funded"];
                _holder setVariable ["ACME_coolerRestoreJournal",_journal,true];
            };
        };
    };
    if ((_row select 4) == "funded") then {
        private _sid = [_holder,_row select 2,_row select 3,false] call ACME_fnc_coolerIssue;
        if (_sid == "") then {_complete = false;} else {
            _row set [5,_sid];
            _row set [4,"issued"];
            _holder setVariable ["ACME_coolerRestoreJournal",_journal,true];
        };
    };
} forEach _plan;
_journal set [3,_complete];
_holder setVariable ["ACME_coolerRestoreJournal",_journal,true];
_complete
