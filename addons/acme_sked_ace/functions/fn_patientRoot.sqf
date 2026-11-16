// Direct attachment avoids chaining the casualty through a moving litter.
params ["_litter"];
private _root = attachedTo _litter;
if (isNull _root) exitWith {_litter};
_root
