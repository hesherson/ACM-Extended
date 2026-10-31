/* [holder] -> [1,rows], or [] while any preparation has unsettled custody.
 * Native cargo and this metadata belong to the SAME coordinated checkpoint.
 * Coolers have a separate clock-normalized snapshot. */
params ["_holder"];
if (isNull _holder) exitWith {[]};
private _shieldPending = missionNamespace getVariable ["ACM_ophthalmology_shieldPending", createHashMap];
if (!(_shieldPending isEqualType createHashMap) || {count _shieldPending > 0}) exitWith {[]};
if (count (_holder getVariable ["ACM_ophthalmology_shieldBindings",[]]) > 0) exitWith {[]};
private _shieldIncoming = _holder getVariable ["ACM_ophthalmology_shieldIncoming",createHashMap];
if (!(_shieldIncoming isEqualType createHashMap) || {count _shieldIncoming > 0}) exitWith {[]};
private _busy = false;
{if (count (_holder getVariable [_x,createHashMap]) > 0) exitWith {_busy = true;};} forEach [
    "ACME_inventoryPending","ACME_inventoryEscrow","ACME_inventoryMutations",
    "ACME_inventoryRequests","ACME_inventoryAdoptions","ACME_inventoryPlacement","ACME_inventoryIncoming"
];
if (_busy || {(_holder getVariable ["ACME_inventoryIncomingKinds",[]]) isNotEqualTo []}) exitWith {[]};
private _restore = _holder getVariable ["ACME_inventoryRestoreJournal",[]];
if (count _restore == 6 && {!(_restore select 3)}) exitWith {[]};
private _native = ([_holder] call ACME_fnc_inventoryLedgerNative) select {(_x select 1) in ["prepared","syringe"]};
private _containers = if (_holder isKindOf "CAManBase") then {[uniformContainer _holder,vestContainer _holder,backpackContainer _holder]} else {[_holder]};
private _tuples = [];
{if (!isNull _x) then {_tuples append (magazinesAmmoCargo _x);};} forEach _containers;
private _carriers = _tuples select {(getText (configFile >> "CfgMagazines" >> (_x select 0) >> "ACME_inventoryKind")) in ["prepared","syringe"]};
if (count _carriers != count _native) exitWith {[]}; // includes invalid/default ammo IDs, never silently omitted.
private _savedTies = _holder getVariable ["ACME_inventoryPersistenceTies",createHashMap];
private _rows = [];
private _valid = true;
{
    _x params ["_token","_kind"];
    private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_token],[]];
    if (count _record < 9 || {(_record select 0) != _kind} || {(_record select 3) isNotEqualTo _holder}
        || {(_record select 5) != "held"}) exitWith {_valid = false;};
    private _class = _record select 8;
    if (({_x isEqualTo [_class,_token]} count _tuples) != 1) exitWith {_valid = false;};
    private _raw = _record select 2;
    if !(_raw isEqualType [] && {count _raw == ([3,2] select (_kind == "syringe"))}
        && {(_raw select 0) isEqualTo (_record select 1)} && {(_raw select 1) isEqualType []}) exitWith {_valid = false;};
    if (_kind == "prepared" && {count (_raw select 1) < 9 || {!((_raw select 2) isEqualType [])}
        || {([1,2,5] findIf {!(((_raw select 1) select _x) isEqualType "")}) >= 0}}) exitWith {_valid = false;};
    private _payload = +_raw;
    private _cache = (_holder getVariable ["ACME_inventoryPayloadCache",createHashMap]) getOrDefault [_kind + ":" + (_record select 1),[]];
    if (_cache isNotEqualTo [] && {(_cache select 1) > (_record select 6)}) exitWith {_valid = false;};
    private _tie = [];
    if (_kind == "prepared") then {
        private _set = +(_payload select 1);
        if ((_set param [5,""]) != "") then {
            _tie = _savedTies getOrDefault [_payload select 0,[]];
            if (_tie isEqualTo []) then {
                private _patient = objectFromNetId (_set select 5);
                _tie = if (isNull _patient) then {[_set select 5,"",""]} else {["encode",_patient] call ACME_fnc_clinicalObjectRef};
            };
        };
        _set set [5,""];
        // Fresh-blood class suffixes name a mission-local donor registry slot.
        // Capture immutable donor data now; never re-resolve that old slot after
        // restart, where the numeric ID can belong to an unrelated donor.
        private _fresh = ((_set param [1,""]) find "ACM_FreshBloodBag_") == 0
            || {((_set param [2,""]) find "FreshBloodBag_") == 0};
        if (_fresh) then {
            private _meta = _set param [11,[]];
            if (_meta isEqualTo []) then {
                private _parts = (_set select 1) splitString "_";
                private _fid = if (count _parts >= 4) then {parseNumber (_parts select 3)} else {-1};
                private _registry = missionNamespace getVariable ["ACM_circulation_FreshBloodList",createHashMap];
                private _entry = _registry getOrDefault [_fid,[]];
                _meta = if (count _entry >= 5) then {["freshV1",_entry select 3,_entry select 4,_entry select 2]} else {["freshMissingV1"]};
            };
            private _known = _meta isEqualType [] && {count _meta == 4} && {(_meta select 0) == "freshV1"}
                && {(_meta select 1) isEqualType true} && {(_meta select 2) isEqualType 0} && {finite (_meta select 2)}
                && {(_meta select 3) isEqualType 0} && {(_meta select 3) in [0,1,2,3,4,5,6,7]};
            while {count _set < 11} do {_set pushBack 0;};
            _set set [11,if (_known) then {["freshAgeV1",_meta select 1,(CBA_missionTime - (_meta select 2)) max 0,_meta select 3]} else {["freshMissingV1"]}];
        };
        _payload set [1,_set];
        private _med = +(_payload param [2,[]]);
        if (_med isNotEqualTo []) then {
            _med set [9,0]; _med set [11,0]; _med set [12,""]; _med set [13,""];
            _payload set [2,_med];
        };
    } else {_payload set [1,+(_payload select 1)];};
    _rows pushBack [_kind,_token,_class,_payload,_tie];
} forEach _native;
if (!_valid) exitWith {[]};
private _snapshot = [1,_rows];
if !([_snapshot] call ACME_fnc_inventorySnapshotValid) exitWith {[]};
_snapshot
