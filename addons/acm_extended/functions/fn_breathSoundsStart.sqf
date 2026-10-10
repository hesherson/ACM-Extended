// the patient respiration sound engine. it starts a per-patient pfh, idempotent and patient-local, that plays
// audible inhale and exhale groups in one of two clinically distinct patterns.
// "biot", the post-ROSC ataxic or biot's pattern: irregular clusters of 2 to 8 breaths at a mostly constant depth
// per cluster, separated by completely unpredictable apneas of 5 to 30 s. it starts 8 s after the ROSC gasp, and
// after 60 to 180 s, randomised per patient, the ROSC gasp itself is mixed in after some clusters as its own
// combined inhale and exhale. it ends when SpO2 recovers to 80 percent.
// "cheyne", the raised-ICP cheyne-stokes pattern: mostly predictable cycles of 45 to 90 s, with 8 to 20 breaths
// whose depth crescendos from 20 percent to 100 percent and back to 20 percent across the cycle, then a 10 to 20 s
// apnea, and repeat. it ends when the cheyne-stokes phase clears, when ACME_cs_active is false.
// both patterns pause while the patient is actively being bagged, meaning a BVM squeeze within ACME_bs_bvmHold
// seconds, using ACME_bvm_lastBreathServer so every observer evaluates the same squeeze age. stopping the BVM or right-click
// pausing it lets the sounds resume on their own. both stop outright in cardiac arrest.
// _this is [_patient, _mode].
// _mode is "biot" for the clustered, irregular post-ROSC pattern, or "steady" for a regular one.
// steady exists for the slow iatrogenic leak in fn_ncdairleaktick. that casualty is not gasping in clusters, they
// are breathing regularly and badly, and the regularity is the point: a medic notices a quiet, even, wrong sound
// far sooner than they notice one more irregular noise from a casualty who is already making several.
params ["_patient", ["_mode", "biot"]];
if (isNull _patient || {!alive _patient} || {!local _patient}) exitWith {};
if ((_patient getVariable ["ACME_bs_pfh", -1]) != -1) exitWith {};

_patient setVariable ["ACME_bs_mode", _mode, false];
private _now = CBA_missionTime;
// post-ROSC biot: the first breath group starts 3 to 8 s after the gasp. cheyne-stokes, from a TBI, starts almost
// immediately once the phase is present.
_patient setVariable ["ACME_bs_mode", _mode, false];
private _startDelay = if (_mode == "biot") then { 3 + (random 5) } else { 0.5 };
_patient setVariable ["ACME_bs_stage", "apnea", false];
_patient setVariable ["ACME_bs_stageAt", _now + _startDelay, false];
_patient setVariable ["ACME_bs_phase2At", _now + 60 + (random 120), false];
// grace for the post-ROSC arrest-flag lag. see the arrest gate of the pfh.
_patient setVariable ["ACME_bs_arrestGraceUntil", _now + (missionNamespace getVariable ["ACME_bs_arrestGrace", 8]), false];
// biot: do not let the SpO2-recovery end fire until the pattern has run a while, so it always plays a solid
// post-ROSC agonal period even if the patient came out of CPR already at or above the recovery SpO2.
_patient setVariable ["ACME_bs_spo2ArmAt", _now + _startDelay + (missionNamespace getVariable ["ACME_bs_biotMinRun", 45]), false];

private _pfh = [{
    params ["_args", "_h"];
    _args params ["_u"];
    private _kill = {
        [_h] call CBA_fnc_removePerFrameHandler;
        _u setVariable ["ACME_bs_pfh", -1, false];
        _u setVariable ["ACME_bs_mode", "", false];
    };
    if (isNull _u || {!alive _u} || {!local _u}) exitWith { call _kill };
    if (_u getVariable ["ace_medical_inCardiacArrest", false]) exitWith {
        // ACM's attemptrosc fires cprsucceeded, which starts this engine, before its circulation tick clears
        // ace_medical_inCardiacArrest, so the flag is usually still true for the first tick or two post-ROSC. wait that
        // window out rather than killing, and only stop if arrest genuinely persists past the grace, which is a real
        // re-arrest. without this the biot pattern killed itself about 0.25 s after ROSC, before any breath.
        if (CBA_missionTime > (_u getVariable ["ACME_bs_arrestGraceUntil", 0])) then { call _kill };
    };
    private _mode = _u getVariable ["ACME_bs_mode", ""];
    if (_mode == "") exitWith { call _kill };
    if (_mode == "biot" && {CBA_missionTime > (_u getVariable ["ACME_bs_spo2ArmAt", 0])} && {(_u getVariable ["ace_medical_spo2", 97]) >= (missionNamespace getVariable ["ACME_bs_spo2End", 80])}) exitWith { call _kill };
    if (_mode == "cheyne" && {!(_u getVariable ["ACME_cs_active", false]) || {!(missionNamespace getVariable ["ACME_sys_cheyneStokes", true])}}) exitWith { call _kill };

    private _now = CBA_missionTime;
    // active ventilation: hold the pattern in place. it resumes by itself once the squeezes stop, whether the BVM is
    // removed, stopped, or paused with a right click.
    if (((serverTime - (_u getVariable ["ACME_bvm_lastBreathServer", -99])) max 0) < (missionNamespace getVariable ["ACME_bs_bvmHold", 6.5])) exitWith {
        _u setVariable ["ACME_bs_stageAt", ((_u getVariable ["ACME_bs_stageAt", _now]) max (_now + 0.8)), false];
    };

    if (_now < (_u getVariable ["ACME_bs_stageAt", 0])) exitWith {};

    private _fnc_play = {
        params ["_u", "_dir", "_tier"];
        private _cls = format ["ACME_Breath%1_%2_%3", _dir, _tier, (1 + floor random 6)];
        private _dist = missionNamespace getVariable ["ACME_bs_distance", 15];
        private _tg = allPlayers inAreaArray [ASLToAGL getPosASL _u, _dist, _dist, 0, false, _dist];
        if !(_tg isEqualTo []) then {
            ["ACME_breathSay3D", [_u, _cls, _dist], _tg] call CBA_fnc_targetEvent;
        };
    };

    switch (_u getVariable ["ACME_bs_stage", "apnea"]) do {
        case "apnea": {
            // plan the next group.
            if (_mode == "biot") then {
                _u setVariable ["ACME_bs_left", 2 + (floor random 7), false];  // 2 to 8 breaths.
                _u setVariable ["ACME_bs_total", -1, false];
                _u setVariable ["ACME_bs_tier", (selectRandomWeighted ["S", 0.25, "M", 0.55, "D", 0.2]), false];
                // steady holds one interval and does not jitter it. the sound has to read as a rhythm rather than
                // as noise, because that is what makes it recognizable as a finding.
                if ((_u getVariable ["ACME_bs_mode", "biot"]) == "steady") then {
                    _u setVariable ["ACME_bs_gap", (missionNamespace getVariable ["ACME_bs_steadyGap", 3.4]), false];
                } else {
                    _u setVariable ["ACME_bs_gap", 2.0 + (random 1.5), false];  // the intra-cluster spacing.
                };
            } else {
                private _total = 8 + (floor random 13);  // 8 to 20 breaths.
                private _cycle = 45 + (random 45);  // a 45 to 90 s cycle.
                private _apnea = 10 + (random 10);  // a 10 to 20 s apnea.
                _u setVariable ["ACME_bs_left", _total, false];
                _u setVariable ["ACME_bs_total", _total, false];
                _u setVariable ["ACME_bs_gap", (((_cycle - _apnea) / _total) max 2.0) min 5.0, false];
                _u setVariable ["ACME_bs_apnea", _apnea, false];
            };
            _u setVariable ["ACME_bs_stage", "in", false];
            _u setVariable ["ACME_bs_stageAt", _now, false];
        };
        case "in": {
            private _tier = "M";
            if (_mode == "biot") then {
                _tier = _u getVariable ["ACME_bs_tier", "M"];
            } else {
                // the cheyne-stokes depth curve: 20 percent, then 100 percent, then 20 percent across the cycle.
                private _total = (_u getVariable ["ACME_bs_total", 12]) max 2;
                private _idx = _total - (_u getVariable ["ACME_bs_left", _total]);
                private _rel = _idx / ((_total - 1) max 1);
                private _depth = 0.2 + (0.8 * (1 - (abs ((2 * _rel) - 1))));
                _tier = if (_depth < 0.45) then { "S" } else { if (_depth < 0.8) then { "M" } else { "D" } };
                _u setVariable ["ACME_bs_curTier", _tier, false];
            };
            [_u, "In", _tier] call _fnc_play;
            _u setVariable ["ACME_bs_stage", "out", false];
            _u setVariable ["ACME_bs_stageAt", _now + 0.7 + (random 0.5), false];  // a small in-to-out pause.
        };
        case "out": {
            private _tier = if (_mode == "biot") then { _u getVariable ["ACME_bs_tier", "M"] } else { _u getVariable ["ACME_bs_curTier", "M"] };
            [_u, "Out", _tier] call _fnc_play;
            private _left = (_u getVariable ["ACME_bs_left", 1]) - 1;
            _u setVariable ["ACME_bs_left", _left, false];
            if (_left > 0) then {
                _u setVariable ["ACME_bs_stage", "in", false];
                _u setVariable ["ACME_bs_stageAt", _now + (_u getVariable ["ACME_bs_gap", 3]), false];
            } else {
                _u setVariable ["ACME_bs_stage", "apnea", false];
                if (_mode == "biot") then {
                    _u setVariable ["ACME_bs_stageAt", _now + 5 + (random 25), false];  // 5 to 30 s, unpredictable.
                    // the later phase: mix the ROSC gasp in after some clusters, as its own combined breath.
                    if ((_now > (_u getVariable ["ACME_bs_phase2At", 1e9])) && {(random 1) < 0.4}) then {
                        [{
                            params ["_u"];
                            if (isNull _u || {!alive _u} || {!local _u} || {(_u getVariable ["ACME_bs_mode", ""]) != "biot"}) exitWith {};
                            if (((serverTime - (_u getVariable ["ACME_bvm_lastBreathServer", -99])) max 0) < (missionNamespace getVariable ["ACME_bs_bvmHold", 6.5])) exitWith {};
                            private _dist = missionNamespace getVariable ["ACME_bs_distance", 15];
                            private _tg = allPlayers inAreaArray [ASLToAGL getPosASL _u, _dist, _dist, 0, false, _dist];
                            if !(_tg isEqualTo []) then {
                                ["ACME_breathSay3D", [_u, "ACME_RoscGasp", _dist], _tg] call CBA_fnc_targetEvent;
                            };
                        }, [_u], 1.2] call CBA_fnc_waitAndExecute;
                    };
                } else {
                    _u setVariable ["ACME_bs_stageAt", _now + (_u getVariable ["ACME_bs_apnea", 14]), false];
                };
            };
        };
    };
}, 0.25, [_patient]] call CBA_fnc_addPerFrameHandler;
_patient setVariable ["ACME_bs_pfh", _pfh, false];
