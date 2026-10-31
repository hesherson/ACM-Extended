#!/usr/bin/env python3
"""Phase 55 regression: ACE medical-menu PFH lifecycle is owned by the native GUI addon."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]

def read(rel): return (ROOT/rel).read_text(encoding='utf-8',errors='replace')
def test_current_phase55_gui_pfh_owner():
    prep=read('addons/gui/XEH_PREP.hpp')
    assert 'PREP(pauseMedicalMenuPFH);' in prep
    assert 'PREP(resumeMedicalMenuPFH);' in prep
    pause=read('addons/gui/functions/fnc_pauseMedicalMenuPFH.sqf')
    resume=read('addons/gui/functions/fnc_resumeMedicalMenuPFH.sqf')
    assert 'ace_medical_gui_menuPFH' in pause and 'CBA_fnc_removePerFrameHandler' in pause
    assert 'ace_medical_gui_menuPFH' in resume and 'CBA_fnc_addPerFrameHandler' in resume
    for rel,fn in [
     ('addons/acm_extended/functions/fn_chestSealInit.sqf','ACM_GUI_fnc_pauseMedicalMenuPFH'),
     ('addons/acm_extended/functions/fn_thoraInit.sqf','ACM_GUI_fnc_pauseMedicalMenuPFH'),
     ('addons/acm_extended/functions/fn_chestSealClose.sqf','ACM_GUI_fnc_resumeMedicalMenuPFH'),
     ('addons/acm_extended/functions/fn_thoraClose.sqf','ACM_GUI_fnc_resumeMedicalMenuPFH'),
    ]:
        assert fn in read(rel), rel
    viol=[]
    for p in (ROOT/'addons/acm_extended').rglob('*.sqf'):
        for i,line in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
            code=line.split('//',1)[0]
            if re.search(r'missionNamespace\s+setVariable\s*\[\s*["\']ace_medical_gui_menuPFH["\']',code,re.I):
                viol.append((p,i,line.strip()))
    assert not viol, '\n'.join(f'{p.relative_to(ROOT)}:{i}: {s}' for p,i,s in viol)
    print('fork phase 55 GUI PFH ownership checks: PASS')


if __name__ == "__main__":
    test_current_phase55_gui_pfh_owner()
