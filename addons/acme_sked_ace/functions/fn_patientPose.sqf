/*
 * The pose a casualty is held in on a litter. With the setting at its default the litter decides
 * (acmeLitterPose): arms along the body, legs straight and together, on the SKED and on the Talon II alike.
 * Arguments: 0: casualty, 1: litter (default: the one they are on, or are being laid on). Returns: state name.
 */
params ["_patient", ["_litter", objNull]];
if (isNull _litter) then {
    _litter = _patient getVariable ["acme_sked_litter", _patient getVariable ["acme_sked_placing", objNull]];
};
private _states = configFile >> "CfgMovesMaleSdr" >> "States";
private _pose = missionNamespace getVariable ["acme_sked_patientAnim", "ACM_LyingState"];
if ((toLowerANSI _pose) in ["acm_lyingstate", ""]) then {
    _pose = "ACME_Litter_Side";
    if (!isNull _litter && {!((vest _patient) in ["ACME_HPMK_Worn", "ACME_HPMK_Worn_Sked", "ACME_HPMK_Worn_Open", "ACME_HPMK_Worn_Open_Sked"])}) then {
        private _own = getText (configOf _litter >> "acmeLitterPose");
        if (_own != "") then {_pose = _own;};
    };
    if !(isClass (_states >> _pose)) then {_pose = "ACM_LyingState";};
};
if ((toLowerANSI _pose) == "unconsciousfaceup" || {!isClass (_states >> _pose)}) then {
    _pose = if (isNil "ACME_fnc_headElevRestAnim") then {"unconsciousfaceup"}
        else {[_patient] call ACME_fnc_headElevRestAnim};
};
if (isClass (_states >> _pose)) exitWith {_pose};
"Unconscious"
