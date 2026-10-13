/* One actual inspired-oxygen contract for native altitude and body reserves.
 * The ventilator owns its measured mixture. A patient sentinel cannot stand
 * in for a hand BVM or turn a room-air/low-FiO2 machine into 95% oxygen.
 */
params ["_patient", ["_exposure", []]];
if (isNull _patient) exitWith {21};
if (count _exposure != 5) then {_exposure = [_patient] call ACME_fnc_flightExposure;};
private _fio2 = if (_exposure select 3) then {100} else {21};
if (_patient getVariable ["ACME_vent_driving", false]) exitWith {
    private _settings = [_patient] call ACME_fnc_ventEffectiveSettings;
    private _effective = if (_settings isEqualType []) then {_settings param [4, 21]} else {21};
    if (_effective isEqualType 0 && {finite _effective}) then {(_effective max 21) min 100} else {21}
};
if ((_patient getVariable ["ACME_nrb_on", false])
    && {_patient getVariable ["ACME_nrb_hasO2", false]}
    && {_patient getVariable ["ACME_nrb_delivering", false]}) then {_fio2 = _fio2 max 70;};
private _provider = _patient getVariable ["ACM_breathing_BVM_provider", objNull];
private _oxygenAt = _patient getVariable ["ACM_breathing_BVM_lastBreathOxygen", -1000];
private _oxygenAge = if (_oxygenAt isEqualType 0 && {finite _oxygenAt}) then {CBA_missionTime - _oxygenAt} else {-1};
private _handBvm = _provider isEqualType objNull && {!isNull _provider} && {!(_provider isEqualTo _patient)}
    && {alive _provider} && {_patient getVariable ["ACM_breathing_BVM_ConnectedOxygen", false]}
    && {_oxygenAge >= 0} && {_oxygenAge < 30}
    && {[_provider, _patient] call ACM_breathing_fnc_bvmSessionValid};
if (_handBvm && {isMultiplayer}) then {
    // The accepted breath also has a public shared clock. Reject stale or
    // future observer samples across patient ownership or provider sessions.
    private _serverAt = _patient getVariable ["ACME_bvm_lastBreathServer", -1000];
    _handBvm = _serverAt isEqualType 0 && {finite _serverAt}
        && {serverTime >= _serverAt} && {serverTime - _serverAt < 30};
};
if (_handBvm) then {_fio2 = _fio2 max 95;};
_fio2
