#include "script_component.hpp"

//
// The treatment bridge is not an optional presentation hook: ACME launcher actions depend on it to own the
// medical-menu handoff and to bypass ACE's generic treatment animation for modal workspaces.  ACE and third-party
// medical addons may PREP/recompile ace_medical_treatment_fnc_treatment during startup, after CfgFunctions has
// selected ACM's override. Reconcile once in postInit, after ACE (a required addon) has completed its startup.
//
// "ACME_ApplyChestSeal" is a stable marker present in ACM's bridge and absent from ACE's native treatment function.
private _acmTreatmentBridge = missionNamespace getVariable ["ace_medical_treatment_fnc_treatment", {}];
private _acmTreatmentBridgeOwned = _acmTreatmentBridge isEqualType {}
    && {(toLowerANSI (str _acmTreatmentBridge) find "acme_applychestseal") >= 0};
if (!_acmTreatmentBridgeOwned) then {
    ace_medical_treatment_fnc_treatment = compile preprocessFileLineNumbers QPATHTOF(overrides\fnc_treatment.sqf);
    diag_log "[ACM] (core) Reconciled ace_medical_treatment_fnc_treatment to ACM treatment bridge.";
};

if (GVAR(ignoreIncompatibleAddonWarning)) then {
    WARNING("Incompatible Addon Warning Disabled");
} else {
    ["CBA_settingsInitialized", {
        [] call FUNC(checkIncompatibleAddons);
    }] call CBA_fnc_addEventHandler;
};

[0, {
    if (_this getVariable [QACEGVAR(medical,isBleeding), false]) exitWith {};

    private _count = 0;

    ({
        _count = _count + (count _x);
    } forEach (_this getVariable [QEGVAR(circulation,IV_Bags), createHashMap]));

    -1 * _count;
}] call ACEFUNC(field_rations,addStatusModifier);

[QGVAR(openMedicalMenu), {
    params ["_target"];

    ACEGVAR(medical_gui,pendingReopen) = false;
    [ACEFUNC(medical_gui,openMenu), _target] call CBA_fnc_execNextFrame;
}] call CBA_fnc_addEventHandler;

["ace_cardiacArrest", LINKFUNC(onCardiacArrest)] call CBA_fnc_addEventHandler;
["ace_unconscious", LINKFUNC(onUnconscious)] call CBA_fnc_addEventHandler;

[QGVAR(handleFatalVitals), LINKFUNC(handleFatalVitals)] call CBA_fnc_addEventHandler;

[QACEGVAR(medical_treatment,fullHealLocalMod), LINKFUNC(fullHealLocal)] call CBA_fnc_addEventHandler;

[QGVAR(showTreatmentText), LINKFUNC(handleTreatmentText)] call CBA_fnc_addEventHandler;

["ace_treatmentStarted", {
    params ["_medic", "_patient", "", "_classname"];

    if (isPlayer _patient) then {
        [QGVAR(showTreatmentText), [_medic, _patient, true], _patient] call CBA_fnc_targetEvent;
    };
}] call CBA_fnc_addEventHandler;

["ace_treatmentFailed", {
    params ["_medic", "_patient", "", "_classname"];

    if (isPlayer _patient) then {
        [QGVAR(showTreatmentText), [_medic, _patient, false], _patient] call CBA_fnc_targetEvent;
    };
}] call CBA_fnc_addEventHandler;

["ace_treatmentSucceded", {
    params ["_medic", "_patient", "", "_classname"];

    if (isPlayer _patient) then {
        [QGVAR(showTreatmentText), [_medic, _patient, false], _patient] call CBA_fnc_targetEvent;
    };

    if (_patient getVariable [QGVAR(WasTreated), false]) exitWith {};

    if !(IS_UNCONSCIOUS(_patient)) exitWith {};

    if (_classname in ["CheckDogTags","SlapAwake","AmmoniaInhalant"]) exitWith {}; // Ignore these

    private _config = configFile >> QACEGVAR(medical_treatment,actions) >> _classname;

    if (isNumber (_config >> "ACM_rollToBack")) then {
        if ([false,true] select (getNumber (_config >> "ACM_rollToBack"))) then {
            _patient setVariable [QGVAR(WasTreated), true, true];
        };
    };
}] call CBA_fnc_addEventHandler;

// External and native wake events share the same state-aware repair as requestWake.
// A later knockout, full heal/restore, second request or owner handoff invalidates this callback.
[QACEGVAR(medical,WakeUp), {
    params [["_unit", objNull, [objNull]]];
    if (isNull _unit || {!local _unit} || {!alive _unit}) exitWith {};
    private _ticket = (_unit getVariable ["ACME_wakeRepairTicket", 0]) + 1;
    _unit setVariable ["ACME_wakeRepairTicket", _ticket, false];
    private _epoch = _unit getVariable ["ACME_clinicalEpoch", 0];
    private _owner = owner _unit;
    [{
        params ["_unit", "_ticket", "_epoch", "_owner"];
        if (isNull _unit || {!local _unit} || {!alive _unit}
            || {owner _unit != _owner}
            || {(_unit getVariable ["ACME_wakeRepairTicket", -1]) != _ticket}
            || {(_unit getVariable ["ACME_clinicalEpoch", 0]) != _epoch}
            || {_unit getVariable ["ACME_clinicalRestoring", false]}) exitWith {};
        if !([_unit] call FUNC(canWake)) exitWith {};
        if ([_unit, "wake-event"] call FUNC(reconcileWake)) then {
            _unit setVariable ["ACME_obtunded_wakeStimGraceUntil", CBA_missionTime + 20, true];
        };
    }, [_unit, _ticket, _epoch, _owner]] call CBA_fnc_execNextFrame;
}] call CBA_fnc_addEventHandler;

[QGVAR(playWakeUpSound), {
    params ["_patient"];

    _patient setVariable [QACEGVAR(medical_feedback,soundTimeoutmoan), CBA_missionTime + 10];

    private _distance = 5;
    private _targets = allPlayers inAreaArray [ASLToAGL getPosASL _patient, _distance, _distance, 0, false, _distance];
    if (_targets isEqualTo []) exitWith {};

    private _sound = selectRandom ["ACM_wakeUp_1","ACM_wakeUp_2","ACM_wakeUp_3","ACM_wakeUp_4"];

    [QACEGVAR(medical_feedback,forceSay3D), [_patient, _sound, _distance], _targets] call CBA_fnc_targetEvent;
}] call CBA_fnc_addEventHandler;

[QGVAR(forceSay3D), { // medical_feedback/postInit
    params ["_patient", "_sound", "_distance", "_pitch"];

    if (ACE_player distance _patient > _distance) exitWith {};

    if (isNull objectParent _patient) then {
        // say3D waits for the previous sound to finish, so use a dummy instead
        private _dummy = "#dynamicsound" createVehicleLocal [0, 0, 0];
        _dummy attachTo [_patient, [0, 0, 0], "camera"];
        _dummy say3D [_sound, _distance, 1, false];

        [{
            detach _this;
            deleteVehicle _this;
        }, _dummy, 5] call CBA_fnc_waitAndExecute;
    } else {
        // Fallback: attachTo doesn't work within vehicles
        _patient say3D [_sound, _distance, _pitch, false];
    };
}] call CBA_fnc_addEventHandler;

[QACEGVAR(medical,death), {
    params ["_unit"];

    _unit setVariable [QEGVAR(circulation,Cardiac_RhythmState), ACM_Rhythm_Asystole, true];
    _unit setVariable [QGVAR(TimeOfDeath), CBA_missionTime, true];
}] call CBA_fnc_addEventHandler;

[QGVAR(cancelCarryingPrompt), LINKFUNC(cancelCarryingPrompt)] call CBA_fnc_addEventHandler;
[QGVAR(cancelCarryLocal), {
    params ["_carrier", "_target"];

    [format [LLSTRING(CancelCarrying_Stopped), [_target, true] call ACEFUNC(common,getName)], 1.5, _carrier] call ACEFUNC(common,displayTextStructured);
    [_carrier, _target] call ACEFUNC(dragging,dropObject_carry);
}] call CBA_fnc_addEventHandler;

[QACEGVAR(dragging,startedCarry), {
    params ["_unit", "_target"];

    if (_target isKindOf "CAManBase") then {
        [_target] call ACEFUNC(weaponselect,putWeaponAway);

        if !(IS_UNCONSCIOUS(_target)) then {
            [QGVAR(cancelCarryingPrompt), [_target, _unit], _target] call CBA_fnc_targetEvent;
        };
    };
}] call CBA_fnc_addEventHandler;

[QGVAR(getUpPrompt), LINKFUNC(getUpPrompt)] call CBA_fnc_addEventHandler;

// Phase 122: Get Up is patient-local. A provider can request it remotely, but the casualty owner owns the
// lying flag and recovery animation transaction.
[QGVAR(getUpRequest), {
    params ["_patient", ["_authorized", true], ["_initiator", objNull]];
    [_patient, _authorized, _initiator] call FUNC(getUp);
}] call CBA_fnc_addEventHandler;

["isNotInLyingState", {!((_this select 0) getVariable [QGVAR(Lying_State), false])}] call ACEFUNC(common,addCanInteractWithCondition);

if (hasInterface) then {
    GVAR(ppLowOxygenTunnelVision_Finalized) = false;
};

GVAR(MedicationTypes_MaxPainAdjust) = ["maxPainReduce", "painReduce"] call FUNC(generateMedicationTypeMap);
GVAR(MedicationTypes_MaxHRAdjust) = ["maxHRIncrease", "hrIncrease"] call FUNC(generateMedicationTypeMap);
GVAR(MedicationTypes_MaxRRAdjust) = ["maxRRAdjust", "rrAdjust"] call FUNC(generateMedicationTypeMap);

[QGVAR(handleSitting), LINKFUNC(handleSitting)] call CBA_fnc_addEventHandler;

ACE_player addEventHandler ["AnimDone", {
    params ["_unit", "_anim"];

    if !(local _unit) exitWith {};
    if (_anim == "AmovPercMstpSnonWnonDnon_AmovPsitMstpSnonWnonDnon_ground") then {
        [{
            params ["_unit"];

            animationState _unit == "amovpsitmstpsnonwnondnon_ground";
        }, {
            params ["_unit"];

            [QGVAR(handleSitting), _unit] call CBA_fnc_localEvent;
        }, [_unit], 2] call CBA_fnc_waitUntilAndExecute;
    };
}];

["ACE_splint", "ACM_SAMSplint"] call ACEFUNC(common,registerItemReplacement);

call FUNC(registerContinuousRuntime);
