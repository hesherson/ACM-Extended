"""A theme migration must preserve native geometry and embedded-device wiring."""

from pathlib import Path
import re
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
BASELINE = "120ad64ee4eaf299ffce9c6f1dad150dc8763d9d"
NATIVE = (
    "acm_extended/config.cpp",
    "acm_extended/TransfusionMenu_Styles.hpp",
    "airway/RscHeadTilt.hpp",
    "airway/SurgicalAirway_Dialog.hpp",
    "breathing/RscUseBVM.hpp",
    "breathing/Stethoscope_Dialog.hpp",
    "card/ui/DD1380_dlg.hpp",
    "cbrn/RscAttributes.hpp",
    "circulation/Defibrillator_Monitor_Dialog.hpp",
    "circulation/MeasureBP_Dialog.hpp",
    "circulation/RscFeelPulse.hpp",
    "circulation/SyringeDraw_Dialog.hpp",
    "core/RscTitles.hpp",
    "zeus/RscAttributes.hpp",
)
DEVICES = ("acme_atak/ui/batdok.html", "acme_tempus/ui/tempus.html", "acme_tempusls/ui/tempusls.html")
GEOMETRY = re.compile(
    r'\b(x|y|w|h|left|top|offset(?:Pressed)?[XY]|rowHeight|idd|idc|size|sizeEx|'
    r'onLoad|onUnload|onButtonClick|action|onKeyDown)\s*=\s*("(?:[^"]|"")*"|[^;]+);'
)


def source(path):
    return (ROOT / "addons" / path).read_text(encoding="utf-8")


def baseline(path):
    return subprocess.check_output(
        ["git", "show", f"{BASELINE}:addons/{path}"], cwd=ROOT, text=True, encoding="utf-8"
    )


# The Megacode Kelly instructor panel was redesigned on purpose after B363: its whole layout is built at runtime
# (fn_megacodePanelLoad / fn_megacodeMenu) and its dialog class is now empty, so its static geometry is left out of
# this comparison. Everything else in config.cpp is still held to the baseline.
MEGACODE_PANEL = re.compile(r"(?s)// megacode kelly, the instructor control panel\..*?(?=// megacode laptop cable tuner\.)")


def geometry(text):
    return GEOMETRY.findall(MEGACODE_PANEL.sub("", text, count=1))


@pytest.mark.parametrize("path", NATIVE)
def test_native_geometry_and_handlers_keep_their_original_definitions(path):
    assert geometry(source(path)) == geometry(baseline(path))


@pytest.mark.parametrize("path", DEVICES)
def test_device_theme_only_overrides_visual_properties(path):
    pattern = re.compile(r'<style id="acme-interface-theme">\n(.*?)</style>\n', re.S)
    theme = pattern.search(source(path))
    assert theme is not None
    assert pattern.sub("", source(path), count=1) == baseline(path)
    rules = re.sub(r"@font-face\{[^}]*\}", "", theme[1])
    declarations = re.findall(r"(?:^|[;{])\s*([-\w]+)\s*:", rules)
    assert declarations
    assert all(prop.startswith("--acme-") or prop in {
        "background-color", "background-image", "border-color", "color", "font-family", "outline-color",
    } for prop in declarations)


def test_ace_medical_menu_controls_keep_their_original_definitions():
    path = "acm_extended/config.cpp"
    pattern = re.compile(
        r"(?ms)^class (?:ace_medical_gui_\w+|ACME_MedicalMenu_LeftText|"
        r"ACME_AEDSyncButton|ACME_EJTransfusionHotspot|ACME_CoolerHotspot).*?^\};"
    )
    original = [item[0] for item in pattern.finditer(baseline(path))]
    assert original
    assert [item[0] for item in pattern.finditer(source(path))] == original
