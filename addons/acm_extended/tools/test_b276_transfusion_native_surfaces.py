"""Native card geometry, read-only identity scope, and input isolation contracts.

The production SQF geometry and identity predicate execute in SQF-VM. Rendering,
font baselines, scrollbar offsets, and native pointer acceptance still need Arma.
"""
from pathlib import Path
import re

import pytest

from test_menu_death_lifecycle import execute, adapt
from test_b156_procedure_supplies import primitives

ROOT = Path(__file__).resolve().parents[3]
LAYOUT = (ROOT / "addons/acm_extended/functions/fn_layoutTransfusionMenu.sqf").read_text()
CONTROLLER = (ROOT / "addons/acm_extended/functions/fn_updateTransfusionControls.sqf").read_text()
DIALOG = (ROOT / "addons/circulation/TransfusionMenu_Dialog.hpp").read_text()
SURFACES = (ROOT / "addons/circulation/TransfusionMenu_Surfaces.hpp").read_text()
CARDS = (ROOT / "addons/acm_extended/functions/fn_updateTransfusionCards.sqf").read_text()
CHROME = (ROOT / "addons/acm_extended/TransfusionMenu_Chrome.hpp").read_text()
STYLES = (ROOT / "addons/acm_extended/TransfusionMenu_Styles.hpp").read_text()
DATA = (ROOT / "addons/acm_extended/functions/fn_transfusionCardData.sqf").read_text()


def authored_geometry():
    # B277 replaces four passive overlays with a bounded two-card fluid pool.
    # Execute its actual viewport and authored rectangle arithmetic; original
    # native lists remain the custody and selection model behind the cards.
    capacity = re.search(r'private _panes = \[\[86004,(\d+),', CARDS).group(1)
    start = CARDS.index("        private _gap = safeZoneH * 0.007;")
    end = CARDS.index('        private _offsetKey =', start)
    sizing = CARDS[start:end].replace("safeZoneH", "1")
    rectangle = re.search(r'private _cardRect = \[[^;]+;', CARDS).group()
    window = (ROOT / "addons/acm_extended/functions/fn_transfusionCardWindow.sqf").read_text()
    return f"ACME_test_window={{" + window + "};" + f"private _capacity={capacity};private _h=_lh;private _py=_ly;private _px=0;private _w=.2;" + sizing + r'''
        private _window=[_rowCount,_capacity,floor ((_rowCount-_capacity) max 0)*_scrollValue] call ACME_test_window;
        private _rows=_rowCount;
        for "_slot" from 0 to (_capacity-1) do {
            private _row=(_window select 1) select _slot;
            private _show=_visible && {_row>=0};
    ''' + rectangle + 'private _cy=_cardRect select 1;'


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
    # Exercise the production guard before any temperature/flow metadata read.
    # B277 recomputes card metadata instead of borrowing a previous label cache.
    end = DATA.index('    ([_patient,_part,_bag] call ACME_fnc_transfusionBagPresentation)')
    code = DATA[:end] + '_metadataAdmitted=true;};'
    replacements = {
        '_list lbText _row': '_rowLabel', '_list lbColor _row': '[1,1,1,1]',
        '_list lbPictureRight _row': '\"native-vial\"', '_list lbPicture _row': '\"native-fluid\"',
        '_list lbValue _row': '_rowValue', 'ctrlIDC _list': '_listIDC',
    }
    for before, after in sorted(replacements.items(), key=lambda item: -len(item[0])):
        code = code.replace(before, after)
    return primitives(adapt(code))


@pytest.mark.parametrize("mutation,allowed", [
    ("", True), ('_part="rightarm";', False), ('_iv=false;', False),
    ('_site=1;', False), ('_patient=_medic;', False),
    ('(_cardSelection select 0) set [9,"replacement"];', False),
    ('_rowLabel="Blood (250 mL)";', False), ('_cache=[];', False),
])
def test_same_text_on_a_new_access_cannot_reuse_old_flow_or_warmer_metadata(mutation, allowed):
    # Empty/changed old caches now permit a fresh metadata read for the same
    # physical bag; they never authorize reuse of the old warming/flow record.
    fresh_same_bag = mutation in ('_rowLabel="Blood (250 mL)";', '_cache=[];')
    execute(r'''
        private _part="leftarm";private _iv=true;private _site=0;
        private _list=missionNamespace;
        private _listIDC=86004;private _rowValue=0;private _rowLabel="Saline (250 mL)";
        private _cardSelection=[["Saline",250,1,0,true,-1,500,-1,0,"physical"]];
        private _cache=[250,500,"LW Quantum · Warming...","",true,"Saline","physical",_rowLabel,[_patient,_part,_iv,_site]];
        private _mapDefault={params["_map","_args"];_args params["_key","_default"];if(_key in _map)then{_map get _key}else{_default}};
        _patient setVariable["ACM_circulation_IV_Bags",createHashMapFromArray[["leftarm",[["Saline",250,1,0,true,-1,500,-1,"physical"]]]]];
        private _metadataAdmitted=false;
    ''' + mutation + r'''
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Target",_patient];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_BodyPart",_part];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_SelectIV",_iv];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_AccessSite",_site];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selection_IVBags",_cardSelection];
    ''' + 'private _scope={' + cache_predicate() + '};[_list,0]call _scope;' +
        f'[_metadataAdmitted isEqualTo {str(allowed or fresh_same_bag).lower()},"stale card metadata escaped physical access scope"] call _check;')
    assert '_cache' not in DATA
    assert 'private _thermal = "";' in DATA
    assert '[_patient,_part,_bag] call ACME_fnc_transfusionBagPresentation' in DATA


def test_decorations_are_predeclared_behind_native_controls_and_never_register_care():
    painter = (ROOT / "addons/acm_extended/functions/fn_transfusionRoundedFrame.sqf").read_text()
    assert "ctrlCreate" not in painter
    assert "addPerFrameHandler" not in painter
    assert "ownerDispatch" not in painter
    assert "lbClear" not in painter and "lbSetCurSel" not in painter
    assert "_patient setVariable" not in painter
    assert "_piece ctrlEnable false;" in painter
    patch = (ROOT / "addons/acm_extended/config.cpp").read_text().split("class ACM_circulation_TransfusionMenu_Dialog {", 1)[1]
    assert patch.index('#include "TransfusionMenu_Chrome.hpp"') < patch.index("class Controls {")
    assert "class Hit:" not in CHROME
    assert "class ACME_TxButton_86006: ACME_TransfusionRoundedFrame" in CHROME
    assert "class ACME_TxDetails: ACME_TransfusionRoundedFrame" in CHROME
    # Card hits are the bounded interactive layer and resolve custody before
    # delegating the existing native selection; decorations remain disabled.
    select = (ROOT / "addons/acm_extended/functions/fn_transfusionCardSelect.sqf").read_text()
    assert "call ACME_fnc_transfusionCardResolve" in select
    assert "_list lbSetCurSel _row;" in select
    assert "ownerDispatch" not in select


def test_native_button_states_and_list_treatment_routes_remain_authoritative():
    assert 'ctrlEnabled _button' in LAYOUT and 'ctrlShown _button' in LAYOUT
    assert 'ctrlPosition _button' in LAYOUT
    assert '"ACME_txRoundHover"' in LAYOUT and '"ACME_txRoundFocus"' in LAYOUT
    assert '"ACME_txSkinTint"' in LAYOUT
    service = (ROOT / "addons/acm_extended/functions/fn_transfusionServicePaint.sqf").read_text()
    assert '_flush ctrlSetBackgroundColor [0,0,0,0];' in service
    assert '"ACME_txSkinTint"' in service
    assert 'ctrlSetBackgroundColor [0,0,0,0];' in LAYOUT
    assert 'call FUNC(TransfusionMenu_ToggleIVFlow)' in DIALOG
    assert 'call FUNC(TransfusionMenu_MoveBag)' in DIALOG


def test_every_row_and_topology_bracket_uses_the_authored_native_card_pitch():
    # The native list pitch is now a hidden backing detail. Visible topology
    # follows the exact card endpoints, including scrolling and mixed panes.
    bracket = (ROOT / "addons/acm_extended/functions/fn_paintTransfusionYBracket.sqf").read_text()
    assert '_endpoints set [_identity select 4,[_cardRect select 0,(_cardRect select 1) + _rowH / 2]]' in CARDS
    assert '"ACME_txCardEndpoints"' in CARDS and '"ACME_txCardEndpoints"' in bracket
    assert '"ACME_txCardsReady"' in bracket
    assert 'count _cardPoints == count _rows' in bracket
    assert 'private _gap = safeZoneH * 0.007;' in CARDS
    assert '(_h - _gap * (_capacity - 1)) / _capacity' in CARDS
    assert 'call ACME_fnc_transfusionCardWindow' in CARDS


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
