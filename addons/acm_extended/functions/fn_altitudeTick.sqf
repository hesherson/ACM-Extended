// Cabin pressure affects existing trapped gas only when pressure changes.
// Hypobaric oxygen availability and transient maneuver stress remain independent.
params ["_patient"];
if (isNull _patient || {!local _patient} || {!alive _patient} || {!(_patient isKindOf "CAManBase")}) exitWith {};
if (!(missionNamespace getVariable ["ACME_sys_flight", true])
    || {!(missionNamespace getVariable ["ACME_altitude_enable", true])}) exitWith {
    // Re-enabling starts at current cabin pressure, without replaying travel while off.
    _patient setVariable ["ACME_alt_ptxSample", nil, false];
    _patient setVariable ["ACME_alt_tickStamp", nil, false];
    [_patient, "ACME_alt_expanding", false] call ACME_fnc_setVarNet;
    [_patient, "ACME_alt_pRatio", 1] call ACME_fnc_setVarNet;
    [_patient, "ACME_alt_ambientRatio", 1] call ACME_fnc_setVarNet;
    [_patient, "ACME_alt_hypoxia", 0] call ACME_fnc_setVarNet;
    [_patient, "ACME_flightG_stress", 0] call ACME_fnc_setVarNet;
    [_patient, "ACME_flightG_resistAdd", 0] call ACME_fnc_setVarNet;
};

private _exposure = [_patient] call ACME_fnc_flightExposure;
private _alt = _exposure select 0;
if (!finite _alt) exitWith {_patient setVariable ["ACME_alt_ptxSample", nil, false];};
_alt = _alt max 0;
private _pRatio = _exposure select 2;
private _now = CBA_missionTime;
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
// Process a given owner/epoch/pressure sample once. A teleport that changes
// pressure at the same clock instant still gets its new observation.
private _stamp = [clientOwner, _epoch, _now, _pRatio];
if ((_patient getVariable ["ACME_alt_tickStamp", []]) isEqualTo _stamp) exitWith {};
_patient setVariable ["ACME_alt_tickStamp", _stamp, false];
[_patient, "ACME_alt_m", round _alt, 10, 2] call ACME_fnc_setVarNetApprox;
[_patient, "ACME_alt_ambientRatio", _exposure select 1, 0.002, 2] call ACME_fnc_setVarNetApprox;
[_patient, "ACME_alt_pRatio", _pRatio, 0.002, 2] call ACME_fnc_setVarNetApprox;

// Owner-local history is cleared by ownerInit on locality transfer. The epoch
// and short sample age also exclude reset/load/stall catch-up. The first valid
// observation establishes a baseline; it cannot create or worsen an injury.
private _sample = _patient getVariable ["ACME_alt_ptxSample", []];
private _sampleValid = _sample isEqualType [] && {count _sample == 4};
if (_sampleValid) then {
    _sample params ["_lastPressure", "_lastOwner", "_lastEpoch", "_lastTime"];
    _sampleValid = _lastPressure isEqualType 0 && {finite _lastPressure}
        && {_lastPressure >= 0.000000001} && {_lastPressure <= 1}
        && {_lastOwner isEqualTo clientOwner} && {_lastEpoch isEqualTo _epoch}
        && {_lastTime isEqualType 0} && {finite _lastTime}
        && {_now >= _lastTime} && {_now - _lastTime <= 5};
};
_patient setVariable ["ACME_alt_ptxSample", [_pRatio, clientOwner, _epoch, _now], false];
private _expanding = false;
if (_sampleValid) then {
    // Boyle ratio composes across the climb and reverses on descent; fixed
    // altitude gives exactly 1 regardless of elapsed time or number of ticks.
    private _factor = ((_sample select 0) / _pRatio) max 0.2 min 5;
    if (_factor != 1) then {
        [_patient, _factor] call ACME_fnc_ptxAmbientChange;
        _expanding = _factor > 1
            && {(_patient getVariable ["ACM_breathing_Pneumothorax_State", 0]) > 0};
    };
};
[_patient, "ACME_alt_expanding", _expanding] call ACME_fnc_setVarNet;

private _dt = [_patient, "altitude", 0.25, 5] call ACME_fnc_clinicalTickDelta;  // independent flight worker cadence

// flight stress: g-loading on a hypovolemic casualty.
// it runs at every altitude, before the altitude cutoff below, because the hardest g in casevac is
// nap-of-the-earth flying, down low, where the aircraft is banking hard and pulling out of terrain. that has
// nothing to do with how high you are.
// a climb or a hard banked turn loads the casualty toward their feet. a patient with normal volume compensates
// without you ever noticing. a hypovolemic one has nothing left to compensate with: venous return falls and the
// pressure goes with it, transiently, every time the aircraft maneuvers, recovering when it settles. this is why
// you fill a casualty before the flight rather than during it, and why the pressure you were happy with on the
// ground is not the pressure you will have in the turn.
// it reaches the cuff through peripheral resistance, the same additive lever every other bp effect uses, so it
// composes with pressors, the TBI and ACM's hardcore offsets rather than fighting them.
private _gDrop = 0;
if (missionNamespace getVariable ["ACME_flightG_enable", true]) then {
    private _veh = _exposure select 4;
    if (!isNull _veh && {isEngineOn _veh}) then {
        // the maneuver magnitude: the climb rate and the bank angle, whichever is loading them harder.
        private _climb = ((velocity _veh) select 2) max 0;
        private _climbFrac = linearConversion [1, (missionNamespace getVariable ["ACME_flightG_climbRateFull", 8]), _climb, 0, 1, true];
        private _upZ = (vectorUp _veh) select 2;  // 1.0 is wings level, and cos(bank) in a turn.
        private _bankFrac = linearConversion [0.98, (missionNamespace getVariable ["ACME_flightG_bankFull", 0.72]), _upZ, 0, 1, true];
        private _gStress = _climbFrac max _bankFrac;

        // the volume status: how little they have left to compensate with.
        private _bvNorm = missionNamespace getVariable ["ACME_hypo_bloodNormal", 6];
        private _deficit = (_bvNorm - (_patient getVariable ["ACM_circulation_Blood_Volume", _bvNorm])) max 0;
        private _hypoFrac = linearConversion [
            (missionNamespace getVariable ["ACME_flightG_hypoStartL", 0.5]),
            (missionNamespace getVariable ["ACME_flightG_hypoFullL", 2.0]),
            _deficit, 0, 1, true
        ];

        _gDrop = -((missionNamespace getVariable ["ACME_flightG_maxResistDrop", 28]) * _gStress * _hypoFrac);
        [_patient, "ACME_flightG_stress", _gStress, 0.02, 1] call ACME_fnc_setVarNetApprox;
    } else {
        [_patient, "ACME_flightG_stress", 0] call ACME_fnc_setVarNet;
    };
} else {
    [_patient, "ACME_flightG_stress", 0] call ACME_fnc_setVarNet;
};
// ease it, so the pressure sags into the turn and recovers out of it rather than stepping.
private _curG = _patient getVariable ["ACME_flightG_resistAdd", 0];
private _gStep = (missionNamespace getVariable ["ACME_flightG_stepPerSec", 18]) * _dt;
[_patient, "ACME_flightG_resistAdd", (_curG + (((_gDrop - _curG) max (-_gStep)) min _gStep)), 0.10, 1] call ACME_fnc_setVarNetApprox;

// Oxygen is a ceiling on the native clinical writer, never a replacement for
// its target. Descent and live disabling therefore remove only this exposure;
// they cannot erase a medication, ventilation or scenario target.
private _targetSat = [_patient, _exposure] call ACME_fnc_altitudeOxygenCeiling;
[_patient, "ACME_alt_hypoxia", (99 - _targetSat), 0.20, 2] call ACME_fnc_setVarNetApprox;
