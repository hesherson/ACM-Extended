"""Execute in-place browser admission, projection and fallback; engine controls are boundaries."""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute, read
from test_historical_vial_execution import map_defaults


def function(name):
    text = read(name)
    for old,new in {
        'owner _patient':'_patientOwner','local _medic':'_medicLocal',
        'findDisplay 86000':'(call _findView)','findDisplay 86200':'objNull','findDisplay 84000':'objNull',
        'ctrlParent _control':'_view','_display displayCtrl 89301':'_browser',
        '_display displayCtrl 86004':'_list','_display displayCtrl (86500 + _slot)':'objNull',
        'fromJSON _text':'_decoded','lbSize _list':'count _nativeRows','lbCurSel _list':'_selected',
        'safeZoneW':'1.7777778','safeZoneH':'1','pixelW':'0.001','pixelH':'0.001',
    }.items(): text=text.replace(old,new)
    variable = {'reactMedicalPage':'_hello','reactMedicalTick':'_packet','reactMedicalMessage':'_reply'}.get(name,'_reply')
    text=re.sub(r'_(?:control|browser) ctrlWebBrowserAction \["ExecJS",format \[[^\n]+;', '_packets pushBack '+variable+';',text)
    text=re.sub(r'_browser ctrlShow ([^;]+);',r'_shown=\1;',text)
    text=re.sub(r'_browser ctrlEnable ([^;]+);',r'_enabled=\1;',text)
    text=text.replace('_browser ctrlSetPosition _rect;','_position=+_rect;').replace('_browser ctrlCommit 0;','')
    text=re.sub(r'\bfinite (_\w+)',r'(\1 isEqualType 0)',text)
    text=text.replace('!isNull objNull','false')
    return 'ACME_fnc_'+name+'={'+map_defaults(adapt(text))+'};'


def setup():
    return r'''
    private _view=missionNamespace;private _browser=uiNamespace;private _list=parsingNamespace;
    private _patientOwner=9;private _medicLocal=true;private _closed=false;
    private _findView={if (_closed) then {objNull} else {_view}};
    private _packets=[];private _selections=[];private _shown=false;private _enabled=false;private _position=[];
    private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
        if (_key in _map && {!isNil {_map get _key}}) then {_map get _key} else {_default}};
    ACME_fnc_patientInteractionDistance={_distance};
    ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",4]};
    ACME_fnc_clinicalObjectRef={["1:2","mission-a","patient-a"]};
    ACME_fnc_transfusionCardSelect={_selections pushBack _this;};
    ACM_circulation_TransfusionMenu_Medic=_medic;ACM_circulation_TransfusionMenu_Target=_patient;
    ACME_fnc_transfusionUiSet={params ["_c","_property","_value"];switch (_property) do {
        case "show": {_shown=_value};case "enable": {_enabled=_value};case "position": {_position=+_value};};true};
    private _context=[_medic,_patient,"",[],4,2,3,5,9];
    _patient setVariable ["ACME_equipmentKitEpoch",2];
    _medic setVariable ["ACME_equipmentKitEpoch",3];
    _medic setVariable ["ACME_providerLocalityEpoch",5];
    _view setVariable ["ACME_reactContext",_context];
    _view setVariable ["ACME_reactSession","ui:7:1"];
    _view setVariable ["ACME_reactReady",true];
    _view setVariable ["ACME_reactActive",true];
    _view setVariable ["ACME_reactRows",createHashMapFromArray [["row:1:0",["active","leftarm",true,1,"uid-a"]]]];
    _view setVariable ["ACME_txCardLayout",createHashMapFromArray [[86004,[[0.1,0.2,0.212,0.210],2,0.1,0,true]]]];
    private _decoded=createHashMapFromArray [["version",2],["session","ui:7:1"],
        ["sequence",2],["operation","select"],["route",["row:1:0"]]];
    ''' + ''.join(function(n) for n in ('reactMedicalValid','reactMedicalFallback','reactMedicalMessage'))


@pytest.mark.parametrize('change',[
    '_patient setVariable ["ACME_clinicalEpoch",5];','_patient setVariable ["ACME_equipmentKitEpoch",3];',
    '_medic setVariable ["ACME_equipmentKitEpoch",4];','_medic setVariable ["ACME_providerLocalityEpoch",6];',
    '_patientOwner=10;','_distance=4;','_alive=false;','_medicLocal=false;',
    '_medic setVariable ["ACE_isUnconscious",true];','_patient setVariable ["ACME_persistenceFrozen",true];',
    '_medic setVariable ["ACME_persistenceFrozen",true];','ACE_player=objNull;',
    '_view setVariable ["ACME_txActionMenu","bag"];',
    'ACM_circulation_TransfusionMenu_Target=missionNamespace;',
    'ACM_circulation_TransfusionMenu_Medic=missionNamespace;',
])
def test_changed_context_cannot_select(change):
    execute(setup()+change+r'''
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [count _selections==0 && {count _waits==0},"invalid context selected or navigated"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_decoded set ["session","old"];','_decoded set ["version",1];','_decoded set ["sequence",0];',
    '_decoded set ["sequence",1.5];','_decoded set ["sequence",1000001];',
    '_decoded set ["operation","manage"];','_decoded set ["operation","native"];',
    '_decoded set ["route",[]];','_decoded set ["route",["row:old:0"]];','_decoded set ["route",[1]];',
    '_decoded set ["extra","unexpected"];','_decoded=[];','_decoded=nil;',
    '_view setVariable ["ACME_reactReady",false];','_view setVariable ["ACME_reactRequestSequence",2];',
])
def test_invalid_or_old_command_cannot_select(change):
    execute(setup()+change+r'''
        [[_browser,false,"packet"] call ACME_fnc_reactMedicalMessage,"browser dialog unhandled"] call _check;
        [count _selections==0 && {count _waits==0},"invalid token selected or navigated"] call _check;
    ''')


def test_select_uses_captured_identity_once_even_for_dead_casualty():
    execute(setup()+r'''
        _patientAlive=false;
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [count _selections==1,"selection duplicated or dead casualty blocked"] call _check;
        [(_browser getVariable "ACME_txIdentity") isEqualTo ["active","leftarm",true,1,"uid-a"],"token mapped to another physical bag"] call _check;
        [(_browser getVariable "ACME_txPatient") isEqualTo _patient,"selection lost captured casualty"] call _check;
        [count _packets==1 && {((_packets select 0) get "request")==2},"missing exact acknowledgment"] call _check;
        [count _waits==0 && {!_closed},"selection navigated/reopened the menu"] call _check;
    ''')


@pytest.mark.parametrize('operation,argument',[('wheel','1'),('wheel','-1'),('key','200'),('key','208'),('key','201'),('key','209'),('key','199'),('key','207')])
def test_supported_input_delegates_original_handler(operation,argument):
    execute(setup()+f'''
        _decoded set ["operation","{operation}"];_decoded set ["route",[{argument}]];
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [count _selections==1 && {{((_selections select 0) select 1)=="{operation}"}},"native input not delegated"] call _check;
    ''')


def test_unknown_row_acknowledges_without_selecting_or_retrying():
    execute(setup()+r'''
        _decoded set ["route",["old-token"]];
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [count _selections==0 && {count _packets==1},"stale row selected or stranded pending input"] call _check;
    ''')


def test_ready_does_not_act_and_requires_empty_payload():
    execute(setup()+r'''
        _view setVariable ["ACME_reactReady",false];_decoded set ["operation","ready"];
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [!(_view getVariable "ACME_reactReady"),"ready accepted a row payload"] call _check;
        _decoded set ["route",[]];[_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [_view getVariable "ACME_reactReady", "ready handshake failed"] call _check;
        [count _selections==0,"handshake selected a card"] call _check;
    ''')


def snapshot_setup():
    return setup()+''.join(function(n) for n in ('transfusionCardWindow','transfusionGraduations','reactMedicalSnapshot'))+r'''
        private _nativeRows=[["active","leftarm",true,1,"uid-a"],["line","leftarm",true,1,"line-b"],["active","leftarm",true,1,"uid-c"]];
        private _selected=0;
        ACME_fnc_transfusionCardIdentity={_nativeRows select (_this select 1)};
        ACME_fnc_transfusionCardData={["Saline 750 mL","Primary","Running","LW Quantum / Inline",[1,1,1,1],"bag.paa","",0.75,1000]};
    '''


def test_snapshot_uses_native_two_card_window_and_graduations():
    execute(snapshot_setup()+r'''
        private _state=[_view] call ACME_fnc_reactMedicalSnapshot;
        private _cards=_state get "cards";
        [count _cards==2 && {_state get "canNext"},"native viewport/overflow changed"] call _check;
        [((_cards select 0) get "name")=="Saline 750 mL" && {(_cards select 0) get "selected"},"native card presentation/selection lost"] call _check;
        [count ((_cards select 0) get "marks")==11,"native graduation model lost"] call _check;
        [count _state==5 && {count (_cards select 0)==12},"raw patient state leaked"] call _check;
    ''')


def test_rebinding_native_window_retires_old_row_tokens():
    execute(snapshot_setup()+r'''
        private _first=[_view] call ACME_fnc_reactMedicalSnapshot;
        private _token=((_first get "cards") select 0) get "token";
        _nativeRows set [0,["active","leftarm",true,1,"replacement-uid"]];
        private _second=[_view] call ACME_fnc_reactMedicalSnapshot;
        [_token!=(((_second get "cards") select 0) get "token"),"replaced bag inherited old token"] call _check;
        [!(_token in (_view getVariable "ACME_reactRows")),"retired row remains selectable"] call _check;
    ''')


def test_empty_access_cannot_materialize_a_card():
    execute(snapshot_setup()+r'''
        _nativeRows=[];private _state=[_view] call ACME_fnc_reactMedicalSnapshot;
        [count (_state get "cards")==0 && {!(_state get "canNext")},"empty access invented a fluid"] call _check;
    ''')


def test_reloaded_page_gets_fresh_session_and_no_old_row_map():
    execute(setup()+function('reactMedicalPage')+r'''
        [_browser] call ACME_fnc_reactMedicalPage;private _first=_view getVariable "ACME_reactSession";
        [_browser] call ACME_fnc_reactMedicalPage;
        [_first!=(_view getVariable "ACME_reactSession") && {count _packets==2},"reload reused session"] call _check;
        [!(_view getVariable "ACME_reactReady") && {count (_view getVariable "ACME_reactRows")==0},"reload retained actionable rows"] call _check;
    ''')


def tick_setup():
    return setup()+function('reactMedicalTick')+r'''
        ACME_fnc_reactMedicalSnapshot={createHashMapFromArray [["visible","state"]]};
    '''


def test_browser_uses_original_pane_geometry_and_bounded_heartbeat():
    execute(tick_setup()+r'''
        [_view] call ACME_fnc_reactMedicalTick;
        [count _position==4 && {abs ((_position select 1)-0.2)<0.0001} && {abs ((_position select 3)-0.210)<0.0001},"browser escaped existing panel"] call _check;
        _nowTime=10.5;[_view] call ACME_fnc_reactMedicalTick;
        [count _packets==1,"steady state sent every refresh"] call _check;
        _nowTime=12;[_view] call ACME_fnc_reactMedicalTick;
        [count _packets==2,"heartbeat missing"] call _check;
    ''')


def test_timeout_restores_native_in_same_display_without_scheduling():
    execute(tick_setup()+r'''
        _view setVariable ["ACME_reactReady",false];_view setVariable ["ACME_reactDeadline",9];
        [_view] call ACME_fnc_reactMedicalTick;
        [!(_view getVariable "ACME_reactActive") && {_view getVariable "ACME_reactFailed"},"failed browser retained pane"] call _check;
        [!_shown && {!_enabled} && {!_closed} && {count _waits==0},"fallback navigated or trapped input"] call _check;
    ''')


def test_close_retires_only_its_context_without_adding_a_worker():
    execute(setup()+function('reactMedicalClose')+r'''
        [_view] call ACME_fnc_reactMedicalClose;[_view] call ACME_fnc_reactMedicalClose;
        [(_view getVariable "ACME_reactContext") isEqualTo [] && {(_view getVariable "ACME_reactSession")==""},"closed view retained authority"] call _check;
        [count _handlers==0 && {count _waits==0},"React added a display worker"] call _check;
    ''')
