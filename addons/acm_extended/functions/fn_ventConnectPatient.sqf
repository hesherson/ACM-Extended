/* Reserve one device before any patient state or provider inventory changes. */
params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_interface", "INVASIVE", [""]]];
if (isNull _medic || {!local _medic} || {isNull _patient}) exitWith {};
if !([_medic, "ventilator"] call ACME_fnc_procedureAllowed) exitWith {};
if !(_interface in ["INVASIVE", "MASK"]) exitWith {};
if (_interface == "MASK" && {!([_patient] call ACME_fnc_ventNivEligible)}) exitWith {};
if (_patient getVariable ["ACM_airway_RecoveryPosition_State", false]) exitWith {
    ["Move the patient out of the recovery position before connecting the ventilator.", 2] call ace_common_fnc_displayTextStructured;
};
[{ace_medical_gui_pendingReopen = false;}, []] call CBA_fnc_execNextFrame;
["ACME_ventCustodyRequest", ["attach", _medic, _patient, _interface]] call CBA_fnc_serverEvent;
