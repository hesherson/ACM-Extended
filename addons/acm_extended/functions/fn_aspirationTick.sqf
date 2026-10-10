/*
 * Persistent aspiration injury.
 * Detects new vomit/emesis episodes, determines how protected the airway was at that moment, and converts the
 * aspirated fraction into a persistent recruitable lung shunt. Suction can clear visible airway fluid but does not
 * erase material that has already entered the lungs.
 */
private _now = CBA_missionTime;
private _candidate = {
    params ["_u"];
    if (isNull _u || {!local _u} || {!alive _u}) exitWith {false};
    private _load = (_u getVariable ["ACME_aspiration_load",0]) max 0;
    private _edema = (_u getVariable ["ACME_aspiration_edema",0]) max 0;
    private _event = _u getVariable ["ACME_laryngo_emesis", []];
    private _vomitState = _u getVariable ["ACM_airway_AirwayObstructionVomit_State",0];
    private _eventKey = if (_event isEqualType [] && {count _event >= 3}) then {
        format ["%1:%2:%3:%4", _event param [0,""], _event param [1,0], _event param [2,0], _vomitState]
    } else {
        format ["native:%1",_vomitState]
    };
    private _fresh = (_eventKey != (_u getVariable ["ACME_aspiration_lastEmesisKey",""]))
        && {_vomitState > 0 || {count _event >= 3}};
    private _residue = (_u getVariable ["ACME_aspiration_injury",0]) > 0.0005
        || {(_u getVariable ["ACME_aspiration_SpO2Penalty",0]) > 0.001}
        || {abs (_u getVariable ["ACME_aspiration_RRDrive",0]) > 0.001}
        || {(_u getVariable ["ACME_aspiration_shunt",0]) > 0.0001}
        || {_u getVariable ["ACME_aspiration_edemaActive",false]}
        || {abs (_u getVariable ["ACME_aspiration_lastRRAdj",0]) > 0.001};
    _fresh || {_load > 0.0005} || {_edema > 0.0005} || {_residue}
};
private _patients = (missionNamespace getVariable ["ACME_aspiration_activePatients", []]) select {[_x] call _candidate};
{
    private _u = _x;
    if (isNull _u || {!local _u} || {!alive _u}) then {continue};

    private _load = (_u getVariable ["ACME_aspiration_load",0]) max 0 min 1;
    private _edema = (_u getVariable ["ACME_aspiration_edema",0]) max 0 min 1;
    private _event = _u getVariable ["ACME_laryngo_emesis", []];
    private _vomitState = _u getVariable ["ACM_airway_AirwayObstructionVomit_State",0];
    private _eventKey = if (_event isEqualType [] && {count _event >= 3}) then {
        format ["%1:%2:%3:%4", _event param [0,""], _event param [1,0], _event param [2,0], _vomitState]
    } else {
        format ["native:%1",_vomitState]
    };
    private _lastKey = _u getVariable ["ACME_aspiration_lastEmesisKey",""];
    private _freshEvent = (_eventKey != _lastKey) && {_vomitState > 0 || {count _event >= 3}};
    private _hadEffect = (_u getVariable ["ACME_aspiration_injury",0]) > 0.0005
        || {(_u getVariable ["ACME_aspiration_SpO2Penalty",0]) > 0.001}
        || {abs (_u getVariable ["ACME_aspiration_RRDrive",0]) > 0.001}
        || {(_u getVariable ["ACME_aspiration_shunt",0]) > 0.0001}
        || {_u getVariable ["ACME_aspiration_edemaActive",false]}
        || {abs (_u getVariable ["ACME_aspiration_lastRRAdj",0]) > 0.001};
    // No emesis, no retained lung injury and no cleanup residue means no physiology
    // and, critically, no periodic zero-valued network heartbeat.
    if (!_freshEvent && {_load <= 0.0005} && {_edema <= 0.0005} && {!_hadEffect}) then {continue};

    if (_freshEvent) then {
        _u setVariable ["ACME_aspiration_lastEmesisKey",_eventKey,false];
        private _stage = if (count _event >= 3) then {_event param [2,2]} else {2};
        private _protection = 1;
        private _ett = _u getVariable ["ACME_ETT_Inserted",false];
        private _cuff = _u getVariable ["ACME_ETT_CuffInflated",false];
        private _oral = toUpperANSI (_u getVariable ["ACM_airway_AirwayItem_Oral",""]);
        if (_ett && {_cuff}) then {_protection = 0.05;} else {
            if (_oral == "SGA") then {_protection = 0.25;};
        };
        if (_u getVariable ["ACM_airway_RecoveryPosition_State",false]) then {_protection = _protection * 0.35;};
        if (_u getVariable ["ace_medical_inCardiacArrest",false]) then {_protection = _protection * 0.75;};

        private _gain = linearConversion [1,8,_stage,0.06,0.32,true] * _protection;
        if (_gain > 0.005) then {
            _load = (_load + _gain) min 1;
            [_u,"ACME_aspiration_load",_load,([0.001,0] select (_load == 0)),0] call ACME_fnc_setVarNetApprox;
            // Used only by this owner-side model; a raw scheduler timestamp has no
            // cross-machine meaning and never needs to be replicated.
            _u setVariable ["ACME_aspiration_lastAt",_now,false];
            if (!isNil "ace_medical_treatment_fnc_addToLog") then {
                [_u,"airway",format ["Aspiration suspected (lung burden %1%%)",round (_load*100)],[]] call ace_medical_treatment_fnc_addToLog;
            };
        };
    };

    private _lastAt = _u getVariable ["ACME_aspiration_tickAt",_now-1];
    private _dt = ((_now - _lastAt) max 0) min 3;
    _u setVariable ["ACME_aspiration_tickAt",_now,false];
    if (_dt <= 0) then {continue};

    // The particulate/chemical aspiration burden clears very slowly. Established alveolar injury is deliberately
    // slower than visible airway-fluid clearance, so suction does not magically normalize the lungs.
    if (_load > 0) then {
        private _recovery = if ((_u getVariable ["ace_medical_spo2",90]) >= 94) then {0.00006} else {0.00002};
        _load = (_load - (_recovery * _dt)) max 0;
        [_u,"ACME_aspiration_load",_load,([0.001,0] select (_load == 0)),0] call ACME_fnc_setVarNetApprox;
    };

    // Aspiration pneumonitis can progress to non-cardiogenic pulmonary edema from inflammatory capillary leak.
    // Minor aspiration does not automatically produce crackles. Moderate/severe or repeated aspiration builds a
    // delayed edema burden over tens of seconds, then resolves far more slowly than the initiating emesis.
    private _edemaTarget = linearConversion [0.14,0.75,_load,0,1,true];
    if (_edemaTarget > _edema) then {
        private _riseFraction = ((0.018 * _dt) min 0.20) max 0;
        _edema = _edema + ((_edemaTarget - _edema) * _riseFraction);
    } else {
        _edema = (_edema - (0.000035 * _dt)) max _edemaTarget;
    };
    _edema = _edema max 0 min 1;

    // Use one effective injury severity for oxygenation/RR/shunt. This is max(), not addition, so the edema
    // manifestation extends established injury without double-counting the same aspiration event.
    private _injury = _load max (0.85 * _edema);
    private _crackleThreshold = missionNamespace getVariable ["ACME_aspiration_edemaCrackleThreshold",0.12];
    [_u,"ACME_aspiration_edema",_edema,([0.001,0] select (_edema == 0)),0] call ACME_fnc_setVarNetApprox;
    [_u,"ACME_aspiration_edemaActive",_edema >= _crackleThreshold] call ACME_fnc_setVarNet;
    [_u,"ACME_aspiration_injury",_injury,([0.001,0] select (_injury == 0)),0] call ACME_fnc_setVarNetApprox;
    [_u,"ACME_aspiration_SpO2Penalty",30 * _injury,([0.03,0] select (_injury == 0)),0] call ACME_fnc_setVarNetApprox;

    // Spontaneous-breathing physiology. Ventilated oxygenation consumes the same effective injury through
    // ACME_fnc_ventOxygenation, where PEEP can recruit part of the flooded/collapsed lung.
    private _vent = (_u getVariable ["ACME_vent_onPatient",false]) && {_u getVariable ["ACME_vent_driving",false]};
    if (!_vent && {_injury > 0.001}) then {
        private _spo2 = _u getVariable ["ace_medical_spo2",97];
        private _ceiling = 98 - (30 * _injury);
        if (_spo2 > _ceiling) then {
            private _fall = (0.03 + (0.18 * _injury)) * _dt;
            private _new = (_spo2 - _fall) max _ceiling;
            [_u, [["spo2",_new,true,true]]] call ACM_core_fnc_setAceMedicalState;
        };
    };

    // Tachypneic compensation while spontaneous respiratory drive exists. Compose against the previous target
    // without accumulating our own last offset, and explicitly clear the old offset when aspiration resolves.
    private _curRR = _u getVariable ["ACM_core_TargetVitals_RespirationRate",16];
    private _lastAdj = _u getVariable ["ACME_aspiration_lastRRAdj",0];
    private _nativeRR = (_curRR - _lastAdj) max 0;
    private _adj = 14 * _injury;
    [_u, [["respirationRate", (_nativeRR + _adj) min 45, 0.02, 3]], true] call ACM_core_fnc_setTargetVitalsState;
    _u setVariable ["ACME_aspiration_lastRRAdj",_adj,false];
    [_u,"ACME_aspiration_RRDrive",_adj,([0.02,0] select (_adj == 0)),0] call ACME_fnc_setVarNetApprox;
    [_u,"ACME_aspiration_shunt",0.30 * _injury,([0.0005,0] select (_injury == 0)),0] call ACME_fnc_setVarNetApprox;
} forEach _patients;
ACME_aspiration_activePatients = _patients select {[_x] call _candidate};
