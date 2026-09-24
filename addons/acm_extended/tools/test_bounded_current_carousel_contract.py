"""Current Body Map / Narc Box carousel contract after the B78/phase-121 simplification.

These are source/layout contracts only. They deliberately protect the present single five-slot carousel,
instant navigation, tag-face selector geometry and bounded hit regions without restoring retired mini-carousel,
hover-growth, gray underlay or multi-control interpolation.
"""
from pathlib import Path
from historical_source import read_source

ROOT=Path(__file__).resolve().parents[1]

def txt(rel):
    return read_source(ROOT/rel, encoding="utf-8", errors="replace")

def geometry_contract():
    inj=txt("functions/fn_skInject.sqf")
    layout=txt("functions/fn_skDynamicLayout.sqf")
    for token in ("ACME_SK_BodyRectCompact","ACME_SK_BodyRectExpanded","ACME_SK_CarouselRectCompact","ACME_SK_CarouselRectExpanded"):
        assert token in inj and token in layout
    assert "private _compactH = safeZoneH * 0.52 / _fillV;" in inj
    assert "private _expandedH = safeZoneH * 0.14 / _fillV;" in inj
    assert "private _toolbarW = _uiW / 11;" in inj
    assert "private _carCompactW = _toolbarW * 0.78;" in inj
    assert "private _carExpandedW = (_toolbarW * 1.72) min (safeZoneH * 0.64);" in inj
    assert "private _carCompactBottom = _drawRowY - safeZoneH*0.080;" in inj
    assert "private _carExpandedBottom = _drawRowY - safeZoneH*0.188;" in inj
    assert "private _carCompactH = safeZoneH*0.105;" in inj
    assert "private _carExpandedH = safeZoneH*0.380;" in inj
    assert "private _routeY = safeZoneY + safeZoneH * (if (_expanded) then {0.228} else {0.630});" in layout
    assert "private _editRect = [_tx, _routeY + _th + _editGap, _tw, _th];" in layout
    assert 'ACME_SK_EditTagBodyRect' in layout
    assert "private _zoneY = (_editRect select 1) + (_editRect select 3) + safeZoneH*0.007;" in layout
    assert "private _zoneBottom = (_boundRect select 1) - safeZoneH*0.012;" in layout
    assert "private _zoneH = (_zoneBottom - _zoneY) max 0;" in layout
    assert "private _duration = 0;" in layout

def render_contract():
    car=txt("functions/fn_skCarouselRender.sqf")
    assert "private _duration = 0;" in car
    assert "private _fullH = safeZoneH * (if (_expanded) then {0.470} else {0.150});" in car
    assert "private _sc = if (_expanded) then {[0.34,0.66,1.0,0.66,0.34]} else {[0.28,0.55,1.0,0.55,0.28]};" in car
    assert "private _al = if (_expanded) then {[0.08,0.34,1.0,0.34,0.08]} else {[0.06,0.24,0.85,0.24,0.06]};" in car
    assert "private _dx = _rw * (if (_expanded) then {0.185} else {0.155});" in car
    assert "if (!_editMode && {_off == _hoverOffset}) then {_alpha = 1;};" in car
    assert "private _activeScale = 1;" in car
    assert "private _hitW = _fullW * 1.55; private _hitH = _fullH * 1.26;" in car
    assert "private _hitY = (_y-_padY) max _hoverTop;" in car
    assert "private _hitBottom = (_y+_h+_padY) min _hoverBottom;" in car
    assert "private _activeHitBottom = (_centerY+_hitH/2) min _hoverBottom;" in car
    assert "(_amt + _nsMl) / (_size max 0.01)" in car
    assert "ACME_SK_CarouselTravel10" in car
    assert "syringe_%1_plunger_ca.paa" in car
    assert "tag_overlay_%1mL_%2.paa" in car
    assert "_e param [8+_ln" in car

def navigation_contract():
    move=txt("functions/fn_skCarouselMove.sqf")
    pick=txt("functions/fn_skCarouselPick.sqf")
    assert "Carousel changes are now instantaneous" in move
    assert 'ACME_SK_CarouselExpanded", true' in move
    assert 'ACME_SK_CarouselCollapseAt", diag_tickTime + 1.35' in move
    assert "[0] call ACME_fnc_skDynamicLayout;" in move
    assert "[0] call ACME_fnc_skCarouselRender;" in move
    assert "_motion" not in move
    assert "ctrlCommit" not in move
    assert "if (uiNamespace getVariable [\"ACME_SK_TagEditMode\", false]) exitWith {};" in move
    assert "if (uiNamespace getVariable [\"ACME_SK_TagEditMode\",false]) exitWith {};" in pick
    assert "call ACME_fnc_skCarouselToggle;" in pick

def header_contract():
    car=txt("functions/fn_skCarouselRender.sqf")
    layout=txt("functions/fn_skDynamicLayout.sqf")
    assert '(_d displayCtrl 84001) ctrlSetText "";' in car
    assert '(_d displayCtrl 84002) ctrlSetText (if (isNull _p) then {"Patient"} else {name _p});' in car
    assert 'private _screenTop = safeZoneY + safeZoneH*0.004;' in layout
    assert 'private _headTop = (_bodyRect select 1) + (_bodyRect select 3)*0.055;' in layout
    assert 'private _headerCenterY = _screenTop + _available*0.30;' in layout
    assert 'private _maxY = _headTop - (_hr select 3) - safeZoneH*0.008;' in layout
    assert '_hr set [0, _uiX + _uiW/2 - (_hr select 2)/2];' in layout

def hint_contract():
    car=txt("functions/fn_skCarouselRender.sqf")
    inj=txt("functions/fn_skInject.sqf")
    for idc in range(84700,84704):
        assert str(idc) in inj and str(idc) in car
    assert 'private _hintScale = if (_expanded) then {1.24} else {0.92};' in car
    assert 'private _hintPad = safeZoneH * (if (_expanded) then {0.020} else {0.006});' in car
    assert 'private _leftKeyX = if (_expanded) then {(_rx - _keyW - _hintPad) max _uiX} else {_toolbarX};' in car
    assert 'private _rightKeyX = if (_expanded) then {(_rx + _rw + _hintPad) min (_uiX + _uiW - _keyW)} else {_toolbarX + _toolbarW - _keyW};' in car
    assert '_x ctrlShow (!_editMode)' in car

def tag_geometry_contract():
    pending=txt("functions/fn_skPendingTagRender.sqf")
    car=txt("functions/fn_skCarouselRender.sqf")
    layout=txt("functions/fn_skDynamicLayout.sqf")
    assert '_button ctrlSetText "Select Syringe Tag";' in pending
    assert 'private _tagCenterX = _x + _w*0.36;' in pending
    assert 'private _btnX = _tagCenterX - _btnW/2;' in pending
    assert 'private _btnY = _y + _h*0.575;' in pending
    assert '_colorBtn ctrlSetText (if (_editMode) then {"Select Syringe Tag"} else {"Edit Syringe Tag"});' in car
    assert 'private _bodyEdit = +(_d getVariable ["ACME_SK_EditTagBodyRect"' in car
    assert 'private _tagCenterX = _ax + _aw*0.36;' in car
    assert '_btnY = _ay + _ah*0.575;' in car
    assert 'private _editRect = [_tx, _routeY + _th + _editGap, _tw, _th];' in layout

def save_contract():
    after=txt("functions/fn_skAfterSaveOpenBody.sqf")
    assert 'ACME_SK_CarouselExpanded", false' in after
    assert 'ACME_SK_View", "syringe"' in after
    assert "call ACME_fnc_skPendingTagReset;" in after
    assert "call ACME_fnc_skSetView;" in after

def retired_contract():
    inj=txt("functions/fn_skInject.sqf")
    setview=txt("functions/fn_skSetView.sqf")
    car=txt("functions/fn_skCarouselRender.sqf")
    layout=txt("functions/fn_skDynamicLayout.sqf")
    body=txt("functions/fn_skBodySyringeRender.sqf")
    assert '84500 + (_slot * 10)' not in inj
    assert 'for "_slot" from 0 to 2' in setview and '84500 + _slot*10' in setview
    assert 'call ACME_fnc_skCarouselRender;' in body
    assert "ACME_fnc_skSyringeSummary" not in car
    assert "84482" not in inj+layout+car
    assert "[0.12,0.12,0.12" not in layout

def body_visibility_contract():
    setview=txt("functions/fn_skSetView.sqf")
    update=txt("functions/fn_skUpdateBody.sqf")
    rows=txt("functions/fn_skListRefresh.sqf")
    assert 'forEach [84133,84134,84302]' not in setview
    assert 'private _show = (uiNamespace getVariable ["ACME_SK_View", "syringe"]) == "body"' in update
    assert '_group ctrlShow _show;' in update
    assert 'private _visible = !_carousel && {!_body};' in rows

def test_current_carousel_geometry_contract():
    geometry_contract()

def test_current_carousel_render_contract():
    render_contract()

def test_current_carousel_navigation_contract():
    navigation_contract()

def test_current_header_contract():
    header_contract()

def test_current_hint_contract():
    hint_contract()

def test_current_tag_geometry_contract():
    tag_geometry_contract()

def test_current_save_contract():
    save_contract()

def test_retired_carousel_artifacts_stay_retired():
    retired_contract()

def test_current_body_visibility_contract():
    body_visibility_contract()
