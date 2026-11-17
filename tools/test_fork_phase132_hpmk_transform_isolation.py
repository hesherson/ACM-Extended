"""B237: executable legacy source contract; failures must not block collection."""

def test_source_contract():
    """Phase 132: wrapped HPMK presentation has no attachTo/physics relationship with the casualty."""
    from pathlib import Path
    R=Path(__file__).resolve().parents[1]
    vis=(R/'addons/acm_extended/functions/fn_registerHpmkVisualRuntime.sqf').read_text()
    server=(R/'addons/acm_extended/functions/fn_hpmkBlanketTick.sqf').read_text()
    # The shell is a local display only. Dropped blankets remain supported.
    import re
    code=re.sub(r'/\*.*?\*/|//[^\n]*','',vis,flags=re.S)
    assert 'ACME_hpmk_wrappedVisuals = createHashMap;' in code
    for forbidden in ('attachTo', '_patient setPos', '_patient setVector', 'createVehicle'):
        assert forbidden not in code,forbidden
    assert 'createSimpleObject [_path, getPosWorldVisual _patient, true]' in code
    assert '_visual setPhysicsCollisionFlag false' in code
    assert 'call ACME_fnc_hpmkBlanketTick' in code
    assert 'attachTo [_p' not in server
    spawn=(R/'addons/acm_extended/functions/fn_hpmkSpawnBlanket.sqf').read_text()
    assert 'createVehicle ["Land_HelipadEmpty_F"' in spawn
    assert 'ACME_hpmk_isBlanket' in spawn


if __name__ == "__main__":
    test_source_contract()
