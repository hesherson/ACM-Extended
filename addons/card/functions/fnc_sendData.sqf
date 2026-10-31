/* Retries carry the identical request and baseline. An ACK retires only that
 * request; a later form or different casualty never inherits its callback. */
params ["_medic", "_packet", ["_attempt", 0]];
if (!hasInterface || {isNull _medic} || {!local _medic} || {!(_medic isEqualTo ACE_player)}
    || {count _packet != 7}) exitWith {false};
private _id = _packet select 3;
private _receipt = [_id, _packet select 0, _packet select 2];
private _pending = +(_medic getVariable ["DD1380_Pending", []]);
if (_attempt == 0) then {
    _pending pushBackUnique _receipt;
    _medic setVariable ["DD1380_Pending", _pending];
};
if !(_receipt in _pending) exitWith {true};
if (_attempt >= 6) exitWith {
    _pending deleteAt (_pending find _receipt);
    _medic setVariable ["DD1380_Pending", _pending];
    ["Card save confirmation timed out. Reopen the card to verify its entries."] call ace_common_fnc_displayTextStructured;
    false
};
["LNX_DD1380_Save", _packet, _packet select 0] call CBA_fnc_targetEvent;
[{_this call DD1380_card_fnc_sendData;}, [_medic, _packet, _attempt + 1], 5] call CBA_fnc_waitAndExecute;
true
