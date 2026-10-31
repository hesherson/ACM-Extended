"""B262: execute NRB donor selection; ensure zero-charge reserve never masks a kit."""
from pathlib import Path

from test_menu_death_lifecycle import adapt, execute

F = Path(__file__).resolve().parents[1] / "functions"
B = F.parents[1] / "breathing" / "functions"


def source(name):
    return (F / ("fn_" + name + ".sqf")).read_text(encoding="utf-8-sig")


def test_nrb_donor_selection_executes_with_kit_and_loose_cylinders():
    original = source("nrbOxygenSource")
    # Only substitute the engine's worn-container/cargo read. Donor selection,
    # short-circuit evaluation and treatment-supply order remain production SQF.
    assert "[uniformContainer _unit, vestContainer _unit, backpackContainer _unit]" in original
    adapted = original.replace(
        "[uniformContainer _unit, vestContainer _unit, backpackContainer _unit]",
        "([_unit] call ACME_test_containers)"
    ).replace("magazinesAmmoCargo _x", "_x")
    execute(r"""
        ACME_test_kitMedic = 1;
        ACME_test_kitPatient = 0;
        ACME_test_cargoMedic = [];
        ACME_test_cargoPatient = [];
        ACME_fnc_treatmentSupplyOrder = {[_medic, _patient]};
        ACME_test_containers = {
            if ((_this select 0) isEqualTo _medic)
            then {ACME_test_cargoMedic}
            else {ACME_test_cargoPatient}
        };
        ACME_fnc_itemCount = {
            if ((_this select 0) isEqualTo _medic)
            then {ACME_test_kitMedic}
            else {ACME_test_kitPatient}
        };
    """ + "ACME_fnc_nrbOxygenSource = {" + adapt(adapted) + "};" + r"""
        [([_medic, _patient] call ACME_fnc_nrbOxygenSource) isEqualTo objNull,
            "no-EFAK kit count incorrectly authorizes oxygen"] call _check;
        efak_medical_fnc_drawCharge = {1};
        [([_medic, _patient] call ACME_fnc_nrbOxygenSource) isEqualTo _medic,
            "EFAK kit-only cylinder missing as oxygen source"] call _check;
        ACME_test_kitMedic = 0;
        ACME_test_kitPatient = 1;
        [([_medic, _patient] call ACME_fnc_nrbOxygenSource) isEqualTo _patient,
            "patient's EFAK kit oxygen missing"] call _check;
        ACME_test_kitMedic = 1;
        ACME_test_cargoPatient = [[["ACM_OxygenTank_425", 9]]];
        [([_medic, _patient] call ACME_fnc_nrbOxygenSource) isEqualTo _medic,
            "medic's kit must take donor priority over patient's loose tank"] call _check;
        ACME_test_kitMedic = 0;
        [([_medic, _patient] call ACME_fnc_nrbOxygenSource) isEqualTo _patient,
            "loose oxygen donor not selected when kit unavailable"] call _check;
        ACME_test_cargoPatient = [[["ACM_OxygenTank_425", 0]]];
        [([_medic, _patient] call ACME_fnc_nrbOxygenSource) isEqualTo _patient,
            "patient's valid EFAK kit was ignored after zero-charge loose cylinder"] call _check;
        ACME_test_kitPatient = 0;
        [([_medic, _patient] call ACME_fnc_nrbOxygenSource) isEqualTo objNull,
            "zero-charge tank incorrectly accepted as oxygen"] call _check;
        ACME_test_cargoMedic = [[["ACM_OxygenTank_425", 6]]];
        [([_medic, _patient] call ACME_fnc_nrbOxygenSource) isEqualTo _medic,
            "positive loose reserve rejected"] call _check;
    """)


def test_kit_eligibility_and_owner_local_reserve_debit_agree():
    source_code = source("nrbOxygenSource")
    draw = source("nrbOxygenDraw")
    native = (B / "fnc_useOxygenTankReserve.sqf").read_text(encoding="utf-8-sig")
    count = source("itemCount")
    assert 'if (!_available && {!isNil "efak_medical_fnc_drawCharge"}) then {' in source_code
    assert '([_unit, "ACM_OxygenTank_425"] call ACME_fnc_itemCount) > 0' in source_code
    assert 'efak_medical_fnc_countItem' in count
    assert '_source' in draw and '[_source] call ACM_breathing_fnc_useOxygenTankReserve' in draw
    assert 'if (_magClassname == "ACM_OxygenTank_425" && {_magCount > 0}) then {' in native
    assert 'if (!_found && {!isNil "efak_medical_fnc_drawCharge"}) then {' in native
    assert '[_unit, "ACM_OxygenTank_425"] call efak_medical_fnc_drawCharge' in native
    assert 'if (_left == 0) then {' in native
