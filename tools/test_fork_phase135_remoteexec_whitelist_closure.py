#!/usr/bin/env python3
"""Phase 135: every fork-owned remoteExec target is represented in CfgRemoteExec without changing global mode."""
import re
from pathlib import Path
R=Path(__file__).resolve().parents[1]
configs=[p.read_text() for p in (R/'addons').rglob('config.cpp')]
# Config contributions merge across addons, including BATDOK and equipment.
remote_cfg='\n'.join(c[c.index('class CfgRemoteExec'):] for c in configs if 'class CfgRemoteExec' in c)
# Do not seize mission-wide policy; only contribute named entries.
assert not re.search(r'\bmode\s*=', remote_cfg)
refs=set()
for p in (R/'addons').rglob('*.sqf'):
    txt=p.read_text(errors='ignore')
    # remove // comments so documentation examples do not create false remote targets
    txt='\n'.join(line.split('//',1)[0] for line in txt.splitlines())
    for m in re.finditer(r'remoteExec(?:Call)?\s*\[\s*"([^"]+)"', txt):
        n=m.group(1)
        if n.startswith('ACME_fnc_') or n=='ACM_airway_fnc_remoteSay3D':
            refs.add(n)
whitelisted=set(re.findall(r'class\s+((?:ACME|ACM)_\w+_fnc_\w+|ACME_fnc_\w+|ACM_airway_fnc_\w+)\s*\{', remote_cfg))
missing=sorted(refs-whitelisted)
assert not missing, missing
for server_only in ['ACME_fnc_bloodColdChainNudge','ACME_fnc_bloodFridgeSpawn','ACME_fnc_megacodeCableApply','ACME_fnc_remoteDeleteVehicle']:
    assert re.search(r'class\s+'+re.escape(server_only)+r'\s*\{[^}]*allowedTargets\s*=\s*2\s*;', remote_cfg, re.S), server_only
assert re.search(r'class\s+ACME_fnc_coolerBoxApplyScale\s*\{[^}]*jip\s*=\s*1\s*;', remote_cfg, re.S)
print(f'PASS phase135: {len(refs)} fork-owned remoteExec targets covered by named CfgRemoteExec entries')
