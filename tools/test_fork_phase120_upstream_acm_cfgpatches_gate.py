#!/usr/bin/env python3
"""Phase 120: preserve all native upstream ACM CfgPatches identities inside the combined fork."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
expected={x.strip().casefold() for x in (ROOT/'tools/upstream_acm_cfgpatches_manifest.txt').read_text().splitlines() if x.strip() and not x.startswith('#')}
assert len(expected)==12
expected_components={name.removeprefix('acm_') for name in expected}
actual=set()
for addon in sorted((ROOT/'addons').iterdir()):
    # This is a preservation test for the supplied ACM source components. MDF
    # feature PBOs are intentionally additional and must not change this set.
    if not addon.is_dir() or addon.name not in expected_components or not (addon/'config.cpp').is_file(): continue
    if addon.name=='main': component='main'
    else:
        sc=addon/'script_component.hpp'; assert sc.is_file(),addon
        m=re.search(r'^\s*#define\s+COMPONENT\s+([A-Za-z0-9_]+)\s*$',sc.read_text(encoding='utf-8',errors='replace'),re.M)
        assert m,addon
        component=m.group(1)
    actual.add(f'ACM_{component}'.casefold())
assert actual==expected, f'native CfgPatches identity drift: missing={sorted(expected-actual)} extra={sorted(actual-expected)}'
ext_cfg=(ROOT/'addons/acm_extended/config.cpp').read_text(encoding='utf-8',errors='replace')
assert re.search(r'class\s+ACM_Extended\s*\{',ext_cfg), 'Extended CfgPatches identity missing'
print('PASS phase120: 12/12 supplied upstream ACM CfgPatches identities preserved plus ACM_Extended')
