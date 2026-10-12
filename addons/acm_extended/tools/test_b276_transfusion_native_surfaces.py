"""Native card geometry, read-only identity scope, and input isolation contracts.

The production SQF geometry and identity predicate execute in SQF-VM. Rendering,
font baselines, scrollbar offsets, and native pointer acceptance still need Arma.
"""
from pathlib import Path
import re

import pytest

from test_menu_death_lifecycle import execute

ROOT = Path(__file__).resolve().parents[3]
LAYOUT = (ROOT / "addons/acm_extended/functions/fn_layoutTransfusionMenu.sqf").read_text()
CONTROLLER = (ROOT / "addons/acm_extended/functions/fn_updateTransfusionControls.sqf").read_text()
DIALOG = (ROOT / "addons/circulation/TransfusionMenu_Dialog.hpp").read_text()
SURFACES = (ROOT / "addons/circulation/TransfusionMenu_Surfaces.hpp").read_text()


def authored_geometry():
    start = LAYOUT.index("        private _rowH = safeZoneH * 0.072;")
    end = LAYOUT.index('            [_card,"show",_show]', start)
    code = LAYOUT[start:end]
    # Only engine reads/handles are fixture boundaries. Keep authored row/clip math.
    code = code.replace("safeZoneH", "1").replace("pixelH", "0.001")
    code = code.replace("lbSize _list", "_rowCount")
    code = code.replace("ctrlScrollValues _list", "[_scrollValue,0]")
    code = re.sub(r"private _(card|caption|track|fill) = _display displayCtrl .*?;\n", "", code)
    code = code.replace("ctrlShown _list", "_visible")
    return code


@pytest.mark.parametrize("height", [.149, .187, .210, .235])
@pytest.mark.parametrize("rows", [0, 1, 2, 8])
@pytest.mark.parametrize("scroll", [0, .37, 1])
def test_real_native_card_rectangles_never_escape_the_owning_list(height, rows, scroll):
    code = authored_geometry()
    execute(f"""
        private _ly=.2;private _lh={height};private _rowCount={rows};
        private _scrollValue={scroll};private _visible=true;private _shown=0;
    """ + code + r'''
        if (_show) then {
            _shown=_shown+1;
            [_row>=0 && {_row<_rows},"card displayed an absent bag"] call _check;
            [_cy>=_ly-.001 && {_cy+_rowH<=_ly+_lh+.001},"card leaked beyond list clip"] call _check;
        };
    };
    [_shown<=4,"unbounded surface growth"] call _check;
    ''' + (r'[_shown==2,"two independently selectable Y bags no longer fit"] call _check;' if rows == 2 else ""))


def cache_predicate():
    start = LAYOUT.index("                private _sourceRow = _cardSelection")
    end = LAYOUT.index("                    _cache params", start)
    code = LAYOUT[start:end]
    return code.replace("_list lbValue _row", "_rowValue").replace("_list lbText _row", "_rowLabel")


@pytest.mark.parametrize("mutation,allowed", [
    ("", True), ('_part="rightarm";', False), ('_iv=false;', False),
    ('_site=1;', False), ('_patient=_medic;', False),
    ('(_cardSelection select 0) set [9,"replacement"];', False),
    ('_rowLabel="Blood (250 mL)";', False), ('_cache=[];', False),
])
def test_same_text_on_a_new_access_cannot_reuse_old_flow_or_warmer_metadata(mutation, allowed):
    execute(r'''
        private _part="leftarm";private _iv=true;private _site=0;
        private _listIDC=86004;private _rowValue=0;private _rowLabel="Saline (250 mL)";
        private _cardSelection=[[]];(_cardSelection select 0) set [9,"physical"];
        private _cache=[250,500,"LW Quantum · Warming...","",true,"Saline","physical",_rowLabel,[_patient,_part,_iv,_site]];
        private _allowed=false;
    ''' + mutation + cache_predicate() + r'''
        _allowed=true;
    };
    ''' + f'[_allowed isEqualTo {str(allowed).lower()},"stale card metadata escaped identity scope"] call _check;')


def test_decorations_are_predeclared_behind_native_controls_and_never_register_care():
    painter = LAYOUT.split("// B276: bounded predeclared decorations.", 1)[1]
    assert "ctrlCreate" not in painter
    assert "addPerFrameHandler" not in painter
    assert "ownerDispatch" not in painter
    assert "lbClear" not in painter and "lbSetCurSel" not in painter
    assert "_patient setVariable" not in painter
    assert 'enable = 0;' in SURFACES
    assert DIALOG.index('#include "TransfusionMenu_Surfaces.hpp"') < DIALOG.index("class Controls {")
    assert "class Hit:" not in SURFACES
    assert "TX_ROW_SURFACE(FluidCard3,86412);" in SURFACES
    assert "TX_ROW_SURFACE(PreparedInfusionCard3,86492);" in SURFACES


def test_native_button_states_and_list_treatment_routes_remain_authoritative():
    assert 'ctrlEnabled _button' in LAYOUT and 'ctrlShown _button' in LAYOUT
    assert 'ctrlPosition _button' in LAYOUT
    assert '"ACME_txSkinHover"' in LAYOUT and '"ACME_txSkinFocus"' in LAYOUT
    assert '"ACME_txSkinTint"' in LAYOUT
    assert '_ctrlSetsBtn ctrlSetBackgroundColor [0,0,0,0];' in CONTROLLER
    service = (ROOT / "addons/acm_extended/functions/fn_transfusionServicePaint.sqf").read_text()
    assert '_flush ctrlSetBackgroundColor [0,0,0,0];' in service
    assert '"ACME_txSkinTint"' in service
    assert 'call FUNC(TransfusionMenu_ToggleIVFlow)' in DIALOG
    assert 'call FUNC(TransfusionMenu_MoveBag)' in DIALOG


def test_every_row_and_topology_bracket_uses_the_authored_native_card_pitch():
    block = (ROOT / "addons/acm_extended/config.cpp").read_text().split(
        "class ACM_circulation_TransfusionMenu_Dialog {", 1)[1].split("// over-resuscitation", 1)[0]
    bracket = (ROOT / "addons/acm_extended/functions/fn_paintTransfusionYBracket.sqf").read_text()
    assert 'rowHeight = QUOTE(safeZoneH * 0.072);' in DIALOG
    assert 'rowHeight = "safeZoneH * 0.072";' in block
    assert 'private _rowH = safeZoneH * 0.072;' in bracket
    assert 'private _paneRowH = safeZoneH * 0.072;' in bracket
    assert 'ctrlScrollValues _list' in LAYOUT


def test_shipped_surfaces_are_native_alpha_textures_with_reproducible_sources():
    import importlib.util
    path = ROOT / "tools/build_transfusion_surfaces.py"
    spec = importlib.util.spec_from_file_location("acme_transfusion_surfaces", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, (size, radius, fill, border) in module.SPECS.items():
        asset = ROOT / f"addons/circulation/ui/transfusionmenu/surfaces/{name}_ca.paa"
        assert asset.read_bytes()[:2] == b"\x05\xff", f"{name}: DXT5 alpha lost"
        image = module.surface(size, radius, fill, border)
        assert image.getpixel((0, 0))[3] == 0
        assert image.getpixel((size[0] // 2, size[1] // 2))[3] == 255
        assert image.getextrema()[3] == (0, 255)
        assert fill >= 0 and fill <= border <= 255
    assert sum(p.stat().st_size for p in module.DEST.glob("*.paa")) < 100_000
