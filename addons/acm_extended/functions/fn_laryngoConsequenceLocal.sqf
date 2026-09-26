/* B32: authoritative misses, graded reflexes, variable emesis and bounded attempt injury.
   Tolerance is 3..5 consecutive misses; emesis becomes possible on miss 4..6.
   This is gameplay calibration, not a clinical prediction model. */
params ["_patient", "_medic", "_epoch", "_id", "_reason"];
if (!local _patient) exitWith {[_patient, "laryngoConsequence", _this] call ACME_fnc_ownerDispatch;};
if (isNull _patient || {isNull _medic} || {!alive _medic} || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {};
if (_medic distance _patient > 5 && {isNull objectParent _medic || {objectParent _medic != objectParent _patient}}) exitWith {};
if !(_reason in ["miss", "gag", "trauma", "teeth", "jerk", "blocked", "esophageal", "success", "awakeTube", "tubeManip"]) exitWith {};
private _receipts = _patient getVariable ["ACME_laryngoEventReceipts", []];
if (_id in _receipts) exitWith {};
_receipts pushBack _id;
if (count _receipts > 64) then {_receipts deleteAt 0;};
_patient setVariable ["ACME_laryngoEventReceipts", _receipts, true];

// Adult vagal airway reflex. Routine laryngoscopy is sympathetic; this is deliberately uncommon.
// Deep cord/tracheal manipulation is the main opportunity. Hypoxemia and repeated instrumentation
// raise the probability substantially. No live HR/BP value is written here: this event only publishes
// a short source state that the authoritative HR/SVR writers consume.
if (!(_patient getVariable ["ace_medical_inCardiacArrest", false])) then {
    private _passChance = missionNamespace getVariable ["ACME_laryngo_vagalPassChance",0.015];
    private _manipChance = missionNamespace getVariable ["ACME_laryngo_vagalManipChance",0.025];
    private _baseChance = switch (_reason) do {
        case "success": {_passChance};
        case "gag": {_manipChance * 1.15};
        case "awakeTube": {_manipChance};
        case "tubeManip": {_manipChance};
        case "trauma": {_manipChance * 0.80};
        case "jerk": {_manipChance * 0.80};
        case "esophageal": {_passChance * 0.50};
        case "blocked": {_passChance * 0.35};
        case "miss": {_passChance * 0.25};
        default {0};
    };

    if (_baseChance > 0) then {
        private _spo2 = (_patient getVariable ["ace_medical_spo2",97]) max 0 min 100;
        private _hypFrac = linearConversion [92,65,_spo2,0,1,true];
        private _hypAdd = _hypFrac * (missionNamespace getVariable ["ACME_laryngo_vagalHypoxiaAddMax",0.12]);
        private _tries = (_patient getVariable ["ACME_laryngo_failCount",0]) max 0;
        private _repeatAdd = ((_tries * (missionNamespace getVariable ["ACME_laryngo_vagalRepeatAddPerTry",0.003]))
            min (missionNamespace getVariable ["ACME_laryngo_vagalRepeatAddMax",0.03]));

        private _chance = (_baseChance + _hypAdd + _repeatAdd) min 0.25;

        // Existing atropine can blunt but not rewrite the event model.
        private _atropine = 0;
        if (!isNil "ACME_fnc_medicationCountCompat") then {
            _atropine = ([_patient,"Atropine",false] call ACME_fnc_medicationCountCompat)
                + ([_patient,"Atropine_IV",false] call ACME_fnc_medicationCountCompat);
        };
        if (_atropine > 0) then {_chance = _chance * 0.35;};

        if (random 1 < _chance) then {
            private _severity = (0.45 + (0.45 * _hypFrac) + random 0.10) min 1;
            if (_atropine > 0) then {_severity = _severity * 0.55;};
            private _duration = (missionNamespace getVariable ["ACME_laryngo_vagalDurationSec",12])
                * random [0.75,1,1.25];
            _patient setVariable ["ACME_laryngo_vagalSeverity",
                (_patient getVariable ["ACME_laryngo_vagalSeverity",0]) max _severity,true];
            _patient setVariable ["ACME_laryngo_vagalUntil",
                CBA_missionTime + _duration,true];

            private _active = missionNamespace getVariable ["ACME_clinical_activePatients",[]];
            _active pushBackUnique _patient;
            missionNamespace setVariable ["ACME_clinical_activePatients",_active];
        };
    };
};

// B39: an awake patient does not calmly accept an oral ET tube, and moving a tube without a fully
// exposed airway provokes an immediate wet gag/emesis episode. These are explicit manipulation events,
// not accumulated placement misses, so they bypass the 3..5 miss tolerance while retaining owner authority.
if (_reason in ["awakeTube", "tubeManip"]) exitWith {
    // Recheck on the patient owner: the reflex may be absent now even if the UI sampled it earlier.
    // Do not roll twice or change the graded sedation model; only honor its zero-reflex exclusions.
    if (([_patient] call ACME_fnc_laryngoReflexChance) <= 0) exitWith {};
    private _old = _patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0];
    private _remaining = _patient getVariable ["ACM_airway_AirwayObstructionVomit_Count", 0];
    private _poolBefore = [_patient] call ACME_fnc_laryngoFluidState;
    private _previousVomit = if ((_poolBefore select 1) == "v") then {_poolBefore select 2} else {0};
    private _amount = if (_reason == "awakeTube") then {1 + floor random 2} else {2 + floor random 3};
    private _stage = (_previousVomit + _amount) min 8;
    [_patient, [["vomit", _old + 1], ["vomitCount", (_remaining - 1) max 0], ["vomitGrace", CBA_missionTime]], true] call ACM_airway_fnc_setAirwayState;
    _patient setVariable ["ACME_laryngo_emesis", [_id, _old + 1, _stage], true];
    _patient setVariable ["ACME_laryngo_pool", [[_old + 1, 0, [_id, _old + 1, _stage]], _stage], true];
    _patient setVariable ["ACME_laryngo_soiled", "vomit", true];
    _patient setVariable ["ACME_laryngo_gagMisses", 0, true];
    [_patient] call ACME_fnc_vomitDislodgeOPA;
    _patient setVariable ["ACME_laryngo_lastGagAt", CBA_missionTime, true];
    playSound3D [format ["acm_extended\sound\wet_gag%1_sfx.ogg", 1 + floor random 3], _patient, false, getPosASL _patient, 2.2, 1, 14];
    if (_reason == "awakeTube") then {
        private _until = CBA_missionTime + (missionNamespace getVariable ["ACME_laryngo_irritationSec", 45]);
        _patient setVariable ["ACME_laryngo_irritationUntil", _until, true];
        _patient setVariable ["ACME_laryngo_irritationNext", CBA_missionTime + 1, true];
        private _active = missionNamespace getVariable ["ACME_clinical_activePatients", []];
        _active pushBackUnique _patient;
        missionNamespace setVariable ["ACME_clinical_activePatients", _active];
    };
};

if (_reason == "success") exitWith {
    _patient setVariable ["ACME_laryngo_gagMisses", 0, true];
    _patient setVariable ["ACME_laryngo_missTolerance", 3 + floor random 3, true];
};
if (_reason in ["teeth", "trauma", "jerk"]) exitWith {
    // Real tissue trauma can contaminate an arrested airway without causing a reflex.
    if (_reason == "teeth") then {
        _patient setVariable ["ACME_laryngo_teethBroken", ((_patient getVariable ["ACME_laryngo_teethBroken", 0]) + 1) min 8, true];
        playSound3D ["a3\sounds_f\weapons\other\dry.wss", _patient, false, getPosASL _patient, 4, 1.6, 12];
    };
    if (alive _patient) then {
        private _blood = _patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0];
        // Preserve larger pre-existing injuries; attempts alone cannot manufacture a full mouth.
        [_patient, [["blood", _blood max 1]], true] call ACM_airway_fnc_setAirwayState;
        _patient setVariable ["ACME_laryngo_soiled", "blood", true];
        _patient setVariable ["ACME_laryngo_bloody", true, true];
        // Rough contact can provoke a dry response under partial sedation. It does
        // not bypass the separate consecutive-miss threshold for emesis.
        private _chance = [_patient, 2] call ACME_fnc_laryngoReflexChance;
        if (CBA_missionTime - (_patient getVariable ["ACME_laryngo_lastGagAt", -1000]) >= 0.65 && {random 1 < _chance}) then {
            _patient setVariable ["ACME_laryngo_lastGagAt", CBA_missionTime, true];
            playSound3D [format ["acm_extended\sound\dry_gag%1_sfx.ogg", 1 + floor random 3], _patient, false, getPosASL _patient, 1.4, 1, 10];
        };
    };
};
if (!alive _patient) exitWith {};
private _last = _patient getVariable ["ACME_laryngo_lastMissAt", -1000];
if (CBA_missionTime - _last < 0.65) exitWith {};
_patient setVariable ["ACME_laryngo_lastMissAt", CBA_missionTime, true];
private _misses = (_patient getVariable ["ACME_laryngo_gagMisses", 0]) + 1;
_patient setVariable ["ACME_laryngo_gagMisses", _misses, true];
_patient setVariable ["ACME_laryngo_failCount", (_patient getVariable ["ACME_laryngo_failCount", 0]) + 1, true];
private _tolerance = _patient getVariable ["ACME_laryngo_missTolerance", -1];
if (_tolerance < 3 || {_tolerance > 5}) then {
    _tolerance = 3 + floor random 3;
    _patient setVariable ["ACME_laryngo_missTolerance", _tolerance, true];
};
// Arrest is checked on the patient owner before any gag/emesis decision. Repeated
// instrumentation instead leaves a modest finite pool; there is no pumping bleed,
// autonomous refill, stomach consumption, gag sound or vomit-triggered tube ejection.
if (_patient getVariable ["ace_medical_inCardiacArrest", false]) exitWith {
    if (_misses >= _tolerance && {random 1 < 0.65}) then {
        if (random 1 < 0.65) then {
            private _secretions = _patient getVariable ["ACME_laryngo_secretions", []];
            private _amount = (_secretions param [1, 0]) + 1 + floor random 2;
            _patient setVariable ["ACME_laryngo_secretions", [_id, _amount min 4], true];
            _patient setVariable ["ACME_laryngo_soiled", "secretions", true];
        } else {
            private _blood = _patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0];
            [_patient, [["blood", _blood max 1]], true] call ACM_airway_fnc_setAirwayState;
            _patient setVariable ["ACME_laryngo_soiled", "blood", true];
            _patient setVariable ["ACME_laryngo_bloody", true, true];
        };
    };
};
private _chance = [_patient, 1 + (_misses max 0) * 0.4] call ACME_fnc_laryngoReflexChance;
// Passage has already sampled a visible gag. Recheck the live hard exclusions here
// without requiring a second random success before its sound can be heard.
private _canGag = _chance > 0 && {_reason == "gag" || {random 1 < _chance}};
private _remaining = _patient getVariable ["ACM_airway_AirwayObstructionVomit_Count", 0];
if (_misses <= _tolerance || {!_canGag} || {_remaining <= 0}) exitWith {
    if (_canGag && {CBA_missionTime - (_patient getVariable ["ACME_laryngo_lastGagAt", -1000]) >= 0.65}) then {
        _patient setVariable ["ACME_laryngo_lastGagAt", CBA_missionTime, true];
        playSound3D [format ["acm_extended\sound\dry_gag%1_sfx.ogg", 1 + floor random 3], _patient, false, getPosASL _patient, 1.4, 1, 10];
    };
};
// One finite, variable episode. Never replenish ACM's remaining stomach-content counter.
private _amount = 1 + floor random 4; // small to moderate: 1..4 of ten visual stages
private _old = _patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0];
private _poolBefore = [_patient] call ACME_fnc_laryngoFluidState;
// Blood/secretions remain separate; do not count their volume again as new vomit.
private _previousVomit = if ((_poolBefore select 1) == "v") then {_poolBefore select 2} else {0};
private _stage = (_previousVomit + _amount) min 8;
[_patient, [["vomit", _old + 1], ["vomitCount", (_remaining - 1) max 0], ["vomitGrace", CBA_missionTime]], true] call ACM_airway_fnc_setAirwayState;
// Atomic, event-specific visual volume; all open views use the same randomized amount.
_patient setVariable ["ACME_laryngo_emesis", [_id, _old + 1, _stage], true];
_patient setVariable ["ACME_laryngo_pool", [[_old + 1, 0, [_id, _old + 1, _stage]], _stage], true];
_patient setVariable ["ACME_laryngo_soiled", "vomit", true];
_patient setVariable ["ACME_laryngo_gagMisses", 0, true];
_patient setVariable ["ACME_laryngo_missTolerance", 3 + floor random 3, true];
[_patient] call ACME_fnc_vomitDislodgeOPA;
_patient setVariable ["ACME_laryngo_lastGagAt", CBA_missionTime, true];
playSound3D [format ["acm_extended\sound\wet_gag%1_sfx.ogg", 1 + floor random 3], _patient, false, getPosASL _patient, 2.2, 1, 14];
// Do not start a second autonomous vomiting worker merely because a placement was missed.
// Any already-running native disease/nausea worker keeps its normal grace period and causes.
