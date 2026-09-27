params ["_uid", "_ok"];
private _pending = missionNamespace getVariable ["ACME_infusionPending", createHashMap];
private _row = _pending getOrDefault [_uid, []];
if (_row isEqualTo [] || {_row select 4}) exitWith {};
_row set [4, true];
if ((missionNamespace getVariable ["ACME_infusion_pendingInject", ""]) == _uid) then {missionNamespace setVariable ["ACME_infusion_pendingInject", ""];};
if (!_ok) then {
    [_row select 2] call ACME_fnc_infusionRefundSupplies;
    [(_row select 2) select 0, "Injection was not accepted because the bag or access changed. Supplies returned."] call ACME_fnc_clinicalNotice;
} else {[_row select 2,false] call ACME_fnc_infusionRefundSupplies;};
[] call ACME_fnc_infusionRefreshTally;
