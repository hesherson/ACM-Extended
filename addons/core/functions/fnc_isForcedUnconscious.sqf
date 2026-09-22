#include "..\script_component.hpp"
/*
 * Author: Blue
 * Check if patient is forced unconscious.
 */
params ["_patient"];

if (isNull _patient || {!alive _patient}) exitWith {true};

if (_patient getVariable ["ace_medical_inCardiacArrest", false]) exitWith {true};
if ((_patient getVariable ["ACME_lido_seizureState", ""]) == "active") exitWith {true};
if (_patient getVariable [QEGVAR(evacuation,casualtyTicketClaimed), false]) exitWith {true};
if (_patient getVariable [QEGVAR(airway,SurgicalAirway_State), false]) exitWith {true};
if (_patient getVariable ["ACME_roc_paralyzed", false]) exitWith {true};

if (!isNil "ACME_fnc_sedationActive") exitWith {
    [_patient] call ACME_fnc_sedationActive
};

false
