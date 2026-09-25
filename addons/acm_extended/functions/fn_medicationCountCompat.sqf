/* B156: ACM returns an effective scalar; current ACE returns [dose, effectiveness].
 * Both raw-count and onset-aware callers consume effectiveness, never the unscaled dose slot.
 * Forward the full argument list, including ACM's body-part filter, unchanged.
 */
if (isNil "ace_medical_status_fnc_getMedicationCount") exitWith {0};
private _value = _this call ace_medical_status_fnc_getMedicationCount;
if (_value isEqualType []) then {_value = _value param [1, 0, [0]];};
if !(_value isEqualType 0) exitWith {0};
_value
