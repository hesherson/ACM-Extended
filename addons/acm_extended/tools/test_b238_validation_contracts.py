"""Execute updated validation expressions against production snippets, not canned results."""
from pathlib import Path
import pytest
from test_menu_death_lifecycle import execute, ROOT

@pytest.mark.parametrize('value,expected',[
    ('[]',False),('["a"]',False),('["a","b"]',False),
    ('["a","b","O+"]',True),('["a","b","O+","80 KG"]',True),
    ('["a","b",3]',False),('[1,"b","O+"]',False),
    ('"bad cache"',False),('true',False),('99',False),
    ('["a","b","O+",false]',True),
])
def test_dogtag_validation_preserves_short_and_malformed_cache_policy(value,expected):
    source=(ROOT/'addons/core/overrides/fnc_getDogtagData.sqf').read_text()
    expression=source.split('private _cacheValid = ',1)[1].split(';',1)[0]
    execute('private _dogtagData='+value+'; private _actual=('+expression+');'+
            f'[_actual isEqualTo {str(expected).lower()},"dogtag cache policy changed"] call _check;')

@pytest.mark.parametrize('value,expected',[('"leftarm"',True),('0',True),('3',True),('[]',False),('true',False),('createHashMap',False)])
def test_iv_site_type_gate_preserves_accepted_types(value,expected):
    source=(ROOT/'addons/acm_extended/functions/fn_ivStickBlows.sqf').read_text()
    gate=source.split('if !(',1)[1].split(') exitWith',1)[0]
    execute('private _site='+value+'; private _actual=('+gate+');'+
            f'[_actual isEqualTo {str(expected).lower()},"IV site type gate changed"] call _check;')

@pytest.mark.parametrize('initial,value,expected',[
    ('[]','"Saline"','["Saline"]'),('["Saline"]','"Saline"','["Saline"]'),
    ('["Saline"]','"saline"','["Saline","saline"]'),
    ('[[1,"a"]]','[1,"a"]','[[1,"a"]]'),
    ('[[1,"a"]]','[1,"b"]','[[1,"a"],[1,"b"]]'),
])
def test_unique_append_keeps_order_case_and_nested_record_membership(initial,value,expected):
    source=(ROOT/'addons/acm_extended/functions/fn_vesicantInjure.sqf').read_text()
    assert '_records pushBackUnique _rec;' in source
    execute(f'private _records={initial};private _rec={value};'+
            '_records pushBackUnique _rec;'+f'[_records isEqualTo {expected},"unique membership changed"] call _check;')

@pytest.mark.parametrize('cold,warm,hang,base',[(True,False,False,100),(True,True,False,100),(True,True,True,200),(False,True,False,200)])
@pytest.mark.parametrize('pressure',[0,0.25,0.75,1])
def test_current_blood_envelope_uses_continuous_pressure_without_losing_cap(cold,warm,hang,base,pressure):
    source=(ROOT/'addons/circulation/functions/fnc_getBloodVolumeChange.sqf').read_text()
    block=source.split('// Blood has an explicit device/temperature flow envelope',1)[1].split('// Final perfusion gate',1)[0]
    block=block[block.index('if (_type in '):]
    # SQF-VM lacks native hash-map lookup. Adapt only that storage boundary;
    # the cuff reader is supplied below, while the entire rate/cap calculation executes.
    lookup='(_unit getVariable ["ACME_piCuffs", createHashMap]) getOrDefault [_bagUid, []]'
    assert block.count(lookup)==1
    block=block.replace(lookup,'(_unit getVariable ["ACME_piCuffs", missionNamespace]) getVariable [_bagUid, []]')
    expected=(base+(300-base)*pressure)/60
    execute(f'''
        private _unit=_patient;private _type="Blood";private _bagUid="bag";
        private _coldFlag={str(cold).lower()};private _warmedFlag={str(warm).lower()};
        private _deltaT=1;private _bagChange=1;private _bagVolumeRemaining=500;
        _unit setVariable ["ACME_hang_flowMult",{2 if hang else 1}];
        ACME_fnc_pressureLevel={{{pressure}}};
    '''+block+f'''
        [abs (_bagChange-{expected})<0.00001,"continuous pressure envelope changed"] call _check;
        [_bagChange<=5 && {{_bagChange>=0}},"blood hard ceiling lost"] call _check;
    ''')
