"""B237: executable legacy source contract; failures must not block collection."""

def test_source_contract():
    """Phase 116: preserve HEMTT project/package identity required by ACM public path compatibility."""
    from pathlib import Path
    import tomllib
    ROOT=Path(__file__).resolve().parents[1]
    project=tomllib.loads((ROOT/'.hemtt/project.toml').read_text(encoding='utf-8'))
    assert project.get('name')=='ACM Extended'
    assert project.get('author')=='mavis'
    assert project.get('prefix')=='ACM', 'HEMTT prefix must remain ACM for x\\ACM public path compatibility'
    assert project.get('mainprefix')=='x', 'HEMTT mainprefix must remain x'
    includes=project.get('files',{}).get('include',[])
    for required in ['mod.cpp','logo.paa','logo_small.paa']:
        assert required in includes, f'HEMTT package include missing {required}'
        assert (ROOT/required).is_file(), f'HEMTT package file absent: {required}'
    assert project.get('version',{}).get('git_hash')==0
    mod=(ROOT/'mod.cpp').read_text(encoding='utf-8',errors='replace')
    assert 'name = "ACM Extended";' in mod and 'stable release' in mod and 'external ACM is not required' in mod
    print('PASS phase116: HEMTT project keeps x/ACM compatibility identity and required root package files')


if __name__ == "__main__":
    test_source_contract()
