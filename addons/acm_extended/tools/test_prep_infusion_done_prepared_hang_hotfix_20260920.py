from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(errors='ignore')


def test_prep_infusion_has_one_done_button_and_no_cancel_action():
    src = read('functions/fn_patchDrawDialog.sqf')
    assert '_ctrlCancel ctrlSetText "Done";' in src
    assert 'Confirm the medications in this bag and return to Transfuse' in src
    assert '_ctrlCancel ctrlSetEventHandler ["ButtonClick", "call ACME_fnc_infusionDone"]' in src
    assert '_ctrlCancel ctrlSetText "Cancel";' not in src
    assert '_doneBtn ctrlShow false;' in src
    assert '_doneBtn ctrlEnable false;' in src


def test_done_waits_for_real_bag_state_and_uninjected_syringe():
    src = read('functions/fn_infusionDone.sqf')
    assert 'ACME_infusion_pendingInject' in src
    assert 'ACM_circulation_SyringeDraw_DrawnAmount' in src
    assert 'ACM_circulation_SyringeDraw_Moving' in src
    assert 'Medication is still in the syringe.' in src
    assert 'Infusion bag confirmed:' in src
    assert '_display closeDisplay 2;' in src


def test_prepared_hang_runtime_is_complete_and_owner_authoritative():
    cfg = read('config.cpp')
    owner = read('functions/fn_ownerDispatch.sqf')
    init = read('functions/fn_clinicalInit.sqf')
    hang = read('functions/fn_hangPreparedSet.sqf')
    commit = read('functions/fn_preparedHangCommit.sqf')
    result = read('functions/fn_preparedHangResult.sqf')

    assert 'class preparedHangCommit {};' in cfg
    assert 'class preparedHangResult {};' in cfg
    assert 'case "preparedHang": {_args call ACME_fnc_preparedHangCommit;};' in owner
    assert '["ACME_preparedHangResult", {_this call ACME_fnc_preparedHangResult;}] call CBA_fnc_addEventHandler;' in init
    assert 'ACME_preparedHangPending' in init
    assert re.search(r'\[_target,\s*"preparedHang",\s*_args\] call ACME_fnc_ownerDispatch;', hang)
    assert hang.index('call ACME_fnc_inventoryLedgerReserve') < hang.index('call ACME_fnc_ownerDispatch')
    assert 'if (_accepted) then {' in hang
    assert '_sets deleteAt _setIdx;' not in hang
    assert 'if (!local _patient) exitWith {[_patient, "preparedHang", _this] call ACME_fnc_ownerDispatch;};' in commit
    assert '_medic setVariable ["ACME_preparedIVSets", _sets, true];' in commit
    assert 'ACME_preparedHangResult' in commit
    assert 'ACME_preparedHangPending' in result
