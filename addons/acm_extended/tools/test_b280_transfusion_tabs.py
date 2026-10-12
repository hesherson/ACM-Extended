"""Check native tab faces, authored frame bindings and decoded shipped textures.

The state expressions execute from production SQF. Engine hit testing remains
an Arma acceptance check; these tests cover the rectangular/grey style regression.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from test_menu_death_lifecycle import ROOT, adapt, execute, read


def class_block(source, name):
    start = re.search(rf'class {name}\s*:[^{{]+\{{', source).end()
    depth = 1
    for index in range(start, len(source)):
        depth += (source[index] == '{') - (source[index] == '}')
        if depth == 0:
            return source[start:index]
    raise AssertionError('unclosed class ' + name)


def test_both_tab_faces_leave_their_native_rounded_frames_visible():
    styles = (ROOT / 'addons/acm_extended/TransfusionMenu_Styles.hpp').read_text()
    config = (ROOT / 'addons/acm_extended/config.cpp').read_text()
    base = class_block(styles, 'ACME_TransfusionActionButton')
    for key in ('colorBackground', 'colorBackgroundActive', 'colorFocused'):
        assert f'{key}[] = {{0,0,0,0}};' in base
        assert f'{key}[] = {{0,0,0,0}};' in class_block(config, 'ACME_PreparedSetsButton')
        assert key not in class_block(styles, 'ACME_TransfusionTabButton')
    controller = read('updateTransfusionControls')
    assert '_ctrlSetsBtn ctrlSetBackgroundColor [0,0,0,0];' in controller
    chrome = (ROOT / 'addons/acm_extended/TransfusionMenu_Chrome.hpp').read_text()
    layout = read('layoutTransfusionMenu')
    ids = list(map(int, re.search(r'private _roundButtons = \[([^]]+)\]', layout).group(1).split(',')))
    for native_id in (86144, 86214):
        assert ids.count(native_id) == 1
        frame_id = 86410 + ids.index(native_id)
        assert f'idc = {frame_id};' in class_block(chrome, f'ACME_TxButton_{native_id}')
    assert '_tab ctrlSetBackgroundColor [0,0,0,0];' in layout
    assert '_tab setVariable ["ACME_txTabSelected",_selected];' in layout


@pytest.mark.parametrize('selected,hover,focus', [(False,False,False),(True,False,False),(False,True,False),(False,False,True)])
def test_both_tabs_use_the_same_grey_state_profile(selected, hover, focus):
    layout = read('layoutTransfusionMenu')
    source = layout[layout.index('        private _selectedFrame ='):layout.index('        private _enabled =')]
    source = source.replace('ctrlIDC _button', '_idc').replace('ctrlPosition _button', '[0,0,.2,.034]').replace('ctrlShown _button', 'true')
    execute(r'''
        private _button=profileNamespace;private _frame=missionNamespace;private _profile="";
        ACME_fnc_transfusionRoundedFrame={_profile=_this select 2;};
    ''' + f'''
        _button setVariable ["ACME_txTabSelected",{str(selected).lower()}];
        _button setVariable ["ACME_txRoundHover",{str(hover).lower()}];
        _button setVariable ["ACME_txRoundFocus",{str(focus).lower()}];
        {{private _idc=_x;
    ''' + adapt(source) + f'''
        [_profile=="{'tab_selected' if selected or hover or focus else 'tab'}","tab state lost its rounded neutral grey profile"]call _check;
        }}forEach[86144,86214];
    ''')


@pytest.mark.parametrize('profile', ['tab', 'tab_selected'])
def test_shipped_tab_slices_are_neutral_grey_with_transparent_corners(profile, tmp_path):
    folder = ROOT / 'addons/acm_extended/ui/transfusion'
    manifest = json.loads((folder / 'chrome_manifest.json').read_text())
    colors = manifest['profiles'][profile]
    for color in colors.values():
        assert color[1:3] == color[3:5] == color[5:7]
    assets = [asset for asset in manifest['assets'] if asset['profile'] == profile]
    assert {asset['part'] for asset in assets} == {'tl','top','tr','left','center','right','bl','bottom','br'}
    for asset in assets:
        path = folder / asset['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset['sha256']
        # Use the real loader for both opaque DXT1 strips and DXT5 corners.
        hemtt = os.environ.get('HEMTT_BINARY') or os.environ.get('HEMTT') or shutil.which('hemtt')
        assert hemtt, 'Pinned HEMTT is required to inspect shipped native textures'
        decoded = tmp_path / (path.stem + '.png')
        subprocess.run([hemtt, 'utils', 'paa', 'convert', str(path), str(decoded)], check=True, capture_output=True, text=True)
        with Image.open(decoded) as image:
            pixels = np.asarray(image.convert('RGBA'))
            rgb, alpha = pixels[:,:,:3], pixels[:,:,3]
        assert rgb.shape == (64,64,3) and alpha.shape == (64,64)
        # RGB565 compression may separate channels by up to one quantization step.
        visible = rgb[alpha >= 128].astype(np.int16)
        assert np.max(np.ptp(visible, axis=1)) <= 8
        assert np.any(alpha == 255)
        if asset['part'] in ('tl','tr','bl','br'):
            assert np.any(alpha == 0), 'opaque corner recreates the rectangular tab regression'
