#include "..\script_component.hpp"
/*
 * Author: Glowbal, mharis001
 * Local callback for administering an IV bag to a patient.
 *
 * Arguments:
 * 0: Patient <OBJECT>
 * 1: Body Part <STRING>
 * 2: Treatment <STRING>
 * 3: Access Type <NUMBER>
 * 4: Is IV? <BOOL>
 * 5: Access Site <NUMBER>
 * 6: Is Fresh Blood? <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, "RightArm", "BloodIV", 1, true, 0, false] call ace_medical_treatment_fnc_ivBagLocal
 *
 * Public: No
 */

params ["_patient", "_bodyPart", "_classname", "_accessType", ["_iv", true], "_accessSite", ["_freshBlood", false], ["_deferPremixed", false], ["_freshBloodEntryNet", []]];

if (!local _patient) exitWith {["ace_medical_treatment_ivBagLocal", _this, _patient] call CBA_fnc_targetEvent;};
private _partIndex = ALL_BODY_PARTS find toLowerANSI _bodyPart;

// Add IV bag to patient's ivBags array
private _IVBags = _patient getVariable [QEGVAR(circulation,IV_Bags), createHashMap];
private _IVBagsBodyPart = _IVBags getOrDefault [_bodyPart, []];

private _donorBloodType = -1;
private _isFBTK = false;

switch (true) do {
    case (_freshBlood): {
        (_classname splitString "_") params ["", "_volume", "_id"];
        private _idNum = parseNumber _id;
        private _freshEntry = [_idNum] call EFUNC(circulation,getFreshBloodEntry);

        // MP/JIP robustness: the target event can beat the public registry update to the patient owner. The medic
        // includes the exact donor entry with the treatment event; use it immediately and repair the local/public
        // registry so later metabolism, labels and locality migrations all see the same donor metadata.
        if !(_freshEntry isEqualType [] && {count _freshEntry >= 3}) then {
            if (_freshBloodEntryNet isEqualType [] && {count _freshBloodEntryNet >= 3}) then {
                _freshEntry = +_freshBloodEntryNet;
                private _freshList = missionNamespace getVariable [QEGVAR(circulation,FreshBloodList), createHashMap];
                _freshList set [_idNum, _freshEntry];
                missionNamespace setVariable [QEGVAR(circulation,FreshBloodList), _freshList, true];
            };
        };

        private _bloodType = _freshEntry param [2, -1];
        _donorBloodType = _bloodType;

        _IVBagsBodyPart pushBack ["FreshBlood", (parseNumber _volume), _accessType, _accessSite, _iv, _bloodType, (parseNumber _volume), _idNum];
    };
    case (_classname in FBTK_ARRAY_DATA): {
        _isFBTK = true;
        private _volume = parseNumber ((_classname splitString "_") select 1);

        _IVBagsBodyPart pushBack ["FBTK", 0, _accessType, _accessSite, _iv, -1, _volume];
    };
    default {
        // Get attributes for the used IV
        private _defaultConfig = configFile >> QUOTE(ACE_ADDON(medical_treatment)) >> "IV";
        private _ivConfig = _defaultConfig >> _classname;

        private _volume = GET_NUMBER(_ivConfig >> "volume",getNumber (_defaultConfig >> "volume"));
        private _type = GET_STRING(_ivConfig >> "type",getText (_defaultConfig >> "type"));
        private _bloodType = GET_NUMBER(_ivConfig >> "bloodtype",-1);

        _donorBloodType = _bloodType;

        _IVBagsBodyPart pushBack [_type, _volume, _accessType, _accessSite, _iv, _bloodType, _volume]; // ["Saline", 1000, ACM_IV_16G_M, 0, false, -1, 1000]
    };
};

// NA3: assign identity before publishing this new bag, preserving all native tuple fields.
private _newBag = _IVBagsBodyPart select ((count _IVBagsBodyPart) - 1);
if (count _newBag < 8) then {_newBag set [7, -1];};
private _sequence = (_patient getVariable ["ACME_bagSequence", 0]) + 1;
_patient setVariable ["ACME_bagSequence", _sequence, true];
_newBag set [8, format ["%1:%2:%3:%4", netId _patient, [_patient] call ACME_fnc_clinicalEpoch, clientOwner, _sequence]];
_IVBags set [_bodyPart, _IVBagsBodyPart];

[_patient, _IVBags, true] call EFUNC(circulation,setIVBagsState);
_patient setVariable [QEGVAR(circulation,IV_Bags_Active), true, true];

[_patient, _bodyPart] call EFUNC(circulation,updateActiveFluidBags);

if (GET_BLOODTYPE(_patient) == -1) then {
    [_patient] call EFUNC(circulation,generateBloodType);
};

if (!_isFBTK && {_donorBloodType > -1 && !([GET_BLOODTYPE(_patient), _donorBloodType] call EFUNC(circulation,isBloodTypeCompatible))}) then {
    [QEGVAR(circulation,handleHemolyticReaction), [_patient], _patient] call CBA_fnc_targetEvent;
};
if (!_deferPremixed) then {[_patient] call ACME_fnc_syncPremixedBags;};

_newBag select 8
