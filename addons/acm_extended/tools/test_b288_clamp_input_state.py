"""Execute clamp input/redraw with a deliberately delayed patient owner.

Native display/control drawing and message transport are explicit boundaries.
The real setter, scroll function, redraw and extracted mouse-release/unload
callbacks execute; these cases do not certify native pointer routing or sound.
"""
import re

import pytest

import test_menu_death_lifecycle as lifecycle
from source_scan import lex, matching, split_args
from test_b274_clamp_overlay import redraw_setup
from test_bounded_selector_lifetime import ui_commands
from test_menu_death_lifecycle import ROOT, adapt, execute, read


@pytest.fixture(autouse=True)
def native_boundary_warnings_fail(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert '[WRN]' not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, 'run', checked)


def source(name):
    text = read(name).replace('findDisplay 86200', '_clampDisplay')
    text = text.replace('findDisplay 86000', '_transfusionDisplay')
    text = text.replace('diag_frameno', '_inputFrame')
    text = re.sub(r'(_\w+) displayCtrl (\d+)', r'\2', text)
    # Native object handles are namespace stand-ins, retaining type rejection
    # for malformed scalar/string requests at this explicit engine boundary.
    text = text.replace('isEqualType objNull', 'isEqualType profileNamespace')
    text = re.sub(r'\bfinite (_\w+)', r'(\1 isEqualType 0)', text)
    return ui_commands(text)


def mouse_callback(event):
    text = read('onClampLoad')
    tokens = lex(text)
    pairs = matching(tokens)
    found = []
    for i, token in enumerate(tokens):
        if token.value != 'ctrlAddEventHandler' or tokens[i - 1].value != '_ctrlDrag':
            continue
        args = split_args(tokens, i + 2, pairs[i + 1], pairs)
        if args[0][0].value != event:
            continue
        callback = args[1]
        assert callback[0].value == '{' and callback[-1].value == '}'
        found.append(text[callback[0].offset + 1:callback[-1].offset])
    assert len(found) == 1, event
    return adapt(found[0])


def unload_callback():
    config = (ROOT / 'addons/acm_extended/config.cpp').read_text()
    clamp = config.split('class ACME_RollerClamp_Dialog {', 1)[1]
    callback = re.search(r'\bonUnload\s*=\s*"([^"]*)";', clamp).group(1)
    return adapt(callback)


def load_prefix():
    # Run the real per-display session initializer. Artwork construction is a
    # separate native boundary; the setter/redraw must see its actual metadata.
    return source('onClampLoad').split('// Vision is owned', 1)[0]


def setup(synchronous=False):
    return redraw_setup() + r'''
        private _transfusionDisplay=profileNamespace;
        private _inputFrame=100;
        private _commands=[];
        private _wire=[];
        ACME_infusion_minDropsPerMinute=0;
        ACME_infusion_maxDropsPerMinute=120;
        CBA_fnc_targetEvent={_wire pushBack +_this;};
        // Full row shape emitted by infusionRegisterCore, including persisted
        // concentration/revision fields; no sparse nil-filled clinical row.
        private _entry=["dose-A","leftarm",0,"Saline",0,true,-1,100,-1,100,100,
            "Epinephrine","Epinephrine_IV",10,10,0,CBA_missionTime,0,CBA_missionTime,
            600,20,20,0.4,"bag-A",0,0,0.1,1];
        _patient setVariable ["ACME_infusion_BagMedications",[_entry]];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [
            ["leftarm",[["Saline",100,1,0,true,-1,100,-1,"bag-A"]]]]];
        _selected=[_patient,[0]];
        ACME_fnc_clinicalEpoch={7};
        ACME_fnc_playClampSfx={};ACME_fnc_updateTransfusionControls={};
        uiNamespace setVariable ["ACME_RollerClamp_DLG",_clampDisplay];
        uiNamespace setVariable ["ACME_RollerClamp_InitDisplay",objNull];
        uiNamespace setVariable ["ACME_RollerClamp_Context",[_patient,[0],["dose-A"],7,"bag-A"]];
        uiNamespace setVariable ["ACME_RollerClamp_Position",0.4];
        uiNamespace setVariable ["ACME_RollerClamp_DropSet",20];
        uiNamespace setVariable ["ACME_RollerClamp_Dragging",false];
        uiNamespace setVariable ["ACME_RollerClamp_ReleaseOnUp",false];
        uiNamespace setVariable ["ACME_RollerClamp_ScrollFrame",-1];
        private _applyOwner={
            params ["_request"];
            (_request select 2)call ACME_fnc_infusionClampLocal;
        };
        ACME_fnc_infusionMedicationStateCommit={
            params ["_patient","_entries"];
            _patient setVariable ["ACME_infusion_BagMedications",_entries];true
        };
    ''' + 'ACME_fnc_infusionClampLocal={' + source('infusionClampLocal') + '};' + \
        ('ACME_fnc_ownerDispatch={_commands pushBack +_this;[_this]call _applyOwner;};' if synchronous else
         'ACME_fnc_ownerDispatch={_commands pushBack +_this;};') + \
        ''.join('ACME_fnc_' + name + '={' + source(name) + '};'
                for name in ('setClampPosition', 'scrollClamp', 'cycleDropSet', 'toggleClamp', 'adjustDripRate')) + \
        ('ACME_fnc_clampResult={' + source('clampResult') + '};' if
         (ROOT / 'addons/acm_extended/functions/fn_clampResult.sqf').exists() else '') + \
        'private _initialize={' + load_prefix() + '};call _initialize;' + \
        'private _mouseDown={' + mouse_callback('MouseButtonDown') + '};' + \
        'private _mouseUp={' + mouse_callback('MouseButtonUp') + '};' + \
        'private _unload={' + unload_callback() + '};'


def test_remote_scroll_keeps_new_wheel_position_until_owner_state_arrives():
    execute(setup() + r'''
        [_clampDisplay,1]call ACME_fnc_scrollClamp;
        [count _commands==1 && {abs (((_commands select 0 select 2)select 3)-0.5)<0.000001},"scroll did not request its exact new position"]call _check;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.5)<0.000001,"scroll redraw reset the desired position before owner delivery"]call _check;
        [((_patient getVariable "ACME_infusion_BagMedications")select 0 select 22)==0.4,"UI wrote the remote clinical entry before owner delivery"]call _check;
        for "_tick" from 1 to 5 do {call ACME_fnc_updateClampDialog;};
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.5)<0.000001,"periodic redraw replaced pending input with the stale replica"]call _check;
        [_commands select 0]call _applyOwner;call ACME_fnc_updateClampDialog;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.5)<0.000001,"confirmed position did not remain on the wheel"]call _check;
    ''')


@pytest.mark.parametrize('sticky', (False, True), ids=('held-drag', 'second-click-release'))
def test_actual_drag_release_keeps_the_last_drawn_position(sticky):
    execute(setup() + r'''
        uiNamespace setVariable ["ACME_RollerClamp_Dragging",true];
        uiNamespace setVariable ["ACME_RollerClamp_Position",0.72];
    ''' + ('[_clampDisplay,0]call _mouseDown;_nowTime=_nowTime+0.1;' if sticky else
           'uiNamespace setVariable ["ACME_RollerClamp_DownTime",_nowTime-1];') + r'''
        [_clampDisplay,0]call _mouseUp;
        [!(uiNamespace getVariable "ACME_RollerClamp_Dragging"),"release did not end the actual drag"]call _check;
        [count _commands==1 && {abs (((_commands select 0 select 2)select 3)-0.72)<0.000001},"release did not commit the actual displayed position"]call _check;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.72)<0.000001,"release redraw reset the displayed position"]call _check;
        call ACME_fnc_updateClampDialog;
        [abs (((_wheelMoves select ((count _wheelMoves)-1))select 0)-0.72)<0.000001,"wheel artwork returned to the old replica after release"]call _check;
    ''')


def test_scroll_events_accumulate_from_pending_input_and_deduplicate_one_frame():
    execute(setup() + r'''
        [_clampDisplay,1]call ACME_fnc_scrollClamp;
        [_clampDisplay,1]call ACME_fnc_scrollClamp;
        [count _commands==1,"control/display relays double-stepped one physical wheel event"]call _check;
        _inputFrame=_inputFrame+1;
        [_clampDisplay,1]call ACME_fnc_scrollClamp;
        [count _commands==2 && {abs (((_commands select 1 select 2)select 3)-0.6)<0.000001},"next scroll restarted from the stale replicated value"]call _check;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.6)<0.000001,"rapid remote scrolling lost accumulated input"]call _check;
    ''')


def test_actual_unload_does_not_submit_the_pre_release_replica():
    execute(setup() + r'''
        uiNamespace setVariable ["ACME_RollerClamp_Dragging",true];
        uiNamespace setVariable ["ACME_RollerClamp_Position",0.72];
        uiNamespace setVariable ["ACME_RollerClamp_DownTime",_nowTime-1];
        [_clampDisplay,0]call _mouseUp;
        [_clampDisplay]call _unload;
        [(_commands findIf {abs (((_x select 2)select 3)-0.72)>0.000001})<0,"closing the clamp sent the reset replica back to the owner"]call _check;
    ''')


def test_synchronous_patient_owner_commits_without_a_visual_reset():
    execute(setup(True) + r'''
        [_clampDisplay,1]call ACME_fnc_scrollClamp;
        [count _commands==1 && {abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.5)<0.000001},"synchronous owner path changed its wheel state"]call _check;
        [abs (((_patient getVariable "ACME_infusion_BagMedications")select 0 select 22)-0.5)<0.000001,"synchronous owner did not commit its exact position"]call _check;
    ''')


def test_current_drag_retains_its_visual_authority_over_older_replicated_state():
    execute(setup() + r'''
        uiNamespace setVariable ["ACME_RollerClamp_Dragging",true];
        uiNamespace setVariable ["ACME_RollerClamp_Position",0.72];
        call ACME_fnc_updateClampDialog;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.72)<0.000001 && {count _commands==0},"redraw stole the wheel while it was actively dragged"]call _check;
    ''')


def test_drop_set_click_does_not_immediately_restore_the_old_owner_value():
    execute(setup() + r'''
        call ACME_fnc_cycleDropSet;
        [count _commands==1 && {(_commands select 0 select 2 select 4)==60},"drop-set click did not request the next size"]call _check;
        [(uiNamespace getVariable "ACME_RollerClamp_DropSet")==60,"drop-set redraw immediately restored the old remote value"]call _check;
    ''')


def test_delayed_owner_does_not_expire_the_last_user_input_after_a_wall_clock_timeout():
    execute(setup() + r'''
        [0.73,true]call ACME_fnc_setClampPosition;
        _nowTime=_nowTime+20;
        call ACME_fnc_updateClampDialog;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.73)<0.000001,"wall-clock timeout restored unconfirmed remote state"]call _check;
        [((_uiTexts get "86206")find "Applying...")>=0,"unconfirmed edit lost its Applying indication"]call _check;
        [count _commands==1,"presentation timeout retransmitted a clinical edit"]call _check;
    ''')


def test_rapid_a_b_a_input_waits_for_the_latest_exact_owner_receipt():
    execute(setup() + r'''
        [0.7,true]call ACME_fnc_setClampPosition;
        [0.4,true]call ACME_fnc_setClampPosition;
        [count _commands==2,"rapid edits were not sent in sequence"]call _check;
        private _latestRequest=(_commands select 1 select 2)param[5,[]];
        [count _latestRequest==3,"live clamp edit has no exact owner request identity"]call _check;
        // The old public value already equals the newest desired A. It must
        // not count as confirmation before B's delayed publication arrives.
        call ACME_fnc_updateClampDialog;
        [_commands select 0]call _applyOwner;
        call ACME_fnc_updateClampDialog;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.4)<0.000001,"older B publication displaced the still-pending latest A"]call _check;
        [_commands select 1]call _applyOwner;
        call ACME_fnc_updateClampDialog;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.4)<0.000001,"latest exact A confirmation changed the chosen input"]call _check;
        private _confirmed=(_patient getVariable "ACME_infusion_BagMedications")select 0;
        [(_latestRequest select 1)in(_confirmed param[28,[]]),"owner state did not echo the latest exact request"]call _check;
    ''')


def test_older_replication_after_confirmation_does_not_rewind_the_same_display():
    execute(setup() + r'''
        [0.7,true]call ACME_fnc_setClampPosition;
        [0.6,true]call ACME_fnc_setClampPosition;
        private _olderStamp=((_commands select 0 select 2)select 5)select 1;
        private _latestStamp=((_commands select 1 select 2)select 5)select 1;
        [_commands select 1]call _applyOwner;call ACME_fnc_updateClampDialog;
        private _confirmed=+((_patient getVariable "ACME_infusion_BagMedications")select 0);
        private _oldReplica=+_confirmed;
        _oldReplica set[21,[0.7]call ACME_fnc_clampPositionToDrops];
        _oldReplica set[22,0.7];_oldReplica set[28,[_olderStamp]];
        _patient setVariable["ACME_infusion_BagMedications",[_oldReplica]];
        call ACME_fnc_updateClampDialog;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.6)<0.000001,"older readback overwrote a confirmed display edit"]call _check;
        // A later clinician's accepted change has a genuinely changed receipt
        // ledger while preserving this client's latest accepted request.
        private _newer=+_confirmed;
        _newer set[21,[0.3]call ACME_fnc_clampPositionToDrops];
        _newer set[22,0.3];_newer set[28,[_latestStamp,[9,1,1]]];
        _patient setVariable["ACME_infusion_BagMedications",[_newer]];
        call ACME_fnc_updateClampDialog;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.3)<0.000001,"confirmed local edit masked a newer clinician's owner state"]call _check;
    ''')


def test_rapid_drop_set_and_toggle_changes_use_the_latest_local_intent():
    execute(setup() + r'''
        call ACME_fnc_cycleDropSet;
        call ACME_fnc_cycleDropSet;
        [(uiNamespace getVariable "ACME_RollerClamp_DropSet")==10,"second drop-set click restarted from stale owner size"]call _check;
        [(_commands select 0 select 2 select 4)==60&&{(_commands select 1 select 2 select 4)==10},"drop-set requests did not accumulate"]call _check;
        call ACME_fnc_toggleClamp;
        [abs (uiNamespace getVariable "ACME_RollerClamp_Position")<0.000001,"close toggle ignored current local input"]call _check;
        call ACME_fnc_toggleClamp;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-1)<0.000001,"second toggle reread stale owner drops instead of reopening"]call _check;
        [count _commands==4,"rapid controls dispatched duplicate or missing edits"]call _check;
    ''')


@pytest.mark.parametrize('replacement', ('patient', 'bag', 'epoch', 'display'))
def test_pending_input_cannot_follow_a_replacement_context(replacement):
    change = {
        'patient': '_selected=[parsingNamespace,[0]];parsingNamespace setVariable["ACME_infusion_BagMedications",[_replacement]];',
        'bag': '_replacement set[23,"other-bag"];_patient setVariable["ACME_infusion_BagMedications",[_replacement]];',
        'epoch': 'ACME_fnc_clinicalEpoch={8};_patient setVariable["ACME_infusion_BagMedications",[_replacement]];',
        'display': '_clampDisplay=parsingNamespace;uiNamespace setVariable["ACME_RollerClamp_InitDisplay",_clampDisplay];',
    }[replacement]
    execute(setup() + r'''
        [0.7,true]call ACME_fnc_setClampPosition;
        private _replacement=+((_patient getVariable "ACME_infusion_BagMedications")select 0);
        _replacement set[22,0.2];_replacement set[21,[0.2]call ACME_fnc_clampPositionToDrops];
    ''' + change + r'''
        call ACME_fnc_updateClampDialog;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.7)>0.000001,"old pending input followed a replacement clamp context"]call _check;
        [count _commands==1,"context replacement dispatched the stale UI input"]call _check;
    ''')


def test_positive_reply_without_public_exact_receipt_does_not_confirm_old_replica():
    execute(setup() + r'''
        [0.7,true]call ACME_fnc_setClampPosition;
        private _stamp=((_commands select 0 select 2)select 5)select 1;
        [_patient,_medic,_stamp,true]call ACME_fnc_clampResult;
        call ACME_fnc_updateClampDialog;
        private _edit=uiNamespace getVariable["ACME_RollerClamp_Edit",[]];
        [count _edit==10&&{!(_edit select 8)}&&{abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.7)<0.000001},"positive reply treated old public state as exact confirmation"]call _check;
        [((_uiTexts get "86206")find "Applying...")>=0,"reply without replicated receipt removed Applying"]call _check;
        [_commands select 0]call _applyOwner;call ACME_fnc_updateClampDialog;
        _edit=uiNamespace getVariable["ACME_RollerClamp_Edit",[]];
        [_edit select 8,"published exact receipt did not confirm the edit"]call _check;
        [((_uiTexts get "86206")find "Applying...")<0,"confirmed edit retained Applying"]call _check;
    ''')


def test_negative_reply_retires_only_the_matching_latest_edit():
    execute(setup() + r'''
        [0.7,true]call ACME_fnc_setClampPosition;
        [0.6,true]call ACME_fnc_setClampPosition;
        private _old=((_commands select 0 select 2)select 5)select 1;
        private _latest=((_commands select 1 select 2)select 5)select 1;
        [_patient,_medic,_old,false]call ACME_fnc_clampResult;
        call ACME_fnc_updateClampDialog;
        private _edit=uiNamespace getVariable["ACME_RollerClamp_Edit",[]];
        [count _edit==10&&{(_edit select 5)isEqualTo _latest}&&{abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.6)<0.000001},"older rejection discarded the newer local edit"]call _check;
        [_patient,_medic,_latest,false]call ACME_fnc_clampResult;
        call ACME_fnc_updateClampDialog;
        [(uiNamespace getVariable["ACME_RollerClamp_Edit",[]])isEqualTo []&&{abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-0.4)<0.000001},"matching rejection left an uncommitted desired value latched"]call _check;
        [count _commands==2,"rejection fabricated a compensating clinical write"]call _check;
    ''')


def test_stationary_drag_release_and_unload_reuse_one_exact_owner_request():
    execute(setup() + r'''
        [0.72,true]call ACME_fnc_setClampPosition;
        private _stamp=((_commands select 0 select 2)select 5)select 1;
        for "_tick" from 1 to 12 do {
            _nowTime=_nowTime+0.25;
            [0.72,true]call ACME_fnc_setClampPosition;
        };
        uiNamespace setVariable ["ACME_RollerClamp_Dragging",true];
        uiNamespace setVariable ["ACME_RollerClamp_DownTime",_nowTime-1];
        [_clampDisplay,0]call _mouseUp;
        private _edit=uiNamespace getVariable["ACME_RollerClamp_Edit",[]];
        [count _commands==1&&{(_edit select 5)isEqualTo _stamp},"stationary drag or release allocated repeated receipt traffic"]call _check;
        [_clampDisplay]call _unload;
        [count _commands==1&&{abs (((_commands select 0 select 2)select 3)-0.72)<0.000001},"unload resent or changed the unchanged final input"]call _check;
    ''')


def test_rapid_rate_adjustments_accumulate_through_the_central_input_setter():
    execute(setup() + r'''
        [1]call ACME_fnc_adjustDripRate;
        [1]call ACME_fnc_adjustDripRate;
        private _latest=[30]call ACME_fnc_dropsToClampPosition;
        [count _commands==2&&{abs (((_commands select 1 select 2)select 3)-_latest)<0.000001},"rate controls reused old remote drops instead of pending input"]call _check;
        [abs ((uiNamespace getVariable "ACME_RollerClamp_Position")-_latest)<0.000001,"rate controls bypassed the stable pending display"]call _check;
    ''')
