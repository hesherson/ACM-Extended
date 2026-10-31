/* Server-wide checkpoint preflight, including journals whose original actors
 * were deleted. Owner-local captures/proofs are still required independently.
 * No unknown outcome is interpreted as a delivered or canceled resource. */
if (!isServer) exitWith {false};
private _shieldPending = missionNamespace getVariable ["ACM_ophthalmology_shieldPending", createHashMap];
if (!(_shieldPending isEqualType createHashMap) || {count _shieldPending > 0}) exitWith {false};
private _ok = true;
{
    _x params ["_name","_stateIndex","_terminal"];
    private _map = missionNamespace getVariable [_name,createHashMap];
    if !(_map isEqualType createHashMap) exitWith {_ok = false;};
    if ((values _map findIf {!(_x isEqualType []) || {!((_x param [_stateIndex,""]) in _terminal)}}) >= 0) exitWith {_ok = false;};
} forEach [
    ["ACME_resourceReturns",4,["delivered"]],
    ["ACM_circulation_FreshBloodGrants",5,["delivered"]],
    ["ACME_bf_serverGrants",3,["delivered","failed"]]
];
if (!_ok) exitWith {false};
private _deliveries = missionNamespace getVariable ["ACME_syringeDeliveries",createHashMap];
if !(_deliveries isEqualType createHashMap) exitWith {false};
if ((values _deliveries findIf {!(_x isEqualType createHashMap) || {(_x getOrDefault ["state",""]) != "settled"}}) >= 0) exitWith {false};
private _vents = missionNamespace getVariable ["ACME_vent_custody",createHashMap];
if !(_vents isEqualType createHashMap) exitWith {false};
if ((values _vents findIf {!(_x isEqualType createHashMap) || {(_x getOrDefault ["phase",""]) != "attached"}}) >= 0) exitWith {false};
private _index = missionNamespace getVariable ["ACME_inventoryLedgerIndex",createHashMap];
if !(_index isEqualType createHashMap) exitWith {false};
{
    private _record = missionNamespace getVariable [format ["ACME_inventoryToken_%1",_index get _x],[]];
    if (count _record < 7 || {(_record select 5) in ["reserved","packing","packingAbort"]}) exitWith {_ok = false;};
} forEach keys _index;
if (!_ok) exitWith {false};
private _boxes = missionNamespace getVariable ["ACME_coolerBoxReceipts",createHashMap];
if !(_boxes isEqualType createHashMap) exitWith {false};
if ((values _boxes findIf {!(_x isEqualType []) || {(_x param [0,""]) == "draw" && {!(_x param [7,false])}}}) >= 0) exitWith {false};
// Private donor receipts are checked by each owner's local preflight. Public
// patient bindings also fence a server checkpoint when another actor vanished.
if (((allUnits + allDeadMen) findIf {
    count (_x getVariable ["ACME_IV_SupplyBindings",createHashMap]) > 0
    || {count (_x getVariable ["ACM_ophthalmology_shieldBindings",[]]) > 0}
    || {count (_x getVariable ["ACM_ophthalmology_shieldIncoming",createHashMap]) > 0}
}) >= 0) exitWith {false};
true
