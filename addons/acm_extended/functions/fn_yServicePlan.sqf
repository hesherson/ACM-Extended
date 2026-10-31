/* [accept, amount, reason]. _reserved includes the active remainder and all queued flushes. */
params ["_mode", "_available", "_reserved", "_bloodPresent", "_dirty", "_primed", ["_running", ""]];
private _free = (_available - _reserved) max 0;
if (_mode == "prime") exitWith {
    if (_primed || {_running != ""}) exitWith {[false, 0, "This line is already primed or being serviced."]};
    if (_free < 25) exitWith {[false, 0, "Priming requires 25 mL in the saline reserve."]};
    [true, 25, ""]
};
if (_mode != "flush") exitWith {[false, 0, "Unknown line service."]};
if (!_primed) exitWith {[false, 0, "Prime the line first."]};
if (_bloodPresent) exitWith {[false, 0, "Flush is available only after the blood limb is empty."]};
if (_running != "" && {_running != "flush"}) exitWith {[false, 0, "Priming is still in progress."]};
if (_free >= 50) exitWith {[true, 50, ""]};
// Required post-2U clearing has a 25 mL minimum; elective extra flushes remain 50 mL.
if (_dirty && {_reserved <= 0} && {_free >= 25}) exitWith {[true, 25, ""]};
[false, 0, "Not enough unqueued saline: 50 mL per flush, or 25 mL for required line clearing."]
