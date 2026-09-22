from pathlib import Path
import re, hashlib, sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
CFG = (ROOT / 'config.cpp').read_text(encoding='utf-8')

checks = []
def check(name, ok, detail=''):
    checks.append((name, bool(ok), detail))

check('version r41', 'version = "1.0.100-r41";' in CFG)
POST=(ROOT/'functions'/'fn_postInit.sqf').read_text(encoding='utf-8')
check('runtime version r41', 'ACME_infusion_version = "1.0.100-r41"' in POST)
check('runtime batch B77', 'ACME_buildBatch = "B77";' in POST)
check('CfgMods ACM_Extended', 'class CfgMods' in CFG and 'class ACM_Extended' in CFG)
check('full logo path', 'logo = "\\acm_extended\\ui\\ACME_logo.paa";' in CFG)
check('small logo path', 'logoSmall = "\\acm_extended\\ui\\ACME_logo_small.paa";' in CFG)
check('logo file exists', (ROOT/'ui'/'ACME_logo.paa').is_file())
check('small logo exists', (ROOT/'ui'/'ACME_logo_small.paa').is_file())

# Exact uploaded source sizes/hashes for this batch.
expected = {
    'ACME_logo.paa': (606700, 'b83a782ad55470f9317883051c64363ec735e61191514d08866a36f14680718f'),
    'ACME_logo_small.paa': (65912, '0dffbc13af3b5b9ed63ef02b770683d8ef60ed97079b1180ce72dbf2ca9de5c8'),
}
for name,(size,sha) in expected.items():
    p=ROOT/'ui'/name
    data=p.read_bytes() if p.exists() else b''
    check(f'{name} exact size', len(data)==size, str(len(data)))
    check(f'{name} exact sha256', hashlib.sha256(data).hexdigest()==sha, hashlib.sha256(data).hexdigest())

# The B77 classes that are ACME-owned inventory items must carry the new mod identity and author.
owned_weapons = {
    'ACME_HTSBag','ACME_HTSBullet','ACME_MannitolVial','ACME_Ventilator','ACME_VentBattery',
    'ACME_Laryngoscope','ACME_ETTube','ACME_MagnesiumBag','ACME_MannitolBag','ACME_PlasmaLyteBag',
    'ACME_PlasmaLyteBag_500','ACME_PlasmaLyteBag_250','ACME_PlasmaLyteBag_100','ACME_SalineBag_50',
    'ACME_SalineBag_100','ACME_Spray_Esketamine','ACME_Vial_EpinephrineCardiac','ACM_Vial_EpinephrineCardiac',
    'ACM_Vial_Norepinephrine','ACM_Vial_Phentolamine','ACM_Vial_Hyaluronidase','ACM_Vial_Rocuronium',
    'ACM_Vial_Sugammadex','ACM_Vial_Ceftriaxone','ACM_Vial_CalciumGluconate','ACM_Vial_Propofol',
    'ACM_Vial_Midazolam','ACM_Vial_Fentanyl','ACME_IVLine','ACME_YTubing','ACME_BloodWarmer',
    'ACME_PressureInfuser','ACME_NARBOA','ACM_EsmololBag','ACM_IV_18g','ACM_IV_20g','ACM_SalineFlush_10',
    'ACM_Thermometer','ACM_NRBMask','ACM_HPMK','ACM_EMMA','ACM_CombatGauze','ACME_NARSPEAR','ACME_AAJT_S',
    'ACME_XStat','ACME_SpoiledBlood','ACME_BloodCooler_CSWB1U','ACME_BloodCooler_CSWB2U','ACME_BloodCooler_CSWB4U'
}
owned_mags = {f'ACM_Syringe_{size}_{drug}' for drug in [
    'EpinephrineCardiac','Norepinephrine','Phentolamine','Hyaluronidase','Midazolam','Rocuronium',
    'Sugammadex','CalciumGluconate','Propofol','Ceftriaxone'] for size in [10,5,3,1]}

def get_root_block(root):
    m=re.search(rf'class\s+{root}\s*\{{', CFG)
    assert m
    start=m.end()-1; d=0
    for i in range(start,len(CFG)):
        if CFG[i]=='{': d+=1
        elif CFG[i]=='}':
            d-=1
            if d==0: return CFG[start+1:i]
    raise AssertionError(root)

def child_body(block, name):
    m=re.search(rf'(?m)^\s*class\s+{re.escape(name)}(?:\s*:\s*[A-Za-z0-9_]+)?\s*\{{', block)
    if not m: return None
    start=m.end()-1; d=0
    for i in range(start,len(block)):
        if block[i]=='{': d+=1
        elif block[i]=='}':
            d-=1
            if d==0: return block[start+1:i]
    return None

for root, names in [('CfgWeapons', owned_weapons), ('CfgMagazines', owned_mags)]:
    block=get_root_block(root)
    for name in sorted(names):
        body=child_body(block,name)
        check(f'{root}/{name} present', body is not None)
        if body is not None:
            check(f'{root}/{name} author', re.search(r'(?m)^\s*author\s*=\s*"mavis"\s*;', body) is not None)
            check(f'{root}/{name} logo identity', re.search(r'(?m)^\s*dlc\s*=\s*"ACM_Extended"\s*;', body) is not None)

# Native ACM acetaminophen override remains attributed to ACM and is not rebranded as an ACME item.
mag = get_root_block('CfgMagazines')
para = child_body(mag, 'ACM_Paracetamol') or ''
check('native ACM paracetamol author preserved', 'author = "Blue";' in para)
check('native ACM paracetamol no ACME dlc', 'dlc = "ACM_Extended";' not in para)

@pytest.mark.parametrize("name,ok,detail", checks, ids=[row[0] for row in checks])
def test_historical_branding_contract(name, ok, detail):
    # Historical checks are intentionally retained; old branding/version failures
    # are newly visible debt, not a request to rebrand current game items.
    assert ok, f"{name}: {detail}"

if __name__ == "__main__":
    failed = [c for c in checks if not c[1]]
    for name, ok, detail in checks:
        if not ok:
            print('FAIL:', name, detail)
    print(f'{len(checks)-len(failed)}/{len(checks)} checks passed')
    sys.exit(bool(failed))
