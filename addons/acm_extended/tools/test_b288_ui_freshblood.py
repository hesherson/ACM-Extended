"""Execute fresh-blood presentation against immutable persisted donor facts.

Only config/localization reads are supplied; the actual resolver and native
label/formatter decisions execute. No native screen rendering is claimed.
"""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read


def setup():
    resolver=read('freshBloodResolve')
    resolver=re.sub(r'finite \(([^()]+)\)',r'((\1) isEqualType 0)',resolver)
    resolver=resolver.replace('finite _id','(_id isEqualType 0)')
    convert=(ROOT/'addons/circulation/functions/fnc_convertBloodType.sqf').read_text()
    for i,name in enumerate(['O','ON','A','AN','B','BN','AB','ABN']):
        convert=re.sub(r'\bACM_BLOODTYPE_'+name+r'\b',str(i),convert)
    native=(ROOT/'addons/circulation/functions/fnc_TransfusionMenu_UpdateBagList.sqf').read_text()
    start=native.index('        if (_type == "FreshBlood") then {')
    native=native[start:native.index('        if !(_type in ["ACME_Empty"',start)]
    native=native.replace('C_LLSTRING(FreshBloodBag_Short)','"Fresh blood %1"')
    fmt=(ROOT/'addons/circulation/functions/fnc_getFluidBagString.sqf').read_text()
    fmt=fmt.replace('LLSTRING(FreshBlood)','"Fresh blood"').replace('LLSTRING(Blood)','"Blood"')
    fmt=re.sub(r'private _config =[^;]+;', 'private _config=0;',fmt)
    fmt=fmt.replace('GET_STRING(_config >> _classname >> "type","Blood")','_kind')
    fmt=fmt.replace('GET_NUMBER(_config >> _classname >>"volume",1000)','_configuredVolume')
    fmt=fmt.replace('GET_NUMBER(_config >> _classname >> "bloodtype",0)','0')
    return r'''
        private _kind="FreshBlood";private _configuredVolume=500;
        private _registryReads=0;
        ACM_circulation_fnc_getFreshBloodEntry={_registryReads=_registryReads+1;[objNull,500,1,true,20]};
    ''' + 'ACME_fnc_freshBloodResolve={' + adapt(resolver) + '};' + \
        'ACM_circulation_fnc_convertBloodType={' + adapt(convert,'circulation') + '};' + \
        'ACM_circulation_fnc_getFluidBagString={' + adapt(fmt,'circulation') + '};' + \
        'private _label={params["_bag"];_bag params["_type","","","","","_bloodType","_volume","_id"];private _name="";' + adapt(native,'circulation') + '_name};'


@pytest.mark.parametrize('saved_id',[-1,1])
def test_active_bag_label_uses_inline_type_even_when_registry_id_was_reused(saved_id):
    execute(setup() + f'''
        private _bag=["FreshBlood",400,1,0,true,6,500,{saved_id},"bag",500,["freshV1",true,10,6]];
        private _text=[_bag]call _label;
        [_text find "AB+" >=0 && {{_text find "O-" <0}},"restored label used new donor"]call _check;
        [_text find "[-1]" <0 && {{_registryReads==0}},"restored label exposed invalid ID or consulted new registry"]call _check;
    ''')


@pytest.mark.parametrize('inline', ['["freshMissingV1"]','["freshV1",true,10,1]'])
def test_fenced_or_type_mismatched_bag_label_never_falls_back_to_new_donor(inline):
    execute(setup() + f'''
        private _text=[["FreshBlood",400,1,0,true,6,500,1,"bag",500,{inline}]]call _label;
        [_text find "donor information unavailable" >=0 && {{_registryReads==0}},"missing donor label borrowed new donor"]call _check;
    ''')


def test_bare_fresh_classname_formats_without_missing_id_index_and_uses_inline_type():
    execute(setup() + r'''
        private _text=["FreshBloodBag_500",["freshV1",true,10,6],6,-1]call ACM_circulation_fnc_getFluidBagString;
        [_text=="Fresh blood 500ml AB+","bare restored classname lost donor type"]call _check;
        [_registryReads==0,"inline formatter read reused ID"]call _check;
    ''')


def test_bare_unknown_fresh_classname_formats_unavailable_without_id_minus_one():
    execute(setup() + r'''
        private _text=["FreshBloodBag_500"]call ACM_circulation_fnc_getFluidBagString;
        [_text find "donor information unavailable" >=0 && {_text find "-1" <0},"unknown formatter fabricated donor/id"]call _check;
    ''')


def test_live_unique_classname_still_uses_current_valid_registry_entry():
    execute(setup() + r'''
        private _text=["FreshBloodBag_500_1"]call ACM_circulation_fnc_getFluidBagString;
        [_text=="Fresh blood 500ml O- [ID:1]" && {_registryReads==1},"ordinary fresh bag lost native donor label"]call _check;
    ''')


def test_nonfresh_formatter_keeps_existing_native_fluid_behavior():
    execute(setup() + r'''
        _kind="Saline";
        [["SalineIV_500"]call ACM_circulation_fnc_getFluidBagString=="Saline 500ml","ordinary saline label changed"]call _check;
    ''')
