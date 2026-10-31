"""Execute current rate, page-focus, seal-rearm and owner-store boundaries.

Engine controls, config reads and networking are stand-ins, not native acceptance.
No clinical algorithm is replaced to obtain these results.
"""
import pytest
from test_menu_death_lifecycle import execute
from test_b157_native_rate import rate_source
from test_bounded_selector_lifetime import setup as selector_setup, selector_contract
from test_bounded_tag_contracts import source
from test_burp_carry_repeat import burp_setup
from test_b156_medication_accuracy import setup as medication_setup

@pytest.mark.parametrize('lease', [
    '[1,_patient,"Head","InsertNPA",7]',
    '[1,_patient,"Head","InsertNPA",6]',
    '[1,_patient,"Body","InsertNPA",7]',
    '[]',
])
def test_configured_normal_speed_never_inherits_faster_workspace_rate(lease):
    execute('''
        private _bodyPart="Head"; private _classname="InsertNPA";
        private _animDuration=3; private _treatmentTime=5; private _ignoreAnimCoef=false;
        _medic setVariable ["ACME_treatmentPoseEpoch",7];
        CBA_fnc_globalEvent={_events pushBack _this;};
    ''' + f'_medic setVariable ["ACME_nativeTreatmentRate",{lease}];' +
        'call {' + rate_source(1) + '};' + '''
        [count _events==1,"missing/duplicate normal-speed update"] call _check;
        [((_events select 0) select 1 select 1)==1,"normal-speed treatment inherited a faster rate"] call _check;
        [_treatmentTime==5,"normal-speed config changed treatment time"] call _check;
    ''')

@pytest.mark.parametrize('view', ['body', 'other'])
@pytest.mark.parametrize('infusion', [False, True])
def test_non_draw_page_does_not_create_focus_stealing_controls(view, infusion):
    execute(selector_setup() + f'uiNamespace setVariable ["ACME_SK_View","{view}"];' +
        ('_display setVariable ["ACME_SK_Return",["bag"]];' if infusion else '') + '''
        call _renderPrefix; call _renderPrefix;
        [count _created==0 && {count _rows==0},"hidden Draw-page controls created on Body Map"] call _check;
        [(_writes findIf {(_x select 1)=="ctrlEnable" && {_x select 2}})<0,"hidden Draw-page control enabled"] call _check;
    ''')


def test_page_gate_contract_rejects_early_control_creation_even_with_original_gate_present():
    text=source('skPendingTagRender')
    marker='private _showSetup = (_view == "syringe");'
    assert marker in text
    with pytest.raises((AssertionError, ValueError)):
        selector_contract(render=text.replace(marker, 'call ACME_fnc_skPendingTagEnsure;\n'+marker))

@pytest.mark.parametrize('kind', ['trauma', 'thora'])
@pytest.mark.parametrize('direction', [-1,1])
@pytest.mark.parametrize('reverse_steps', [1,2,4])
def test_partial_reverse_never_rearms_relief(kind, direction, reverse_steps):
    execute(burp_setup(kind) + f'private _direction={direction};' + '''
        [_direction] call _lift;
        [_burpRequests==1 && {_effects==1},"initial relief missing"] call _check;
    ''' + f'for "_i" from 1 to {reverse_steps} do {{[-_direction] call _wheel;}};' + '''
        [_direction] call _lift;
        [_burpRequests==1 && {_effects==1},"partial reversal bypassed complete-reseal requirement"] call _check;
        [-_direction] call _lift; [_direction] call _lift;
        [_burpRequests==2 && {_effects==2},"full reseal did not rearm"] call _check;
    ''')

@pytest.mark.parametrize('public', [False, True])
@pytest.mark.parametrize('local_owner', [False, True])
def test_real_medication_store_writer_preserves_owner_and_publication_policy(public, local_owner):
    execute(medication_setup() + f'_medicLocal={str(local_owner).lower()};' + '''
        _medic setVariable ["ACME_narcStore",[["old"]]];
    ''' + f'private _result=[_medic,[["new"]],{str(public).lower()}] call ACME_fnc_narcStoreCommit;' + f'''
        [_result isEqualTo {str(local_owner).lower()},"owner authorization result wrong"] call _check;
        [count _storePublications=={int(local_owner)},"remote writer published or local write was lost"] call _check;
    ''' + (f'''
        [((_storePublications select 0) select 2) isEqualTo {str(public).lower()},"writer changed publication policy"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo [["new"]],"local store update lost"] call _check;
    ''' if local_owner else '''
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo [["old"]],"nonowner changed store"] call _check;
    '''))
