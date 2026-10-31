"""B237: executable legacy source contract; failures must not block collection."""

def test_source_contract():
    """Phase 132: wrapped HPMK presentation has no attachTo/physics relationship with the casualty."""
    from pathlib import Path
    R=Path(__file__).resolve().parents[1]
    vis=(R/'addons/acm_extended/functions/fn_registerHpmkVisualRuntime.sqf').read_text()
    server=(R/'addons/acm_extended/functions/fn_hpmkBlanketTick.sqf').read_text()
    # No wrapped-patient object or follower PFH is created. Dropped blankets remain supported.
    import re
    code=re.sub(r'/\*.*?\*/|//[^\n]*','',vis,flags=re.S)
    assert 'ACME_hpmk_wrappedVisuals = createHashMap;' in code
    for forbidden in ('getPosWorldVisual _patient','vectorDirVisual _patient',
                      '_vis attachTo','ACME_hpmk_wrappedVisuals set','0.05, []] call CBA_fnc_addPerFrameHandler'):
        assert forbidden not in code,forbidden
    assert 'call ACME_fnc_hpmkBlanketTick' in code
    assert 'attachTo [_p' not in server
    spawn=(R/'addons/acm_extended/functions/fn_hpmkSpawnBlanket.sqf').read_text()
    assert 'createVehicle ["Land_HelipadEmpty_F"' in spawn
    assert 'ACME_hpmk_isBlanket' in spawn
    print('PASS phase132: HPMK wrapped visuals remain disabled; dropped blankets are retained and cannot form a magic-carpet attach chain')


if __name__ == "__main__":
    test_source_contract()
