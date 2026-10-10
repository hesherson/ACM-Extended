"""B245/B246 healthy-idle networking/backpressure contracts.

These checks target the report that desync can begin without an injury. They require
healthy owned units to produce no periodic ACME physiology publications and keep
full-owner discovery off the hot 4 Hz paths.
"""
from pathlib import Path
import re

from test_menu_death_lifecycle import adapt, execute
from test_historical_vial_execution import map_defaults

ROOT = Path(__file__).resolve().parents[1]


def src(name):
    return (ROOT / "functions" / f"fn_{name}.sqf").read_text(encoding="utf-8-sig")


def test_preoxygenation_healthy_room_air_is_silent_and_neutral():
    s = src("preoxygenationTick")
    guard = 'if (abs (_reserveProbe - 0.30) <= 0.001 && {!_supportProbe} && {!_physProbe}) then {continue};'
    assert guard in s
    assert s.index(guard) < s.index('call ACME_fnc_setVarNetApprox')
    assert 'ACM_breathing_RespirationRate", 16' in s
    assert 'private _supplemental = _fio2Frac > 0.22;' in s
    assert 'if (_effectiveVent && {_supplemental} && {_spo2 >= 92}) then {' in s
    assert 'if (_reserve > 0.30) then {_reserve = (_reserve - _baselineStep) max 0.30;};' in s
    assert '([0.005,0] select (abs (_reserve - 0.30) <= 0.000001)),0] call ACME_fnc_setVarNetApprox;' in s


def test_aspiration_neutral_state_has_no_heartbeat():
    s = src("aspirationTick")
    guard = 'if (!_freshEvent && {_load <= 0.0005} && {_edema <= 0.0005} && {!_hadEffect}) then {continue};'
    assert guard in s
    assert s.index(guard) < s.index('call ACME_fnc_setVarNetApprox')
    for field in (
        "ACME_aspiration_load", "ACME_aspiration_edema", "ACME_aspiration_injury",
        "ACME_aspiration_SpO2Penalty", "ACME_aspiration_RRDrive", "ACME_aspiration_shunt",
    ):
        rows = [line for line in s.splitlines() if f'"{field}"' in line and "setVarNetApprox" in line]
        assert rows, field
        assert all(",0] call ACME_fnc_setVarNetApprox" in line for line in rows), (field, rows)


def test_shock_neutral_state_has_no_heartbeat():
    s = src("shockPhenotypeTick")
    guard = 'if (!_forcedActive && {!_tension} && {_htx < 0.75} && {!_circShock} && {_blood >= 5.1} && {!_hadShock}) then {continue};'
    assert guard in s
    assert s.index(guard) < s.index('call ACME_fnc_setVarNetApprox')
    for field in ("ACME_shock_resistDelta", "ACME_shock_hrAdj", "ACME_shock_severity"):
        row = next(line for line in s.splitlines() if f'"{field}"' in line and "setVarNetApprox" in line)
        assert ",0] call ACME_fnc_setVarNetApprox" in row


def test_idle_physiology_uses_one_shared_slow_discovery():
    discovery = src("idlePhysDiscovery")
    runtime = src("expansionRegisterRuntime")
    assert discovery.count('ACME_clinical_ownedUnits') == 1
    assert 'ACME_preox_activePatients = _preox;' in discovery
    assert 'ACME_aspiration_activePatients = _aspiration;' in discovery
    assert 'ACME_shock_activePatients = _shock;' in discovery
    assert 'ACME_rhythmThreshold_activePatients = _rhythmThreshold;' in discovery
    assert 'ACME_circ_activePatients = _circPatients;' in discovery
    assert 'ACME_coag_activePatients = _coag;' in discovery
    assert 'ACME_infusion_activePatients = _infusion;' in discovery
    # Preserve the former circulation fallback's one-second worst case while
    # replacing the independent 1 s / 2 s / 2 s owner scans with this one pass.
    assert '[{ call ACME_fnc_idlePhysDiscovery; }, 1, []] call CBA_fnc_addPerFrameHandler;' in runtime

    for name, registry in {
        "preoxygenationTick": "ACME_preox_activePatients",
        "aspirationTick": "ACME_aspiration_activePatients",
        "shockPhenotypeTick": "ACME_shock_activePatients",
        "rhythmThresholdTick": "ACME_rhythmThreshold_activePatients",
    }.items():
        s = src(name)
        assert registry in s
        assert 'ACME_clinical_ownedUnits' not in s
        assert '} forEach _patients;' in s
        assert f'{registry} = _patients select' in s
        # Any network-capable mutation in the hot worker must be downstream of
        # the discovered-patient loop, never in unconditional top-level code.
        mutation = min(
            [i for token in ("ACME_fnc_setVarNet", "ACM_core_fnc_set", "ACM_circulation_fnc_set")
             if (i := s.find(token)) >= 0],
            default=-1,
        )
        if mutation >= 0:
            loop_start = s.index('{\n    private _u = _x;', s.index('private _patients ='))
            loop_end = s.index('} forEach _patients;', loop_start)
            assert loop_start < mutation < loop_end


def test_circulation_full_owner_discovery_is_centralized():
    circ = src("circHandle")
    discovery = src("idlePhysDiscovery")
    assert 'ACME_circDiscoveryNextAt' not in circ
    assert 'ACME_clinical_ownedUnits' not in circ
    assert 'private _needsCirc =' in discovery
    assert 'ACME_circ_activePatients = _circPatients;' in discovery
    assert 'ACME_circ_State' in discovery


def test_custom_rhythm_hot_tick_uses_explicit_active_registry():
    tick = src("rhythmTick")
    commit = src("rhythmActiveCommit")
    owner = src("ownerRegister")
    lifecycle = src("ownerInit")
    assert 'ACME_clinical_ownedUnits' not in tick
    assert 'ACME_rhythm_activePatients' in tick
    assert 'ACME_rhythm_activePatients = (missionNamespace getVariable ["ACME_rhythm_activePatients", []]) select' in tick
    assert 'missionNamespace getVariable ["ACME_rhythm_activePatients", []]' in commit
    assert '_active pushBackUnique _unit' in commit
    assert 'ACME_rhythm_activePatients' in owner
    assert lifecycle.count('"ACME_rhythm_activePatients"') >= 2


def test_circ_coag_and_infusion_hot_workers_do_not_scan_every_healthy_owner():
    saline = src("salineAcidosisTrack")
    fluid = src("fluidCommit")
    circ = src("circHandle")
    coag = src("coagulationTick")
    infusion = src("handleInfusions")
    discovery = src("idlePhysDiscovery")
    assert 'ACME_clinical_ownedUnits' not in saline
    assert 'ACME_circ_activePatients' in saline
    assert 'ACME_circ_activePatients pushBackUnique _patient' in fluid
    for hot in (circ, coag, infusion):
        assert 'ACME_clinical_ownedUnits' not in hot
    assert 'ACME_circDiscoveryNextAt' not in circ
    assert 'ACME_coag_lastSweep' not in coag
    assert 'ACME_infusionDiscoveryNextAt' not in infusion
    assert discovery.count('ACME_clinical_ownedUnits') == 1
    assert 'private _kept = [];' in infusion
    assert 'if !(_updated isEqualTo []) then {_kept pushBack _p;};' in infusion
    assert 'ACME_infusion_activePatients = _kept;' in infusion


def test_b201_idle_broadcaster_shapes_cannot_return():
    # This deliberately scans only the three historically problematic full-owner
    # models. Stable replicated state may be refreshed for active patients, but a
    # neutral full-owner loop may not pair a heartbeat maxAge with setVarNetApprox.
    for name in ("preoxygenationTick", "aspirationTick", "shockPhenotypeTick"):
        s = src(name)
        assert "setVarNetApprox" in s
        # All approximate rows in these three paths use change/owner publication only.
        rows = [line for line in s.splitlines() if "setVarNetApprox" in line and not line.lstrip().startswith("//")]
        assert rows
        assert all(",0] call ACME_fnc_setVarNetApprox" in line for line in rows), (name, rows)




def test_locality_transfer_retires_idle_physiology_registries():
    s = src("ownerInit")
    owner_register = src("ownerRegister")
    for registry in (
        "ACME_preox_activePatients", "ACME_aspiration_activePatients", "ACME_shock_activePatients",
        "ACME_rhythmThreshold_activePatients", "ACME_circ_activePatients", "ACME_coag_activePatients",
        "ACME_infusion_activePatients",
    ):
        assert s.count(f'"{registry}"') >= 2
    assert '[[_patient]] call ACME_fnc_idlePhysDiscovery;' in owner_register


def test_manual_carrier_recovery_does_not_dispatch_every_healthy_unit():
    s = src("registerManualPlateCarrierRuntime")
    start = s.index('if (_now >= (missionNamespace getVariable ["ACME_manualPlateCarrierRecoveryAt", -1])) then {')
    end = s.index('private _kept = [];', start)
    audit = s[start:end]
    assert 'forEach (allUnits select {' in audit
    assert 'local _x && {alive _x}' in audit
    assert 'getVariable ["ACME_manualPlateCarrierState", ""]) != ""' in audit
    assert 'forEach allUnits;' not in audit


def _healthy_vm(name):
    s = src(name)
    # Only adapt object/locality commands that occur before each function's healthy
    # early exit. Any unsupported command beyond that guard would fail the VM,
    # making accidental fall-through visible rather than silently mocked.
    s = re.sub(r'\bisNull _u\b', '(_u isEqualTo objNull)', s)
    s = re.sub(r'\blocal _u\b', 'true', s)
    s = re.sub(r'\balive _u\b', 'true', s)
    s = re.sub(r'alive \(_u getVariable \["ACM_breathing_BVM_Medic",\s*objNull\]\)', 'false', s)
    # Keep the production body otherwise intact. The generic historical adapter
    # rewrites unrelated syntax deep in these functions; for this healthy-idle
    # execution case we only need the explicit engine boundaries above.
    return map_defaults(s.replace("toLowerANSI", "toLower"))


def test_actual_healthy_idle_models_issue_zero_publication_requests():
    # Execute the actual shared discovery for two idle minutes. The source
    # contract above proves every hot physiology mutation lives behind the
    # resulting active registries. This avoids pretending SQF-VM can parse every
    # engine-heavy clinical script while still executing the scheduling boundary.
    definition = "ACME_fnc_idlePhysDiscovery={" + _healthy_vm("idlePhysDiscovery") + "};"
    execute(definition + r'''
        private _mapDefault={params ["_map","_args"]; _args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        private _exactRequests=0;
        private _approxRequests=0;
        ACME_fnc_setVarNet={_exactRequests=_exactRequests+1;};
        ACME_fnc_setVarNetApprox={_approxRequests=_approxRequests+1;};
        ACME_clinical_ownedUnits=[_patient];

        _patient setVariable ["ACM_breathing_RespirationRate",16];
        _patient setVariable ["ace_medical_spo2",97];
        _patient setVariable ["ACM_circulation_Blood_Volume",6];

        for "_i" from 0 to 119 do {
            CBA_missionTime = 10 + _i;
            [] call ACME_fnc_idlePhysDiscovery;
            [ACME_preox_activePatients isEqualTo [] && {ACME_aspiration_activePatients isEqualTo []}
                && {ACME_shock_activePatients isEqualTo []}
                && {ACME_rhythmThreshold_activePatients isEqualTo []}
                && {ACME_circ_activePatients isEqualTo []}
                && {ACME_coag_activePatients isEqualTo []}
                && {ACME_infusion_activePatients isEqualTo []},
                "healthy discovery enrolled idle physiology"] call _check;
        };

        [_exactRequests==0,"healthy idle discovery issued exact network publication"] call _check;
        [_approxRequests==0,"healthy idle discovery issued approximate network publication"] call _check;
        [isNil {_patient getVariable "ACME_preox_lastTick"},"healthy discovery created preoxygenation scheduler state"] call _check;
        [isNil {_patient getVariable "ACME_aspiration_tickAt"},"healthy discovery created aspiration scheduler state"] call _check;
    ''')
