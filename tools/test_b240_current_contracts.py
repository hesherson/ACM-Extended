"""B240 negative controls: source invariants, not native-engine execution.

A test-local Path.read_text substitution supplies one deliberate broken source to a
reviewed contract. All other reads remain real. No candidate file is modified.
"""
from pathlib import Path
import importlib.util
import pytest
from run_sharded_regressions import current_selection

ROOT = Path(__file__).resolve().parents[1]
F = "addons/acm_extended/functions/"


def reviewed(name):
    path=ROOT/"tools"/("test_fork_"+name+".py")
    spec=importlib.util.spec_from_file_location("b240_"+name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod,"test_current_"+name)


MUTATIONS = [
    ("phase8_getup", "addons/core/functions/fnc_getUp.sqf", "[_patient, _roll, 2] call ACME_fnc_doAnim;", "[_patient, _roll, 1] call ACME_fnc_doAnim;"),
    ("phase8_getup", "addons/core/functions/fnc_getUp.sqf", "if (_carryOwned) exitWith", "if (false) exitWith"),
    ("phase125_chest_firstpass_flip", F+"fn_chestSealRoll.sqf", 'if ((_lock param [0, ""]) != _tok) exitWith {};', 'if (false) exitWith {};'),
    ("phase125_chest_firstpass_flip", F+"fn_chestSealRoll.sqf", 'private _stillRollable = [_p] call ACME_fnc_chestSealCanPhysicalRoll;', 'private _stillRollable = true;'),
    ("phase129_hang_bag_visual_animation", F+"fn_hangBagClaimAck.sqf", 'if (_medic getVariable ["ACME_hang_Claimed", false]) exitWith {};', 'if (false) exitWith {};'),
    ("phase129_hang_bag_visual_animation", F+"fn_hangBagClaimLocal.sqf", 'private _nextFlow = (_flow max 1) min 5;', 'private _nextFlow = (_flow max 1) min 50;'),
    ("phase129_hang_bag_visual_animation", F+"fn_hangBagClaimLocal.sqf", 'if (isNull _patient || {!local _patient}) exitWith {false};', 'if (isNull _patient) exitWith {false};'),
    ("phase129_hang_bag_visual_animation", F+"fn_hangBagStart.sqf", None, '\n[_medic,_patient] call ACME_fnc_hangBagActivate;'),
    ("phase140_hemtt_runtime_warnings_gate", F+"fn_skWasteBegin.sqf", 'setMousePosition [_plungerX + (_plungerW / 2), _mouseYClamped];', 'setMousePosition [_uiX + (_uiW / 2), _mouseYClamped];'),
    ("phase140_hemtt_runtime_warnings_gate", F+"fn_skCompoundBegin.sqf", 'setMousePosition [_plungerX + (_plungerW / 2), _mouseYClamped];', 'setMousePosition [_uiX + (_uiW / 2), _mouseYClamped];'),
    ("phase140_hemtt_runtime_warnings_gate", "addons/core/overrides/fnc_handleBandageOpening.sqf", None, '\n[{},[],1] call CBA_fnc_waitAndExecute;'),
    ("phase142_getup_acre_babel_gate", F+"fn_obtundedVoice.sqf", None, '\ncall acre_api_fnc_babelSetSpokenLanguages;'),
    ("phase112_ace_override_target_contract", "addons/core/overrides/fnc_hasItem.sqf", 'call ACME_fnc_carrierInventoryGet', 'call ACME_fnc_wrongInventory'),
    ("phase112_ace_override_target_contract", "addons/core/overrides/fnc_useItem.sqf", 'call ACME_fnc_carrierSupplyTake', 'call ACME_fnc_wrongConsumption'),
]


@pytest.mark.parametrize("name,relative,old,new", MUTATIONS, ids=[f"{i}-{row[0]}" for i,row in enumerate(MUTATIONS)])
def test_reviewed_contract_rejects_deliberately_broken_source(monkeypatch,name,relative,old,new):
    test=reviewed(name)
    test()  # Establish the current-source positive control first.
    target=ROOT/relative
    real=Path.read_text
    source=real(target)
    if old is not None:
        assert old in source, (relative,old)
        modified=source.replace(old,new)
    else:
        modified=source+new
    assert modified!=source
    def changed(path,*args,**kwargs):
        return modified if path==target else real(path,*args,**kwargs)
    with monkeypatch.context() as context:
        context.setattr(Path,"read_text",changed)
        with pytest.raises(AssertionError):
            test()


@pytest.mark.parametrize("suffix", ['\n// call acre_api_fnc_babelSetSpokenLanguages;', '\nprivate _label = "acre_api_fnc_babelSetSpokenLanguages";'])
def test_retired_babel_scan_ignores_comment_and_label_decoys(monkeypatch,suffix):
    target=ROOT/F/"fn_obtundedVoice.sqf"
    real=Path.read_text
    modified=real(target)+suffix
    with monkeypatch.context() as context:
        context.setattr(Path,"read_text",lambda path,*a,**kw: modified if path==target else real(path,*a,**kw))
        reviewed("phase142_getup_acre_babel_gate")()


@pytest.mark.parametrize("fragment", [
    'class hasItem { file = QPATHTOF(overrides/fnc_hasItem.sqf); };',
    'class accidentalOverride { file = QPATHTOF(overrides/fnc_hasItem.sqf); };',
    'class handleBandageOpening { file = QPATHTOF(overrides/fnc_handleBandageOpening.sqf); };',
])
def test_exact_override_delta_rejects_duplicate_extra_and_retired_targets(monkeypatch,fragment):
    target=ROOT/"addons/core/CfgFunctions.hpp"
    real=Path.read_text
    modified=real(target)+f'\n    class B240Unexpected {{ tag="ace_medical_treatment"; class Extra {{ {fragment} }}; }};\n'
    with monkeypatch.context() as context:
        context.setattr(Path,"read_text",lambda path,*a,**kw: modified if path==target else real(path,*a,**kw))
        with pytest.raises(AssertionError):
            reviewed("phase112_ace_override_target_contract")()


def test_all_b240_reviewed_modules_are_required_by_current_gate():
    reviewed_paths = {'addons/acm_extended/tools/test_b36_ej_orientation.py', 'tools/test_fork_phase112_ace_override_target_contract.py', 'tools/test_fork_phase125_chest_firstpass_flip.py', 'addons/acm_extended/tools/test_bounded_head_provider_sequence.py', 'tools/test_fork_phase129_hang_bag_visual_animation.py', 'addons/acm_extended/tools/test_b156_reset_lifecycle.py', 'addons/acm_extended/tools/test_push_seconds_execution.py', 'tools/test_fork_phase145_zone3_reboa_smart_bandage.py', 'addons/acm_extended/tools/test_b72_chest_tag_head_provider.py', 'tools/test_fork_phase142_getup_acre_babel_gate.py', 'tools/test_fork_phase8_getup.py', 'tools/test_fork_phase140_hemtt_runtime_warnings_gate.py'}
    selected=set(current_selection(ROOT))
    assert reviewed_paths<=selected, sorted(reviewed_paths-selected)
