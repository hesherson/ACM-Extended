from historical_source import read_source, assert_release_identity
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def txt(rel): return read_source(ROOT/rel, encoding='utf-8',errors='replace')

def test_version_b58():
    assert_release_identity()
    p=txt('functions/fn_postInit.sqf')
    assert_release_identity()

def test_final_name_ui_removed_and_drawn_body_only():
    s=txt('functions/fn_skInject.sqf')
    assert 'Final Syringe Name (25 max)' not in s
    assert 'ctrlCreate ["ACME_SK_NameEdit", 84161]' not in s
    v=txt('functions/fn_skSetView.sqf')
    assert 'forEach [84133,84134,84302]' in v
    assert '_c ctrlShow _body' in v

def test_dedicated_syringe_menu_button_and_keys():
    s=txt('functions/fn_skInject.sqf')
    assert 'Open Syringe Menu' in s
    assert 'safeZoneH / 46' in s
    assert '_key == 30' in s and '_key == 32' in s
    v=txt('functions/fn_skSetView.sqf')
    assert 'Close Syringe Menu' in v
    assert '_carousel = _view == "carousel"' in v

def test_carousel_infinite_wrap_and_measured_plunger():
    from test_historical_carousel_input import test_keyboard_steps_keep_wraparound_and_never_mutate_the_store, test_actual_plunger_fraction_uses_total_solution_and_clamps_to_the_barrel
    # The old interpolation/nudge path is retired. Use the shared immediate selector and total-solution plunger.
    for count in (0,1,2,3):
        for direction in (-1,1):
            test_keyboard_steps_keep_wraparound_and_never_mutate_the_store(count,direction)
    for size in (1,3,5,10):
        for fraction in (0,0.5,1,1.2):
            test_actual_plunger_fraction_uses_total_solution_and_clamps_to_the_barrel(size,fraction)
    assert 'syringe_%1_plunger_ca.paa' in txt('functions/fn_skCarouselRender.sqf')

def test_tags_have_three_editors_and_all_colors():
    # The same three editors and 12 colors remain, with optional None and Edit Syringe Tag.
    from test_bounded_tag_contracts import editor_wiring
    from test_historical_syringe_identity import test_tag_color_uses_selected_identity_without_changing_text_or_dose
    editor_wiring()
    for color in ('none','yellow_induction','blue_opioid','red_paralytic'):
        test_tag_color_uses_selected_identity_without_changing_text_or_dose(color)

def test_tag_assets_are_paa_and_all_sizes_present():
    base=ROOT/'ui/syringe_tags'
    for size in ('1mL','3mL','5mL','10mL'):
        files=list((base/size).glob('*.paa'))
        assert len(files)==12, (size,len(files))

def test_tag_metadata_persists_on_store_and_self_menu_exists():
    from test_historical_syringe_identity import test_tag_color_uses_selected_identity_without_changing_text_or_dose, test_editing_updates_only_selected_tag_without_repainting_active_editor
    for color in ("", "none", "blue_opioid"):
        test_tag_color_uses_selected_identity_without_changing_text_or_dose(color)
    for editing in (True, False):
        test_editing_updates_only_selected_tag_without_repainting_active_editor(editing)
    c=txt('config.cpp')
    assert 'class ACME_DrawnSyringes' in c
    assert 'insertChildren = "_this call ACME_fnc_skSyringeSelfMenu";' in c
    assert 'class skSyringeSelfMenu {};' in c

def test_store_lifetime_current_life_only():
    from test_historical_syringe_identity import test_personal_lifecycle_clears_kit_and_selection_but_not_patient_equipment, test_headless_machine_does_not_install_personal_kit_handlers
    assert 'call ACME_fnc_registerSyringeLifecycleRuntime;' in txt('functions/fn_postInit.sqf')
    for event in ('Killed','Respawn'):
        test_personal_lifecycle_clears_kit_and_selection_but_not_patient_equipment(event)
    test_headless_machine_does_not_install_personal_kit_handlers()

def test_carousel_headers_summary_and_patient_location():
    r=txt('functions/fn_skCarouselRender.sqf')
    assert 'ACME_fnc_skSyringeSummary' in r
    assert 'displayCtrl 84001' in r and 'displayCtrl 84002' in r
    s=txt('functions/fn_skSyringeSummary.sqf')
    assert 'Concentration' in s and ' in %4 mL' in s

def test_font_binary_not_redistributed_and_handwriting_fallback_is_runtime_safe():
    # Font file is intentionally not shipped; Arma custom fonts require generated PAA/FXY families.
    assert not list(ROOT.rglob('*.ttf'))
    cfg=txt('config.cpp')
    assert 'class ACME_SK_TagEdit: RscEdit' in cfg
    assert 'font = "Caveat";' in cfg

def test_tag_static_text_matches_editor_font_and_ad_keys_do_not_steal_typing():
    cfg=txt('config.cpp')
    inj=txt('functions/fn_skInject.sqf')
    assert 'class ACME_SK_TagText: RscText' in cfg
    assert 'private _t = _display ctrlCreate ["ACME_SK_TagText", _baseId + _x];' in inj
    assert '(ctrlIDC _focus) in [84460,84461,84462]' in inj
    assert 'exitWith {false}' in inj


def test_self_action_opens_native_size_before_entering_carousel():
    from test_historical_syringe_identity import test_self_menu_open_uses_stable_id_and_native_size, test_stale_self_menu_callback_cannot_open_a_different_syringe
    # The pending entry is now a stable ID, not the retired array-index handoff.
    for size, expected in ((1,1),(3,3),(5,5),(10,10),(2,10)):
        test_self_menu_open_uses_stable_id_and_native_size(size,expected)
    test_stale_self_menu_callback_cannot_open_a_different_syringe()
