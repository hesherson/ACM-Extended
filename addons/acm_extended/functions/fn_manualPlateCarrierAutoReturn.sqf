/* Stable B183: force a manually removed carrier back onto a casualty that wakes, moves or is transported. */
params [
    ["_patient", objNull, [objNull]],
    ["_reason", "state", [""]]
];

if (isNull _patient) exitWith {false};
if (!local _patient) exitWith {
    [_patient, "manualPlateCarrierAutoReturn", [_patient, _reason]] call ACME_fnc_ownerDispatch;
    true
};

private _state = _patient getVariable ["ACME_manualPlateCarrierState", ""];
private _lease = _patient getVariable ["ACME_manualPlateCarrierLease", ""];
if (_state == "" && {_lease == ""}) exitWith {false};

private _provider = _patient getVariable ["ACME_manualPlateCarrierProvider", objNull];

// If Semi-Fowler is borrowing this manual carrier, retire that posture first without playing a visible lowering
// animation. The head-elevation vest restore hook only releases the borrowed support back to manual custody;
// the forced chest-access restore below then returns it to the casualty.
if (_patient getVariable ["ACME_headElev_manualCarrierBorrowed", false]) then {
    if (_patient getVariable ["ACME_headElevated", false]) then {
        [objNull, _patient, true, true] call ACME_fnc_headElevateStop;
    } else {
        [_patient, "release"] call ACME_fnc_manualPlateCarrierHeadElevSupport;
    };
};

// Retire the persistent manual lease without disturbing unrelated chest-access leases.
private _leases = _patient getVariable ["ACME_chestAccess_leases", createHashMap];
if !(_leases isEqualType createHashMap) then {_leases = createHashMap;};
if (_lease != "") then {_leases deleteAt _lease;};
_patient setVariable ["ACME_chestAccess_leases", _leases, true];
if ((_patient getVariable ["ACME_chestAccess_readyLease", ""]) == _lease) then {
    _patient setVariable ["ACME_chestAccess_readyLease", "", true];
};

// Stop only the provider episode created by this manual lease.
if (!isNull _provider && {_lease != ""}) then {
    [_provider, "chestAccessVestProvider", [_provider, _patient, "manualstop", false, "", _lease]]
        call ACME_fnc_ownerDispatch;
};

// A wake/transport may happen in the middle of removal or animated replacement. Cancel that exact patient
// choreography before forcing the carrier back on. This never clears a foreign patient animation lease.
private _busy = _patient getVariable ["ACME_chestAccess_vestBusy", ""];
if (_busy != "") then {
    if ((_patient getVariable ["ACME_chestAccess_removeSpeedToken", ""]) == _busy) then {
        _patient setVariable ["ACME_chestAccess_removeSpeedToken", "", false];
        [_patient, _busy] call ACME_fnc_patientAnimRelease;
    };
    if ((_patient getVariable ["ACME_chestAccess_restoreSpeedToken", ""]) == _busy) then {
        _patient setVariable ["ACME_chestAccess_restoreSpeedToken", "", false];
        [_patient, _busy] call ACME_fnc_patientAnimRelease;
    };

    private _lock = _patient getVariable ["ACME_patientAnimLock", []];
    if ((_lock param [0, ""]) == _busy
        && {(_lock param [1, ""]) in ["chest-access-vest", "chest-access-vest-restore"]}) then {
        _patient setVariable ["ACME_patientAnimLock", [], true];
    };

    _patient setVariable ["ACME_chestAccess_vestBusy", "", false];
    [_patient, true] call ACME_fnc_headElevCollision;
};

// Force means transport/wake correctness outranks reverse theatre. The restore function returns the exact
// saved vest slot, deletes the parked prop and clears temporary chest-access custody in this same owner frame.
private _saved = +(_patient getVariable ["ACME_chestAccess_vestLoadout", []]);
private _hadCustody = (count _saved) == 2;
if (_hadCustody) then {
    [_patient, true, _provider, "access", true] call ACME_fnc_chestAccessVestRestore;
};

_patient setVariable ["ACME_manualPlateCarrierState", "", true];
["ACME_manualPlateCarrierTrack", [_patient]] call CBA_fnc_localEvent;
_patient setVariable ["ACME_manualPlateCarrierLease", "", true];
_patient setVariable ["ACME_manualPlateCarrierProvider", objNull, true];
_patient setVariable ["ACME_manualPlateCarrierOriginASL", [], true];
_patient setVariable ["ACME_manualPlateCarrierRemoved", false, true];

if (_hadCustody || {(vest _patient) != ""}) then {
    [_patient, "activity", format ["Plate carrier automatically returned (%1)", _reason], []]
        call ace_medical_treatment_fnc_addToLog;
};

if (!isNull _provider) then {
    ["ACME_manualPlateCarrierAck", [_patient, true, true], _provider] call CBA_fnc_targetEvent;
};
true
