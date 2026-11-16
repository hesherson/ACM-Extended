// Read-only query for mission scripts: [available rescuers, optional destination vehicle] -> deployed class.
params [["_providers", 0, [0]], ["_vehicle", objNull, [objNull]]];
if (!isNull _vehicle && {_vehicle isKindOf "vtx_H60_base"}) exitWith {"ACME_Talon_Open"};
if (_providers < 1) exitWith {""};
["ACME_SKED_Open", "ACME_Talon_Open"] select (_providers >= 3)
