"""B239: execute the reviewed current contract; original script assertions retained where applicable."""

def test_current_phase126_vent_roc_assessment():
    #!/usr/bin/env python3
    """Phase 126: Check Breathing reports delivered ventilation and CBA rocuronium threshold matches runtime."""
    from pathlib import Path
    import re
    ROOT=Path(__file__).resolve().parents[1]
    check=(ROOT/'addons/breathing/functions/fnc_checkBreathingLocal.sqf').read_text()
    settings=(ROOT/'addons/acm_extended/XEH_settings.hpp').read_text()
    roc=(ROOT/'addons/acm_extended/functions/fn_rocuroniumTick.sqf').read_text()
    dbg=(ROOT/'addons/acm_extended/functions/fn_debugMenu.sqf').read_text()
    idx_vent=check.index('ACME_vent_driving')
    idx_cs=check.index('// Cheyne-Stokes')
    assert idx_vent < idx_cs
    for token in ['ACME_vent_effectiveRR','ACME_vent_vte','ACME_vent_mvDelivered','mechanically ventilated']:
        assert token in check
    m=re.search(r'"ACME_roc_blockThreshold".*?\[(0\.1),\s*(3),\s*(0\.5),\s*(1)\]',settings,re.S)
    assert m, 'CBA rocuronium threshold must allow/default to 0.5'
    assert 'getVariable ["ACME_roc_blockThreshold", 0.5]' in roc
    assert 'call ACME_fnc_debugMenuClinical;' in dbg
    clinical=(ROOT/'addons/acm_extended/functions/fn_debugMenuClinical.sqf').read_text()
    assert 'private _par = _patient getVariable ["ACME_roc_paralyzed", false];' in clinical
    assert 'ACME_roc_blockThreshold' not in clinical, 'debug must consume actual paralysis instead of recomputing it'
    rr=(ROOT/'addons/breathing/functions/fnc_updateRespirationRate.sqf').read_text()
    assert 'ACME_roc_paralyzed' in rr and 'if (_central == 0 || {_arrest} || {_paralyzed}' in rr
    print('PASS phase126: ventilator assessment uses delivered breaths and rocuronium threshold is internally consistent')


if __name__ == "__main__":
    test_current_phase126_vent_roc_assessment()
