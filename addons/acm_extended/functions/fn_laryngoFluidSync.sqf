/* Reconcile the local airway renderer with the patient owner's exact remaining compartment volume. */
params ["_patient"];
if (isNull _patient) exitWith {};

private _state = [_patient] call ACME_fnc_laryngoFluidState;
private _previous = uiNamespace getVariable ["ACME_laryngo_fluidSeen", []];
if (_state isEqualTo _previous) exitWith {};
uiNamespace setVariable ["ACME_laryngo_fluidSeen", _state];

_state params ["_stamp", "_kind", "_target"];
if (_kind == "" || {_target <= 0}) exitWith {
    uiNamespace setVariable ["ACME_laryngo_fluidKind", ""];
    uiNamespace setVariable ["ACME_laryngo_fluidStage", 0];
    uiNamespace setVariable ["ACME_laryngo_fluidMode", "rest"];
};

private _firstView = count _previous != 3;
private _newEpisode = _firstView || {!((_previous select 0) isEqualTo _stamp)};
private _newVomit = !_firstView && {_kind == "v"}
    && {(_previous select 1) != "v" || {!((_previous select 0) isEqualTo _stamp)}};
private _canEmesis = alive _patient
    && {!(_patient getVariable ["ace_medical_inCardiacArrest", false])}
    && {!(_patient getVariable ["ACME_roc_paralyzed", false])};

private _current = uiNamespace getVariable ["ACME_laryngo_fluidStage", 0];
uiNamespace setVariable ["ACME_laryngo_fluidKind", _kind];
uiNamespace setVariable ["ACME_laryngo_fluidCap", _target];

// The owner ledger is the source of truth after suction. A new live contamination event may visually fill from the
// currently visible remainder up to the NEW additive target, but an observer or reopen can never reconstruct an
// absolute historical volume. If the target shrinks, clamp immediately.
if (_firstView || {!_newEpisode} || {_current > _target}
    || {_kind == "v" && {!_newVomit || {!_canEmesis}}}) then {
    _current = _target;
    uiNamespace setVariable ["ACME_laryngo_fluidStage", _current];
};

uiNamespace setVariable ["ACME_laryngo_fluidMode", if (_current < _target) then {"fill"} else {"rest"}];
uiNamespace setVariable ["ACME_laryngo_fluidFillNext", 0];
uiNamespace setVariable ["ACME_laryngo_fluidPhaseNext", 0];
if (_newVomit && {_canEmesis}) then {
    uiNamespace setVariable ["ACME_laryngo_ejectedThisVomit", false];
};
