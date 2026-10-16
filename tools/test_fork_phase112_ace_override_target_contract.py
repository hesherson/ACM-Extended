"""B240: reviewed current contract, with individually reportable execution."""

def test_current_phase112_ace_override_target_contract():
    #!/usr/bin/env python3
    """Phase 112: freeze compile-time ACE override targets against the supplied ACE3 baseline."""
    from pathlib import Path
    import json, re

    ROOT=Path(__file__).resolve().parents[1]
    MANIFEST=ROOT/'tools/ace_override_target_manifest.json'


    def block(text:str, brace:int)->str:
        depth=0; i=brace; state='code'; quote=''
        while i<len(text):
            c=text[i]; n=text[i+1] if i+1<len(text) else ''
            if state=='line':
                if c=='\n': state='code'
            elif state=='block':
                if c=='*' and n=='/': state='code'; i+=1
            elif state=='string':
                if c==quote and n==quote: i+=1
                elif c==quote: state='code'
            else:
                if c=='/' and n=='/': state='line'; i+=1
                elif c=='/' and n=='*': state='block'; i+=1
                elif c in ('"',"'"): state='string'; quote=c
                elif c=='{': depth+=1
                elif c=='}':
                    depth-=1
                    if depth==0: return text[brace+1:i]
            i+=1
        raise AssertionError('unterminated CfgFunctions class')


    def actual_targets():
        out=[]
        for cfg in [ROOT/'addons/core/CfgFunctions.hpp',ROOT/'addons/gui/CfgFunctions.hpp']:
            text=cfg.read_text(encoding='utf-8',errors='replace')
            for m in re.finditer(r'(?m)^\s{4}class\s+[A-Za-z0-9_]+\s*\{',text):
                body=block(text,text.find('{',m.start()))
                tm=re.search(r'\btag\s*=\s*"(ace_[A-Za-z0-9_]+)"\s*;',body)
                if not tm: continue
                tag=tm.group(1)
                for fm in re.finditer(r'class\s+([A-Za-z0-9_]+)\s*\{[^{}]*?\bfile\s*=\s*QPATHTOF\(([^)]+)\)\s*;[^{}]*?\};',body,re.S):
                    out.append((tag,fm.group(1),cfg.parent.name,fm.group(2).replace('\\','/')))
        return sorted(out,key=lambda x:(x[0].casefold(),x[1].casefold()))

    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))['targets']
    expected=sorted(((x['tag'],x['function'],x['owner_addon'],x['local'].split('/',1)[1]) for x in manifest),key=lambda x:(x[0].casefold(),x[1].casefold()))
    actual=actual_targets()
    # Reviewed additions support the current inventory transaction/menu lifecycle; the physical
    # bandage invariant deliberately retired our bandage-opening override. No other delta is allowed.
    added = {
        ('ace_medical_treatment','hasItem','core','overrides/fnc_hasItem.sqf'),
        ('ace_medical_treatment','useItem','core','overrides/fnc_useItem.sqf'),
        ('ace_medical_gui','onMenuClose','gui','overrides/fnc_onMenuClose.sqf'),
    }
    retired = {('ace_medical_treatment','handleBandageOpening','core','overrides/fnc_handleBandageOpening.sqf')}
    assert set(actual)-set(expected)==added, 'unreviewed ACE override addition or missing current target'
    assert set(expected)-set(actual)==retired, 'unreviewed ACE override removal or retired target restored'
    assert len(actual)==len(set(actual))==72, 'duplicate/missing ACE override target'
    from current_source_contracts import _has
    assert _has((ROOT/'addons/core/overrides/fnc_hasItem.sqf').read_text(), 'call ACME_fnc_carrierInventoryGet')
    assert _has((ROOT/'addons/core/overrides/fnc_useItem.sqf').read_text(), 'call ACME_fnc_carrierSupplyTake')
    for tag,fn,owner,local in actual:
        assert (ROOT/'addons'/owner/local).is_file(), f'missing local override source: {owner}/{local}'
    missing=[(x['tag'],x['function']) for x in manifest if not x['upstream_present']]
    assert missing==[('ace_medical_status','getBloodVolumeChange')], f'unexpected ACE source exceptions: {missing}'
    assert len(manifest)==70
    print('PASS phase112: 72 current ACE targets, original 70-entry manifest plus explicit reviewed delta')


if __name__ == "__main__":
    test_current_phase112_ace_override_target_contract()
