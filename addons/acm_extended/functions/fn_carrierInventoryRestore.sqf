/* Settle custody once, in the patient owner's unscheduled frame. Live Gear/treatment changes win.
   Never overwrite a replacement vest or restore spent supplies from a stale loadout snapshot. */
params ["_patient", "_saved", "_savedVar"];
if (isNull _patient || {!local _patient}) exitWith {false};
private _class = _saved param [0, "", [""]];
if (_class == "") exitWith {false};
if (_patient getVariable [_savedVar + "Settled", false]) exitWith {true};
private _live = _patient getVariable [_savedVar + "Live", false];
if (!_live) exitWith {
    // B265: decode the OLD vest-only loadout before touching equipment. Modern
    // custody below uses live cargo, never this historical snapshot.
    if (vest _patient != "") exitWith {false};
    if !(_saved isEqualType [] && {count _saved == 2} && {(_saved select 1) isEqualType []}) exitWith {false};
    private _valid = true;
    private _budget = 10000; // Count expanded children too, not just top-level rows.
    private _decode = {
        params ["_rows", ["_depth", 0], ["_copies", 1]];
        private _out = [[], [], [], []];
        if (!(_rows isEqualType []) || {_depth > 8}) exitWith {_valid = false; _out};
        {
            if (!(_x isEqualType []) || {count _x < 2}) exitWith {_valid = false;};
            private _item = _x select 0;
            private _count = _x select 1;
            private _nested = [];
            private _hasNested = false;
            // Serialized container entry; accept both direct and counted
            // representations without mistaking an attached weapon for it.
            if (_item isEqualType "" && {_count isEqualType []} && {count _x == 2}) then {
                _nested = _count; _count = 1; _hasNested = true;
            };
            if (_item isEqualType [] && {count _item == 2}
                && {(_item select 0) isEqualType ""} && {(_item select 1) isEqualType []}) then {
                _nested = _item select 1; _item = _item select 0; _hasNested = true;
            };
            if (!(_count isEqualType 0) || {!finite _count} || {_count < 0}
                || {_count != floor _count} || {_count > 10000}) exitWith {_valid = false;};
            _budget = _budget - (_count * _copies);
            if (_budget < 0) exitWith {_valid = false;};
            if (_item isEqualType []) then {
                // Weapon detail preserves attachments and BOTH loaded mags.
                if (count _x != 2 || {count _item != 7} || {!((_item select 0) isEqualType "")}
                    || {(_item select 0) == ""}) exitWith {_valid = false;};
                if (([1,2,3,6] findIf {!((_item select _x) isEqualType "")}) >= 0) exitWith {_valid = false;};
                if (([4,5] findIf {!((_item select _x) isEqualType [])}) >= 0) exitWith {_valid = false;};
                {
                    private _mag = _item select _x;
                    if (_mag isNotEqualTo [] && {count _mag != 2
                        || {!((_mag select 0) isEqualType "")} || {(_mag select 0) == ""}
                        || {!((_mag select 1) isEqualType 0)} || {!finite (_mag select 1)}
                        || {(_mag select 1) < 0} || {(_mag select 1) != floor (_mag select 1)}}) exitWith {_valid = false;};
                } forEach [4,5];
                if (!_valid) exitWith {};
                for "_i" from 1 to _count do {(_out select 2) pushBack (+_item);};
            } else {
                if (!(_item isEqualType "") || {_item == ""}) exitWith {_valid = false;};
                private _isPack = getNumber (configFile >> "CfgVehicles" >> _item >> "isBackpack") > 0;
                private _isContainer = _isPack || {getText (configFile >> "CfgWeapons" >> _item >> "ItemInfo" >> "containerClass") != ""};
                if (_hasNested && {!_isContainer}) exitWith {_valid = false;};
                if (_isContainer) then {
                    if (count _x != 2) exitWith {_valid = false;};
                    private _child = [_nested, _depth + 1, _copies * _count] call _decode;
                    if (!_valid) exitWith {};
                    for "_i" from 1 to _count do {(_out select 3) pushBack [_item, _isPack, _child];};
                } else {
                    if (isClass (configFile >> "CfgMagazines" >> _item)) then {
                        if (count _x > 3) exitWith {_valid = false;};
                        private _ammo = _x param [2, getNumber (configFile >> "CfgMagazines" >> _item >> "count")];
                        if (!(_ammo isEqualType 0) || {!finite _ammo} || {_ammo < 0}
                            || {_ammo != floor _ammo}) exitWith {_valid = false;};
                        for "_i" from 1 to _count do {(_out select 1) pushBack [_item, _ammo];};
                    } else {
                        if (count _x != 2) exitWith {_valid = false;};
                        for "_i" from 1 to _count do {(_out select 0) pushBack _item;};
                    };
                };
            };
            if (!_valid) exitWith {};
        } forEach _rows;
        _out
    };
    private _snapshot = [_saved select 1] call _decode;
    if (!_valid) exitWith {false};
    _patient addVest _class;
    if (vest _patient != _class) exitWith {false};
    [vestContainer _patient, _snapshot] call ACME_fnc_carrierCargoPopulate;
    if !([_snapshot, [vestContainer _patient] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual) exitWith {
        removeVest _patient;
        diag_log "[ACME CARRIER B265] Legacy cargo rejected; original snapshot retained.";
        false
    };
    _patient setVariable [_savedVar + "Settled", true, true];
    true
};
// Do not discard either carrier when another mod equips a different vest during custody.
if (vest _patient != "") exitWith {false};
private _cargo = _patient getVariable ["ACME_carrierCargo", objNull];
if (!isNull _cargo && {(_cargo getVariable ["ACME_carrierSavedVar", ""]) != _savedVar
    || {!((_cargo getVariable ["ACME_carrierPatient", objNull]) isEqualTo _patient)}}) exitWith {false};
if (!isNull _cargo) then {_cargo setVariable ["ACME_carrierClosing", true, true];};
private _snapshot = [_cargo] call ACME_fnc_carrierCargoSnapshot;
_patient addVest _class;
if (vest _patient != _class) exitWith {
    if (!isNull _cargo) then {_cargo setVariable ["ACME_carrierClosing", false, true];};
    false
};
[vestContainer _patient, _snapshot] call ACME_fnc_carrierCargoPopulate;
if !([_snapshot, [vestContainer _patient] call ACME_fnc_carrierCargoSnapshot] call ACME_fnc_carrierCargoEqual) exitWith {
    // Keep the live holder authoritative if the returned vest rejected any contents.
    removeVest _patient;
    if (!isNull _cargo) then {_cargo setVariable ["ACME_carrierClosing", false, true];};
    diag_log "[ACME CARRIER] Restored cargo did not round-trip; live custody retained.";
    false
};
_patient setVariable ["ACME_carrierCargo", objNull, true];
_patient setVariable [_savedVar + "Live", false, true];
_patient setVariable [_savedVar + "Settled", true, true];
if (!isNull _cargo) then {
    // Pending supply refunds fall back to the donor once this exact container is gone.
    [_cargo, [[], [], [], []]] call ACME_fnc_carrierCargoPopulate;
    deleteVehicle _cargo;
};
true
