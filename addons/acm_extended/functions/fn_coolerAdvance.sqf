/* B287: advance one canonical cooler without mutating its source arrays.
 * State: [baseClass, coolantStartServerTime, [[bagClass,warmSeconds],...], lastSampleServerTime].
 * Only the portion of an interval after coolant expiry contributes warm exposure.
 * Spoilage is applied by the holder transaction, never by this pure state transform.
 */
params [["_state", [], [[]]], ["_now", serverTime, [0]]];
if (count _state != 4 || {!finite _now}) exitWith {[]};
_state params ["_base", "_start", "_entries", "_last"];
if !(_base isEqualType "" && {_start isEqualType 0} && {_entries isEqualType []} && {_last isEqualType 0}) exitWith {[]};
if (!finite _start || {!finite _last}) exitWith {[]};
private _valid = true;
{
    if !(_x isEqualType [] && {count _x == 2} && {(_x # 0) isEqualType ""}
        && {(_x # 1) isEqualType 0} && {finite (_x # 1)} && {(_x # 1) >= 0}) exitWith {_valid = false;};
} forEach _entries;
if (!_valid) exitWith {[]};
private _sample = _now max _last;
private _chain = getNumber (configFile >> "CfgWeapons" >> _base >> "ACME_coolerColdChainTime");
private _rate = missionNamespace getVariable ["ACME_coolerThawRateInside", 0.2];
if !(_rate isEqualType 0 && {finite _rate} && {_rate >= 0}) then {_rate = 0.2;};
private _increment = 0;
if (_chain > 0) then {
    private _expiry = _start + _chain;
    _increment = (((_sample - _expiry) max 0) - ((_last - _expiry) max 0)) * _rate;
};
[_base, _start, _entries apply {[_x # 0, (_x # 1) + _increment]}, _sample]
