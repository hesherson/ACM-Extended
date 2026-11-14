if (!hasInterface) exitWith {};
["unit", {
    params ["_unit", ["_previous", objNull]];
    if (!isNull _previous) then {
        private _handlers = _previous getVariable ["ACME_medicalChestInventoryEH", []];
        if (_handlers isNotEqualTo []) then {
            _previous removeEventHandler ["InventoryOpened", _handlers select 0];
            _previous removeEventHandler ["InventoryClosed", _handlers select 1];
            _previous setVariable ["ACME_medicalChestInventoryEH", []];
            _previous setVariable ["ACME_medicalChestViewing", objNull];
        };
    };
    if (isNull _unit || {(_unit getVariable ["ACME_medicalChestInventoryEH", []]) isNotEqualTo []}) exitWith {};

    private _open = _unit addEventHandler ["InventoryOpened", {
        params ["_unit", "_primary", "_secondary"];
        private _cargo = objNull;
        {
            if (!isNull _x && {_x isKindOf "ACME_MedicalChestCargo"}) exitWith {_cargo = _x;};
        } forEach [_primary, _secondary];
        if (isNull _cargo) exitWith {false};
        private _chest = _cargo getVariable ["ACME_medicalChestAnchor", objNull];
        if (isNull _chest || {!((_chest getVariable ["ACME_medicalChestState", [0, false]]) select 1)}) exitWith {true};
        _unit setVariable ["ACME_medicalChestViewing", _cargo];
        false
    }];
    private _close = _unit addEventHandler ["InventoryClosed", {
        params ["_unit"];
        _unit setVariable ["ACME_medicalChestViewing", objNull];
    }];
    _unit setVariable ["ACME_medicalChestInventoryEH", [_open, _close]];
}, true] call CBA_fnc_addPlayerEventHandler;

["ACME_medicalChestOpened", {
    // The event can arrive before the replicated state and cargo position.
    [{
        params ["_actor", "_chest", "_cargo", "_revision"];
        (_chest getVariable ["ACME_medicalChestState", []]) isEqualTo [_revision, true]
            && {!isNull _cargo} && {attachedTo _cargo isNotEqualTo objNull}
            && {_actor distance _cargo <= 4.5}
    }, {
        params ["_actor"];
        if (_actor isEqualTo ACE_player && {local _actor} && {alive _actor}
            && {!(_actor getVariable ["ACE_isUnconscious", false])}) then {
            _actor action ["Gear", _this select 2];
        };
    }, _this, 4] call CBA_fnc_waitUntilAndExecute;
}] call CBA_fnc_addEventHandler;

["ACME_medicalChestClosed", {
    params ["_cargo", "_revision"];
    if (isNull _cargo || {isNull ACE_player} || {(ACE_player getVariable ["ACME_medicalChestViewing", objNull]) isNotEqualTo _cargo}) exitWith {};
    private _chest = _cargo getVariable ["ACME_medicalChestAnchor", objNull];
    if (!isNull _chest && {((_chest getVariable ["ACME_medicalChestState", [0, false]]) select 0) > _revision}) exitWith {};
    private _inventory = findDisplay 602;
    if (!isNull _inventory) then {_inventory closeDisplay 2;};
}] call CBA_fnc_addEventHandler;
