"""Run the shared client fallback and check the runtime scheduling boundaries."""
from test_menu_death_lifecycle import adapt, execute, read


def test_two_huds_share_one_fallback_and_do_not_retain_a_released_patient():
    source = read("bvmVisualPatient").replace(
        '(_provider nearEntities ["CAManBase", 10])', '(call _nearby)'
    ).replace("alive _patient", "true").replace("_provider distance _patient", "1")
    execute("private _find = {" + adapt(source) + "};" + r"""
        private _nowTime = 10;
        private _scans = 0;
        private _fixturePatient = _patient;
        private _nearby = {_scans = _scans + 1; [_fixturePatient]};
        _patient setVariable ["ACM_breathing_BVM_Medic", _medic];
        missionNamespace setVariable ["ACM_breathing_BVMTarget", objNull];
        [([_medic] call _find) isEqualTo _patient, "fallback missed the provider"] call _check;
        [([_medic] call _find) isEqualTo _patient && {_scans == 1}, "second HUD repeated the scan"] call _check;
        _patient setVariable ["ACM_breathing_BVM_Medic", objNull];
        [([_medic] call _find) isEqualTo objNull, "cached patient outlived their provider receipt"] call _check;
        missionNamespace setVariable ["ACM_breathing_BVMTarget", _patient];
        _medic setVariable ["ACM_breathing_isUsingBVM", true];
        [([_medic] call _find) isEqualTo _patient && {_scans == 1}, "native activity waited for the cache"] call _check;
        missionNamespace setVariable ["ACM_breathing_BVMTarget", objNull];
        _nowTime = 10.3;
        [([_medic] call _find) isEqualTo objNull && {_scans == 2}, "fallback expiry did not resample"] call _check;
    """)


def test_fridge_stock_and_ventilator_lighting_have_independent_cadences():
    fridge_init = read("initBloodStorageRuntime")
    assert 'ACME_fnc_bloodFridgeStockTick }, 1,' in fridge_init
    assert 'ACME_fnc_bloodFridgeTick }, 0.25,' in fridge_init
    assert "ACME_fnc_bloodFridgeExpire" not in read("bloodFridgeTick")
    assert "ACME_fnc_bloodFridgeExpire" in read("bloodFridgeTakeOwner")
    vent = read("ventPanelTick")
    assert vent.index('"ACME_vent_ambientNextAt", diag_tickTime + 0.1') < vent.index("_provider nearObjects _rad")
    assert "ACME_fnc_bvmVisualPatient" in read("bvmVentTick")
    assert "ACME_fnc_bvmVisualPatient" in read("emmaTick")
