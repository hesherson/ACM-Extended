"""B246 owner-discovery consolidation and infusion-retirement contracts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def src(name):
    return (ROOT / "functions" / f"fn_{name}.sqf").read_text(encoding="utf-8-sig")


def test_idle_chest_seal_server_has_no_all_players_scan():
    s = src("chestSealNetInit")
    guard = 'if (count ACME_CS_sessions == 0 && {count ACME_CS_editResults == 0}) exitWith {};'
    assert guard in s
    assert s.index(guard) < s.index('private _players = allPlayers;')


def test_one_owner_scan_feeds_all_idle_and_maintenance_registries():
    discovery = src("idlePhysDiscovery")
    runtime = src("expansionRegisterRuntime")
    assert discovery.count('ACME_clinical_ownedUnits') == 1
    for assignment in (
        'ACME_preox_activePatients = _preox;',
        'ACME_aspiration_activePatients = _aspiration;',
        'ACME_shock_activePatients = _shock;',
        'ACME_rhythmThreshold_activePatients = _rhythmThreshold;',
        'ACME_circ_activePatients = _circPatients;',
        'ACME_coag_activePatients = _coag;',
        'ACME_infusion_activePatients = _infusion;',
    ):
        assert assignment in discovery
    assert '[{ call ACME_fnc_idlePhysDiscovery; }, 1, []] call CBA_fnc_addPerFrameHandler;' in runtime


def test_hot_circulation_coagulation_and_infusion_workers_never_scan_owner_registry():
    for name in ("circHandle", "coagulationTick", "handleInfusions"):
        s = src(name)
        assert 'ACME_clinical_ownedUnits' not in s, name
    assert 'ACME_circDiscoveryNextAt' not in src("circHandle")
    assert 'ACME_coag_lastSweep' not in src("coagulationTick")
    assert 'ACME_infusionDiscoveryNextAt' not in src("handleInfusions")


def test_shared_discovery_cannot_erase_fresh_direct_enrollment_before_first_hot_tick():
    discovery = src("idlePhysDiscovery")
    for registry in ("ACME_circ_activePatients", "ACME_coag_activePatients", "ACME_infusion_activePatients"):
        row = next(line for line in discovery.splitlines() if f'missionNamespace getVariable ["{registry}", []]) select' in line)
        assert '!isNull _x' in row and 'local _x' in row and 'alive _x' in row


def test_preserved_shared_registries_cannot_accumulate_duplicate_patients():
    discovery = src("idlePhysDiscovery")
    assert 'if (_needsCirc) then {_circPatients pushBackUnique _u;};' in discovery
    assert '_coag pushBackUnique _u;' in discovery
    assert '_infusion pushBackUnique _u;' in discovery


def test_empty_medicated_infusion_publishes_final_clear_then_retires():
    worker = src("handleInfusions")
    commit = src("infusionMedicationStateCommit")
    assert 'private _kept = [];' in worker
    assert '[_p, _updated] call ACME_fnc_infusionMedicationStateCommit;' in worker
    assert 'if !(_updated isEqualTo []) then {_kept pushBack _p;};' in worker
    assert 'ACME_infusion_activePatients = _kept;' in worker
    # A transition from a non-empty signature to [] forces the final clear immediately.
    assert '_sig isNotEqualTo _lastSig' in commit
    assert '[_patient, "ACME_infusion_BagMedications", _entries] call ACME_fnc_setVarNet;' in commit


def test_infusion_move_reservation_is_not_mistaken_for_completion():
    worker = src("handleInfusions")
    assert 'if (_id in keys (_p getVariable ["ACME_bagMoves", createHashMap])) then {_e set [17, 0]; _updated pushBack _e;};' in worker
