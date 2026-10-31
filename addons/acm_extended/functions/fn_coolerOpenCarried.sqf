private _rows=[ACE_player] call ACME_fnc_coolerRows;
if (_rows isEqualTo []) exitWith {["Cooler is waiting for inventory synchronization.",2,ACE_player] call ace_common_fnc_displayTextStructured;};
[(_rows select 0) select 0] call ACME_fnc_coolerOpenDialog;
