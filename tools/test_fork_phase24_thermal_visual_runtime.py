"""B237: executable legacy source contract; failures must not block collection."""

def test_source_contract():
    from pathlib import Path
    ROOT=Path(__file__).resolve().parents[1]
    POST=(ROOT/'addons/acm_extended/functions/fn_postInit.sqf').read_text()
    CFG=(ROOT/'addons/acm_extended/config.cpp').read_text()
    helpers={
     'initHangBagRuntime':('fn_initHangBagRuntime.sqf','ACME_treatmentPoseSync'),
     'initHpmkCoreRuntime':('fn_initHpmkCoreRuntime.sqf','ACME_fnc_hpmkTick'),
     'initProcedureEnvironmentConfig':('fn_initProcedureEnvironmentConfig.sqf','ACME_darkness_bleachByColor'),
     'registerHpmkVisualRuntime':('fn_registerHpmkVisualRuntime.sqf','ACME_hpmk_wrappedVisuals'),
    }
    for fn,(file,token) in helpers.items():
        p=ROOT/'addons/acm_extended/functions'/file
        assert p.exists(),p
        s=p.read_text()
        assert token in s,(fn,token)
        assert f'class {fn} {{}};' in CFG,fn
        assert f'call ACME_fnc_{fn};' in POST,fn
    for token in ['["ACME_treatmentPoseSync"','[{call ACME_fnc_hpmkTick}','ACME_acre_babblePulseMildMin','ACME_darkness_bleachByColor','ACME_hpmk_wrappedVisuals']:
        assert token not in POST,token
    positions=[POST.index(f'call ACME_fnc_{fn};') for fn in helpers]
    assert positions == sorted(positions),positions
    assert len(POST.splitlines()) < 2050,len(POST.splitlines())
    print('fork phase 24 thermal/visual runtime ownership checks: PASS')

    # Babel manipulation was deliberately retired; thermal initialization must not re-enable it.
    for retired in ('acreBabbleInit','acreBabbleSet','acreBabbleTick','initAcreBabbleRuntime'):
        assert not (ROOT/'addons/acm_extended/functions'/f'fn_{retired}.sqf').exists()
        assert f'class {retired} {{}};' not in CFG
        assert f'call ACME_fnc_{retired};' not in POST


if __name__ == "__main__":
    test_source_contract()
