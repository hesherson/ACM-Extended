/* B391: confusion from the casualty's own vitals, on the machine that owns the player (as fn_obtundedAuto.sqf).
 * The band sits just above obtundation's: SpO2 below 93 % or MAP below 72 mmHg, held for 10 s, enters;
 * SpO2 95 % and MAP 75 mmHg leave it. Obtundation and unconsciousness take over from it and clear it. */
if !(missionNamespace getVariable ["ACME_sys_obtunded", false]) exitWith {};
if !(missionNamespace getVariable ["ACME_confused_autoEnable", true]) exitWith {};
private _spo2Enter = missionNamespace getVariable ["ACME_confused_spo2Enter", 93];
private _spo2Recover = missionNamespace getVariable ["ACME_confused_spo2Recover", 95];
private _mapEnter = missionNamespace getVariable ["ACME_confused_mapEnter", 72];
private _mapRecover = missionNamespace getVariable ["ACME_confused_mapRecover", 75];
private _dwell = missionNamespace getVariable ["ACME_confused_dwellEnter", 10];
{
    private _u = _x;
    if (!local _u || {_u getVariable ["ACME_confused_manual", false]}) then {continue};
    private _on = _u getVariable ["ACME_confused", false];
    private _deeper = (_u getVariable ["ACE_isUnconscious", false]) || {_u getVariable ["ACME_obtunded", false]}
        || {_u getVariable ["ace_medical_inCardiacArrest", false]};
    if (_deeper) then {
        if (_on) then {[_u, false, false, "deeper"] call ACME_fnc_confusedSet;};
        continue;
    };
    private _spo2 = _u getVariable ["ace_medical_spo2", 97];
    private _bp = [_u] call ace_medical_status_fnc_getBloodPressure;
    _bp params [["_d", 80], ["_s", 120]];
    private _map = _d + (_s - _d) / 3;
    if (_on) then {
        if (_spo2 >= _spo2Recover && {_map >= _mapRecover}) then {[_u, false, false, "recover"] call ACME_fnc_confusedSet;};
    } else {
        private _inBand = _spo2 < _spo2Enter || {_map < _mapEnter};
        if (!_inBand || {CBA_missionTime < (_u getVariable ["ACME_confused_refractoryUntil", -1])}) then {
            _u setVariable ["ACME_confused_dwellSince", -1];
        } else {
            private _since = _u getVariable ["ACME_confused_dwellSince", -1];
            if (_since < 0) then {_u setVariable ["ACME_confused_dwellSince", CBA_missionTime];} else {
                if (CBA_missionTime - _since >= _dwell) then {[_u, true, false, "vitals"] call ACME_fnc_confusedSet;};
            };
        };
    };
} forEach ((missionNamespace getVariable ["ACME_clinical_ownedUnits", []]) select {alive _x && {isPlayer _x}});
