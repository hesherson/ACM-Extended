"""B237: executable legacy source contract; failures must not block collection."""

def test_source_contract():
    from pathlib import Path
    import re
    ROOT=Path(__file__).resolve().parents[1]
    POST=(ROOT/"addons/acm_extended/functions/fn_postInit.sqf").read_text()
    CFG=(ROOT/"addons/acm_extended/config.cpp").read_text()
    helpers={
     "registerRoscBreathingRuntime":("fn_registerRoscBreathingRuntime.sqf","ace_medical_CPRSucceeded"),
     "registerClampDragRuntime":("fn_registerClampDragRuntime.sqf","ACME_RollerClamp_Dragging"),
     "initTbiCoreState":("fn_initTbiCoreState.sqf","ACME_tbi_activePatients"),
     "initTbiCoreConfig":("fn_initTbiCoreConfig.sqf","ACME_tbi_baseICP"),
     "registerProcedureIntegrationRuntime":("fn_registerProcedureIntegrationRuntime.sqf","ACME_infusionPulse"),
    }
    for fn,(file,token) in helpers.items():
        text=(ROOT/"addons/acm_extended/functions"/file).read_text()
        assert token in text,(fn,token)
        assert f"class {fn} {{}};" in CFG
        assert f"call ACME_fnc_{fn};" in POST
    for token in ["ace_medical_CPRSucceeded", "ACME_RollerClamp_Dragging", "ACME_tbi_activePatients =", "ACME_tbi_baseICP =", "ACME_infusionPulse", "ACME_breathSay3D"]:
        assert token not in POST,token
    # Keep the executable orchestrator bounded to registered helper calls, not a historical comment count.
    for line in re.sub(r'/\*.*?\*/|//[^\n]*','',POST,flags=re.S).splitlines():
        if line.strip():
            match=re.fullmatch(r'call ACME_fnc_([A-Za-z0-9_]+);',line.strip())
            assert match,line
            assert f'class {match[1]} {{}};' in CFG,match[1]
    print("fork phase 39 remaining clinical runtime ownership checks: PASS")


if __name__ == "__main__":
    test_source_contract()
