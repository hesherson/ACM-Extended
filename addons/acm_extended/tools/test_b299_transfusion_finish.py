"""Current B299 contracts, separate from historical B296/B298 recovery provenance."""
import importlib.util
import json
import subprocess
from pathlib import Path
import pytest
from test_menu_death_lifecycle import ROOT,execute,read
from test_b275_transfusion_tags_knowledge import fn

BASE='5a5e484acabbc6c0bf9424328c5807ae962ea6d4'
B299='2e463fd1457905fd1f6bb087bbc87991e08a36ae'

def test_native_changes_are_only_authorized_acme_transfusion_surfaces():
    changed=subprocess.check_output(['git','diff','--name-only',BASE,B299,'--','addons'],cwd=ROOT,text=True).splitlines()
    allowed={'addons/acm_extended/functions/fn_reactMedicalSnapshot.sqf',
             'addons/acm_extended/functions/fn_reactMedicalMessage.sqf',
             'addons/acm_extended/functions/fn_updateTransfusionAccessHotspots.sqf',
             'addons/acm_extended/functions/fn_transfusionTagLeader.sqf',
             'addons/acm_extended/functions/fn_initForkStartupRuntime.sqf',
             'addons/acm_extended/ui/react/index.html','addons/main/script_build.hpp'}
    assert all(p in allowed or p.startswith('addons/acm_extended/ui/transfusion/') or '/tools/' in p for p in changed)
    assert subprocess.check_output(['git','diff',BASE,B299,'--','addons/gui','addons/circulation','addons/acm_extended/ui/iv'],cwd=ROOT)==b''

@pytest.mark.parametrize('left',[False,True])
def test_live_flag_box_hangs_at_outer_end_with_neck_and_site_dot(left):
    source=read('updateTransfusionAccessHotspots')
    block=source[source.index('_placedLabels pushBack (+_rect)'):source.index('\n        };\n    };\n    [_label,"show"')]
    block=block.replace('pixelW','.001').replace('pixelH','.002')
    execute(fn('transfusionTagLeader')+r'''
      private _positions=createHashMap;
      ACME_fnc_transfusionUiSet={params ["_ctrl","_op","_value"];if (_op=="position") then {_positions set [_ctrl,_value];};};
      private _label="label";private _tagHit="hit";private _leader="leader";private _dot="dot";
      private _borders=["top","left","bottom","right"];private _placedLabels=[];
      private _anchor=[.45,.4,.05,.06];private _rect=[.65,.3,.13,.03];
      private _labelW=.10;private _flagOverhang=.03;
    '''+'private _left='+str(left).lower()+';\n'+block+r'''
      private _box=_positions get "label";private _top=_positions get "top";
      private _line=_positions get "leader";private _point=_positions get "dot";
      [abs ((_top select 2)-.13)<.00001,"rail lost neck"] call _check;
      private _junction=if (_left) then {.78} else {.65};
      private _boxInner=if (_left) then {(_box select 0)+(_box select 2)} else {_box select 0};
      [abs (abs (_boxInner-_junction)-.03)<.00001,"box starts at diagonal junction"] call _check;
      private _site=if (_left) then {.45} else {.50};
      [abs ((_point select 0)+.0015-_site)<.00001 && {abs ((_point select 1)+.003-.4)<.00001},"dot not centered on line base"] call _check;
      [(_positions get "hit") isEqualTo _box,"label click area changed"] call _check;
    ''')

def test_outline_is_slightly_thinner_and_original_medical_art_is_unchanged():
    spec=importlib.util.spec_from_file_location('outline',ROOT/'tools/generate_transfusion_access_outlines.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    from PIL import Image,ImageDraw
    image=Image.new('RGBA',(32,32));ImageDraw.Draw(image).rectangle((12,12,20,20),fill='white')
    alpha=module.contour(image).getchannel('A')
    assert alpha.getpixel((11,15))==255
    assert 64<alpha.getpixel((10,15))<128
    assert alpha.getpixel((9,15))==0 and alpha.getpixel((15,15))==0
    manifest=json.loads((ROOT/'addons/acm_extended/ui/transfusion/access/manifest.json').read_text())
    assert manifest['radiusPixels']==1.4


def test_first_paint_requires_bundled_font_and_engine_measurement():
    app=(ROOT/'frontend/medical-ui/App.jsx').read_text()
    assert "document.fonts.load" in app and 'context.measureText(FONT_PROBE)' in app
    assert 'if (!snapshot.state || !calibrated) return;' in app
    assert 'requestAnimationFrame(()=>store.painted())' in app
    assert 'renderCards && snapshot.state?.cards.map' in app
    assert 'const renderCards=!needsFont || fontReady;' in app
    assert '"Hg0123456789" getTextWidth ["RobotoCondensed",safeZoneH * 0.018]' in read('reactMedicalSnapshot')
    assert 'addPerFrameHandler' not in read('reactMedicalSnapshot')


def test_window_material_has_warm_reflection_without_global_or_clinical_changes():
    spec=importlib.util.spec_from_file_location('chrome',ROOT/'tools/generate_transfusion_chrome.py')
    module=importlib.util.module_from_spec(spec)
    exec(subprocess.check_output(['git','show',B299+':tools/generate_transfusion_chrome.py'],cwd=ROOT,text=True),module.__dict__)
    parts=module.window_material(module.render_parts(*module.PROFILES['window']))
    a=parts['center'].getpixel((2,2));b=parts['center'].getpixel((60,60))
    assert a[0]>b[0] and a[1]>b[1] and a[3]==b[3]==255
    for part in parts.values():assert part.size==(64,64)
    assert parts['tl'].getpixel((0,0))[3]==0
    for name in ('layoutTransfusionMenu','updateTransfusionCards','transfusionCardData','reactMedicalTick','reactMedicalOpen'):
        path='addons/acm_extended/functions/fn_'+name+'.sqf'
        assert subprocess.check_output(['git','show',B299+':'+path],cwd=ROOT)==subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)

@pytest.mark.parametrize('profile,expected',[('panel',(24,25,28)),('selected',(48,50,57)),('button',(32,33,37))])
def test_shipped_paa_contains_current_material_instead_of_old_converter_output(profile,expected,tmp_path):
    import os,shutil
    from PIL import Image
    hemtt=os.environ.get('HEMTT_BINARY') or shutil.which('hemtt')
    assert hemtt,'HEMTT is required to inspect shipped material'
    source=ROOT/f'addons/acm_extended/ui/transfusion/{profile}_center_ca.paa'
    output=tmp_path/(profile+'.png')
    subprocess.run([hemtt,'utils','paa','convert',str(source),str(output),'--no-color'],check=True,capture_output=True)
    pixel=Image.open(output).convert('RGBA').getpixel((32,32))
    assert all(abs(a-b)<=5 for a,b in zip(pixel[:3],expected)),pixel
    assert pixel[3]==255

@pytest.mark.parametrize('route,session,menu,expected',[('[]','ui:7:1','',True),('["bad"]','ui:7:1','',False),('[]','old','',False),('[]','ui:7:1','bag-actions',True)])
def test_calibration_failure_returns_only_matching_bound_pane_to_native(route,session,menu,expected):
    from test_b293_react_bridge import setup
    # Match setup's actual session, retaining an explicit wrong-session case.
    code=setup()
    import re
    current=re.search(r'\["ACME_reactSession","([^"]+)"\]',code)
    assert current
    session=current[1] if session=='ui:7:1' else session
    execute(code+f'''
        private _fallbacks=0;ACME_fnc_reactMedicalFallback={{_fallbacks=_fallbacks+1;}};
        _view setVariable ["ACME_txActionMenu","{menu}"];
        _decoded set ["operation","fallback"];_decoded set ["route",{route}];_decoded set ["session","{session}"];
        [_browser,false,"packet"] call ACME_fnc_reactMedicalMessage;
        [_fallbacks=={1 if expected else 0} && {{count _selections==0}},"fallback escaped its presentation session"] call _check;
    ''')
