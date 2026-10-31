/* B217 tactile exam. Keep the source medical display alive; there is no ACE progress dialog.
 * One private action serial owns input, the 1.5-second contact, and both provider pose generations.
 * Seated care retains a 1.5-second clinical check without forcing an on-foot RTM through a vehicle seat.
 */
params ["_medic", "_patient", "_part", "_class"];
if (_class != "ACME_FeelSkin" || {isNull _medic} || {isNull _patient} || {!local _medic}
    || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)}) exitWith {false};
if ((_medic getVariable ["ACME_feelSkinAction", []]) isNotEqualTo []) exitWith {false};
if !(_this call ace_medical_treatment_fnc_canTreatCached) exitWith {false};
if !([_medic, _class] call ACME_fnc_procedureActionAllowed) exitWith {false};
if (objectParent _medic isNotEqualTo objectParent _patient
    || {([_medic, _patient] call ACME_fnc_patientInteractionDistance) > ace_medical_gui_maxDistance}
    || {!([_medic, _patient, ["isNotInside", "isNotSwimming", "isNotInZeus"]] call ace_common_fnc_canInteractWith)}
    || {isNull objectParent _medic && {[_medic] call ACME_fnc_animBlocked}}
    || {missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]}) exitWith {false};
private _serial = (_medic getVariable ["ACME_feelSkinSerial", 0]) + 1;
_medic setVariable ["ACME_feelSkinSerial", _serial];
private _vehicle = objectParent _medic;
private _epoch = -1;
if (isNull _vehicle) then {_epoch = [_medic, "chestSealWorkspace", -1, _patient] call ACME_fnc_treatmentPoseStart;};
if (isNull _vehicle && {_epoch < 0}) exitWith {false};
private _menu = displayNull;
if (hasInterface && {_medic isEqualTo ACE_player}) then {_menu = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];};
// 0 serial, 1 arguments, 2 current pose epoch, 3 phase (workspace=-1/reach=0/contact=1), 4 contact started,
// 5 action started, 6 PFH, 7 locality epoch, 8 source display, 9 display handler IDs,
// 10 started with menu, 11 seat, 12 return observed, 13 return deadline, 14 clinical epoch.
private _record = [_serial, +_this, _epoch, -1, -1, CBA_missionTime, -1,
    _medic getVariable ["ACME_providerLocalityEpoch", 0], _menu, [], !isNull _menu, _vehicle, false, -1,
    [_patient] call ACME_fnc_clinicalEpoch];
if (!isNull _vehicle) then {_record set [3, 1]; _record set [4, CBA_missionTime];};
_medic setVariable ["ACME_feelSkinAction", _record];
if (!isNull _menu) then {
    _menu setVariable ["ACME_feelSkinInput", [_medic, _serial]];
    private _key = _menu displayAddEventHandler ["KeyDown", {
        params ["_display", "_key"];
        if !(_key in [1, 0xF0]) exitWith {false};
        (_display getVariable ["ACME_feelSkinInput", [objNull, -1]]) call ACME_fnc_feelSkinStop;
        false
    }];
    private _mouse = _menu displayAddEventHandler ["MouseButtonDown", {
        params ["_display", "_button"];
        if (_button != 1) exitWith {false};
        (_display getVariable ["ACME_feelSkinInput", [objNull, -1]]) call ACME_fnc_feelSkinStop;
        false
    }];
    _record set [9, [["KeyDown", _key], ["MouseButtonDown", _mouse]]];
};
private _pfh = [ACME_fnc_feelSkinTick, 0, [_medic, _serial]] call CBA_fnc_addPerFrameHandler;
_record set [6, _pfh];
true
