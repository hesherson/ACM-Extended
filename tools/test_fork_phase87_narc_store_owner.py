from pathlib import Path
import importlib.util
import sys
ROOT=Path(__file__).resolve().parents[1]; FUN=ROOT/'addons/acm_extended/functions'
_spec=importlib.util.spec_from_file_location('phase87_source_scan',ROOT/'addons/acm_extended/tools/source_scan.py')
_scan=importlib.util.module_from_spec(_spec)
sys.modules[_spec.name]=_scan
_spec.loader.exec_module(_scan)


def _signature(tokens):
    return [(t.kind,t.value.lower() if t.kind=='ident' else t.value) for t in tokens]


def _positions(tokens,statement):
    source=_signature(tokens); wanted=_signature(_scan.lex(statement))
    return [i for i in range(len(source)-len(wanted)+1) if source[i:i+len(wanted)]==wanted]


def _store_writes(tokens):
    return [i for i,t in enumerate(tokens)
            if t.kind=='ident' and t.value.lower()=='setvariable'
            and i+2<len(tokens) and tokens[i+1].value=='['
            and tokens[i+2].kind=='string' and tokens[i+2].value=='ACME_narcStore']


def _top_level(tokens,index):
    pairs=_scan.matching(tokens)
    return not any(a<index<b for a,b in pairs.items() if a<b)


def test_exact_original_contract():
    # B279 adds only the canonical inventory projection endpoint. Both writers
    # require the actual provider-local guard; comments and labels are not proof.
    owner=FUN/'fn_narcStoreCommit.sqf'
    projection=FUN/'fn_skInventoryReconcile.sqf'
    assert owner.exists() and projection.exists()
    cfg=_scan.lex((ROOT/'addons/acm_extended/config.cpp').read_text(errors='ignore'))
    for helper in ('narcStoreCommit','skInventoryReconcile'):
        assert _positions(cfg,'class '+helper+' {};'),helper
    for writer in (owner,projection):
        tokens=_scan.lex(writer.read_text(errors='ignore'))
        writes=_store_writes(tokens)
        assert len(writes)==1,writer.name
        guards=_positions(tokens,'if (isNull _owner || {!local _owner}) exitWith {false};')
        assert any(g<writes[0] and _top_level(tokens,g) for g in guards),writer.name
        assert tokens[writes[0]-1].kind=='ident' and tokens[writes[0]-1].value=='_owner',writer.name
    tokens=_scan.lex(owner.read_text(errors='ignore'))
    assert _positions(tokens,'_owner setVariable ["ACME_narcStore",_store,_public];')
    tokens=_scan.lex(projection.read_text(errors='ignore'))
    write=_store_writes(tokens)[0]
    assert _positions(tokens,'_owner setVariable ["ACME_narcStore",_ordered,_reserved isEqualTo []];')
    # The changed-only branch must actually enclose the projection write. Live
    # reserved rows remain private, rather than becoming inventory-poll broadcasts.
    pairs=_scan.matching(tokens)
    branch='if !(_ordered isEqualTo _current) then {'
    openings=[b+len(_scan.lex(branch))-1 for b in _positions(tokens,branch)]
    assert any(b in pairs and b<write<pairs[b] for b in openings)
    viol=[]
    for p in FUN.glob('*.sqf'):
        if p in {owner,projection}: continue
        text=p.read_text(errors='ignore')
        if 'acme_narcstore' not in text.lower() or 'setvariable' not in text.lower(): continue
        if any(_store_writes(tokens) for tokens in _scan.code_streams(text)):
            viol.append(p.name)
    assert not viol,viol


if __name__ == '__main__':
    test_exact_original_contract()
    print('phase87 narc store owner: PASS')
