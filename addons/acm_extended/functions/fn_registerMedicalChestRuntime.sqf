if (!hasInterface) exitWith {};
["unit", {
    params ["_unit", ["_previous", objNull]];
    if (!isNull _previous) then {
        private _handlers = _previous getVariable ["ACME_medicalChestInventoryEH", []];
        if (_handlers isNotEqualTo []) then {
            _previous removeEventHandler ["InventoryOpened", _handlers select 0];
            _previous removeEventHandler ["InventoryClosed", _handlers select 1];
            _previous setVariable ["ACME_medicalChestInventoryEH", []];
            [_previous] call ACME_fnc_medicalChestEndViewing;
        };
    };
    if (isNull _unit || {(_unit getVariable ["ACME_medicalChestInventoryEH", []]) isNotEqualTo []}) exitWith {};

    private _open = _unit addEventHandler ["InventoryOpened", {
        params ["_unit", "_primary", "_secondary"];
        [_unit] call ACME_fnc_medicalChestEndViewing;
        private _cargo = objNull;
        {
            if (!isNull _x && {_x isKindOf "ACME_MedicalChestCargo"}) exitWith {_cargo = _x;};
        } forEach [_primary, _secondary];
        if (isNull _cargo) exitWith {
            private _target = objNull;
            {
                if (([_x] call ACME_fnc_medicalChestTarget) isNotEqualTo []) exitWith {_target = _x;};
            } forEach [_primary, _secondary];
            if (isNull _target && {(isNull _primary || {_primary isEqualTo _unit}) && {isNull _secondary}}) then {
                private _aim = cursorObject;
                if (isNull _aim) then {_aim = cursorTarget;};
                if (!isNull _aim && {_unit distance _aim <= 4}
                    && {([_aim] call ACME_fnc_medicalChestTarget) isNotEqualTo []}) then {
                    _target = _aim;
                };
            };
            if (isNull _target || {_unit distance _target > 4}) exitWith {false};
            [ACME_fnc_medicalChestInventory, [_target, _unit]] call CBA_fnc_execNextFrame;
            true
        };
        private _chest = _cargo getVariable ["ACME_medicalChestAnchor", objNull];
        if (isNull _chest || {_chest getVariable ["ACME_medicalChestTransition", false]}) exitWith {true};
        (_chest getVariable ["ACME_medicalChestState", [0, false]]) params ["_revision", "_open"];
        if (!_open) exitWith {true};
        // Wait for the actual Gear display in case another InventoryOpened handler blocks it.
        _unit setVariable ["ACME_medicalChestViewing", [_cargo, _revision, CBA_missionTime + 0.8, -1]];
        false
    }];
    private _close = _unit addEventHandler ["InventoryClosed", {
        params ["_unit", "_container"];
        private _session = _unit getVariable ["ACME_medicalChestViewing", []];
        if (_session isNotEqualTo [] && {_container isEqualTo (_session select 0) || {isNull _container}}) then {
            [_unit] call ACME_fnc_medicalChestEndViewing;
        };
    }];
    _unit setVariable ["ACME_medicalChestInventoryEH", [_open, _close]];
}, true] call CBA_fnc_addPlayerEventHandler;

[{
    private _unit = ACE_player;
    if (isNull _unit) exitWith {};
    private _session = _unit getVariable ["ACME_medicalChestViewing", []];
    if (_session isEqualTo []) exitWith {};
    _session params ["_cargo", "_revision", "_deadline", "_nextReport"];
    private _chest = _cargo getVariable ["ACME_medicalChestAnchor", objNull];
    if (isNull _cargo || {isNull _chest} || {!alive _unit} || {_unit getVariable ["ACE_isUnconscious", false]}
        || {_unit distance _cargo > 4.5}
        || {(_chest getVariable ["ACME_medicalChestState", []]) isNotEqualTo [_revision, true]}) exitWith {
        [_unit] call ACME_fnc_medicalChestEndViewing;
    };
    if (isNull (findDisplay 602)) exitWith {
        if (_nextReport >= 0 || {CBA_missionTime >= _deadline}) then {
            [_unit] call ACME_fnc_medicalChestEndViewing;
        };
    };
    if (CBA_missionTime >= _nextReport && {!(_chest getVariable ["ACME_medicalChestTransition", false])}) then {
        _session set [3, CBA_missionTime + 1];
        [_cargo, _unit, _revision, true] remoteExecCall ["ACME_fnc_medicalChestView", 2];
    };
}, 0.10] call CBA_fnc_addPerFrameHandler;

["ACME_medicalChestOpened", {
    // The event can arrive before the replicated state and cargo position.
    [{
        params ["_actor", "_chest", "_cargo", "_revision"];
        (_chest getVariable ["ACME_medicalChestState", []]) isEqualTo [_revision, true]
            && {!(_chest getVariable ["ACME_medicalChestTransition", false])}
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

["ACME_medicalChestClosing", {
    params ["_cargo", "_revision"];
    if (isNull _cargo || {isNull ACE_player}) exitWith {};
    private _session = ACE_player getVariable ["ACME_medicalChestViewing", []];
    if (_session isEqualTo [] || {(_session select [0, 2]) isNotEqualTo [_cargo, _revision]}) exitWith {};
    [ACE_player] call ACME_fnc_medicalChestEndViewing;
    private _inventory = findDisplay 602;
    if (!isNull _inventory) then {_inventory closeDisplay 2;};
}] call CBA_fnc_addEventHandler;
