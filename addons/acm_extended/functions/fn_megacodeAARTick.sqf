/* Objective Megacode instructor timeline. No score: record what happened and when. */
{
    private _u = _x;
    if (isNull _u || {!local _u} || {!(_u getVariable ["ACME_isMegacode",false])}) then {continue};
    if (isNil {_u getVariable "ACME_MC_aarStart"}) then {[_u] call ACME_fnc_megacodeAARReset;};

    private _last = _u getVariable ["ACME_MC_aarLast",createHashMap];
    if !(_last isEqualType createHashMap) then {_last = createHashMap;};

    private _scen = _u getVariable ["ACME_MC_scenActive",false];
    private _prevScen = _last getOrDefault ["scenario",false];
    if (_scen && {!_prevScen}) then {
        [_u] call ACME_fnc_megacodeAARReset;
        _last = createHashMap;
        [_u,"scenario",format ["Scenario started: %1",_u getVariable ["ACME_MC_scenName","unnamed"]],0] call ACME_fnc_megacodeAARRecord;
    };
    _last set ["scenario",_scen];

    private _arrest = _u getVariable ["ace_medical_inCardiacArrest",false];
    private _prevArrest = _last getOrDefault ["arrest",false];
    if (_arrest && {!_prevArrest}) then {[_u,"arrest","Cardiac arrest",2] call ACME_fnc_megacodeAARRecord;};
    if (!_arrest && {_prevArrest}) then {[_u,"rosc","ROSC / arrest state cleared",0] call ACME_fnc_megacodeAARRecord;};
    _last set ["arrest",_arrest];

    private _cpr = alive (_u getVariable ["ace_medical_CPR_provider",objNull]);
    private _prevCPR = _last getOrDefault ["cpr",false];
    if (_cpr != _prevCPR) then {
        [_u,"cpr",if (_cpr) then {"CPR started"} else {"CPR stopped"},if (_cpr) then {1} else {0}] call ACME_fnc_megacodeAARRecord;
    };
    _last set ["cpr",_cpr];

    private _rhythm = if (!isNil "ACME_fnc_rhythmGet") then {[_u] call ACME_fnc_rhythmGet} else {-1};
    private _prevRhythm = _last getOrDefault ["rhythm",-999];
    if (_rhythm != _prevRhythm) then {
        // the rhythm by name (the codes of ACME_fnc_megacodeSetRhythm), not the bare number.
        private _rhythmName = createHashMapFromArray [
            [0,"sinus"],[1,"asystole"],[2,"VF"],[3,"pulseless VT"],[4,"VT"],[5,"PEA"],
            [100,"A-fib RVR"],[101,"atrial tach"],[102,"torsades"],[103,"A-fib"],[104,"SVT"]
        ] getOrDefault [_rhythm, str _rhythm];
        [_u,"rhythm",format ["Rhythm changed: %1",_rhythmName],0] call ACME_fnc_megacodeAARRecord;
    };
    _last set ["rhythm",_rhythm];

    private _ett = _u getVariable ["ACME_ETT_Inserted",false];
    if (_ett && {!(_last getOrDefault ["ett",false])}) then {[_u,"airway","ET tube passed",0] call ACME_fnc_megacodeAARRecord;};
    _last set ["ett",_ett];
    private _cuff = _u getVariable ["ACME_ETT_CuffInflated",false];
    if (_cuff && {!(_last getOrDefault ["cuff",false])}) then {[_u,"airway","ETT cuff inflated / definitive airway",0] call ACME_fnc_megacodeAARRecord;};
    _last set ["cuff",_cuff];

    private _vent = _u getVariable ["ACME_vent_onPatient",false];
    if (_vent != (_last getOrDefault ["vent",false])) then {
        [_u,"vent",if (_vent) then {"Ventilator connected"} else {"Ventilator disconnected"},0] call ACME_fnc_megacodeAARRecord;
    };
    _last set ["vent",_vent];

    private _nrb = _u getVariable ["ACME_nrb_on",false];
    if (_nrb != (_last getOrDefault ["nrb",false])) then {[_u,"oxygen",if (_nrb) then {"NRB applied"} else {"NRB removed"},0] call ACME_fnc_megacodeAARRecord;};
    _last set ["nrb",_nrb];

    private _shock = _u getVariable ["ACME_shock_phenotype","none"];
    if (_shock != (_last getOrDefault ["shock","none"])) then {
        [_u,"shock",format ["Shock phenotype: %1 (%2%%)",_shock,round ((_u getVariable ["ACME_shock_severity",0])*100)],1] call ACME_fnc_megacodeAARRecord;
    };
    _last set ["shock",_shock];

    private _asp = (_u getVariable ["ACME_aspiration_load",0]) max 0;
    private _prevAsp = _last getOrDefault ["aspiration",0];
    if (_asp >= 0.08 && {_prevAsp < 0.08}) then {[_u,"aspiration",format ["Aspiration lung injury detected (%1%%)",round (_asp*100)],2] call ACME_fnc_megacodeAARRecord;};
    _last set ["aspiration",_asp];

    private _meds = _u getVariable ["ace_medical_medications",[]];
    private _seen = _u getVariable ["ACME_MC_aarSeenMeds",[]];
    {
        private _med = _x param [0,""];
        private _added = _x param [1,-1];
        private _key = format ["%1:%2",_med,_added];
        if (_med != "" && {!(_key in _seen)}) then {
            _seen pushBack _key;
            [_u,"med",format ["Medication: %1",_med],0] call ACME_fnc_megacodeAARRecord;
        };
    } forEach _meds;
    if (count _seen > 80) then {_seen deleteRange [0,(count _seen)-80];};
    _u setVariable ["ACME_MC_aarSeenMeds",_seen,false];

    private _tx = _u getVariable ["ACM_circulation_TransfusedBlood_Volume",0];
    private _prevTx = _last getOrDefault ["transfused",0];
    if (_tx >= (_prevTx + 0.45)) then {
        [_u,"blood",format ["Transfused blood total: %1 L",(_tx toFixed 1)],0] call ACME_fnc_megacodeAARRecord;
        _last set ["transfused",_tx];
    };

    private _spo2 = _u getVariable ["ace_medical_spo2",100];
    private _worst = (_u getVariable ["ACME_MC_aarWorstSpO2",100]) min _spo2;
    if (_worst < (_u getVariable ["ACME_MC_aarWorstSpO2",100])) then {
        _u setVariable ["ACME_MC_aarWorstSpO2",_worst,true];
    };
    private _bp = if (!isNil "ace_medical_status_fnc_getBloodPressure") then {[_u] call ace_medical_status_fnc_getBloodPressure} else {[0,0]};
    _bp params ["_dbp","_sbp"];
    private _lowSBP = (_u getVariable ["ACME_MC_aarLowestSBP",999]) min _sbp;
    if (_lowSBP < (_u getVariable ["ACME_MC_aarLowestSBP",999])) then {
        _u setVariable ["ACME_MC_aarLowestSBP",_lowSBP,true];
    };
    private _hypoxBand = if (_spo2 < 80) then {2} else {if (_spo2 < 90) then {1} else {0}};
    if (_hypoxBand > (_last getOrDefault ["hypox",0])) then {[_u,"hypoxia",format ["SpO2 crossed %1%%",if (_hypoxBand==2) then {80} else {90}],_hypoxBand] call ACME_fnc_megacodeAARRecord;};
    _last set ["hypox",_hypoxBand];
    private _hypotBand = if (_sbp > 0 && {_sbp < 70}) then {2} else {if (_sbp > 0 && {_sbp < 90}) then {1} else {0}};
    if (_hypotBand > (_last getOrDefault ["hypot",0])) then {[_u,"hypotension",format ["SBP crossed %1 mmHg",if (_hypotBand==2) then {70} else {90}],_hypotBand] call ACME_fnc_megacodeAARRecord;};
    _last set ["hypot",_hypotBand];

    _u setVariable ["ACME_MC_aarLast",_last,false];
} forEach (+(missionNamespace getVariable ["ACME_megacode_units", []]));
ACME_megacode_units = (missionNamespace getVariable ["ACME_megacode_units", []]) select {
    !isNull _x && {_x getVariable ["ACME_isMegacode", false]}
};
