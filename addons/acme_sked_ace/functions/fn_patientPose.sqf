params ["_patient"];
private _states = configFile >> "CfgMovesMaleSdr" >> "States";
private _pose = missionNamespace getVariable ["acme_sked_patientAnim", "ACM_LyingState"];
if ((toLowerANSI _pose) == "unconsciousfaceup" || {!isClass (_states >> _pose)}) then {
    _pose = if (isNil "ACME_fnc_headElevRestAnim") then {"unconsciousfaceup"}
        else {[_patient] call ACME_fnc_headElevRestAnim};
};
if (isClass (_states >> _pose)) exitWith {_pose};
"Unconscious"
