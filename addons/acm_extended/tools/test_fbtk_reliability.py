from pathlib import Path

ADDONS = Path(__file__).resolve().parents[2]
CIRC = ADDONS / "circulation" / "functions"
CORE = ADDONS / "core" / "overrides"
EXT = ADDONS / "acm_extended" / "functions"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="strict")


def test_fbtk_is_rejected_on_io_before_inventory_is_consumed():
    s = read(CIRC / "fnc_TransfusionMenu_AddBag.sqf")
    gate = s.index('FBTK blood collection requires IV access')
    consume = s.index('removeItem _itemClassname')
    assert gate < consume
    assert '(_itemClassname in FBTK_ARRAY)' in s
    assert '!GVAR(TransfusionMenu_SelectIV)' in s


def test_fbtk_full_boundary_yields_nominal_bag_size():
    s = read(CIRC / "fnc_TransfusionMenu_RemoveBag.sqf")
    assert 'ACME_fbtk_fullToleranceMl' in s
    assert '_tol = (_tol max 0) min 5;' in s
    assert '_remainingVolume >= ((_volume - _tol) max 0)' in s
    assert 'format ["ACM_FieldBloodTransfusionKit_%1", _volume]' in s


def test_fbtk_collection_conserves_volume_and_cannot_overdraw_donor():
    s = read(CIRC / "fnc_getBloodVolumeChange.sqf")
    f = s.index('if (_type == "FBTK") then {', s.index('ACME_fnc_medicationLineFraction'))
    a = s.index('private _admitted = _bagChange * _fluidPassRatio;', f)
    block = s[f:a]
    assert '_bagChange = _bagChange * _fluidPassRatio;' in block
    assert '_fluidPassRatio = 1;' in block
    assert 'private _donorAvailableMl' in block
    assert '_bagChange = _bagChange min _donorAvailableMl;' in block
    assert '_bagVolumeRemaining = (_bagVolumeRemaining + _bagChange) min _originalVolume;' in s
    assert '_bloodVolumeChange = _bloodVolumeChange - (_admitted / 1000);' in s


def test_fbtk_ui_explains_iv_only_collection():
    s = read(EXT / "fn_updateTransfusionControls.sqf")
    assert 'private _selIsFBTK' in s
    assert '_selIsFBTK && {!_ivSel}' in s
    assert '_txt = "IV required";' in s


def test_fresh_blood_mp_registry_and_metadata_handoff_remain_present():
    post = read(ADDONS / "circulation" / "XEH_postInit.sqf")
    iv = read(CORE / "fnc_ivBag.sqf")
    local = read(CORE / "fnc_ivBagLocal.sqf")
    assert 'requestFreshBloodBag' in post
    assert 'receiveFreshBloodBag' in post
    assert 'requestFreshBloodRegistry' in post
    assert '_freshBloodEntry' in iv
    assert '_freshBloodEntryNet' in local
