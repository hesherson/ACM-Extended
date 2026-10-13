#!/usr/bin/env python3
"""Phase 58 regression: HPMK state/on pair has one mutation endpoint."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
FUN=ROOT/'addons/acm_extended/functions'

def read(rel): return (ROOT/rel).read_text(encoding='utf-8',errors='replace')
assert 'class hpmkStateCommit {};' in read('addons/acm_extended/config.cpp')
commit=read('addons/acm_extended/functions/fn_hpmkStateCommit.sqf')
for k in ('ACME_hpmk_state','ACME_hpmk_on','wrapped','exposed','prepped'):
    assert k in commit
for rel in (
 'fn_hpmkPrep.sqf','fn_hpmkWrap.sqf','fn_hpmkUnwrap.sqf','fn_hpmkCoverChest.sqf',
 'fn_hpmkExposeChest.sqf','fn_hpmkRemove.sqf','fn_hpmkBlanketTick.sqf','fn_respawnClinicalReset.sqf','fn_clearAllAilments.sqf'
):
    assert 'ACME_fnc_hpmkStateCommit' in read('addons/acm_extended/functions/'+rel), rel
from current_source_contracts import _has
respawn=read('addons/acm_extended/functions/fn_registerRhythmLifecycleRuntime.sqf')
assert _has(respawn, '[_newUnit, _issuedAt] call ACME_fnc_respawnClinicalReset;')
assert _has(respawn, '[_u, _issuedAt] call ACME_fnc_respawnClinicalReset;')
clear=read('addons/acm_extended/functions/fn_clearAllAilments.sqf')
assert '"ACME_hpmk_on", "ACME_hpmk_state"' not in clear
viol=[]
for p in FUN.rglob('*.sqf'):
    if p.name=='fn_hpmkStateCommit.sqf': continue
    for i,raw in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
        code=raw.split('//',1)[0]
        if re.search(r'setVariable\s*\[\s*["\']ACME_hpmk_(?:state|on)["\']',code): viol.append((p,i,raw.strip()))
        if 'ACME_fnc_setVarNet' in code and re.search(r'\[\s*[^,\]]+\s*,\s*["\']ACME_hpmk_(?:state|on)["\']\s*,',code): viol.append((p,i,raw.strip()))
assert not viol, '\n'.join(f'{p.relative_to(ROOT)}:{i}: {s}' for p,i,s in viol)
print('fork phase 58 HPMK state-writer checks: PASS')
