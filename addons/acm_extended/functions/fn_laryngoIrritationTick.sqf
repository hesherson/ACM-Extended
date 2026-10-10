/* B120 persistent laryngeal/airway contamination after an awake or inadequately sedated tube attempt.
   This models repeated gagging/secretions plus occasional minor instrumentation blood and finite emesis.  Cardiac
   arrest and neuromuscular paralysis stop the physical reflex. Adequate hypnotic effect terminates the episode. */
params ["_patient"];
if (isNull _patient || {!alive _patient} || {!local _patient}) exitWith {};
private _now = CBA_missionTime;
private _until = _patient getVariable ["ACME_laryngo_irritationUntil", 0];
if !(_until isEqualType 0 && {finite _until} && {_until > _now}) exitWith {};
if (_patient getVariable ["ace_medical_inCardiacArrest", false]) exitWith {
    _patient setVariable ["ACME_laryngo_irritationUntil", 0, true];
};
if (_patient getVariable ["ACME_roc_paralyzed", false]) exitWith {};
private _sed = [_patient] call ACME_fnc_sedationOnBoard;
if (_sed >= (missionNamespace getVariable ["ACME_laryngo_proceduralSedation", 0.75])) exitWith {
    _patient setVariable ["ACME_laryngo_irritationUntil", 0, true];
};
private _next = _patient getVariable ["ACME_laryngo_irritationNext", 0];
if (_now < _next) exitWith {};
private _min = missionNamespace getVariable ["ACME_laryngo_irritationPulseMin", 2.0];
private _max = (missionNamespace getVariable ["ACME_laryngo_irritationPulseMax", 3.5]) max _min;
_patient setVariable ["ACME_laryngo_irritationNext", _now + _min + random (_max - _min), true];
private _id = format ["awake-%1-%2", [_patient] call ACME_fnc_clinicalEpoch, floor (_now * 10)];

// Gag cadence is not a fluid generator. Ongoing irritation replenishes only at
// bounded intervals, and actual suction postpones passive recollection for 30s.
if (_now >= (_patient getVariable ["ACME_airwaySecretionRefillAt", 0])) then {
    private _secretions = _patient getVariable ["ACME_laryngo_secretions", []];
    private _secStage = ((_secretions param [1, 0]) + 1) min 4;
    _patient setVariable ["ACME_laryngo_secretions", [_id, _secStage], true];
    _patient setVariable ["ACME_laryngo_soiled", "secretions", true];
    _patient setVariable ["ACME_airwaySecretionRefillAt", _now + 30, true];
};
if (_now >= (_patient getVariable ["ACME_airwayBloodRefillAt", 0]) && {random 1 < 0.22}) then {
    private _blood = _patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0];
    [_patient, [["blood", _blood max ((_blood + 1) min 3)]], true] call ACM_airway_fnc_setAirwayState;
    _patient setVariable ["ACME_laryngo_bloody", true, true];
    _patient setVariable ["ACME_laryngo_soiled", "blood", true];
    _patient setVariable ["ACME_airwayBloodRefillAt", _now + 30, true];
};

// Vomit remains finite: consume native stomach contents rather than creating an infinite reservoir. Secretions
// and minor blood can continue for the full irritation episode after that reserve is exhausted.
private _remaining = _patient getVariable ["ACM_airway_AirwayObstructionVomit_Count", 0];
if (_remaining > 0 && {random 1 < 0.30}) then {
    private _old = _patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0];
    private _poolBefore = [_patient] call ACME_fnc_laryngoFluidState;
    private _previousVomit = if ((_poolBefore select 1) == "v") then {_poolBefore select 2} else {0};
    private _stage = (_previousVomit + 1 + floor random 2) min 8;
    [_patient, [["vomit", _old + 1], ["vomitCount", (_remaining - 1) max 0], ["vomitGrace", _now]], true] call ACM_airway_fnc_setAirwayState;
    _patient setVariable ["ACME_laryngo_emesis", [_id, _old + 1, _stage], true];
    _patient setVariable ["ACME_laryngo_pool", [[_old + 1, 0, [_id, _old + 1, _stage]], _stage], true];
    _patient setVariable ["ACME_laryngo_soiled", "vomit", true];
    [_patient] call ACME_fnc_vomitDislodgeOPA;
    playSound3D [format ["acm_extended\sound\wet_gag%1_sfx.ogg", 1 + floor random 3], _patient, false, getPosASL _patient, 1.8, 1, 12];
} else {
    if (random 1 < 0.45) then {
        playSound3D [format ["acm_extended\sound\dry_gag%1_sfx.ogg", 1 + floor random 3], _patient, false, getPosASL _patient, 1.2, 1, 9];
    };
};
