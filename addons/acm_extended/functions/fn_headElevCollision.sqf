// Turn the physics collision of a casualty off while a positioning animation plays, and turn it on again after.
// Call it as [_patient, false] call ACME_fnc_headElevCollision to turn collision off, and [_patient, true] to
// restore the casualty's ordinary mass.
//
// B202: collision restoration is deferred by one frame and generation-checked. Root-motion patient animations can
// finish with the model still intersecting terrain for the remainder of the current simulation frame. Restoring full
// PhysX mass before the neutral lying pose has settled can turn that overlap into a real impact, which ACE then
// records as blunt wounds/fractures. A newer movement request invalidates the pending restoration automatically.
params [["_patient", objNull, [objNull]], ["_enabled", true, [true]]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {[_patient, "headElevCollision", [_patient, _enabled]] call ACME_fnc_ownerDispatch;};
// Restore is always allowed to release collision custody acquired before a setting change. A disabled
// presentation request must not invalidate an already queued restore by advancing its collision epoch.
if (!_enabled && {!(missionNamespace getVariable ["ACME_interventionAnimations", true])}) exitWith {};

private _epoch = 1 + (_patient getVariable ["ACME_headElev_collisionEpoch", 0]);
_patient setVariable ["ACME_headElev_collisionEpoch", _epoch, false];

if (_enabled) exitWith {
    private _mass = _patient getVariable ["ACME_headElev_mass", -1];
    if (!(_mass isEqualType 0) || {_mass <= 0}) exitWith {};

    [{
        params ["_p", "_epoch"];
        if (isNull _p || {!local _p}) exitWith {};
        if ((_p getVariable ["ACME_headElev_collisionEpoch", -1]) != _epoch) exitWith {};

        private _mass = _p getVariable ["ACME_headElev_mass", -1];
        if (!(_mass isEqualType 0) || {_mass <= 0}) exitWith {};
        ["ace_common_setMass", [_p, _mass]] call CBA_fnc_globalEvent;
        _p setVariable ["ACME_headElev_mass", nil, true];
    }, [_patient, _epoch]] call CBA_fnc_execNextFrame;
};

// A second disable invalidates a queued restore but must never record the already-relaxed mass as the original.
if ((_patient getVariable ["ACME_headElev_mass", -1]) > 0) exitWith {};
private _mass = getMass _patient;
if (_mass <= 1) exitWith {};
_patient setVariable ["ACME_headElev_mass", _mass, true];
["ace_common_setMass", [_patient, 1e-12]] call CBA_fnc_globalEvent;
