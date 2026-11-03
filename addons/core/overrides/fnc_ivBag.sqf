#include "..\script_component.hpp"
/*
 * Author: Glowbal, mharis001
 * Administers an IV bag treatment to the patient.
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 * 2: Body Part <STRING>
 * 3: Treatment <STRING>
 * 4: Item User (not used) <OBJECT>
 * 5: Used Item <STRING>
 * 6: Is IV? <BOOL>
 * 7: Access Site <NUMBER>
 * 8: Optional portable blood-use clock <ARRAY>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, cursorObject, "RightArm", "BloodIV", objNull, "ACE_bloodIV"] call ace_medical_treatment_fnc_ivBag
 *
 * Public: No
 */

params ["_medic", "_patient", "_bodyPart", "_classname", ["_itemUser",objNull], "_usedItem", ["_iv", true], ["_accessSite", -1],["_useClock",[]]];
if (_useClock isEqualTo []) then {
    if (isNull _itemUser) then {_itemUser=_medic;};
    private _row=[["native-iv",_usedItem,_classname,"","","","",false,""],_itemUser,_usedItem] call ACME_fnc_bloodUseSeed;
    _useClock=[_row,"prepared","get"] call ACME_fnc_bloodUseRow;
};

private _isFreshBlood = false;
private _freshBloodEntry = [];

private _classParts = _classname splitString "_";
if ((_classParts param [0, ""]) == "FreshBloodBag") then {
    _isFreshBlood = true;
    private _freshBloodID = parseNumber (_classParts param [2, "-1"]);
    _freshBloodEntry = [_freshBloodID] call EFUNC(circulation,getFreshBloodEntry);
    _usedItem = format ["%1_%2_%3", (_usedItem splitString "_" select 0), (_usedItem splitString "_" select 1), (_usedItem splitString "_" select 2)];
};

[_patient, _usedItem] call ACEFUNC(medical_treatment,addToTriageCard);

if (_classname in FBTK_ARRAY_DATA) then {
    private _amount = (_classname splitString "_") select 1;
    [_patient, "activity", "%1 began collecting blood (%2ml) from %3", [[_medic, false, true] call ACEFUNC(common,getName), _amount, ([_bodyPart] call FUNC(getBodyPartString))]] call ACEFUNC(medical_treatment,addToLog);
} else {
    [_patient, "activity", LELSTRING(circulation,GUI_BeganTransfusing), [[_medic, false, true] call ACEFUNC(common,getName), ([_classname] call EFUNC(circulation,getFluidBagString)), ([_bodyPart] call FUNC(getBodyPartString))]] call ACEFUNC(medical_treatment,addToLog);
};

private _partIndex = ALL_BODY_PARTS find toLowerANSI _bodyPart;

private _accessType = [_patient, _iv, _partIndex, _accessSite] call EFUNC(circulation,getAccessType);

// Carry the donor metadata with the owner-targeted event. missionNamespace replication and CBA target events are
// separate network paths; without this, the patient owner could receive the bag before the fresh-blood registry.
[QACEGVAR(medical_treatment,ivBagLocal), [_patient, _bodyPart, _classname, _accessType, _iv, _accessSite, _isFreshBlood, false, _freshBloodEntry,[],_useClock], _patient] call CBA_fnc_targetEvent;
