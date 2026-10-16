// Stow/remove the HPMK from prepped, wrapped or exposed state and recover the reusable kit.
// Patient state is mutated only by the patient owner. Inventory recovery is targeted to the receiver's owner.
// _automatic is used by Get Up/mobile-state cleanup; manual treatment already plays its removal SFX in callbackStart.
// The ACE callback's third argument is bodyPart; only internal cleanup callers pass the automatic flag.
private _entryArgs = if ((_this param [2, false]) isEqualType "") then {_this select [0, 2]} else {_this};
_entryArgs params [
    ["_medic", objNull, [objNull]],
    ["_patient", objNull, [objNull]],
    ["_automatic", false, [false]]
];
if (isNull _patient) exitWith {false};
if (!local _patient) exitWith {
    ["ACME_ownerCommand", [_patient, "hpmkRemove", [_medic, _patient, _automatic]], _patient] call CBA_fnc_targetEvent;
    true
};

private _state = _patient getVariable ["ACME_hpmk_state", ""];
if (_state == "") exitWith {false};

// Explicit callers, especially Get Up, choose the receiver. Automatic fallback transitions use the provider whose
// inventory supplied the kit, then the casualty as a final no-loss fallback.
private _receiver = _medic;
if (isNull _receiver) then { _receiver = _patient getVariable ["ACME_hpmk_provider", objNull]; };
if (isNull _receiver) then { _receiver = _patient; };

_patient setVariable ["ACME_hpmk_returnPending", true, true];
[_patient, "", true, false] call ACME_fnc_hpmkStateCommit;
_patient setVariable ["ACME_hpmk_provider", objNull, true];
if (!isNil "ACME_hpmk_activePatients") then {
    ACME_hpmk_activePatients = ACME_hpmk_activePatients - [_patient];
};

["ACME_hpmkReturnItem", [_receiver], _receiver] call CBA_fnc_targetEvent;

if (_automatic) then {
    // Keep the transaction guard up briefly while the replicated empty state reaches the server-side blanket watcher.
    // This prevents a stale wrapped snapshot from also spawning a dropped HPMK after Get Up already returned the item.
    [{
        params ["_p"];
        if (!isNull _p) then { _p setVariable ["ACME_hpmk_returnPending", false, true]; };
    }, [_patient], 1] call CBA_fnc_waitAndExecute;
    private _near = allPlayers select {alive _x && {(_x distance _patient) <= 80}}; if !(_near isEqualTo []) then {["ACME_worldSfx", [_patient, "ACM_HPMK_Remove"], _near] call CBA_fnc_targetEvent;};
} else {
    _patient setVariable ["ACME_hpmk_returnPending", false, true];
    [(["HPMK stowed.", "HPMK removed."] select (_state in ["wrapped", "exposed"])), 2.5, _medic] call ACME_fnc_netNotice;
};

if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    private _entry = if (_automatic) then {"NAR HPMK removed automatically on Get Up/mobile transition (recovered)"} else {"NAR HPMK removed (recovered)"};
    [_patient, "activity", _entry, []] call ace_medical_treatment_fnc_addToLog;
};
true
