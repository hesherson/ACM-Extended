#include "..\script_component.hpp"
/*
 * Author: BaerMitUmlaut
 * Deserializes the medical state of a unit and applies it.
 *
 * Arguments:
 * 0: Unit <OBJECT>
 * 1: State as JSON <STRING>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, _json] call ace_medical_fnc_deserializeState;
 *
 * Public: Yes
 */
params [["_unit", objNull, [objNull]], ["_json", "{}", [""]]];

// Don't run in scheduled environment
if (canSuspend) exitWith {
    [ACEFUNC(medical,deserializeState), _this] call CBA_fnc_directCall
};

if (isNull _unit) exitWith {};
if (!local _unit) exitWith { ERROR_1("unit [%1] is not local",_unit) };

// If unit is not initialized yet, wait until event is raised
if !(_unit getVariable [QACEGVAR(medical,initialized), false]) exitWith {
    [QACEGVAR(medical_status,initialized), {
        params ["_unit"];
        _thisArgs params ["_target"];

        if (_unit == _target) then {
            _thisArgs call ACEFUNC(medical,deserializeState);
            [_thisType, _thisId] call CBA_fnc_removeEventHandler;
        };
    }, _this] call CBA_fnc_addEventHandlerArgs;
};

private _acmeBinding = "NA4:deserializeState";
private _state = [_json] call CBA_fnc_parseJSON;
if (isNull _state) exitWith {};
private _clinical = _state getVariable ["ACME_Clinical_v3", []];
private _validation = [_clinical] call ACME_fnc_clinicalValidate;
if !(_validation select 0) exitWith {
    _state call CBA_fnc_deleteNamespace;

};
// Decode into a clock write plan before reset, not while mutating the patient.
private _nativeClocks = _state getVariable ["ACME_NativeClocks_v3", []];
private _clockAllowed = ["ACM_airway_AirwayObstructionVomit_GracePeriod", "ACM_airway_AirwayChecked_Time", "ACM_breathing_TensionPneumothorax_Time", "ACM_breathing_BVM_lastBreath", "ACM_breathing_BVM_lastBreathOxygen", "ACM_circulation_LozengeItem_InsertTime", "ACM_circulation_ROSC_Time", "ACM_circulation_CardiacArrest_Time", "ACM_circulation_CardiacArrest_DeteriorationTime", "ACM_circulation_ReversibleCardiacArrest_Time", "ACM_circulation_AED_LastShock", "ACM_circulation_CPR_StoppedTime", "ACM_circulation_AmmoniaInhalant_LastUse", "ACM_disability_Tourniquet_ApplyTime"];
private _clockWrites = [];
private _clockSeen = createHashMap;
private _clockBudget = [100000];
private _clockOK = _nativeClocks isEqualType [];
if (_clockOK) then {
    _clockOK = (_nativeClocks findIf {
        if !(_x isEqualType [] && {count _x == 2} && {!isNil {_x select 0}}
            && {(_x select 0) isEqualType ""} && {!isNil {_x select 1}}) exitWith {true};
        _x params ["_key", "_encoded"];
        private _keyLower = toLowerANSI _key;
        if (_keyLower in _clockSeen) exitWith {true};
        _clockSeen set [_keyLower, true];
        if !([_encoded, 0, _clockBudget] call ACME_fnc_clinicalEncodedValid) exitWith {true};
        if !(_key in _clockAllowed) exitWith {false};
        private _value = [_encoded, false] call ACME_fnc_clinicalCodec;
        if (isNil "_value") exitWith {false};
        private _valid = if (_key == "ACM_disability_Tourniquet_ApplyTime") then {
            _value isEqualType [] && {count _value == 6} && {(_value findIf {
                isNil "_x" || {!(_x isEqualType 0)} || {!finite _x}
            }) < 0}
        } else {_value isEqualType 0 && {finite _value}};
        if (!_valid) exitWith {true};
        _clockWrites pushBack [_key, _value];
        false
    }) < 0;
};
if (!_clockOK) exitWith {_state call CBA_fnc_deleteNamespace; };

private _variableList = [
    [VAR_BLOOD_VOL, DEFAULT_BLOOD_VOLUME],
    [VAR_HEART_RATE, DEFAULT_HEART_RATE],
    [VAR_BLOOD_PRESS, [80, 120]],
    [VAR_PERIPH_RES, DEFAULT_PERIPH_RES],
    // State transition should handle this
    // [VAR_CRDC_ARRST, false],
    [VAR_SPO2, DEFAULT_SPO2],
    [VAR_HEMORRHAGE, 0],
    [VAR_PAIN, 0],
    [VAR_IN_PAIN, false],
    [VAR_PAIN_SUPP, 0],
    [VAR_OPEN_WOUNDS, createHashMap],
    [VAR_BANDAGED_WOUNDS, createHashMap],
    [VAR_STITCHED_WOUNDS, createHashMap],

    [VAR_FRACTURES, DEFAULT_FRACTURE_VALUES],
    // State transition should handle this
    // [VAR_UNCON, false],
    [VAR_TOURNIQUET, DEFAULT_TOURNIQUET_VALUES],
    [QACEGVAR(medical,occludedMedications), nil],
    [QACEGVAR(medical,triageLevel), 0],
    [QACEGVAR(medical,triageCard), []],
    [VAR_BODYPART_DAMAGE, DEFAULT_BODYPART_DAMAGE_VALUES],
    // Offset needs to be converted
    // [VAR_MEDICATIONS, []]
    ////////////////////////////////
    // Airway
    [QEGVAR(airway,AirwayReflex_State), true],
    [QEGVAR(airway,AirwayCollapse_State), 0],
    [QEGVAR(airway,AirwayObstructionVomit_State), 0],
    [QEGVAR(airway,AirwayObstructionVomit_GracePeriod), -1],
    [QEGVAR(airway,AirwayObstructionVomit_Count), 2],
    [QEGVAR(airway,AirwayObstructionBlood_State), 0],
    [QEGVAR(airway,RecoveryPosition_State), false],
    [QEGVAR(airway,AirwayItem_Oral), ""],
    [QEGVAR(airway,AirwayItem_Nasal), ""],
    [QEGVAR(airway,AirwayChecked_Time), nil],
    [QEGVAR(airway,SurgicalAirway_State), false],
    [QEGVAR(airway,SurgicalAirway_IncisionStitched), false],
    [QEGVAR(airway,SurgicalAirway_IncisionCount), 0],
    [QEGVAR(airway,SurgicalAirway_StrapSecure), false],
    [QEGVAR(airway,SurgicalAirway_TubeUnSecure), false],
    // Breathing
    [QEGVAR(breathing,ChestInjury_State), false],
    [QEGVAR(breathing,Pneumothorax_State), 0],
    [QEGVAR(breathing,TensionPneumothorax_State), false],
    [QEGVAR(breathing,TensionPneumothorax_Time), nil],
    [QEGVAR(breathing,Hemothorax_State), 0],
    [QEGVAR(breathing,Hemothorax_Fluid), 0],
    [QEGVAR(breathing,ChestSeal_State), false],
    [QEGVAR(breathing,Thoracostomy_State), nil],
    [QEGVAR(breathing,Thoracostomy_UsedKit), false],
    [QEGVAR(breathing,PulseOximeter_Display), [[0,0],[0,0]]],
    [QEGVAR(breathing,PulseOximeter_Placement), [false,false]],
    [QEGVAR(breathing,PulseOximeter_LastSync), [-1,-1]],
    [QEGVAR(breathing,Hardcore_Pneumothorax), false],
    [QEGVAR(breathing,BVM_lastBreath), nil],
    [QEGVAR(breathing,BVM_lastBreathOxygen), nil],
    [QEGVAR(breathing,RespirationRate), 18],
    [QEGVAR(breathing,Stethoscope_LungState), [0,0]],
    // Circulation
    [QEGVAR(circulation,LozengeItem), ""],
    [QEGVAR(circulation,LozengeItem_InsertTime), -1],
    [QEGVAR(circulation,PressureCuff_Placement), [false,false]],
    [QEGVAR(circulation,ROSC_Time), nil],
    [QEGVAR(circulation,CardiacArrest_Time), nil],
    [QEGVAR(circulation,Hardcore_PostCardiacArrest), false],
    [QEGVAR(circulation,IV_Placement), ACM_IV_PLACEMENT_DEFAULT_0],
    [VAR_IV_COMPLICATIONS_PAIN, ACM_IV_PLACEMENT_DEFAULT_0],
    [VAR_IV_COMPLICATIONS_FLOW, ACM_IV_PLACEMENT_DEFAULT_0],
    [VAR_IV_COMPLICATIONS_BLOCK, ACM_IV_PLACEMENT_DEFAULT_0],
    [QEGVAR(circulation,IO_Placement), ACM_IO_PLACEMENT_DEFAULT_0],
    [QEGVAR(circulation,IV_Bags), createHashMap],
    [QEGVAR(circulation,IV_Bags_Active), false],
    [QEGVAR(circulation,IV_Bags_FreshBloodEffect), 0],
    [QEGVAR(circulation,ActiveFluidBags_IV), ACM_IV_PLACEMENT_DEFAULT_1],
    [QEGVAR(circulation,ActiveFluidBags_IO), ACM_IO_PLACEMENT_DEFAULT_1],
    [VAR_FLUIDBAG_FLOW_IV, ACM_IV_PLACEMENT_DEFAULT_1],
    [VAR_FLUIDBAG_FLOW_IO, ACM_IO_PLACEMENT_DEFAULT_1],
    [QEGVAR(circulation,Blood_Volume), 6],
    [QEGVAR(circulation,Plasma_Volume), 0],
    [QEGVAR(circulation,Saline_Volume), 0],
    [QEGVAR(circulation,Platelet_Count), 3],
    [QEGVAR(circulation,Calcium_Count), 0],
    [QEGVAR(circulation,Calcium_FirstDose), false],
    [QEGVAR(circulation,Overload_Volume), 0],
    [QEGVAR(circulation,TransfusedBlood_Volume), 0],
    [QEGVAR(circulation,HemolyticReaction_Volume), 0],
    [QEGVAR(circulation,HemolyticReaction_Severity), 0],
    [QEGVAR(circulation,Cardiac_RhythmState), ACM_Rhythm_Sinus],
    [QEGVAR(circulation,CardiacArrest_TargetRhythm), nil],
    [QEGVAR(circulation,CardiacArrest_DeteriorationTime), nil],
    [QEGVAR(circulation,CardiacArrest_ShockResistant), false],
    [QEGVAR(circulation,CardiacArrest_ResistChecked), false],
    [QEGVAR(circulation,ReversibleCardiacArrest_Time), nil],
    [QEGVAR(circulation,ReversibleCardiacArrest_State), false],
    [QEGVAR(circulation,Vasoconstriction_State), 0],
    [QEGVAR(circulation,AED_LastShock), nil],
    [QEGVAR(circulation,AED_ShockTotal), 0],
    [QEGVAR(circulation,CPR_StoppedTotal), nil],
    [QEGVAR(circulation,CPR_StoppedTime), nil],
    [QEGVAR(circulation,AmmoniaInhalant_LastUse), -1],
    [QEGVAR(circulation,CirculationState), true],
    [QEGVAR(circulation,BloodType), ACM_BLOODTYPE_O],
    // Core
    [QEGVAR(core,KnockOut_State), false],
    [QEGVAR(core,WasTreated), false],
    [QEGVAR(core,WasWounded), false],
    // Disability
    [QEGVAR(disability,Tourniquet_Time), [0,0,0,0,0,0]],
    [QEGVAR(disability,Tourniquet_ApplyTime), [-1,-1,-1,-1,-1,-1]],
    [VAR_SPLINTS, DEFAULT_SPLINT_VALUES],
    [QEGVAR(disability,Fracture_State), [0,0,0,0,0,0]],
    [QEGVAR(disability,Fracture_Prepared), [false,false,false,false,false,false]],
    [QEGVAR(disability,Fracture_Pain), [false,false,false,false,false,false]],
    [QEGVAR(disability,Fracture_ReFracture), [false,false,false,false,false,false]],
    [QEGVAR(disability,Fracture_NoEffect), [false,false,false,false,false,false]],
    [VAR_TOURNIQUET_NECROSIS, DEFAULT_TOURNIQUET_NECROSIS],
    [VAR_TOURNIQUET_NECROSIS_T, DEFAULT_TOURNIQUET_NECROSIS],
    // Damage
    [VAR_CLOTTED_WOUNDS, createHashMap],
    [VAR_WRAPPED_WOUNDS, createHashMap],
    [VAR_INTERNAL_WOUNDS, createHashMap]
];

// CBRN
private _CBRN_HazardsToCheck = [];

if (EGVAR(CBRN,enable)) then {
    _variableList append [
        [QEGVAR(CBRN,Exposed_State), false],
        [QEGVAR(CBRN,Exposed_External_State), false],
        [QEGVAR(CBRN,Contaminated_State), false],
        [QEGVAR(CBRN,BreathingAbility_State), 1],
        [QEGVAR(CBRN,BreathingAbility_Increase_State), 1],
        [QEGVAR(CBRN,EyesWashed), false],
        [QEGVAR(CBRN,Filter_State), DEFAULT_FILTER_CONDITION],
        [QEGVAR(CBRN,AirwayInflammation), 0],
        [QEGVAR(CBRN,SkinIrritation), [0,0,0,0,0,0]],
        [QEGVAR(CBRN,LungTissueDamage), 0],
        [QEGVAR(CBRN,CapillaryDamage), 0],
        [QEGVAR(CBRN,AirwaySpasm), false],
        [QEGVAR(CBRN,Chemical_Chlorine_Blindness), false],
        [QEGVAR(CBRN,Chemical_Lewisite_Blindness), false],
        [QEGVAR(CBRN,IsImmune), false],
        [QEGVAR(CBRN,Blindness_State), false]
    ];

    // Hazard Exposure
    {
        _variableList pushBack [(format ["ACM_CBRN_%1_Buildup", toLower _x]), 0];
        _variableList pushBack [(format ["ACM_CBRN_%1_Buildup_Threshold", toLower _x]), -1];
        _variableList pushBack [(format ["ACM_CBRN_%1_Exposed_State", toLower _x]), false];
        _variableList pushBack [(format ["ACM_CBRN_%1_Exposed_External_State", toLower _x]), false];
        _variableList pushBack [(format ["ACM_CBRN_%1_Contaminated_State", toLower _x]), false];
        _variableList pushBack [(format ["ACM_CBRN_%1_WasExposed", toLower _x]), false];

        _CBRN_HazardsToCheck pushBack (format ["ACM_CBRN_%1_Buildup", toLower _x]);
    } forEach EGVAR(CBRN,HazardType_Array);
};

// Build a validated native write plan BEFORE tearing down the existing patient.
private _writes = [];
private _invalid = "";
{
    _x params ["_var", "_default"];
    private _value = _state getVariable _x;
    if (isNil "_value") then {_writes pushBack [_var]; continue;};
    if (typeName _value == "LOCATION") then {
        private _keys = allVariables _value;
        _value = _keys createHashMapFromArray (_keys apply {_value getVariable _x});
    };
    if (_value isEqualTo objNull) then {
        if (isNil "_default") then {_writes pushBack [_var];} else {_writes pushBack [_var, _default];};
        continue;
    };
    if (!isNil "_default" && {!(_value isEqualType _default)}) exitWith {_invalid = _var;};
    if (_value isEqualType 0 && {!finite _value}) exitWith {_invalid = _var;};
    _writes pushBack [_var, _value];
} forEach _variableList;
private _medications = _state getVariable [VAR_MEDICATIONS, []];
if !(_medications isEqualType [] && {(_medications findIf {
    if !(_x isEqualType [] && {count _x >= 15} && {(_x select 0) isEqualType ""}
        && {(_x select 13) isEqualType ""}) exitWith {true};
    private _entry = _x;
    ([1,2,3,4,5,6,7,8,9,10,11,12,14] findIf {
        !((_entry select _x) isEqualType 0 && {finite (_entry select _x)})
    }) >= 0
}) < 0}) then {_invalid = VAR_MEDICATIONS;};
private _targetState = _state getVariable [QACEGVAR(medical,statemachineState), "Default"];
if !(_targetState in ["Default","Injured","Unconscious","CardiacArrest","FatalInjury","Dead"]) then {_invalid = "statemachineState";};
if (_invalid != "") exitWith {
    _state call CBA_fnc_deleteNamespace;

};
_unit setVariable ["ACME_clinicalRestoring", true, false];
[_unit] call ACME_fnc_clearAllAilments;
{
    private _value = _x param [1, nil];
    _unit setVariable [_x select 0, _value, true];
} forEach _writes;

// Apply only the preflighted native clocks, before workers or state-machine entry.
{_unit setVariable [_x select 0, _x select 1, true];} forEach _clockWrites;

// Reset timers
_unit setVariable [QACEGVAR(medical,lastWakeUpCheck), nil];

// Convert medications offset to time
// Native medication entries were validated before reset.
{
    _x set [1, _x#1 + CBA_missionTime];
} forEach _medications;
_unit setVariable [VAR_MEDICATIONS, _medications, true];

// All Extended injury/ROSC constraints exist before state-machine entry callbacks
// or native workers read them. ownerRegister is deferred by the restore guard.
[_unit, _clinical, [_unit] call ACME_fnc_clinicalEpoch] call ACME_fnc_clinicalRestore;

// Update effects
[_unit] call ACEFUNC(medical_engine,updateDamageEffects);
[_unit] call ACEFUNC(medical_status,updateWoundBloodLoss);

// Transition within statemachine
private _currentState = [_unit, ACEGVAR(medical,STATE_MACHINE)] call CBA_statemachine_fnc_getCurrentState;
[_unit, ACEGVAR(medical,STATE_MACHINE), _currentState, _targetState] call CBA_statemachine_fnc_manualTransition;

// Manually call wake up transition if necessary
if (_currentState in ["Unconscious", "CardiacArrest"] && {_targetState in ["Default", "Injured"]}) then {
    [_unit, false] call ACEFUNC(medical_status,setUnconsciousState);
};

// Resume only after the validated state transition has completed.
_unit setVariable ["ACME_clinicalRestoring", false, false];
// The validated restored episode may remain unconscious throughout teardown/rebuild.
if (!isNil "ACME_fnc_aiProtectionSync") then {[_unit, "restore"] call ACME_fnc_aiProtectionSync;};

// Airway
if (IS_UNCONSCIOUS(_unit)) then {
    [QEGVAR(airway,handleAirwayCollapse), [_unit]] call CBA_fnc_localEvent;

    if !(_state getVariable [QEGVAR(airway,AirwayReflex_State), false]) then {
        if ([_unit, "head"] call EFUNC(damage,isBodyPartBleeding) || (_state getVariable [QEGVAR(airway,AirwayObstructionBlood_PFH), -1] > -1)) then {
            [QEGVAR(airway,handleAirwayObstruction_Blood), [_unit]] call CBA_fnc_localEvent;
        };
    };

    if (_state getVariable [QEGVAR(airway,AirwayObstructionVomit_PFH), -1] > -1) then {
        [QEGVAR(airway,handleAirwayObstruction_Vomit), [_unit]] call CBA_fnc_localEvent;
    };
};

// Breathing: restore the injury's existing air/leak balance. The native injury
// entry point would reopen its leak and turn a stable saved chest into a new injury.
if ((_unit getVariable [QEGVAR(breathing,Pneumothorax_State), 0]) > 0
    || {_unit getVariable [QEGVAR(breathing,TensionPneumothorax_State), false]}
    || {_unit getVariable [QEGVAR(breathing,ChestInjury_State), false]}
    || {count (_unit getVariable ["ACME_ptx_state", []]) > 0}) then {
    [_unit] call ACME_fnc_ptxEnsure;
};

if (_state getVariable [QEGVAR(breathing,Hemothorax_PFH), -1] > -1) then {
    [_unit] call EFUNC(breathing,handleHemothorax);
};

if (_state getVariable [QEGVAR(breathing,PulseOximeter_Placement), [false, false]] isNotEqualTo [false,false]) then {
    [objNull, _unit] call EFUNC(breathing,handlePulseOximeter);
};

// Circulation
if (_state getVariable [QEGVAR(circulation,CardiacArrest_PFH), -1] > -1) then {
    [_unit, true] call EFUNC(circulation,handleCardiacArrest);
};

if (_state getVariable [QEGVAR(circulation,ReversibleCardiacArrest_PFH), -1] > -1) then {
    [_unit, true] call EFUNC(circulation,handleReversibleCardiacArrest);
};

if (_state getVariable [QEGVAR(circulation,HemolyticReaction_PFH), -1] > -1) then {
    [_unit] call EFUNC(circulation,handleHemolyticReaction);
};

// Disability
if (_state getVariable [QEGVAR(disability,TourniquetEffects_PFH), -1] > -1) then {
    [_unit] call EFUNC(disability,handleTourniquetEffects);
};

// Damage
if (_state getVariable [QEGVAR(damage,Coagulation_PFH), -1] > -1) then {
    [_unit] call EFUNC(damage,handleCoagulationPFH);
};

if (_state getVariable [QEGVAR(damage,IBCoagulation_PFH), -1] > -1) then {
    [_unit] call EFUNC(damage,handleIBCoagulationPFH);
};

// CBRN
if (EGVAR(CBRN,enable)) then {
    {
        if (_state getVariable [(format ["ACM_CBRN_%1_WasExposed", toLower _x]), false]) then {
            [_unit, _x] call EFUNC(CBRN,initHazardUnit);
        };
    } forEach EGVAR(CBRN,HazardType_Array);
};

[_unit] call ACME_fnc_ownerRegister;
_state call CBA_fnc_deleteNamespace;
