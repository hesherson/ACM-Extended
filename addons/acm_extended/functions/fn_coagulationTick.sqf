/* B156: integrated clot strength, active patients at 5 Hz with a 2 s discovery fallback.
 * Explicit candidates are used by owner/treatment registration and circulation changes.
 * Healthy units keep implicit neutral defaults and generate no periodic coagulation packets.
 */
params [["_candidates", [], [[]]]];
private _active = (missionNamespace getVariable ["ACME_coag_activePatients", []]) select {!isNull _x && {local _x} && {alive _x}};
private _patients = +_candidates;
if (_patients isEqualTo []) then {
    _patients = +_active;
    private _lastSweep = missionNamespace getVariable ["ACME_coag_lastSweep", -1];
    if (_lastSweep < 0 || {CBA_missionTime - _lastSweep >= 2}) then {
        missionNamespace setVariable ["ACME_coag_lastSweep", CBA_missionTime];
        {_patients pushBackUnique _x;} forEach allUnits;
    };
};
{
    private _u = _x;
    if (!isNull _u && {local _u} && {alive _u}) then {
        // The base has a dedicated writer contract. Rebuild from input physiology after transfer,
        // including saves from versions whose only stored value was the combined output.
        private _base = ([_u] call ACME_fnc_coagulationBase) select 0;
        private _infectionCoag = (_u getVariable ["ACM_infection_Coag_Mult",1]) max 1;
        private _pathologyBase = _base * _infectionCoag;
        private _platelets = (_u getVariable ["ACM_circulation_Platelet_Count",3]) max 0;
        private _saline = (_u getVariable ["ACM_circulation_Saline_Volume",0]) max 0;
        private _plasmaVol = (_u getVariable ["ACM_circulation_Plasma_Volume",0]) max 0;
        private _givenMl = (_u getVariable ["ACME_circ_salineGivenMl",0]) max 0;
        // Retain TXA through its onset phase; an effect of zero is not a completed treatment.
        private _hasTXA = ((_u getVariable ["ace_medical_medications",[]]) findIf {(_x param [0,""]) == "TXA_IV"}) >= 0;
        private _needs = _pathologyBase > 1 || {_platelets < 3} || {_saline > 0} || {_plasmaVol > 0} || {_givenMl > 0} || {_hasTXA};
        private _hadEffect = (_u getVariable ["ACME_ca_coagMult",1]) != 1
            || {(_u getVariable ["ACME_ca_coagBaseMult",1]) != 1}
            || {(_u getVariable ["ACME_coag_clotStrength",1]) != 1}
            || {(_u getVariable ["ACME_coag_dilutionSeverity",0]) != 0}
            || {(_u getVariable ["ACME_coag_extraMult",1]) != 1};
        if (_needs || {_hadEffect}) then {
            private _plateletStrength = linearConversion [0,3,_platelets,0.18,1,true];
            // Redistributed crystalloid still contributes to factor dilution. Plasma supplies factors.
            private _dilutionLoad = (_saline + (_givenMl / 1000 * 0.35)) max 0;
            private _dilutionSeverity = linearConversion [0.5,2.5,_dilutionLoad,0,1,true];
            private _dilutionMult = 1 + (0.70 * _dilutionSeverity);
            private _txa = ([_u,"TXA_IV",false] call ACME_fnc_medicationCountCompat) max 0 min 2;
            private _txaBenefit = linearConversion [0,1.5,_txa,0,0.18,true];
            private _factorBenefit = linearConversion [0,1.5,_plasmaVol,0,0.22,true];
            private _combinedBurden = (_pathologyBase max 1) * _dilutionMult;
            private _strength = ((_plateletStrength / _combinedBurden) + _txaBenefit + _factorBenefit) max 0.08 min 1.15;
            private _extraMult = (1 / (_strength max 0.10)) max 1 min 3.0;
            private _published = (_pathologyBase * _extraMult) max 1 min 5;
            // Replicated object values already survive JIP. Send changes and owner refreshes,
            // retaining exact owner values without a stable-value heartbeat every three seconds.
            // Neutral endpoints are exact so retirement cannot strand a sub-threshold remote residue.
            [_u,"ACME_ca_coagBaseMult",_pathologyBase,([0.005,0] select (_pathologyBase == 1)),0] call ACME_fnc_setVarNetApprox;
            [_u,"ACME_coag_clotStrength",_strength,([0.002,0] select (_strength == 1)),0] call ACME_fnc_setVarNetApprox;
            [_u,"ACME_coag_dilutionSeverity",_dilutionSeverity,([0.002,0] select (_dilutionSeverity == 0)),0] call ACME_fnc_setVarNetApprox;
            [_u,"ACME_coag_extraMult",_extraMult,([0.005,0] select (_extraMult == 1)),0] call ACME_fnc_setVarNetApprox;
            [_u,"ACME_ca_coagMult",_published,([0.005,0] select (_published == 1)),0] call ACME_fnc_setVarNetApprox;
        };
        if (_needs) then {_active pushBackUnique _u;} else {_active = _active - [_u];};
    };
} forEach (_patients arrayIntersect _patients);
missionNamespace setVariable ["ACME_coag_activePatients", _active];
