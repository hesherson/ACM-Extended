#include "..\script_component.hpp"
/*
 * Author: ACM Extended Fork
 * Airway-owned mutation endpoint for native ACM airway state that Extended systems need to adjust.
 *
 * The caller supplies a list of [field,value] pairs. Only the native airway fields below are accepted; unknown
 * names are ignored. This keeps ACM airway storage inside its owning addon while allowing Extended procedures and
 * training systems to request an atomic-looking patch without writing ACM variables directly.
 *
 * Arguments:
 * 0: Patient <OBJECT>
 * 1: Changes <ARRAY> of [field,value]
 *    Supported fields: collapse, blood, vomit, vomitCount, vomitGrace, vomitPFH, recovery, headTilt
 * 2: Public <BOOL> (default true)
 *
 * Return Value:
 * Number of applied fields <NUMBER>
 *
 * Public: Yes
 */
params [
    ["_patient", objNull, [objNull]],
    ["_changes", [], [[]]],
    ["_public", true, [true]]
];
if (isNull _patient) exitWith {0};

private _applied = 0;
{
    if (_x isEqualType [] && {count _x >= 2}) then {
        _x params ["_field", "_value"];
        switch (_field) do {
            case "collapse": {
                _patient setVariable [QGVAR(AirwayCollapse_State), _value, _public];
                _applied = _applied + 1;
            };
            case "blood": {
                // Clearing/restarting this native compartment retires its partial suction ledger.
                if (_value isEqualType 0 && {_value <= 0 || {(_patient getVariable [QGVAR(AirwayObstructionBlood_State), 0]) <= 0}}) then {
                    _patient setVariable ["ACME_laryngo_bloodRemaining", [], _public];
                    // Retire only the shared blood pool; an overlying vomit pool
                    // has its own independently suctioned remaining volume.
                    private _pool = _patient getVariable ["ACME_laryngo_pool", []];
                    if (_pool isEqualType [] && {count _pool >= 1}) then {
                        private _stamp = _pool select 0;
                        if (_stamp isEqualType [] && {count _stamp >= 2}
                            && {(_stamp select 0) isEqualType 0} && {(_stamp select 1) isEqualType 0}
                            && {(_stamp select 0) <= 0} && {(_stamp select 1) > 0}) then {
                            _patient setVariable ["ACME_laryngo_pool", [], _public];
                        };
                    };
                };
                _patient setVariable [QGVAR(AirwayObstructionBlood_State), _value, _public];
                _applied = _applied + 1;
            };
            case "vomit": {
                _patient setVariable [QGVAR(AirwayObstructionVomit_State), _value, _public];
                _applied = _applied + 1;
            };
            case "vomitCount": {
                _patient setVariable [QGVAR(AirwayObstructionVomit_Count), _value, _public];
                _applied = _applied + 1;
            };
            case "vomitGrace": {
                _patient setVariable [QGVAR(AirwayObstructionVomit_GracePeriod), _value, _public];
                _applied = _applied + 1;
            };
            case "vomitPFH": {
                _patient setVariable [QGVAR(AirwayObstructionVomit_PFH), _value, _public];
                _applied = _applied + 1;
            };
            case "recovery": {
                _patient setVariable [QGVAR(RecoveryPosition_State), _value, _public];
                _applied = _applied + 1;
            };
            case "headTilt": {
                _patient setVariable [QGVAR(HeadTilt_State), _value, _public];
                _applied = _applied + 1;
            };
        };
    };
} forEach _changes;

_applied
