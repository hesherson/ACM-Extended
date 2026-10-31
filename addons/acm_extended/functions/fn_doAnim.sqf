// play an animation, unless the unit is in a vehicle.
// call it as [_unit, _animation, _priority] call ACME_fnc_doAnim, which is exactly ACE's own argument order for
// ace_common_fnc_doAnimation. every ACME call site uses this instead of calling ACE directly.
//
// WHY IT EXISTS.
// ACE's doAnimation does not refuse a unit in a vehicle. It handles the case explicitly, at
// ace common/functions/fnc_doAnimation.sqf:37, by broadcasting the move globally instead of to the owner,
// because playMove and playMoveNow have local effects on remote machines inside vehicles. So ACE animates a
// seated unit on purpose, and every ACME call to it did the same.
// Arma's unit animations are authored for a unit standing on terrain. Forcing one on a unit in a cargo seat puts
// the animation and the seat animation of the vehicle in competition for the same skeleton, and the engine
// resolves that badly: units get flung out of seats, welded half in and half out, left in a seat that no longer
// exists, or teleported to the vehicle origin.
// This is not cosmetic. It breaks the airframe for everyone in it.
//
// THE RULE, AND IT HAS NO EXCEPTIONS.
// A unit in a vehicle plays nothing. This covers the casualty and the provider equally, and every pose the addon
// owns: head elevation and semi-Fowler's, supine repositioning, direct pressure, chest inspection, the chest seal
// roll, obtundation, HPMK wrapping, the hold bag crouch, seizures and the stance locks.
// The treatment still runs and only the theatre is cut. A casualty in a helicopter is still elevated, still
// receives the physiology, and simply is not posed for it, because the seat already holds them.
//
// The same test lives in fn_doAnimHeld and fn_animQueue, so a pose that goes through the queue is stopped one
// level higher and never reaches this function.
params ["_unit", ["_animation", ""], ["_priority", 0]];
if (isNull _unit) exitWith {};
if !(missionNamespace getVariable ["ACME_interventionAnimations", true]) exitWith {};
if ([_unit] call ACME_fnc_animBlocked) exitWith {};
[_unit, _animation, _priority] call ace_common_fnc_doAnimation;
