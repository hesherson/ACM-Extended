/* Retire only this owner-local floor lease. No detach, pose, medical, mass or
 * collision changes; an external transport/controller owns its own cleanup. */
params [["_patient",objNull,[objNull]], ["_serial",-1,[0]], ["_handoff",false,[false]]];
if (isNull _patient) exitWith {false};
private _record = _patient getVariable ["ACME_flightContainment",[]];
if (_record isEqualTo [] || {_serial >= 0 && {(_record select 0) != _serial}}) exitWith {false};
_patient setVariable ["ACME_flightContainment",[],false];
private _pfh = _record select 5;
if (_pfh >= 0) then {[_pfh] call CBA_fnc_removePerFrameHandler;};
if (local _patient && {!_handoff}) then {
    private _context = _patient getVariable ["ACME_flightContainmentContext",[]];
    if (!(_context isEqualTo []) && {(_context select 0) == (_record select 0)}) then {
        _patient setVariable ["ACME_flightContainmentContext",[],true];
    };
};
true
