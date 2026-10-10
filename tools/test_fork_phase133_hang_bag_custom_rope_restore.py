"""B237: executable legacy source contract; failures must not block collection."""

def test_source_contract():
    """Phase 133: retain the user-validated custom IV rope while preserving Phase 132 stability fixes."""
    from pathlib import Path
    R=Path(__file__).resolve().parents[1]
    F=R/'addons/acm_extended/functions'
    request=(F/'fn_hangBagStart.sqf').read_text()
    start=(F/'fn_hangBagActivate.sqf').read_text()
    assert 'call ACME_fnc_ownerDispatch' in request
    assert 'createSimpleObject' not in request
    init=(F/'fn_initHangBagRuntime.sqf').read_text()
    tick=(F/'fn_hangBagTick.sqf').read_text()
    config=(R/'addons/acm_extended/config.cpp').read_text()
    assert 'ACME_hang_ropeClass = "ACME_IVLine_Rope";' in init
    for cls in ['ACME_IVLine_Rope','ACME_IVLine_Rope_Blood','ACME_IVLine_Rope_Plasma']:
        assert cls in start
        assert f'class {cls}' in config
    assert 'private _ropeClass = "";' not in start
    assert '_ropeClass\n    ] call ACME_fnc_ivLineCreate' in start
    assert 'createSimpleObject [_bagModel' in start
    assert 'createVehicleLocal [0, 0, 0]' in start
    for bad in ['_medic setPosASL','_medic setDir _lockDir','_medic setVelocity [0,0,0]','_medic setVelocityModelSpace']:
        assert bad not in tick
    assert 'call ACME_fnc_doAnim;' not in tick
    print('PASS phase133: custom per-fluid Hang Bag IV rope restored without restoring provider transform/animation fighting')


if __name__ == "__main__":
    test_source_contract()
