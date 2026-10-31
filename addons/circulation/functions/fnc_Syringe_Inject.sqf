#include "..\script_component.hpp"
/*
 * Author: Blue
 * Handle administering syringe medication.
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 * 2: Body Part <STRING>
 * 3: Medication Classname <STRING>
 * 4: Syringe Size <NUMBER>
 * 5: IV? <BOOL>
 * 6: Return Syringe? <BOOL>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, cursorObject, "RightArm", "Morphine", 10, true, true] call ACM_circulation_fnc_Syringe_Inject;
 *
 * Public: No
 */

private _acmeBinding = "B13:Syringe_Inject";
params ["_medic", "_patient", "_bodyPart", "_classname", ["_size", 10], ["_iv", true], ["_returnSyringe", true],["_preparedReceipt",[],[[]]]];
private _routeClass = if (_iv) then {_classname + "_IV"} else {_classname};
if (isNull _medic || {!local _medic} || {!alive _medic} || {isNull _patient}) exitWith {};
if !([_routeClass, _iv, true] call ACME_fnc_medicationRouteAllowed) exitWith {
    ["This drug is not supported through the selected route. Syringe retained.", 3, _medic] call ace_common_fnc_displayTextStructured;
};
if (_medic distance _patient > 5 && {isNull objectParent _medic || {objectParent _medic != objectParent _patient}}) exitWith {};
if (getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _classname >> "concentration") <= 0) exitWith {};


if (_iv && !([_patient, _bodyPart, 0] call FUNC(hasIV)) && !([_patient, _bodyPart, 0] call FUNC(hasIO))) exitWith {
    [(format [LLSTRING(Syringe_PushFailed), toLower ([_bodyPart] call EFUNC(core,getBodyPartString))]), 2, _medic, 13] call ACEFUNC(common,displayTextStructured);
};
// B279: upgraded/tagged syringes use one transferable inventory token. Legacy
// native actions still administer through their original route and ACK contract.
// The transfer identity remains reserved until that receipt is accepted/refunded.
// A freshly drawn native magazine can be injected immediately, before an async
// registration ACK. Leave that raw direct-push path intact rather than upgrading
// its magazine during the very action which is about to consume it.
private _inventoryRows = _medic getVariable ["ACME_narcStore",[]];
private _nativeClass = format ["ACM_Syringe_%1_%2",_size,_classname];
private _capturedAmmo = -1;
if !(_preparedReceipt isEqualTo []) then {
    if ((_preparedReceipt param [0,""]) == _nativeClass) then {_capturedAmmo = _preparedReceipt param [1,-1,[0]];} else {_capturedAmmo = 0;};
};
if (_capturedAmmo == 0) exitWith {};
private _nativePresent = false;
{
    if (!isNull _x && {((magazinesAmmoCargo _x) findIf {(_x select 0) == _nativeClass && {_capturedAmmo < 0 || {(_x select 1) == _capturedAmmo}}}) >= 0}) exitWith {_nativePresent = true;};
} forEach [uniformContainer _medic,vestContainer _medic,backpackContainer _medic];
private _inventoryIdx = _inventoryRows findIf {
    (_x param [13,"",[""]]) == "inventoryB279" && {(_x param [0,""]) == _classname}
    && {(_x param [1,0]) == _size} && {(_x param [6,""]) == ""}
};
if (!_nativePresent && {_capturedAmmo < 0} && {_inventoryIdx >= 0}) exitWith {
    private _row = +(_inventoryRows select _inventoryIdx);
    private _request = [_medic,_row] call ACME_fnc_skInventoryReserve;
    if (_request == "") exitWith {};
    private _ml = _row param [2,0];
    private _conc = getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _classname >> "concentration");
    private _seconds = if (_iv) then {
        ((_ml * (missionNamespace getVariable ["ACME_syringe_pushSecPerMl",1.0]))
            max (missionNamespace getVariable ["ACME_syringe_pushMinSec",1.5]))
            min (missionNamespace getVariable ["ACME_syringe_pushMaxSec",10])
    } else {missionNamespace getVariable ["ACME_syringe_imDeliverySec",3]};
    private _emptyItems = if (_returnSyringe) then {[format ["ACM_Syringe_%1",_size]]} else {[]};
    private _label = localize (format ["STR_ACM_Circulation_Medication_%1",_classname]);
    [_medic,_request,ACME_fnc_skInventoryInjectClaim,[_medic,_patient,_bodyPart,[[_routeClass,_conc*_ml,_iv,_label,_seconds]],-2,_row,[],_row,_request,_emptyItems]] call ACME_fnc_inventoryLedgerClaim;
};

private _itemClassname = "";
private _administrationString = LLSTRING(Intramuscular_Short);
private _actionString = LLSTRING(Syringe_Injected);
private _medicationName = localize (format ["STR_ACM_Circulation_Medication_%1", _classname]);
private _medicationClassname = _classname;

if (_classname in ["Phentolamine", "Hyaluronidase"]) then {_administrationString = "local infiltration";};
if (_iv) then {
    _medicationClassname = format ["%1_IV", _classname];
    _administrationString = LLSTRING(Intravenous_Short);
    _actionString = LLSTRING(Syringe_Pushed);
};

_itemClassname = format ["ACM_Syringe_%1_%2", _size, _classname];

private _dose = 0;

{
    if (_dose > 0) exitWith {};
    private _targetItems = [];
    _targetItems append ((magazinesAmmoCargo _x) select {(_x select 0) == _itemClassname && {_capturedAmmo < 0 || {(_x select 1) == _capturedAmmo}}});

    if (count _targetItems < 1) then {
        continue;
    };

    _targetItems sort false;

    private _count = ((_targetItems select 0) select 1);
    _dose = _count;

    _x addMagazineAmmoCargo [_itemClassname, -1, _count];
} forEach [uniformContainer _medic, vestContainer _medic, backpackContainer _medic];

if (_dose < 1) exitWith {};

private _medicationConcentration = getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _classname >> "concentration");

private _stringDose = (_dose / 100) * _medicationConcentration;

private _microDose = _classname in ["Fentanyl", "EpinephrineCardiac", "Norepinephrine"];
private _doseMeasurement = if (_classname == "Hyaluronidase") then {"U"} else {["mg", "mcg"] select _microDose};

if (_stringDose < 1 && !_microDose) then {
    _stringDose = round (_stringDose * 10);
    _stringDose = (_stringDose / 10);
} else {
    if (_microDose) then {
        _stringDose = round(_stringDose * 1000);
    } else {
        _stringDose = round(_stringDose);
        if (_stringDose >= 1000 && {_doseMeasurement == "mg"}) then {
            _stringDose = _stringDose / 1000;
            _doseMeasurement = "g";
        };
    };
};

// B14: success log and empty syringe follow owner acceptance, not request submission.
private _drawn = +(_medic getVariable ["ACME_narcStore",[]]);
private _si = _drawn findIf {(_x param [0,""]) == _classname && {(_x param [1,0]) == _size}
    && {round ((_x param [2,0]) * 100) == _dose} && {(_x param [4,0]) == 0} && {(_x param [5,[]]) isEqualTo []}
    && {(_x param [13,"",[""]]) != "inventoryB279"}};
private _refundRows = [];
if (_si >= 0) then {_refundRows pushBack (_drawn deleteAt _si);[_medic,_drawn] call ACME_fnc_narcStoreCommit;};
private _empty = if (_returnSyringe) then {[format ["ACM_Syringe_%1",_size]]} else {[]};

private _concentrationDose = _medicationConcentration * (_dose / 100);

private _pushMl = (_dose / 100) max 0.01;
private _pushSec = if (_iv) then {
    ((_pushMl * (missionNamespace getVariable ["ACME_syringe_pushSecPerMl",1.0]))
        max (missionNamespace getVariable ["ACME_syringe_pushMinSec",1.5]))
        min (missionNamespace getVariable ["ACME_syringe_pushMaxSec",10])
} else {missionNamespace getVariable ["ACME_syringe_imDeliverySec",3]};
[_medic, _patient, _bodyPart, [[_medicationClassname, _concentrationDose, _iv, _medicationName, _pushSec]], "administer", -2, [[[_itemClassname,_dose]],_refundRows,_empty]] call ACME_fnc_medicationRequest;

if (alive _patient && {!_iv} && {([_patient, "Lidocaine", false, GET_BODYPART_INDEX(_bodyPart)] call ACEFUNC(medical_status,getMedicationCount)) < 0.5}) then {
    [_patient, (linearConversion [1, 10, (_dose / 100), 0.1, 0.4])] call ACEFUNC(medical,adjustPainLevel);
    [_patient, "hit"] call ACEFUNC(medical_feedback,playInjuredSound);
};

[QEGVAR(core,openMedicalMenu), _patient] call CBA_fnc_localEvent;
