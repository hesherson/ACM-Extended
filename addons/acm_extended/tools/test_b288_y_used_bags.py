"""Execute the complete production Y handler with exact virtual used-leg custody.

Only native config/UI/inventory/ACE item delivery are boundaries. No temporary
nominal native item can stand in for an exact partial used bag.
"""
import re

import pytest

from test_b274_transfusion_preparation import stage_setup, gui
from test_menu_death_lifecycle import execute, read


def setup():
    source = gui(read('transfusionYTubing'))
    source = source.replace('isNull(_display)', '(_display isEqualTo objNull)')
    source = source.replace('isClass (configFile >> "CfgWeapons" >> _itemClass)', '(_itemClass in _bagClasses)')
    source = source.replace('isClass (configFile >> "CfgWeapons" >> _c)', '(_c in _bagClasses)')
    source = re.sub(r'finite \(([^\n]*?)\)', r'((\1) call _finite)', source)
    # Literal native item removals are still exercised through the same stock
    # boundary as the existing B274/B287 production Y tests.
    return stage_setup().replace('_medic removeItem _x;', '[_medic,_x] call ACME_fnc_itemTake;') + r'''
    private _bagClasses=["ACM_BloodBag_ON_500","ACM_SalineBag_500"];
    private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
    ACM_circulation_fnc_formatFluidBagName={params ["_type"];if (_type=="Blood") then {"ACM_BloodBag_ON_500"} else {"ACM_SalineBag_500"}};
    private _bloodRow=["blood1","Blood",183,0,0,500,"Partial blood"];
    private _salineRow=["saline1","Saline",47,0,-1,500,"Partial saline"];
    _medic setVariable ["ACME_usedBags",[+_bloodRow,+_salineRow]];
    _medic setVariable ["fixtureStock",["ACME_YTubing"]];
    _rowData=["Blood|usedbag|USED|blood1","Saline|usedbag|USED|saline1"];
    ACME_fnc_transfusionYTubing={''' + source + r'''};
    private _presses={_selection=0;[] call ACME_fnc_transfusionYTubing;_selection=1;[] call ACME_fnc_transfusionYTubing;[] call ACME_fnc_transfusionYTubing;};
    private _finish={(_waits select 0 select 1) call (_waits select 0 select 0);};
    '''


def test_used_legs_remain_exact_virtual_rows_until_final_beat_then_fund_one_set():
    execute(setup() + r'''
    call _presses;
    [count _waits==1 && {count _debits==0},"used build did not wait before debit"] call _check;
    [(_medic getVariable "ACME_usedBags") isEqualTo [_bloodRow,_salineRow],"used legs materialized before completion"] call _check;
    [(_medic getVariable "fixtureStock") isEqualTo ["ACME_YTubing"],"partial bag became a nominal native item"] call _check;
    call _finish;
    private _sets=_medic getVariable ["ACME_preparedIVSets",[]];
    [count _sets==1 && {((_sets select 0) select 9)==183} && {((_sets select 0) select 10)==47},"exact partial volumes lost"] call _check;
    [(_medic getVariable "ACME_usedBags") isEqualTo [] && {(_medic getVariable "fixtureStock") isEqualTo []},"sources not consumed exactly once"] call _check;
    [count _debits==1 && {((_debits select 0) select 1)=="ACME_YTubing"},"virtual used legs debited nominal native items"] call _check;
    call _finish;
    [count (_medic getVariable "ACME_preparedIVSets")==1 && {count _debits==1},"replayed completion funded another set"] call _check;
    ''')


@pytest.mark.parametrize('mutation', [
    '_display=objNull;',
    'missionNamespace setVariable ["ACME_yPending",""];',
    '_medic setVariable ["ACME_persistenceFrozen",true];',
    '_patient setVariable ["ACME_persistenceFrozen",true];',
    '_medic setVariable ["ACME_equipmentKitEpoch",1];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    'ACM_circulation_TransfusionMenu_Selected_BodyPart="rightarm";',
    'ACM_circulation_TransfusionMenu_Target=missionNamespace;',
    '_alive=false;',
])
def test_cancel_context_change_or_freeze_keeps_partial_bags_and_all_native_supplies(mutation):
    execute(setup() + 'call _presses;' + mutation + r'''
    call _finish;
    [(_medic getVariable "ACME_usedBags") isEqualTo [_bloodRow,_salineRow],"canceled build consumed exact used bags"] call _check;
    [(_medic getVariable "fixtureStock") isEqualTo ["ACME_YTubing"] && {count _debits==0},"cancel created/consumed nominal blood or saline"] call _check;
    [(_medic getVariable ["ACME_preparedIVSets",[]]) isEqualTo [],"canceled build produced set"] call _check;
    [(_medic getVariable ["ACME_yBuildPending",[]]) isEqualTo [],"canceled build left save blocked"] call _check;
    ''')


@pytest.mark.parametrize('leg', ['blood', 'saline'])
def test_missing_or_changed_used_leg_during_beat_does_not_consume_other_leg_or_tubing(leg):
    change = '_medic setVariable ["ACME_usedBags",[_salineRow]];' if leg == 'blood' else '_medic setVariable ["ACME_usedBags",[_bloodRow]];'
    execute(setup() + 'call _presses;' + change + r'''
    private _before=str (_medic getVariable "ACME_usedBags");
    call _finish;
    [str (_medic getVariable "ACME_usedBags")==_before && {count _debits==0},"missing leg consumed surviving source"] call _check;
    [(_medic getVariable "fixtureStock") isEqualTo ["ACME_YTubing"],"missing leg created nominal native bag"] call _check;
    ''')


def test_changed_used_volume_after_selection_cannot_be_inflated_from_old_snapshot():
    execute(setup() + r'''
    _selection=0;[] call ACME_fnc_transfusionYTubing;
    private _changed=+_bloodRow;_changed set [2,12];
    _medic setVariable ["ACME_usedBags",[_changed,_salineRow]];
    _selection=1;[] call ACME_fnc_transfusionYTubing;[] call ACME_fnc_transfusionYTubing;
    [count _waits==0 && {count _debits==0},"stale exact volume scheduled build"] call _check;
    [((_medic getVariable "ACME_usedBags") select 0 select 2)==12,"stale selection rewrote current remaining volume"] call _check;
    ''')


def test_existing_same_class_full_native_bag_is_not_substituted_for_selected_partial():
    execute(setup() + r'''
    _medic setVariable ["fixtureStock",["ACME_YTubing","ACM_BloodBag_ON_500","ACM_SalineBag_500"]];
    call _presses;call _finish;
    private _stock=+(_medic getVariable "fixtureStock");_stock sort true;
    [_stock isEqualTo ["ACM_BloodBag_ON_500","ACM_SalineBag_500"],"selected partial consumed unrelated full native bags"] call _check;
    [(_medic getVariable "ACME_usedBags") isEqualTo [],"selected partial remains alongside funded set"] call _check;
    ''')


def test_failed_prepared_enqueue_refunds_native_tubing_and_exact_virtual_rows():
    execute(setup() + r'''
    ACME_fnc_preparedInventoryCommit={false};
    call _presses;call _finish;
    [(_medic getVariable "ACME_usedBags") isEqualTo [_bloodRow,_salineRow],"failed enqueue lost virtual source"] call _check;
    [(_medic getVariable "fixtureStock") isEqualTo ["ACME_YTubing"],"failed enqueue did not refund tubing"] call _check;
    [(_medic getVariable ["ACME_preparedIVSets",[]]) isEqualTo [],"failed enqueue left an unfunded set"] call _check;
    call _finish;
    [count _refunds==1,"replayed failure duplicated tubing refund"] call _check;
    ''')


@pytest.mark.parametrize('used_leg', ['blood', 'saline'])
def test_mixed_used_and_native_legs_preserve_exact_partial_and_consume_only_real_native_leg(used_leg):
    config = r'''
    _rowData=["Blood|usedbag|USED|blood1","ACM_SalineBag_500|SalineIV_500"];
    _medic setVariable ["ACME_usedBags",[_bloodRow]];
    _medic setVariable ["fixtureStock",["ACME_YTubing","ACM_SalineBag_500"]];
    ''' if used_leg == 'blood' else r'''
    _rowData=["ACM_BloodBag_ON_500|BloodIV_ON_500","Saline|usedbag|USED|saline1"];
    _medic setVariable ["ACME_usedBags",[_salineRow]];
    _medic setVariable ["fixtureStock",["ACME_YTubing","ACM_BloodBag_ON_500"]];
    '''
    expected = '((_sets select 0) select 9)==183 && {((_sets select 0) select 10)==0}' if used_leg == 'blood' else '((_sets select 0) select 9)==0 && {((_sets select 0) select 10)==47}'
    execute(setup() + config + 'call _presses;call _finish;private _sets=_medic getVariable ["ACME_preparedIVSets",[]];' +
            f'[count _sets==1 && {{{expected}}},"mixed partial volume changed"] call _check;' + r'''
    [count _debits==2 && {(_medic getVariable "fixtureStock") isEqualTo []} && {(_medic getVariable "ACME_usedBags") isEqualTo []},"mixed sources not consumed exactly once"] call _check;
    ''')


def test_late_old_build_callback_cannot_clear_or_commit_a_new_build():
    execute(setup() + r'''
    call _presses;
    private _pending=missionNamespace getVariable "ACME_yBuildPending";
    _nowTime=_nowTime+3;
    [] call ACME_fnc_transfusionYTubing;
    [count _waits==1 && {(missionNamespace getVariable "ACME_yBuildPending") isEqualTo _pending},"wall-time expiry replaced a pending build"] call _check;
    call _finish;
    [count (_medic getVariable ["ACME_preparedIVSets",[]])==1 && {count _debits==1},"original current build not funded exactly once"] call _check;
    call _finish;
    [count (_medic getVariable ["ACME_preparedIVSets",[]])==1 && {count _debits==1},"late replay funded another build"] call _check;
    ''')


def test_changed_clinical_episode_cancels_without_consuming_partial_rows():
    execute(setup() + r'''
    call _presses;ACME_fnc_clinicalEpoch={2};call _finish;
    [(_medic getVariable "ACME_usedBags") isEqualTo [_bloodRow,_salineRow] && {count _debits==0},"old clinical episode consumed Y sources"] call _check;
    ''')


def test_final_native_leg_debit_failure_refunds_tubing_and_keeps_partial_row():
    execute(setup() + r'''
    _rowData=["Blood|usedbag|USED|blood1","ACM_SalineBag_500|SalineIV_500"];
    _medic setVariable ["ACME_usedBags",[_bloodRow]];
    _medic setVariable ["fixtureStock",["ACME_YTubing","ACM_SalineBag_500"]];
    call _presses;
    private _oldUse=ace_medical_treatment_fnc_useItem;
    ace_medical_treatment_fnc_useItem={if (((_this select 2) select 0)=="ACM_SalineBag_500") exitWith {[objNull,"",false]};_this call _oldUse};
    call _finish;
    private _stock=+(_medic getVariable "fixtureStock");_stock sort true;
    [_stock isEqualTo ["ACME_YTubing","ACM_SalineBag_500"],"late native failure lost tubing or saline"] call _check;
    [(_medic getVariable "ACME_usedBags") isEqualTo [_bloodRow],"late native failure consumed partial blood"] call _check;
    [(_medic getVariable ["ACME_preparedIVSets",[]]) isEqualTo [],"unfunded native leg created prepared set"] call _check;
    ''')


@pytest.mark.parametrize('cancel', ['unconscious', 'control_switch'])
def test_provider_incapacitation_or_same_frame_control_switch_cancels_sources(cancel):
    change = '_medic setVariable ["ACE_isUnconscious",true];' if cancel == 'unconscious' else 'ACME_fnc_controlledProvider={_patient};'
    execute(setup() + 'call _presses;' + change + r'''
    call _finish;
    [count _debits==0 && {(_medic getVariable "ACME_usedBags") isEqualTo [_bloodRow,_salineRow]},"incapacitated/uncontrolled provider consumed source"] call _check;
    ''')


def test_same_vehicle_reach_contract_allows_physically_separated_seats():
    execute(setup() + r'''
    _distance=100;ACME_fnc_patientInteractionDistance={0};
    call _presses;call _finish;
    [count (_medic getVariable ["ACME_preparedIVSets",[]])==1 && {count _debits==1},"reachable same-cabin patient rejected by raw seat distance"] call _check;
    ''')


def test_superseded_callback_retires_only_its_old_unit_busy_flag():
    execute(setup() + r'''
    call _presses;
    private _new=[999,["new provider context"]];
    missionNamespace setVariable ["ACME_yBuildPending",_new];
    call _finish;
    [(missionNamespace getVariable "ACME_yBuildPending") isEqualTo _new,"old callback cleared newer global build"] call _check;
    [(_medic getVariable ["ACME_yBuildPending",[]]) isEqualTo [],"old callback left old provider permanently busy"] call _check;
    [count _debits==0,"superseded provider consumed source"] call _check;
    ''')


@pytest.mark.parametrize('actor', ['provider', 'patient'])
def test_new_native_supply_debit_honors_frozen_save_participant(actor):
    target = '_medic' if actor == 'provider' else '_patient'
    execute(setup() + f'{target} setVariable ["ACME_persistenceFrozen",true];' + r'''
    private _receipt=[_medic,_patient,["ACME_YTubing"]] call ACME_fnc_treatmentSupplyTake;
    [_receipt isEqualTo [] && {count _debits==0} && {(_medic getVariable "fixtureStock") isEqualTo ["ACME_YTubing"]},"save freeze admitted a fresh native debit"] call _check;
    ''')
