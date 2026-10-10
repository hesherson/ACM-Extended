#include "..\script_component.hpp"
/*
 * Author: ACM Extended Fork
 * Circulation-owned mutation endpoint for native ACM circulation runtime state touched by Extended systems.
 *
 * Public writes retain owner-local publication deduplication for scalar, identity and structured values. Arrays and
 * HashMaps are cached by serialized value so mutable containers cannot bypass suppression. IV_Bags and
 * CardiacArrest_TargetRhythm deliberately remain
 * outside this generic endpoint because they have dedicated native owner APIs.
 *
 * Arguments:
 * 0: Object carrying the circulation state <OBJECT>
 * 1: Changes <ARRAY> of [field,value]
 * 2: Public <BOOL> (default true)
 *
 * Return Value:
 * Number of accepted publications <NUMBER>
 *
 * Public: Yes
 */
params [
    ["_unit", objNull, [objNull]],
    ["_changes", [], [[]]],
    ["_public", true, [true]]
];
if (isNull _unit) exitWith {0};

private _ownerKey = QGVAR(ForkStatePublishOwner);
private _cacheKey = QGVAR(ForkStatePublished);
private _cache = _unit getVariable [_cacheKey, createHashMap];
if (_public && {local _unit}) then {
    private _ownerStamp = [owner _unit, local _unit];
    if !((_unit getVariable [_ownerKey, []]) isEqualTo _ownerStamp) then {
        _cache = createHashMap;
        _unit setVariable [_cacheKey, _cache, false];
        _unit setVariable [_ownerKey, _ownerStamp, false];
    };
};

private _publish = {
    params ["_var", "_value"];
    private _k = toLowerANSI _var;
    private _type = typeName _value;
    private _fingerprint = if (_type in ["ARRAY", "HASHMAP"]) then {
        [_type, str _value]
    } else {
        [_type, _value]
    };

    if (_public && {local _unit}) then {
        private _old = _unit getVariable _var;
        private _published = _cache get _k;
        private _localSame = false;
        if (!isNil "_old") then {
            _localSame = if (_type in ["ARRAY", "HASHMAP"]) then {
                [_type, str _old] isEqualTo _fingerprint
            } else {
                _old isEqualTo _value
            };
        };
        if (_localSame && {!isNil "_published"} && {_published isEqualTo _fingerprint}) exitWith {false};
        _cache set [_k, _fingerprint];
    } else {
        _cache deleteAt _k;
    };
    _unit setVariable [_var, _value, _public];
    true
};

private _applied = 0;
{
    if (_x isEqualType [] && {count _x >= 2}) then {
        _x params ["_field", "_value"];
        private _accepted = false;
        switch (_field) do {
            case "cardiacArrestPFH": { _accepted = [QGVAR(CardiacArrest_PFH), _value] call _publish; };
            case "reversibleCardiacArrestPFH": { _accepted = [QGVAR(ReversibleCardiacArrest_PFH), _value] call _publish; };
            case "cprProvider": { _accepted = [QACEGVAR(medical,CPR_provider), _value] call _publish; };
            case "cprMedic": { _accepted = [QGVAR(CPR_Medic), _value] call _publish; };
            case "cprSession": { _accepted = [QGVAR(CPR_session), _value] call _publish; };
            case "aedUpdateStep": { _accepted = [QGVAR(AED_UpdateStep), _value] call _publish; };
            case "aedPadsLastBeep": { _accepted = [QGVAR(AED_Pads_LastBeep), _value] call _publish; };
            case "aedPadsLastSync": { _accepted = [QGVAR(AED_Pads_LastSync), _value] call _publish; };
            case "aedPadsDisplay": { _accepted = [QGVAR(AED_Pads_Display), _value] call _publish; };
            case "ivBagsActive": { _accepted = [QGVAR(IV_Bags_Active), _value] call _publish; };
            case "fluidBagsFlowIV": { _accepted = [QGVAR(FluidBagsFlow_IV), _value] call _publish; };
            case "fluidBagsFlowIO": { _accepted = [QGVAR(FluidBagsFlow_IO), _value] call _publish; };
            case "ivPlacement": { _accepted = [QGVAR(IV_Placement), _value] call _publish; };
            case "cardiacRhythmState": { _accepted = [QGVAR(Cardiac_RhythmState), _value] call _publish; };
            case "bloodVolume": { _accepted = [QGVAR(Blood_Volume), _value] call _publish; };
            case "overloadVolume": { _accepted = [QGVAR(Overload_Volume), _value] call _publish; };
            case "salineVolume": { _accepted = [QGVAR(Saline_Volume), _value] call _publish; };
            case "aedEkgRhythm": { _accepted = [QGVAR(AED_EKGRhythm), _value] call _publish; };
            case "aedCharged": { _accepted = [QGVAR(AED_Charged), _value] call _publish; };
            case "aedInUse": { _accepted = [QGVAR(AED_InUse), _value] call _publish; };
            case "aedMedicInUse": { _accepted = [QGVAR(AED_Medic_InUse), _value] call _publish; };
            case "aedLastShock": { _accepted = [QGVAR(AED_LastShock), _value] call _publish; };
            case "aedShockTotal": { _accepted = [QGVAR(AED_ShockTotal), _value] call _publish; };
            case "aedAnalyzeBusy": { _accepted = [QGVAR(AED_Analyze_Busy), _value] call _publish; };
            case "aedAnalyzeRhythmState": { _accepted = [QGVAR(AED_AnalyzeRhythm_State), _value] call _publish; };
            case "cardiacArrestResistChecked": { _accepted = [QGVAR(CardiacArrest_ResistChecked), _value] call _publish; };
            case "cardiacArrestShockResistant": { _accepted = [QGVAR(CardiacArrest_ShockResistant), _value] call _publish; };
            case "aedNibpDisplay": { _accepted = [QGVAR(AED_NIBP_Display), _value] call _publish; };
            case "bloodType": { _accepted = [QGVAR(BloodType), _value] call _publish; };
            case "roscTime": { _accepted = [QGVAR(ROSC_Time), _value] call _publish; };
        };
        if (_accepted) then {_applied = _applied + 1;};
    };
} forEach _changes;
_applied
