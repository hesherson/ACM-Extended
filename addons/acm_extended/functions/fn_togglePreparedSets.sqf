// the "Prepared IV sets" button in the transfusion menu. it toggles the right-hand fluid area between the normal
// available-bags list, 86005, meaning the loose and cooler blood and saline, and the stored prepared iv sets of the
// provider, shown in the overlay list 86145.
// the actual show and hide swap, the overlay population and the spike button relabel to "Hang Set" are handled in
// fn_updatetransfusioncontrols off the same ACME_preparedListMode flag, and this simply flips it and forces a
// one-shot re-sync so the switch is immediate.
private _display = findDisplay 86000;
if (isNull _display) exitWith {};

// A successful spike opens the prepared view explicitly. Manual presses still
// toggle; repeated completion refreshes must not toggle it back to Loose Bags.
private _requested = _this param [0, ""];
private _on = if (_requested isEqualType true) then {_requested} else {
    !(uiNamespace getVariable ["ACME_preparedListMode", false])
};
uiNamespace setVariable ["ACME_preparedListMode", _on];

// leaving a half-finished y build armed while flipping the list is confusing, so clear any pending pairing.
if (_on) then {
    missionNamespace setVariable ["ACME_yPending", ""];
    missionNamespace setVariable ["ACME_yPendingData", ""];
    missionNamespace setVariable ["ACME_yPendingSaline", ""];
    missionNamespace setVariable ["ACME_yPendingSalineData", ""];
};

// force the list sync in fn_updatetransfusioncontrols to rebuild our rows on the next pass. it early-outs when the
// signature is unchanged, and this guarantees the mode switch takes effect at once.
uiNamespace setVariable ["ACME_coolerRowSig", "__force__"];
uiNamespace setVariable ["ACME_preparedRowSig", "__force__"];
_display setVariable ["ACME_txActivePane", ["inventory", "prepared"] select _on];
call ACME_fnc_transfusionFilterInventory;
