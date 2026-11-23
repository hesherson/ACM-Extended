/*
 * Twice a second, on every machine: every casualty who is strapped into a litter is turned the way his litter
 * says he lies (acme_sked_attach: [offset, direction, up] in the litter's axes, public).
 *
 * The turn of an attached unit is set where the unit is local and does not reliably reach other machines; a
 * machine that missed it shows the casualty as he lay before. An attached unit that is not local does take a
 * turn that is set here, and setting the same turn again changes nothing, so every machine simply sets it.
 * A casualty who hangs on what his litter hangs on (a rescuer who carries it) is turned by the same rule as
 * fn_reattach.sqf uses. The pose he lies in is kept the same way (see below).
 */
// (acme_sked_orientKeep false: off, for the tests that measure what the engine does by itself)
if !(missionNamespace getVariable ["acme_sked_orientKeep", true]) exitWith {};
{
    private _litter = _x;
    private _patient = _litter getVariable ["acme_sked_patient", objNull];
    (_litter getVariable ["acme_sked_attach", []]) params [["_off", []], ["_dir", [0, 1, 0]], ["_up", [0, 0, 1]]];
    if (!isNull _patient && {_off isNotEqualTo []} && {isNull objectParent _patient}
        && {!(_patient getVariable ["acme_sked_loading", false])}) then {
        // The pose is an animation, and a machine that joins in progress does not get it: it shows him in the
        // sprawl of an unconscious man, half out of a SKED or sunk into a Talon's deck, while it reports the
        // litter pose as his animation (seen in the game 2026-11-18, run mpedge379e). So the name cannot be
        // trusted: the first three times this machine sees him on this litter (at once, 1.5 s and 4.5 s later)
        // it puts him into the pose itself, and again whenever the name is another. For this machine only;
        // where he is local the pose guard keeps it (fn_poseGuard.sqf).
        // B393: not while a provider's animation lease holds his body (his owner plays that animation everywhere)
        if (alive _patient && {!local _patient} && {isNil "ACME_fnc_patientAnimHeld" || {!([_patient] call ACME_fnc_patientAnimHeld)}}) then {
            private _pose = [_patient, _litter] call acme_sked_fnc_patientPose;
            (_patient getVariable ["acme_sked_poseSet", [objNull, 0, 0]]) params ["_for", "_times", "_next"];
            if (_for isNotEqualTo _litter) then {_times = 0; _next = 0;};
            if ((toLowerANSI animationState _patient) != (toLowerANSI _pose) || {_times < 3 && {diag_tickTime >= _next}}) then {
                _patient switchMove _pose;
                _patient setVariable ["acme_sked_poseSet", [_litter, _times + 1, diag_tickTime + ([1.5, 3, 6] param [_times, 6])]];
            };
        };
        private _root = attachedTo _patient;
        if (_root isEqualTo _litter) then {
            _patient setVectorDirAndUp [_dir, _up];
        } else {
            if (!isNull _root && {(attachedTo _litter) isEqualTo _root}) then {
                _patient setVectorDirAndUp [
                    _root vectorWorldToModelVisual (_litter vectorModelToWorldVisual _dir),
                    _root vectorWorldToModelVisual (_litter vectorModelToWorldVisual _up)
                ];
            };
        };
    };
} forEach (entities [["ACME_SKED_Wrapped"], [], false, true]);
