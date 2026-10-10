"""B213 debug data and renderer checks. Arma controls/config enumeration are explicit engine boundaries."""
from pathlib import Path
import re

import pytest

from medication_inventory import inventory
from test_debug_single_overlay import definition
from test_menu_death_lifecycle import ROOT, execute, read

SOURCE = read('debugMenuClinical')


def helpers(*names):
    return ''.join(definition(name) for name in names)


@pytest.mark.parametrize('value', ['yes', 'no'])
@pytest.mark.parametrize('label', ['Aware', 'Paralyzed', 'TPTX', 'Checked?'])
def test_boolean_labels_always_end_in_one_question_mark(label, value):
    execute(helpers('_pair', '_one') + f'''
        private _oneRow=["{label}","{value}","color"] call _one;
        private _pairRow=["{label}","{value}","color","{label}","{value}","color"] call _pair;
        {{[(_x select [(count _x)-1])=="?" && {{(_x find "??")==-1}},"boolean punctuation missing/duplicated"] call _check;}} forEach [_oneRow select 0,_pairRow select 0,_pairRow select 3];
        private _plain=["Pressure",4,"color"] call _one;
        [(_plain select 0)=="Pressure","numeric reading acquired a question mark"] call _check;
    ''')


def test_all_installed_concrete_medication_classes_have_one_always_present_family_slot():
    matrix=inventory(ROOT/'addons/core/ACM_Medication.hpp',ROOT/'addons/acm_extended/config.cpp')
    names=[row['classname'] for row in matrix['medication_classes']]
    source=SOURCE[SOURCE.index('private _medicationGroups ='):SOURCE.index('// Nondrug sedation')]
    source=re.sub(r'\("true" configClasses .*?\) apply \{configName _x\}', '_catalog',source)
    source=source.replace('finite _value','true')
    import json
    execute(helpers('_medicationFamily','_sect')+'''
        private _right=[];private _cSect="gold";private _cGood="green";private _cMute="muted";
        missionNamespace setVariable ["ACME_debugMedicationGroups",[]];
        private _queries=[];
        ACME_fnc_medicationCountCompat={_queries pushBack _this;0};
    '''+f'private _catalog={json.dumps(names+ ["ACM_IV_Medication","ACM_PO_Medication"])};'+source+f'''
        [count _queries=={len(names)},"a registered medication route was hidden or queried twice"] call _check;
        [(_queries apply {{_x select 1}}) arrayIntersect _catalog isEqualTo (_queries apply {{_x select 1}}),"noncatalog classes appeared"] call _check;
        [{{!(_x select 2)}} count _queries==count _queries,"drug rows bypass onset-aware effect calculation"] call _check;
        [count _medicationRows==29,"unexpected concrete medication family coverage"] call _check;
        [{{(_x select 1)=="0.00"}} count _medicationRows==count _medicationRows,"empty drugs disappeared instead of retaining a zero slot"] call _check;
        private _allClasses=[];{{_allClasses append (_x select 1);}} forEach _medicationGroups;
        [count _allClasses=={len(names)} && {{count (_allClasses arrayIntersect _allClasses)==count _allClasses}},"medication class was lost/duplicated during grouping"] call _check;
    ''')


@pytest.mark.parametrize('name,family',[
    ('Ketamine_IV','Ketamine'),('Ketamine','Ketamine'),('Atropine_IV_L','Atropine'),
    ('Fentanyl_BUC','Fentanyl'),('EpinephrineCardiac_IV','Epinephrine'),
    ('CalciumGluconate_IV','CalciumGluconate'),('FutureDrug_IV','FutureDrug')])
def test_route_families_preserve_drug_identity_and_future_catalog_entries(name,family):
    execute(helpers('_medicationFamily')+f'[["{name}"] call _medicationFamily=="{family}","route family mismatch"] call _check;')


def test_medication_effects_sum_routes_without_using_sedation_components_or_inventory():
    source=SOURCE[SOURCE.index('private _medicationRows ='):SOURCE.index('// Nondrug sedation')].replace('finite _value','true')
    execute(helpers('_sect')+'''
        private _right=[];private _cSect="gold";private _cGood="green";private _cMute="muted";
        private _medicationGroups=[["Fentanyl",["Fentanyl","Fentanyl_IV","Fentanyl_BUC"]],["Naloxone",["Naloxone"]]];
        ACME_fnc_medicationCountCompat={switch (_this select 1) do {case "Fentanyl": {0.1};case "Fentanyl_IV":{0.7};case "Fentanyl_BUC":{0.2};default{0};}};
    '''+source+'''
        [(_medicationRows select 0) isEqualTo ["Fentanyl","1.00","green"],"route effects not combined"] call _check;
        [(_medicationRows select 1) isEqualTo ["Naloxone","0.00","muted"],"zero drug slot missing"] call _check;
    ''')


def test_requested_clinical_terms_and_order_are_bound_to_correct_data():
    for label in ['CircVol','EffVol','ExcsVol','Platelets','Calcium','VC','Brain damage','HTX','FThor Left','FThor Right','Herniation','Paralyzed','Seizing']:
        assert f'"{label}"' in SOURCE
    assert '"Calcium", _calcium toFixed 2' in SOURCE
    assert '"Brain damage", _tbiStruct toFixed 2' in SOURCE
    assert SOURCE.index('["AIRWAY / CHEST"]') < SOURCE.index('["METABOLIC"]') < SOURCE.index('["NEURO / TBI"]')
    render=definition('_renderAll')
    assert render.index('_allRows append _top;') < render.index('_allRows append _network;') < render.index('_allRows append _left;')
    assert SOURCE.index('["MEDICATIONS"]') < SOURCE.index('// Nondrug sedation') < SOURCE.index('["SEDATION / AWARENESS"]')
    section=SOURCE[SOURCE.index('// Nondrug sedation'):SOURCE.index('// Cerebral seizure state')]
    assert '"Sedation load"' in section and '"Aware"' in section and '"Paralyzed"' in section
    assert '"Roc"' not in section and '"Ket"' not in section


def test_tube_marker_uses_same_cyan_as_native_medical_menu_and_keeps_side():
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    color=re.search(r'class ACME_Torso_ChestTube_Right.*?colorText\[\] = \{([^}]+)',config,re.S)[1]
    rgb=[round(float(v.strip())*255) for v in color.split(',')[:3]]
    assert '#' + ''.join(f'{v:02X}' for v in rgb)=='#30E8ED'
    assert 'private _cTube  = "#30E8ED";' in SOURCE
    for side in 'LR':
        assert f'private _thora{side} = if (_tube{side}) then {{"[TUBE]"}}' in SOURCE
        assert f'if (_tube{side}) then {{_cTube}}' in SOURCE


def test_patient_details_are_below_title_and_use_native_weight_and_blood_type():
    source=SOURCE[SOURCE.index('private _bloodTypeID ='):SOURCE.index('private _renderAll =')]
    assert '"ACM_circulation_BloodType", -1' in source
    assert '["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]' in source
    assert '"ACM_core_BodyWeight", 80' in source
    assert source.index('ACME DEBUG') < source.index('["Patient"') < source.index('["Blood type"')
    assert 'else {"unknown"}' in source


def test_colons_align_over_whole_columns_with_indent_and_separator_after_last_section():
    execute('''
        private _cLabel="label";private _cMute="muted";private _cSect="gold";
        private _valueW=11;private _baseFontH=0.0092;private _fontH=0.0092;private _gapFactor=0.26;
        private _gap=0;private _totalW=0.255;private _panelBottom=1;private _y=0;
        private _ctrlH="header";private _ctrlL="body";private _rendered=[];
        private _applyFont={};private _measureNaturalWidth={0.2};private _measureRows={0.2};private _layout={};
        private _renderBlock={_rendered pushBack _this;};
    '''+helpers('_safe','_padRight','_alignValue','_pair','_one','_wrapValue','_formatRow','_sect','_renderAll')+'''
        private _header=["TITLE",["Patient","Casualty","white"] call _one];
        private _top=[["OWNERSHIP"] call _sect,["Role","client","white","MP","yes","white"] call _pair];
        private _network=[["RUNTIME"] call _sect,["Build",213,"white"] call _one];
        private _left=[["VITALS"] call _sect,["HR",80,"white","RR",16,"white"] call _pair];
        private _right=[["MEDICATIONS"] call _sect,["CalciumGluconate","0.00","white","Norepinephrine","0.00","white"] call _pair];
        call _renderAll;
        private _rows=(_rendered select 1) select 1;
        private _data=_rows select {(_x find " :</t>")>=0};
        private _colon=(_data select 0) find " :</t>";
        {
            [(_x find "  <t color='label'>")==0,"data labels are not indented"] call _check;
            [(_x find " :</t>")==_colon,"first-column colon is misaligned"] call _check;
        } forEach _data;
        [count (_rows select {(_x find "________")>=0})==4,"missing section bottom separator"] call _check;
        [((_rows select ((count _rows)-1)) find "________")>=0,"last section lacks separator"] call _check;
        [((_data select 0) find "MP?")>=0,"boolean label lost punctuation during rendering"] call _check;
        [((_data select 3) find "CalciumGluconate :</t>")>=0,"colon is not one space past longest label"] call _check;
    ''')
