"""Execute the existing Y workflow and its canonical cooler-draw continuation.

Native UI/inventory helpers and the async cooler draw are boundaries. The real
three-press handler, pending request guard, continuation checks, and final
physical component transaction execute from production source.
"""
import pytest

from test_b274_transfusion_preparation import stage_setup, gui
from test_menu_death_lifecycle import execute, read


def fixture():
    callback = gui(read('coolerYDrawDone')).replace('local _owner', 'true').replace('alive _owner', '_alive').replace('isNull(_display)', '(_display isEqualTo objNull)').replace('isNull _owner', '(_owner isEqualTo objNull)')
    return stage_setup().replace("_medic removeItem _x;", "[_medic,_x] call ACME_fnc_itemTake;") + r'''
        private _draws=[];private _clinicalEpoch=1;
        ACME_fnc_clinicalEpoch={_clinicalEpoch};
        ACME_fnc_coolerDraw={_draws pushBack _this;true};
        ACME_fnc_coolerYDrawDone={''' + callback + r'''};
        _medic setVariable ["ACME_equipmentKitEpoch",0];
        _medic setVariable ["ACME_providerLocalityEpoch",0];
        missionNamespace setVariable ["ACME_yCoolerDrawPending",[]];
        missionNamespace setVariable ["ACME_yCoolerDrawSerial",0];
        missionNamespace setVariable ["ACME_yPendingBloodUsedId",""];
        missionNamespace setVariable ["ACME_yPendingSalineUsedId",""];
        missionNamespace setVariable ["ACME_yBuildingActive",-1];
        _rowData=["ACM_BloodBag_ON_500|BloodIV_ON_500|COOLER","ACM_SalineBag_500|SalineIV_500"];
        _medic setVariable ["fixtureStock",["ACM_SalineBag_500","ACME_YTubing"]];
        _selection=0;[] call ACME_fnc_transfusionYTubing;
        _selection=1;[] call ACME_fnc_transfusionYTubing;
        [] call ACME_fnc_transfusionYTubing;
    '''


def deliver():
    return r'''
        private _stock=+(_medic getVariable ["fixtureStock",[]]);
        _stock pushBack "ACM_BloodBag_ON_500";
        _medic setVariable ["fixtureStock",_stock];
        private _completion=(_draws select 0) select 2;
        [true,_completion select 1] call (_completion select 0);
    '''


def test_press_three_claims_cooler_once_and_never_debits_projection():
    execute(fixture()+r'''
        [] call ACME_fnc_transfusionYTubing;
        [count _draws==1,"repeated press queued more than one source claim"] call _check;
        [count _waits==0 && {count _debits==0},"build consumed before cooler source arrived"] call _check;
        [(_medic getVariable "fixtureStock") isEqualTo ["ACM_SalineBag_500","ACME_YTubing"],"draw request minted a loose bag"] call _check;
    ''')


def test_success_resumes_existing_build_once_and_retains_cold_tag():
    execute(fixture()+r'''
        // A native list rebuild now includes a loose row. The selected source
        // remains the cooler whose canonical debit was acknowledged.
        _rowData pushBack "ACM_BloodBag_ON_500|BloodIV_ON_500";
    '''+deliver()+r'''
        [count _waits==1 && {count _draws==1},"successful draw did not resume one build"] call _check;
        private _completion=(_draws select 0) select 2;
        [true,_completion select 1] call (_completion select 0);
        [count _waits==1,"replayed draw completion scheduled another build"] call _check;
        (_waits select 0 select 1) call (_waits select 0 select 0);
        private _sets=_medic getVariable ["ACME_preparedIVSets",[]];
        [count _sets==1 && {(_sets select 0 select 7)},"canonical cooled source lost cold tag"] call _check;
        [(_medic getVariable "fixtureStock") isEqualTo [],"physical components were not consumed exactly once"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    'ACM_circulation_TransfusionMenu_Target=missionNamespace;',
    'ACM_circulation_TransfusionMenu_Selected_BodyPart="rightarm";',
    'ACM_circulation_TransfusionMenu_SelectIV=false;',
    'ACM_circulation_TransfusionMenu_Selected_AccessSite=1;',
    'ACM_circulation_TransfusionMenu_Selected_Inventory=1;',
    '_medic setVariable ["ACME_equipmentKitEpoch",1];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    'missionNamespace setVariable ["ACME_yPending","ACM_BloodBag_A_500"];',
    'missionNamespace setVariable ["ACME_yPendingSaline",""];',
    'missionNamespace setVariable ["ACME_yPendingData","changed"];',
    'missionNamespace setVariable ["ACME_yPendingSalineData","changed"];',
    'missionNamespace setVariable ["ACME_yPendingBloodUsedId","changed"];',
    'missionNamespace setVariable ["ACME_yPendingSalineUsedId","changed"];',
    'uiNamespace setVariable ["ACME_preparedListMode",true];',
    'missionNamespace setVariable ["ACME_piggybackPending",["changed"]];',
    '_display=objNull;',
    '_alive=false;',
    '_clinicalEpoch=2;',
])
def test_delayed_draw_keeps_bag_loose_when_original_intent_changed(change):
    execute(fixture()+change+deliver()+r'''
        [count _waits==0 && {count _debits==0},"stale continuation started a Y build"] call _check;
        ["ACM_BloodBag_ON_500" in (_medic getVariable "fixtureStock"),"stale intent discarded delivered source"] call _check;
        [(missionNamespace getVariable "ACME_yCoolerDrawPending") isEqualTo [],"completed request left UI blocked"] call _check;
    ''')


def test_terminal_failed_draw_unblocks_retry_without_creating_inventory():
    execute(fixture()+r'''
        private _completion=(_draws select 0) select 2;
        [false,_completion select 1] call (_completion select 0);
        [(missionNamespace getVariable "ACME_yCoolerDrawPending") isEqualTo [],"failure left pending UI request"] call _check;
        [] call ACME_fnc_transfusionYTubing;
        [count _draws==2 && {count _waits==0} && {count _debits==0},"terminal rejection did not permit a safe fresh request"] call _check;
    ''')


def test_stale_completion_cannot_clear_a_new_request():
    execute(fixture()+r'''
        private _old=missionNamespace getVariable "ACME_yCoolerDrawPending";
        private _new=[999,_old select 1];
        missionNamespace setVariable ["ACME_yCoolerDrawPending",_new];
        private _completion=(_draws select 0) select 2;
        [false,_completion select 1] call (_completion select 0);
        [(missionNamespace getVariable "ACME_yCoolerDrawPending") isEqualTo _new,"old completion canceled newer intent"] call _check;
    ''')
