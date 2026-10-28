/* Presentation/held diagnostics only. Generic resource-return receipts are
 * the delivery authority; replay and migration here can never add an item. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_bloodFridgeReceive;};};
params ["_anchor", "_class", "_player", ["_token", [], [[]]], ["_status","delivered"],["_bridge",""]];
if (isNull _player || {!local _player} || {count _token != 2}) exitWith {};
if (_bridge=="") then {_bridge=format ["fridge:%1:%2:%3",netId _player,_token select 0,_token select 1];};
private _deliveryKey=format ["%1:%2",_token select 0,_token select 1];
private _deliveries=_player getVariable ["ACME_bf_deliveryReceipts",createHashMap];
private _previous=_deliveries getOrDefault [_deliveryKey,[]];
private _ack={
    if (_class!="") then {["ACME_bfDeliveryAck",[_anchor,_player,_token,_class,clientOwner]] call CBA_fnc_serverEvent;};
};
private _received = _player getVariable ["ACME_bf_receivedTokens", []];
private _products=[["item",_class]];
private _proof=(_player getVariable ["ACME_resourceReturnReceived",createHashMap]) getOrDefault [_bridge,[]];
if (_status=="held") exitWith {
    if (hasInterface && {_player isEqualTo ACE_player}) then {["Blood pickup is reserved for recovery.",3] call ace_common_fnc_displayTextStructured;};
};
if (_status=="uncertain") exitWith {
    if (_proof isNotEqualTo [_products,"uncertain"] || {_previous isNotEqualTo []}) exitWith {};
    _deliveries set [_deliveryKey,[_anchor,+_token,_class,"uncertain"]];
    _player setVariable ["ACME_bf_deliveryReceipts",_deliveries,true];
    diag_log "[ACME BLOOD FRIDGE] Native delivery returned no verifiable placement; stock remains reserved for recovery.";
};
if (_class!="" && {_proof isNotEqualTo [_products,"delivered"]}) exitWith {};
if (_previous isEqualTo [_anchor,_token,_class,"delivered"]) exitWith {call _ack;};
_deliveries set [_deliveryKey,[_anchor,+_token,_class,"delivered"]];
_player setVariable ["ACME_bf_deliveryReceipts",_deliveries,true];
call _ack;
_received pushBack _token;
// This bounded legacy window is presentation bookkeeping. Generic private
// decisions and server journals retain all authority for physical delivery.
if (count _received > 64) then {_received deleteAt 0;};
_player setVariable ["ACME_bf_receivedTokens", _received, true];
if (!hasInterface) exitWith {["ACME_bfTakeStop",[_anchor,_player,_token]] call CBA_fnc_serverEvent;};
private _current = (_player getVariable ["ACME_bf_take", []]) isEqualTo [_token, _anchor];
if (_class != "") then {
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
