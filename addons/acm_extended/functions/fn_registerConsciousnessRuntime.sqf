// These three controllers are player-facing/local-player physiology. Dedicated servers have no interface and
// must not carry idle visual/input PFHs for them.
if (hasInterface) then {
    // obtunded vision and voice run every frame, so the darkness oscillation stays smooth.
    [{call ACME_fnc_obtundedTick}, 0, []] call CBA_fnc_addPerFrameHandler;
    // physiological auto-obtundation evaluates locally owned player units on a slow cadence.
    [{call ACME_fnc_obtundedAuto}, 1.5, []] call CBA_fnc_addPerFrameHandler;
    [{call ACME_fnc_consciousnessBudget}, 1, []] call CBA_fnc_addPerFrameHandler;
    // B391: the confused level below obtundation, and garbled speech for both (ACRE2 Babel)
    [{call ACME_fnc_confusedAuto}, 1.5, []] call CBA_fnc_addPerFrameHandler;
    [{call ACME_fnc_confusedTick}, 0, []] call CBA_fnc_addPerFrameHandler;
    [{call ACME_fnc_conscSpeech}, 0.5, []] call CBA_fnc_addPerFrameHandler;
    // every client prepares Babel when it is first asked; a player joining later gets the JIP copy of the event
    ["ACME_babelEnsure", {call ACME_fnc_babelEnsure;}] call CBA_fnc_addEventHandler;
};

// Shared wrapping audio follows ACE's actual start/end events on every machine.
[] call ACME_fnc_wrapSfxInit;

// Track when a medic is working on a player-patient. This is informational/grace state only. B49 deliberately
// removed the old obtunded treatment hook that forced ACM_rollToBack actions into a locked supine posture. The
// treatment itself may still roll/reposition a casualty when clinically required, but obtundation no longer adds
// any body-position writer of its own.
["ace_treatmentStarted", {
    params ["_medic", "_patient", "_bodyPart", "_classname"];
    if (isPlayer _patient) then {
        [_patient, "careGrace", [missionNamespace getVariable ["ACME_obtunded_careGraceMax", 25]]] call ACME_fnc_ownerDispatch;
    };
}] call CBA_fnc_addEventHandler;

// the debug overlay target follows the casualty this client starts treating. this is local ui state only. it
// does not broadcast and it does not change patient physiology.
if (hasInterface) then {
    ["ace_treatmentStarted", {
        params ["_medic", "_patient"];
        private _me = if (!isNil "ACE_player" && {!isNull ACE_player}) then {ACE_player} else {player};
        if (!isNull _patient && {!isNull _medic} && {_medic isEqualTo _me}) then {
            missionNamespace setVariable ["ACME_debug_target", _patient];
            missionNamespace setVariable ["ACME_debug_lastTreatmentTarget", _patient];
            missionNamespace setVariable ["ACME_tbi_debugTarget", _patient];
        };
    }] call CBA_fnc_addEventHandler;
};
{
    [_x, {
        params ["_medic", "_patient"];
        if (isPlayer _patient) then {[_patient, "careGrace", [1]] call ACME_fnc_ownerDispatch;};  // small owner-local tail
    }] call CBA_fnc_addEventHandler;
} forEach ["ace_treatmentSucceded", "ace_treatmentFailed"];
