/* B230: resolve only the newly created carrier, never a nearest-volume or old bag.
 * Native/compatibility callbacks need not return the bag UID. The authoritative
 * before/after difference must contain exactly one new carrier on this access.
 * Returned tuple: [row index, stable UID], or [] on absent/ambiguous/mismatched creation.
 */
params ["_patient", "_part", "_before", "_type", "_volume", "_site", "_iv", "_access"];
if (isNull _patient || {!local _patient}) exitWith {[]};
private _bags = (_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_part, []];
private _added = [];
{
    private _bag = _x;
    private _uid = _bag param [8, "", [""]];
    private _known = if (_uid != "") then {
        (_before findIf {(_x param [8, "", [""]]) isEqualTo _uid}) >= 0
    } else {
        (_before findIf {_x isEqualTo _bag}) >= 0
    };
    if (!_known) then {_added pushBack _forEachIndex;};
} forEach _bags;
if (count _added != 1) exitWith {[]};
private _index = _added select 0;
private _bag = _bags select _index;
if (count _bag < 7
    || {(_bag param [0, ""]) isNotEqualTo _type}
    || {(_bag param [2, -1]) isNotEqualTo _access}
    || {(_bag param [3, -1]) isNotEqualTo _site}
    || {(_bag param [4, true]) isNotEqualTo _iv}
    || {!finite (_bag select 1)} || {!finite (_bag select 6)}
    || {abs ((_bag select 1) - _volume) > 0.001}
    || {abs ((_bag select 6) - _volume) > 0.001}) exitWith {[]};
private _uid = _bag param [8, "", [""]];
if (_uid == "") then {
    // Legacy tuples receive an owner-issued identity only after exact creation is proven.
    private _sequence = (_patient getVariable ["ACME_bagSequence", 0]) + 1;
    _patient setVariable ["ACME_bagSequence", _sequence, true];
    _uid = format ["%1:%2:%3:%4", netId _patient, [_patient] call ACME_fnc_clinicalEpoch, clientOwner, _sequence];
    if (count _bag < 8) then {_bag set [7, -1];};
    _bag set [8, _uid];
    private _map = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
    _bags set [_index, _bag]; _map set [_part, _bags];
    [_patient, _map, false] call ACME_fnc_ivBagsCommit;
};
[_index, _uid]
