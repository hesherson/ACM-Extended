/* Per-side chest-tube presence, with a legacy native-only fallback.
   An explicit false on either side means this patient uses the Extended
   thoracostomy system. A stale native aggregate cannot make removed tubes
   available for suction or other interventions. Read-only on all machines. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient) exitWith {false};
private _left = _patient getVariable ["ACME_thora_tube_left", false];
private _right = _patient getVariable ["ACME_thora_tube_right", false];
if (_left || {_right}) exitWith {true};
private _explicit = !(isNil {_patient getVariable "ACME_thora_tube_left"})
    || {!(isNil {_patient getVariable "ACME_thora_tube_right"})};
if (_explicit) exitWith {false};
// Native-only ACM patients (including older saves) never created the two
// explicit tube booleans. Keep their existing legacy tube semantics.
(_patient getVariable ["ACM_breathing_Thoracostomy_State", 0]) in [2, 3]
