/* Configured native animation duration. Negative speed encodes seconds; positive is reciprocal. */
params [["_animation", "", [""]]];
private _speed = getNumber (configFile >> "CfgMovesMaleSdr" >> "States" >> _animation >> "speed");
if (!finite _speed || {_speed == 0}) exitWith {0};
if (_speed < 0) then {-_speed} else {1 / _speed}
