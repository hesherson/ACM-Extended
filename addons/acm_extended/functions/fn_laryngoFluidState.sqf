/* Pure read: [native/event identity, fluid kind, remaining visual stages].
   A matching owner ledger preserves partial suction across providers and reopening.
   New native events add only their new volume to the retained suction remainder. */
params ["_patient"];
private _vom = _patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0];
private _blood = _patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0];
private _emesis = _patient getVariable ["ACME_laryngo_emesis", []];
private _secretions = _patient getVariable ["ACME_laryngo_secretions", []];
private _secretionStage = (_secretions param [1, 0]) max 0 min 4;
// Identity belongs to the visible compartment. Blood deposited behind existing
// vomit must not invalidate a partial vomit debit and restore the original volume.
private _stamp = if (_vom > 0) then {[_vom, 0, _emesis]} else {[0, _blood, []]};
private _kind = if (_vom > 0) then {"v"} else {if (_blood > 0) then {"b"} else {""}};
private _target = if (_vom > 0) then {(_vom * 2) min 8} else {(_blood * 2) min 6};
// A later native blood increment adds ONLY new fluid, not the amount already
// suctioned. Persist the blood compartment independently of visible vomit/secretions.
if (_kind == "b") then {
    private _remainingBlood = _patient getVariable ["ACME_laryngo_bloodRemaining", []];
    if (count _remainingBlood == 2 && {(_remainingBlood select 0) <= _blood}) then {
        _target = ((_remainingBlood select 1) + 2 * (_blood - (_remainingBlood select 0))) max 0 min 6;
    };
};
// Vomit needs a separate debit ledger too. Native event counters are not a
// remaining-volume meter: incrementing one must never restore fluid already removed.
// The airway writer captures the exact previous contents before changing its count,
// including an explicit procedural episode's already-additive stage.
if (_kind == "v") then {
    private _remainingVomit = _patient getVariable ["ACME_laryngo_vomitRemaining", []];
    private _savedEmesis = [];
    private _hasLedger = _remainingVomit isEqualType [] && {count _remainingVomit == 3}
        && {(_remainingVomit select 0) isEqualType 0}
        && {(_remainingVomit select 1) isEqualType 0}
        && {(_remainingVomit select 2) isEqualType []};
    if (_hasLedger) then {
        private _seen = (_remainingVomit select 0) max 0;
        private _remaining = (_remainingVomit select 1) max 0 min 8;
        _savedEmesis = _remainingVomit select 2;
        _target = if (_vom >= _seen) then {
            (_remaining + 2 * (_vom - _seen)) min 8
        } else {
            _remaining min ((_vom * 2) max 0)
        };
    };
    // A clinical restore rebinds the receipt's epoch, not its event identity.
    // A zero-volume tombstone remembers the old receipt across clear/restart,
    // where the native count may legitimately reuse the same value.
    private _identity = {
        params ["_event"];
        if (count _event < 3) exitWith {[]};
        [_event select 0, _event select 1, _event select 2, _event param [4, 0]]
    };
    private _newExplicit = !_hasLedger
        || {!(([_emesis] call _identity) isEqualTo ([_savedEmesis] call _identity))};
    if (_newExplicit && {count _emesis in [3,5]} && {(_emesis select 1) == _vom}
        && {!((_emesis select 0) isEqualType "") || {((_emesis select 0) find "ACME-native-vomit:") != 0}}) then {
        _target = (_emesis select 2) max 1 min 8;
    };
};
// Secretions are their own compartment. New secretion behind blood/vomit must not
// invalidate that active compartment's partial suction ledger or refill its volume.
if (_kind == "" && {_secretionStage > 0}) then {
    _kind = "s";
    _target = _secretionStage;
    _stamp pushBack (_secretions param [0, ""]);
};
private _pool = +(_patient getVariable ["ACME_laryngo_pool", []]);
// Normalize a B31 three-field ledger on read without rewriting saved/native state.
if (count _pool == 2 && {count (_pool select 0) == 3}) then {
    private _oldStamp = +(_pool select 0);
    if (_kind == "v") then {_oldStamp set [1, 0];};
    if (_kind == "b" && {(_oldStamp select 0) == 0}) then {_oldStamp set [2, []];};
    _pool set [0, _oldStamp];
};
if (count _pool == 2 && {(_pool select 0) isEqualTo _stamp}) then {
    _target = (_pool select 1) max 0 min _target;
};
if (_kind == "") then {_target = 0;};
[_stamp, _kind, _target]
