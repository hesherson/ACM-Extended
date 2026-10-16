// Server-side stock anchor. The native fridge already has an authored door; keep one visible object so ACE's
// interaction target does not disappear as it opens. Door_1_noSound_source is the BI fridge's user source.
// _this is [_closed, _stock, _restock], where _stock is [[bloodclass, count], ...].
params ["_closed", ["_stock", []], ["_restock", true]];
if (!isServer || isNull _closed) exitWith {};
if (_closed getVariable ["ACME_bf_setup", false]) exitWith {};
_closed setVariable ["ACME_bf_setup", true];

_closed animateSource ["Door_1_noSound_source", 0, true];

// Stock is broadcast for menu labels; only the server changes it.
_closed setVariable ["ACME_bloodFridge", true, true];
_closed setVariable ["ACME_bf_anchor", _closed, true];
_closed setVariable ["ACME_bf_openObj", objNull, true];
_closed setVariable ["ACME_bf_stock", _stock, true];
_closed setVariable ["ACME_bf_default", +_stock, true];
_closed setVariable ["ACME_bf_restock", _restock, true];
// this is kept so the contents screen can say when it next refills, rather than only whether it does.
_closed setVariable ["ACME_bf_regenMins", (_closed getVariable ["ACME_bf_regenMins", (missionNamespace getVariable ["ACME_bf_regenMinsDefault", 1440])]), true];
_closed setVariable ["ACME_bf_open", false, true];
_closed setVariable ["ACME_bf_viewers", createHashMap];  // owner-local: netid -> last ping time
_closed setVariable ["ACME_bf_takers", createHashMap];  // server-local: netid -> [unit, token, deadline]

private _list = missionNamespace getVariable ["ACME_bloodFridges", []];
_list pushBackUnique _closed;
missionNamespace setVariable ["ACME_bloodFridges", _list];
