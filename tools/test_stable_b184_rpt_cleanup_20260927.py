#!/usr/bin/env python3
"""Stable B189 build: B184/B185 RPT cleanup remains enforced."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def class_body(cfg: str, class_name: str) -> str:
    """Return one Cfg class body using brace depth, not a brittle first-'};' split."""
    marker = f"class {class_name}"
    start = cfg.index(marker)
    open_brace = cfg.index("{", start)
    depth = 0
    in_string = False
    escape = False

    for i in range(open_brace, len(cfg)):
        ch = cfg[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return cfg[open_brace + 1:i]

    raise AssertionError(f"unterminated class {class_name}")


def test_iv_ghost_band_reconcile_is_boolean_end_to_end():
    s = read("addons/acm_extended/functions/fn_transientStateReconcile.sqf")
    block = s.split("// Repair only ghost IV constriction-band state.", 1)[1].split(
        "// Surgical-airway lifetime", 1
    )[0]

    assert 'private _flagRaw =' in block
    assert 'private _flag = (_flagRaw isEqualType true) && {_flagRaw};' in block
    assert 'private _stateOn = (_stateFlag isEqualType true) && {_stateFlag};' in block
    assert 'private _bandOn = (_bandFlag isEqualType true) && {_bandFlag};' in block
    assert 'private _rowValid = false;' in block
    assert 'forEach _siteRows;' in block

    # B184 removed the numeric findIf/index comparison that produced
    # "Type Bool, expected Number" when malformed transient state leaked through.
    assert "_siteRows findIf" not in block
    assert "_rowValid = _ri >= 0;" not in block


def test_empty_native_animation_is_normalized_before_string_operations():
    s = read("addons/core/functions/fnc_treatmentNative.sqf")
    marker = s.index("// B184: custom ACME launchers deliberately blank native animation fields.")
    replace = s.index('_medicAnim = [_medicAnim, "[wpn]", _wpn] call CBA_fnc_replace;', marker)

    block = s[marker:replace]
    assert 'if !(_medicAnim isEqualType "") then {_medicAnim = "";};' in block


def test_animation_duration_lookup_is_skipped_entirely_when_native_animation_is_blank():
    s = read("addons/core/functions/fnc_treatmentNative.sqf")
    start = s.index("// Determine the animation length only when native animation theatre actually exists.")
    end = s.index("// These animations have transitions that take a bit longer...", start)
    block = s[start:end]

    assert "private _animDuration = 0;" in block
    assert 'if (_medicAnim != "") then {' in block
    assert "animDurations" in block
    assert "WARNING_2" in block

    # The lookup and warning are both nested under the non-empty guard.
    guard = block.index('if (_medicAnim != "") then {')
    lookup = block.index("animDurations")
    warning = block.index("WARNING_2")
    assert guard < lookup < warning


def test_custom_modal_actions_are_allowed_to_have_no_native_animation():
    cfg = read("addons/acm_extended/config.cpp")

    for cls in ("ACME_ApplyChestSeal", "ACME_InspectChest", "ACME_IVMinigameStart"):
        body = class_body(cfg, cls)
        assert 'animationMedic = "";' in body

    # These two explicitly blank all inherited provider variants because their own controller owns presentation.
    for cls in ("ACME_ApplyChestSeal", "ACME_InspectChest"):
        body = class_body(cfg, cls)
        assert 'animationMedicProne = "";' in body
        assert 'animationMedicSelf = "";' in body
        assert 'animationMedicSelfProne = "";' in body

    # Thoracostomy inherits a blank native animation from CheckPulse/diagnose lineage.
    assert "class ACME_PerformThoracostomy: CheckPulse" in cfg


def test_manual_plate_carrier_awake_guard_uses_valid_sqf_syntax():
    s = read("addons/acm_extended/functions/fn_manualPlateCarrierCanToggle.sqf")

    # B189 deliberately split the old compound lazy-eval expression into simple executable guards.
    # This is clearer to HEMTT/SQF parsing and avoids the malformed-brace regression entirely.
    assert 'if (!(alive _medic)) exitWith {false};' in s
    assert 'if (!([_medic] call ace_common_fnc_isAwake)) exitWith {false};' in s
    # B208 permits corpse equipment access; only a living, awake patient blocks removal.
    assert 'if (!(alive _patient)) exitWith {false};' not in s
    assert 'private _awake = alive _patient && {' in s

    # Persistent removal is valid only while the casualty remains medically down.
    assert 'private _awake = alive _patient && {!(_patient getVariable ["ACE_isUnconscious", false])}' in s
    assert '&& {!(_patient getVariable ["ace_medical_unconscious", false])};' in s
    assert s.rstrip().endswith("!_awake")

    # The malformed historical expression must never return.
    assert 'if (!alive _medic || {!([_medic] call ace_common_fnc_isAwake})' not in s


def test_structured_item_descriptions_escape_xml_ampersands():
    cfg = read("addons/acm_extended/config.cpp")
    assert 'descriptionShort = "Hypothermia Prevention &amp; Management Kit. Reusable warming blanket.";' in cfg
    assert 'descriptionShort = "Abdominal Aortic &amp; Junctional Tourniquet' in cfg

    for line in cfg.splitlines():
        if "descriptionShort" not in line:
            continue
        # Reject raw ampersands that are not one of the standard XML entities.
        assert not re.search(r"&(?!amp;|lt;|gt;|quot;|apos;)", line)


def test_build_identity_is_b186_stable():
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")
    cfg = read("addons/acm_extended/config.cpp")
    assert 'version = "1.2.4";' in cfg
    assert 'ACME_buildBatch = "B190";' in startup
    assert 'ACME_debugRevision = "";' in startup


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("stable B189 RPT/syntax cleanup regression: PASS")
