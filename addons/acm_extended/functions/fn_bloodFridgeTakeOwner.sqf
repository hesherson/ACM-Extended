/* Stock debit and grant journal commit precede transport. A door lease can
 * expire independently; it is never evidence that the inventory was delivered. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_bloodFridgeTakeOwner;};};
params ["_anchor", "_class", "_player", ["_token", [], [[]]]];
if (!isServer || {isNull _anchor} || {isNull _player} || {count _token != 2}) exitWith {};
_token params [["_requestOwner", -1, [0]], ["_sequence", 0, [0]]];
if (_requestOwner != owner _player || {!finite _requestOwner} || {_requestOwner != floor _requestOwner}
    || {!finite _sequence} || {_sequence < 1} || {_sequence != floor _sequence}) exitWith {};
if !(_anchor getVariable ["ACME_bloodFridge", false]) exitWith {};
private _grantKey=format ["%1:%2:%3",netId _player,_requestOwner,_sequence];
private _grants=_anchor getVariable ["ACME_bf_grants",createHashMap];
private _serverGrants=missionNamespace getVariable ["ACME_bf_serverGrants",createHashMap];
private _grant=_serverGrants getOrDefault [_grantKey,[]];
if (_grant isNotEqualTo []) exitWith {
    if ((_grant select 0) isEqualTo _player && {(_grant select 1) isEqualTo _token} && {(_grant select 2)==_class}
        && {(_grant select 5) isEqualTo _anchor}) then {
        private _bridge=_grant param [6,""];
        if ((_grant select 3)=="pending" && {_bridge!=""}) then {
            ["fridgeStock",[_player,_anchor,_bridge,[["item",_class]]]] call ACME_fnc_resourceReturnBroker;
        };
        if ((_grant select 3)=="delivered") then {["ACME_bfGive",[_anchor,_class,_player,_token,"delivered",_bridge],_player] call CBA_fnc_targetEvent;};
        if ((_grant select 3)=="failed") then {["ACME_bfGive",[_anchor,"",_player,_token],_player] call CBA_fnc_targetEvent;};
    };
};
if (_player getVariable ["ACME_persistenceFrozen",false] || {_anchor getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
// Keep each connected owner's high-water mark across A -> B -> A locality changes. A single last-owner pair
// would forget A's receipt and allow a delayed A request to debit stock again when control returned to A.
private _history = _player getVariable ["ACME_bf_serverTakeTokens", createHashMap];
private _key = str _requestOwner;
if (_sequence <= (_history getOrDefault [_key, 0])) exitWith {};
private _liveOwners = [2, _requestOwner] + (allPlayers apply {owner _x});
{if !((parseNumber _x) in _liveOwners) then {_history deleteAt _x;};} forEach keys _history;
_history set [_key, _sequence];
_player setVariable ["ACME_bf_serverTakeTokens", _history];
private _valid = alive _player && {!(_player getVariable ["ACE_isUnconscious", false])}
    && {_player distance _anchor <= 4.5} && {isNull objectParent _player};
private _stock = [_anchor getVariable ["ACME_bf_stock", []]] call ACME_fnc_syringeDeliveryCopy;
private _i = _stock findIf {(_x # 0) == _class && {(_x # 1) > 0}};
if (!_valid || {_i < 0}) exitWith {
    ["ACME_bfGive", [_anchor, "", _player, _token], _player] call CBA_fnc_targetEvent;
};
private _originalStock=[_stock] call ACME_fnc_syringeDeliveryCopy;
private _entry = +(_stock # _i);
_entry set [1, (_entry # 1) - 1];
_stock set [_i, _entry];
private _bridge="fridge:"+_grantKey;
private _newGrant=[_player,+_token,_class,"applying",diag_tickTime+2,_anchor,_bridge];
_grants set [_grantKey,_newGrant];_anchor setVariable ["ACME_bf_grants",_grants];
_serverGrants set [_grantKey,_newGrant];missionNamespace setVariable ["ACME_bf_serverGrants",_serverGrants];
private _pending=_player getVariable ["ACME_bf_pendingGrants",createHashMap];
_pending set [_grantKey,[_anchor,+_token,_class]];_player setVariable ["ACME_bf_pendingGrants",_pending,true];
_anchor setVariable ["ACME_bf_stock", [_stock] call ACME_fnc_syringeDeliveryCopy, true];
private _observed=[_anchor getVariable ["ACME_bf_stock",[]]] call ACME_fnc_syringeDeliveryCopy;
if (_observed isNotEqualTo _stock) exitWith {
    private _unchanged=_observed isEqualTo _originalStock;
    _newGrant set [3,["stockUncertain","failed"] select _unchanged];
    _newGrant set [7,[[_originalStock,_stock,_observed]] call ACME_fnc_syringeDeliveryCopy];
    _grants set [_grantKey,_newGrant];_anchor setVariable ["ACME_bf_grants",_grants];
    _serverGrants set [_grantKey,_newGrant];missionNamespace setVariable ["ACME_bf_serverGrants",_serverGrants];
    if (_unchanged) then {_pending deleteAt _grantKey;_player setVariable ["ACME_bf_pendingGrants",_pending,true];};
    ["ACME_bfGive",[_anchor,if (_unchanged) then {""} else {_class},_player,_token,if (_unchanged) then {"unavailable"} else {"held"},_bridge],_player] call CBA_fnc_targetEvent;
};
// This exact virtual-stock debit is canonical before the generic grant may
// dispatch. Only that broker/receiver can materialize the item across owners.
_newGrant set [3,"pending"];
_grants set [_grantKey,_newGrant];_anchor setVariable ["ACME_bf_grants",_grants];
_serverGrants set [_grantKey,_newGrant];missionNamespace setVariable ["ACME_bf_serverGrants",_serverGrants];
private _active=missionNamespace getVariable ["ACME_bf_activeGrants",[]];_active pushBackUnique _grantKey;
missionNamespace setVariable ["ACME_bf_activeGrants",_active];
["fridgeStock",[_player,_anchor,_bridge,[["item",_class]]]] call ACME_fnc_resourceReturnBroker;
private _takers = _anchor getVariable ["ACME_bf_takers", createHashMap];
_takers set [netId _player, [_player, _token, diag_tickTime + 8]];
_anchor setVariable ["ACME_bf_takers", _takers];
call ACME_fnc_bloodFridgeTick;
