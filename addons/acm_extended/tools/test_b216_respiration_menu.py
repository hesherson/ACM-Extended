"""Execute respiratory action routing, ordering and flat/dropdown rendering."""
import itertools
import re

import pytest

from test_historical_menu_execution import F, menu_setup, section_setup
from test_menu_death_lifecycle import execute


@pytest.mark.parametrize('category', ['examine', 'airway'])
def test_explicit_respiratory_route_overrides_legacy_category_without_capturing_other_examinations(category):
    execute(menu_setup()+f'''
        private _config=["ACME_MeasureRespirations","{category}",["CheckPulse","examine",[],"Pulse"],"Respirations"];
        [([_config] call ACME_fnc_menuActionInfo) isEqualTo ["airway","ventilation",false],"wrong respiratory tab/section"] call _check;
        private _foreign=["ForeignPulseChild","examine",["CheckPulse","examine",[],"Pulse"],"Other"];
        [([_foreign] call ACME_fnc_menuActionInfo) isEqualTo ["examine","",false],"unrelated assessment was moved"] call _check;
    ''')


@pytest.mark.parametrize('names', list(itertools.permutations(['ACME_MeasureRespirations','CheckBreathing','UseBVM'])))
def test_order_uses_class_identity_and_preserves_native_callbacks(names):
    code=menu_setup()
    for index,name in enumerate(names):
        code+=f'''["{name}","airway"] call _add;
            (_configList select {index}) set [3,"translated {index}"];
            ((missionNamespace getVariable "ace_medical_gui_actions") select {index}) set [0,"translated {index}"];
        '''
    code+='''
        ["ForeignAirway","airway"] call _add;
        call _collect;
        private _rows=ace_medical_gui_actions;
        private _ids=_rows apply {_x select 8};
        private _checkIndex=_ids find "CheckBreathing";
        [(_ids find "ACME_MeasureRespirations")==(_checkIndex+1),"measurement not immediately below Check Breathing"] call _check;
        [count _rows==4 && {(_ids select 3)=="ForeignAirway"},"unrelated row lost/reordered"] call _check;
        [_conditions==0 && {count _callbacks==0},"collection invoked clinical callbacks"] call _check;
        private _measurement=_rows select (_checkIndex+1);
        [(_measurement select 9)=="ventilation" && {(_measurement select 4) isEqualTo ["item"]},"row metadata lost"] call _check;
        ["original arguments"] call (_measurement select 3);
        [_callbacks isEqualTo [["original arguments"]],"native callback replaced"] call _check;
    '''
    execute(code)


def test_missing_check_breathing_does_not_hide_measurement():
    execute(menu_setup()+'''
        ["ForeignAirway","airway"] call _add;
        ["ACME_MeasureRespirations","airway"] call _add;
        call _collect;
        [(ace_medical_gui_actions apply {_x select 8}) isEqualTo ["ForeignAirway","ACME_MeasureRespirations"],"optional parent absence hid measurement"] call _check;
    ''')


@pytest.mark.parametrize('bodypart', [0,1])
@pytest.mark.parametrize('view', ['flat','closed','open'])
def test_actual_breathing_group_contains_measurement_on_head_and_body(bodypart,view):
    config=(F/'fn_initMedicalMenuConfig.sqf').read_text()
    code=section_setup()+config+f'''
        _bodyPart={bodypart}; ace_medical_gui_selectedBodyPart=_bodyPart;
        _selectedCategory="airway"; _nestEnabled={str(view!='flat').lower()};
        missionNamespace setVariable ["ace_medical_gui_actions",[]]; _configList=[];
        ["ACME_MeasureRespirations","airway"] call _add;
        ["CheckBreathing","airway"] call _add;
        call _collect;
    '''
    if view=='open':
        code+='_display setVariable ["ACME_menuOpen",["ventilation"]];'
    code+='private _rows=call _render; private _ids=_rows apply {_x param [8,""]};'
    if view=='closed':
        code+='''[count _rows==1 && {((_rows select 0) param [7,""])=="ventilation"},"closed Breathing section missing or leaked action"] call _check;'''
    else:
        code+='''["ACME_MeasureRespirations" in _ids,"measurement hidden from breathing view"] call _check;'''
        if bodypart==0:
            code+='''[(_ids find "ACME_MeasureRespirations")==((_ids find "CheckBreathing")+1),"dropdown/flat order changed"] call _check;'''
        else:
            code+='''[!("CheckBreathing" in _ids),"existing head-only assessment scope changed"] call _check;'''
    execute(code)


def test_config_category_changes_without_changing_observation_launcher_or_anatomy():
    config=(F.parent/'config.cpp').read_text()
    block=re.search(r'class ACME_MeasureRespirations: CheckPulse \{(.*?)\n    \};',config,re.S).group(1)
    assert 'category = "airway";' in block
    assert 'allowedSelections[] = {"Head", "Body"};' in block
    assert 'callbackSuccess = "ACME_fnc_respirationStart";' in block
    assert 'treatmentTime = 0.001;' in block
