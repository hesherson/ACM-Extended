/* B216 server-authoritative stock transaction. Door lease and dispense are one unscheduled owner operation. */
params ["_anchor", "_class", "_player", ["_token", [], [[]]]];
if (!isServer || {isNull _anchor} || {isNull _player} || {count _token != 2}) exitWith {};
_token params [["_requestOwner", -1, [0]], ["_sequence", 0, [0]]];
if (_requestOwner != owner _player || {_sequence < 1}) exitWith {};
if !(_anchor getVariable ["ACME_bloodFridge", false]) exitWith {};
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
private _stock = +(_anchor getVariable ["ACME_bf_stock", []]);
private _i = _stock findIf {(_x # 0) == _class && {(_x # 1) > 0}};
if (!_valid || {_i < 0}) exitWith {
    ["ACME_bfGive", [_anchor, "", _player, _token], _player] call CBA_fnc_targetEvent;
};
private _entry = +(_stock # _i);
_entry set [1, (_entry # 1) - 1];
_stock set [_i, _entry];
_anchor setVariable ["ACME_bf_stock", _stock, true];
private _takers = _anchor getVariable ["ACME_bf_takers", createHashMap];
_takers set [netId _player, [_player, _token, diag_tickTime + 8]];
_anchor setVariable ["ACME_bf_takers", _takers];
call ACME_fnc_bloodFridgeTick;
["ACME_bfGive", [_anchor, _class, _player, _token], _player] call CBA_fnc_targetEvent;
