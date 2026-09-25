"""Batch 6: actual thoracostomy selection/refresh/hover at explicit UI boundaries.

Controls are identified by fixture IDs and their properties are recorded. Provider
permissions and inventory counts are fixtures; selection scopes and render-choice
logic run from the checked-out SQF. No game rendering or inventory replication.
"""
import re
from pathlib import Path
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute

F = ROOT / 'addons/acm_extended/functions'


def source(name):
    return (F / ('fn_' + name + '.sqf')).read_text()


def ui_code(text):
    # UI lookup returns its fixture control identifier, not an Arma control.
    text = re.sub(r'_\w+ displayCtrl (_\w+|\d+)', r'\1', text)
    text = re.sub(r'\bparseText\s+', '', text)
    ts = lex(text); pairs = matching(ts); reverse = {b:a for a,b in pairs.items()}
    commands = {'ctrlSetTextColor','ctrlSetPosition','ctrlSetBackgroundColor','ctrlSetText',
                'ctrlEnable','ctrlShow','ctrlCommit','ctrlSetTooltip','ctrlSetStructuredText'}
    edits = []
    for i,t in enumerate(ts):
        if t.kind != 'ident': continue
        metadata = t.value in ('getVariable','setVariable') and i > 0 and ts[i-1].value in ('_bg','_btn')
        if t.value not in commands and not metadata: continue
        a = i-1
        if ts[a].value in (')',']'): a = reverse[a]
        j = i+1
        while j < len(ts) and ts[j].value not in (';','}'):
            if ts[j].value in ('[','(','{') and j in pairs: j = pairs[j]+1
            else: j += 1
        left = text[ts[a].offset:t.offset].strip()
        right = text[ts[i+1].offset:ts[j].offset].strip()
        if metadata:
            call = '_controlRead' if t.value == 'getVariable' else '_controlSet'
            value = f'([{left},{right}] call {call})'
        else: value = f'([{left},"{t.value}",{right}] call _controlWrite)'
        edits.append((ts[a].offset, ts[j].offset, value))
    for a,b,v in reversed(edits): text = text[:a]+v+text[b:]
    return adapt(text)


def function(name):
    text=source(name)
    if name=='thoraUpdateTrayIcons':
        # This VM lacks continue. An inner call makes exitWith leave only the
        # current foreach iteration, preserving the original continue semantics.
        text=text.replace('\n{\n    private _bg = _x;', '\n{\n    call {\n    private _bg = _x;',1)
        text=text.replace('if (_tool == "tube" && {!_canTube} && {_held != "tube"}) then {', 'if (_tool == "tube" && {!_canTube} && {_held != "tube"}) exitWith {')
        text=text.replace('        continue;\n    } else {','    };\n    call {',1)
        text=text.replace('} forEach (uiNamespace getVariable ["ACME_Thora_SlotBGs"','};\n} forEach (uiNamespace getVariable ["ACME_Thora_SlotBGs"',1)
    return 'ACME_fnc_' + name + '={' + ui_code(text) + '};\n'


def controls():
    return '''
        private _controlProps=createHashMap; private _controlValues=createHashMap;
        private _uiWrites=[];
        private _controlRead={params ["_c","_args"];_args params ["_k","_default"];
            private _key=(str _c)+":"+_k;
            if (_key in _controlProps) then {_controlProps get _key} else {_default}};
        private _controlSet={params ["_c","_args"];_args params ["_k","_v"];_controlProps set [(str _c)+":"+_k,_v];};
        private _controlWrite={params ["_c","_op","_v"];_uiWrites pushBack _this;_controlValues set [(str _c)+":"+_op,_v];};
    '''


def setup():
    return controls()+'''
        private _allowTube=true; private _allowSeal=true; private _allowOpen=true;
        private _tubeStock=1; private _sealStock=1; private _kit="ACM_ThoracostomyKit";
        private _countReads=[]; private _permissionReads=[];
        ACME_fnc_procedureAllowed={params ["_who","_which"];_permissionReads pushBack _who;
            switch (_which) do {case "chestTube":{_allowTube};case "thoracostomySeal":{_allowSeal};default{_allowOpen}}};
        ace_common_fnc_getCountOfItem={params ["_who","_item"];_countReads pushBack _who;
            if (_item=="ACM_ChestTubeKit") then {_tubeStock} else {_sealStock}};
        ace_medical_treatment_fnc_isMedic={true};
        ACME_fnc_treatmentSupplyCount={params ["_who","_patient","_item"];[_who,_item] call ace_common_fnc_getCountOfItem};
        ACME_fnc_thoraKitItem={_kit};
        uiNamespace setVariable ["ACME_Thora_DLG",missionNamespace];
        uiNamespace setVariable ["ACME_Thora_Patient",_patient];
        uiNamespace setVariable ["ACME_Thora_Medic",_medic];
        uiNamespace setVariable ["ACME_Thora_Side","right"];
        uiNamespace setVariable ["ACME_Thora_Held",""];
        uiNamespace setVariable ["ACME_Thora_SlotBGs",[100,200]];
        {
            _x params ["_bg","_tool"];
            [_bg,["thoraTool",_tool]] call _controlSet;
            [_bg,["thoraIcon",_bg+1]] call _controlSet;
            [_bg,["thoraBtn",_bg+2]] call _controlSet;
            [_bg,["thoraCount",_bg+3]] call _controlSet;
            [_bg+2,["thoraIcon",_bg+1]] call _controlSet;
            [_bg+2,["thoraBG",_bg]] call _controlSet;
            [_bg+2,["thoraTool",_tool]] call _controlSet;
            [_bg+2,["thoraIconRect",[0.1,0.2,0.05,0.08]]] call _controlSet;
        } forEach [[100,"tube"],[200,"seal"]];
    '''+function('thoraCanSweep')+function('thoraClosureMode')+function('thoraUpdateTrayIcons')+function('thoraSelectTool')+function('thoraSlotHover')


@pytest.mark.parametrize('tool', ['tube','seal'])
@pytest.mark.parametrize('reject', ['permission','stock','provider'])
def test_rejected_closure_selection_cannot_change_held_tool_or_interrupt_current_step(tool,reject):
    change = {'permission':'_allowTube=false;_allowSeal=false;',
              'stock':'_tubeStock=0;_sealStock=0;',
              'provider':'uiNamespace setVariable ["ACME_Thora_Medic",objNull];'}[reject]
    execute(setup()+change+'''
        uiNamespace setVariable ["ACME_Thora_Held","scalpel"];
        uiNamespace setVariable ["ACME_Thora_Cutting",true];
        uiNamespace setVariable ["ACME_Thora_TubeSnap",true];
    '''+f'["{tool}",true] call ACME_fnc_thoraSelectTool;'+'''
        [(uiNamespace getVariable "ACME_Thora_Held")=="scalpel","rejected tool still selected"] call _check;
        [uiNamespace getVariable ["ACME_Thora_Cutting",false],"rejected click cancelled existing cutting"] call _check;
        [uiNamespace getVariable ["ACME_Thora_TubeSnap",false],"rejected click reset unrelated state"] call _check;
        [count _uiWrites==0,"rejected selection repainted as accepted"] call _check;
    ''')


@pytest.mark.parametrize('tool', ['tube','seal'])
@pytest.mark.parametrize('alive', [True,False])
def test_valid_selection_and_last_item_putdown_remain_available(tool,alive):
    execute(setup()+f'_patientAlive={str(alive).lower()};'+f'["{tool}",true] call ACME_fnc_thoraSelectTool;'+
            f'[(uiNamespace getVariable "ACME_Thora_Held")=="{tool}","valid closure selection failed"] call _check;'+'''
        _tubeStock=0;_sealStock=0;_allowTube=false;_allowSeal=false;
        call ACME_fnc_thoraUpdateTrayIcons;
    '''+f'[(_controlValues get "{102 if tool=="tube" else 202}:ctrlEnable"),"selected depleted closure cannot be put down"] call _check;'+
            f'["{tool}",true] call ACME_fnc_thoraSelectTool;'+'''
        [(uiNamespace getVariable "ACME_Thora_Held")=="","last item could not be put down"] call _check;
        [!(_controlValues get "102:ctrlEnable") && {!(_controlValues get "202:ctrlEnable")},"unavailable unselected closures enabled"] call _check;
    ''')


@pytest.mark.parametrize('tool',['tube','seal'])
def test_selection_uses_captured_provider_not_new_controlled_unit(tool):
    execute(setup()+'''ACE_player=missionNamespace;'''+f'["{tool}",true] call ACME_fnc_thoraSelectTool;'+'''
        [count _countReads>0 && {count _permissionReads>0},"provider checks omitted"] call _check;
        {[_x isEqualTo _medic,"used newly controlled actor for inventory or permission"] call _check;} forEach (_countReads+_permissionReads);
    ''')


@pytest.mark.parametrize('held',['tube','seal'])
@pytest.mark.parametrize('hover',['tube','seal'])
@pytest.mark.parametrize('enter',[True,False])
def test_hover_preserves_only_the_actual_held_tools_shadow(held,hover,enter):
    icon=101 if hover=='tube' else 201
    execute(setup()+f'uiNamespace setVariable ["ACME_Thora_Held","{held}"];'+
            f'[{icon+1},{str(enter).lower()}] call ACME_fnc_thoraSlotHover;'+
            f'private _color=_controlValues get "{icon}:ctrlSetTextColor";'+
            f'[_color isEqualTo {"[0,0,0,1]" if held==hover else "[1,1,1,1]" if enter else "[1,1,1,0.85]"},"hover shadow confused separate tube/seal identities"] call _check;')


@pytest.mark.parametrize('held',['tube','seal'])
def test_inventory_refresh_preserves_held_identity_and_black_shadow(held):
    own=101 if held=='tube' else 201
    other=201 if held=='tube' else 101
    execute(setup()+f'uiNamespace setVariable ["ACME_Thora_Held","{held}"];'+'''
        for "_i" from 1 to 5 do {
            _tubeStock=0;_sealStock=0;
            call ACME_fnc_thoraUpdateTrayIcons;
        };
    '''+f'[(uiNamespace getVariable "ACME_Thora_Held")=="{held}","inventory changed held identity"] call _check;'+
            f'[(_controlValues get "{own}:ctrlSetTextColor") isEqualTo [0,0,0,1],"refresh lost held shadow"] call _check;'+
            f'[(_controlValues get "{other}:ctrlSetTextColor") isEqualTo [0.4,0.4,0.4,0.5],"other depleted slot not independently locked"] call _check;'+'''
        [(_uiWrites findIf {(_x select 1)=="ctrlSetPosition"})<0,"refresh resized tray geometry"] call _check;
    ''')


@pytest.mark.parametrize('tool',['tube','seal'])
def test_internal_closure_putdown_does_not_change_into_the_other_tool(tool):
    execute(setup()+f'uiNamespace setVariable ["ACME_Thora_Held","{tool}"];'+'''
        ["tube"] call ACME_fnc_thoraSelectTool;
        [(uiNamespace getVariable "ACME_Thora_Held")=="","internal closure cleanup selected another tool"] call _check;
    ''')


@pytest.mark.parametrize('open_tract',[True,False])
def test_repeat_finger_sweep_needs_no_second_kit_but_new_tract_does(open_tract):
    execute(setup()+'''
        _kit="";
        _patient setVariable ["ACME_thora_incision_right",[[0.2,0.4],0,3]];
    '''+f'_patient setVariable ["ACME_thora_open_right","{"finger" if open_tract else ""}"];'+'''
        ["finger"] call ACME_fnc_thoraSelectTool;
    '''+f'[(uiNamespace getVariable "ACME_Thora_Held")=="{"finger" if open_tract else ""}","finger kit/aftercare policy changed"] call _check;')


def test_real_closure_availability_never_substitutes_a_seal_for_a_tube():
    execute(setup()+'''
        _tubeStock=0;_sealStock=1;
        private _result=[_medic] call ACME_fnc_thoraClosureMode;
        [_result isEqualTo ["tube",0,false],"tube availability silently became a seal"] call _check;
        _tubeStock=2;_allowTube=true;
        _result=[_medic] call ACME_fnc_thoraClosureMode;
        [_result isEqualTo ["tube",2,true],"available tube identity wrong"] call _check;
    ''')
