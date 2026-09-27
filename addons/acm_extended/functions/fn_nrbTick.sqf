// sustain the NRB high-flow o2 flow, draw oxygen from the carried tank of the applying medic, and yank the mask off,
// AED-style, if that medic moves out of range or into a different vehicle.
// the passive oxygen rule:
// the tank can flow continuously, and the SpO2 support is breath-gated.
// if the patient is apneic, or not moving air, the NRB gives no oxygen benefit.
// if the patient is breathing, the mask raises SpO2 slowly toward the floor, scaled by the rr and the airway and
// breathing effectiveness, which is closer to ACM BVM oxygen behavior.
if (isNil "ACME_nrb_activePatients") exitWith {};
if !(missionNamespace getVariable ["ACME_sys_nrb", true]) exitWith {
    {
        if (!isNull _x && {local _x}) then {
            _x setVariable ["ACME_nrb_lastTickLocal", CBA_missionTime, false];
            [_x, -1, -1, false, true, true] call ACME_fnc_nrbStateCommit;
            if (_x getVariable ["ACME_nrb_sfxWanted", true]) then {
                _x setVariable ["ACME_nrb_sfxWanted", false, false];
                ["ACME_nrbSound", [_x, false]] call CBA_fnc_serverEvent;
            };
        };
    } forEach ACME_nrb_activePatients;
};

// Per-patient elapsed time is measured below; the PFH cadence remains 0.5 seconds.
private _floor = missionNamespace getVariable ["ACME_nrb_spo2Floor", 95];
private _ratePerSec = missionNamespace getVariable ["ACME_nrb_spo2RatePerSec", 0.35];
private _maxDist = missionNamespace getVariable ["ACME_nrb_maxDistance", 6];
private _flowLPM = missionNamespace getVariable ["ACME_nrb_flowLPM", 15];  // l/min drawn from the tank while flowing.
private _minRR = missionNamespace getVariable ["ACME_nrb_minRR", 1];
private _fullRR = missionNamespace getVariable ["ACME_nrb_fullEffectRR", 12];
private _minAirway = missionNamespace getVariable ["ACME_nrb_minAirway", 0.05];
private _minBreathing = missionNamespace getVariable ["ACME_nrb_minBreathing", 0.05];
// ACM_OxygenTank_425 is a 425 l cylinder modeled as 283 reserve units, at count=283, so each
// useoxygentankreserve unit is about 1.5 l. spend a unit each time that many liters have flowed, so at the
// default 15 l/min that is 1 unit every 6 s, or 10 units a minute, exactly matching ACM's own BVM
// consumption.
private _litersPerUnit = (missionNamespace getVariable ["ACME_nrb_tankCapacityL", 425]) / (missionNamespace getVariable ["ACME_nrb_tankUnits", 283]);

private _fnc_stopSfx = {
    params ["_u"];
    ["ACME_nrbSound", [_u, false]] call CBA_fnc_serverEvent;
    _u setVariable ["ACME_nrb_sfxWanted", false, false];
    [_u, -1, -1, false, true, true] call ACME_fnc_nrbStateCommit;
};

{
    private _u = _x;
    if (isNull _u || {!local _u}) then { continue; };
    // Death freezes oxygen delivery, but it must not make the physical mask disappear.  The corpse keeps the same
    // ACME_nrb_on/hasO2 evidence until a medic explicitly removes it; only sound and active delivery are stopped.
    // This also prevents the presence/absence of the Remove NRB action from becoming a death-state oracle.
    if (!alive _u) then {
        [_u] call _fnc_stopSfx;
        continue;
    };
    if !(_u getVariable ["ACME_nrb_on", false]) then {
        [_u] call _fnc_stopSfx;
        continue;
    };

    // Advanced-airway invariant. If an i-gel, ETT or surgical airway appears through another provider, Zeus,
    // restore, or any race after NRB placement, the mask is no longer a valid oxygen interface. Retire it here on
    // the patient owner so an impossible NRB+advanced-airway state cannot persist even outside menu-driven paths.
    if !([_u] call ACME_fnc_nrbAirwayCompatible) then {
        private _maskMedic = _u getVariable ["ACME_nrb_medic", objNull];
        [_u] call _fnc_stopSfx;
        [_u, false, false, -1, true, true] call ACME_fnc_nrbStateCommit;
        _u setVariable ["ACME_nrb_session", "", true];
        _u setVariable ["ACME_nrb_drawPending", [], true];
        _u setVariable ["ACME_nrb_o2Pending", 0, true];
        ["NRB removed: advanced airway now requires BVM or ventilator support.", 2.5, _maskMedic] call ACME_fnc_netNotice;
        continue;
    };

    private _now = CBA_missionTime;
    private _dt = ((_now - (_u getVariable ["ACME_nrb_lastTickLocal", _now - 0.5])) max 0) min 2;
    _u setVariable ["ACME_nrb_lastTickLocal", _now, false];

    private _medic = _u getVariable ["ACME_nrb_medic", objNull];

    // the range tether, an AED-style yank.
    private _yank = isNull _medic
        || {!alive _medic}
        || {(objectParent _medic) isNotEqualTo (objectParent _u)}
        || {(_medic distance _u) > _maxDist};
    if (_yank) then {
        [_u] call _fnc_stopSfx;
        [_u, false, false, -1, true, true] call ACME_fnc_nrbStateCommit;
        ["NRB pulled off. Out of range.", 2.5, _medic] call ACME_fnc_netNotice;
        continue;
    };

    if !(_u getVariable ["ACME_nrb_hasO2", false]) then {[_u, -1, -1, false, true, true] call ACME_fnc_nrbStateCommit;};
    // the oxygen draw from the tank of the medic, metered at _flowLPM.
    if (_u getVariable ["ACME_nrb_hasO2", false]) then {
        // ACM_OxygenTank_425 is 425 l over 283 reserve units, so spend a unit each _litersPerUnit, about 1.5 l, that
        // flows. the fractional liters accumulate each 0.5 s tick.
        private _request = _u getVariable ["ACME_nrb_drawPending", []];
        // A lost acknowledgement cannot grant unlimited unaccounted oxygen. Keep retrying
        // the same transaction; after 2 s pause flow/uptake until the owner confirms it.
        private _awaitingTooLong = count _request >= 3 && {_now - (_request select 2) > 2};
        private _pending = (_u getVariable ["ACME_nrb_o2Pending", 0]) + (if (_awaitingTooLong) then {0} else {_flowLPM / 60 * _dt});
        [_u, "ACME_nrb_o2Pending", _pending] call ACME_fnc_setVarNet;
        if (count _request == 0 && {_pending >= _litersPerUnit}) then {
            private _sequence = (_u getVariable ["ACME_nrb_drawSeq", 0]) + 1;
            _u setVariable ["ACME_nrb_drawSeq", _sequence, true];
            _request = [_u getVariable ["ACME_nrb_session", ""], _sequence, _now];
            _u setVariable ["ACME_nrb_drawPending", _request, true];
            _u setVariable ["ACME_nrb_lastDrawSend", -1, false];
        };
        if (count _request >= 3 && {_now - (_u getVariable ["ACME_nrb_lastDrawSend", -1]) >= 1}) then {
            _u setVariable ["ACME_nrb_lastDrawSend", _now, false];
            private _source = _u getVariable ["ACME_nrb_oxygenSource", _medic];
            if (!isNull _source) then {
                ["ACME_nrbDraw", [_u, _medic, _request select 0, _request select 1, 0, _source], _source] call CBA_fnc_targetEvent;
            } else {
                [_u, _request select 0, _request select 1, false] call ACME_fnc_nrbOxygenAck;
            };
        };
        private _flowing = !_awaitingTooLong && {_u getVariable ["ACME_nrb_hasO2", false]};
        if (isNil {_u getVariable "ACME_nrb_sfxWanted"} || {(_u getVariable ["ACME_nrb_sfxWanted", false]) != _flowing}) then {
            _u setVariable ["ACME_nrb_sfxWanted", _flowing, false];
            ["ACME_nrbSound", [_u, _flowing]] call CBA_fnc_serverEvent;
        };
        [_u, -1, -1, _flowing, true, true] call ACME_fnc_nrbStateCommit;
        if (!_flowing) then { continue; };

        // passive mask support: no spontaneous ventilation means no oxygen uptake.
        private _rr = _u getVariable ["ACME_resp_neuralRR", (_u getVariable ["ACM_breathing_RespirationRate", 0])];
        private _airway = if (!isNil "ACM_airway_fnc_getAirwayState") then {[_u] call ACM_airway_fnc_getAirwayState} else {_u getVariable ["ACM_airway_AirwayState", 1]};
        private _breathing = if (!isNil "ACM_breathing_fnc_getBreathingState") then {[_u] call ACM_breathing_fnc_getBreathingState} else {_u getVariable ["ACM_breathing_BreathingState", 1]};
        private _hasPulse = [_u] call ACM_circulation_fnc_hasPulse;
        private _movingAir = _hasPulse && {_rr > _minRR} && {_airway > _minAirway} && {_breathing > _minBreathing};

        if (_movingAir) then {
            private _rrFrac = linearConversion [_minRR, _fullRR, _rr, 0.15, 1, true];
            private _ventFrac = ((_airway min _breathing) max 0 min 1) * _rrFrac;
            private _spo2 = _u getVariable ["ace_medical_spo2", 97];

            if (_spo2 < _floor) then {
                // BVM-style easing: a bigger gap rises faster, capped by a slow passive maximum gain.
                private _gapGain = ((_floor - _spo2) / 5) max 0;
                private _maxGain = _ratePerSec * _ventFrac;
                private _gain = (_gapGain min _maxGain) * _dt;
                if (_gain > 0) then {
                    [_u, [["spo2", ((_spo2 + _gain) min _floor), true, true]]] call ACM_core_fnc_setAceMedicalState;
                    [_u, "ACME_nrb_lastO2Uptake", CBA_missionTime] call ACME_fnc_setVarNet;
                };
            };

            // mark a recent oxygenated spontaneous breath, for systems and debug that need breath-gated o2 timing.
            private _nextBreath = _u getVariable ["ACME_nrb_nextBreathMark", 0];
            if (CBA_missionTime >= _nextBreath) then {
                _u setVariable ["ACME_nrb_nextBreathMark", CBA_missionTime + (60 / (_rr max 1)), false];
                [_u, "ACME_nrb_lastSpontaneousO2Breath", CBA_missionTime] call ACME_fnc_setVarNet;
            };
        };
    };
} forEach (+ACME_nrb_activePatients);
ACME_nrb_activePatients = ACME_nrb_activePatients select {!isNull _x && {local _x} && {alive _x} && {_x getVariable ["ACME_nrb_on", false]}};
