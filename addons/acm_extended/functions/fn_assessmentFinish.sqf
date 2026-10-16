/* Native completion callbacks are class/patient checked before releasing the assessment episode. */
params [["_args", [], [[]]]];
_args params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_part", "", [""]], ["_class", "", [""]]];
if (isNull _medic || {!local _medic}) exitWith {};
private _record = _medic getVariable ["ACME_assessment", []];
if (_record isEqualTo []) exitWith {
    private _seated = _medic getVariable ["ACME_assessmentSeated", []];
    if (_seated isEqualTo [] || {(_args param [7, -2]) != -1}
        || {(_args param [8, -1]) != (_seated select 0)}) exitWith {};
    private _owned = _seated select 1;
    if ((_owned param [1, objNull]) isNotEqualTo _patient
        || {(_owned param [2, ""]) != _part}
        || {(toLowerANSI (_owned param [3, ""])) != toLowerANSI _class}) exitWith {};
    _medic setVariable ["ACME_assessmentSeated", [], false];
    if (!isNull objectParent _medic && {objectParent _medic isEqualTo (_seated select 2)}
        && {objectParent _patient isEqualTo (_seated select 2)}) then {
        [_medic, _patient, _seated select 0] call ACME_fnc_assessmentReopen;
    };
};
if (_record isEqualTo [] || {(_args param [7, -1]) != (_record select 0)}) exitWith {};
private _owned = _record select 1;
if ((_owned param [1, objNull]) isNotEqualTo _patient
    || {(_owned param [2, ""]) != _part}
    || {(toLowerANSI (_owned param [3, ""])) != toLowerANSI _class}) exitWith {};
[_medic, _record select 0, true] call ACME_fnc_assessmentStop;
