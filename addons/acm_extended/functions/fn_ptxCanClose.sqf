/* B271 read-only surgical closure readiness. No provider-visible model values.
   Low PTX alone is insufficient: a drain can mask a continuing internal leak. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient) exitWith {false};
// Existing mechanical aftercare remains available after engine death.
if (!alive _patient) exitWith {true};
private _state = _patient getVariable ["ACME_ptx_state", []];
if !(_state isEqualType [] && {count _state == 9} && {(_state select 0) isEqualTo 1}
    && {(_state findIf {!(_x isEqualType 0) || {!finite _x}}) < 0}) exitWith {false};
private _context = [_patient] call ACME_fnc_ptxContext;
if ((_context select 0) > 0
    || {_patient getVariable ["ACM_breathing_TensionPneumothorax_State", false]}
    || {(_state select 1) > 1} || {(_state select 2) > 0.000001}
    || {(_state select 4) > 0.1}) exitWith {false};
// A tract on a patient with no PTX episode has no observation clock to advance.
if ((_state select 6) == 0 && {(_state select 1) <= 0} && {(_state select 4) <= 0}) exitWith {true};
if !((_patient getVariable ["ACME_ptx_observationRevision", 0]) isEqualTo 1) exitWith {false};
private _interval = missionNamespace getVariable ["ACME_ptx_stableSec", 60];
if !(_interval isEqualType 0 && {finite _interval}) then {_interval = 60;};
(_state select 3) >= (_interval max 0 min 86400)
