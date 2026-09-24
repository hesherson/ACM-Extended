#!/usr/bin/env python3
"""Phase 130: Plasma-Lyte remains paired in the ACM fluid registry and selected inventory list."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
init=(R/'addons/acm_extended/functions/fn_initInfusionConfig.sqf').read_text()
menu=(R/'addons/circulation/functions/fnc_TransfusionMenu_SwitchTargetInventory.sqf').read_text()
cfg=(R/'addons/acm_extended/config.cpp').read_text()
vol=(R/'addons/core/overrides/fnc_getBloodVolumeChange.sqf').read_text()
for item,data in [('ACME_PlasmaLyteBag','PlasmaLyteIV_1000'),('ACME_PlasmaLyteBag_500','PlasmaLyteIV_500'),('ACME_PlasmaLyteBag_250','PlasmaLyteIV_250'),('ACME_PlasmaLyteBag_100','PlasmaLyteIV_100')]:
    assert item in init and data in init
    assert item in menu and data in menu
    assert f'class {item}' in cfg
assert 'while {count ACM_circulation_Fluids_Array_Data <= _index}' in init
assert 'GVAR(TransfusionMenu_Selected_Inventory) == 2' in menu
assert '[_target, 0] call ACME_fnc_itemList' in menu
assert 'case "PlasmaLyte"' in vol or '"PlasmaLyte"' in vol
print('PASS phase130: Plasma-Lyte item/data pairs survive list rebuilds and selected inventory gating')
