/* Charge authorization is bound to the original pads, clinical episode and power cycle.
   The browser's ready message must return the exact context captured at charge start. */
params ["_o", "_operation", ["_energy", 0], ["_context", []]];
if (isNull _o) exitWith {[]};
private _patient = _o getVariable ["acme_tempusls_pat", objNull];
private _power = _o getVariable ["acme_tempusls_pw", [false]];
if (isNull _patient || {!(_power select 0)} || {!(_o getVariable ["acme_tempusls_pads",true])}) exitWith {[]};
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
if (_operation == "begin") exitWith {
    if (!finite _energy || {_energy < 1} || {_energy > 200}) exitWith {[]};
    [_o] call ACME_fnc_tempusLsChargeClear;
    private _serial = (missionNamespace getVariable ["ACME_tempusls_chargeSerial", 0]) + 1;
    missionNamespace setVariable ["ACME_tempusls_chargeSerial", _serial];
    private _token = format ["tls-charge:%1:%2", clientOwner, _serial];
    private _started = [_token, _patient, _epoch, _power, _energy, serverTime];
    _o setVariable ["acme_tempusls_charging", _started, true];
    _started
};
if (_operation != "ready" || {count _context != 6}
    || {_context isNotEqualTo (_o getVariable ["acme_tempusls_charging", []])}
    || {(_context select 1) isNotEqualTo _patient} || {(_context select 2) != _epoch}
    || {(_context select 3) isNotEqualTo _power}
    || {serverTime - (_context select 5) > 15} || {serverTime < (_context select 5)}) exitWith {[]};
private _charge = +_context;
_charge set [5, serverTime + 20];
_o setVariable ["acme_tempusls_charging", [], true];
_o setVariable ["acme_tempusls_charge", _charge, true];
_o setVariable ["acme_tempusls_armed", true, true];
_charge
