/* Pure read: [native/event identity, fluid kind, remaining visual stages].
   A matching owner ledger preserves partial suction across providers and reopening.
   A new native obstruction invalidates the old ledger without suppressing ACM causes. */
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
// Secretions are their own compartment. New secretion behind blood/vomit must not
// invalidate that active compartment's partial suction ledger or refill its volume.
if (_kind == "" && {_secretionStage > 0}) then {
    _kind = "s";
    _target = _secretionStage;
    _stamp pushBack (_secretions param [0, ""]);
};
if (_kind == "v" && {count _emesis == 3} && {(_emesis select 1) == _vom}) then {
    _target = (_emesis select 2) max 1 min 8;
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
