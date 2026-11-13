/* The panel button uses the same patient-scoped pairing action as the medical menu. */
params ["_ls"];
if (isNull _ls) exitWith {};
private _patient = _ls getVariable ["acme_tempusls_pat",objNull];
if (isNil "ACME_fnc_equipmentMonitorAction" || {!([ACE_player,_patient,"ls","pair",true,_ls] call ACME_fnc_equipmentMonitorAction)}) then {
    ["Set up a powered Tempus Pro and LS for the same patient before pairing.",2] call ace_common_fnc_displayTextStructured;
};
