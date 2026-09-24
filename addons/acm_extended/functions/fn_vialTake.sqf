/* Debit exact source-solution mL from a background partial-vial ledger.
   The first partial draw consumes the physical vial item and leaves its unused solution in ACME_infusion_openVials.
   Multiple opened vials of the same medication may be pooled invisibly; total volume is conserved exactly. */
params [["_holder", objNull, [objNull]], ["_med", "", [""]], ["_ml", 0, [0]], ["_provider", objNull, [objNull]]];
if (isNull _holder || {_med == ""} || {_ml <= 0} || {!finite _ml}) exitWith {false};
// Callers with a captured provider retain that provider across player switching/refund callbacks.
// Legacy three-argument UI callers still use the currently controlled provider.
if (isNull _provider && {hasInterface}) then {_provider = ACE_player;};
private _leaseValid = true;
if (hasInterface && {!isNull _provider} && {_holder isNotEqualTo _provider}) then {
    private _lease = missionNamespace getVariable ["ACME_vialLeaseAccepted", []];
    _leaseValid = _lease isEqualType [] && {count _lease >= 3}
        && {(_lease param [0,objNull]) isEqualTo _holder}
        && {(_lease param [1,""]) != ""}
        && {(_lease param [2,0]) > serverTime};
};
// Exit the function, not just the nested shared-source branch, before any inventory or ledger write.
if (!_leaseValid) exitWith {false};
private _cap = [_med] call ACME_fnc_vialCapacity;
if (_cap <= 0) exitWith {false};
private _vial = [_med] call ACME_fnc_vialClass;
private _legacyVial = if (_med == "EpinephrineCardiac") then {"ACM_Vial_EpinephrineCardiac"} else {""};
private _map = _holder getVariable ["ACME_infusion_openVials", createHashMap];
private _open = (_map getOrDefault [_med, 0]) max 0;
private _sealedPrimary = [_holder, _vial] call ACME_fnc_vialItemCount;
private _sealedLegacy = if (_legacyVial != "") then {[_holder, _legacyVial] call ACME_fnc_vialItemCount} else {0};
private _sealed = _sealedPrimary + _sealedLegacy;
private _available = _open + (_sealed max 0) * _cap;
if (_available + 0.000001 < _ml) exitWith {false};
private _needed = ceil (((_ml - _open) max 0) / _cap);
if (_needed > _sealed) exitWith {false};
for "_i" from 1 to _needed do {
    private _consumeClass = _vial;
    if (([_holder, _vial] call ACME_fnc_vialItemCount) < 1 && {_legacyVial != ""} && {([_holder, _legacyVial] call ACME_fnc_vialItemCount) > 0}) then {_consumeClass = _legacyVial;};
    if (_holder isKindOf "CAManBase") then {[_holder, _consumeClass] call ACME_fnc_itemTake;} else {_holder addItemCargoGlobal [_consumeClass, -1];};
};
private _left = (_open + _needed * _cap - _ml) max 0;
private _discardResidual = missionNamespace getVariable ["ACME_vialDiscardResidualMl",0.0105];
if (_left > 0 && {_left <= _discardResidual}) then {_left = 0;};
_map set [_med, _left];
[_holder, _map] call ACME_fnc_openVialStoreCommit;
true
