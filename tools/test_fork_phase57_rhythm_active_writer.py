#!/usr/bin/env python3
"""Phase 57 regression: ACME_rhythm_active has one mutation endpoint."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
EXT=ROOT/'addons/acm_extended'

def read(rel): return (ROOT/rel).read_text(encoding='utf-8',errors='replace')
assert 'class rhythmActiveCommit {};' in read('addons/acm_extended/config.cpp')
commit=read('addons/acm_extended/functions/fn_rhythmActiveCommit.sqf')
assert '"ACME_rhythm_active"' in commit
assert 'ACME_fnc_setVarNet' in commit and 'setVariable' in commit
for rel in (
 'addons/acm_extended/functions/fn_rhythmSet.sqf',
 'addons/acm_extended/functions/fn_rhythmRelease.sqf',
 'addons/acm_extended/functions/fn_megacodeDie.sqf',
 'addons/acm_extended/functions/fn_megacodeSetRhythm.sqf',
 'addons/acm_extended/functions/fn_megacodeScenarioTick.sqf',
 'addons/acm_extended/functions/fn_megacodeResetUnit.sqf',
 'addons/acm_extended/functions/fn_megacodeSpawn.sqf',
 'addons/acm_extended/functions/fn_respawnClinicalReset.sqf',
):
    assert 'ACME_fnc_rhythmActiveCommit' in read(rel), rel
from current_source_contracts import _has
respawn=read('addons/acm_extended/functions/fn_registerRhythmLifecycleRuntime.sqf')
assert _has(respawn, '[_newUnit, _issuedAt] call ACME_fnc_respawnClinicalReset;')
assert _has(respawn, '[_u, _issuedAt] call ACME_fnc_respawnClinicalReset;')
viol=[]
for p in (EXT/'functions').rglob('*.sqf'):
    if p.name=='fn_rhythmActiveCommit.sqf': continue
    for i,raw in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
        line=raw.split('//',1)[0]
        if re.search(r'setVariable\s*\[\s*["\']ACME_rhythm_active["\']',line): viol.append((p,i,raw.strip()))
        if 'ACME_fnc_setVarNet' in line and re.search(r'\[\s*[^,\]]+\s*,\s*["\']ACME_rhythm_active["\']\s*,',line): viol.append((p,i,raw.strip()))
assert not viol, '\n'.join(f'{p.relative_to(ROOT)}:{i}: {s}' for p,i,s in viol)
print('fork phase 57 rhythm-active writer checks: PASS')
