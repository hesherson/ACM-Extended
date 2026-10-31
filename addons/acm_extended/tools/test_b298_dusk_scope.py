"""Dusk restyle retains native authority, geometry, offline wiring and readable material."""
import re
import subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[3]
BASE='0d1e5fc04a11514ed06ca98d1188699d0c78ea4a'
B298='5a5e484acabbc6c0bf9424328c5807ae962ea6d4'
def published(path):
    return subprocess.check_output(['git','show',B298+':'+path],cwd=ROOT)
FRONT=ROOT/'frontend/medical-ui'


def test_restyle_cannot_rewrite_card_logic_handlers_or_geometry():
    original=subprocess.check_output(['git','show',BASE+':frontend/medical-ui/App.jsx'],cwd=ROOT,text=True)
    current=published('frontend/medical-ui/App.jsx').decode().replace("'--color-clinical':`rgba(","color:`rgba(").replace('className="acme-medical-surface" ','')
    assert current==original
    for name in ['bridge.mjs','layout.mjs']:
        assert published('frontend/medical-ui/'+name)==subprocess.check_output(['git','show',BASE+':frontend/medical-ui/'+name],cwd=ROOT)


def test_all_native_menu_runtime_and_medical_artwork_are_outside_restyle():
    paths=subprocess.check_output(['git','diff','--name-only',BASE,B298,'--','addons'],cwd=ROOT,text=True).splitlines()
    allowed={'addons/acm_extended/ui/react/index.html','addons/acm_extended/functions/fn_initForkStartupRuntime.sqf','addons/main/script_build.hpp'}
    assert not [p for p in paths if p not in allowed and '/tools/' not in p]
    original=subprocess.check_output(['git','show',BASE+':addons/acm_extended/functions/fn_initForkStartupRuntime.sqf'],cwd=ROOT,text=True)
    assert published('addons/acm_extended/functions/fn_initForkStartupRuntime.sqf').decode().replace('B298','B297')==original


def rgb(value):
    if value.startswith('#'):
        return [int(value[i:i+2],16)/255 for i in [1,3,5]]+[1]
    return [float(x)/255 for x in re.findall(r'[\d.]+',value)[:3]]+[float(re.findall(r'[\d.]+',value)[3])]


def light(color):
    return sum(w*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4) for w,v in zip([.2126,.7152,.0722],color))


def contrast(a,b):
    x,y=sorted([light(a),light(b)]);return (y+.05)/(x+.05)


TOKENS=dict(re.findall(r'(--[\w-]+):\s*([^;]+);',(FRONT/'tokens.css').read_text()))
@pytest.mark.parametrize('surface',[k for k in TOKENS if k.startswith('--color-card-') or k in ['--color-piggyback-card','--color-piggyback-selected']])
def test_medical_labels_stay_readable_over_black_midgrey_and_white(surface):
    fill=rgb(TOKENS[surface])
    for backdrop in [0,.5,1]:
        background=[v*fill[3]+backdrop*(1-fill[3]) for v in fill[:3]]
        for token in ['--color-muted','--color-ink','--color-piggyback','--color-warming','--color-native-label']:
            assert contrast(rgb(TOKENS[token])[:3],background)>=4.5,(surface,backdrop,token)
        assert contrast(rgb(TOKENS['--color-focus'])[:3],background)>=3


def test_backdrop_capability_is_explicit_and_not_a_claim_to_blur_the_game_world():
    css=(FRONT/'style.css').read_text();app=(FRONT/'App.jsx').read_text()
    assert '[data-acme-backdrop="internal"] .card' in css
    assert 'data-acme-backdrop' not in app
    assert 'color-scheme: normal' in css
    assert 'animation:' not in css.split('@media')[0] and 'transition:' not in css.split('@media')[0]
    assert 'var(--color-clinical' in css and 'overflow-x: clip' in css
