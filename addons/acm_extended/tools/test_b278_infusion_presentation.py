"""B278 infusion names identify contents without changing physical carrier identity.

Production presentation helpers run in SQF-VM; localization and native control
queries are the Arma boundaries. No dosing, bag custody or icon substitution.
"""
import json
import re
import xml.etree.ElementTree as ET

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_b156_procedure_supplies import primitives
from test_b275_transfusion_presentation import presentation_setup


def fn(name):
    source = read(name).replace('finite _dose', 'true').replace(
        'localize format ["STR_ACM_Circulation_Medication_%1", _name]',
        '([format ["STR_ACM_Circulation_Medication_%1", _name]] call _localize)',
    )
    return 'ACME_fnc_' + name + '={' + primitives(adapt(source)) + '};'


def setup():
    # Use actual shipped English medication names, rather than fixture aliases.
    translations = {}
    for path in (ROOT / 'addons/circulation/stringtable.xml', ROOT / 'addons/acm_extended/stringtable.xml'):
        for key in ET.parse(path).getroot().iter('Key'):
            if key.attrib['ID'].startswith('STR_ACM_Circulation_Medication_'):
                text = key.findtext('English') or key.findtext('Original')
                if text:
                    translations[key.attrib['ID']] = text
    pairs = ','.join(json.dumps([key, text], ensure_ascii=False) for key, text in translations.items())
    return (
        'private _translations=createHashMapFromArray[' + pairs + '];'
        'private _localize={params["_key"];private _text=_translations get _key;if(isNil "_text")exitWith{_key};_text};'
        + ''.join(fn(name) for name in (
            'infusionName', 'infusionTitle', 'formatDose', 'preparedComponents',
            'formatInfusionLabel', 'formatPreparedLabel',
            'transfusionFluidShorthand', 'transfusionAccessLabel',
        ))
        + r'''
        private _entry={
            params["_name",["_uid","selected"],["_dose",1000]];
            private _record=[];for "_i" from 0 to 23 do {_record pushBack 0;};
            _record set[10,100];_record set[11,_name];_record set[14,_dose];
            _record set[20,20];_record set[21,60];_record set[22,-1];_record set[23,_uid];_record
        };
        '''
    )


@pytest.mark.parametrize('drug,title,short', [
    ('CalciumChloride', 'Calcium Chloride infusion', 'CaCl'),
    ('CalciumGluconate', 'Calcium Gluconate infusion', 'CaGlu'),
    ('Epinephrine', 'Epinephrine infusion', 'Epi'),
    ('Ketamine', 'Ketamine infusion', 'Ket'),
    ('Norepinephrine', 'Norepinephrine infusion', 'Norepi'),
    ('Propofol', 'Propofol infusion', 'Prop'),
    ('Ceftriaxone', 'Ceftriaxone infusion', 'Ceftriaxone'),
    ('UnknownAddonDrug', 'UnknownAddonDrug infusion', 'UnknownAddonDrug'),
])
def test_single_drug_prepared_and_active_titles_use_medication_not_saline(drug, title, short):
    execute(setup() + f'''
        private _active=["{drug}"] call _entry;
        private _prepared=["prepared","saline100","SalineIV_100","{drug}",1000,600,20,0,0,10,110,0,objNull,objNull,[]];
        private _before=str[_active,_prepared];
        [[[_active param[11,""]] ] call ACME_fnc_infusionTitle=="{title}","single-drug title wrong"]call _check;
        [["{drug}"] call ACME_fnc_infusionName=="{short}","canonical mixture alias changed"]call _check;
        [([_active,[_active]]call ACME_fnc_formatInfusionLabel)find"{title} | ">=0,"active row named carrier rather than drug"]call _check;
        [([_prepared]call ACME_fnc_formatPreparedLabel)find"{title} | ">=0,"prepared row named carrier rather than drug"]call _check;
        [([_prepared]call ACME_fnc_formatPreparedLabel)find"1g {short}">=0,"prepared details lost dose/name association"]call _check;
        [_before==str[_active,_prepared],"presentation rewrote clinical keys or doses"]call _check;
    ''')


def test_mixture_title_deduplicates_components_and_excludes_another_bag_uid():
    execute(setup() + r'''
        private _chloride=["CalciumChloride"]call _entry;
        private _gluconate=["CalciumGluconate"]call _entry;
        private _duplicate=["CalciumChloride"]call _entry;
        private _other=["Ketamine","different"]call _entry;
        private _all=[_chloride,_gluconate,_duplicate,_other];
        private _prepared=["prepared","saline100","SalineIV_100","CalciumChloride",1000,600,20,0,0,10,110,0,objNull,objNull,
            [["CalciumChloride",1000,1],["CalciumGluconate",3000,1],["CalciumChloride",500,1]]];
        private _before=str[_all,_prepared];
        [([_chloride,_all]call ACME_fnc_formatInfusionLabel)find"CaCl + CaGlu infusion | ">=0,"mixture included duplicate or another physical bag"]call _check;
        [([_prepared]call ACME_fnc_formatPreparedLabel)find"CaCl + CaGlu infusion | ">=0,"prepared mixture titles differ from attached title"]call _check;
        [([_prepared]call ACME_fnc_formatPreparedLabel)find"3g CaGlu">=0,"mixture lost component dose"]call _check;
        private _bags=[["Saline",110,0,0,true,-1,100,-1,"selected"]];
        [[_bags,_all,true,0]call ACME_fnc_transfusionAccessLabel=="CaCl/CaGlu","occupied access conflated calcium salts or used carrier label"]call _check;
        [_before==str[_all,_prepared],"mixture title changed bag/component records"]call _check;
    ''')


def test_titles_use_real_localization_unknown_names_without_guessed_abbreviations():
    execute(setup() + r'''
        _translations set["STR_ACM_Circulation_Medication_CalciumChloride","Chlorure de calcium"];
        [[["CalciumChloride"]]call ACME_fnc_infusionTitle=="Chlorure de calcium infusion","full title bypassed native translation"]call _check;
        [[["CalciumChloride","UnknownAddonDrug","CALCIUMCHLORIDE"]]call ACME_fnc_infusionTitle=="CaCl + UnknownAddonDrug infusion","unknown mixture ingredient invented an alias or case duplicate"]call _check;
        [[[]]call ACME_fnc_infusionTitle=="Infusion","empty record invented carrier or medication"]call _check;
        [[["CalciumChloride","","calciumchloride"]]call ACME_fnc_infusionTitle=="Chlorure de calcium infusion","duplicate records mislabeled a single drug as mixture"]call _check;
    ''')


@pytest.mark.parametrize('prepared', [False, True])
@pytest.mark.parametrize('mixture', [False, True])
@pytest.mark.parametrize('piggyback', [False, True])
def test_native_cards_use_the_same_titles_and_keep_native_physical_art(prepared, mixture, piggyback):
    source = read('transfusionCardData')
    replacements = {
        'ctrlIDC _list': '86127' if prepared else '86129',
        '_list lbText _row': '"Old saline label | old detail [PiB]"' if piggyback else '"Old saline label | old detail"',
        '_list lbColor _row': '[1,1,1,1]',
        '_list lbPicture _row': '"native-saline.paa"',
        '_list lbPictureRight _row': '"native-vial.paa"',
        '_list lbValue _row': '1',
        '_list lbData _row': '"unused"',
    }
    for before, after in sorted(replacements.items(), key=lambda item: -len(item[0])):
        source = source.replace(before, after)
    # Native CfgWeapons controls art lookups. Keep the bag/vial boundaries distinct.
    source = re.sub(r'getText \(configFile >> "CfgWeapons" >> \(_entry param \[1,""\]\) >> "picture"\)', '"native-saline.paa"', source)
    source = re.sub(r'getText \(configFile >> "CfgWeapons" >>[^;]+\)', '"native-vial.paa"', source)
    presentation = presentation_setup().replace('private _cfg = configFile >> "CfgWeapons" >> _class;', 'private _cfg = configFile;')
    presentation = presentation.replace('getText (_cfg >> "shortName")', '""').replace('getText (_cfg >> "displayName")', '""')
    # Localized name/format helpers supersede any engine fixture stubs.
    fixture = presentation + setup() + r'''
        ACM_circulation_fnc_formatFluidBagName={"Fixture"};
        private _selection=[+_primary,+_secondary];
        {private _uid=_x param[8,""];_x set[8,_forEachIndex];_x set[9,_uid];}forEach _selection;
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Target",_patient];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_BodyPart","leftarm"];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_SelectIV",true];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_AccessSite",0];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selection_IVBags",_selection];
        private _meds=[["CalciumChloride","secondary"]call _entry];
        private _components=[["CalciumChloride",1000,1]];
    '''
    if mixture:
        fixture += '_meds pushBack (["CalciumGluconate","secondary",3000]call _entry);_components pushBack ["CalciumGluconate",3000,1];'
    fixture += r'''
        _patient setVariable["ACME_infusion_BagMedications",_meds];
        private _prepared=["prepared","saline100","SalineIV_100","CalciumChloride",1000,600,20,0,0,10,110,0,objNull,objNull,_components];
        _medic setVariable["ACME_infusion_PreparedBags",[[],_prepared]];
        private _list=profileNamespace;private _row=0;
        private _before=str[_patient getVariable "ACM_circulation_IV_Bags",_medic getVariable "ACME_infusion_PreparedBags",_meds];
    ''' + 'ACME_fnc_transfusionCardData={' + primitives(adapt(source)) + '};'
    title = 'CaCl + CaGlu infusion' if mixture else 'Calcium Chloride infusion'
    if not prepared or piggyback:
        title += ' [PiB]'
    execute(fixture + f'''
        private _data=[_list,0]call ACME_fnc_transfusionCardData;
        [(_data select 0)=="{title}","card title did not match native prepared/active medication label"]call _check;
        [(_data select 5)=="native-saline.paa"&&{{(_data select 6)=="native-vial.paa"}},"medication title replaced physical carrier/vial art"]call _check;
        [(_data select 1)find"CaCl">=0,"dose lost its medication association"]call _check;
        [_before==str[_patient getVariable "ACM_circulation_IV_Bags",_medic getVariable "ACME_infusion_PreparedBags",_meds],"card presentation mutated custody or clinical keys"]call _check;
    ''')
