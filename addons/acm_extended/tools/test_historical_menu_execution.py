"""Execute current menu policy and collector/section logic, not retired UI models.

Config primitives are explicit arrays [class,category,parent,label]; render controls
and transport are not simulated. Conditions and callbacks are actual SQF closures.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute

F=ROOT/'addons/acm_extended/functions'
GUI=ROOT/'addons/gui/overrides'


def config_adapter(text):
    # Only config-engine reads change. Mapping, lineage, row copies, bucket ordering
    # and callback values execute as checked in.
    for name in ('_config','_base','_x'):
        text=text.replace('configName '+name,'('+name+' select 0)')
        for field,index in [('category',1),('displayName',3)]:
            text=text.replace('getText ('+name+' >> "'+field+'")','('+name+f' select {index})')
    text=text.replace('isClass _base','(count _base > 0)')
    text=text.replace('inheritsFrom _base','(_base param [2,[]])')
    return adapt(text,'gui')


def menu_setup():
    groups=(F/'fn_menuExamineGroups.sqf').read_text()
    mapper=(F/'fn_menuActionInfo.sqf').read_text()
    collector=(GUI/'fnc_collectActions.sqf').read_text().split('private _actions = missionNamespace',1)[1]
    collector='private _actions = missionNamespace'+collector
    # SQF-VM requires the explicit length for a range-to-end select.
    collector=collector.replace('(_actions select [count _configs])', '(_actions select [count _configs, (count _actions) - (count _configs)])')
    collector=collector.replace('configProperties [configFile >> "ace_medical_treatment_actions", "isClass _x"]','_configList')
    return ('ACME_fnc_menuExamineGroups={'+groups+'};'+
        'ACME_fnc_menuActionInfo={'+config_adapter(mapper)+'};'+
        'private _collect={'+config_adapter(collector)+'};'+'''
        private _conditions=0; private _callbacks=[]; private _configList=[];
        private _condition={_conditions=_conditions+1;true};
        private _action={_callbacks pushBack _this;};
        private _row={params ["_name","_category"];[_name,_category,_condition,_action,["item"],"original-icon"]};
        private _add={params ["_name","_category",["_parent",[]]];
            _configList pushBack [_name,_category,_parent,_name];
            private _rows=missionNamespace getVariable ["ace_medical_gui_actions",[]];
            _rows pushBack ([_name,_category] call _row);
            missionNamespace setVariable ["ace_medical_gui_actions",_rows];
        };
        missionNamespace setVariable ["ace_medical_gui_actions",[]];
        missionNamespace setVariable ["ACME_menuExamineGroups",[]];
    ''')


@pytest.mark.parametrize('name,category,parent,expected',[
    ('UseBVM','airway','UseStethoscope',['airway','ventilation',False]),
    ('UseBVM_Oxygen','airway','UseBVM',['airway','ventilation',False]),
    ('UseBVM_VehicleOxygen','airway','UseBVM',['airway','ventilation',False]),
    ('UseBVM_PortableOxygen','airway','UseBVM',['airway','ventilation',False]),
    ('UseStethoscope','examine','CheckBreathing',['airway','chest',False]),
    ('ACME_InspectChest','examine','CheckBreathing',['airway','chest',False]),
    ('SlapAwake','advanced','CheckResponse',['examine','',False]),
    ('CheckDogTags','examine','',['examine','',False]),
    ('CheckResponse','examine','',['examine','',False]),
    ('CheckPulse','examine','',['examine','',False]),
    ('AnotherAddonExam','examine','CheckPulse',['examine','',False]),
    ('AnotherAddonBVM','airway','UseBVM',['airway','',False]),
    ('Morphine','medication','',['medication','',False]),
    ('PlacePulseOximeter','examine','',['examine','examine_monitoring_equipment',False]),
    ('InspectIV_Upper','examine','',['examine','examine_injuries',False]),
])
def test_current_routes_do_not_capture_foreign_descendants_or_restore_basic_dropdowns(name,category,parent,expected):
    result=str(expected).replace("'",'"').replace('False','false')
    execute(menu_setup()+f'private _config=["{name}","{category}",["{parent}","{category}",[],"parent"],"label"];'+
        f'[([_config] call ACME_fnc_menuActionInfo) isEqualTo {result},"wrong category/bucket"] call _check;')


def test_collector_preserves_callbacks_items_icons_and_foreign_examination_order():
    execute(menu_setup()+'''
        ["ForeignFirst","examine"] call _add;
        ["CheckDogTags","examine"] call _add;
        ["CheckPulse","examine"] call _add;
        ["MeasureBloodPressure","examine"] call _add;
        ["ForeignSecond","examine"] call _add;
        ["ACME_InspectChest","examine"] call _add;
        ["UseBVM","airway",["UseStethoscope","examine",[],"steth"]] call _add;
        private _extra=["Drag","drag",_condition,_action];
        (missionNamespace getVariable "ace_medical_gui_actions") pushBack _extra;
        call _collect;
        private _rows=ace_medical_gui_actions;
        private _names=_rows apply {_x select 0};
        [_names isEqualTo ["MeasureBloodPressure","ForeignFirst","CheckPulse","ForeignSecond","ACME_InspectChest","UseBVM","Drag","CheckDogTags"],"current class ordering lost"] call _check;
        [_conditions==0 && {count _callbacks==0},"collection executed eligibility or treatment"] call _check;
        private _foreign=_rows select 1;
        [(_foreign select 4) isEqualTo ["item"] && {(_foreign select 5)=="original-icon"},"foreign metadata changed"] call _check;
        [call (_foreign select 2) && {_conditions==1},"condition closure replaced"] call _check;
        ["same arguments"] call (_foreign select 3);
        [_callbacks isEqualTo [["same arguments"]],"treatment callback replaced"] call _check;
        [(_rows select 6) isEqualTo _extra,"native tail row changed"] call _check;
    ''')


def test_collector_fails_closed_if_native_prefix_no_longer_matches_config():
    execute(menu_setup()+'''
        ["ForeignFirst","examine"] call _add;
        ["CheckPulse","examine"] call _add;
        private _rows=missionNamespace getVariable "ace_medical_gui_actions";
        (_rows select 0) set [0,"foreign reordered display"];
        private _before=+_rows;
        call _collect;
        [ace_medical_gui_actions isEqualTo _before,"mismatched prefix remapped callbacks"] call _check;
        [_conditions==0 && {count _callbacks==0},"mismatch ran action"] call _check;
    ''')


def section_setup():
    text=(GUI/'fnc_updateActions.sqf').read_text()
    a=text.index('private _menuActions = missionNamespace')
    b=text.index('private _shownIndex',a)
    text=text[a:b]
    text=text.replace("getText (configFile >> 'ace_medical_treatment_actions' >> 'CheckDogTags' >> 'displayName')","'Dog tags'")
    # Unsupported VM map getOrDefault primitive is replaced at that one boundary;
    # real hashmaps and the source's condition/row-copy algorithm are retained.
    text=text.replace("_nameKeys getOrDefault [_name, '']","([_nameKeys,_name,''] call _mapDefault)")
    # Config lookup is an engine boundary in this renderer harness. Anatomy itself has dedicated source/config
    # contracts; this execution fixture is for row ordering, conditions and callbacks.
    anatomy_start=text.index("private _groupAnatomyAllowed = {")
    anatomy_end=text.index("if (_nestEnabled) then {", anatomy_start)
    text=text[:anatomy_start] + "private _groupAnatomyAllowed={true};\n" + text[anatomy_end:]
    return menu_setup()+'''
        private _display=uiNamespace; private _target=_patient;
        private _bodyPart=0; private _selectedCategory="examine";
        private _nestEnabled=true; private _clinicalDescriptors=false;
        private _asBool={(_this select 0) isEqualTo true};
        private _mapDefault={params ["_map","_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
        private _available=true; private _seen=0;
        ACME_fnc_headElevateCanStart={true};
        _display setVariable ["ACME_menuOpen",[]];
        private _groupCondition={_seen=_seen+1;_available};
        private _grouped=["Pressure cuff","examine",_groupCondition,_action,[],"",[],"","PressureCuff_Attach","examine_monitoring_equipment"];
        private _direct=["Response","examine",_condition,_action,[],"",[],"","CheckResponse",""];
        private _dog=["Dog tags","examine",_condition,_action,[],"",[],"","CheckDogTags",""];
        missionNamespace setVariable ["ACME_menuGroups",[["examine_monitoring_equipment","Monitoring Equipment","examine",["Pressure cuff"],{true},[]]]];
        missionNamespace setVariable ["ace_medical_gui_actions",[_grouped,_direct,_dog]];
    '''+'private _render={'+adapt(text)+'; _menuActions};'


@pytest.mark.parametrize('grouped,opened,available',[
    (False,False,False),(False,False,True),
    (True,False,False),(True,False,True),
    (True,True,False),(True,True,True)])
def test_section_eligibility_and_callbacks_survive_flat_closed_and_open_views(grouped,opened,available):
    execute(section_setup()+f'_nestEnabled={str(grouped).lower()}; _available={str(available).lower()};'+
        ('_display setVariable ["ACME_menuOpen",["examine_monitoring_equipment"]];' if opened else '')+'''
        private _rows=call _render;
        private _visible=_rows select {call (_x select 2)};
        private _names=_visible apply {_x select 0};
        [(_names select ((count _names)-1))=="Dog tags","dog tags not last standalone"] call _check;
        ["Response" in _names,"basic assessment hidden in a dropdown"] call _check;
        [_seen==1,"grouped condition not evaluated once"] call _check;
    '''+f'[count _rows=={(3 if not grouped else (2+(1+int(opened) if available else 0)))},"incorrect grouping cardinality"] call _check;'+
        ('''private _child=_visible select ((count _visible)-2); ["original"] call (_child select 3); [_callbacks isEqualTo [["original"]],"opened child lost treatment callback"] call _check;''' if grouped and opened and available else ''))


@pytest.mark.parametrize('bodypart',[0,1,2,3,4,5])
@pytest.mark.parametrize('dead',[False,True])
def test_flat_direct_rows_are_not_rewritten_by_dropdown_anatomy_guard(bodypart,dead):
    execute(section_setup()+f'_bodyPart={bodypart}; _patientAlive={str(not dead).lower()}; _nestEnabled=false; _selectedCategory="airway";'+'''
        missionNamespace setVariable ["ace_medical_gui_actions",[
            ["Airway","airway",{true},_action,[],"",[],"","CheckAirway", "adjuncts"],
            ["Breathing","airway",{true},_action,[],"",[],"","CheckBreathing", "ventilation"],
            ["Other","airway",{true},_action,[],"",[],"","ForeignAction", ""]
        ]];
        private _rows=call _render;
        [count _rows==3,"flat/direct rows were removed by dropdown-only anatomy policy"] call _check;
        private _callbacksBefore=+_callbacks;
        ["direct"] call ((_rows select 2) select 3);
        [count _callbacks==count _callbacksBefore+1,"direct action callback was replaced"] call _check;
    ''')


@pytest.mark.parametrize('names',[
    ['CheckPulse','InspectIV_Lower','MeasureBloodPressure','ForeignExam','PressureCuff_Attach'],
    ['PressureCuff_Attach','ForeignExam','InspectIV_Lower','CheckPulse','MeasureBloodPressure'],
    ['MeasureBloodPressure','InspectIV_Lower','CheckPulse','PressureCuff_Attach','ForeignExam'],
])
def test_table_orders_only_grouped_equipment_and_keeps_direct_rows_in_native_order(names):
    expected=['PressureCuff_Attach','MeasureBloodPressure','InspectIV_Lower']+[n for n in names if n in ('CheckPulse','ForeignExam')]
    execute(menu_setup()+''.join('["'+name+'","examine"] call _add;' for name in names)+
            'call _collect; private _names=ace_medical_gui_actions apply {_x select 0};'+
            '[_names isEqualTo '+str(expected).replace("'",'"')+',"group order/native direct order changed"] call _check;')
