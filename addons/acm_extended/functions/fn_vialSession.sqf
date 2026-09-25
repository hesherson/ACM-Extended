/* B25: local UI binding between a draw session and physical vials.
   This deliberately does NOT consume inventory. It only limits how much source solution a currently open syringe
   may stage before Save/Inject commits through the existing vial ledger.

   Modes:
     ["select", med, reservedMl, display]  - bind one physical vial; if the current bound vial is exhausted and
                                             the user deliberately clicks the same medication again, bind ONE more.
     ["limit",  med, reservedMl, display]  - return total mL of this medication intentionally unlocked for this syringe.
     ["preview",med, reservedMl, display]  - return [currentVialMl, vialCountRemaining, totalMlRemaining, unlockedMl].
     ["clear",  "", 0, display]           - forget all staged vial bindings for the dialog.

   A partial opened vial is always used before an unopened vial. No automatic rollover occurs. */
params [
    ["_mode", "limit", [""]],
    ["_med", "", [""]],
    ["_reservedMl", 0, [0]],
    ["_display", displayNull, [displayNull]]
];
if (isNull _display) then {_display = findDisplay 84000;};
if (isNull _display) exitWith {if (_mode == "preview") then {[0,0,0,0]} else {0}};
if (_mode == "clear") exitWith {
    _display setVariable ["ACME_SK_VialSessions", createHashMap];
    _display setVariable ["ACME_SK_VialHolder",objNull];
    uiNamespace setVariable ["ACME_SK_VialHolder",objNull];
    0
};
if (_med == "") exitWith {if (_mode == "preview") then {[0,0,0,0]} else {0}};

private _holder = [ACE_player] call ACME_fnc_vialHolder;
if (isNull _holder) exitWith {if (_mode == "preview") then {[0,0,0,0]} else {0}};
private _boundHolder = _display getVariable ["ACME_SK_VialHolder",objNull];
if (!isNull _boundHolder && {!(_holder isEqualTo _boundHolder)}) exitWith {if (_mode == "preview") then {[0,0,0,0]} else {0}};
_display setVariable ["ACME_SK_VialHolder",_holder];
// Unload may have retired findDisplay before its autosave runs. Preserve the
// donor binding through that callback, then skClose clears it after settlement.
uiNamespace setVariable ["ACME_SK_VialHolder",_holder];
private _cap = [_med] call ACME_fnc_vialCapacity;
if (_cap <= 0) exitWith {if (_mode == "preview") then {[0,0,0,0]} else {0}};
private _vialClass = [_med] call ACME_fnc_vialClass;
// B48: if the native medication row came from a physical alias/class, bind the vial session to that exact
// inventory classname instead of reconstructing a classname from the medication key.
private _rowsB48 = _display getVariable ["ACME_SK_MedicationRows", []];
private _rowB48 = _rowsB48 findIf {(_x param [1, ""]) == _med};
if (_rowB48 >= 0) then {
    private _physicalClass = (_rowsB48 select _rowB48) param [3, ""];
    if (_physicalClass != "") then {_vialClass = _physicalClass;};
};
private _openMap = _holder getVariable ["ACME_infusion_openVials", createHashMap];
private _openNow = ((_openMap getOrDefault [_med, 0]) max 0) min _cap;
// B73: 0.01 mL cannot be usefully manipulated at the UI's 0.01 mL resolution. Discard that remnant rather than
// forcing a new syringe session to bind a nearly-empty ghost vial before the next real vial can be selected.
private _discardResidual = missionNamespace getVariable ["ACME_vialDiscardResidualMl",0.0105];
if (_openNow > 0 && {_openNow <= _discardResidual}) then {
    _openMap set [_med,0];
    [_holder, _openMap] call ACME_fnc_openVialStoreCommit;
    _openNow = 0;
};
private _sealedNow = [_holder, _vialClass] call ACME_fnc_vialItemCount;
if (_med == "EpinephrineCardiac") then {_sealedNow = _sealedNow + ([_holder, "ACM_Vial_EpinephrineCardiac"] call ACME_fnc_vialItemCount);};
private _sessions = _display getVariable ["ACME_SK_VialSessions", createHashMap];
private _entry = _sessions getOrDefault [_med, []];

// Entry is [startingOpenMl, startingSealedCount, selectedSealedCount, unlockedMl, vialCapacityMl].
if (_entry isEqualTo []) then {
    private _selSealed = if (_openNow > 0.000001) then {0} else {[0,1] select (_sealedNow > 0)};
    private _unlocked = if (_openNow > 0.000001) then {_openNow} else {if (_sealedNow > 0) then {_cap} else {0}};
    _entry = [_openNow, _sealedNow, _selSealed, _unlocked, _cap];
    _sessions set [_med, _entry];
    _display setVariable ["ACME_SK_VialSessions", _sessions];
};
_entry params ["_startOpen", "_startSealed", "_selectedSealed", "_unlocked", "_entryCap"];
_reservedMl = (_reservedMl max 0) min (_startOpen + _startSealed * _entryCap);

if (_mode == "select") then {
    // Another vial is opened for THIS syringe only after the current bound vial is effectively exhausted and the
    // provider deliberately clicks the medication again. B73 treats <=0.01 mL as discardable residue: if endpoint
    // rounding ever strands that amount, selecting the next vial abandons it rather than trapping the workflow.
    private _boundRemainder = (_unlocked - _reservedMl) max 0;
    if (_boundRemainder <= (_discardResidual + 0.000001) && {_selectedSealed < _startSealed}) then {
        _selectedSealed = _selectedSealed + 1;
        // If there was a micro-remnant, do NOT grant it again. The new usable ceiling starts at the amount already
        // staged plus one fresh vial. fn_vialTake applies the same discard threshold at commit, preserving mass.
        _unlocked = (_reservedMl + _entryCap) min (_startOpen + _startSealed * _entryCap);
        _entry set [2, _selectedSealed];
        _entry set [3, _unlocked];
        _sessions set [_med, _entry];
        _display setVariable ["ACME_SK_VialSessions", _sessions];
    };
    _unlocked
} else {
    if (_mode == "preview") then {
        private _totalStart = _startOpen + (_startSealed * _entryCap);
        // Any difference between nominal selected-vial capacity and the unlocked ceiling is deliberately discarded
        // micro-residue from a prior vial. Count it as gone so the UI immediately advances to the fresh vial.
        private _selectedCapacity = _startOpen + (_selectedSealed * _entryCap);
        private _discardedSession = (_selectedCapacity - _unlocked) max 0;
        private _totalLeft = (_totalStart - _reservedMl - _discardedSession) max 0;
        private _vialCountStart = _startSealed + (if (_startOpen > 0.000001) then {1} else {0});
        private _exhausted = 0;
        private _r = (_reservedMl + _discardedSession) min _totalStart;
        private _cur = 0;

        if (_startOpen > 0.000001) then {
            if (_r < _startOpen - 0.0005) then {
                _cur = _startOpen - _r;
                _r = 0;
            } else {
                _r = (_r - _startOpen) max 0;
                _exhausted = _exhausted + 1;
            };
        };

        if (_cur <= 0.000001) then {
            private _sealedConsumedFull = floor ((_r + 0.000001) / _entryCap);
            _exhausted = _exhausted + (_sealedConsumedFull min _startSealed);
            private _rem = _r - (_sealedConsumedFull * _entryCap);
            if (_rem > 0.0005 && {_sealedConsumedFull < _selectedSealed}) then {
                _cur = (_entryCap - _rem) max 0;
            } else {
                // Exact exhaustion must remain 0.00 until the user explicitly selects another vial.
                if (_r <= 0.0005 && {_startOpen <= 0.000001} && {_selectedSealed > 0}) then {_cur = _entryCap;};
                if (_r > 0.0005 && {_rem <= 0.0005} && {_sealedConsumedFull < _selectedSealed}) then {_cur = _entryCap;};
            };
        };

        // If the partial vial was exhausted and the user manually unlocked a sealed vial but has not drawn from it,
        // show that newly selected vial at full capacity.
        if (_cur <= 0.000001 && {_reservedMl < _unlocked - 0.0005}) then {
            _cur = _entryCap min (_unlocked - _reservedMl);
        };

        private _vialsLeft = (_vialCountStart - _exhausted) max 0;
        [_cur max 0 min _entryCap, _vialsLeft, _totalLeft, _unlocked]
    } else {
        _unlocked
    };
};
