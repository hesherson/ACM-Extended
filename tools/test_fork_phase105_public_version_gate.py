#!/usr/bin/env python3
"""Phase 105: keep public/runtime/debug version identity set to v1.2.4."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / 'addons/acm_extended/config.cpp'
START = ROOT / 'addons/acm_extended/functions/fn_initForkStartupRuntime.sqf'
DEBUG = [ROOT / 'addons/acm_extended/functions' / name for name in (
    'fn_debugMenuClinical.sqf',
)]
EXPECTED = '1.2.4'


def main() -> None:
    cfg = CFG.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'class\s+ACM_Extended\s*\{.*?\bversion\s*=\s*"([^"]+)"\s*;', cfg, re.S)
    assert m, 'ACM_Extended CfgPatches version missing'
    assert m.group(1) == EXPECTED, m.group(1)

    start = START.read_text(encoding='utf-8', errors='replace')
    assert 'getText (configFile >> "CfgPatches" >> "ACM_Extended" >> "version")' in start
    assert f'ACME_infusion_version = "{EXPECTED}"' in start
    batch = re.search(r'ACME_buildBatch\s*=\s*"(B\d+)"\s*;', start)
    assert batch, 'internal build batch stamp missing or malformed'

    for page in DEBUG:
        debug = page.read_text(encoding='utf-8', errors='replace')
        assert 'configFile >> "CfgPatches" >> "ACM_Extended" >> "version"' in debug
        assert 'ACME_infusion_version' in debug

    # Public runtime code must not hard-code an obsolete pre-1.1 public version. Historical tests/docs are excluded.
    obsolete=[]
    for path in sorted((ROOT/'addons/acm_extended/functions').glob('*.sqf')):
        text=path.read_text(encoding='utf-8',errors='replace')
        for token in re.findall(r'"((?:0\.9\.[^"]+)|(?:1\.0\.100[^\"]*))"', text):
            obsolete.append(f'{path.relative_to(ROOT)}: {token}')
    assert not obsolete, 'obsolete public/runtime version literals:\n'+'\n'.join(obsolete[:50])

    print(f'fork phase 105 public-version gate: PASS (public {EXPECTED}, internal {batch.group(1)})')

if __name__=='__main__': main()
