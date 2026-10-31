"""B215 read-only bag presentation and final engine-metric layout behavior."""
import json
import re

import pytest

from test_debug_single_overlay import definition
from test_menu_death_lifecycle import execute, read

SOURCE = read('debugMenuClinical')


def helpers(*names):
    return ''.join(definition(n) for n in names).replace('toLowerANSI', 'toLower')


def drug_entry(uid='bag1', drug='Epinephrine', dose=0.5, part='leftarm', index=0,
               kind='Saline', site=1, iv=True, blood=-1, volume=500, fresh=-1):
    return ['dose', part, index, kind, site, iv, blood, volume, fresh, volume, 400,
            drug, drug+'_IV', dose, dose, 0, 0, 0, 0, 0, 20, 60, 0.4, uid]


def sqf(value):
    return json.dumps(value)


def bag_setup():
    return '''private _cGood="good";private _cWarn="warn";private _cMute="mute";private _cLabel="label";'''+helpers(
        '_medicationFamily', '_medicationLabel', '_medicationShort', '_bpShort',
        '_fluidShort', '_matchingBagMeds', '_fluidBagRows')+'ACME_fnc_formatDose={'+read('formatDose')+'};'


@pytest.mark.parametrize('name,label',[
    ('CalciumGluconate','Calcium Gluconate'),('CalciumChloride','Calcium Chloride'),
    ('AmmoniaInhalant','Ammonia Inhalant'),('TXA','TXA'),('HTS3','HTS3'),
    ('HIVTest','HIV Test'),('FutureDrug','Future Drug'),('Future_Drug','Future Drug'),
])
def test_medication_names_are_readable_without_splitting_acronyms(name,label):
    execute(helpers('_medicationLabel')+f'[[{sqf(name)}] call _medicationLabel=={sqf(label)},"medication word separation incorrect"] call _check;')


def test_medication_caption_matches_effective_dose_units_not_serum_concentration():
    assert '["MEDICATIONS"] call _sect' in SOURCE
    assert 'Effective reference-dose equivalents' in SOURCE
    assert 'MEDICATION SERUM LEVELS' not in SOURCE
    assert '[_patient, _x, false] call ACME_fnc_medicationCountCompat' in SOURCE
    assert 'param [1, 0, [0]]' in read('medicationCountCompat')


@pytest.mark.parametrize('value,expected',[(0,'0.000'),(0.0001,'0.000'),(0.12356,'0.124'),(2.25,'2.250')])
def test_ptx_is_displayed_to_exact_thousandths(value,expected):
    assert '["PTX", _ptx toFixed 3,' in SOURCE
    execute(f'[({value} toFixed 3)=="{expected}","PTX precision changed"] call _check;')


def test_obsolete_transport_section_is_removed_without_removing_runtime_diagnostics():
    assert 'CHEST-SEAL TRANSPORT' not in SOURCE
    assert 'ACME_CS_pending' not in SOURCE and 'ACME_CS_sessions' not in SOURCE
    assert 'RUNTIME / NETWORK' in SOURCE and 'COMPATIBILITY' in SOURCE


def test_multidrug_bag_uses_one_size_title_and_separate_correct_dose_details():
    entries=[drug_entry(),drug_entry(drug='CalciumGluconate',dose=2000),drug_entry(uid='other',drug='Ketamine',dose=70)]
    execute(bag_setup()+f'private _entries={sqf(entries)};'+'''
        private _bag=["Saline",400,2,1,true,-1,500,-1,"bag1"];
        private _rows=[_bag,"leftarm",0,_entries] call _fluidBagRows;
        [count _rows==5,"bag was duplicated or drug lost"] call _check;
        [(_rows select 0) isEqualTo ["bullet","500 mL NS","good",0],"title used remaining volume or omitted type"] call _check;
        [(_rows select 1) select 1=="LUE IV1 | 400 mL remaining","site/remaining volume missing"] call _check;
        [(_rows select 2) select 1=="Clamp: 60 gtt/min (20 gtt/mL)","flow units wrong"] call _check;
        [(_rows select 3) select 1=="Epi: 500mcg remaining","microgram dose mislabeled"] call _check;
        [(_rows select 4) select 1=="Ca Gluc: 2g remaining","gram dose or shorthand wrong"] call _check;
        [{(_x select 3)==0} count _rows==1,"multiple title bullets for one physical bag"] call _check;
    ''')


def test_identical_bags_keep_their_own_drugs_even_after_indices_change():
    entries=[drug_entry(uid='bagA',index=0,drug='Ketamine',dose=70),drug_entry(uid='bagB',index=1,drug='Norepinephrine',dose=4)]
    execute(bag_setup()+f'private _entries={sqf(entries)};'+'''
        private _one=[["Saline",350,2,1,true,-1,500,-1,"bagB"],"leftarm",0,_entries] call _fluidBagRows;
        private _two=[["Saline",350,2,1,true,-1,500,-1,"bagA"],"leftarm",1,_entries] call _fluidBagRows;
        [(_one select 3) select 1=="Norepi: 4mg remaining","first bag inherited old slot medication"] call _check;
        [(_two select 3) select 1=="Ketamine: 70mg remaining","second bag inherited old slot medication"] call _check;
    ''')


@pytest.mark.parametrize('field,value',[(1,'rightarm'),(2,1),(3,'Plasma'),(4,2),(5,False),(6,3),(7,1000),(8,14),(23,'wrong-id')])
def test_legacy_matching_rejects_every_wrong_identity_field(field,value):
    entry=drug_entry(uid='');entry[field]=value
    execute(bag_setup()+f'private _entries={sqf([entry])};'+'''
        private _rows=[["Saline",400,2,1,true,-1,500,-1,""],"leftarm",0,_entries] call _fluidBagRows;
        [count _rows==2,"legacy entry crossed a physical bag boundary"] call _check;
    ''')


def test_legacy_slot_exact_match_is_read_only_and_does_not_join_empty_uids():
    entries=[drug_entry(uid=''),drug_entry(uid='',index=1,drug='Ketamine',dose=70)]
    execute(bag_setup()+f'private _entries={sqf(entries)};'+'''
        private _bag=["Saline",400,2,1,true,-1,500,-1];private _before=str [_bag,_entries];
        private _rows=[_bag,"leftarm",0,_entries] call _fluidBagRows;
        [count _rows==4 && {(_rows select 3) select 1=="Epi: 500mcg remaining"},"empty IDs joined unrelated components"] call _check;
        [str [_bag,_entries]==_before,"presentation mutated bag or component data"] call _check;
    ''')
    fluid=SOURCE[SOURCE.index('// B215: one bullet per'):]
    assert 'setVariable' not in fluid and 'ACME_fnc_bagIdentity' not in fluid
    assert 'ACME_fnc_infusionFlow' not in fluid and 'ownerDispatch' not in fluid


@pytest.mark.parametrize('kind,remaining,expected',[
    ('ACME_Empty',0,0),('ACME_EmptySaline',400,0),('Saline',0,0),('Plasma',100,2),('FBTK',0,2),
])
def test_empty_markers_are_hidden_but_connected_collection_bags_remain_visible(kind,remaining,expected):
    execute(bag_setup()+f'''
        private _rows=[["{kind}",{remaining},2,-1,false,-1,500,-1,"id"],"leftleg",0,[]] call _fluidBagRows;
        [count _rows=={expected},"physical/empty bag classification wrong"] call _check;
        if (count _rows>0) then {{[((_rows select 1) select 1) find "LLE IO"==0,"IO location lost"] call _check;}};
    ''')


def test_no_connected_bags_is_explicit_and_has_no_empty_placeholder_details():
    section=SOURCE[SOURCE.index('_right pushBack (["FLUIDS / INFUSIONS"]'):]
    execute('private _right=[];private _cSect="gold";private _cMute="muted";private _fluidRows=[];'+helpers('_sect')+section.replace('call _renderAll;', '')+'''
        [count _right==2,"empty fluids generated detail lines"] call _check;
        [(_right select 1) isEqualTo ["bullet","No connected bags","muted",0],"empty bag state unclear"] call _check;
    ''')


def test_fluid_bullets_escape_tags_and_wrap_with_hanging_indentation():
    execute('private _cLabel="label";'+helpers('_safe','_padRight','_alignValue','_wrapValue','_formatRow')+'''
        private _row=[["bullet","Future <fluid> & another long medication name spanning the panel safely","gold",1],4,[6,6]] call _formatRow;
        [(_row find "    • <t")==0,"detail bullet indentation missing"] call _check;
        [(_row find "&lt;fluid&gt; &amp;")>=0,"fluid text was not escaped"] call _check;
        [(_row find "<br/>      <t")>=0,"long sub-bullet lacks hanging wrap"] call _check;
        [(_row find " :</t>")==-1,"bullet was incorrectly formatted as paired data"] call _check;
    ''')


@pytest.mark.parametrize('need_height_fit',[False,True])
def test_final_backdrop_width_tracks_content_after_vertical_font_reduction(need_height_fit):
    execute('''
        private _cLabel="label";private _cMute="mute";private _cSect="gold";
        private _valueW=11;private _baseFontH=0.01;private _fontH=0.01;private _gapFactor=0.26;
        private _gap=0;private _totalW=0.40;private _panelBottom=1;private _y=0;
        private _ctrlH="header";private _ctrlL="body";private _lastWidth=0;
        private _applyFont={};private _measureNaturalWidth={30*_fontH+0.005};
        private _layout={_lastWidth=_totalW;};private _renderBlock={};
    '''+f'private _measureRows={{{80 if need_height_fit else 20}*_fontH}};'+helpers('_safe','_padRight','_alignValue','_pair','_one','_wrapValue','_formatRow','_sect','_renderAll')+'''
        private _header=["TITLE"];private _top=[];private _network=[];private _left=[];
        private _right=[["FLUIDS"] call _sect,["bullet","500 mL NS","good",0]];
        call _renderAll;
        [abs (_lastWidth-(30*_fontH+0.005))<0.00001,"backdrop kept max width after final text scaling"] call _check;
        [_lastWidth<0.40,"unused right-side background remains"] call _check;
    '''+('[_fontH<0.01,"height overflow was not fitted"] call _check;' if need_height_fit else '[_fontH==0.01,"font shrank without overflow"] call _check;'))


@pytest.mark.parametrize('kind,blood,label', [('Blood',1,'O-'),('FreshBlood',6,'AB+'),('FBTK',7,'AB-')])
def test_blood_products_show_their_actual_donor_type(kind,blood,label):
    execute(bag_setup()+f'''
        private _rows=[["{kind}",200,2,1,true,{blood},500,-1,"id"],"rightarm",0,[]] call _fluidBagRows;
        [count _rows==3 && {{(_rows select 2) select 1=="Blood type: {label}"}},"blood product type lost or taken from patient instead of donor bag"] call _check;
    ''')
