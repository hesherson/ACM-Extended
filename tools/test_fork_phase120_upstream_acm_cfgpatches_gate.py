"""B237: executable legacy source contract; failures must not block collection."""

def test_source_contract():
    """Phase 120: preserve all native upstream ACM CfgPatches identities inside the combined fork."""
    from pathlib import Path
    import re
    ROOT=Path(__file__).resolve().parents[1]
    expected={x.strip().casefold() for x in (ROOT/'tools/upstream_acm_cfgpatches_manifest.txt').read_text().splitlines() if x.strip() and not x.startswith('#')}
    assert len(expected)==12
    actual=set()
    for addon in sorted((ROOT/'addons').iterdir()):
        if not addon.is_dir() or addon.name in ('acm_extended','itemtext') or not (addon/'config.cpp').is_file(): continue
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

    # Item-text compatibility is an additional local addon, not a replacement for a native ACM identity.
    itemtext=(ROOT/'addons/itemtext/config.cpp').read_text()
    assert 'class ACM_itemtext' in itemtext
    assert 'requiredAddons' in itemtext


if __name__ == "__main__":
    test_source_contract()
