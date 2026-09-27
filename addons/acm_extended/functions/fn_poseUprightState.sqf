/* B175: choose the provider work state for a conscious independently standing casualty.
   Arma's medicUp family is still a kneeling-provider family (AinvPknl...), but its hands work upward/in front
   rather than down onto a casualty on the floor. ACME_poseUprightStates maps explicit treatment modes only.

   A candidate is used only if it exists in CfgMovesMaleSdr on this machine. Missing/renamed BI states therefore
   fall back to the established downed-casualty state and can never block a clinical action.

   Arguments: 0 mode, 1 normal/downed state, 2 patient
   Return: [state, usingMedicUp] */
params [["_mode", "", [""]], ["_normal", "", [""]], ["_patient", objNull, [objNull]]];
if (_normal == "" || {!([_patient] call ACME_fnc_patientUpright)}) exitWith {[_normal, false]};

private _table = missionNamespace getVariable ["ACME_poseUprightStates", createHashMap];
private _candidate = _table getOrDefault [_mode, ""];
if !(_candidate isEqualType "") then {_candidate = "";};
if (_candidate == "") exitWith {[_normal, false]};

if (isClass (configFile >> "CfgMovesMaleSdr" >> "States" >> _candidate)) exitWith {[_candidate, true]};
[_normal, false]
