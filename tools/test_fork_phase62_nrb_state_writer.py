#!/usr/bin/env python3
"""Phase 62 regression: NRB on/O2/delivery tuple has one mutation endpoint."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
FUN=ROOT/'addons/acm_extended/functions'
def read(rel): return (ROOT/rel).read_text(encoding='utf-8',errors='replace')
assert 'class nrbStateCommit {};' in read('addons/acm_extended/config.cpp')
commit=read('addons/acm_extended/functions/fn_nrbStateCommit.sqf')
for key in ('ACME_nrb_on','ACME_nrb_hasO2','ACME_nrb_delivering'):
    assert key in commit
assert 'if (!_newOn)' in commit and 'if (!_newO2)' in commit
for rel in ('fn_nrbStateLocal.sqf','fn_nrbTick.sqf','fn_nrbOxygenAck.sqf','fn_clinicalRestore.sqf','fn_clinicalReset.sqf','fn_respawnClinicalReset.sqf'):
    assert 'ACME_fnc_nrbStateCommit' in read('addons/acm_extended/functions/'+rel), rel
from current_source_contracts import _has
respawn=read('addons/acm_extended/functions/fn_registerRhythmLifecycleRuntime.sqf')
assert _has(respawn, '[_newUnit, _issuedAt] call ACME_fnc_respawnClinicalReset;')
assert _has(respawn, '[_u, _issuedAt] call ACME_fnc_respawnClinicalReset;')
viol=[]
keys='(?:ACME_nrb_on|ACME_nrb_hasO2|ACME_nrb_delivering)'
for p in FUN.rglob('*.sqf'):
    if p.name=='fn_nrbStateCommit.sqf': continue
    for i,raw in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
        code=raw.split('//',1)[0]
        if re.search(r'setVariable\s*\[\s*["\']'+keys+r'["\']',code): viol.append((p,i,raw.strip()))
        if 'ACME_fnc_setVarNet' in code and re.search(keys,code): viol.append((p,i,raw.strip()))
assert not viol, '\n'.join(f'{p.relative_to(ROOT)}:{i}: {s}' for p,i,s in viol)

gui = read('addons/gui/overrides/fnc_updateInjuryList.sqf')
assert 'ACME_nrb_on' in gui
assert 'ACME_nrb_hasO2' in gui
assert 'NRB [%1 L/min O2]' in gui
assert 'NRB [No O2]' in gui
assert 'if (_selectionN == -1)' in gui
assert 'if (_selectionN in [0,1] && {_nrbOn})' in gui

print('fork phase 62 NRB state-writer checks: PASS')
