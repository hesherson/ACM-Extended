/* Reserve a whole preparation atomically on the calling client. A late missing item
   restores all earlier components to their exact donors. Each entry is an item class
   or [class, personalOnly] for a used/cooled bag already materialized in medic inventory. */
params ["_medic", "_patient", "_requirements"];
if (_requirements isEqualTo []) exitWith {[]};
private _receipts = [];
isNil {
    private _ok = true;
    {
        private _item = _x;
        private _personalOnly = false;
        if (_x isEqualType []) then {_item = _x param [0, ""]; _personalOnly = _x param [1, false];};
        private _receipt = [_medic, _patient, [_item], _personalOnly] call ACME_fnc_treatmentSupplyTake;
        if (_receipt isEqualTo []) exitWith {_ok = false;};
        _receipts pushBack _receipt;
    } forEach _requirements;
    if (!_ok) then {
        {[_x] call ACME_fnc_treatmentSupplyRefund;} forEach _receipts;
        _receipts = [];
    };
    true
};
_receipts
