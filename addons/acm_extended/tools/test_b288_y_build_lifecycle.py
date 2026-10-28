"""Execute Y lifecycle ownership across cancellation and presentation failures.

The full production handler/callbacks run; native UI/config/ACE inventory are
explicit boundaries inherited from the existing Y execution fixtures. Throwing
presentation stand-ins verifies queue/cleanup ordering, not native rendering.
"""
import pytest

from test_b288_y_used_bags import setup
from test_menu_death_lifecycle import execute


PAIR_CLEARED = r'''
    [(missionNamespace getVariable ["ACME_yPending",""])=="" && {(missionNamespace getVariable ["ACME_yPendingSaline",""])==""},"owned component classes left armed"]call _check;
    [(missionNamespace getVariable ["ACME_yPendingData",""])=="" && {(missionNamespace getVariable ["ACME_yPendingSalineData",""])==""},"owned component data left armed"]call _check;
    [(missionNamespace getVariable ["ACME_yPendingBloodVol",0])==0 && {(missionNamespace getVariable ["ACME_yPendingSalineVol",0])==0},"owned exact-volume intent leaked"]call _check;
    [(missionNamespace getVariable ["ACME_yPendingBloodUsedId",""])=="" && {(missionNamespace getVariable ["ACME_yPendingSalineUsedId",""])==""},"owned used-bag IDs leaked"]call _check;
    [(missionNamespace getVariable ["ACME_yPendingBloodUsedRow",[]])isEqualTo [] && {(missionNamespace getVariable ["ACME_yPendingSalineUsedRow",[]])isEqualTo []},"owned used-bag rows leaked"]call _check;
    [(missionNamespace getVariable ["ACME_yPendingPatient",objNull])isEqualTo objNull,"owned pairing patient leaked"]call _check;
'''


BUSY_CLEARED = r'''
    [(missionNamespace getVariable ["ACME_yBuildPending",[]])isEqualTo [],"finished build token leaked"]call _check;
    [(missionNamespace getVariable ["ACME_yBuildingActive",-1])==-1,"finished build timestamp leaked"]call _check;
    [(_medic getVariable ["ACME_yBuildPending",[]])isEqualTo [],"finished provider save fence leaked"]call _check;
'''


def test_rejected_current_context_clears_all_owned_pairing_and_keeps_sources():
    execute(setup() + r'''
    call _presses;
    ACM_circulation_TransfusionMenu_Selected_BodyPart="rightarm";
    call _finish;
    [(_medic getVariable "ACME_usedBags")isEqualTo [_bloodRow,_salineRow] && {count _debits==0},"context cancellation consumed source"]call _check;
    [(_medic getVariable ["ACME_preparedIVSets",[]])isEqualTo [],"context cancellation prepared a set"]call _check;
    ''' + PAIR_CLEARED + BUSY_CLEARED)


def test_build_completion_is_queued_before_synchronous_presentation_failure():
    execute(setup() + r'''
    ACME_fnc_updateTransfusionControls={if ((missionNamespace getVariable ["ACME_yBuildingActive",-1])>=0) then {throw "presentation fault";};};
    try {call _presses;} catch {};
    [count _waits==1,"UI failure prevented durable completion registration"]call _check;
    if (count _waits==1) then {call _finish;};
    [count (_medic getVariable ["ACME_preparedIVSets",[]])==1,"queued build could not finish after presentation failure"]call _check;
    ''' + PAIR_CLEARED + BUSY_CLEARED)


def test_completion_releases_owned_fences_before_final_presentation_failure():
    execute(setup() + r'''
    call _presses;
    ACME_fnc_transfusionFilterInventory={throw "presentation fault";};
    try {call _finish;} catch {};
    [count (_medic getVariable ["ACME_preparedIVSets",[]])==1 && {count _debits==1},"committed sources were lost to a presentation error"]call _check;
    ''' + PAIR_CLEARED + BUSY_CLEARED)


def test_pending_build_remains_authoritative_when_diagnostic_clock_advances():
    execute(setup() + r'''
    call _presses;
    private _pending=missionNamespace getVariable "ACME_yBuildPending";
    _nowTime=_nowTime+30;
    // CBA mission time has not advanced; its existing delayed job still owns this recipe.
    []call ACME_fnc_transfusionYTubing;
    [count _waits==1 && {(missionNamespace getVariable "ACME_yBuildPending")isEqualTo _pending},"wall-clock expiry replaced the existing build job"]call _check;
    call _finish;
    [count (_medic getVariable ["ACME_preparedIVSets",[]])==1 && {count _debits==1},"original job did not complete once"]call _check;
    ''' + PAIR_CLEARED + BUSY_CLEARED)


@pytest.mark.parametrize('change', [
    '_display=objNull;',
    'ACM_circulation_TransfusionMenu_Target=missionNamespace;',
    'ACM_circulation_TransfusionMenu_SelectIV=false;',
    'ACM_circulation_TransfusionMenu_Selected_AccessSite=1;',
    'ACM_circulation_TransfusionMenu_Selected_Inventory=1;',
    '_medic setVariable ["ACME_equipmentKitEpoch",1];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    'ACME_fnc_clinicalEpoch={2};',
    'uiNamespace setVariable ["ACME_preparedListMode",true];',
    'missionNamespace setVariable ["ACME_piggybackPending",["other intent"]];',
    '_medic setVariable ["ACME_persistenceFrozen",true];',
    'ACME_fnc_controlledProvider={_patient};',
])
def test_owned_build_cancellation_retires_all_recipe_metadata(change):
    execute(setup() + 'call _presses;' + change + r'''
    call _finish;
    [(_medic getVariable "ACME_usedBags")isEqualTo [_bloodRow,_salineRow] && {count _debits==0},"cancellation spent sources"]call _check;
    ''' + PAIR_CLEARED + BUSY_CLEARED)


def test_replayed_old_build_preserves_successor_recipe_timer_and_provider_fence():
    execute(setup() + r'''
    call _presses;
    private _old=missionNamespace getVariable "ACME_yBuildPending";
    private _new=[999,+(_old select 1)];
    missionNamespace setVariable ["ACME_yBuildPending",_new];
    missionNamespace setVariable ["ACME_yBuildingActive",12345];
    _medic setVariable ["ACME_yBuildPending",[999,0,0]];
    missionNamespace setVariable ["ACME_yPending","ACM_BloodBag_A_500"];
    missionNamespace setVariable ["ACME_yPendingBloodVol",321];
    private _recipe=[missionNamespace getVariable "ACME_yPending",missionNamespace getVariable "ACME_yPendingData",missionNamespace getVariable "ACME_yPendingSaline",missionNamespace getVariable "ACME_yPendingBloodVol",missionNamespace getVariable "ACME_yPendingBloodUsedRow",missionNamespace getVariable "ACME_yPendingPatient"];
    call _finish;
    [(missionNamespace getVariable "ACME_yBuildPending")isEqualTo _new && {(missionNamespace getVariable "ACME_yBuildingActive")==12345},"old callback retired successor request/timer"]call _check;
    [(_medic getVariable "ACME_yBuildPending")isEqualTo [999,0,0],"old callback retired successor provider fence"]call _check;
    [[missionNamespace getVariable "ACME_yPending",missionNamespace getVariable "ACME_yPendingData",missionNamespace getVariable "ACME_yPendingSaline",missionNamespace getVariable "ACME_yPendingBloodVol",missionNamespace getVariable "ACME_yPendingBloodUsedRow",missionNamespace getVariable "ACME_yPendingPatient"]isEqualTo _recipe,"old callback rewrote successor recipe"]call _check;
    [count _debits==0,"old callback spent successor sources"]call _check;
    ''')


def test_source_commit_reentry_cannot_start_or_replace_the_owned_build():
    execute(setup() + r'''
    call _presses;
    private _owned=missionNamespace getVariable "ACME_yBuildPending";
    ACME_fnc_preparedInventoryCommit={
        [(missionNamespace getVariable "ACME_yBuildPending")isEqualTo _owned,"build token retired before source commit"]call _check;
        _nowTime=_nowTime+30;
        []call ACME_fnc_transfusionYTubing;
        [count _waits==1 && {(missionNamespace getVariable "ACME_yBuildPending")isEqualTo _owned},"source commit reentry replaced owned build"]call _check;
        true
    };
    call _finish;
    [count (_medic getVariable ["ACME_preparedIVSets",[]])==1 && {count _debits==1},"commit reentry duplicated a source"]call _check;
    ''' + PAIR_CLEARED + BUSY_CLEARED)


@pytest.mark.parametrize('fault', ['filter', 'notice', 'prepared_view'])
def test_final_presentation_failures_happen_after_raw_source_and_fence_settlement(fault):
    change = {
        'filter': 'ACME_fnc_transfusionFilterInventory={throw "filter fault";};',
        'notice': 'ace_common_fnc_displayTextStructured={throw "notice fault";};',
        'prepared_view': 'ACME_fnc_togglePreparedSets={throw "prepared view fault";};',
    }[fault]
    execute(setup() + 'call _presses;' + change + r'''
    try {call _finish;} catch {};
    [count (_medic getVariable ["ACME_preparedIVSets",[]])==1 && {count _debits==1},"presentation failure lost committed product"]call _check;
    ''' + PAIR_CLEARED + BUSY_CLEARED)


from test_b287_cooler_y_build import fixture as draw_setup, deliver


@pytest.mark.parametrize('change', [
    '_display=objNull;',
    'ACM_circulation_TransfusionMenu_Target=missionNamespace;',
    'ACM_circulation_TransfusionMenu_Selected_BodyPart="rightarm";',
    'ACM_circulation_TransfusionMenu_SelectIV=false;',
    'ACM_circulation_TransfusionMenu_Selected_AccessSite=1;',
    '_medic setVariable ["ACME_equipmentKitEpoch",1];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    '_clinicalEpoch=2;',
    'uiNamespace setVariable ["ACME_preparedListMode",true];',
    '_medic setVariable ["ACME_persistenceFrozen",true];',
])
def test_context_canceled_draw_clears_owned_recipe_and_keeps_the_delivered_bag(change):
    execute(draw_setup() + change + deliver() + r'''
    [count _waits==0 && {count _debits==0},"canceled draw began source consumption"]call _check;
    ["ACM_BloodBag_ON_500"in(_medic getVariable "fixtureStock"),"canceled draw removed its physical delivered bag"]call _check;
    [(missionNamespace getVariable ["ACME_yCoolerDrawPending",[]])isEqualTo [],"draw fence leaked"]call _check;
    ''' + PAIR_CLEARED)


def test_failed_draw_cleans_recipe_before_refresh_can_fail():
    execute(draw_setup() + r'''
    ACME_fnc_transfusionFilterInventory={throw "draw presentation fault";};
    private _completion=(_draws select 0)select 2;
    try {[false,_completion select 1]call(_completion select 0);}catch{};
    [(missionNamespace getVariable ["ACME_yCoolerDrawPending",[]])isEqualTo [],"failed draw kept ownership fence"]call _check;
    [count _waits==0 && {count _debits==0},"failed draw spent or minted source"]call _check;
    ''' + PAIR_CLEARED)


def test_old_draw_callback_never_clears_a_successor_request_or_recipe():
    execute(draw_setup() + r'''
    private _old=missionNamespace getVariable "ACME_yCoolerDrawPending";
    private _new=[999,_old select 1];
    missionNamespace setVariable ["ACME_yCoolerDrawPending",_new];
    missionNamespace setVariable ["ACME_yPending","ACM_BloodBag_A_500"];
    missionNamespace setVariable ["ACME_yPendingBloodVol",321];
    private _recipe=[missionNamespace getVariable "ACME_yPending",missionNamespace getVariable "ACME_yPendingBloodVol",missionNamespace getVariable "ACME_yPendingPatient"];
    private _completion=(_draws select 0)select 2;
    [false,_completion select 1]call(_completion select 0);
    [(missionNamespace getVariable "ACME_yCoolerDrawPending")isEqualTo _new,"old draw cleared successor request"]call _check;
    [[missionNamespace getVariable "ACME_yPending",missionNamespace getVariable "ACME_yPendingBloodVol",missionNamespace getVariable "ACME_yPendingPatient"]isEqualTo _recipe,"old draw cleared successor recipe"]call _check;
    ''')
