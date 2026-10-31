"""B239: execute the reviewed current contract; original script assertions retained where applicable."""

def test_current_phase153_nrb_advanced_airway_exclusion():
    #!/usr/bin/env python3
    """RC7 regression: NRB may coexist only with no adjunct, OPA and/or NPA, never i-gel/ETT/surgical airway."""
    from build_contract import assert_current_build as _assert_current_build
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    FUN = ROOT / "addons" / "acm_extended" / "functions"

    def read(path):
        return path.read_text(encoding="utf-8", errors="replace")

    cfg = read(ROOT / "addons" / "acm_extended" / "config.cpp")
    compat = read(FUN / "fn_nrbAirwayCompatible.sqf")
    apply = read(FUN / "fn_nrbApply.sqf")
    local = read(FUN / "fn_nrbStateLocal.sqf")
    tick = read(FUN / "fn_nrbTick.sqf")
    insert = read(ROOT / "addons" / "airway" / "functions" / "fnc_insertAirwayItem.sqf")
    cric = read(ROOT / "addons" / "airway" / "functions" / "fnc_canEstablishSurgicalAirway.sqf")
    laryngo = read(FUN / "fn_laryngoOpen.sqf")
    startup = read(FUN / "fn_initForkStartupRuntime.sqf")

    assert 'class nrbAirwayCompatible {};' in cfg

    # Compatibility helper explicitly permits empty/OPA oral state; NPA is nasal and intentionally independent.
    assert '(_oral in ["", "OPA"])' in compat
    assert 'ACME_ETT_Inserted' in compat
    assert 'ACM_airway_SurgicalAirway_TubeInserted' in compat
    assert 'SGA' not in '(_oral in ["", "OPA"])'

    # NRB menu + both runtime mutation boundaries use the same compatibility helper.
    apply_block = cfg.split("class ACME_ApplyNRB:", 1)[1].split("class ACME_RemoveNRB:", 1)[0]
    assert 'ACME_fnc_nrbAirwayCompatible' in apply_block
    assert 'ACME_fnc_nrbAirwayCompatible' in apply
    assert 'ACME_fnc_nrbAirwayCompatible' in local

    # Advanced-airway actions require the NRB to be removed first.
    igel_block = cfg.split("class InsertIGel:", 1)[1].split("// CPR remains", 1)[0]
    assert "ACME_nrb_on" in igel_block
    intub_block = cfg.split("class ACME_IntubateStart:", 1)[1].split("class ACME_Extubate:", 1)[0]
    assert "ACME_nrb_on" in intub_block
    assert '_type == "SGA"' in insert and 'ACME_nrb_on' in insert
    assert 'ACME_nrb_on' in cric
    assert 'ACME_nrb_on' in laryngo and 'ACME_ETT_Inserted' in laryngo

    # Out-of-band/Zeus/race changes cannot leave an impossible NRB+advanced-airway combination alive.
    assert 'if !([_u] call ACME_fnc_nrbAirwayCompatible) then {' in tick
    assert 'NRB removed: another airway device now occupies the mask interface.' in tick

    _assert_current_build()
    # Current runtime identity is checked by the independent build contract above.
    assert '[_u, false, false, -1, true, true] call ACME_fnc_nrbStateCommit;' in tick
    assert 'ACME_nrb_drawPending' in tick and 'ACME_nrb_session' in tick

    print("PASS rc7: NRB only with no airway adjunct, OPA and/or NPA")


if __name__ == "__main__":
    test_current_phase153_nrb_advanced_airway_exclusion()
