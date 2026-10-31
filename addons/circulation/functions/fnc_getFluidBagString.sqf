#include "..\script_component.hpp"
/*
 * Author: Blue
 * Get formatted fluid bag name from config string
 *
 * Arguments:
 * 0: Classname <STRING>
 *
 * Return Value:
 * Fluid Bag Name <STRING>
 *
 * Example:
 * ["salineIV_500"] call ACM_circulation_fnc_getFluidBagString;
 *
 * Public: No
 */

params ["_classname", ["_inline", [], [[]]], ["_expectedBloodType", -1, [0]], ["_knownID", -1, [0]]];

private _classnameSplit = _classname splitString "_";
private _freshBloodID = _knownID;

if ((_classnameSplit select 0) == "FreshBloodBag") then {
    _freshBloodID = parseNumber (_classnameSplit param [2, str _knownID]);
    _classname = format ["%1_%2", (_classnameSplit select 0), (_classnameSplit select 1)];
};

private _config = configFile >> QUOTE(ACE_ADDON(medical_treatment)) >> "IV";
private _fluidType = GET_STRING(_config >> _classname >> "type","Blood");
private _fluidAmount = GET_NUMBER(_config >> _classname >>"volume",1000);

switch (_fluidType) do {
    case "Blood": {
        _fluidType = format ["%1 %2 %3ml", LLSTRING(Blood), ([GET_NUMBER(_config >> _classname >> "bloodtype",0), 1] call FUNC(convertBloodType)), _fluidAmount];
    };
    case "FreshBlood": {
        private _freshEntry = [_freshBloodID, _inline, _expectedBloodType] call ACME_fnc_freshBloodResolve;
        if (_freshEntry isNotEqualTo []) then {
            _fluidType = format ["%1 %2ml %3", LLSTRING(FreshBlood), _fluidAmount, [(_freshEntry select 2), 1] call FUNC(convertBloodType)];
            if (_freshBloodID >= 0) then {_fluidType = _fluidType + format [" [ID:%1]", _freshBloodID];};
        } else {
            _fluidType = format ["%1 %2ml (donor information unavailable)", LLSTRING(FreshBlood), _fluidAmount];
        };
    };
    default {
        _fluidType = (format ["%1 %2ml", _fluidType, _fluidAmount]);
    };
};

_fluidType;
