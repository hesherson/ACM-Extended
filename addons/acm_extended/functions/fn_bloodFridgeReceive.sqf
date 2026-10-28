/* Inventory delivery is independent of cosmetic reach. Its receipt is permanent
 * for this mission and acknowledged only after native placement readback. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_bloodFridgeReceive;};};
params ["_anchor", "_class", "_player", ["_token", [], [[]]]];
if (isNull _player || {!local _player} || {count _token != 2}) exitWith {};
// Tokens sequence across all fridges for this provider. The key survives
// deletion of the source furniture while an accepted grant is in transport.
private _deliveryKey=format ["%1:%2",_token select 0,_token select 1];
private _deliveries=_player getVariable ["ACME_bf_deliveryReceipts",createHashMap];
private _previous=_deliveries getOrDefault [_deliveryKey,[]];
private _ack={
    ["ACME_bfDeliveryAck",[_anchor,_player,_token,_class,clientOwner]] call CBA_fnc_serverEvent;
};
if (_previous isNotEqualTo []) exitWith {
    if (_previous isEqualTo [_anchor,_token,_class,"delivered"]) then {call _ack;};
};
private _received = _player getVariable ["ACME_bf_receivedTokens", []];
if (_token in _received) exitWith {
    // An in-session upgrade can encounter a pre-journal delivery receipt.
    _deliveries set [_deliveryKey,[_anchor,+_token,_class,"delivered"]];
    _player setVariable ["ACME_bf_deliveryReceipts",_deliveries,true];call _ack;
};
private _placed=_class=="";
if (_class != "") then {
    private _before={_x==_class} count ((uniformItems _player)+(vestItems _player)+(backpackItems _player));
    private _nearHolder=nearestObject [_player,"WeaponHolder"];
    private _groundBefore=if (isNull _nearHolder) then {0} else {{_x==_class} count itemCargo _nearHolder};
    private _placement=[_player,_class] call ace_common_fnc_addToInventory;
    private _after={_x==_class} count ((uniformItems _player)+(vestItems _player)+(backpackItems _player));
    _placed=_after==_before+1;
    private _knownUnplaced=false;
    if (!_placed && {!isNil "_placement"} && {_placement isEqualType []} && {count _placement==2}
        && {(_placement select 0) isEqualType true} && {(_placement select 1) isEqualType objNull}) then {
        private _holder=_placement select 1;
        _knownUnplaced=_after==_before;
        if (!isNull _holder && {_holder isNotEqualTo _player}) then {
            private _expected=if (_holder isEqualTo _nearHolder) then {_groundBefore+1} else {1};
            private _groundAfter={_x==_class} count itemCargo _holder;
            _placed=_groundAfter==_expected;
            _knownUnplaced=_knownUnplaced && {_groundAfter==_expected-1};
        };
    };
    if (!_placed) exitWith {
        // A conforming ACE result with unchanged native cargo proves no grant
        // was materialized. Retry that same funded journal; never debit again.
        if (!_knownUnplaced) then {
            _deliveries set [_deliveryKey,[_anchor,+_token,_class,"uncertain"]];
            _player setVariable ["ACME_bf_deliveryReceipts",_deliveries,true];
            diag_log "[ACME BLOOD FRIDGE] Native delivery returned no verifiable placement; stock remains reserved for recovery.";
        };
    };
};
// A failed inner placement exit must not fall through to a successful receipt.
if (!_placed) exitWith {};
_deliveries set [_deliveryKey,[_anchor,+_token,_class,"delivered"]];
_player setVariable ["ACME_bf_deliveryReceipts",_deliveries,true];
call _ack;
_received pushBack _token;
// Keep the legacy presentation window bounded. The permanent exact delivery
// receipts above remain the authority for transport retries after this window.
if (count _received > 64) then {_received deleteAt 0;};
_player setVariable ["ACME_bf_receivedTokens", _received, true];
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
