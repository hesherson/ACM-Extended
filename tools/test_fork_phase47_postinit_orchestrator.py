"""B237: executable legacy source contract; failures must not block collection."""

def test_source_contract():
    from pathlib import Path
    import re
    ROOT=Path(__file__).resolve().parents[1]
    POST=(ROOT/"addons/acm_extended/functions/fn_postInit.sqf").read_text()
    CFG=(ROOT/"addons/acm_extended/config.cpp").read_text()
    POST=re.sub(r'/\*.*?\*/|//[^\n]*','',POST,flags=re.S)
    NET=(ROOT/"addons/acm_extended/functions/fn_initNetworkSyncConfig.sqf").read_text()
    assert 'class initNetworkSyncConfig {};' in CFG
    assert 'ACME_net_epsilon = 0.005;' in NET
    assert 'call ACME_fnc_initNetworkSyncConfig;' in POST
    for forbidden in ['setVariable','CBA_fnc_addEventHandler','CBA_fnc_addPerFrameHandler','addMissionEventHandler','ACME_net_epsilon =']:
        assert forbidden not in POST,forbidden
    # Every executable postInit line is now an explicit subsystem/function call; history belongs in comments/docs.
    for no,line in enumerate(POST.splitlines(),1):
        code=line.strip()
        if not code or code.startswith('//'): continue
        assert re.fullmatch(r'call ACME_fnc_[A-Za-z0-9_]+;',code),(no,code)
    # Comment length is not runtime complexity. Every executable call must resolve to a registered helper.
    for name in re.findall(r'call ACME_fnc_([A-Za-z0-9_]+);',POST):
        assert f'class {name} {{}};' in CFG,name
        assert (ROOT/'addons/acm_extended/functions'/f'fn_{name}.sqf').is_file(),name
    print("fork phase 47 orchestration-only postInit checks: PASS")


if __name__ == "__main__":
    test_source_contract()
