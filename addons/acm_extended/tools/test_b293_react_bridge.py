"""Execute the new local browser admission and deferred handoff in SQF-VM.

Native displays, JSON decoding, time, proximity and scheduling are explicit
boundaries. No browser/runtime or real multiplayer transport is certified here.
"""
import re

import pytest

from test_menu_death_lifecycle import adapt, execute, read
from test_historical_vial_execution import map_defaults


def function(name):
    text = read(name)
    for old, new in {
        'owner _patient': '_patientOwner', 'local _medic': '_medicLocal',
        'findDisplay 89300': '(call _findView)', 'ctrlParent _control': '_view',
        '_display displayCtrl 89301': '_browser', 'fromJSON _text': '_decoded',
        '_display closeDisplay 0;': '_closed=true;',
    }.items():
        text = text.replace(old, new)
    if name == 'reactMedicalPage':
        text = re.sub(r'_control ctrlWebBrowserAction \["ExecJS",format \[[^\n]+;', '_helloPackets pushBack _hello;', text)
    elif name == 'reactMedicalTick':
        text = re.sub(r'\(_display displayCtrl 89301\) ctrlWebBrowserAction \["ExecJS",format \[[^\n]+;', '_sentPackets pushBack _packet;', text)
        text = text.replace('(_display displayCtrl 89301) ctrlWebBrowserAction', '_browser ctrlWebBrowserAction')
        text = re.sub(r'\(?_browser\)? ctrlWebBrowserAction \["ExecJS",format \[[^\n]+;', '_sentPackets pushBack _packet;', text)
    else:
        text = re.sub(r'_control ctrlWebBrowserAction \["ExecJS",format \[[^\n]+;', '_rejections=_rejections+1;', text)
    text = re.sub(r'\bfinite (_\w+)', r'(\1 isEqualType 0)', text)
    return 'ACME_fnc_' + name + '={' + map_defaults(adapt(text)) + '};'


def setup():
    return r'''
        private _view=missionNamespace;private _browser=uiNamespace;
        private _patientOwner=9;private _medicLocal=true;private _closed=false;
        private _findView={if (_closed) then {objNull} else {_view}};
        private _access=true;private _handoffs=[];
        private _rejections=0;
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map && {!isNil {_map get _key}}) then {_map get _key} else {_default}};
        ACME_fnc_patientInteractionDistance={_distance};
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",4]};
        ACME_fnc_transfusionAccessValid={_access};
        ACM_circulation_fnc_openTransfusionMenu={_handoffs pushBack _this;};
        private _context=[_medic,_patient,"leftarm",[],4,2,3,5,9];
        _patient setVariable ["ACME_equipmentKitEpoch",2];
        _medic setVariable ["ACME_equipmentKitEpoch",3];
        _medic setVariable ["ACME_providerLocalityEpoch",5];
        _view setVariable ["ACME_reactContext",_context];
        _view setVariable ["ACME_reactSerial",7];
        ACME_reactSerial=7;
        _view setVariable ["ACME_reactSession","ui:7:1"];
        _view setVariable ["ACME_reactReady",true];
        private _decoded=createHashMapFromArray [["version",1],["session","ui:7:1"],
            ["sequence",2],["operation","manage"],["route",["leftarm",true,1]]];
    ''' + ''.join(function(n) for n in ('reactMedicalValid','reactMedicalFallback','reactMedicalMessage'))


@pytest.mark.parametrize('change', [
    '_patient setVariable ["ACME_clinicalEpoch",5];',
    '_patient setVariable ["ACME_equipmentKitEpoch",3];',
    '_medic setVariable ["ACME_equipmentKitEpoch",4];',
    '_medic setVariable ["ACME_providerLocalityEpoch",6];',
    '_patientOwner=10;', '_distance=4;', '_alive=false;', '_medicLocal=false;',
    '_medic setVariable ["ACE_isUnconscious",true];',
    '_patient setVariable ["ACME_persistenceFrozen",true];',
    '_medic setVariable ["ACME_persistenceFrozen",true];',
    'ACE_player=objNull;',
])
def test_changed_patient_provider_or_owner_rejects_browser_requests(change):
    execute(setup() + change + r'''
        [[_browser,false,"packet"] call ACME_fnc_reactMedicalMessage,"rejection blocked JSDialog"] call _check;
        [!_closed && {count _waits==0},"invalid context navigated or scheduled a treatment"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_decoded set ["session","old"];', '_decoded set ["version",2];',
    '_decoded set ["sequence",0];', '_decoded set ["sequence",1.5];',
    '_decoded set ["sequence",1000001];', '_decoded set ["operation","compile"];',
    '_decoded set ["route",["bad",true,0]];', '_decoded set ["route",["leftarm",false,2]];',
    '_decoded set ["route",["leftarm",1,0]];', '_decoded set ["route",[]];',
    '_decoded set ["extra","unexpected"];', '_decoded=[];', '_decoded=nil;',
    '_access=false;', '_view setVariable ["ACME_reactReady",false];',
    '_view setVariable ["ACME_reactRequestSequence",2];',
])
def test_invalid_or_duplicate_request_does_not_navigate(change):
    execute(setup() + change + r'''
        [[_browser,false,"packet"] call ACME_fnc_reactMedicalMessage,"invalid request blocked Chromium"] call _check;
        [!_closed && {count _waits==0},"bad/replayed request reached native UI"] call _check;
    ''')


def test_one_captured_access_handoff_bypasses_react_and_never_replays():
    execute(setup() + r'''
        _patientAlive=false;
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [_closed && {count _waits==1},"dead casualty was blocked or duplicate navigation scheduled"] call _check;
        private _job=_waits select 0;(_job select 1) call (_job select 0);
        [count _handoffs==1 && {(_handoffs select 0) isEqualTo [_medic,_patient,"leftarm",[true,1],true]},"handoff selected another access or reentered React"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_patientOwner=10;', '_patient setVariable ["ACME_clinicalEpoch",5];',
    'ACME_reactSerial=8;', '_dialog=true;', '_access=false;',
])
def test_deferred_handoff_rechecks_identity_access_and_newer_ui(change):
    execute(setup() + r'''
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
    ''' + change + r'''
        private _job=_waits select 0;(_job select 1) call (_job select 0);
        [count _handoffs==0,"delayed handoff affected newer patient or dialog"] call _check;
    ''')


def test_ready_handshake_cannot_navigate_or_accept_route_payload():
    execute(setup() + r'''
        _view setVariable ["ACME_reactReady",false];
        _decoded set ["operation","ready"];_decoded set ["route",[]];
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [_view getVariable ["ACME_reactReady",false],"ready handshake did not activate session"] call _check;
        [!_closed && {count _waits==0},"handshake executed native UI"] call _check;
    ''')


def snapshot_setup():
    return setup() + function('transfusionGraduations') + function('reactMedicalSnapshot') + r'''
        private _presentationCalls=[];
        ACME_fnc_clinicalObjectRef={["1:2","mission-a","patient-a"]};
        ACME_fnc_transfusionAccessValid={params ["_p","_part","_iv","_site"];
            _part=="leftarm" && {_iv} && {_site==1}};
        ACME_fnc_transfusionBagPresentation={params ["_p","_part","_bag"];
            _presentationCalls pushBack _bag;
            ["Saline 750 mL",[1,1,1,1],"LW Quantum / Inline","Primary",true]};
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[
            ["Saline",750,1,1,true,-1,1000,-1,"uid-a"],
            ["Blood",250,1,2,true,-1,250,-1,"different-site"]
        ]]]];
        _patient setVariable ["ACME_infusion_BagMedications",[["hidden-medication-remainder"]]];
    '''


def test_snapshot_exports_only_established_access_and_visible_bag_information():
    execute(snapshot_setup() + r'''
        private _state=[_context] call ACME_fnc_reactMedicalSnapshot;
        private _rows=_state get "accesses";
        [count _rows==1,"projection invented access or omitted the actual route"] call _check;
        private _row=_rows select 0;private _bags=_row get "bags";
        [count _bags==1 && {count _presentationCalls==1},"another site's bag leaked into selected access"] call _check;
        private _bag=_bags select 0;
        [(_bag get "remainingMl")==750 && {(_bag get "capacityMl")==1000},"visible volume changed"] call _check;
        [count _bag==7 && {count (_state get "observations")==0},"unmeasured physiology or raw medication state exported"] call _check;
        [count (_bag get "marks")==11 && {((_bag get "marks") select 1) isEqualTo [0.1,100]},"native bag graduations were lost"] call _check;
        [(_state get "view")=="transfusion" && {count ((_state get "patient") get "ref")==3},"shared view/patient identity missing"] call _check;
    ''')


def test_empty_established_access_is_retained_without_inventing_a_bag():
    execute(snapshot_setup() + r'''
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMap];
        private _state=[_context] call ACME_fnc_reactMedicalSnapshot;
        [count (_state get "accesses")==1,"empty real access disappeared"] call _check;
        [count (((_state get "accesses") select 0) get "bags")==0,"snapshot materialized a phantom bag"] call _check;
    ''')


def test_snapshot_has_a_bounded_bag_projection_and_reports_overflow():
    execute(snapshot_setup() + r'''
        private _bags=[];
        for "_i" from 1 to 140 do {_bags pushBack ["Saline",500,1,1,true,-1,1000,-1,str _i];};
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",_bags]]];
        private _state=[_context] call ACME_fnc_reactMedicalSnapshot;
        [count (((_state get "accesses") select 0) get "bags")==128 && {_state get "truncated"},"projection exceeded its memory/work budget or hid overflow"] call _check;
    ''')


def test_reloaded_page_gets_a_new_session_and_retires_the_old_request_sequence():
    execute(setup() + function('reactMedicalPage') + r'''
        private _helloPackets=[];
        [_browser] call ACME_fnc_reactMedicalPage;
        private _first=_view getVariable "ACME_reactSession";
        _view setVariable ["ACME_reactReady",true];
        _view setVariable ["ACME_reactRequestSequence",99];
        [_browser] call ACME_fnc_reactMedicalPage;
        [_first!=(_view getVariable "ACME_reactSession") && {count _helloPackets==2},"reload reused former session"] call _check;
        [!(_view getVariable "ACME_reactReady") && {(_view getVariable "ACME_reactRequestSequence")==0},"reload inherited ready/command state"] call _check;
        [_browser,false,"late former request"] call ACME_fnc_reactMedicalMessage;
        [!_closed && {count _waits==0},"old page navigated after reload"] call _check;
    ''')


def test_steady_state_is_suppressed_until_the_bounded_freshness_heartbeat():
    execute(setup() + function('reactMedicalTick') + r'''
        private _sentPackets=[];
        ACME_fnc_reactMedicalSnapshot={createHashMapFromArray [["visible","state"]]};
        [[_view],0] call ACME_fnc_reactMedicalTick;
        _nowTime=10.5;[[_view],0] call ACME_fnc_reactMedicalTick;
        [count _sentPackets==1,"steady presentation sent every poll"] call _check;
        _nowTime=12;[[_view],0] call ACME_fnc_reactMedicalTick;
        [count _sentPackets==2 && {((_sentPackets select 1) get "sequence")==2},"bounded heartbeat/sequence was lost"] call _check;
    ''')


def test_browser_startup_timeout_hands_off_once_to_the_native_menu():
    execute(setup() + function('reactMedicalTick') + r'''
        _view setVariable ["ACME_reactReady",false];
        _view setVariable ["ACME_reactDeadline",9];
        [[_view],0] call ACME_fnc_reactMedicalTick;
        [_closed && {count _waits==1},"blocked browser stranded the menu"] call _check;
        private _job=_waits select 0;(_job select 1) call (_job select 0);
        [count _handoffs==1 && {(_handoffs select 0 select 4)},"timeout reentered browser instead of native"] call _check;
    ''')


def test_close_retires_its_worker_and_captured_context_once():
    execute(setup() + function('reactMedicalClose') + r'''
        private _stopped=[];
        CBA_fnc_removePerFrameHandler={_stopped pushBack (_this select 0);};
        _view setVariable ["ACME_reactPFH",42];
        [_view] call ACME_fnc_reactMedicalClose;[_view] call ACME_fnc_reactMedicalClose;
        [_stopped isEqualTo [42],"display worker survived or was removed twice"] call _check;
        [(_view getVariable "ACME_reactContext") isEqualTo [] && {(_view getVariable "ACME_reactSession")==""},"closed view retained authority"] call _check;
    ''')
