"""B259: slow vascular medication enters before completion; 40 BPM is not free CO2 clearance."""
from pathlib import Path
from test_menu_death_lifecycle import adapt, execute
from test_bounded_normal_push_lifetime import setup as push_setup

F = Path(__file__).resolve().parents[1] / "functions"


def text(name):
    return (F / f"fn_{name}.sqf").read_text(encoding="utf-8-sig")


def test_300_second_normal_calcium_push_starts_incremental_worker():
    execute(push_setup() + r"""
        _durationText = "300";
        uiNamespace setVariable ["ACME_SK_PendingInjection",["leftarm",1,"vascular"]];
        [call ACME_fnc_skConfirmInjection,"normal long push did not start"] call _check;
        [_hcStarts == 1, "300s vascular push still waits until completion"] call _check;
        [count _waits == 0, "300s vascular push scheduled completion-only callback"] call _check;
        [count _delivered == 0, "mock worker accidentally administered instant dose"] call _check;
    """)


def test_default_three_second_and_im_push_still_use_original_visual_lifecycle():
    execute(push_setup() + r"""
        _durationText = "";
        [call ACME_fnc_skConfirmInjection,"default push did not start"] call _check;
        [_hcStarts == 0 && {count _waits == 1},
            "default three-second push unexpectedly changed route"] call _check;
    """)


def test_standard_worker_batches_after_one_second_not_after_entire_duration():
    src=text("hardcorePushSendBatch")
    begin=src.index("private _batchSec = if")
    end=src.index("if (!_force &&",begin)
    # SQF-VM does not implement HashMap getOrDefault; exercise the verbatim
    # branch after replacing only that engine-owned metadata lookup.
    assert '_job getOrDefault ["standardTimed",false]' in src[begin:end]
    expr=adapt(src[begin:end]).replace(
        '_job getOrDefault ["standardTimed",false]', '_standardTimed'
    )
    execute(r"""
        private _standardTimed=true;
        private _standardBatch={
    """ + expr + r""" _batchSec; };
        [call _standardBatch == 1, "normal medication aliquots are not admitted each second"] call _check;
        _standardTimed=false;
        ACME_hcMed_pushBatchSec=5;
        [call _standardBatch == 5, "hardcore push's separate batch setting was overwritten"] call _check;
    """)


def test_slow_push_retains_inventory_escrow_and_locality_checks():
    start=text("hardcorePushStart")
    tick=text("hardcorePushTick")
    ack=text("hardcorePushAck")
    assert '["standardTimed",_standardTimed]' in start
    assert '["providerLocalityEpoch",ACE_player getVariable' in start
    assert 'ACME_fnc_medicationRequest' in text("hardcorePushSendBatch")
    assert 'ACME_fnc_hardcorePushRestoreDelta' in ack
    assert '[_patient,_body,_site] call ACME_fnc_medicationLineBloodBusy' in tick
    assert '(_medic getVariable ["ACME_providerLocalityEpoch",0]) != _localityEpoch' in tick


def test_expiratory_emptying_efficiency_is_calculated_from_live_rate():
    src=text("ventDriveTick")
    begin=src.index("private _emptyingFrac =")
    end=src.index(";",src.index("private _emptyingEfficiency =",begin))+1
    calculation=adapt(src[begin:end])
    execute("private _tNeeded=1.8; private _tE=1.0; " + calculation + r"""
        [abs (_emptyingEfficiency - 0.3086419753) < 0.001,
            "40BPM short expiratory time did not reduce useful ventilation"] call _check;
        _tE=3.3;
    """ + calculation.replace("private _emptyingFrac","_emptyingFrac").replace("private _emptyingEfficiency","_emptyingEfficiency") + r"""
        [_emptyingEfficiency > 0.999, "normal-rate ventilation was penalized"] call _check;
    """)


def test_simv_40_bpm_does_not_bypass_arrest_gas_exchange_penalties():
    src=text("circHandle")
    assert "private _ventOwnsArrest = (_patient getVariable" in src
    assert "if (!_ventOwnsArrest) then {" in src
    assert 'private _actualRR = _patient getVariable ["ACME_vent_effectiveRR", 0];' in src
    assert 'private _cprEfficiency = linearConversion [12, 40, _actualRR, 1, 0.45, true];' in src
    assert "_ventFrac = _ventFrac * _cprEfficiency;" in src
    assert "private _respDeficit = 0;" in src
    assert "private _mvAlv = ((" in text("ventDriveTick")
    assert "* _emptyingEfficiency;" in text("ventDriveTick")


def test_b259_does_not_reset_chemical_acidosis_or_force_wake():
    src=text("circHandle")
    new = src[src.index("// B259: the generic hand-bagging floor"):src.index("private _paCO2Normal =",src.index("// B259: the generic hand-bagging floor"))]
    assert 'setVariable ["ACME_circ_State"' not in new
    assert "ACE_isUnconscious" not in new
    assert "CPRSucceeded" not in new
    assert "_metabolicAcidosis =" not in new
