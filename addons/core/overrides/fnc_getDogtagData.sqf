#include "..\script_component.hpp"
/*
 * Author: esteldunedain
 * Gets unit's dog tag data.
 *
 * Arguments:
 * 0: Target <OBJECT>
 *
 * Return Value:
 * Dog tag Data <ARRAY>
 * 0: Name <STRING>
 * 1: SSN <STRING>
 * 2: Blood Type <STRING>
 * 3: Weight <STRING>
 *
 * Example:
 * _dogtagData = [player] call ace_dogtags_fnc_getDogtagData
 *
 * Public: No
 */

params ["_target"];

// Reuse only structurally valid cached identity data. Corrupt/stale caches are regenerated natively.
private _dogtagData = _target getVariable QACEGVAR(dogtags,dogtagData);
private _cacheValid = !isNil "_dogtagData"
    && {_dogtagData isEqualType []}
    && {count _dogtagData >= 3}
    && {(_dogtagData select [0, 3]) isEqualTypeAll ""};

if (_cacheValid) exitWith {_dogtagData};
if (!isNil "_dogtagData") then {
    _target setVariable [QACEGVAR(dogtags,dogtagData), nil];
};

// Create dog tag data once for the unit: nickname, code (eg. 135-13-900) and blood type
private _targetName = [_target, false, true] call ACEFUNC(common,getName);
private _bloodType = GET_BLOODTYPE(_target);
private _weight = "";

if (_bloodType == -1) then {
    _bloodType = [_target] call EFUNC(circulation,generateBloodType);
};

if (GVAR(Dogtag_ShowWeight)) then {
    _weight = format ["%1 KG", round GET_BODYWEIGHT(_target)];
};

private _dogtagData = [
    _targetName,
    _targetName call ACEFUNC(dogtags,ssn),
    ([_bloodType, 1] call EFUNC(circulation,convertBloodType)),
    _weight
];

// Store it
_target setVariable [QACEGVAR(dogtags,dogtagData), _dogtagData, true];

_dogtagData
