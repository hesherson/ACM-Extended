params ["_owner", "_kind", "_sid"];
(([_owner,_kind] call ACME_fnc_inventoryLedgerRows) findIf {(_x param [0, ""]) == _sid}) >= 0
