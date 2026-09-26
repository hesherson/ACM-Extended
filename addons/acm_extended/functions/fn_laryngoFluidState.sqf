/* Authoritative airway-fluid read.
 *
 * Native ACM obstruction fields are cumulative event counters, not remaining-volume meters. The old implementation
 * multiplied the absolute counter by a stage size and invalidated one shared remaining-volume ledger whenever the
 * counter changed. If a casualty vomited again after partial suction, that reconstructed fluid which had already
 * been removed. Repeated events could therefore make a finite airway look effectively bottomless.
 *
 * Each physical compartment now owns [last native counter observed, remaining visual stages]. A new native event
 * contributes only the DELTA since that ledger was written. Suction debits survive later events, and vomit, blood
 * and secretions cannot refill each other. This function remains read-only; owner-side drain/event transactions
 * persist the ledgers.
 *
 * Return: [event identity, active kind, exact remaining visual stages].
 */
params ["_patient"];
if (isNull _patient) exitWith {[[], "", 0]};

private _vom = (_patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0]) max 0;
private _blood = (_patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0]) max 0;
private _bloodEvent = (_patient getVariable ["ACME_airwayBloodEventSerial", 0]) max 0;
// Older casualties/builds may have no event serial yet. Preserve their current contents without inventing
// additional events; the first owner-side bleed event will establish the serial.
if (_bloodEvent <= 0 && {_blood > 0}) then {_bloodEvent = _blood;};
private _secretions = _patient getVariable ["ACME_laryngo_secretions", []];
private _secretionStage = (_secretions param [1, 0]) max 0 min 4;
private _legacy = +(_patient getVariable ["ACME_laryngo_pool", []]);

private _remainingFor = {
    params ["_ledgerVar", "_active", "_eventSerial", "_perEvent", "_cap", "_kind", "_legacy"];
    if (!_active || {_eventSerial <= 0}) exitWith {0};

    private _ledger = +(_patient getVariable [_ledgerVar, []]);
    private _seen = 0;
    private _remaining = 0;

    if (_ledger isEqualType [] && {count _ledger >= 2}
        && {(_ledger param [0, 0]) isEqualType 0}
        && {(_ledger param [1, 0]) isEqualType 0}) then {
        _seen = (_ledger select 0) max 0;
        _remaining = (_ledger select 1) max 0 min _cap;
    } else {
        // One-release migration path for the old shared [stamp,remaining] ledger. Reading it never mutates state.
        if (_legacy isEqualType [] && {count _legacy == 2}) then {
            private _oldStamp = _legacy param [0, []];
            private _oldRemaining = _legacy param [1, -1];
            if (_oldStamp isEqualType [] && {_oldRemaining isEqualType 0} && {_oldRemaining >= 0}) then {
                private _oldVom = _oldStamp param [0, 0];
                private _oldBlood = _oldStamp param [1, 0];
                private _compatible = (_kind == "v" && {_oldVom > 0} && {_oldBlood == 0})
                    || {_kind == "b" && {_oldBlood > 0} && {_oldVom == 0}};
                if (_compatible) then {
                    _seen = [_oldBlood, _oldVom] select (_kind == "v");
                    _remaining = _oldRemaining max 0 min _cap;
                };
            };
        };
    };

    // With no prior debit ledger, the current native count is the initial physical contents.
    if (_seen <= 0 && {_remaining <= 0}) exitWith {(_eventSerial * _perEvent) min _cap};

    // Native counters increase by event. Add only the newly-created contamination, never the historical total.
    if (_eventSerial > _seen) then {
        _remaining = (_remaining + ((_eventSerial - _seen) * _perEvent)) min _cap;
    };

    // A native clear/reset can only reduce what remains. It can never resurrect an older pool.
    if (_eventSerial < _seen) then {
        _remaining = _remaining min ((_eventSerial * _perEvent) min _cap);
    };

    _remaining max 0 min _cap
};

private _vomitRemaining = ["ACME_laryngo_poolVomit", _vom > 0, _vom, 2, 8, "v", _legacy] call _remainingFor;
private _bloodRemaining = ["ACME_laryngo_poolBlood", _blood > 0, _bloodEvent, 2, 6, "b", _legacy] call _remainingFor;

if (_vom > 0 && {_vomitRemaining > 0}) exitWith {
    [["v", _vom], "v", _vomitRemaining]
};
if (_blood > 0 && {_bloodRemaining > 0}) exitWith {
    [["b", _blood], "b", _bloodRemaining]
};
if (_secretionStage > 0) exitWith {
    [["s", _secretions param [0, ""], _secretionStage], "s", _secretionStage]
};

[[], "", 0]
