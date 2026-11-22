// Direct attachment avoids chaining the casualty through a moving litter.
params ["_litter"];
// A litter dragged with ACME's drag hangs on the rescuer and its place on them changes all the time: the casualty
// stays attached to the litter itself and goes where it goes.
if (!isNull (_litter getVariable ["acme_drag_by", objNull])) exitWith {_litter};
private _root = attachedTo _litter;
if (isNull _root) exitWith {_litter};
_root
