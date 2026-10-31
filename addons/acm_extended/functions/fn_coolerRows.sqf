/* Physical native magazine possession selects one independent cooler instance. */
params [["_owner",ACE_player]];
if (isNull _owner) exitWith {[]};
([_owner,"cooler"] call ACME_fnc_inventoryLedgerRows) apply {
    _x params ["_sid","_state"];
    [_sid,[_state select 0,_state select 1,(_state select 2) apply {+_x},_state select 3]]
}
