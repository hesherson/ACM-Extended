/*
 * Shock phenotypes layered onto ACM's existing hemodynamics.
 * The native blood-volume/pleural/circulation systems remain authoritative for the cause; this layer shapes
 * compensatory SVR/HR and exposes a phenotype for pulse/skin/training systems.
 */
private _now = CBA_missionTime;
private _candidate = {
    params ["_u"];
    if (isNull _u || {!local _u} || {!alive _u}) exitWith {false};
    private _prior = (toLowerANSI (_u getVariable ["ACME_shock_phenotype","none"])) != "none"
        || {abs (_u getVariable ["ACME_shock_severity",0]) > 0.001}
        || {abs (_u getVariable ["ACME_shock_resistDelta",0]) > 0.01}
        || {abs (_u getVariable ["ACME_shock_hrAdj",0]) > 0.01}
        || {_u getVariable ["ACME_shock_warm",false]}
        || {_u getVariable ["ACME_shock_ownsCirc",false]};
    private _forced = _u getVariable ["ACME_shock_forced", []];
    private _forcedLive = _forced isEqualType [] && {count _forced >= 2}
        && {(_forced param [2,-1]) < 0 || {_now <= (_forced param [2,-1])}};
    private _circ = _u getVariable ["ACME_circ_State", createHashMap];
    _prior || {_forcedLive}
        || {_u getVariable ["ACM_breathing_TensionPneumothorax_State", false]}
        || {(_u getVariable ["ACM_breathing_Hemothorax_Fluid",0]) >= 0.75}
        || {_circ isEqualType createHashMap && {_circ getOrDefault ["shockActive",false]}}
        || {(_u getVariable ["ACM_circulation_Blood_Volume",6]) < 5.1}
};
private _patients = (missionNamespace getVariable ["ACME_shock_activePatients", []]) select {[_x] call _candidate};
{
    private _u = _x;
    if (isNull _u || {!local _u} || {!alive _u}) then {continue};

    private _type = "none";
    private _sev = 0;
    private _hadShock = (toLowerANSI (_u getVariable ["ACME_shock_phenotype","none"])) != "none"
        || {abs (_u getVariable ["ACME_shock_severity",0]) > 0.001}
        || {abs (_u getVariable ["ACME_shock_resistDelta",0]) > 0.01}
        || {abs (_u getVariable ["ACME_shock_hrAdj",0]) > 0.01}
        || {_u getVariable ["ACME_shock_warm",false]}
        || {_u getVariable ["ACME_shock_ownsCirc",false]};
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

    private _tension = _u getVariable ["ACM_breathing_TensionPneumothorax_State", false];
    private _htx = (_u getVariable ["ACM_breathing_Hemothorax_Fluid",0]) max 0;
    private _circProbe = _u getVariable ["ACME_circ_State", createHashMap];
    private _circShock = (_circProbe isEqualType createHashMap) && {_circProbe getOrDefault ["shockActive",false]}
        && {!(_u getVariable ["ACME_shock_ownsCirc",false])};
    private _blood = _u getVariable ["ACM_circulation_Blood_Volume",6];
    private _forcedActive = _type != "none";

    // A healthy unit with no previous shock output is completely silent. Once a
    // phenotype existed, run one neutralization pass and then retire naturally.
    if (!_forcedActive && {!_tension} && {_htx < 0.75} && {!_circShock} && {_blood >= 5.1} && {!_hadShock}) then {continue};

    if (_type == "none") then {
        // Obstructive shock outranks hypovolemia because its pulse/pressure character is clinically distinct.
        if (_tension || {_htx >= 0.75}) then {
            _type = "obstructive";
            _sev = (if (_tension) then {0.70} else {0}) max (linearConversion [0.5,1.5,_htx,0.25,1,true]);
        } else {
            if (_circShock) then {
                _type = "distributive";
                _sev = (_circProbe getOrDefault ["shockSeverity",0.4]) max 0 min 1;
            } else {
                if (_blood < 5.1) then {
                    _type = "hemorrhagic";
                    _sev = linearConversion [5.1,2.8,_blood,0.12,1,true];
                };
            };
        };
    };

    private _svrAdj = 0;
    private _hrAdj = 0;
    switch (_type) do {
        case "hemorrhagic":  {_svrAdj = 28 * _sev; _hrAdj = 48 * _sev;};
        case "distributive": {_svrAdj = -48 * _sev; _hrAdj = 38 * _sev;};
        case "cardiogenic":  {_svrAdj = 24 * _sev; _hrAdj = 26 * _sev;};
        case "obstructive":  {_svrAdj = 30 * _sev; _hrAdj = 36 * _sev;};
        case "neurogenic":   {_svrAdj = -38 * _sev; _hrAdj = -32 * _sev;};
    };

    // Publish source-separated hemodynamic drives. The authoritative fork-native HR/resistance endpoints
    // compose these once with native physiology; this PFH never fights those writers directly.
    [_u,"ACME_shock_resistDelta",_svrAdj,([0.10,0] select (_svrAdj == 0)),0] call ACME_fnc_setVarNetApprox;
    [_u,"ACME_shock_hrAdj",_hrAdj,([0.10,0] select (_hrAdj == 0)),0] call ACME_fnc_setVarNetApprox;

    // Forced cardiogenic/neurogenic shock needs a pressure-failure component even with preserved blood volume.
    // Reuse ACME's established shock MAP-drop state, and relinquish it cleanly when this layer no longer owns it.
    private _ownsCirc = _u getVariable ["ACME_shock_ownsCirc",false];
    if (_type in ["cardiogenic","neurogenic","obstructive"]) then {
        private _circ = _u getVariable ["ACME_circ_State",createHashMap];
        if !(_circ isEqualType createHashMap) then {_circ = createHashMap;};
        private _oldActive = _circ getOrDefault ["shockActive",false];
        private _oldSeverity = _circ getOrDefault ["shockSeverity",0];
        _circ set ["shockActive",true];
        _circ set ["shockSeverity",_sev];
        if (!_oldActive || {abs (_oldSeverity - _sev) >= 0.005}) then {
            [_u, _circ] call ACME_fnc_circStateCommit;
        } else {
            _u setVariable ["ACME_circ_State",_circ,false];
        };
        _u setVariable ["ACME_shock_ownsCirc",true,false];
        if (!isNil "ACME_circ_activePatients") then {ACME_circ_activePatients pushBackUnique _u;};
    } else {
        if (_ownsCirc) then {
            private _circ = _u getVariable ["ACME_circ_State",createHashMap];
            if (_circ isEqualType createHashMap) then {
                private _wasActive = _circ getOrDefault ["shockActive",false];
                private _wasSeverity = _circ getOrDefault ["shockSeverity",0];
                _circ set ["shockActive",false];
                _circ set ["shockSeverity",0];
                if (_wasActive || {_wasSeverity != 0}) then {
                    [_u, _circ] call ACME_fnc_circStateCommit;
                } else {
                    _u setVariable ["ACME_circ_State",_circ,false];
                };
            };
            _u setVariable ["ACME_shock_ownsCirc",false,false];
        };
    };

    [_u,"ACME_shock_phenotype",_type] call ACME_fnc_setVarNet;
    [_u,"ACME_shock_severity",_sev,([0.002,0] select (_sev == 0)),0] call ACME_fnc_setVarNetApprox;
    [_u,"ACME_shock_warm",(_type == "distributive" || {_type == "neurogenic"})] call ACME_fnc_setVarNet;
} forEach _patients;
ACME_shock_activePatients = _patients select {[_x] call _candidate};
