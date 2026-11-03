params ["_o", "_u", ["_on", false], ["_rate", 70], ["_ma", 0], ["_demand", false]];
if (isNull _u || {isNull _o} || {!local _u}) exitWith {};
private _actor = _o getVariable ["acme_tempusls_operator", objNull];
if (isRemoteExecuted && {isNull _actor || {remoteExecutedOwner != owner _actor}}) exitWith {};
private _old = _u getVariable ["acme_tempusls_paceSet", []];
if (!_on) exitWith {
    // A delayed disconnect from one device must not stop a newer device.
    if (count _old > 0 && {(_old select 0) isEqualTo _o}) then {
        _u setVariable ["acme_tempusls_paceSet", []];
        [_u, "acme_tempusls_capture", false] call ACME_fnc_setVarNet;
    };
};
if (isNull _actor || {!alive _actor} || {_actor distance _o > 3}
    || {_o distance _u > 6} || {(_o getVariable ["acme_tempusls_pat", objNull]) isNotEqualTo _u}
    || {!((_o getVariable ["acme_tempusls_pw", [false]]) select 0)}) exitWith {};
if (!finite _rate || {!finite _ma}) exitWith {};
_u setVariable ["acme_tempusls_paceSet", [_o, true, round (_rate max 30 min 180), round (_ma max 0 min 200), _demand, [_u] call ACME_fnc_clinicalEpoch, _actor]];
if (isNil {_u getVariable "acme_tempusls_thr"}) then {_u setVariable ["acme_tempusls_thr", 45 + round random 40, true];};
if ((_u getVariable ["acme_tempusls_paceId", -1]) >= 0) exitWith {};
private _id = [{
    params ["_u", "_id"];
    private _settings = _u getVariable ["acme_tempusls_paceSet", []];
    if (isNull _u || {!local _u} || {!alive _u} || {count _settings < 7}) exitWith {
        if (!isNull _u && {local _u}) then {
            [_u, "acme_tempusls_capture", false] call ACME_fnc_setVarNet;
            _u setVariable ["acme_tempusls_paceId", -1];
        };
        [_id] call CBA_fnc_removePerFrameHandler;
    };
    _settings params ["_device", "_on", "_rate", "_ma", "_demand", "_epoch", "_actor"];
    if (isNull _device || {_epoch != ([_u] call ACME_fnc_clinicalEpoch)}
        || {(_device getVariable ["acme_tempusls_pat", objNull]) isNotEqualTo _u}
        || {!((_device getVariable ["acme_tempusls_pw", [false]]) select 0)} || {_device distance _u > 6}) exitWith {
        _u setVariable ["acme_tempusls_paceSet", []];
        [_u, "acme_tempusls_capture", false] call ACME_fnc_setVarNet;
    };
    if (_u getVariable ["acme_tempusls_capture", false] && {!(_u getVariable ["ACE_isUnconscious", false])}
        && {diag_tickTime > (_u getVariable ["acme_tempusls_painAt", 0])}) then {
        _u setVariable ["acme_tempusls_painAt", diag_tickTime + 2];
        [_u, linearConversion [40, 200, _ma, 0.3, 0.8, true]] call ace_medical_fnc_adjustPainLevel;
    };
}, 0.5, _u] call CBA_fnc_addPerFrameHandler;
_u setVariable ["acme_tempusls_paceId", _id];
