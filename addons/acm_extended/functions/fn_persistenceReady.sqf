/* Local checkpoint preflight. Server calls additionally inspect authoritative
 * journals involving this unit. This does not freeze other mission participants. */
params ["_unit",["_requireLocal",true]];
if (isNull _unit || {_requireLocal && {!local _unit}}) exitWith {false};
// Retire only IV reservations whose existing B236 unknown-outcome policy
// already commits after deadline+30. Never refund or silently retire an
// unscoped active supply; any remaining local receipt makes this owner busy.
private _stock = missionNamespace getVariable ["ACME_supplyReceipts",createHashMap];
private _scopes = missionNamespace getVariable ["ACME_IV_SupplyScopes",createHashMap];
{
    private _scope = _scopes get _x;
    if (_scope isEqualType [] && {count _scope == 8} && {(_scope select 6) isEqualType 0}
        && {finite (_scope select 6)} && {(_scope select 6) + 30 < serverTime}) then {
        if ((_stock getOrDefault [_x,[]]) isEqualTo (_scope select 0)) then {_stock deleteAt _x;};
        _scopes deleteAt _x;
    };
} forEach keys _scopes;
if (local _unit) then {
    private _bindings = _unit getVariable ["ACME_IV_SupplyBindings",[]];
    private _live = _bindings select {!(_x isEqualType [] && {count _x == 8} && {(_x select 6) isEqualType 0} && {finite (_x select 6)} && {(_x select 6) + 30 < serverTime})};
    if (_live isNotEqualTo _bindings) then {_unit setVariable ["ACME_IV_SupplyBindings",_live,true];};
};
if (count _stock > 0 || {count (_unit getVariable ["ACME_IV_SupplyBindings",[]]) > 0}) exitWith {false};
if (count (_unit getVariable ["ACME_resourceReturnSourcePending",createHashMap]) > 0) exitWith {false};
private _sourceDecisions = missionNamespace getVariable ["ACME_resourceReturnSources",createHashMap];
// This private machine may still fund a return after both actor objects were
// deleted. Require its terminal source decision even for a different local
// capture; per-object public flags cannot represent a deleted actor.
if (((values _sourceDecisions) findIf {(_x param [1,""]) in ["applying","funded","admitted","uncertain"]}) >= 0) exitWith {false};
private _fundingReady = true;
if (!isServer) then {
    private _funded = _unit getVariable ["ACME_resourceReturnFunded",createHashMap];
    private _resolved = _unit getVariable ["ACME_resourceReturnResolved",createHashMap];
    if (((keys _funded) findIf {!(_resolved getOrDefault [_x,false])}) >= 0) exitWith {_fundingReady = false;};
    private _freshFunded = _unit getVariable ["ACME_txRemoveFunded",createHashMap];
    private _freshResolved = _unit getVariable ["ACME_txRemoveResolved",createHashMap];
    if (((keys _freshFunded) findIf {!(_freshResolved getOrDefault [_x,false])}) >= 0) exitWith {_fundingReady = false;};
};
if (!_fundingReady) exitWith {false};
private _bloodImport = _unit getVariable ["ACME_bloodRestoreUnresolved",[]];
if (_bloodImport isNotEqualTo [] && {(_bloodImport param [0,-1]) == (_unit getVariable ["ACME_equipmentKitEpoch",0])}) exitWith {false};
if ((_unit getVariable ["ACME_bloodRestoreOutbox",[]]) isNotEqualTo []) exitWith {false};
if ((_unit getVariable ["ACME_yBuildPending",[]]) isNotEqualTo []) exitWith {false};
if (count (_unit getVariable ["ACME_bf_pendingGrants",createHashMap]) > 0
    || {(_unit getVariable ["ACME_infusionMixFlowInput",[]]) isNotEqualTo []}) exitWith {false};
private _mixEpoch = _unit getVariable ["ACME_clinicalEpoch",0];
private _mix = _unit getVariable ["ACME_infusionMixFlowLeases",createHashMap];
if (((values _mix) findIf {(_x param [0,""]) == "active" && {(_x param [5,-1]) == _mixEpoch}}) >= 0) exitWith {false};
if (count (_unit getVariable ["ACM_circulation_freshBloodPending",createHashMap]) > 0) exitWith {false};
private _freshReceived = _unit getVariable ["ACM_circulation_freshBloodReceived",createHashMap];
if (((values _freshReceived) findIf {(_x param [3,""]) != "delivered"}) >= 0) exitWith {false};
if (count (_unit getVariable ["ACME_resourceReturnPending",createHashMap]) > 0) exitWith {false};
private _returnsReceived = _unit getVariable ["ACME_resourceReturnReceived",createHashMap];
if (((values _returnsReceived) findIf {(_x param [1,""]) != "delivered"}) >= 0) exitWith {false};
private _sessions = _unit getVariable ["ACME_syringeDeliverySessions",createHashMap];
if (((values _sessions) findIf {(_x param [2,""]) != "settled"}) >= 0) exitWith {false};
if ((_unit getVariable ["ACME_bf_take",[]]) isNotEqualTo []
    || {count (_unit getVariable ["ACME_medicationEscrow",createHashMap]) > 0}) exitWith {false};
private _clients = missionNamespace getVariable ["ACME_syringeDeliveryClientSessions",createHashMap];
if (((values _clients) findIf {(_x param [0,objNull]) isEqualTo _unit && {!((_x param [4,""]) in ["terminal","settled"])}}) >= 0) exitWith {false};
private _messages = missionNamespace getVariable ["ACME_syringeDeliveryOutbox",createHashMap];
if (((values _messages) findIf {((_x param [0,[]]) param [1,objNull]) isEqualTo _unit}) >= 0) exitWith {false};
if (!isServer) exitWith {true};
private _safe = true;
private _returns = missionNamespace getVariable ["ACME_resourceReturns",createHashMap];
if (((values _returns) findIf {(_x param [4,""]) != "delivered" && {(_x param [0,objNull]) isEqualTo _unit || {(_x param [1,objNull]) isEqualTo _unit}}}) >= 0) exitWith {false};
private _fundedReturns = _unit getVariable ["ACME_resourceReturnFunded",createHashMap];
if (((keys _fundedReturns) findIf {((_returns getOrDefault [_x,[]]) param [4,""]) != "delivered"}) >= 0) exitWith {false};
private _freshGrants = missionNamespace getVariable ["ACM_circulation_FreshBloodGrants",createHashMap];
if (((values _freshGrants) findIf {(_x param [5,""]) != "delivered" && {(_x param [0,objNull]) isEqualTo _unit || {(_x param [1,objNull]) isEqualTo _unit}}}) >= 0) exitWith {false};
private _fundedFresh = _unit getVariable ["ACME_txRemoveFunded",createHashMap];
if (((keys _fundedFresh) findIf {((_freshGrants getOrDefault [_x,[]]) param [5,""]) != "delivered"}) >= 0) exitWith {false};
private _fridgeGrants = missionNamespace getVariable ["ACME_bf_serverGrants",createHashMap];
if (((values _fridgeGrants) findIf {(_x param [0,objNull]) isEqualTo _unit && {!((_x param [3,""]) in ["delivered","failed"])}}) >= 0) exitWith {false};
{
    private _grants = _x getVariable ["ACME_bf_grants",createHashMap];
    if (((values _grants) findIf {(_x param [0,objNull]) isEqualTo _unit && {!((_x param [3,""]) in ["delivered","failed"])}}) >= 0) exitWith {_safe = false;};
} forEach (missionNamespace getVariable ["ACME_bloodFridges",[]]);
if (!_safe) exitWith {false};
private _deliveries = missionNamespace getVariable ["ACME_syringeDeliveries",createHashMap];
{
    private _j = _deliveries get _x;
    if ((_j getOrDefault ["state",""]) != "settled") then {
        if ((_j getOrDefault ["medic",objNull]) isEqualTo _unit) exitWith {_safe = false;};
        private _batches = _j getOrDefault ["batches",createHashMap];
        if (((values _batches) findIf {((_x param [0,[]]) param [0,objNull]) isEqualTo _unit}) >= 0) exitWith {_safe = false;};
    };
} forEach keys _deliveries;
if (!_safe) exitWith {false};
private _vents = missionNamespace getVariable ["ACME_vent_custody",createHashMap];
{
    private _r = _vents get _x;
    if ((_r getOrDefault ["phase",""]) in ["taking","returning","finalizing"]
        && {[_r getOrDefault ["patient",objNull],_r getOrDefault ["supplier",objNull],_r getOrDefault ["recipient",objNull]] find _unit >= 0}) exitWith {_safe = false;};
} forEach keys _vents;
_safe
