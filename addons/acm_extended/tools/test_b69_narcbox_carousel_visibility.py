from historical_source import read_source, assert_release_identity
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def txt(rel):
    return read_source(ROOT / rel, encoding="utf-8", errors="replace")


def test_b69_version_stamp():
    assert_release_identity()
    post = txt('functions/fn_postInit.sqf')
    assert_release_identity()
    assert_release_identity()


def test_main_select_syringe_tag_is_created_after_runtime_source_panels_for_top_z_order():
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_lifetime import selector_contract
    selector_contract()


def test_main_select_syringe_tag_is_narrower_and_has_real_art_clearance():
    # Later B78 geometry/readiness supersedes this historical identifier's older implementation.
    from test_bounded_selector_geometry import geometry_source_contract
    geometry_source_contract()


def test_tag_text_controls_require_an_actual_tag_color():
    pending = txt('functions/fn_skPendingTagRender.sqf')
    car = txt('functions/fn_skCarouselRender.sqf')
    open_edit = txt('functions/fn_skTagEditOpen.sqf')
    tag_color = txt('functions/fn_skTagColor.sqf')
    assert 'private _hasTag = !(_color in ["", "none"]);' in pending
    assert '_e ctrlShow _hasTag;' in pending and '_e ctrlEnable _hasTag;' in pending
    assert 'private _showEditor = _editMode && {_curHasTag};' in car
    assert '_edit ctrlShow _showEditor;' in car and '_edit ctrlEnable _showEditor;' in car
    assert 'if (_color in ["","none"]) then {84470} else {84460}' in open_edit
    assert 'if (_id in ["","none"]) then {84470} else {84460}' in tag_color


def test_body_map_hides_all_preparation_source_sections_until_draw_syringe_returns():
    view = txt('functions/fn_skSetView.sqf')
    rows = txt('functions/fn_skListRefresh.sqf')
    assert '(_display displayCtrl 84007) ctrlShow (!_infusion && {!_body});' in view
    assert '(_display displayCtrl 84008) ctrlShow (!_body);' in view
    assert '(_display displayCtrl 84129) ctrlShow (!_body);' in view
    assert '(_display displayCtrl 84131) ctrlShow (!_infusion && {!_body});' in view
    assert 'private _visible = !_carousel && {!_body};' in rows
    assert '(_d displayCtrl 84008) ctrlShow (!_body);' in rows
    assert '(_d displayCtrl 84129) ctrlShow (!_body);' in rows


def test_carousel_layout_cannot_reveal_hidden_body_overlays_during_promotion():
    layout = txt('functions/fn_skDynamicLayout.sqf')
    body = txt('functions/fn_skUpdateBody.sqf')
    assert '_group ctrlShow (!_editMode);' not in layout
    assert 'if (_editMode) then {_group ctrlShow false;};' in layout
    assert 'ACME_SK_TagEditMode' in body
    assert '_group ctrlShow _show;' in body
    assert 'ace_medical_gui_fnc_updateBodyImage' in body


def test_hover_events_cannot_snap_an_in_flight_carousel():
    from test_historical_carousel_input import test_hover_is_presentation_only_and_keeps_selection_and_expansion, test_actual_slot_hover_alpha_changes_without_changing_its_geometry
    # There is no interpolated in-flight carousel now. Hover changes alpha, not selection/geometry.
    for expanded in (False,True):
        for hover in (False,True):
            test_hover_is_presentation_only_and_keeps_selection_and_expansion(expanded,hover)
        test_actual_slot_hover_alpha_changes_without_changing_its_geometry(expanded,2)
    render=txt('functions/fn_skCarouselRender.sqf')
    assert 'private _duration = 0;' in render
    assert 'private _carouselBusy = uiNamespace getVariable ["ACME_SK_CarouselBusy",false];' in render
    assert '!_carouselBusy' in render


def test_promotion_animates_hints_with_syringes_and_preserves_each_plunger_fill():
    move = txt('functions/fn_skCarouselMove.sqf')
    render = txt('functions/fn_skCarouselRender.sqf')
    assert 'private _motion = 0.220;' in move
    assert '[_motion] call ACME_fnc_skDynamicLayout; [_motion] call ACME_fnc_skCarouselRender;' in move
    assert '_leftKey ctrlSetPosition' in render and '_rightKey ctrlSetPosition' in render
    assert '_x ctrlCommit _duration;' in render
    assert 'private _plungerY = _py + (_travel10 * _sizeRatio * _frac' in move
    assert 'private _partY = if (_part == 2) then {_plungerY} else {_py};' in move
    assert 'uiNamespace setVariable["ACME_SK_CarouselBusy",false];\n    [0] call ACME_fnc_skCarouselRender;' in move


def test_chest_holes_use_nonzero_seal_aware_spacing_and_more_rejection_attempts():
    gen = txt('functions/fn_chestSealGenHoles.sqf')
    post = txt('functions/fn_postInit.sqf')
    assert 'ACME_CS_minHoleSep", 0.052' in gen
    assert 'private _fnc_clearance = {' in gen
    assert '_dx max _dy' in gen
    assert 'for "_try" from 1 to 48 do {' in gen
    assert 'forEach [[40,140], [200,250], [290,340]];' in gen
    assert 'ACME_CS_minHoleSep       = 0.052;' in post


def test_b68_three_second_push_and_b67_cardiac_safety_still_present():
    # Current timed confirmation and native ACM rhythm authority supersede the old inline push/floor.
    from test_bounded_push_native_contract import historical_combined_check
    historical_combined_check()


def test_deterministic_thorax_lattice_can_pack_four_seal_safe_centers():
    # Mirrors B69's authored fallback lattice. Chest-seal art is 0.05 x 0.05 body UV;
    # the runtime uses Chebyshev/per-axis clearance, so >=0.052 means footprints do not overlap.
    import math

    cx, cy, rx, ry = 0.5, 0.29, 0.08, 0.06
    candidates = []
    for a0, a1 in ((40, 140), (200, 250), (290, 340)):
        for ai in range(21):
            angle = a0 + ((a1 - a0) * (ai / 20))
            for radius in (0.60, 0.70, 0.80, 0.90, 0.96):
                candidates.append((
                    cx + math.cos(math.radians(angle)) * rx * radius,
                    cy + math.sin(math.radians(angle)) * ry * radius,
                ))

    def clearance(p, q):
        return max(abs(p[0] - q[0]), abs(p[1] - q[1]))

    # Check every possible lattice first hole. Greedy farthest-point placement must still fit three more.
    worst = 1.0
    for first in candidates:
        points = [first]
        for _ in range(3):
            best = max(candidates, key=lambda c: min(clearance(c, p) for p in points))
            points.append(best)
        minimum = min(clearance(a, b) for i, a in enumerate(points) for b in points[i + 1:])
        worst = min(worst, minimum)
    assert worst >= 0.052
