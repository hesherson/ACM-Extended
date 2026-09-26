/*
 * Shock phenotypes layered onto ACM's existing hemodynamics.
 * Native causes and source-separated disease drives remain authoritative; this layer classifies the dominant
 * bedside phenotype and only supplies legacy phenotype drives when another source is not already doing so.
 */
private _now = CBA_missionTime;
{
    private _u = _x;
    if (isNull _u || {!local _u} || {!alive _u}) then {continue};

    private _type = "none";
    private _sev = 0;
    private _externalDrive = false;
    private _forced = _u getVariable ["ACME_shock_forced", []];
    if (_forced isEqualType [] && {count _forced >= 2}) then {
        private _until = _forced param [2,-1];
        if (_until < 0 || {_now <= _until}) then {
            _type = toLowerANSI (_forced param [0,"none"]);
            _sev = (_forced param [1,0]) max 0 min 1;
        } else {
            [_u,"ACME_shock_forced",[]] call ACME_fnc_setVarNet;
        };
    };

    if (_type == "none") then {
        private _tension = _u getVariable ["ACM_breathing_TensionPneumothorax_State", false];
        private _htx = (_u getVariable ["ACM_breathing_Hemothorax_Fluid",0]) max 0;
        if (_tension || {_htx >= 0.75}) then {
            _type = "obstructive";
            _sev = (if (_tension) then {0.70} else {0}) max (linearConversion [0.5,1.5,_htx,0.25,1,true]);
        } else {
            // Major hemorrhage remains the dominant bedside label in combat polytrauma. Sepsis physiology
            // still composes underneath it through its own HR/SVR/preload outputs.
            private _blood = _u getVariable ["ACM_circulation_Blood_Volume",6];
            if (_blood < 5.1) then {
                _type = "hemorrhagic";
                _sev = linearConversion [5.1,2.8,_blood,0.12,1,true];
            } else {
                private _sepsis = (_u getVariable ["ACM_infection_Sepsis_Severity",0]) max 0 min 1;
                if (_sepsis > 0.01) then {
                    _type = "distributive";
                    _sev = _sepsis;
                    _externalDrive = true;
                } else {
                    private _circ = _u getVariable ["ACME_circ_State", createHashMap];
                    if (_circ isEqualType createHashMap && {_circ getOrDefault ["shockActive",false]} && {!(_u getVariable ["ACME_shock_ownsCirc",false])}) then {
                        _type = "distributive";
                        _sev = (_circ getOrDefault ["shockSeverity",0.4]) max 0 min 1;
                    };
                };
            };
        };
    };

    private _svrAdj = 0;
    private _hrAdj = 0;
    if (!_externalDrive) then {
        switch (_type) do {
            case "hemorrhagic":  {_svrAdj = 28 * _sev; _hrAdj = 48 * _sev;};
            case "distributive": {_svrAdj = -48 * _sev; _hrAdj = 38 * _sev;};
            case "cardiogenic":  {_svrAdj = 24 * _sev; _hrAdj = 26 * _sev;};
            case "obstructive":  {_svrAdj = 30 * _sev; _hrAdj = 36 * _sev;};
            case "neurogenic":   {_svrAdj = -38 * _sev; _hrAdj = -32 * _sev;};
        };
    };

    [_u,"ACME_shock_resistDelta",_svrAdj,0.10,2] call ACME_fnc_setVarNetApprox;
    [_u,"ACME_shock_hrAdj",_hrAdj,0.10,2] call ACME_fnc_setVarNetApprox;

    private _ownsCirc = _u getVariable ["ACME_shock_ownsCirc",false];
    if (_type in ["cardiogenic","neurogenic","obstructive"]) then {
        private _circ = _u getVariable ["ACME_circ_State",createHashMap];
        if !(_circ isEqualType createHashMap) then {_circ = createHashMap;};
        private _oldActive = _circ getOrDefault ["shockActive",false];
        private _oldSeverity = _circ getOrDefault ["shockSeverity",0];
        _circ set ["shockActive",true];
        _circ set ["shockSeverity",_sev];
        _u setVariable ["ACME_circ_State",_circ,(!_oldActive || {abs (_oldSeverity - _sev) >= 0.005})];
        _u setVariable ["ACME_shock_ownsCirc",true,false];
        if (!isNil "ACME_circ_activePatients") then {ACME_circ_activePatients pushBackUnique _u;};
    } else {
        if (_ownsCirc) then {
            private _circ = _u getVariable ["ACME_circ_State",createHashMap];
            if (_circ isEqualType createHashMap) then {
                _circ set ["shockActive",false];
                _circ set ["shockSeverity",0];
                _u setVariable ["ACME_circ_State",_circ,true];
            };
            _u setVariable ["ACME_shock_ownsCirc",false,false];
        };
    };

    [_u,"ACME_shock_phenotype",_type] call ACME_fnc_setVarNet;
    [_u,"ACME_shock_severity",_sev,0.002,2] call ACME_fnc_setVarNetApprox;
    [_u,"ACME_shock_warm",(_type == "distributive" || {_type == "neurogenic"})] call ACME_fnc_setVarNet;
} forEach allUnits;
