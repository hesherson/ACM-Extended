from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]; FUN=ROOT/'addons/acm_extended/functions'

def test_exact_original_contract():
    owner=FUN/'fn_narcStoreCommit.sqf'
    assert owner.exists()
    assert 'class narcStoreCommit {};' in (ROOT/'addons/acm_extended/config.cpp').read_text(errors='ignore')
    pat=re.compile(r'setVariable\s*\[\s*["\']ACME_narcStore["\']')
    viol=[]
    for p in FUN.glob('*.sqf'):
        if p==owner: continue
        if pat.search(p.read_text(errors='ignore')): viol.append(p.name)
    assert not viol, viol


if __name__ == '__main__':
    test_exact_original_contract()
    print('phase87 narc store owner: PASS')
