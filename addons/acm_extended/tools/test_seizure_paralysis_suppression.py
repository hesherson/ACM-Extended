from pathlib import Path

ADDON = Path(__file__).resolve().parents[1]
ROOT = ADDON.parent

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="strict")

def test_shared_control_is_registered_and_rocuronium_is_not_anticonvulsant():
    cfg = read(ADDON / "config.cpp")
    ctl = read(ADDON / "functions" / "fn_seizureControl.sqf")
    assert "class seizureControl {};" in cfg
    assert "ACME_fnc_benzoOnBoard" in ctl
    assert "ACME_fnc_sedationComponents" in ctl
    assert "ACME_seizure_propofolControlWeight" in ctl
    assert "ACME_seizure_ketamineControlFloor" in ctl
    assert "ACME_roc_paralyzed" not in ctl
    assert "Rocuronium is deliberately absent" in ctl

def test_existing_seizure_machine_uses_general_control_and_preserves_breakthrough():
    s = read(ADDON / "functions" / "fn_lidoToxTick.sqf")
    assert "call ACME_fnc_seizureControl" in s
    assert "_seizureControlled" in s
    assert "private _benzo =" not in s
    assert "_mida >=" not in s
    assert "_causePresent && {!_seizureControlled}" in s
    assert "_triggerNow && {!_seizureControlled}" in s

def test_paralysis_masks_motor_expression_without_clearing_cerebral_state():
    motion = read(ADDON / "functions" / "fn_seizureMotion.sqf")
    gesture = read(ADDON / "functions" / "fn_seizureGestureAdvance.sqf")
    collapse = read(ADDON / "functions" / "fn_seizureCollapse.sqf")
    lido = read(ADDON / "functions" / "fn_lidoToxTick.sqf")
    assert 'ACME_roc_paralyzed' in motion
    assert 'ACME_roc_paralyzed' in gesture
    assert 'ACME_roc_paralyzed' in collapse
    active_block = lido.split('case "active":', 1)[1].split('case "postictal":', 1)[0]
    assert "ACME_roc_paralyzed" not in active_block
    assert "ACME_fnc_seizureMotion" in active_block

def test_paralysis_prevents_convulsive_opa_ejection():
    collapse = read(ADDON / "functions" / "fn_seizureCollapse.sqf")
    assert '!(_patient getVariable ["ACME_roc_paralyzed", false])' in collapse
    assert 'ACM_airway_AirwayItem_Oral' in collapse

def test_control_state_is_debuggable_and_reset():
    debug = read(ADDON / "functions" / "fn_debugMenuClinical.sqf")
    clear = read(ADDON / "functions" / "fn_clearAllAilments.sqf")
    fields = read(ADDON / "functions" / "fn_clinicalFields.sqf")
    assert "SEIZURE CONTROL" in debug
    assert '"MASKED"' in debug
    for name in ("ACME_seizure_drive","ACME_seizure_suppression","ACME_seizure_suppressed"):
        assert name in debug
        assert name in clear
        assert name in fields

def test_internal_tuning_keeps_old_midazolam_baseline():
    s = read(ADDON / "functions" / "fn_initDrugPhysiologyConfig.sqf")
    assert "ACME_seizure_driveBase = 1.0;" in s
    assert "ACME_seizure_midazolamControlWeight = 1.0;" in s
    assert "ACME_seizure_propofolControlWeight = 1.0;" in s
    assert "ACME_seizure_ketamineControlFloor = 0.30;" in s
    assert "ACME_seizure_controlHysteresis = 0.10;" in s
