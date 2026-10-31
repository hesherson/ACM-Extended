/* Convert one source-funded public cooler into an identified native carrier. */
if (canSuspend) exitWith {private _sid = ""; isNil {_sid = _this call ACME_fnc_coolerIssue;}; _sid};
params ["_owner","_base",["_state",[]],["_consumeBase",true]];
if (isNull _owner || {!local _owner}
    || {!(_base in ["ACME_BloodCooler_CSWB1U","ACME_BloodCooler_CSWB2U","ACME_BloodCooler_CSWB4U"])}) exitWith {""};
private _class = ["cooler",["",[_base]]] call ACME_fnc_inventoryLedgerClass;
if (_class == "") exitWith {""};
if (_state isNotEqualTo [] && {count _state != 4 || {(_state select 0) != _base}}) exitWith {""};
private _person=_owner isKindOf "CAManBase";
private _inputs=if (_person) then {(uniformItems _owner)+(vestItems _owner)+(backpackItems _owner)} else {itemCargo _owner};
private _before = { _x == _base } count _inputs;
if (_consumeBase && {_before < 1}) exitWith {""};
if (_consumeBase) then {
    if (_person) then {_owner removeItem _base;} else {
        _owner addItemCargoGlobal [_base,-1];
    };
};
// Funding is proved by actual inventory readback, not a cached ACE count.
private _after = { _x == _base } count (if (_person) then {(uniformItems _owner)+(vestItems _owner)+(backpackItems _owner)} else {itemCargo _owner});
if (_consumeBase && {_after != _before - 1}) exitWith {""};
if (_state isEqualTo []) then {
    private _legacyCoolant=_owner getVariable ["ACME_coolerCoolant",createHashMap];
    if (_base in _legacyCoolant) then {
        private _legacyStore=_owner getVariable ["ACME_coolerStore",createHashMap];
        _state=[_base,serverTime-(time-(_legacyCoolant get _base)),+(_legacyStore getOrDefault [_base,[]]),serverTime];
        _legacyCoolant deleteAt _base; _legacyStore deleteAt _base;
        [_owner,"coolant",_legacyCoolant,false] call ACME_fnc_coolerStateCommit;
        [_owner,"store",_legacyStore,false] call ACME_fnc_coolerStateCommit;
    };
};
if (_state isEqualTo []) then {
    private _contents = [];
    private _fill = missionNamespace getVariable ["ACME_coolerFillType","ON"];
    private _capacity = floor (getNumber (configFile >> "CfgWeapons" >> _base >> "ACME_coolerCapacityMl") / 500);
    for "_i" from 1 to _capacity do {_contents pushBack [format ["ACM_BloodBag_%1_500",_fill],0];};
    _state = [_base,serverTime,_contents,serverTime];
} else {_state = [_state,serverTime] call ACME_fnc_coolerAdvance;};
private _sequence = (missionNamespace getVariable ["ACME_coolerIssueSequence",0])+1;
missionNamespace setVariable ["ACME_coolerIssueSequence",_sequence];
private _sid = format ["cooler:%1:%2:%3:%4",clientOwner,netId _owner,diag_tickTime,_sequence];
private _rows = [_owner] call ACME_fnc_coolerRows;
_rows pushBack [_sid,_state];
if !([_owner,"cooler",_rows] call ACME_fnc_inventoryLedgerCommit) exitWith {
    if (_consumeBase) then {if (_person) then {_owner addItem _base;} else {_owner addItemCargoGlobal [_base,1];};};
    ""
};
_sid
