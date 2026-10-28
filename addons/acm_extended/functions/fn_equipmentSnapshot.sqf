/* Equipment-only checkpoint. [] means busy/invalid; never save it as an empty store. */
if (canSuspend) exitWith {private _result = []; isNil {_result = _this call ACME_fnc_equipmentSnapshot;}; _result};
params ["_holder"];
if (isNull _holder || {!local _holder}) exitWith {[]};
private _restoreJournal = _holder getVariable ["ACME_equipmentRestoreJournal",[]];
if (count _restoreJournal > 0 && {(_restoreJournal param [1,-1]) == (_holder getVariable ["ACME_equipmentKitEpoch",0])}) exitWith {[]};
// Owner-authoritative transaction boundaries are not restart journals.
if (count (_holder getVariable ["ACME_medicationEscrow",createHashMap]) > 0
    || {count (_holder getVariable ["ACME_txRemoveRecovery",createHashMap]) > 0}
    || {private _sessions = _holder getVariable ["ACME_syringeDeliverySessions",createHashMap]; ((keys _sessions) findIf {((_sessions get _x) param [2,""]) != "settled"}) >= 0}) exitWith {[]};
private _busy = false;
if (hasInterface) then {
    if (_holder isEqualTo ACE_player && {(missionNamespace getVariable ["ACME_yBuildingActive",-1]) >= 0
        || {(missionNamespace getVariable ["ACME_spikingActive",[]]) isNotEqualTo []}}) then {_busy = true;};
    {
        private _pending = uiNamespace getVariable [_x,createHashMap];
        if (count _pending > 0) exitWith {_busy = true;};
    } forEach ["ACME_txPullPending","ACME_txRemoveContexts","ACME_usedRehangPending","ACME_yDiscardPending","ACME_yRefillPending"];
    private _draw = uiNamespace getVariable ["ACME_SK_PendingInjection",[]];
    if (_draw isNotEqualTo []) then {_busy = true;};
};
if (_busy) exitWith {[]};
private _map = _holder getVariable ["ACME_infusion_openVials",createHashMap];
if !(_map isEqualType createHashMap) exitWith {[]};
private _vials = (keys _map) apply {[_x,_map get _x]};
private _bagStore = _holder getVariable ["ACME_usedBags",[]];
if !(_bagStore isEqualType [] && {count _bagStore <= 1024} && {_bagStore isEqualTo [] || {_bagStore isEqualTypeAll []}}) exitWith {[]};
private _bags = _bagStore apply {+_x};
{
    if ((_x param [1,""]) == "FreshBlood") then {
        private _meta = _x param [8,[]];
        if (_meta isEqualTo []) then {
            private _registry = missionNamespace getVariable ["ACM_circulation_FreshBloodList",createHashMap];
            private _entry = _registry getOrDefault [_x param [7,-1],[]];
            _meta = if (count _entry >= 5) then {["freshV1",_entry select 3,_entry select 4,_entry select 2]} else {["freshMissingV1"]};
        };
        private _validFresh = _meta isEqualType [] && {count _meta == 4} && {(_meta select 0) == "freshV1"}
            && {(_meta select 1) isEqualType false} && {(_meta select 2) isEqualType 0} && {finite (_meta select 2)}
            && {(_meta select 3) isEqualTo (_x param [4,-1])};
        _x set [7,-1];
        _x set [8,if (_validFresh) then {["freshAgeV1",_meta select 1,(CBA_missionTime - (_meta select 2)) max 0,_meta select 3]} else {["freshMissingV1"]}];
    };
} forEach _bags;
private _vent = [];
if (([_holder,"ACME_Ventilator"] call ace_common_fnc_getCountOfItem) > 0 && {!(_holder getVariable ["ACME_vent_connected",false])}) then {
    {if (!isNil {_holder getVariable _x}) then {_vent pushBack [_x,_holder getVariable _x];};} forEach ([] call ACME_fnc_ventDeviceFields);
};
private _carrier = [];
private _cargo = _holder getVariable ["ACME_carrierCargo",objNull];
if (!isNull _cargo) then {
    if (_cargo getVariable ["ACME_carrierClosing",false] || {!((_cargo getVariable ["ACME_carrierPatient",objNull]) isEqualTo _holder)} || {vest _holder != ""}) exitWith {_busy = true;};
    private _savedVar = _cargo getVariable ["ACME_carrierSavedVar",""];
    private _saved = _holder getVariable [_savedVar,[]];
    private _tree = [_cargo] call ACME_fnc_equipmentCargoSnapshot;
    if (count _saved != 2 || {_tree isEqualTo []} || {_holder getVariable [_savedVar + "Settled",false]}) exitWith {_busy = true;};
    _carrier = [_savedVar,_saved select 0,_tree];
} else {
    // A destroyed live cargo owns an empty vest shell; never reuse its pre-removal contents.
    {
        private _saved = _holder getVariable [_x,[]];
        if (count _saved == 2 && {!(_holder getVariable [_x + "Settled",false])}) exitWith {
            if (_holder getVariable [_x + "Live",false]) then {_carrier = [_x,_saved select 0,[[[],[],[],[]],[1,[]],[1,"holder",[]],[]]];} else {_busy = true;};
        };
    } forEach ["ACME_chestAccess_vestLoadout","ACME_CS_vestLoadout","ACME_headElev_vestLoadout"];
};
if (_busy) exitWith {[]};
// getUnitLoadout contains nested containers, but the unit's ordinary opaque
// ledger projection scans only its three top-level clothing containers. Save
// each direct child separately; its cargo tree recursively carries metadata.
private _nested = [];
private _roots = [uniformContainer _holder,vestContainer _holder,backpackContainer _holder];
{
    private _slot = _forEachIndex;
    if (!isNull _x) then {
        {
            _x params ["_class","_child"];
            private _tree = [_child] call ACME_fnc_equipmentCargoSnapshot;
            if (_tree isEqualTo []) exitWith {_busy = true;};
            _nested pushBack [_slot,_class,_tree];
        } forEach everyContainer _x;
    };
    if (_busy) exitWith {};
} forEach _roots;
if (_busy) exitWith {[]};
private _snapshot = [1,_vials,_bags,_vent,_carrier,_nested];
if !([_snapshot] call ACME_fnc_equipmentSnapshotValid) exitWith {[]};
_snapshot
