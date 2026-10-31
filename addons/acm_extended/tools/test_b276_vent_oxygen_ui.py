"""Execute ventilator oxygen edits without blocking unrelated controls.

The attached-source state, provider request and checked-out handlers run in
SQF-VM. Namespace units, owner transport and native control drawing are explicit
engine boundaries; this suite does not certify native Arma rendering or input.
"""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read


def function(name):
    text = read(name).replace("hasInterface", "false")
    text = text.replace("serverTime", "_nowTime")
    text = re.sub(r'objNull\s*,\s*\[objNull\]', 'objNull', text)
    text = re.sub(r'playSound "[^"]+";', "", text)
    text = text.replace("disableSerialization;", "")
    if name == "ventPanelOxygenRefresh":
        text = text.replace("ctrlText _supply", '(_supply get "text")')
        text = text.replace("(_dlg displayCtrl 87756)", "_backCtl")
        for command, key in (("ctrlSetText", "text"), ("ctrlEnable", "enabled"),
                             ("ctrlSetTextColor", "textColor"),
                             ("ctrlSetBackgroundColor", "background")):
            text = re.sub(r'(\w+)\s+' + command + r'\s+([^;]+);',
                          rf'\1 set ["{key}", \2];', text)
    adapted = adapt(text)
    if name == "ventOxygenGate":
        # The shared fixture's mission-handler return adapter does not apply
        # to the native warning display's KeyDown callback.
        adapted = adapted.replace('    false\n}] select 1);', '    false\n}];')
    return "ACME_fnc_" + name + "={" + adapted + "};"


def fixture():
    return r'''
        private _requests=[];
        private _writes=[];
        private _repaints=0;
        private _supplyPicked=missionNamespace;
        ACME_fnc_clinicalEpoch={1};
        ACME_fnc_ownerDispatch={_requests pushBack _this;};
        ACME_fnc_ventOxygenSource={_supplyPicked};
        ACME_fnc_ventPanelListRefresh={};
        ACME_fnc_ventPanelOxygenRefresh={_repaints=_repaints+1;};
        ACME_fnc_ventPanelShowScreen={uiNamespace setVariable ["ACME_vent_screen",_this select 0];};
        ACME_fnc_ventPanelNavClick={uiNamespace setVariable ["ACME_vent_screen","params"];};
        ACME_fnc_ventPanelSetValue={_writes pushBack _this;};
        ACME_fnc_ventPanelRefresh={};
        ACME_fnc_ventPanelLiveRefresh={};
        ACME_fnc_ventLogbookAdd={};
        ACME_fnc_ventFormatIE={str (_this select 0)};
        ACME_fnc_ventColor={_this select 0};
        uiNamespace setVariable ["ACME_vent_target",_patient];
        uiNamespace setVariable ["ACME_vent_powered",true];
        uiNamespace setVariable ["ACME_vent_flipped",false];
        uiNamespace setVariable ["ACME_vent_screen","params"];
        uiNamespace setVariable ["ACME_vent_paramsPage",0];
        uiNamespace setVariable ["ACME_vent_paramsNav",[false,false,false,false,false]];
        uiNamespace setVariable ["ACME_vent_listCount",5];
        uiNamespace setVariable ["ACME_vent_selIdx",0];
        uiNamespace setVariable ["ACME_vent_editingParam",-1];
        uiNamespace setVariable ["ACME_vent_editingFio2",false];
        uiNamespace setVariable ["ACME_vent_fio2",40];
        _patient setVariable ["ACME_vent_fio2",40];
        _patient setVariable ["ACME_vent_o2Session","oxygen-session"];
        _patient setVariable ["ACME_vent_o2Source",missionNamespace];
        _patient setVariable ["ACME_vent_o2Status","READY"];
        _patient setVariable ["ACME_vent_o2VerifiedUntil",100];
        _patient setVariable ["ACME_vent_o2ReserveUnits",10];
        _patient setVariable ["ACME_vent_o2Credit",0];
        _patient setVariable ["ACME_vent_o2Epoch",1];
        _patient setVariable ["ACME_vent_o2Custody","vent1"];
        _patient setVariable ["ACME_vent_custodyId","vent1"];
        missionNamespace setVariable ["ACME_vent_simpleMode",false];
        missionNamespace setVariable ["ACME_vent_scrollCooldown",0];
    ''' + "".join(function(name) for name in (
        "ventRecoveryNear", "ventOxygenState", "ventOxygenRequest", "ventPanelKnob",
        "ventPanelListClick", "ventPanelActivateSel", "ventPanelLiveEdit",
    ))


@pytest.mark.parametrize("simple", [False, True])
@pytest.mark.parametrize("available", [False, True])
def test_params_oxygen_row_reaches_supply_page_without_gating_other_controls(simple, available):
    execute(fixture() + f'''
        missionNamespace setVariable ["ACME_vent_simpleMode",{str(simple).lower()}];
        _patient setVariable ["ACME_vent_o2Status","{ 'READY' if available else 'EMPTY' }"];
        [0] call ACME_fnc_ventPanelListClick;
        [uiNamespace getVariable "ACME_vent_screen"=="o2","oxygen row did not reach supply page"] call _check;
        [uiNamespace getVariable "ACME_vent_editingParam"==-1,"oxygen row left stale in-place edit"] call _check;
        [count _requests==0,"opening supply page changed patient settings"] call _check;
    ''')


@pytest.mark.parametrize("row", [1,2,3,4])
def test_connected_oxygen_unlocks_only_fio2_in_simple_delivery(row):
    execute(fixture() + f'''
        missionNamespace setVariable ["ACME_vent_simpleMode",true];
        [{row}] call ACME_fnc_ventPanelListClick;
        [uiNamespace getVariable "ACME_vent_editingParam"==-1,"oxygen unlocked another Simple setting"] call _check;
        [uiNamespace getVariable "ACME_vent_screen"=="params","oxygen changed another Simple setting's route"] call _check;
        [0] call ACME_fnc_ventPanelListClick;
        [uiNamespace getVariable "ACME_vent_screen"=="o2","Simple oxygen control remained automatic"] call _check;
    ''')


@pytest.mark.parametrize("cause", ["missing", "empty", "unavailable", "checking", "expired", "epoch", "custody", "distance"])
@pytest.mark.parametrize("screen", ["params", "o2"])
def test_source_loss_blocks_only_fio2_even_with_stale_edit_flags(cause, screen):
    change = {
        "missing": '_patient setVariable ["ACME_vent_o2Session",""];',
        "empty": '_patient setVariable ["ACME_vent_o2Status","EMPTY"];',
        "unavailable": '_patient setVariable ["ACME_vent_o2Status","UNAVAILABLE"];',
        "checking": '_patient setVariable ["ACME_vent_o2Status","VERIFYING"];',
        "expired": '_patient setVariable ["ACME_vent_o2VerifiedUntil",1];',
        "epoch": '_patient setVariable ["ACME_vent_o2Epoch",2];',
        "custody": '_patient setVariable ["ACME_vent_custodyId","replacement"];',
        "distance": '_distance=6;',
    }[cause]
    execute(fixture() + change + f'''
        uiNamespace setVariable ["ACME_vent_screen","{screen}"];
        uiNamespace setVariable ["ACME_vent_editingParam",0];
        uiNamespace setVariable ["ACME_vent_editingFio2",true];
        [1] call ACME_fnc_ventPanelKnob;
        [count _requests==0,"stale oxygen editor sent an unauthorized FiO2 request"] call _check;
        [_patient getVariable "ACME_vent_fio2"==40,"source loss destroyed saved FiO2 choice"] call _check;
    ''' + (r'''
        [uiNamespace getVariable "ACME_vent_editingParam"==-1,"params oxygen edit stayed active"] call _check;
    ''' if screen == "params" else r'''
        [!(uiNamespace getVariable "ACME_vent_editingFio2"),"oxygen-page edit stayed active"] call _check;
    '''))


@pytest.mark.parametrize("simple", [False, True])
@pytest.mark.parametrize("initial,direction,want", [(40,1,41),(40,-1,39),(95,1,95),(21,-1,21)])
def test_oxygen_dial_uses_owner_request_and_preserves_sparrow_range(simple, initial, direction, want):
    execute(fixture() + f'''
        missionNamespace setVariable ["ACME_vent_simpleMode",{str(simple).lower()}];
        uiNamespace setVariable ["ACME_vent_screen","o2"];
        _patient setVariable ["ACME_vent_fio2",{initial}];
        [] call ACME_fnc_ventPanelActivateSel;
        [uiNamespace getVariable "ACME_vent_editingFio2","usable cylinder did not unlock oxygen value"] call _check;
        [{direction}] call ACME_fnc_ventPanelKnob;
        [count _requests==1,"FiO2 dial bypassed owner transport"] call _check;
        private _args=(_requests select 0) select 2;
        [_args select 1=="fio2" && {{_args select 3=={want}}},"FiO2 request wrong value/command"] call _check;
        [_args select 2 isEqualTo ACE_player,"FiO2 request lost provider identity"] call _check;
        [_patient getVariable "ACME_vent_fio2"=={initial},"UI directly mutated patient FiO2"] call _check;
        [uiNamespace getVariable "ACME_vent_fio2"=={want},"local oxygen dial did not repaint requested value"] call _check;
    ''')


@pytest.mark.parametrize("row,key,initial", [(1,"ie",2),(2,"peep",5),(3,"psup",10),(4,"trigSensCmH2O",-2)])
def test_no_oxygen_does_not_block_other_advanced_parameter_editors(row, key, initial):
    execute(fixture() + f'''
        _patient setVariable ["ACME_vent_o2Status","EMPTY"];
        _patient setVariable ["ACME_vent_{key}",{initial}];
        [{row}] call ACME_fnc_ventPanelListClick;
        [uiNamespace getVariable "ACME_vent_editingParam"=={row},"oxygen blocked another editor"] call _check;
        [1] call ACME_fnc_ventPanelKnob;
        [_patient getVariable "ACME_vent_{key}"!={initial},"oxygen blocked another parameter writer"] call _check;
        [count _requests==0,"unrelated parameter became an oxygen command"] call _check;
    ''')


@pytest.mark.parametrize("slot,mode,key,initial", [(0,"SIMV VC PS","bpm",12),(1,"SIMV VC PS","vt",500),(1,"SIMV PC","pinsp",20)])
def test_no_tank_keeps_rate_volume_and_pressure_control_live(slot, mode, key, initial):
    execute(fixture() + f'''
        _patient setVariable ["ACME_vent_o2Status","EMPTY"];
        _patient setVariable ["ACME_vent_mode","{mode}"];
        _patient setVariable ["ACME_vent_{key}",{initial}];
        uiNamespace setVariable ["ACME_vent_{key}",{initial}];
        uiNamespace setVariable ["ACME_vent_selIdx",{slot}];
        [1] call ACME_fnc_ventPanelLiveEdit;
        [_patient getVariable "ACME_vent_{key}"!={initial},"no tank blocked RR/VT/PInsp"] call _check;
    ''')


@pytest.mark.parametrize("attached,command", [(False,"attach"),(True,"detach")])
@pytest.mark.parametrize("simple", [False, True])
def test_source_action_and_back_remain_operable_without_usable_oxygen(attached, command, simple):
    execute(fixture() + f'''
        missionNamespace setVariable ["ACME_vent_simpleMode",{str(simple).lower()}];
        _patient setVariable ["ACME_vent_o2Status","EMPTY"];
        _patient setVariable ["ACME_vent_o2Session","{'oxygen-session' if attached else ''}"];
        uiNamespace setVariable ["ACME_vent_screen","o2"];
        uiNamespace setVariable ["ACME_vent_selIdx",1];
        [] call ACME_fnc_ventPanelActivateSel;
        [count _requests==1 && {{((_requests select 0) select 2) select 1=="{command}"}},"source action did not reach owner"] call _check;
        _nowTime=_nowTime+1;
        uiNamespace setVariable ["ACME_vent_selIdx",2];
        [] call ACME_fnc_ventPanelActivateSel;
        [uiNamespace getVariable "ACME_vent_screen"=="params","source page BACK was blocked"] call _check;
    ''')


@pytest.mark.parametrize("usable,editing,want", [(False,False,"21%"),(False,True,"21%"),(True,False,"40%"),(True,True,"65%")])
def test_oxygen_painter_shows_actual_room_air_on_loss_and_preserves_stored_choice(usable, editing, want):
    execute(fixture() + function("ventPanelOxygenRefresh") + f'''
        uiNamespace setVariable ["ACME_vent_dlg",missionNamespace];
        uiNamespace setVariable ["ACME_vent_screen","o2"];
        uiNamespace setVariable ["ACME_vent_editingFio2",{str(editing).lower()}];
        uiNamespace setVariable ["ACME_vent_fio2",65];
        _patient setVariable ["ACME_vent_o2Status","{'READY' if usable else 'EMPTY'}"];
        private _valueCtl=createHashMap;
        private _supplyCtl=createHashMapFromArray [["text",""]];
        private _actionCtl=createHashMap;
        private _backCtl=createHashMap;
        uiNamespace setVariable ["ACME_vent_o2ValCtrl",_valueCtl];
        uiNamespace setVariable ["ACME_vent_o2SupplyCtrl",_supplyCtl];
        uiNamespace setVariable ["ACME_vent_o2SourceCtrl",_actionCtl];
        [] call ACME_fnc_ventPanelOxygenRefresh;
        [_valueCtl get "text"=="{want}","oxygen value contradicted usable attached supply"] call _check;
        [_valueCtl get "enabled" isEqualTo {str(usable).lower()},"only oxygen value was not correctly gated"] call _check;
        [_actionCtl get "text"=="DISCONNECT OXYGEN","empty source lost disconnect action"] call _check;
        [_patient getVariable "ACME_vent_fio2"==40,"read-only oxygen painter mutated stored settings"] call _check;
    ''')


@pytest.mark.parametrize("state,want", [("none",False),("READY",True),("EMPTY",False),("expired",False)])
@pytest.mark.parametrize("editor", [0,2])
def test_b276_compatibility_warning_requires_attached_source_without_drawing_gas(state, want, editor):
    change = {
        "none": '_patient setVariable ["ACME_vent_o2Session",""];',
        "READY": "",
        "EMPTY": '_patient setVariable ["ACME_vent_o2Status","EMPTY"];',
        "expired": '_patient setVariable ["ACME_vent_o2VerifiedUntil",1];',
    }[state]
    execute(fixture() + function("ventOxygenGate") + change + f'''
        private _draws=0;
        ACME_fnc_nrbOxygenSource={{missionNamespace}};
        ACME_fnc_useOxygenTankReserve={{_draws=_draws+1; true}};
        uiNamespace setVariable ["ACME_vent_editingParam",{editor}];
        uiNamespace setVariable ["ACME_vent_editingFio2",true];
        [call ACME_fnc_ventOxygenGate isEqualTo {str(want).lower()},"compatibility warning accepted an unattached or expired cylinder"] call _check;
        [_draws==0 && {{count _requests==0}},"compatibility warning consumed gas or changed settings"] call _check;
        [_patient getVariable "ACME_vent_fio2"==40,"compatibility warning changed saved FiO2"] call _check;
        [uiNamespace getVariable "ACME_vent_editingParam"=={editor if want or editor != 0 else -1},"warning cleared another parameter editor"] call _check;
        [uiNamespace getVariable "ACME_vent_editingFio2" isEqualTo {str(want).lower()},"warning kept a stale oxygen editor"] call _check;
    ''')


def test_ui_only_fio2_mutations_are_requests_and_reuses_existing_panel_tick():
    knob=read("ventPanelKnob")
    assert not re.search(r'_\w+ setVariable \["ACME_vent_fio2"', knob)
    from source_scan import lex
    tokens=[token.value for token in lex(knob)]
    request=[token.value for token in lex('"fio2", _viewer, _v] call ACME_fnc_ventOxygenRequest')]
    assert sum(tokens[index:index+len(request)]==request for index in range(len(tokens)-len(request)+1))==2
    router=read("ventPanelShowScreen")
    assert 'ctrlCreate ["ACME_VentActionG", -1]' in router
    assert 'ACME_vent_o2SourceCtrl' in router and 'ACME_vent_o2SupplyCtrl' in router
    assert 'uiNamespace setVariable ["ACME_vent_o2ValCtrl", controlNull]' in router
    tick=read("ventPanelTick")
    block=tick[tick.index("// A supply replica change"):tick.index("// slow measured BPM")]
    assert 'call ACME_fnc_ventPanelOxygenRefresh' in block
    assert 'addPerFrameHandler' not in block and 'ventPanelShowScreen' not in block


def test_fio2_request_contract_rejects_retired_global_provider(monkeypatch):
    real=read
    current=real('ventPanelKnob')
    old='"fio2", _viewer, _v] call ACME_fnc_ventOxygenRequest'
    assert current.count(old)==2
    broken=current.replace(old, '"fio2", ACE_player, _v] call ACME_fnc_ventOxygenRequest')
    monkeypatch.setitem(globals(), 'read', lambda name: broken if name=='ventPanelKnob' else real(name))
    with pytest.raises(AssertionError):
        test_ui_only_fio2_mutations_are_requests_and_reuses_existing_panel_tick()
