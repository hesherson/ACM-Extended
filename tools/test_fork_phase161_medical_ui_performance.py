#!/usr/bin/env python3
"""RC16 guard: expensive medical/transfusion UI work is throttled and registration is idempotent."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

reg = read("addons/acm_extended/functions/fn_registerTransfusionUiRuntime.sqf")
tx_open = read("addons/circulation/functions/fnc_openTransfusionMenu.sqf")
tx_controls = read("addons/acm_extended/functions/fn_updateTransfusionControls.sqf")
actions = read("addons/gui/overrides/fnc_updateActions.sqf")
injury = read("addons/gui/overrides/fnc_updateInjuryList.sqf")
startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")

# One registration only; expensive custom transfusion controls at 4 Hz.
assert 'ACME_transfusionUiRuntimeRegistered' in reg
assert '}, 0.25, []] call CBA_fnc_addPerFrameHandler;' in reg
assert 'ACME_transfusionUiPFH' in reg

# Native transfusion display repaint loop is 10 Hz instead of every rendered frame.
assert '}, 0.10, [_display, _medic, _patient, _inVehicle, _menuGeneration, _closeID]] call CBA_fnc_addPerFrameHandler;' in tx_open
assert '}, 0, [_display, _medic, _patient, _inVehicle, _menuGeneration, _closeID]] call CBA_fnc_addPerFrameHandler;' not in tx_open

# nearestObjects/cooler discovery has its own slower cache window.
assert 'ACME_txCoolerNextScan' in tx_controls
assert 'diag_tickTime + 0.75' in tx_controls
assert tx_controls.index('ACME_txCoolerNextScan') < tx_controls.index('nearestObjects')

# Main medical menu expensive action paint is 10 Hz unless selection context changes.
assert 'ACME_menuPaintKey' in actions
assert 'ACME_menuNextPaint' in actions
assert 'diag_tickTime + 0.10' in actions
assert "_menu setVariable ['ACME_menuNextPaint', 0];" in actions

# Context variables must be declared before the throttle key uses them.
assert actions.index("private _target = missionNamespace getVariable ['ace_medical_gui_target', objNull];") < actions.index("private _paintKey = [_target, _bodyPart, _selectedCategory];")
assert actions.index("private _bodyPart = missionNamespace getVariable ['ace_medical_gui_selectedBodyPart', -1];") < actions.index("private _paintKey = [_target, _bodyPart, _selectedCategory];")
assert actions.index("private _selectedCategory = missionNamespace getVariable ['ace_medical_gui_selectedCategory', ''];") < actions.index("private _paintKey = [_target, _bodyPart, _selectedCategory];")

# Injury list rebuild is ~6.7 Hz unless target/bodypart changes.
assert 'ACME_injuryPaintKey' in injury
assert 'ACME_injuryNextPaint' in injury
assert 'diag_tickTime + 0.15' in injury

batch = re.search(r'ACME_buildBatch\s*=\s*"([^"]+)"\s*;', startup)
revision = re.search(r'ACME_debugRevision\s*=\s*"([^"]+)"\s*;', startup)
assert batch and batch.group(1), "internal build batch stamp missing"
assert revision and revision.group(1), "debug revision stamp missing"

print("PASS 1.2.4: medical/transfusion UI repaint work is bounded and declarations are ordered")
