// Experimental drag handles are available only in HEMTT dev/launch builds.
if (getNumber (configFile >> "CfgPatches" >> "ACM_Extended" >> "acme_developmentBuild") != 1) exitWith {false};
// Provider-side request to attach the ACME drag handle.
params [["_medic",objNull,[objNull]],["_patient",objNull,[objNull]]];
if (isNull _medic || {isNull _patient} || {!local _medic}) exitWith {false};
if (_medic isEqualTo _patient) exitWith {false};
if (_medic getVariable ["ACME_dragHandle_pending",false]) exitWith {false};
if (!isNull (_medic getVariable ["ACME_dragHandle_patient",objNull])) exitWith {false};

// Do not let a strict client-side visibility predicate silently eat the click. The patient owner performs the
// authoritative validation below and returns a specific reason if a race/conflict appeared after the menu painted.
_medic setVariable ["ACME_dragHandle_pending",true];
[_patient,"dragHandleStart",[_patient,_medic]] call ACME_fnc_ownerDispatch;

// Never strand the interaction if locality churn prevents an acknowledgement. The owner transaction is still
// authoritative; this only releases the local UI gate so the medic can try again.
[{
    params ["_m"];
    if (!isNull _m && {local _m} && {_m getVariable ["ACME_dragHandle_pending",false]}
        && {isNull (_m getVariable ["ACME_dragHandle_patient",objNull])}) then {
        _m setVariable ["ACME_dragHandle_pending",false];
    };
},[_medic],3] call CBA_fnc_waitAndExecute;
true
