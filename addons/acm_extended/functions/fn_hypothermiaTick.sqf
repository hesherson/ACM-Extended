// the auto-hypothermia driver, which is the third leg of the trauma lethal triad happening on its own. it runs on
// a slow pfh and is cool-only, because rewarming stays the job of the HPMK and cool-only never fights the debug
// tool.
// the real-life model: hypothermia here is injury-driven. the cold load comes from hemorrhage, through impaired
// thermogenesis and hypoperfusion, and from cold stored products, in a massive transfusion. the ambient
// temperature is only a multiplier on that injury load. a cold field accelerates the cooling of a casualty and a
// warm one slows it, and ambient alone never cools a healthy, uninjured soldier, because no injury load means no
// drop however cold the map is. patients wrapped in an HPMK are skipped, because the rewarming of the blanket
// owns them.
// the cold loads are:
// 1. cumulative blood loss, the primary one. it is the total liters bled, as an accumulator, so transfusion
// top-ups do not undo it.
// 2. massive transfusion, the secondary one. it is cold stored products, from
// ACM_circulation_TransfusedBlood_Volume.
// 3. ambient temperature, a multiplier on 1 and 2 only. cold amplifies and warm attenuates.

// the system toggle, read live, so unticking hypothermia in addon options stops this system immediately and
// completely with no mission restart.
if !(missionNamespace getVariable ["ACME_sys_hypothermia", true]) exitWith {};
private _coolStep = (missionNamespace getVariable ["ACME_hypo_coolRatePerMin", 0.5]) * ((missionNamespace getVariable ["ACME_hypo_coolTickSec", 5]) / 60);
private _floor = missionNamespace getVariable ["ACME_hypo_floorC", 28];
private _bloodNormal = missionNamespace getVariable ["ACME_hypo_bloodNormal", 6];

// cumulative blood loss into the target drop, the primary source.
private _lossStart = missionNamespace getVariable ["ACME_hypo_lossStartL", 0.8];
private _lossFull  = missionNamespace getVariable ["ACME_hypo_lossFullL", 2.5];
private _maxLoss   = missionNamespace getVariable ["ACME_hypo_lossMaxDrop", 6];
// massive transfusion into the target drop, the secondary source.
private _txStart = missionNamespace getVariable ["ACME_hypo_txStartL", 1.0];
private _txFull  = missionNamespace getVariable ["ACME_hypo_txFullL", 3.0];
private _maxTx   = missionNamespace getVariable ["ACME_hypo_txMaxDrop", 3];
// the ambient multiplier on the injury-driven drop. cold is above 1 and warm is below 1.
private _ambCold = missionNamespace getVariable ["ACME_hypo_ambientColdC", -10];
private _ambWarm = missionNamespace getVariable ["ACME_hypo_ambientWarmC", 30];
private _ambMaxMult = missionNamespace getVariable ["ACME_hypo_ambientMaxMult", 1.6];
private _ambMinMult = missionNamespace getVariable ["ACME_hypo_ambientMinMult", 0.75];

// the AFib-RVR trigger: severe hypothermia commonly throws atrial fibrillation.
private _afibTempC  = missionNamespace getVariable ["ACME_rhythm_afibHypoTempC", 32];
private _afibChance = missionNamespace getVariable ["ACME_rhythm_afibHypoChance", 0.15];

{
    private _u = _x;
    private _hpmkOn = _u getVariable ["ACME_hpmk_on", false];

    // Infection owns only the requested fever offset. This established writer owns
    // the actual core-temperature state, so hypothermia, HPMK and fever cannot race.
    private _feverOffset = (_u getVariable ["ACM_infection_Fever_Offset", 0]) max 0;
    private _feverActive = _u getVariable ["ACME_infectionFeverActive", false];

    private _bv = _u getVariable ["ACM_circulation_Blood_Volume", _bloodNormal];
    private _tx = _u getVariable ["ACM_circulation_TransfusedBlood_Volume", 0];

    // the cumulative blood loss accumulator, which only ever increases from bleeding.
    private _lastBV = _u getVariable ["ACME_hypo_lastBV", _bv];
    private _cumLoss = _u getVariable ["ACME_hypo_cumLoss", 0];
    if (_bv < _lastBV) then { _cumLoss = _cumLoss + (_lastBV - _bv); };
    _u setVariable ["ACME_hypo_lastBV", _bv];

    // cold-load recovery.
    // when the driver is controlled, the thermal debt clears. the gates are: not actively bleeding, with ACE
    // getbloodloss at or below the controlled threshold, perfusing, with a MAP above the floor, and not below the
    // severe-hypothermia floor, below which the body cannot self-rewarm and must be actively rewarmed. an HPMK on
    // accelerates the decay.
    // this runs for wrapped and unwrapped patients alike, and the wrapped ones simply clear faster, which is why it is
    // here, before the HPMK skip below.
    private _recovering = false;
    if (_cumLoss > 0 || {(_u getVariable ["ACME_hypo_temp", 37]) < 36.9}) then {
        private _tempNow = _u getVariable ["ACME_hypo_temp", 37];
        private _selfFloor = missionNamespace getVariable ["ACME_hypo_selfRecoverFloorC", 30];
        if (_tempNow > _selfFloor) then {
            private _bleedNow = [_u] call ace_medical_status_fnc_getBloodLoss;
            private _controlled = _bleedNow <= (missionNamespace getVariable ["ACME_hypo_recoverBleedMax", 0.00002]);
            if (_controlled) then {
                private _bpR = _u call ace_medical_status_fnc_getBloodPressure;
                _bpR params [["_dR", 0], ["_sR", 0]];
                private _mapR = _dR + ((_sR - _dR) / 3);
                if (_mapR >= (missionNamespace getVariable ["ACME_hypo_recoverMinMAP", 55])) then {
                    _recovering = true;
                    private _decayPerMin = missionNamespace getVariable ["ACME_hypo_recoverPerMin", 0.35];
                    if (_hpmkOn) then {
                        _decayPerMin = _decayPerMin * (missionNamespace getVariable ["ACME_hypo_recoverHPMKmult", 2.0]);
                    };
                    private _decayStep = _decayPerMin * ((missionNamespace getVariable ["ACME_hypo_coolTickSec", 5]) / 60);
                    _cumLoss = (_cumLoss - _decayStep) max 0;

                    // passive self-rewarming. once the driver is controlled and they are perfusing, the body generates its own heat.
                    // for an unwrapped patient, because the HPMK tick already rewarms wrapped ones and faster, the core temp drifts
                    // up toward normal at a slow passive rate. it is still gated above the severe floor, below which there is no
                    // self-rewarming and the HPMK is mandatory. this is what lets hypothermia actually resolve in the field after
                    // hemorrhage control with no blanket, just slowly.
                    if (!_hpmkOn) then {
                        private _tNow = _u getVariable ["ACME_hypo_temp", 37];
                        if (_tNow < 36.9) then {
                            private _selfWarmStep = (missionNamespace getVariable ["ACME_hypo_selfRewarmPerMin", 0.15]) * ((missionNamespace getVariable ["ACME_hypo_coolTickSec", 5]) / 60);
                            [_u, ((_tNow + _selfWarmStep) min 37), true, true, false] call ACME_fnc_hypothermiaTemperatureCommit;
                        };
                    };
                };
            };
        };
    };
    _u setVariable ["ACME_hypo_cumLoss", _cumLoss];

    // the injury-driven cold load, primary plus secondary. no injury load means no hypothermia.
    private _lossDrop = linearConversion [_lossStart, _lossFull, _cumLoss, 0, _maxLoss, true];
    private _txDrop   = linearConversion [_txStart, _txFull, _tx, 0, _maxTx, true];
    private _baseDrop = _lossDrop + _txDrop;

    // the cooling application. it is skipped for HPMK-wrapped patients, because the rewarming tick of the blanket owns
    // their temperature, and the cold-load recovery above, which did run for them, has already been
    // HPMK-accelerated. the accumulator and the recovery run for everyone, and only the active pull-down toward the
    // cold target is the HPMK's to suppress.
    if (!_hpmkOn && {!_recovering} && {_baseDrop > 0.01}) then {
        // ambient only scales an existing injury load.
        private _ambient = [getPosASL _u] call ACME_fnc_ambientTemp;
        // flight chill. it is subtracted here, at the single point where the question of how cold it is around this
        // casualty is answered, so it flows into the existing hypothermia model and straight on into the lethal triad
        // with no new pathway. the flight that is supposed to save them is cooling their clotting cascade the whole way,
        // and an HPMK on before launch shuts almost all of it off.
        _ambient = _ambient - ([_u] call ACME_fnc_flightChill);
        private _ambMult = linearConversion [_ambCold, _ambWarm, _ambient, _ambMaxMult, _ambMinMult, true];
        private _target = (37 - (_baseDrop * _ambMult)) max _floor;

        private _temp = _u getVariable ["ACME_hypo_temp", 37];
        if (_temp > _target) then {
            private _new = (_temp - _coolStep) max _target;
            [_u, _new, true, true, false] call ACME_fnc_hypothermiaTemperatureCommit;
            if (_new < 36) then { ACME_circ_activePatients pushBackUnique _u; };
        };
    };

    // Apply fever last so an infection's prescribed thermal response is not
    // overwritten by the same tick's trauma-cooling calculation. Fever recovery
    // is likewise owned here and returns only a fever-raised temperature to 37 C.
    private _tempAfterTrauma = _u getVariable ["ACME_hypo_temp", 37];
    if (_feverOffset > 0) then {
        private _feverTarget = (37 + _feverOffset) min 40.5;
        if (_tempAfterTrauma < _feverTarget) then {
            [_u, (_tempAfterTrauma + (0.25 * (ACME_hypo_coolTickSec / 5))) min _feverTarget, true, true, false] call ACME_fnc_hypothermiaTemperatureCommit;
        };
        _u setVariable ["ACME_infectionFeverActive", true, false];
    } else {
        if (_feverActive && {_tempAfterTrauma > 37}) then {
            private _cooled = (_tempAfterTrauma - (0.15 * (ACME_hypo_coolTickSec / 5))) max 37;
            [_u, _cooled, true, true, false] call ACME_fnc_hypothermiaTemperatureCommit;
            if (_cooled <= 37) then { _u setVariable ["ACME_infectionFeverActive", false, false]; };
        };
    };

    // severe hypothermia, at or below afibtempc, gives a chance of AFib with RVR.
    if ((_u getVariable ["ACME_hypo_temp", 37]) <= _afibTempC
        && {(_u getVariable ["ACME_rhythm_active", 0]) == 0}
        && {alive _u} && {!(_u getVariable ["ace_medical_inCardiacArrest", false])}
        && {random 1 < _afibChance}
    ) then {
        [objNull, _u, 100, "AFib with RVR", (missionNamespace getVariable ["ACME_rhythm_afibHR", 150])] call ACME_fnc_rhythmToggle;
        // the activity-log line is removed, because it revealed the condition of the patient.
    };
} forEach (allUnits select {
    local _x && {alive _x} && {
        ((_x getVariable ["ACM_circulation_Blood_Volume", _bloodNormal]) < (_bloodNormal - 0.2))  // bled.
        || {(_x getVariable ["ACM_circulation_TransfusedBlood_Volume", 0]) > 0}  // transfused.
        || {(_x getVariable ["ACME_hypo_temp", 37]) < 36.9}  // already cooling.
        || {(_x getVariable ["ACM_infection_Fever_Offset", 0]) > 0}  // infection fever.
        || {_x getVariable ["ACME_infectionFeverActive", false]}  // fever recovery.
    }
});
