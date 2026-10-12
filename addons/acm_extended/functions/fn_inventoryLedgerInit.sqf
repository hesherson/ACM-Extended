if (missionNamespace getVariable ["ACME_inventoryLedgerInitialized",false]) exitWith {};
missionNamespace setVariable ["ACME_inventoryLedgerInitialized",true];
["ACME_inventoryBroker",{_this call ACME_fnc_inventoryLedgerBroker;}] call CBA_fnc_addEventHandler;
["ACME_inventoryReply",{_this call ACME_fnc_inventoryLedgerReply;}] call CBA_fnc_addEventHandler;
// Native cargo reads deliberately bypass ACE's item-count cache during Take/Put.
["CAManBase","Take",{
    params ["_unit","_container","_class"];
    private _kind = getText (configFile >> "CfgMagazines" >> _class >> "ACME_inventoryKind");
    if (!(_kind in ["prepared","syringe"]) || {!local _unit}) exitWith {};
    private _tracked = missionNamespace getVariable ["ACME_inventoryTracked",[]]; _tracked pushBackUnique _unit; missionNamespace setVariable ["ACME_inventoryTracked",_tracked];
    private _internal = _container isEqualTo _unit || {_container in [uniformContainer _unit,vestContainer _unit,backpackContainer _unit]}
        || {!isNull _container && {objectParent _container isEqualTo _unit}};
    if (!_internal) then {[_unit,_kind] call ACME_fnc_inventoryLedgerMarkIncoming;};
    [{[_this select 0] call ACME_fnc_inventoryLedgerReconcile;},[_unit]] call CBA_fnc_execNextFrame;
}] call CBA_fnc_addClassEventHandler;
["CAManBase","Put",{params ["_unit","_container","_class"]; private _kind = getText (configFile >> "CfgMagazines" >> _class >> "ACME_inventoryKind"); if (_kind in ["prepared","syringe"] && {local _unit}) then {private _tracked = missionNamespace getVariable ["ACME_inventoryTracked",[]]; _tracked pushBackUnique _unit; missionNamespace setVariable ["ACME_inventoryTracked",_tracked];[{[_this select 0] call ACME_fnc_inventoryLedgerReconcile;},[_unit]] call CBA_fnc_execNextFrame;};}] call CBA_fnc_addClassEventHandler;
["CAManBase","Local",{
    params ["_unit","_local"];
    if (!_local || {isNull _unit}) exitWith {};
    private _participates = count (_unit getVariable ["ACME_inventoryPending",createHashMap]) > 0
        || {count (_unit getVariable ["ACME_inventoryEscrow",createHashMap]) > 0}
        || {count (_unit getVariable ["ACME_inventoryMutations",createHashMap]) > 0}
        || {count ([_unit] call ACME_fnc_inventoryLedgerNative) > 0};
    if (_participates) then {
        [_unit] call ACME_fnc_inventoryLedgerMarkIncoming;
        private _tracked = missionNamespace getVariable ["ACME_inventoryTracked",[]]; _tracked pushBackUnique _unit;
        missionNamespace setVariable ["ACME_inventoryTracked",_tracked];
        [_unit] call ACME_fnc_inventoryLedgerReconcile;
        [_unit] call ACME_fnc_preparedInventoryRecover;
    };
}] call CBA_fnc_addClassEventHandler;
[{
    private _tracked = (missionNamespace getVariable ["ACME_inventoryTracked",[]]) select {!isNull _x && {local _x}};
    missionNamespace setVariable ["ACME_inventoryTracked",_tracked];
    {
        private _owner = _x;
        if (isNull _owner || {!local _owner}) then {continue;};
        private _pending = _owner getVariable ["ACME_inventoryPending",createHashMap];
        {
            private _p = _y;
            if ((_p select 3) != (_owner getVariable ["ACME_equipmentKitEpoch",0])) then {_pending deleteAt _x; continue;};
            if ((_p param [6,"pending"]) == "blocked" || {CBA_missionTime < (_p param [4,0])}) then {continue;};
            private _n = (_p param [5,0])+1; _p set [5,_n]; _p set [4,CBA_missionTime+((2^(_n min 4)) min 15)]; _pending set [_x,_p];
            ["ACME_inventoryBroker",["register",_owner,_p select 0,_p select 1,_p select 2,""]] call CBA_fnc_serverEvent;
        } forEach _pending;
        _owner setVariable ["ACME_inventoryPending",_pending,false];
        private _requests = _owner getVariable ["ACME_inventoryRequests",createHashMap];
        {
            private _r = _y;
            if (CBA_missionTime < (_r select 1)) then {continue;};
            private _n = (_r select 2)+1; _r set [2,_n]; _r set [1,CBA_missionTime+((2^(_n min 4)) min 15)]; _requests set [_x,_r];
            ["ACME_inventoryBroker",_r select 0] call CBA_fnc_serverEvent;
        } forEach _requests;
        _owner setVariable ["ACME_inventoryRequests",_requests,false];
        if (!isNil "ACME_fnc_skInventoryImportNative") then {
            private _rows = _owner getVariable ["ACME_narcStore",[]];
            private _imported = [_owner,_rows] call ACME_fnc_skInventoryImportNative;
            if (_imported isNotEqualTo _rows) then {[_owner,_imported,true] call ACME_fnc_narcStoreCommit;};
        };
        [_owner] call ACME_fnc_inventoryLedgerReconcile;
        [_owner] call ACME_fnc_preparedInventoryRecover;
    } forEach _tracked;
},1] call CBA_fnc_addPerFrameHandler;

["unit",{params ["_unit"]; private _tracked = missionNamespace getVariable ["ACME_inventoryTracked",[]]; _tracked pushBackUnique _unit; missionNamespace setVariable ["ACME_inventoryTracked",_tracked];},true] call CBA_fnc_addPlayerEventHandler;
