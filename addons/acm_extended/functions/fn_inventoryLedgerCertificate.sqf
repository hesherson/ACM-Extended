params ["_owner","_kind","_sid","_request"];
private _held = (_owner getVariable ["ACME_inventoryEscrow",createHashMap]) getOrDefault [_request,[]];
if (count _held < 6 || {(_held select 2) != _kind} || {((_held select 1) param [0,""]) != _sid}) exitWith {[]};
private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_held select 0],[]];
if (count _record < 7 || {(_record select 3) isNotEqualTo _owner} || {(_record select 4) != _request}
    || {(_record select 5) != "reserved"} || {(_record select 2) isNotEqualTo (_held select 1)}
    || {(_held select 4) != (_owner getVariable ["ACME_equipmentKitEpoch",0])}) exitWith {[]};
+(_held select 1)
