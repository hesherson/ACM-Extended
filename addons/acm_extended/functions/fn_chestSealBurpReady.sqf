// One six-second cooldown per casualty, shared by both seal types and every provider.
// Use the synchronized engine clock; a remote client's CBA mission clock is not the owner's clock.
params ["_patient", ["_commit", false]];
if (isNull _patient || {_commit && {!local _patient}}) exitWith {false};
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _last = _patient getVariable ["ACME_CS_burpCooldown", []];
if ((_last param [2, ""]) == "serverTime"
    && {(_last param [0, -1]) isEqualTo _epoch}
    && {serverTime < (_last param [1, 0])}) exitWith {false};
if (_commit) then {
    _patient setVariable ["ACME_CS_burpCooldown", [_epoch, serverTime + 6, "serverTime"], true];
};
true
