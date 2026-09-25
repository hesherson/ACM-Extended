// attach the medic-owned EMMA inline on the own BVM of the medic.
// the physical inventory item remains in inventory, and this only toggles the BVM state of the reusable device.
// _this is the ACE callback [_medic, _patient, _bodyPart].
params ["_medic", ["_patient", objNull]];
if (isNull _medic) exitWith {};

if (([_medic, _patient, "ACM_EMMA"] call ACME_fnc_treatmentSupplyCount) <= 0) exitWith {
    ["You do not have an EMMA.", 2, _medic] call ace_common_fnc_displayTextStructured;
};

// moving the EMMA back to the medic-owned BVM must tear down any patient-side or i-gel route first.
[_medic] call ACME_fnc_emmaClearIGelForMedic;

private _layer = "ACME_EMMA" call BIS_fnc_rscLayer;
_layer cutText ["", "PLAIN"];
uiNamespace setVariable ["ACME_EMMA_DLG", displayNull];

if ((_medic getVariable ["ACME_emma_bvmAttached", false])) exitWith {
    ["EMMA is already attached to your BVM.", 2, _medic] call ace_common_fnc_displayTextStructured;
};

_medic setVariable ["ACME_emma_supplyPatient", _patient, false];
_medic setVariable ["ACME_emma_bvmAttached", true, true];
_medic setVariable ["ACME_emma_route", "bvm", false];
_medic setVariable ["ACME_emma_capPatient", objNull, false];
_medic setVariable ["ACME_emma_lastPatient", objNull, false];
_medic setVariable ["ACME_emma_lastBag", -1e9, false];
_medic setVariable ["ACME_emma_lastContactPatient", objNull, false];
_medic setVariable ["ACME_emma_lastContactTime", -1e9, false];

["EMMA attached to your BVM.", 2, _medic] call ace_common_fnc_displayTextStructured;
