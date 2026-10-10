/* Progress deadline decision: current deadline = succeed; larger deadline = keep same action/UI;
 * -1 = fail safely. Called only at/after the current deadline by the assessment-only ACE adapter. */
params ["_args", "_elapsed", "_deadline", "_initial"];
_args params ["_medic", "_patient", "_part", "_class"];
if (!isNull objectParent _medic) exitWith {[_deadline, -1] select ((_args param [7, -2]) != -1)};
private _record = _medic getVariable ["ACME_assessment", []];
if (_record isEqualTo [] || {(_args param [7, -1]) != (_record select 0)}) exitWith {-1};
private _pose = _medic getVariable ["ACME_treatmentPoseState", []];
if ((_pose param [0, -1]) != (_record select 0)) exitWith {-1};
// Prone has a supported continuous fallback rather than a finite kneeling RTM. It still
// requires actual observed work and the full configured clinical interval.
if ((_pose param [20, false]) && {(_record select 2) >= 1}) exitWith {_deadline};
if ((_record select 2) == 3) exitWith {_deadline};
// No unbounded action when the requested RTM cannot enter/finish. Never report success for skipped work.
if (_elapsed >= _initial + 5) exitWith {-1};
ceil (_elapsed + 0.001)
