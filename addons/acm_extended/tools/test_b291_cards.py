"""Execute the imported DD1380 document contract and form lifetimes.

Rendering, controls and CBA transport are explicit engine fixtures; normalization,
owner admission, duplicate/revision decisions, page capture and ACKs run checked-out SQF.
"""
from pathlib import Path
import re

import pytest

from test_b156_procedure_supplies import primitives
from test_menu_death_lifecycle import ROOT, adapt, execute

CARD = ROOT / 'addons/card'
FIELDS = ('DD1380_Priority', 'DD1380_Checkboxes', 'DD1380_Text',
          'DD1380_Back_Checkboxes', 'DD1380_Back_Text')
IDS = dict(re.findall(r'^#define\s+(IDC_DD1380_\w+)\s+(\d+)',
                      (CARD / 'ui/idc_macros.hpp').read_text(), re.M))


def source(name):
    text = (CARD / 'functions' / f'fnc_{name}.sqf').read_text()
    for key, value in IDS.items():
        text = re.sub(r'\b' + key + r'\b', value, text)
    # Native locality and UI primitives are fixtures. The guards and ownership
    # decisions remain in the production functions under test.
    text = text.replace('local _patient', '_patientLocal')
    text = text.replace('local _medic', '_medicLocal')
    text = text.replace('cbChecked (_display displayCtrl _x)', '([_display, _x] call _cbChecked)')
    text = text.replace('ctrlText (_display displayCtrl _x)', '([_display, _x] call _ctrlText)')
    text = text.replace('ctrlParent _control', '_control')
    text = text.replace('_display closeDisplay 0', '[_display] call _closeDisplay')
    text = text.replace('createDialog "DD1380_Card1_dlg"', '["DD1380_Card1_dlg"] call _createDialog')
    text = text.replace('createDialog (if (_page == 1) then {"DD1380_Card2_dlg"} else {"DD1380_Card1_dlg"})',
                        '[(if (_page == 1) then {"DD1380_Card2_dlg"} else {"DD1380_Card1_dlg"})] call _createDialog')
    text = text.replace('findDisplay 38580', '_sourceDisplayFixture')
    text = re.sub(r'\bdialog\b', '_dialog', text)
    text = text.replace('serverTime', 'CBA_missionTime')
    text = text.replace('finite (_document select 0)', '((_document select 0) call _nativeFinite)')
    text = re.sub(r'\bfinite (_\w+)', r'(\1 call _nativeFinite)', text)
    return 'DD1380_card_fnc_' + name + '={' + primitives(adapt(text)) + '};'


def setup():
    names = ('fieldIds', 'getDocument', 'receiveData', 'setData', 'resetDocument',
             'saveAck', 'sendData', 'openReady', 'requestDocument', 'openCardLocal',
             'flipPage', 'getDate')
    return r'''
        private _patientLocal=true;private _medicLocal=true;
        private _nativeFinite={_this isEqualType 0;};
        private _sourceDisplayFixture=objNull;
        private _display=missionNamespace;private _notifications=[];
        private _opened=[];private _closed=[];private _submitted=[];
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if !(_key in (keys _map)) exitWith {_default};_map get _key};
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",0]};
        ACM_GUI_fnc_pauseMedicalMenuPFH={_removed pushBack "medicalPFH";};
        ace_common_fnc_displayTextStructured={_notifications pushBack _this;};
        private _createDialog={_opened pushBack (_this select 0);true};
        private _closeDisplay={_closed pushBack (_this select 0);_this call DD1380_card_fnc_setData;};
        private _cbChecked={params ["_d","_id"];private _v=(_d getVariable "fixtureCb") get _id;if (isNil "_v") exitWith {false};_v};
        private _ctrlText={params ["_d","_id"];private _v=(_d getVariable "fixtureText") get _id;if (isNil "_v") exitWith {""};_v};
        _display setVariable ["fixtureCb",createHashMap];_display setVariable ["fixtureText",createHashMap];
    ''' + ''.join(source(n) for n in names) + r'''
        private _data=([_patient,false] call DD1380_card_fnc_getDocument) select 1;
        private _packet=[_patient,_medic,0,"request1",0,_data,0];
        private _context=[_medic,_patient,0,"form1",0,_data,+_data];
        _display setVariable ["DD1380_context",_context];_display setVariable ["DD1380_page",1];
        uiNamespace setVariable ["DD1380_context",_context];
    '''


def test_read_only_normalization_does_not_publish_or_mutate_legacy_state():
    execute(setup() + r'''
        _patient setVariable ["DD1380_Text",createHashMapFromArray [[1107,"Unit A"]]];
        private _doc=[_patient,false] call DD1380_card_fnc_getDocument;
        [(_doc select 1 select 2 get 1107)=="Unit A","legacy document lost"] call _check;
        [isNil {_patient getVariable "DD1380_Document"},"read-only helper published a new canonical document"] call _check;
        [count (_patient getVariable "DD1380_Text")==1,"normalization mutated stored legacy map"] call _check;
    ''')


def test_owner_migrates_old_document_once_then_canonical_wins_over_mixed_mirrors():
    execute(setup() + r'''
        _patient setVariable ["DD1380_Text",createHashMapFromArray [[1107,"Unit A"]]];
        _patient setVariable ["DD1380_Revision",3];
        private _doc=[_patient,true] call DD1380_card_fnc_getDocument;
        _patient setVariable ["DD1380_Text",createHashMapFromArray [[1107,"stale mirror"]]];
        _patient setVariable ["DD1380_Revision",99];
        private _read=[_patient,true] call DD1380_card_fnc_getDocument;
        [_read select 0==3 && {(_read select 1 select 2 get 1107)=="Unit A"},"mixed legacy fields replaced canonical document"] call _check;
        [(_patient getVariable "DD1380_Revision")==3 && {((_patient getVariable "DD1380_Text") get 1107)=="Unit A"},"canonical restore did not repair mirrors"] call _check;
    ''')


@pytest.mark.parametrize('publish', [False, True])
def test_nonowner_get_document_never_writes(publish):
    execute(setup() + '_patientLocal=false;' + f'[_patient,{str(publish).lower()}] call DD1380_card_fnc_getDocument;' + r'''
        [isNil {_patient getVariable "DD1380_Document"},"nonowner published document"] call _check;
    ''')


def test_owner_commit_is_atomic_revisioned_and_duplicate_delivery_is_idempotent():
    execute(setup() + r'''
        (_data select 2) set [1107,"Unit A"];
        _packet call DD1380_card_fnc_receiveData;
        _packet call DD1380_card_fnc_receiveData;
        private _doc=_patient getVariable "DD1380_Document";
        [_doc select 0==1 && {(_doc select 1 select 2 get 1107)=="Unit A"},"document was not committed once"] call _check;
        [count (_patient getVariable "DD1380_Receipts")==1 && {count _events==2},"duplicate delivery changed receipt/revision or omitted ACK"] call _check;
        [((_events select 0 select 1) select 4) && {((_events select 1 select 1) select 4)},"accepted retry was not acknowledged"] call _check;
    ''')


@pytest.mark.parametrize('mutation', [
    '_packet set [2,9];',
    '_packet set [4,2];',
    '_packet set [4,-1];',
    '_packet set [4,0.5];',
    '_packet set [5,[]];',
    '_packet set [3,""];',
    '_distance=7;',
    '_alive=false;',
    '_medic setVariable ["ACE_isUnconscious",true];',
])
def test_stale_or_unusable_card_request_cannot_replace_patient_document(mutation):
    execute(setup() + mutation + r'''
        _packet call DD1380_card_fnc_receiveData;
        [isNil {_patient getVariable "DD1380_Document"},"rejected request wrote canonical document"] call _check;
        [(_patient getVariable ["DD1380_Revision",0])==0,"rejected request advanced revision"] call _check;
    ''')


@pytest.mark.parametrize('mutation', [
    '(_data select 0) set [1001,"true"];',
    '(_data select 2) set [1107,true];',
    '(_data select 2) set [99999,"unexpected"];',
    '(_data select 2) deleteAt 1107;',
    '_data set [3,[]];',
    '(_data select 4) set [1651,[123]];',
    'private _long="";for "_i" from 1 to 1025 do {_long=_long+"x";};(_data select 2) set [1107,_long];',
])
def test_invalid_form_payload_does_not_bypass_field_types_or_size_limits(mutation):
    execute(setup() + mutation + r'''
        _packet call DD1380_card_fnc_receiveData;
        [isNil {_patient getVariable "DD1380_Document"},"invalid form committed"] call _check;
        [count _events==1 && {!((_events select 0 select 1) select 4)},"invalid form was not explicitly rejected"] call _check;
    ''')


def test_changed_revision_rejects_second_editor_without_overwriting_first():
    execute(setup() + r'''
        (_data select 2) set [1107,"first provider"];
        _packet call DD1380_card_fnc_receiveData;
        _packet set [3,"second-request"];
        private _otherData=([_patient,false] call DD1380_card_fnc_getDocument) select 1;
        (_otherData select 2) set [1107,"second provider"];
        _packet set [5,_otherData];
        _packet call DD1380_card_fnc_receiveData;
        [((_patient getVariable "DD1380_Document") select 1 select 2 get 1107)=="first provider","second editor overwrote current revision"] call _check;
        [!((_events select 1 select 1) select 4),"revision conflict was silently accepted"] call _check;
    ''')


def test_nonowner_request_reroutes_with_original_epoch_and_bounded_hops():
    execute(setup() + r'''
        _patientLocal=false;_packet set [2,8];
        _packet call DD1380_card_fnc_receiveData;
        [count _events==1 && {(_events select 0 select 1 select 2)==8}
            && {(_events select 0 select 1 select 6)==1},"reroute refreshed the captured epoch or lost its hop bound"] call _check;
        _packet set [6,4];_packet call DD1380_card_fnc_receiveData;
        [count _events==1,"reroute exceeded four hops"] call _check;
    ''')


def test_display_harvest_uses_captured_patient_and_submits_once_on_final_close():
    execute(setup() + r'''
        DD1380_card_fnc_sendData={_submitted pushBack _this;};
        ace_medical_gui_target=missionNamespace;
        (_display getVariable "fixtureText") set [1107,"captured patient"];
        [_display] call DD1380_card_fnc_setData;
        [_display] call DD1380_card_fnc_setData;
        [count _submitted==1 && {(_submitted select 0 select 1 select 0) isEqualTo _patient},"form followed mutable medical target or saved twice"] call _check;
        [(_submitted select 0 select 1 select 5 select 2 get 1107)=="captured patient","form omitted entered text"] call _check;
    ''')


def test_page_flip_preserves_local_draft_and_native_unload_cannot_save_twice():
    execute(setup() + r'''
        DD1380_card_fnc_sendData={_submitted pushBack _this;};
        (_display getVariable "fixtureText") set [1107,"front draft"];
        [_display] call DD1380_card_fnc_flipPage;
        [count _submitted==0 && {_opened isEqualTo ["DD1380_Card2_dlg"]},"page flip submitted data or failed transition"] call _check;
        [((uiNamespace getVariable "DD1380_context") select 6 select 2 get 1107)=="front draft","page flip lost draft"] call _check;
        [_display] call DD1380_card_fnc_setData;
        [count _submitted==0,"late native unload saved the page twice"] call _check;
    ''')


def test_new_clinical_episode_discards_old_display_edits():
    execute(setup() + r'''
        DD1380_card_fnc_sendData={_submitted pushBack _this;};
        (_display getVariable "fixtureText") set [1107,"old life"];
        _patient setVariable ["ACME_clinicalEpoch",1];
        [_display] call DD1380_card_fnc_setData;
        [count _submitted==0,"previous episode document survived reset"] call _check;
    ''')


def test_document_reset_clears_canonical_legacy_and_receipts():
    execute(setup() + r'''
        (_data select 2) set [1107,"old life"];
        _packet call DD1380_card_fnc_receiveData;
        [_patient] call DD1380_card_fnc_resetDocument;
        private _doc=_patient getVariable "DD1380_Document";
        [_doc select 0==0 && {(_doc select 1 select 2 get 1107)==""},"new casualty retained previous document"] call _check;
        [(_patient getVariable "DD1380_Revision")==0 && {count (_patient getVariable "DD1380_Receipts")==0},"new casualty retained old document transaction state"] call _check;
    ''')


def test_ack_retires_only_matching_request_and_rejection_is_visible():
    execute(setup() + r'''
        _medic setVariable ["DD1380_Pending",[["old",_patient,0],["new",_patient,0]]];
        [_medic,_patient,0,"old",false,"Changed elsewhere"] call DD1380_card_fnc_saveAck;
        [_medic,_patient,0,"old",false,"Changed elsewhere"] call DD1380_card_fnc_saveAck;
        [(_medic getVariable "DD1380_Pending") isEqualTo [["new",_patient,0]],"old ACK cleared newer save"] call _check;
        [count _notifications==1,"rejection did not notify exactly once"] call _check;
    ''')


@pytest.mark.parametrize('page', [1, 2])
def test_both_authored_pages_call_handlers_without_boolean_chaining(page):
    ui = (CARD / 'ui/DD1380_dlg.hpp').read_text()
    assert f'onLoad = "[_this select 0, {page}] call DD1380_card_fnc_onLoad;";' in ui
    assert '&& _this call' not in ui
    assert 'setData &&' not in ui


def test_source_configs_keep_public_namespace_and_exact_font_assets():
    for folder, patch, prefix in [('card', 'DD1380_card', r'z\DD1380\addons\card'),
                                   ('card_main', 'DD1380_main', r'z\DD1380\addons\main')]:
        addon = ROOT / 'addons' / folder
        config = (addon / 'config.cpp').read_text()
        assert f'class {patch}' in config and f'ACME_BUILD_CONFIG("{folder}")' in config
        assert (addon / '$PBOPREFIX$').read_text().strip() == prefix
        assert not (addon / 'config.bin').exists()
        assert 'ignore_pboprefix = true' in (addon / 'addon.toml').read_text()
    fonts = (ROOT / 'addons/card_main/CfgFontFamilies.hpp').read_text()
    for size in re.findall(r'QPATHTOF\(fonts\\BiroScriptPlus\\BiroScriptPlus(\d+)\)', fonts):
        base = ROOT / 'addons/card_main/fonts/BiroScriptPlus'
        assert (base / f'BiroScriptPlus{size}.fxy').is_file()
        assert all((base / f'BiroScriptPlus{size}-{i:02}.paa').is_file() for i in range(1, 5))
    for asset in ('TCCC1.paa', 'TCCC2.paa'):
        assert (CARD / 'data/ui' / asset).is_file()


def test_dead_casualty_document_remains_openable_and_writable():
    execute(setup() + r'''
        _patientAlive=false;
        uiNamespace setVariable ["DD1380_openRequest",[_medic,_patient,0,"open1",objNull]];
        [_medic,_patient,0,"open1",[_patient,false] call DD1380_card_fnc_getDocument] call DD1380_card_fnc_openReady;
        [_opened isEqualTo ["DD1380_Card1_dlg"],"dead casualty card could not open"] call _check;
        (_data select 4) set [1651,"Recorded after death"];
        _packet call DD1380_card_fnc_receiveData;
        [(_patient getVariable "DD1380_Document" select 0)==1,"dead casualty document could not be saved"] call _check;
    ''')


def test_owner_commit_freezes_local_cba_packet_maps():
    execute(setup() + r'''
        (_data select 2) set [1107,"accepted entry"];
        _packet call DD1380_card_fnc_receiveData;
        (_data select 2) set [1107,"changed caller map"];
        [((_patient getVariable "DD1380_Document") select 1 select 2 get 1107)=="accepted entry","accepted document retained mutable request maps"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    'uiNamespace setVariable ["DD1380_openRequest",[_medic,_patient,0,"new-open",_sourceDisplayFixture]];',
    '_sourceDisplayFixture=uiNamespace;',
    'ace_medical_gui_target=missionNamespace;',
    '_patient setVariable ["ACME_clinicalEpoch",1];',
    '_medicLocal=false;',
    '_alive=false;',
])
def test_delayed_owner_snapshot_cannot_hijack_changed_patient_or_dialog(change):
    execute(setup() + r'''
        _sourceDisplayFixture=missionNamespace;ace_medical_gui_target=_patient;
        uiNamespace setVariable ["DD1380_openRequest",[_medic,_patient,0,"open1",_sourceDisplayFixture]];
        private _reply=[_medic,_patient,0,"open1",[_patient,false] call DD1380_card_fnc_getDocument];
    ''' + change + r'''
        _reply call DD1380_card_fnc_openReady;
        [count _opened==0 && {count _removed==0},"stale owner snapshot stole another menu's focus"] call _check;
    ''')


def test_owner_snapshot_opens_captured_document_and_retires_source_medical_pfh():
    execute(setup() + r'''
        _sourceDisplayFixture=missionNamespace;ace_medical_gui_target=_patient;
        uiNamespace setVariable ["DD1380_openRequest",[_medic,_patient,0,"open1",_sourceDisplayFixture]];
        (_data select 2) set [1107,"owner snapshot"];
        _patient setVariable ["DD1380_Text",createHashMapFromArray [[1107,"mixed mirror"]]];
        [_medic,_patient,0,"open1",[4,_data]] call DD1380_card_fnc_openReady;
        private _context=uiNamespace getVariable "DD1380_context";
        [_opened isEqualTo ["DD1380_Card1_dlg"] && {_removed isEqualTo ["medicalPFH"]},"opening did not retire stale medical renderer"] call _check;
        [_context select 4==4 && {(_context select 6 select 2 get 1107)=="owner snapshot"},"card reread mixed public mirrors instead of owner snapshot"] call _check;
    ''')


def test_save_retry_replays_owner_receipt_and_late_ack_does_not_duplicate_commit():
    execute(setup() + r'''
        private _drop=true;
        CBA_fnc_targetEvent={
            _events pushBack _this;
            if ((_this select 0)=="LNX_DD1380_Save") then {(_this select 1) call DD1380_card_fnc_receiveData;};
            if ((_this select 0)=="LNX_DD1380_SaveAck" && {!_drop}) then {(_this select 1) call DD1380_card_fnc_saveAck;};
        };
        [_medic,_packet] call DD1380_card_fnc_sendData;
        _drop=false;
        private _wait=_waits deleteAt 0;(_wait select 1) call (_wait select 0);
        _wait=_waits deleteAt 0;(_wait select 1) call (_wait select 0);
        [(_patient getVariable "DD1380_Revision")==1 && {count (_patient getVariable "DD1380_Receipts")==1},"retry committed a second document revision"] call _check;
        [count (_medic getVariable "DD1380_Pending")==0 && {count _events==4},"matching ACK did not retire retry"] call _check;
    ''')


def test_missing_ack_has_bounded_retries_and_reports_uncertain_confirmation():
    execute(setup() + r'''
        [_medic,_packet] call DD1380_card_fnc_sendData;
        for "_i" from 1 to 6 do {
            private _wait=_waits deleteAt 0;(_wait select 1) call (_wait select 0);
        };
        [count _events==6 && {count _waits==0} && {count _notifications==1},"missing ACK retry was unbounded or silent"] call _check;
        [count (_medic getVariable "DD1380_Pending")==0,"unconfirmed request retained retry state"] call _check;
    ''')


def test_ack_with_wrong_subject_cannot_retire_pending_save():
    execute(setup() + r'''
        _medic setVariable ["DD1380_Pending",[["request1",_patient,0]]];
        [_medic,missionNamespace,0,"request1",true,""] call DD1380_card_fnc_saveAck;
        [_medic,_patient,1,"request1",true,""] call DD1380_card_fnc_saveAck;
        [count (_medic getVariable "DD1380_Pending")==1,"wrong patient/epoch ACK retired an unrelated save"] call _check;
    ''')


def test_open_request_reads_one_captured_owner_snapshot_and_keeps_dead_subject():
    execute(setup() + r'''
        _patientAlive=false;
        [_medic,_patient,0,"open1"] call DD1380_card_fnc_requestDocument;
        [count _events==1 && {(_events select 0 select 0)=="LNX_DD1380_OpenReady"},"owner omitted snapshot reply"] call _check;
        private _reply=_events select 0 select 1;
        [_reply select 1 isEqualTo _patient && {_reply select 3=="open1"}
            && {count (_reply select 4)==2},"owner snapshot lost captured patient/request identity"] call _check;
    ''')


def test_initial_open_waits_for_snapshot_and_does_not_close_the_source_menu_early():
    execute(setup() + r'''
        _sourceDisplayFixture=missionNamespace;_dialog=true;
        [_medic,_patient] call DD1380_card_fnc_openCardLocal;
        [count _events==1 && {(_events select 0 select 0)=="LNX_DD1380_DocumentRequest"},"open skipped owner snapshot"] call _check;
        [count _opened==0 && {count _removed==0} && {_dialog},"open closed UI before snapshot admission"] call _check;
        [count (uiNamespace getVariable "DD1380_openRequest")==5,"pending request lost source display identity"] call _check;
    ''')


def test_owner_snapshot_request_reroutes_without_refreshing_episode():
    execute(setup() + r'''
        _patientLocal=false;
        [_medic,_patient,7,"open1"] call DD1380_card_fnc_requestDocument;
        [count _events==1 && {(_events select 0 select 1 select 2)==7}
            && {(_events select 0 select 1 select 4)==1},"snapshot reroute changed episode or omitted hop count"] call _check;
    ''')


@pytest.mark.parametrize('name,marker', [
    ('openCardLocal', 'B291:DD1380OwnerSnapshot'),
    ('setData', 'B291:DD1380CapturedDocument'),
])
def test_runtime_markers_are_executable_and_detect_a_standalone_override(name, marker):
    raw = (CARD / 'functions' / f'fnc_{name}.sqf').read_text()
    assert f'private _acmeReconcile = "{marker}";' in raw
    execute(setup() + f'''
        private _checked = DD1380_card_fnc_{name};
        [(toLower str _checked find toLower "{marker}") >= 0,
            "compiled DD1380 entry point lost its executable ownership marker"] call _check;
        _checked = {{true}};
        [(toLower str _checked find toLower "{marker}") < 0,
            "standalone DD1380 override falsely retained fork ownership"] call _check;
    ''')
