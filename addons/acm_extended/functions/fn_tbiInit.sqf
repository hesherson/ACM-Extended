// initialize the TBI state on a patient. it is idempotent: a re-init will not wipe an existing injury unless
// _force is true. the state is one hashmap on the unit, so it networks and persists like ACM's own medical vars.
// the CPP model is CPP equals MAP minus ICP. the TBI severity worsens when CPP stays below the threshold, from a
// low MAP, a high ICP, or both. herniation is a timed cascade once ICP crosses the herniation trigger.
params ["_patient", ["_severity", 0.5], ["_force", false]];
if (isNull _patient) exitWith {createHashMap};
if (!local _patient) exitWith {
    ["ACME_ownerCommand", [_patient, "tbiInit", _this], _patient] call CBA_fnc_targetEvent;
    _patient getVariable ["ACME_tbi_State", createHashMap]
};
if (isNil "ACME_tbi_activePatients") then { ACME_tbi_activePatients = []; };
ACME_tbi_activePatients pushBackUnique _patient;

// a sentinel: a negative severity, such as the -1 for random from spawntbipatient, means pick one. without this the
// raw -1 was being stored as the severity, which made the structural ICP ceiling, icpmax times severity, negative
// and dragged ICP below zero through the autoregulation relax. always clamp to a sane 0 to 1.
if (_severity < 0) then { _severity = 0.30 + random 0.60; };  // a random moderate-to-severe TBI.
_severity = (_severity max 0) min 1;
if (_severity > 0) then {_patient setVariable ["ACME_wakeHadTBI",true,true];};

private _existing = _patient getVariable ["ACME_tbi_State", createHashMap];
if (count _existing > 0 && {!_force}) exitWith {_existing};

private _baseICP = missionNamespace getVariable ["ACME_tbi_baseICP", 10];  // todo[ref]: the normal ICP in mmhg.
private _state = createHashMapFromArray [
    ["icp", _baseICP],  // the ICP proxy, mmhg-like.
    ["severity", _severity],  // B119: current acute/reversible TBI burden, 0 to 1.
    ["structuralSeverity", _severity],  // high-water structural injury grade; history/vulnerability, not an automatic deterioration timer.
    ["autoregIntegrity", -1],  // first-tick sentinel; replaced with the structural-grade baseline.
    ["autonomicIntegrity", -1],  // first-tick sentinel; replaced with the structural-grade baseline.
    ["autonomicTone", 0],  // signed systemic TBI tone: +1 sympathetic clamp, -1 vasomotor failure.
    ["herniating", false],  // the herniation cascade is armed.
    ["herniationClock", -1],  // the seconds remaining until the next herniation stage. -1 is inactive.
    ["herniationStage", 0],  // 0 is none, 1 unilateral, 2 bilateral and 3 terminal.
    ["pupils", 0],  // 0 is PERRL, 1 anisocoria or sluggish, 2 unilateral blown and 3 bilateral fixed.
    ["side", selectRandom ["left", "right"]],  // the lesion side, meaning the side of the first blown pupil, which is ipsilateral.
    ["gcsMotor", 6],  // 6 obeys down to 1 none, as an assessment proxy.
    ["cushing", false],  // the cushing reflex, hypertension plus bradycardia, is active.
    ["pressorMAP", 0],  // the current pressor-driven MAP support in mmhg, volume-gated.
    ["sodium", missionNamespace getVariable ["ACME_tbi_baseSodium", 140]],  // the running na+ for the HTS ceiling.
    ["lowCPPTime", 0],  // the accumulated seconds below the CPP threshold.
    ["lastTick", CBA_missionTime]
];

[_patient, _state] call ACME_fnc_tbiStateCommit;
ACME_tbi_activePatients pushBackUnique _patient;
_patient setVariable ["ACME_tbi_HasTBI", true, true];
_state
