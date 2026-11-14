/* Replace the physical kit in its original inventory container. The package
 * weighs more than its contents, so a full container can still unpack it. */
params ["_unit",["_pickedUp",""]];
if (isNull _unit || {!local _unit} || {!alive _unit} || {is3DEN}
    || {_unit isEqualTo (missionNamespace getVariable ["ace_arsenal_center",objNull])}) exitWith {0};
private _kits = (items _unit) select {
    (_x find "ACME_IVStartKit_") == 0 && {_pickedUp == "" || {_x == _pickedUp}}
};
if (_kits isEqualTo []) exitWith {0};
if (_unit getVariable ["ACME_persistenceFrozen",false]) exitWith {
    if !(_unit getVariable ["ACME_ivStartKitDeferred",false]) then {
        _unit setVariable ["ACME_ivStartKitDeferred",true];
        [{
            params ["_unit"];
            isNull _unit || {!local _unit} || {!(_unit getVariable ["ACME_persistenceFrozen",false])}
        },{
            params ["_unit"];
            if (isNull _unit) exitWith {};
            _unit setVariable ["ACME_ivStartKitDeferred",false];
            [_unit] call ACME_fnc_ivStartKitUnpack;
        },[_unit]] call CBA_fnc_waitUntilAndExecute;
    };
    0
};

private _unpacked = 0;
private _contents = [["ACM_IV_18g",2],["ACME_NARBOA",1],["ACME_Tegaderm",1],["ACME_SalineLock",1],["ACM_SalineFlush_10",1]];
private _containers = [uniformContainer _unit,vestContainer _unit,backpackContainer _unit];
isNil {
    {
        private _kit = _x;
        private _index = _containers findIf {!isNull _x && {_kit in itemCargo _x}};
        if (_index >= 0) then {
            private _container = _containers select _index;
            private _beforeKits = {_x == _kit} count (itemCargo _container);
            _container addItemCargoGlobal [_kit,-1];
            if (({_x == _kit} count (itemCargo _container)) == _beforeKits - 1) then {
                private _added = [];
                private _complete = true;
                {
                    _x params ["_class","_count"];
                    if !(_container canAdd [_class,_count]) exitWith {_complete = false;};
                    private _before = {_x == _class} count (itemCargo _container);
                    _container addItemCargoGlobal [_class,_count];
                    private _delta = ({_x == _class} count (itemCargo _container)) - _before;
                    if (_delta > 0) then {_added pushBack [_class,-_delta];};
                    if (_delta != _count) exitWith {_complete = false;};
                } forEach _contents;
                if (_complete) then {
                    _unpacked = _unpacked + 1;
                } else {
                    {_container addItemCargoGlobal _x;} forEach _added;
                    _container addItemCargoGlobal [_kit,1];
                };
            };
        };
    } forEach _kits;
};
_unpacked
