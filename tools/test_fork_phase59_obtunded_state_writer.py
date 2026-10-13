#!/usr/bin/env python3
"""Phase 59 regression: persistent obtundation state tuple has one mutation endpoint."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
FUN=ROOT/'addons/acm_extended/functions'

def read(rel): return (ROOT/rel).read_text(encoding='utf-8',errors='replace')
assert 'class obtundedStateCommit {};' in read('addons/acm_extended/config.cpp')
commit=read('addons/acm_extended/functions/fn_obtundedStateCommit.sqf')
for key in ('ACME_obtunded','ACME_obtunded_manual','ACME_obtunded_posture'):
    assert key in commit
assert 'if (_on) then {"free"} else {""}' in commit
for rel in ('fn_obtundedSet.sqf','fn_obtundedApply.sqf','fn_respawnClinicalReset.sqf','fn_clearAllAilments.sqf'):
    assert 'ACME_fnc_obtundedStateCommit' in read('addons/acm_extended/functions/'+rel), rel
from current_source_contracts import _has
respawn=read('addons/acm_extended/functions/fn_registerRhythmLifecycleRuntime.sqf')
assert _has(respawn, '[_newUnit, _issuedAt] call ACME_fnc_respawnClinicalReset;')
assert _has(respawn, '[_u, _issuedAt] call ACME_fnc_respawnClinicalReset;')
clear=read('addons/acm_extended/functions/fn_clearAllAilments.sqf')
assert '"ACME_obtunded", "ACME_obtunded_manual", "ACME_obtunded_posture"' not in clear
viol=[]
keys='(?:ACME_obtunded|ACME_obtunded_manual|ACME_obtunded_posture)'
for p in FUN.rglob('*.sqf'):
    if p.name=='fn_obtundedStateCommit.sqf': continue
    for i,raw in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
        code=raw.split('//',1)[0]
        if re.search(r'setVariable\s*\[\s*["\']'+keys+r'["\']',code):
            viol.append((p,i,raw.strip()))
assert not viol, '\n'.join(f'{p.relative_to(ROOT)}:{i}: {s}' for p,i,s in viol)
print('fork phase 59 obtunded-state writer checks: PASS')
