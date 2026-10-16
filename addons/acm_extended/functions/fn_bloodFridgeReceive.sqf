/* B216 provider-local acknowledgement. Inventory delivery is independent of the cosmetic reach lifecycle. */
params ["_anchor", "_class", "_player", ["_token", [], [[]]]];
if (isNull _player || {!local _player} || {count _token != 2}) exitWith {};
private _received = _player getVariable ["ACME_bf_receivedTokens", []];
if (_token in _received) exitWith {};
_received pushBack _token;
// Bound receipt memory while carrying recent deduplication across locality transfers. Each accepted take emits
// exactly one reliable give event; this window additionally rejects accidental repeated delivery.
if (count _received > 64) then {_received deleteAt 0;};
_player setVariable ["ACME_bf_receivedTokens", _received, true];
private _current = (_player getVariable ["ACME_bf_take", []]) isEqualTo [_token, _anchor];
if (_class != "") then {
    // ACE retains its normal ground-holder fallback when the taker's inventory is full.
    [_player, _class] call ace_common_fnc_addToInventory;
    if (_player isEqualTo ACE_player) then {
        [format ["Took %1 from the blood fridge.", getText (configFile >> "CfgWeapons" >> _class >> "displayName")], 2]
            call ace_common_fnc_displayTextStructured;
    };
};
if (_class == "" || {!_current} || {!(_player isEqualTo ACE_player)} || {!alive _player}
    || {_player getVariable ["ACE_isUnconscious", false]} || {isNull _anchor}
    || {_player distance _anchor > 4.5} || {[_player] call ACME_fnc_animBlocked}
    || {_player getVariable ["ACME_DP_Active", false]}
    || {!([_player, _anchor, []] call ace_common_fnc_canInteractWith)}
    || {[_player] call ACME_fnc_providerStanceOwned}) exitWith {
    if (_current) then {_player setVariable ["ACME_bf_take", []];};
    ["ACME_bfTakeStop", [_anchor, _player, _token]] call CBA_fnc_serverEvent;
    if (_class == "" && {_player isEqualTo ACE_player}) then {
        ["That blood unit is no longer available.", 2] call ace_common_fnc_displayTextStructured;
    };
};

// This is the same complete Putdown / return sequence as head elevation and lowering. It already owns
// logical empty hands, 1.5x playback, prone substitution, cancellation and a bounded completion watchdog.
[_player, "elevate"] call ACME_fnc_headElevMedicSeq;
private _animToken = _player getVariable ["ACME_headElev_medicAnimToken", -1];
[{
    params ["_args", "_pfh"];
    _args params ["_player", "_anchor", "_token", "_animToken", "_deadline"];
    private _current = !isNull _player && {local _player}
        && {(_player getVariable ["ACME_bf_take", []]) isEqualTo [_token, _anchor]};
    private _ownsAnim = _current
        && {(_player getVariable ["ACME_headElev_medicAnimToken", -2]) == _animToken};
    private _abort = !_current || {isNull _anchor} || {!alive _player}
        || {_player getVariable ["ACE_isUnconscious", false]} || {_player distance _anchor > 4.5}
        || {!(_player isEqualTo ACE_player)} || {[_player] call ACME_fnc_animBlocked}
        || {_player getVariable ["ACME_DP_Active", false]}
        || {!([_player, _anchor, []] call ace_common_fnc_canInteractWith)}
        || {diag_tickTime >= _deadline};
    if (!_abort && {_ownsAnim} && {_player getVariable ["ACME_headElev_seqActive", false]}) exitWith {};
    [_pfh] call CBA_fnc_removePerFrameHandler;
    if (_abort && {_ownsAnim} && {_player isEqualTo ACE_player}
        && {_player getVariable ["ACME_headElev_seqActive", false]}) then {
        call ACME_fnc_headElevateCancelSeq;
    };
    if (_current) then {_player setVariable ["ACME_bf_take", []];};
    ["ACME_bfTakeStop", [_anchor, _player, _token]] call CBA_fnc_serverEvent;
}, 0.05, [_player, _anchor, _token, _animToken, diag_tickTime + 7]] call CBA_fnc_addPerFrameHandler;
