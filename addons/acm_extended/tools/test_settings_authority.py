from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="strict")


def _setting_array(text: str, name: str) -> str:
    needle = f'"{name}"'
    idx = text.find(needle)
    assert idx >= 0, f"missing setting: {name}"
    start = text.rfind("[", 0, idx)
    assert start >= 0

    depth = 0
    in_string = False
    in_line_comment = False
    in_block_comment = False
    i = start
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_string:
            if ch == '"' and nxt == '"':
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch == '"':
            in_string = True
            i += 1
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1

    raise AssertionError(f"unterminated setting array: {name}")


def _top_level_parts(array_text: str) -> list[str]:
    body = array_text[1:-1]
    parts: list[str] = []
    start = 0
    square = curly = paren = 0
    in_string = False
    in_line_comment = False
    in_block_comment = False

    i = 0
    while i < len(body):
        ch = body[i]
        nxt = body[i + 1] if i + 1 < len(body) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_string:
            if ch == '"' and nxt == '"':
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch == '"':
            in_string = True
            i += 1
            continue

        if ch == "[":
            square += 1
        elif ch == "]":
            square -= 1
        elif ch == "{":
            curly += 1
        elif ch == "}":
            curly -= 1
        elif ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
        elif ch == "," and square == 0 and curly == 0 and paren == 0:
            parts.append(body[start:i].strip())
            start = i + 1
        i += 1

    parts.append(body[start:].strip())
    return parts


def setting_scope(text: str, name: str) -> int:
    parts = _top_level_parts(_setting_array(text, name))
    assert len(parts) >= 6, f"setting has no explicit CBA scope: {name}"
    assert parts[5] in {"0", "1", "2"}, (name, parts[5])
    return int(parts[5])


def _all_setting_names(text: str) -> list[str]:
    return [
        m.group(1)
        for m in re.finditer(
            r'\[\s*"(ACME_[^"]+)"\s*,\s*"(?:CHECKBOX|SLIDER|LIST|EDITBOX|COLOR)"',
            text,
        )
    ]


def test_true_client_preferences_are_local_only_and_non_overridable():
    pre = read("XEH_preInit.sqf")
    extra = read("XEH_settings.hpp")

    pre_client = [
        "ACME_hc_descriptors",
        "ACME_iv_uiScaleV3",
        "ACME_iv_trayIconBias",
        "ACME_iv_bruiseMaxAlpha",
        "ACME_iv_bruiseBoost14",
        "ACME_iv_palpModel",
        "ACME_iv_phenotypeForce",
        "ACME_iv_dotSize",
        "ACME_iv_prepDabAlpha",
        "ACME_iv_prepDabSize",
        "ACME_iv_prepHoldSec",
        "ACME_iv_prepFadeSec",
        "ACME_infusion_clampScrollStep",
        "ACME_infusion_clampScrollInvert",
        "ACME_infusion_clampSfxEnabled",
        "ACME_debug_enabled",
        "ACME_hang_useRope",
        "ACME_seizure_animEnabled",
    ]
    extra_client = [
        "ACME_tbi_debugHud",
        "ACME_a11y_colorblindMode",
        "ACME_a11y_bvmVentCircle",
        "ACME_a11y_bvmVentInflateSec",
        "ACME_a11y_menuLeftAlign",
        "ACME_menuNestEnabled",
        "ACME_menuColorHeaders",
        "ACME_a11y_colorblindStrength",
        "ACME_bloodTypeLock",
        "ACME_motion_interpolate",
        "ACME_motion_interpolationTime",
        "ACME_minigameNV_focusBlur",
    ]

    for name in pre_client:
        assert setting_scope(pre, name) == 2, name
    for name in extra_client:
        assert setting_scope(extra, name) == 2, name


def test_shared_gameplay_settings_are_global_only():
    pre = read("XEH_preInit.sqf")
    for name in [
        "ACME_obtunded_autoEnable",
        "ACME_iv_prepMarksToClean",
        "ACME_iv_fossaSpread",
        "ACME_hc_medications",
        "ACME_sys_tbi",
        "ACME_sys_junc",
        "ACME_allowThoracostomy",
        "ACME_skillMedicationPreparation",
    ]:
        assert setting_scope(pre, name) == 1, name


def test_no_acme_setting_uses_ambiguous_overridable_scope_zero():
    # CBA scope 0 means local but mission/server-overridable. ACME intentionally uses only:
    # 1 = shared gameplay, 2 = genuinely client-owned presentation/accessibility.
    pre = read("XEH_preInit.sqf")
    extra = read("XEH_settings.hpp")
    for text in (pre, extra):
        names = _all_setting_names(text)
        assert names
        for name in names:
            assert setting_scope(text, name) in (1, 2), name
