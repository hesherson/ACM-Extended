// Stable B180: one rare clot-failure event partially reopens ONE unsecured clot.
// Physical dressings/wraps/stitches are never touched here.
params [
    ["_unit", objNull, [objNull]],
    ["_fraction", 0.15, [0]],
    ["_bodyPartFilter", "", [""]],
    ["_woundIDFilter", -1, [0]]
];

if (isNull _unit || {!alive _unit} || {!local _unit}) exitWith {0};
_fraction = (_fraction max 0.05) min 0.25;

private _open = _unit getVariable ["ace_medical_openWounds", createHashMap];
private _clotted = _unit getVariable ["ACM_damage_ClottedWounds", createHashMap];
if !(_clotted isEqualType createHashMap) exitWith {0};

private _candidates = [];
{
    private _part = _x;
    if (_bodyPartFilter != "" && {_part != _bodyPartFilter}) then {continue};

    private _rows = _clotted getOrDefault [_part, []];
    {
        private _id = _x param [0, -1];
        private _amt = _x param [1, 0];
        if (_amt > 0.001 && {_woundIDFilter < 0 || {_id == _woundIDFilter}}) then {
            // Selection is weighted only to choose WHICH single clot fails. The amount reopened below is capped
            // to a fraction of one wound, never a fraction of the entire aggregate row.
            _candidates pushBack [_part, _forEachIndex, _id, (_amt min 1) max 0.01];
        };
    } forEach _rows;
} forEach (keys _clotted);

if (_candidates isEqualTo []) exitWith {0};

private _total = 0;
{_total = _total + (_x select 3);} forEach _candidates;
private _roll = random (_total max 0.001);
private _pick = _candidates select 0;
{
    _roll = _roll - (_x select 3);
    if (_roll <= 0) exitWith {_pick = _x;};
} forEach _candidates;

_pick params ["_part", "_idx", "_id"];
private _cRows = +(_clotted getOrDefault [_part, []]);
if (_idx < 0 || {_idx >= count _cRows}) exitWith {0};

private _cw = +(_cRows select _idx);
private _camt = _cw param [1, 0];
if (_camt <= 0.001) exitWith {0};

// One event creates only a partial wound. Even a row representing many clots can lose at most this one fraction.
private _move = _fraction min _camt;
private _remaining = (_camt - _move) max 0;
if (_remaining <= 0.001) then {
    _cRows deleteAt _idx;
} else {
    _cw set [1, _remaining];
    _cRows set [_idx, _cw];
};
_clotted set [_part, _cRows];

private _oRows = +(_open getOrDefault [_part, []]);
private _oi = _oRows findIf {(_x param [0, -1]) == _id};
if (_oi >= 0) then {
    private _ow = +(_oRows select _oi);
    _ow set [1, (_ow param [1, 0]) + _move];
    _oRows set [_oi, _ow];
} else {
    private _new = +_cw;
    if (_new isEqualTo []) then {_new = [_id, _move, 0, 0];};
    _new set [0, _id];
    _new set [1, _move];
    _oRows pushBack _new;
};
_open set [_part, _oRows];

[_unit, [["clottedWounds", _clotted]], true] call ACM_damage_fnc_setWoundState;
[_unit, [["openWounds", _open, true]]] call ACM_core_fnc_setAceMedicalState;
[_unit] call ace_medical_status_fnc_updateWoundBloodLoss;

private _partIndex = ["head","body","leftarm","rightarm","leftleg","rightleg"] find _part;
switch (_partIndex) do {
    case 0: {[_unit, true, false, false, false] call ace_medical_engine_fnc_updateBodyPartVisuals;};
    case 1: {[_unit, false, true, false, false] call ace_medical_engine_fnc_updateBodyPartVisuals;};
    case 2;
    case 3: {[_unit, false, false, true, false] call ace_medical_engine_fnc_updateBodyPartVisuals;};
    case 4;
    case 5: {
        [_unit, false, false, false, true] call ace_medical_engine_fnc_updateBodyPartVisuals;
        [_unit] call ace_medical_engine_fnc_updateDamageEffects;
    };
    default {};
};

if (_unit isEqualTo ACE_player) then {
    ["A clot partially reopened one wound.", 2] call ace_common_fnc_displayTextStructured;
};

1
