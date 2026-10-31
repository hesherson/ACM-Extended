"""Resource, owner-attach and fluid-credit contracts for direct propofol bottles.

The optional SQF-VM check executes the production compatibility predicate. Native
object locality/UI commands still require Arma acceptance; no Python model claims
to reproduce those commands or the roller-clamp implementation.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
FUN = ROOT / "addons/acm_extended/functions"


def read(name):
    return (FUN / f"fn_{name}.sqf").read_text()


def bottle_transaction_fixture():
    # Reuse B230's declared engine boundaries and execute the current production
    # factory/owner transaction/register/ACK functions. Only the mocked config
    # catalogue gains this real B273 action; custody/decision code is unchanged.
    helpers = ROOT / 'addons/acm_extended/tools'
    if str(helpers) not in sys.path:
        sys.path.insert(0, str(helpers))
    from test_b230_prepared_infusion_transaction import setup, execute
    fixture = setup().replace('"SalineIV_500","MagnesiumBag"', '"SalineIV_500","MagnesiumBag","ACME_PropofolIV_50"')
    fixture += r'''
      _configuredType="ACME_Propofol";_configuredVolume=50;
      _validClasses pushBack "Propofol_IV";
      _set=["set1","ACM_Vial_Propofol","ACME_PropofolIV_50","","","","Propofol 500mg",false,"propofol",50,0];
      _prepared=["set1","ACM_Vial_Propofol","ACME_PropofolIV_50","Propofol",500,1800,20,0,0,10,50,0,_medic,objNull,[["Propofol",500,1]],"set1",50,"propofol-bottle"];
      call _store;
      _request=[_medic,_patient,_medic,"ACM_Vial_Propofol","ACME_PropofolIV_50",objNull,"leftarm",true,0,50,_prepared,0,"Propofol 500mg"];
    '''
    return fixture, execute


@pytest.mark.parametrize('route', ['iv', 'io'])
def test_production_bottle_attach_binds_500mg_to_50ml_and_ack_custody(route):
    fixture, execute = bottle_transaction_fixture()
    if route == 'io':
        fixture += '_request set [6,"body"];_request set [7,false];_request set [8,-1];'
    execute(fixture + r'''
      call _pending;call _send;
      [call _ack select 1,"valid paired bottle rejected"] call _check;
      private _bags=call _stock;private _meds=call _entries;
      [count _bags==1 && {(_bags select 0 select 0)=="ACME_Propofol"} && {(_bags select 0 select 1)==50},"bottle carrier wrong"] call _check;
      [count _meds==1 && {(_meds select 0 select 11)=="Propofol"} && {(_meds select 0 select 14)==500},"propofol dose wrong"] call _check;
      [(_meds select 0 select 23)==(_bags select 0 select 8),"dose lost physical bottle identity"] call _check;
      [(_meds select 0 select 26)==10 && {(_meds select 0 select 22)==0},"concentration or initially closed clamp wrong"] call _check;
      [count _bagWrites==1 && {count _medWrites==1} && {(_bagWrites select 0 select 1)!="[]"},"plain unmedicated bottle published"] call _check;
      [count (_medic getVariable "ACME_infusion_PreparedBags")==1 && {count (_medic getVariable "ACME_preparedIVSets")==1},"bottle consumed before owner ACK"] call _check;
      call _send;[count (call _stock)==1 && {_factoryCalls==1},"replay created a second bottle"] call _check;
      (call _ack) call ACME_fnc_preparedAttachAck;
      (call _ack) call ACME_fnc_preparedAttachAck;
      [(_medic getVariable "ACME_infusion_PreparedBags") isEqualTo [] && {(_medic getVariable "ACME_preparedIVSets") isEqualTo []},"accepted bottle custody not settled"] call _check;
      [count _clampQueue==1 && {count _refunds==0},"duplicate ACK opened clamp twice or returned unopened stock"] call _check;
    ''')


@pytest.mark.parametrize('invalid', ['marker', 'component', 'volume', 'set-kind', 'set-volume', 'missing-set', 'missing-prepared', 'saline-mixture', 'occupied'])
def test_production_bottle_owner_rejects_bad_or_missing_custody_before_carrier_creation(invalid):
    fixture, execute = bottle_transaction_fixture()
    edit = {
        'marker': '_prepared set [17,"saline"];call _store;',
        'component': '_prepared set [14,[["Propofol",499,1]]];call _store;',
        'volume': '_prepared set [10,49];call _store;',
        'set-kind': '_set set [8,"saline"];call _store;',
        'set-volume': '_set set [9,49];call _store;',
        'missing-set': '_medic setVariable ["ACME_preparedIVSets",[]];',
        'missing-prepared': '_medic setVariable ["ACME_infusion_PreparedBags",[]];',
        'saline-mixture': '_configuredType="Saline";',
        'occupied': '_patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[["Saline",100,1,0,true,-1,100,-1,"other-bag"]]]]];',
    }[invalid]
    execute(fixture + edit + r'''
      private _beforeBags=str (_patient getVariable "ACM_circulation_IV_Bags");
      private _beforePrepared=str (_medic getVariable "ACME_infusion_PreparedBags");
      private _beforeSets=str (_medic getVariable "ACME_preparedIVSets");
      call _pending;call _send;
      [!(call _ack select 1) && {_factoryCalls==0},"invalid custody created a carrier"] call _check;
      [str (_patient getVariable "ACM_circulation_IV_Bags")==_beforeBags && {call _entries isEqualTo []},"rejection changed bag or medication state"] call _check;
      (call _ack) call ACME_fnc_preparedAttachAck;
      [str (_medic getVariable "ACME_infusion_PreparedBags")==_beforePrepared && {str (_medic getVariable "ACME_preparedIVSets")==_beforeSets},"rejection lost custody"] call _check;
      [count _clampQueue==0 && {count _refunds==0},"rejection opened clamp or duplicated unopened vial"] call _check;
    ''')


def test_spiking_captures_selected_unopened_source_and_debits_one_line():
    source = read("spikePropofolBottle")
    assert 'ACM_circulation_TransfusionMenu_Selected_Inventory' in source
    assert 'objectParent _medic' in source
    assert '[_medic, _patient, _mode, _vehicle, _holder, _token, _release], 1.6]' in source
    assert source.count('call ACME_fnc_transfusionTakeSelected') == 1
    assert '[_medic, _patient, "ACM_Vial_Propofol", _mode, _vehicle]' in source
    assert source.count('call ACME_fnc_treatmentSupplyTake;') == 1
    assert '[_medic, _patient, ["ACME_IVLine"]]' in source
    assert '[_bottleReceipt] call ACME_fnc_treatmentSupplyRefund;' in source
    assert '[_bottleReceipt, false]' in source and '[_lineReceipt, false]' in source
    # Partial vial ledgers cannot be pooled to synthesize a new physical bottle.
    for forbidden in ('ACME_infusion_openVials', 'ACME_fnc_infusionVialVolume', 'ACME_fnc_medicationTakeSources'):
        assert forbidden not in source
    assert '[["Propofol", 500, 1]], _uid, 50, "propofol-bottle"]' in source
    assert '0, 0, CBA_missionTime, 50,' in source  # prepared clamp is initially closed


def test_shared_patient_or_vehicle_bottle_uses_same_owner_lease_as_syringe_draws():
    source = read('spikePropofolBottle')
    assert 'private _holder = [_medic, _patient, _vehicle] param [_mode, objNull];' in source
    assert '[_medic, _holder] call ACME_fnc_vialLeaseEnsure;' in source
    assert '[_medic, _patient, _mode, _vehicle, _holder, _token, _release, _begin], 3,' in source
    assert '(_acceptedLease param [1, ""]) == _token' in source
    assert '(_acceptedLease param [2, 0]) > serverTime' in source
    assert source.index('if (!_leaseValid) exitWith') < source.index('call ACME_fnc_transfusionTakeSelected')
    assert '[_holder, "vialLease", [_medic, "release", _token]]' in source
    assert 'if (_ownsAccepted) then {' in source and 'if (_ownsPending) then {' in source
    assert 'if (_holder isEqualTo _medic) exitWith' in source


def test_prepared_bottle_retains_custody_until_owner_ack_and_uses_existing_clamp():
    source = read("spikePropofolBottle")
    assert 'setVariable ["ACME_preparedIVSets", _sets, true]' in source
    assert 'setVariable ["ACME_infusion_PreparedBags", _prepared, true]' in source
    owner = read("preparedAttachLocal")
    for guard in (
        '_item == "ACM_Vial_Propofol"', '_action == "ACME_PropofolIV_50"',
        '_carrierVolume == 50', '(_prepared param [17, ""]) == "propofol-bottle"',
        '_components isEqualTo [["Propofol", 500, 1]]',
        '(_set param [8, ""]) == "propofol"', '(_set param [9, 0]) == 50',
    ):
        assert guard in owner
    assert '_x isEqualTo _prepared' in owner
    assert 'ACME_fnc_preparedAttachBlockReason' in owner
    request = read("preparedAttachRequest")
    assert 'if ((_prepared param [15, ""]) == "" && {_staged isEqualTo []}) then {' in request
    for name in ('givePreparedBag', 'preparedAttachRequest', 'preparedAttachLocal', 'preparedAttachAck'):
        assert 'ACME_IVLine' not in read(name), name  # hanging never consumes a second administration line
    ack = read("preparedAttachAck")
    assert ack.index('if (!_ok) exitWith') < ack.index('forEach ["ACME_infusion_PreparedBags", "ACME_preparedIVSets"]')
    assert 'ACME_fnc_queueInfusionClamp' in ack
    assert 'ACME_fnc_openRollerClamp' not in source
    plain_hang = read('preparedHangCommit')
    assert 'if (_kind == "propofol" || {_bloodClass == "ACM_Vial_Propofol"}' in plain_hang
    assert plain_hang.index('if (_kind == "propofol"') < plain_hang.index('private _bloodUid =')


def test_propofol_is_not_a_saline_admixture_and_syringe_bolus_registry_remains():
    registry = read("initMedicationRegistry")
    allowed = re.search(r'ACME_infusion_allowedMedications\s*=\s*\[(.*?)\];', registry, re.S).group(1)
    assert '"Propofol"' not in allowed
    assert 'if (_medication == "Propofol") exitWith {false};' in read("registerPreparedBag")
    assert '(_ctx param [3, ""]) == "ACME_Propofol"' in read("injectIntoBag")
    # The Narc Box still reads the complete registry; only infusion mode applies this filter.
    rows = read("medicationSourceRows")
    assert 'if (_infusion && {!(_med in _allowedMeds)}) then {continue};' in rows
    config = (ROOT / 'addons/acm_extended/config.cpp').read_text()
    assert 'class Propofol_IV: ACM_IV_Medication' in config
    assert 'class ACM_Vial_Propofol: ACE_ItemCore' in config


def test_emulsion_volume_cannot_credit_saline_blood_plasma_or_return_unopened_stock():
    flow = (ROOT / 'addons/circulation/functions/fnc_getBloodVolumeChange.sqf').read_text()
    # Medication admission is computed before the dedicated no-credit fluid arm.
    assert flow.index('call ACME_fnc_fluidCommit') < flow.index('case "ACME_Propofol":')
    arm = flow.split('case "ACME_Propofol":', 1)[1].split('case "Plasma":', 1)[0]
    assert '_salineVolumeChange' not in arm and '_bloodVolumeChange' not in arm
    assert '_plasmaVolumeChange' not in arm and '_reactionBloodVolumeChange' not in arm
    registry = read("initMedicationRegistry")
    premixes = registry.split('ACME_infusion_premixedByType =', 1)[1]
    assert '"acme_propofol"' not in premixes
    assert 'if (_type == "Saline" || {_flush}) then {' in read("fluidCommit")
    assert '(_bag param [0, ""]) == "ACME_Propofol"' in read("transfusionRemoveBagCommit")
    pull = read('transfusionPullCommit')
    guard = pull[pull.index('private _medicated ='):pull.index('private _prepared = ["pull"')]
    assert '_type == "ACME_Propofol"' in guard
    assert '(_x param [23,""]) == _uid' in guard  # identified medication carrier
    assert '(_x param [2,-1]) == _idx' in guard  # legacy carrier fallback
    assert 'if (_medicated) exitWith {[false,' in guard
    assert 'Use Remove Infusion for a medicated bag. The infusion remains attached.' in guard
    # Pull never clears the dose or converts a medicated carrier to plain fluid.
    # Explicit Remove Infusion owns that deliberate discard through its writer.
    assert 'ACME_fnc_infusionDeliver' not in pull
    assert 'ACME_fnc_infusionMedicationStateCommit' not in pull
    remove = read('infusionRemoveLocal')
    assert remove.index('call ACME_fnc_infusionRetire;') < remove.index('_arr deleteAt _index;')
    retire = read('infusionRetire')
    assert '[_patient, _x, true] call ACME_fnc_infusionDeliver;' in retire
    assert '[_patient, _keep] call ACME_fnc_infusionMedicationStateCommit;' in retire
    setter = (ROOT / 'addons/circulation/functions/fnc_setIVLocal.sqf').read_text()
    special = re.search(r'private _special = .*?;', setter).group(0)
    assert '"ACME_Propofol"' in special  # accidental access removal retains exact bag/dose, never a fresh vial


def test_production_emulsion_compatibility_predicate_in_sqf_vm():
    executable = os.environ.get('ACME_SQF_VM') or os.environ.get('SQFVM') or shutil.which('sqfvm')
    if not executable:
        pytest.skip('SQF-VM executable not configured; native object/UI acceptance remains separate')
    source = read('infusionRegisterCore')
    # Execute only the pure production guard; SQF-VM does not implement Arma locality.
    guard = source.split('private _isPropofolBottle =', 1)[1].split('private _classIV =', 1)[0]
    code = 'ACME_test_guard = {params ["_type","_medication","_solutionMl","_hasExisting"];private _foundBag=[_type];private _existing=if (_hasExisting) then {[1]} else {[]};private _isPropofolBottle=' + guard + ';"accepted"};'
    cases = [
        ('ACME_Propofol', 'Propofol', 0, False, 'accepted'),
        ('ACME_Propofol', 'Propofol', 0, True, ''),
        ('ACME_Propofol', 'Propofol', 1, False, ''),
        ('ACME_Propofol', 'Midazolam', 0, False, ''),
        ('ACME_Propofol', 'Ketamine', 5, False, ''),
        ('Saline', 'Propofol', 0, False, ''),
        ('Saline', 'Propofol', 5, False, ''),
        ('Saline', 'Ketamine', 5, False, 'accepted'),
        ('Magnesium', 'Magnesium', 0, False, 'accepted'),
    ]
    for index, (fluid, med, ml, existing, expected) in enumerate(cases):
        flag = 'true' if existing else 'false'
        code += f'if ((["{fluid}","{med}",{ml},{flag}] call ACME_test_guard) != "{expected}") then {{throw "case-{index}";}};'
    code += 'diag_log "PROP_COMPATIBILITY_PASS";'
    result = subprocess.run([executable, '-a', '--suppress-welcome', '--no-execute-print', '--no-work-print', '--sqf', code], cwd=ROOT, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PROP_COMPATIBILITY_PASS' in result.stdout, result.stdout + result.stderr
    assert '[ERR]' not in result.stdout and '[FAT]' not in result.stdout, result.stdout
