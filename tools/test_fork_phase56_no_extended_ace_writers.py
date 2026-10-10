#!/usr/bin/env python3
"""Phase 56 regression: Extended consumes ACE APIs/state but does not publish ace_* variables directly."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
EXT=ROOT/'addons/acm_extended'

def read(rel): return (ROOT/rel).read_text(encoding='utf-8',errors='replace')
def test_current_phase56_no_extended_ace_writers():
    prep=read('addons/core/XEH_PREP.hpp')
    for fn in ('setAceMedicalState','setDraggingCapability','setCursorInteractionMode'):
        assert f'PREP({fn});' in prep
    cfg=read('addons/core/config.cpp')
    assert '"ace_dragging"' in cfg and '"ace_interact_menu"' in cfg
    assert 'ace_dragging_canDrag' in read('addons/core/functions/fnc_setDraggingCapability.sqf')
    assert 'ace_interact_menu_alwaysUseCursorSelfInteraction' in read('addons/core/functions/fnc_setCursorInteractionMode.sqf')
    assert 'ACM_core_fnc_setDraggingCapability' in read('addons/acm_extended/functions/fn_coolerBoxDeploy.sqf')
    assert 'ACM_core_fnc_setCursorInteractionMode' in read('addons/acm_extended/functions/fn_installLightKey.sqf')
    assert 'ACM_core_fnc_setCursorInteractionMode' in read('addons/acm_extended/functions/fn_aceCursorRestore.sqf')
    viol=[]
    for p in EXT.rglob('*.sqf'):
        for i,raw in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
            line=raw.split('//',1)[0]
            if not line.strip(): continue
            m=re.search(r'(?:missionNamespace\s+)?setVariable\s*\[\s*["\'](ace_[^"\']+)["\']',line,re.I)
            if m: viol.append((p,i,m.group(1),raw.strip(),'setVariable'))
            if 'ACME_fnc_setVarNet' in line:
                m=re.search(r'\[\s*[^,\]]+\s*,\s*["\'](ace_[^"\']+)["\']\s*,',line,re.I)
                if m: viol.append((p,i,m.group(1),raw.strip(),'setVarNet'))
    if viol:
        raise AssertionError('\n'.join(f'{p.relative_to(ROOT)}:{i}: {kind} {var}: {src}' for p,i,var,src,kind in viol))
    print('fork phase 56 no direct Extended ACE writer checks: PASS')


if __name__ == "__main__":
    test_current_phase56_no_extended_ace_writers()
