"""B260: preserve measured epinephrine and evaluate ventilation ownership correctly."""
from pathlib import Path
from test_bounded_normal_push_lifetime import execute, setup

F = Path(__file__).resolve().parents[1] / "functions"


def source(name):
    return (F / f"fn_{name}.sqf").read_text(encoding="utf-8-sig")


def test_long_generic_vascular_push_still_uses_incremental_controller():
    execute(setup() + r"""
        _durationText="300";
        [call ACME_fnc_skConfirmInjection,"slow normal push rejected"] call _check;
        [_hcStarts==1 && {count _waits==0},
            "generic 300-second vascular dose reverted to completion-only"] call _check;
    """)


def test_measured_epinephrine_retains_legacy_confirmation_and_partial_volume():
    execute(setup() + r"""
        _durationText="30";
        _row set [6,"epiMixB12"];
        [_medic,[_row,_other]] call ACME_fnc_narcStoreCommit;
        [call ACME_fnc_skConfirmInjection,"measured epi confirmation rejected"] call _check;
        [_hcStarts==0 && {count _waits==1},
            "measured epi bypassed its selector-captured partial-dose protocol"] call _check;
    """)


def test_cpr_penalty_updates_current_co2_deficit_without_direct_rosc_write():
    circ=source("circHandle")
    block=circ.split("// B259: the generic hand-bagging floor",1)[1].split("private _paCO2Normal =",1)[0]
    assert "if (!_ventOwnsArrest) then {" in block
    assert "private _compressing = !isNull" in block
    assert "_ventFrac = _ventFrac * _cprEfficiency;" in block
    assert "_effVent = _targetRR * _ventFrac;" in block
    assert "_respDeficit = (1 - (_ventFrac min 1)) max 0 min 1;" in block
    assert 'CPRSucceeded' not in block
