/* Each local feed owns a generation. Retired callbacks cannot clear a newer feed. */
params ["_o", "_u"];
if (isNull _o || {isNull _u}
    || {(_o getVariable ["acme_tempus_pat", objNull]) isNotEqualTo _u}) exitWith {};
if (!local _u) exitWith { [_o, _u] remoteExecCall ["ACME_fnc_tempusFeed", _u] };
private _current = _o getVariable ["acme_tempus_feeding", []];
if (count _current == 2 && {(_current select 0) isEqualTo _u}) exitWith {};
private _generation = (_o getVariable ["acme_tempus_feedGeneration", 0]) + 1;
_o setVariable ["acme_tempus_feedGeneration", _generation];
_o setVariable ["acme_tempus_feeding", [_u, _generation]];
[{
    params ["_args", "_id"];
    _args params ["_o", "_u", "_generation"];
    private _ownsFeed = !isNull _o && {
        (_o getVariable ["acme_tempus_feeding", []]) isEqualTo [_u, _generation]
    };
    private _stop = {
        if (_ownsFeed) then { _o setVariable ["acme_tempus_feeding", []] };
        [_id] call CBA_fnc_removePerFrameHandler;
    };
    if (!_ownsFeed || {isNull _u}
        || {(_o getVariable ["acme_tempus_pat", objNull]) isNotEqualTo _u}) exitWith { call _stop };
    if (!local _u) exitWith {
        call _stop;
        [_o, _u] remoteExecCall ["ACME_fnc_tempusFeed", _u];
    };
    if (_u distance _o > 6) exitWith {
        call _stop;
        _o setVariable ["acme_tempus_pat", objNull, true];
        _o setVariable ["acme_tempus_v", [], true];
    };
    if !((_o getVariable ["acme_tempus_pw", [false]]) select 0) exitWith {};
    private _v = [_u] call ACME_fnc_tempusVitals;
    if (_v isNotEqualTo (_o getVariable ["acme_tempus_v", []])) then { _o setVariable ["acme_tempus_v", _v, true] };
}, 1.5, [_o, _u, _generation]] call CBA_fnc_addPerFrameHandler;
