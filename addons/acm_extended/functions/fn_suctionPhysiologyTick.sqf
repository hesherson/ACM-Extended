/* B13: mild, bounded extra oxygen-target penalty, integrated only on the patient owner.
   Ten seconds is a gameplay grace period, not a clinical threshold. A parked SALAD
   catheter drains the upper esophageal inlet, not the trachea: much smaller penalty.
   Native apnea, obstruction and lung disease remain independent and are not capped here. */
params ["_patient"];
if (isNull _patient || {!local _patient}) exitWith {};
private _dt = [_patient, "suctionPhysiology", 0, 2] call ACME_fnc_clinicalTickDelta;
private _now = CBA_missionTime;
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _sessions = _patient getVariable ["ACME_suctionSessions", []];
private _live = _sessions select {
    _x params ["_token","_medic","_expires","_mode","_e"];
    private _present = alive _patient && {!isNull _medic} && {alive _medic} && {!(_medic getVariable ["ACE_isUnconscious", false])}
        && {_e == _epoch} && {_expires > _now}
        && {_medic distance _patient <= 5 || {!isNull objectParent _medic && {objectParent _medic == objectParent _patient}}};
    if (_mode in ["hand","salad"]) then {_present = _present && {([_medic, _patient, "ACM_ACCUVAC"] call ACME_fnc_treatmentSupplyCount) > 0};};
    if (_mode == "manual") then {
        private _proof = _medic getVariable ["ACME_suctionManualSession", []];
        _present = _present && {(_proof param [0, objNull]) == _patient} && {(_proof param [1, ""]) == _token};
    };
    _present
};
if !(_live isEqualTo _sessions) then {_patient setVariable ["ACME_suctionSessions", _live, true];};
private _pinned = _live select {(_x select 3) == "salad"};
[_patient, "ACME_suction_pinned", !(_pinned isEqualTo [])] call ACME_fnc_setVarNet;
[_patient, "ACME_suction_pinPos", if (_pinned isEqualTo []) then {[]} else {(_pinned select 0) select 6}] call ACME_fnc_setVarNet;
private _active = !(_live isEqualTo []);
private _risk = if ((_live findIf {(_x select 3) != "salad"}) >= 0) then {1} else {0.15};
private _exposure = (_patient getVariable ["ACME_suctionExposure", 0]) max 0;
private _debt = (_patient getVariable ["ACME_o2Drain_suction", 0]) max 0 min 6;
private _grace = (missionNamespace getVariable ["ACME_sucFreeSec", 10]) max 5 min 15;
if (_active) then {
    _exposure = (_exposure + _dt) min 120;
    private _over = (_exposure - _grace) max 0;
    private _supported = _patient getVariable ["ACME_vent_driving", false];
    _supported = _supported || {(_now - (_patient getVariable ["ACM_breathing_BVM_lastBreathOxygen", -100])) < 5};
    private _supportFactor = if (_supported) then {0.5} else {1};
    private _cap = if (_risk < 1) then {1} else {6};
    private _rate = 0.25 * (linearConversion [0, 20, _over, 0, 1, true]) * _risk * _supportFactor;
    // Changing to a parked catheter cannot instantly erase a previous deep-suction debt.
    if (_debt < _cap) then {_debt = (_debt + _rate * _dt) min _cap;};
} else {
    _exposure = (_exposure - 2 * _dt) max 0; // brief mouse releases do not rearm a fresh 10 seconds
    _debt = (_debt - 0.4 * _dt) max 0;
};
[_patient, "ACME_suctionExposure", _exposure] call ACME_fnc_setVarNet;
[_patient, "ACME_o2Drain_suction", _debt] call ACME_fnc_setVarNet;
[_patient, "ACME_sucWarned", _active && {_exposure > _grace}] call ACME_fnc_setVarNet;
// Retired wall-clock field is only a diagnostic sentinel, never a second integrator.
[_patient, "ACME_sucRunSince", if (_active) then {_now - _exposure} else {-1}] call ACME_fnc_setVarNet;
