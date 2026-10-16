/*
 * Phase 57: authoritative writer for ACME_rhythm_active.
 *
 * The public/deduplicate switches preserve the two pre-existing publication contracts:
 * - rhythmSet/rhythmRelease used ACME_fnc_setVarNet scalar deduplication;
 * - Megacode/lifecycle setup used direct setVariable publication.
 */
params [
    ["_unit", objNull, [objNull]],
    ["_code", 0, [0]],
    ["_public", true, [true]],
    ["_deduplicate", true, [true]]
];
if (isNull _unit) exitWith {_code};
if (_public && {_deduplicate}) then {
    [_unit, "ACME_rhythm_active", _code] call ACME_fnc_setVarNet;
} else {
    _unit setVariable ["ACME_rhythm_active", _code, _public];
};
// B245: custom-rhythm symptoms run only for explicitly active local patients.
// The registry is machine-local and rebuilt by ownerRegister after locality transfer.
if (local _unit) then {
    private _active = missionNamespace getVariable ["ACME_rhythm_activePatients", []];
    if (_code >= 100 && {alive _unit}) then {_active pushBackUnique _unit;} else {_active = _active - [_unit];};
    missionNamespace setVariable ["ACME_rhythm_activePatients", _active];
};
_code
