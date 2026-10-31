/* Restore only gear removed by head elevation. Execute on the patient's owner.
   Use the vest's loadout entry to retain partial magazines and weapon attachments. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!local _patient}) exitWith {false};

// A carrier borrowed from persistent manual custody must never be re-worn merely because Semi-Fowler ends.
// Return only the head-elevation view of the custody and park the same prop above the casualty again.
if (_patient getVariable ["ACME_headElev_manualCarrierBorrowed", false]) exitWith {
    [_patient, "release"] call ACME_fnc_manualPlateCarrierHeadElevSupport;
};
if (!(_patient getVariable ["ACME_headElev_vestRemoved", false])
    && {(_patient getVariable ["ACME_headElev_propVest", ""]) == ""}
    && {count (_patient getVariable ["ACME_headElev_vestLoadout", []]) == 0}) exitWith {true};
private _restored = false;
isNil {
    private _removed = _patient getVariable ["ACME_headElev_vestRemoved", false];
    private _saved = _patient getVariable ["ACME_headElev_vestLoadout", []];
    private _legacy = _patient getVariable ["ACME_headElev_propVest", ""];
    private _hasRecord = !isNil {_patient getVariable "ACME_headElev_vestRemoved"};
    // Older sessions retained item classes only. Never append them to a worn vest.
    if (!_hasRecord && {_legacy != ""} && {vest _patient == ""}) then {
        _saved = [_legacy, (_patient getVariable ["ACME_headElev_propVestItems", []]) apply {[_x, 1]}];
        _removed = true;
    };
    if (_removed && {count _saved == 2} && {(_saved param [0, "", [""]]) != ""}) then {
        if (vest _patient == "") then {
            _restored = [_patient, _saved, "ACME_headElev_vestLoadout"] call ACME_fnc_carrierInventoryRestore;
        };
        // A different worn carrier, or an engine refusal, keeps the custody record.
    } else {
        _restored = !_removed;
    };
    if (_restored) then {
        _patient setVariable ["ACME_headElev_vestRemoved", false, true];
        _patient setVariable ["ACME_headElev_vestLoadout", [], true];
        _patient setVariable ["ACME_headElev_propVest", "", true];
        _patient setVariable ["ACME_headElev_propVestItems", [], true];
    };
};
_restored
