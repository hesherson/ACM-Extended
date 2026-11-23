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
    assert 'ACME_fnc_coolerBoxRequest' in read('addons/acm_extended/functions/fn_coolerBoxDeploy.sqf')
    assert 'ACM_core_fnc_setDraggingCapability' in read('addons/acm_extended/functions/fn_coolerBoxBroker.sqf')
    assert 'ACM_core_fnc_setCursorInteractionMode' in read('addons/acm_extended/functions/fn_installLightKey.sqf')
    assert 'ACM_core_fnc_setCursorInteractionMode' in read('addons/acm_extended/functions/fn_aceCursorRestore.sqf')
    # B366-B385 ACM_ -> ACME_ item rename (one item set, no alias classes): ACE Arsenal's stored loadout lists are
    # rewritten to the canonical classnames when the loadouts display opens. Not ACE runtime state; exact file/vars.
    rename_migration={('fn_initItemClassRuntime.sqf','ace_arsenal_saved_loadouts'),
                      ('fn_initItemClassRuntime.sqf','ace_arsenal_defaultLoadoutsList')}
    viol=[]
    for p in EXT.rglob('*.sqf'):
        for i,raw in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
            line=raw.split('//',1)[0]
            if not line.strip(): continue
            m=re.search(r'(?:missionNamespace\s+)?setVariable\s*\[\s*["\'](ace_[^"\']+)["\']',line,re.I)
            if m and (p.name,m.group(1)) not in rename_migration: viol.append((p,i,m.group(1),raw.strip(),'setVariable'))
            if 'ACME_fnc_setVarNet' in line:
                m=re.search(r'\[\s*[^,\]]+\s*,\s*["\'](ace_[^"\']+)["\']\s*,',line,re.I)
                if m: viol.append((p,i,m.group(1),raw.strip(),'setVarNet'))
    if viol:
        raise AssertionError('\n'.join(f'{p.relative_to(ROOT)}:{i}: {kind} {var}: {src}' for p,i,var,src,kind in viol))
    print('fork phase 56 no direct Extended ACE writer checks: PASS')


if __name__ == "__main__":
    test_current_phase56_no_extended_ace_writers()
