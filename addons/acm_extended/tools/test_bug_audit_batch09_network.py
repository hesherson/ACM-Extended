from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / "functions"

def source(name: str) -> str:
    return (F / f"fn_{name}.sqf").read_text(encoding="utf-8-sig")

def should_publish(last, last_at, value, now, epsilon, max_age):
    if last is None:
        return True
    moved = abs(value - last) >= epsilon if epsilon > 0 else value != last
    aged = max_age > 0 and (last_at < 0 or now - last_at >= max_age)
    return moved or aged

def test_approx_helper_keeps_exact_local_value_and_forces_owner_refresh():
    s = source("setVarNetApprox")
    assert '_obj setVariable [_name, _value, false];' in s
    assert 'ACME_net_approxOwner' in s
    assert 'createHashMap' in s
    assert '_obj setVariable [_name, _value, true];' in s
    assert 'diag_tickTime' in s

def test_approx_reference_threshold_and_heartbeat_contract():
    assert should_publish(None, -1, 1.0, 0, 0.1, 5)
    assert not should_publish(1.0, 0, 1.04, 1, 0.1, 5)
    assert should_publish(1.0, 0, 1.11, 1, 0.1, 5)
    assert should_publish(1.0, 0, 1.04, 5, 0.1, 5)

def test_five_hz_coagulation_uses_approx_publication():
    s = source("coagulationTick")
    for key in (
        'ACME_coag_clotStrength',
        'ACME_coag_dilutionSeverity',
        'ACME_coag_extraMult',
        'ACME_ca_coagMult',
    ):
        assert f'"{key}"' in s
    assert s.count('call ACME_fnc_setVarNetApprox') >= 4

def test_shock_tick_dedupes_scalar_and_hashmap_publication():
    s = source("shockPhenotypeTick")
    assert 'ACME_fnc_setVarNetApprox' in s
    assert 'abs (_oldSeverity - _sev) >= 0.005' in s
    assert 'ACME_fnc_setVarNet;' in s
    assert '_u setVariable ["ACME_circ_State",_circ,false];' in s

def test_aspiration_and_preoxygenation_preserve_owner_exact_values():
    asp = source("aspirationTick")
    pre = source("preoxygenationTick")
    # Atomic authority replaces the duplicate early load write; mirrors still retain exact owner values.
    assert '[_u,"ACME_aspiration_State",_state] call ACME_fnc_setVarNet;' in asp
    for field in ("load", "edema", "injury", "SpO2Penalty", "RRDrive", "shunt"):
        rows = [row for row in asp.splitlines() if f'"ACME_aspiration_{field}"' in row and 'call ACME_fnc_setVarNetApprox' in row]
        assert len(rows) == 1 and ',0] call ACME_fnc_setVarNetApprox' in rows[0]
    assert '_u setVariable ["ACME_aspiration_lastAt",_now,false];' in asp
    assert 'ACM_core_TargetVitals_RespirationRate' not in asp
    assert 'call ACM_core_fnc_setTargetVitalsState' not in asp
    endpoint = (ROOT.parent / "breathing/functions/fnc_updateRespirationRate.sqf").read_text(encoding="utf-8-sig")
    assert '[_unit] call ACME_fnc_aspirationState' in endpoint
    assert '14 * _injury' in endpoint
    assert 'call ACME_fnc_setVarNetApprox' in pre
    assert 'call ACME_fnc_setVarNet;' in pre

def test_circulation_hot_scalars_are_threshold_published():
    s = source("circHandle")
    for key in (
        'ACME_ca_mapDropEased',
        'ACME_ca_serumLevel',
        'ACME_amio_serumLevel',
        'ACME_lido_serumLevel',
        'ACME_esmolol_serumLevel',
        'ACME_pressorResistAdd',
        'ACME_circ_resistDelta',
        'ACME_hrTarget_circ',
        'ACME_vent_etco2Adj',
    ):
        line = next(x for x in s.splitlines() if f'"{key}"' in x and 'setVarNetApprox' in x)
        assert 'setVarNetApprox' in line
    assert '_patient setVariable ["ACME_vent_etco2AdjAt",CBA_missionTime,false];' in s

def test_megacode_does_not_rebroadcast_unchanged_aar_extrema_or_scheduler_clock():
    aar = source("megacodeAARTick")
    watch = source("megacodeWatch")
    assert 'if (_worst < (_u getVariable ["ACME_MC_aarWorstSpO2",100]))' in aar
    assert 'if (_lowSBP < (_u getVariable ["ACME_MC_aarLowestSBP",999]))' in aar
    assert '_d setVariable ["ACME_MC_arrestLast", _now, false];' in watch
    assert '_d setVariable ["ACME_MC_arrestElapsed", _elapsed, false];' in watch

def test_helper_registered_once():
    cfg = (ROOT / "config.cpp").read_text(encoding="utf-8-sig")
    assert cfg.count('class setVarNetApprox {};') == 1
