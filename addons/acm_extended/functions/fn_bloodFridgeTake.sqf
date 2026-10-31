/* B216: one local request per reach. The server grants stock atomically before provider theatre, so a cancelled
 * reach never destroys a unit or requires a competing restock/refund transaction. No weapons are restored. */
params ["_anchor", "_class", "_player"];
if (isNull _anchor || {isNull _player} || {!local _player} || {!alive _player}
    || {!(_player isEqualTo ACE_player)} || {_player getVariable ["ACE_isUnconscious", false]}
    || {_player distance _anchor > 4.5} || {[_player] call ACME_fnc_animBlocked}) exitWith {};
if ((_player getVariable ["ACME_bf_take", []]) isNotEqualTo []) exitWith {};
if (_player getVariable ["ACME_DP_Active", false]) exitWith {};
if !([_player, _anchor, []] call ace_common_fnc_canInteractWith) exitWith {};
if ([_player] call ACME_fnc_providerStanceOwned) exitWith {};
private _sequence = 1 + (_player getVariable ["ACME_bf_takeToken", 0]);
_player setVariable ["ACME_bf_takeToken", _sequence];
private _token = [clientOwner, _sequence];
_player setVariable ["ACME_bf_take", [_token, _anchor]];
["ACME_bfTake", [_anchor, _class, _player, _token]] call CBA_fnc_serverEvent;
// Lost/late acknowledgement must not keep the local menu disabled forever. A late valid grant still delivers
// the stock, but its old presentation cannot take over a newer interaction.
[{
    params ["_player", "_anchor", "_token"];
    if (isNull _player || {!local _player}) exitWith {};
    if ((_player getVariable ["ACME_bf_take", []]) isEqualTo [_token, _anchor]) then {
        _player setVariable ["ACME_bf_take", []];
        ["ACME_bfTakeStop", [_anchor, _player, _token]] call CBA_fnc_serverEvent;
    };
}, [_player, _anchor, _token], 10] call CBA_fnc_waitAndExecute;
