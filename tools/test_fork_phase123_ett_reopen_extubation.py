"""B237: executable legacy source contract; failures must not block collection."""

def test_source_contract():
    """ETT reopen preserves geometry; deliberate extubation clears cuff and securement on the owner."""
    from pathlib import Path
    ROOT=Path(__file__).resolve().parents[1]
    F=ROOT/'addons/acm_extended/functions'
    open_=(F/'fn_laryngoOpen.sqf').read_text()
    init=(F/'fn_laryngoInit.sqf').read_text()
    ext=(F/'fn_laryngoExtubate.sqf').read_text()
    cfg=(ROOT/'addons/acm_extended/config.cpp').read_text()
    assert 'if (_patient getVariable ["ACME_ETT_Secured", false]) then' in open_
    assert '0.999' not in open_[open_.index('// already intubated'):open_.index('// can this airway')]
    secured=init[init.index('if (uiNamespace getVariable ["ACME_laryngo_reopenSecured"'):init.index('// coming back to a tube')]
    assert 'ACME_ETT_Depth' in secured and '[_dsp, _savedDepth] call ACME_fnc_laryngoTubeFrames' in secured
    resume=init[init.index('if (uiNamespace getVariable ["ACME_laryngo_resume"'):init.index('// suction mode.')]
    for token in ['ACME_ETT_CuffInflated','ACME_ETT_TipFrac','ACME_laryngo_tubeAnchorRel','ACME_fnc_laryngoTubePose']:
        assert token in resume
    assert 'if (_cuffUp) then' in resume and 'ACME_laryngo_state", "cuff"' in resume
    assert 'ACME_fnc_procedureAllowed' in ext and 'ACME_ETT_Inserted' in ext
    assert '[_patient, "ettExtubate", [_medic]] call ACME_fnc_ownerDispatch;' in ext
    owner=(F/'fn_ownerDispatch.sqf').read_text().split('case "ettExtubate": {',1)[1].split('case "laryngoConsequence"',1)[0]
    assert 'if (_patient getVariable ["ACME_ETT_Inserted", false]) then' in owner
    assert '[_patient, false, false, false, false, true, false] call ACME_fnc_ettAirwayStateCommit;' in owner
    assert owner.index('call ACME_fnc_ventAirwayLoss') < owner.index('call ACME_fnc_ettAirwayStateCommit') < owner.index('"ACME_ettReturnTube"')
    block=cfg[cfg.index('class ACME_Extubate'):cfg.index('class ACME_OpenAirwayView')]
    assert "(_patient getVariable ['ACME_ETT_Inserted', false])" in block
    assert "treatmentTime = 4;" in block
    assert "!(_patient getVariable ['ACME_ETT_CuffInflated', false])" not in block
    assert "!(_patient getVariable ['ACME_ETT_Secured', false])" not in block
    print('PASS phase123: ETT reopen preserves geometry and deliberate extubation clears securement/cuff on the owner after its treatment')


if __name__ == "__main__":
    test_source_contract()
