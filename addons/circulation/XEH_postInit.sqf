#include "script_component.hpp"

call FUNC(registerCPRRuntime);

[QGVAR(handleCardiacArrest), LINKFUNC(handleCardiacArrest)] call CBA_fnc_addEventHandler;
[QGVAR(handleReversibleCardiacArrest), LINKFUNC(handleReversibleCardiacArrest)] call CBA_fnc_addEventHandler;

[QGVAR(attemptROSC), LINKFUNC(attemptROSC)] call CBA_fnc_addEventHandler;

[QACEGVAR(medical,CPRSucceeded), {
    params ["_patient"];

    _patient setVariable [QGVAR(Cardiac_RhythmState), ACM_Rhythm_Sinus, true];

    if (([_patient, "Adenosine_IV", false] call ACEFUNC(medical_status,getMedicationCount) > 0.1)) exitWith {};

    _patient setVariable [QGVAR(ROSC_Time), CBA_missionTime, true];
    if ([_patient] call FUNC(recentAEDShock)) then {
        _patient setVariable [QGVAR(AED_LastShock), 0, true];
    };
}] call CBA_fnc_addEventHandler;

[QGVAR(handleCPR), LINKFUNC(handleCPR)] call CBA_fnc_addEventHandler;

[QGVAR(checkCapillaryRefillLocal), LINKFUNC(checkCapillaryRefillLocal)] call CBA_fnc_addEventHandler;

[QGVAR(setIVLocal), LINKFUNC(setIVLocal)] call CBA_fnc_addEventHandler;
[QGVAR(handleIVComplication), LINKFUNC(handleIVComplication)] call CBA_fnc_addEventHandler;
[QGVAR(setAEDLocal), LINKFUNC(setAEDLocal)] call CBA_fnc_addEventHandler;
[QGVAR(setPressureCuffLocal), LINKFUNC(setPressureCuffLocal)] call CBA_fnc_addEventHandler;

[QGVAR(handleMed_AdenosineLocal), LINKFUNC(handleMed_AdenosineLocal)] call CBA_fnc_addEventHandler;
[QGVAR(handleMed_AmmoniaInhalantLocal), LINKFUNC(handleMed_AmmoniaInhalantLocal)] call CBA_fnc_addEventHandler;
[QGVAR(handleMed_AtropineLocal), LINKFUNC(handleMed_AtropineLocal)] call CBA_fnc_addEventHandler;
[QGVAR(handleMed_CalciumChlorideLocal), LINKFUNC(handleMed_CalciumChlorideLocal)] call CBA_fnc_addEventHandler;
[QGVAR(handleMed_DimercaprolLocal), LINKFUNC(handleMed_DimercaprolLocal)] call CBA_fnc_addEventHandler;
[QGVAR(handleMed_NaloxoneLocal), LINKFUNC(handleMed_NaloxoneLocal)] call CBA_fnc_addEventHandler;
[QGVAR(handleMed_TXALocal), LINKFUNC(handleMed_TXALocal)] call CBA_fnc_addEventHandler;
[QGVAR(handleMed_KetamineLocal), LINKFUNC(handleAnestheticEffects)] call CBA_fnc_addEventHandler;
[QGVAR(handleMed_LidocaineLocal), LINKFUNC(handleAnestheticEffects)] call CBA_fnc_addEventHandler;

[QGVAR(setLozengeLocal), LINKFUNC(setLozengeLocal)] call CBA_fnc_addEventHandler;

[QGVAR(handleHemolyticReaction), LINKFUNC(handleHemolyticReaction)] call CBA_fnc_addEventHandler;

[QGVAR(handleMedicationEffects), {
    params ["_patient", "_bodyPart", "_classname", ["_dose", 1]];

    // Handle special medication effects
    if (_classname in ["AmmoniaInhalant", "Naloxone", "TXA_IV", "Ketamine", "Ketamine_IV", "Lidocaine", "CalciumChloride_IV", "Adenosine_IV", "Atropine", "Atropine_IV", "Dimercaprol"]) then {
        private _shortClassname = (_classname splitString "_") select 0;
        [(format ["ACM_circulation_handleMed_%1Local", toLower _shortClassname]), [_patient, _bodyPart, _classname, _dose], _patient] call CBA_fnc_targetEvent;
    };
}] call CBA_fnc_addEventHandler;

call FUNC(generateBloodTypeList);

["isNotPerformingCPR", {!((_this select 0) getVariable [QGVAR(isPerformingCPR), false])}] call ACEFUNC(common,addCanInteractWithCondition);

if (GVAR(Hardcore_PostCardiacArrest)) then {
    [QGVAR(Hardcore_PostCardiacArrest), {
        ([1, 1.4] select (_this getVariable [QGVAR(Hardcore_PostCardiacArrest), false]));
    }] call ACEFUNC(advanced_fatigue,addDutyFactor);
};

GVAR(Fluids_Array) = FLUIDS_ARRAY;
GVAR(Fluids_Array_Data) = FLUIDS_ARRAY_DATA;

// Blood Bags
{
    private _bloodType = _x;

    {
        private _entry = format ["BloodBag_%1_%2", _bloodType, _x];
        GVAR(Fluids_Array_Data) pushBack _entry;
        GVAR(Fluids_Array) pushBack format ["ACM_%1", _entry];
    } forEach [1000,500,250];
} forEach ["O","ON","A","AN","B","BN","AB","ABN"];

GVAR(Fluids_Array) append FBTK_ARRAY;
GVAR(Fluids_Array_Data) append FBTK_ARRAY_DATA;

["ACE_bloodIV", "ACM_BloodBag_ON_1000"] call ACEFUNC(common,registerItemReplacement);
["ACE_bloodIV_500", "ACM_BloodBag_ON_500"] call ACEFUNC(common,registerItemReplacement);
["ACE_bloodIV_250", "ACM_BloodBag_ON_250"] call ACEFUNC(common,registerItemReplacement);

// Syringes

ACM_SYRINGES_10 = ['ACM_Syringe_10'];
ACM_SYRINGES_5 = ['ACM_Syringe_5'];
ACM_SYRINGES_3 = ['ACM_Syringe_3'];
ACM_SYRINGES_1 = ['ACM_Syringe_1'];

{ // Filled Syringes
    private _size = getNumber (_x >> "count");

    private _targetArray = switch (_size) do {
        case 1000: {ACM_SYRINGES_10};
        case 500: {ACM_SYRINGES_5};
        case 300: {ACM_SYRINGES_3};
        default {ACM_SYRINGES_1};
    };

    _targetArray pushBack (configName _x);
} forEach ("getNumber (_x >> 'ACM_isSyringe') > 0" configClasses (configFile >> "CfgMagazines"));

// Vials

ACM_MEDICATION_VIALS = [];

{ // Medication Vials
    ACM_MEDICATION_VIALS pushBack (configName _x);
} forEach ("getNumber (_x >> 'ACM_isVial') > 0" configClasses (configFile >> "CfgWeapons"));

// Fresh whole blood registry. The server is authoritative for ID allocation and keeps one compatibility seed at
// ID 0; usable inventory classes are IDs 1..512. Clients explicitly request a snapshot on postInit/JIP rather than
// relying on a one-time publicVariable broadcast that may have happened before they connected.
if (isServer) then {
    missionNamespace setVariable [QGVAR(FreshBloodList), (createHashMapFromArray [[0,[objNull,250,ACM_BLOODTYPE_ON,true,CBA_missionTime]]]), true];
};

if (hasInterface || isServer) then {
    [QGVAR(updateFreshBloodBagName), {
        params ["_size", "_id", ["_bloodTypeNet", -1]];

        private _classname = format ["ACM_FreshBloodBag_%1_%2", _size, _id];
        private _freshEntry = [_id] call FUNC(getFreshBloodEntry);
        private _bloodType = if (_freshEntry isEqualType [] && {count _freshEntry >= 3}) then {_freshEntry param [2, -1]} else {_bloodTypeNet};
        if (_bloodType < 0) exitWith {};
        private _bloodTypeString = [_bloodType, 1] call FUNC(convertBloodType);
        private _newName = format [C_LLSTRING(FreshBloodBag), (format ["%1 (%2ml) [%3]", _bloodTypeString, _size, _id])];
        [_classname, _newName] call CBA_fnc_renameInventoryItem;
    }] call CBA_fnc_addEventHandler;
};

// Send the current registry to a newly joined client, or to a client that detects an inventory item before its
// metadata. Serialize as key/value pairs so the network payload is ordinary arrays on every supported Arma build.
[QGVAR(requestFreshBloodRegistry), {
    if (!isServer) exitWith {};
    params ["_requester"];
    if (isNull _requester) exitWith {};
    private _freshList = missionNamespace getVariable [QGVAR(FreshBloodList), createHashMap];
    private _pairs = [];
    { _pairs pushBack [_x, _y]; } forEach _freshList;
    [QGVAR(syncFreshBloodRegistry), [_pairs], _requester] call CBA_fnc_targetEvent;
}] call CBA_fnc_addEventHandler;

[QGVAR(syncFreshBloodRegistry), {
    if (!hasInterface) exitWith {};
    params ["_pairs"];
    private _freshList = createHashMapFromArray _pairs;
    missionNamespace setVariable [QGVAR(FreshBloodList), _freshList, false];
    {
        _x params ["_id", "_entry"];
        if (_id > 0 && {_entry isEqualType []} && {count _entry >= 3}) then {
            [QGVAR(updateFreshBloodBagName), [_entry param [1, 0], _id, _entry param [2, -1]]] call CBA_fnc_localEvent;
        };
    } forEach _pairs;
}] call CBA_fnc_addEventHandler;

// Filled FBTKs request their unique donor-bag ID from the server. This removes both the JIP ID-0 failure and
// concurrent-client ID collisions. The exact donor entry is sent back with the item so the receiving medic has
// valid metadata before the inventory class is exposed to the transfusion menu.
[QGVAR(requestFreshBloodBag), {
    if (!isServer) exitWith {};
    params ["_medic", "_donor", "_volume"];
    if (isNull _medic || {isNull _donor} || {!(_volume in [250, 500])}) exitWith {};
    private _freshBloodID = [_donor, _volume] call FUNC(generateFreshBloodEntry);
    if (_freshBloodID < 1) exitWith {
        [QGVAR(receiveFreshBloodBag), [_medic, _volume, -1, []], _medic] call CBA_fnc_targetEvent;
    };
    private _freshEntry = [_freshBloodID] call FUNC(getFreshBloodEntry);
    private _freshBloodType = _freshEntry param [2, -1];
    [QGVAR(updateFreshBloodBagName), [_volume, _freshBloodID, _freshBloodType]] call CBA_fnc_globalEvent;
    [QGVAR(receiveFreshBloodBag), [_medic, _volume, _freshBloodID, _freshEntry], _medic] call CBA_fnc_targetEvent;
}] call CBA_fnc_addEventHandler;

[QGVAR(receiveFreshBloodBag), {
    if (!hasInterface) exitWith {};
    params ["_medic", "_volume", "_id", "_entry"];
    if (_id < 1 || {!(_entry isEqualType [])} || {count _entry < 3}) exitWith {
        ["Unable to allocate a donor blood bag ID. The filled FBTK was not returned.", 3] call ACEFUNC(common,displayTextStructured);
    };

    // Install the donor metadata first. This guarantees the menu and ivBag callback can resolve ABO/time data even
    // if the server's public registry update arrives after this targeted delivery event.
    private _freshList = missionNamespace getVariable [QGVAR(FreshBloodList), createHashMap];
    _freshList set [_id, _entry];
    missionNamespace setVariable [QGVAR(FreshBloodList), _freshList, false];

    private _className = format ["%1_%2", (["FreshBlood", _volume] call FUNC(formatFluidBagName)), _id];
    private _returnedItem = [_medic, _className] call ACEFUNC(common,addToInventory);
    if !(_returnedItem param [0, false]) then {
        // Preserve the donor product instead of deleting it when the collector's inventory is full.
        private _holder = createVehicle ["GroundWeaponHolder", _medic modelToWorld [0, 1, 0], [], 0, "CAN_COLLIDE"];
        _holder addItemCargoGlobal [_className, 1];
        ["Inventory full. Fresh donor blood was placed on the ground.", 2.5] call ACEFUNC(common,displayTextStructured);
    };
    [QGVAR(updateFreshBloodBagName), [_volume, _id, _entry param [2, -1]]] call CBA_fnc_localEvent;
}] call CBA_fnc_addEventHandler;

if (hasInterface) then {
    [{!isNull player}, {
        [QGVAR(requestFreshBloodRegistry), [player]] call CBA_fnc_serverEvent;
    }, []] call CBA_fnc_waitUntilAndExecute;
};
