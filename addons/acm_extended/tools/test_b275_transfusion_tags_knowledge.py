"""B275 native-map tag geometry and observer-specific dogtag knowledge.

Runs production geometry/knowledge in SQF-VM. UI rendering remains an Arma check.
"""
import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read


def fn(name):
    source = adapt(read(name))
    # These fixtures use distinct namespaces for native object identities.
    source = source.replace('_observer != ACE_player', '_observer isNotEqualTo ACE_player')
    source = source.replace('!isNull (_x param [0, objNull])', '!((_x param [0, objNull]) isEqualTo objNull)')
    source = source.replace('!isNull (_x param [1, objNull])', '!((_x param [1, objNull]) isEqualTo objNull)')
    return 'ACME_fnc_' + name + '={' + source + '};'


@pytest.mark.parametrize('width,height', [(1440,1080),(1920,1080),(2520,1080),(3840,1080)])
def test_all_native_sites_have_separate_outward_tags_with_seamless_top_edges(width,height):
    execute(fn('transfusionTagRect') + fn('transfusionTagLeader') + '''
      ACME_fnc_skSiteGeometry={''' + read('skSiteGeometry') + '''};
      private _outer=[.5-1/6.8,.5-1/3.5,1/3.4,1/1.75];
      _outer params ["_ox","_oy","_ow","_oh"];
    ''' + f'''
      private _pixelW=1/{width};private _pixelH=1/{height};
    ''' + '''
      private _dw=_ow;private _dh=_ow*(_pixelH/_pixelW);
      if (_dh>_oh) then {_dh=_oh;_dw=_oh*(_pixelW/_pixelH);};
      private _dx=_ox+(_ow-_dw)/2;private _dy=_oy+(_oh-_dh)/2;
      private _placed=[];
      {
        _x params ["_key","_part","_site","_idc","_input","_uv"];
        _uv params ["_u","_v","_uw","_uh"];
        private _anchor=[_dx+_u*_dw-6*_pixelW,_dy+_v*_dh-6*_pixelH,_uw*_dw+12*_pixelW,_uh*_dh+12*_pixelH];
        private _left=(_anchor select 0)+(_anchor select 2)/2<_dx+_dw/2;
        private _above=(_part=="head") || {_v<.35} || {!_left && {_v<.55}};
        private _size=[_dw*.18,(_dh*.035) max (14*_pixelH)];
        private _rect=[_anchor,_size,_outer,_placed,3*_pixelH,_left,_above] call ACME_fnc_transfusionTagRect;
        [count _rect==4,"occupied tag vanished in native geometry"] call _check;
        if (count _rect==4) then {
          _rect params ["_rx","_ry","_rw","_rh"];
          [_rx>=_ox && {_ry>=_oy} && {_rx+_rw<=_ox+_ow+.000001} && {_ry+_rh<=_oy+_oh+.000001},"tag outside native map bounds"] call _check;
          [if (_left) then {_rx+_rw<(_anchor select 0)} else {_rx>(_anchor select 0)+(_anchor select 2)},"tag moved inward over body"] call _check;
          private _overlap=_placed findIf {_rx<(_x select 0)+(_x select 2) && {_rx+_rw>(_x select 0)} && {_ry<(_x select 1)+(_x select 3)} && {_ry+_rh>(_x select 1)}};
          [_overlap<0,"bilateral or clustered tags overlap"] call _check;
          private _line=[_anchor,_rect,_left] call ACME_fnc_transfusionTagLeader;
          private _corner=if (_left) then {[_line select 0,_line select 1]} else {[(_line select 0)+(_line select 2),(_line select 1)+(_line select 3)]};
          [abs ((_corner select 0)-(if (_left) then {_rx+_rw} else {_rx}))<.000001 && {abs ((_corner select 1)-_ry)<.000001},"diagonal does not meet top border corner"] call _check;
          [(_line select 2)>0 && {abs (_line select 3)>0},"outward leader is not diagonal"] call _check;
          _placed pushBack _rect;
        };
      } forEach (call ACME_fnc_skSiteGeometry);
      [count _placed==19,"not every native peripheral/IO/EJ site mapped"] call _check;
    ''')


@pytest.mark.parametrize('blood',['A+','A-','B+','B-','AB+','AB-','O+','O-'])
def test_dogtag_knowledge_requires_the_local_observer_and_exact_patient_instance(blood):
    execute(fn('knownBloodType') + fn('rememberDogtagBloodType') + f'''
      _patient setVariable ["ace_dogtags_dogtagData",["Patient","SSN","{blood}"]];
      [[_medic,_patient] call ACME_fnc_knownBloodType=="???","public identity was treated as knowledge"] call _check;
      [[_medic,_patient,["Patient","SSN","{blood}"]] call ACME_fnc_rememberDogtagBloodType,"local completed view not remembered"] call _check;
      [[_medic,_patient] call ACME_fnc_knownBloodType=="{blood}","inspection not available after menu lifecycle"] call _check;
      [[_medic,missionNamespace] call ACME_fnc_knownBloodType=="???","replacement patient inherited old knowledge"] call _check;
      ACE_player=missionNamespace;
      [[ACE_player,_patient] call ACME_fnc_knownBloodType=="???","another medic inherited knowledge"] call _check;
      [!([_medic,_patient,["Patient","SSN","{blood}"]] call ACME_fnc_rememberDogtagBloodType),"remote observer learned local knowledge"] call _check;
      ACE_player=_medic;
      [[_medic,_patient] call ACME_fnc_knownBloodType=="{blood}","other observer cleared recorded read"] call _check;
      [count (uiNamespace getVariable ["ACME_dogtagBloodKnowledge",[]])==1,"duplicate record"] call _check;
    ''')


@pytest.mark.parametrize('data',['[]','["N","S"]','["N","S",3]','["N","S","unknown"]'])
def test_malformed_dogtag_data_does_not_establish_blood_type_knowledge(data):
    execute(fn('knownBloodType') + fn('rememberDogtagBloodType') + f'''
      [!([_medic,_patient,{data}] call ACME_fnc_rememberDogtagBloodType),"invalid ABO accepted"] call _check;
      [[_medic,_patient] call ACME_fnc_knownBloodType=="???","invalid display invented blood type"] call _check;
    ''')


@pytest.mark.parametrize('kind,want',[('Blood','B'),('FreshBlood','B'),('ACME_SalineY','NS'),('Plasma','P'),('Saline','NS'),('TranexamicAcid','TXA'),('CalciumChloride','Ca'),('CalciumGluconate','Ca'),('Propofol','PRO')])
def test_bag_tags_keep_compact_recognizable_fluid_shorthand(kind,want):
    execute(fn('transfusionFluidShorthand') + f'[["{kind}"] call ACME_fnc_transfusionFluidShorthand=="{want}","wrong native bag shorthand"] call _check;')


def test_live_renderer_only_shows_tags_for_nonempty_bags_and_reuses_native_artwork():
    source=read('updateTransfusionAccessHotspots')
    assert '_showLabel = _has && {_text != ""}' in source
    assert 'call ACME_fnc_transfusionAccessLabel' in source
    assert '["RscLine", 87030 + _siteIndex]' in source
    assert 'call ACME_fnc_transfusionTagLeader' in source
    assert '[_tx,_ty,_tw,pixelH]' in source
    assert 'call ACME_fnc_piggybackLine' in source
    assert 'call ACME_fnc_ejTexturePath' in source
    assert 'ctrlSetAngle' not in source and 'drawLine' not in source
    assert '[_part, !_isIO, _site]' in source


@pytest.mark.parametrize('iv',[True,False])
def test_empty_and_other_access_bags_do_not_label_the_selected_access(iv):
    execute(fn('transfusionFluidShorthand') + fn('transfusionAccessLabel') + f'''
      private _iv={str(iv).lower()};
      private _bags=[["Blood",0,0,0,_iv],["Saline",.001,0,0,_iv],["ACME_Empty",500,0,0,_iv],["ACME_EmptySaline",500,0,0,_iv],["Plasma",500,0,0,!_iv]];
      [[_bags,[],_iv,0] call ACME_fnc_transfusionAccessLabel=="","empty or other-route bag produced a tag"] call _check;
      _bags pushBack ["Blood",250,0,0,_iv];_bags pushBack ["ACME_SalineY",500,0,0,_iv];
      [[_bags,[],_iv,0] call ACME_fnc_transfusionAccessLabel=="B+NS","occupied connected line shorthand wrong"] call _check;
      if (_iv) then {{[[_bags,[],true,1] call ACME_fnc_transfusionAccessLabel=="","other IV site inherited tag"] call _check;}};
    ''')


def test_infusion_label_resolves_only_matching_bag_uid_and_deduplicates_carriers():
    execute(fn('transfusionFluidShorthand') + fn('transfusionAccessLabel') + '''
      private _txa=[];_txa resize 24;_txa set [11,"TranexamicAcid"];_txa set [23,"secondary"];
      private _calcium=[];_calcium resize 24;_calcium set [11,"CalciumGluconate"];_calcium set [23,"other-site"];
      private _bags=[["Saline",400,0,1,true,-1,500,-1,"primary"],["Saline",80,0,1,true,-1,100,-1,"secondary"]];
      [[_bags,[_txa,_calcium],true,1] call ACME_fnc_transfusionAccessLabel=="NS+TXA","infusion bag got carrier or another site's medicine label"] call _check;
      _bags pushBack ["Saline",200,0,1,true,-1,500,-1,"extra"];
      [[_bags,[_txa,_calcium],true,1] call ACME_fnc_transfusionAccessLabel=="NS+TXA","duplicate native fluid label"] call _check;
    ''')


def test_dogtag_read_hook_waits_for_native_display_and_never_publishes_knowledge():
    source=(ROOT/'addons/core/overrides/fnc_checkDogtag.sqf').read_text()
    assert source.index('call ACEFUNC(dogtags,showDogtag)') < source.index('call ACME_fnc_rememberDogtagBloodType')
    assert 'uiNamespace getVariable [QACEGVAR(dogtags,tag), displayNull]' in source
    assert 'DOGTAG_SHOW_DELAY] call CBA_fnc_waitAndExecute' in source
    for name in ['knownBloodType','rememberDogtagBloodType']:
        assert 'ace_dogtags_dogtagData' not in read(name)
        assert ', true]' not in read(name)
