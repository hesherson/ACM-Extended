/* Stable equipment facts for an owner-certified save lease. Empty string means
 * missing/invalid metadata. Elapsed cold-chain/collection ages are deliberately
 * excluded; native identity, contents, exact volumes and device settings remain.
 * This is a comparison value, not a cryptographic digest or authorization key. */
params ["_metadata"];
if !(_metadata isEqualType createHashMap) exitWith {""};
private _valid = true;
{
    _x params ["_key", "_validator"];
    if !(_key in _metadata && {[_metadata get _key] call _validator}) exitWith {_valid = false;};
} forEach [
    ["ACME_coolers_v1", ACME_fnc_coolerSnapshotValid],
    ["ACME_inventory_v1", ACME_fnc_inventorySnapshotValid],
    ["ACME_equipment_v1", ACME_fnc_equipmentSnapshotValid],
    ["ACME_blood_v1", ACME_fnc_bloodExposureSnapshotValid]
];
if (!_valid) exitWith {""};
private _copy = {if (_this isEqualType []) exitWith {_this apply {_x call _copy}}; _this};
// Plain str rounds a scalar for display. Scale by an exact binary power and
// retain the normalized mantissa, so nearby float values cannot share a proof
// merely because both display as (for example) 3.25 mL.
private _encode = {
    if (_this isEqualType []) exitWith {["A", _this apply {_x call _encode}]};
    if (_this isEqualType 0) exitWith {
        if (_this == 0) exitWith {["N", "0", "0"]};
        private _exponent = (floor (log (abs _this) / log 2)) max -126 min 127;
        ["N", (_this * (2 ^ (-_exponent))) toFixed 12, str _exponent]
    };
    if (_this isEqualType true) exitWith {["B", _this]};
    ["S", _this]
};
private _sorted = {private _rows = _this apply {str (_x call _encode)}; _rows sort true; _rows};
private _freshFacts = {
    private _meta = _this call _copy;
    if (count _meta == 4 && {(_meta select 0) isEqualTo "freshAgeV1"}) then {_meta set [2, 0];};
    _meta
};
private _inventoryFacts = {
    private _rows = (_this select 1) apply {
        private _row = _x call _copy;
        if ((_row select 0) == "prepared") then {
            private _body = (_row select 3) select 1;
            if (count _body > 11) then {_body set [11, (_body select 11) call _freshFacts];};
        };
        _row
    };
    _rows call _sorted
};
private _coolerFacts = {
    private _rows = (_this select 2) apply {
        [_x select 0, _x select 1, _x select 2, ((_x select 4) apply {_x select 0}) call _sorted]
    };
    [_this select 1, _rows call _sorted]
};
private _treeFacts = {
    _this params ["_cargo", "_inventory", "_coolers", "_children"];
    private _nested = [];
    {
        _nested pushBack [_x select 0, _x select 1, (_children select _forEachIndex) call _treeFacts];
    } forEach (_cargo select 3);
    [(_cargo select 0) call _sorted, (_cargo select 1) call _sorted,
        (_cargo select 2) call _sorted, _nested call _sorted,
        _inventory call _inventoryFacts, _coolers call _coolerFacts]
};
private _equipment = _metadata get "ACME_equipment_v1";
private _used = (_equipment select 2) apply {
    private _row = _x call _copy;
    if ((_row select 1) == "FreshBlood") then {_row set [8, (_row select 8) call _freshFacts];};
    _row
};
private _carrier = _equipment select 4;
private _carrierFacts = if (_carrier isEqualTo []) then {[]} else {
    [_carrier select 0, _carrier select 1, (_carrier select 2) call _treeFacts]
};
private _nestedFacts = (_equipment param [5, []]) apply {[_x select 0, _x select 1, (_x select 2) call _treeFacts]};
str [
    (_metadata get "ACME_coolers_v1") call _coolerFacts,
    (_metadata get "ACME_inventory_v1") call _inventoryFacts,
    [(_equipment select 1) call _sorted, _used call _sorted, (_equipment select 3) call _sorted, _carrierFacts, _nestedFacts call _sorted],
    (((_metadata get "ACME_blood_v1") select 1) apply {_x select 0}) call _sorted
]
