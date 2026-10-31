"""Execute native/browser handoff and geometry; pin silhouette masks and ACE scope."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import pytest
from test_b293_react_bridge import setup, function, tick_setup
from test_menu_death_lifecycle import ROOT, execute


def test_frame_rate_updates_do_not_recommit_browser_geometry_or_flood_snapshots():
    execute(tick_setup()+r'''
        private _positions=[];
        ACME_fnc_transfusionUiSet={params ["_c","_property","_value"];
            if (_property=="position") then {_positions pushBack _value;};true};
        ACME_fnc_reactMedicalSnapshot={createHashMapFromArray [["volume",_nowTime]]};
        for "_i" from 0 to 99 do {
            _nowTime=10+_i*.004;[_view] call ACME_fnc_reactMedicalTick;
        };
        [count _positions==1,"browser geometry recommitted at frame rate"] call _check;
        [count _packets<=4 && {count _packets>=3},"snapshot delivery is not bounded at 10Hz"] call _check;
        _view setVariable ["ACME_txCardLayout",createHashMapFromArray [[86004,[[.1,.2,.212,.22],2,.1065,0,true]]]];
        [_view] call ACME_fnc_reactMedicalTick;
        [count _positions==2,"real viewport change was ignored"] call _check;
    ''')


def test_browser_cannot_replace_native_cards_until_first_paint():
    execute(tick_setup()+r'''
        _view setVariable ["ACME_reactPainted",false];_view setVariable ["ACME_reactDeadline",20];
        [_view] call ACME_fnc_reactMedicalTick;
        [!(_view getVariable "ACME_reactActive") && {!_browserShown} && {!_enabled},"unpainted page hid native cards"] call _check;
        _decoded set ["operation","painted"];_decoded set ["route",[]];
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        _nowTime=10.2;[_view] call ACME_fnc_reactMedicalTick;
        [_view getVariable "ACME_reactActive" && {_browserShown} && {_enabled},"painted page never acquired its pane"] call _check;
        [count _selections==0,"paint acknowledgment performed treatment"] call _check;
    ''')


def test_page_that_never_paints_returns_to_native_without_reload():
    execute(tick_setup()+r'''
        _view setVariable ["ACME_reactPainted",false];_view setVariable ["ACME_reactDeadline",9];
        [_view] call ACME_fnc_reactMedicalTick;
        [_view getVariable "ACME_reactFailed" && {!(_view getVariable "ACME_reactActive")},"failed paint trapped the pane"] call _check;
        [count _packets==0 && {!_closed} && {count _waits==0},"paint failure reloaded or scheduled a menu"] call _check;
    ''')


@pytest.mark.parametrize('route,ready,sent', [('[]',True,0),('[1]',True,1),('[]',False,1)])
def test_paint_requires_empty_route_ready_handshake_and_a_sent_snapshot(route,ready,sent):
    execute(setup()+f'''
        _view setVariable ["ACME_reactPainted",false];
        _view setVariable ["ACME_reactReady",{str(ready).lower()}];_view setVariable ["ACME_reactStateSequence",{sent}];
        _decoded set ["operation","painted"];_decoded set ["route",{route}];
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [!(_view getVariable "ACME_reactPainted"),"invalid paint acknowledgment accepted"] call _check;
    ''')


def test_ace_surfaces_and_original_medical_artwork_unchanged():
    changed=subprocess.check_output(['git','diff','--name-only','4ef4d3fdcdd4cb6c49bdb27a3b46fcc0641bb824','--','addons/gui','addons/circulation','addons/acm_extended/ui/iv'],cwd=ROOT,text=True)
    assert not changed.strip(), changed
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    original=subprocess.check_output(['git','show','4ef4d3fdcdd4cb6c49bdb27a3b46fcc0641bb824:addons/acm_extended/config.cpp'],cwd=ROOT,text=True)
    assert config.replace('            class reactMedicalRect {};\n','')==original
    source=(ROOT/'addons/acm_extended/functions/fn_updateTransfusionAccessHotspots.sqf').read_text()
    assert '[1,1,1,0.08]' not in source and '[0.20,0.65,0.20,0.22]' not in source
    assert '_outline ctrlEnable false;' in source
    assert '87300 + _siteIndex' in source
    assert '_tw + _flagOverhang' in source
    assert '_labelW + _flagOverhang' in source
    assert '_placedLabels pushBack (+_rect)' in source


MANIFEST=ROOT/'addons/acm_extended/ui/transfusion/access/manifest.json'
@pytest.mark.parametrize('asset',json.loads(MANIFEST.read_text())['assets'],ids=lambda a:a['key'])
def test_outline_source_and_packed_asset_provenance(asset):
    assert hashlib.sha256((ROOT/asset['source']).read_bytes()).hexdigest()==asset['sourceSha256']
    assert hashlib.sha256((MANIFEST.parent/asset['file']).read_bytes()).hexdigest()==asset['sha256']
    assert asset['size']==[512,512]


def test_contour_tracks_icon_alpha_without_filling_its_bounding_box():
    from PIL import Image,ImageDraw
    spec=importlib.util.spec_from_file_location('outlines',ROOT/'tools/generate_transfusion_access_outlines.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=Image.new('RGBA',(64,64));draw=ImageDraw.Draw(source);draw.line([(15,10),(15,45),(45,45)],fill='white',width=5)
    alpha=module.contour(source).getchannel('A')
    assert alpha.getpixel((15,25))==0 and alpha.getpixel((10,10))==0 and alpha.getpixel((45,10))==0
    assert alpha.getpixel((11,25))>0
    assert sum(v>0 for v in alpha.get_flattened_data())<500

@pytest.mark.parametrize('width,height',[(1440,1080),(1920,1080),(2520,1080),(3840,1080)])
def test_full_flag_overhang_is_inside_map_and_reserved_against_other_tags(width,height):
    from test_b275_transfusion_tags_knowledge import fn,read
    execute(fn('transfusionTagRect')+fn('transfusionTagLeader')+f'''
        private _pw=1/{width};private _ph=1/{height};
    '''+r'''
        private _bounds=[.5-1/6.8,.5-1/3.5,1/3.4,1/1.75];
        _bounds params ["_ox","_oy","_ow","_oh"];
        private _dw=_ow;private _dh=_ow*(_ph/_pw);
        if (_dh>_oh) then {_dh=_oh;_dw=_oh*(_pw/_ph);};
        private _dx=_ox+(_ow-_dw)/2;private _dy=_oy+(_oh-_dh)/2;
        private _placed=[];
        {
            _x params ["_key","_part","_site","_idc","_input","_uv"];
            _uv params ["_u","_v","_uw","_uh"];
            private _anchor=[_dx+_u*_dw-6*_pw,_dy+_v*_dh-6*_ph,_uw*_dw+12*_pw,_uh*_dh+12*_ph];
            private _left=(_anchor select 0)+(_anchor select 2)/2<_dx+_dw/2;
            private _above=_part=="head" || {_v<.35} || {!_left && {_v<.55}};
            private _tail=(_dw*.035) max (10*_pw);private _labelW=_dw*.18;
            private _flag=[_anchor,[_labelW+_tail,(_dh*.035) max (14*_ph)],_bounds,_placed,3*_ph,_left,_above] call ACME_fnc_transfusionTagRect;
            [count _flag==4,"full flag could not fit"] call _check;
            if (count _flag==4) then {
                _flag params ["_x","_y","_w","_h"];
                [_x>=_ox && {_x+_w<=_ox+_ow+.00001} && {_y>=_oy} && {_y+_h<=_oy+_oh+.00001},"flag overhang escaped map"] call _check;

                private _label=[_x+(if (_left) then {_tail} else {0}),_y,_labelW,_h];
                private _line=[_anchor,_label,_left] call ACME_fnc_transfusionTagLeader;
                private _start=if (_left) then {[(_line select 0)+(_line select 2),(_line select 1)+(_line select 3)]} else {[_line select 0,_line select 1]};
                [abs ((_start select 1)-(_anchor select 1))<.000001,"leader starts midway down icon rectangle"] call _check;
                _placed pushBack _flag;
            };
        } forEach (''' + read('skSiteGeometry') + r''');
        [count _placed==19,"clustered flag sites disappeared"] call _check;
    ''')
