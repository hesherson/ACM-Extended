"""Cross-config inventory invariants for the contributed item weights.

These checks detect preparation changing an item's native encumbrance or losing
its medical classification. Engine load limits remain covered by in-game tests.
"""
from decimal import Decimal
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXT = (ROOT / "addons/acm_extended/config.cpp").read_text()
WEAPONS = EXT[EXT.index("class CfgWeapons {"):]
MAGAZINES = EXT[EXT.index("class CfgMagazines {"):EXT.index("class CfgWeapons {")]
CIRCULATION = (ROOT / "addons/circulation/CfgWeapons.hpp").read_text()
NATIVE_MAGS = (ROOT / "addons/circulation/CfgMagazines.hpp").read_text()
BLOOD = (ROOT / "addons/circulation/CfgWeapons_Blood.hpp").read_text()


def body(source, name):
    match = re.search(rf"\bclass\s+{re.escape(name)}\s*(?::[^{{;]+)?\{{", source)
    assert match, f"missing config class {name}"
    depth = 1
    for index in range(match.end(), len(source)):
        depth += (source[index] == "{") - (source[index] == "}")
        if depth == 0:
            return source[match.end():index]
    raise AssertionError(f"unclosed config class {name}")


def number(source, name, prop):
    match = re.search(rf"\b{prop}\s*=\s*(\d+(?:\.\d+)?)\s*;", body(source, name))
    assert match, f"missing {prop} in {name}"
    return Decimal(match[1])


def mass(source, name):
    return number(source, name, "mass")


def test_autoinjector_weight_does_not_replace_medical_classification():
    source = (ROOT / "addons/cbrn/CfgWeapons.hpp").read_text()
    assert number(source, "ACM_Autoinjector_ATNA", "ACE_isMedicalItem") == 1
    assert mass(source, "ACM_Autoinjector_ATNA") == Decimal("1.8")
    assert "class ACM_Autoinjector_Midazolam: ACM_Autoinjector_ATNA" in source


def test_filled_oxygen_tank_cannot_weigh_less_than_empty_tank():
    full = (ROOT / "addons/breathing/CfgMagazines.hpp").read_text()
    empty = (ROOT / "addons/breathing/CfgWeapons.hpp").read_text()
    assert mass(full, "ACM_OxygenTank_425") > mass(empty, "ACM_OxygenTank_425_Empty")
    assert number(full, "ACM_OxygenTank_425", "count") == 283
    assert number(full, "ACM_OxygenTank_425", "ACE_isMedicalItem") == 1


@pytest.mark.parametrize("size", [1, 3, 5, 10])
def test_prepared_syringe_carrier_matches_empty_syringe(size):
    assert mass(MAGAZINES, f"ACME_PreparedSyringe_{size}") == mass(CIRCULATION, f"ACM_Syringe_{size}")


def test_native_prepared_syringe_magazines_match_each_empty_size():
    assert mass(NATIVE_MAGS, "ACM_Syringe_10_Epinephrine") == mass(CIRCULATION, "ACM_Syringe_10")
    entries = re.findall(r"PREPARE_SYRINGE\(\d+,([\d.]+),(\d+),", NATIVE_MAGS)
    assert len(entries) >= 40
    for value, size in entries:
        assert Decimal(value) == mass(CIRCULATION, f"ACM_Syringe_{size}")


def test_extended_prepared_syringes_match_each_empty_size():
    names = re.findall(r"class\s+(ACM_Syringe_(1|3|5|10)_\w+)\s*:", MAGAZINES)
    assert len(names) >= 40
    for name, size in names:
        assert mass(MAGAZINES, name) == mass(CIRCULATION, f"ACM_Syringe_{size}")


def carrier_masses():
    names = re.findall(r"class\s+(ACME_PreparedIVSet_M\w+)\s*:", MAGAZINES)
    assert len(names) == len(set(names)), "duplicate prepared carrier class"
    return {mass(MAGAZINES, name) for name in names}


# ACE-owned saline/plasma bags retain the attached upstream 250/500/1000 mL
# masses. ACME-owned weights below are read from their actual active configs.
ACE_FLUID_MASSES = [Decimal("2.5"), Decimal("5"), Decimal("10")]
SINGLE_BAGS = [
    "ACME_SalineBag_50", "ACME_SalineBag_100", "ACME_MagnesiumBag",
    "ACME_MannitolBag", "ACME_HTSBag", "ACM_EsmololBag",
    "ACME_PlasmaLyteBag", "ACME_PlasmaLyteBag_500",
    "ACME_PlasmaLyteBag_250", "ACME_PlasmaLyteBag_100", "ACM_Vial_Propofol",
]
BLOOD_BAGS = ["ACM_BloodBag_O_250", "ACM_BloodBag_O_500", "ACM_BloodBag_O_1000"]


@pytest.mark.parametrize("name", SINGLE_BAGS)
def test_each_active_single_bag_has_exact_physical_carrier_mass(name):
    assert mass(WEAPONS, name) + mass(WEAPONS, "ACME_IVLine") in carrier_masses()


@pytest.mark.parametrize("name", BLOOD_BAGS)
def test_blood_preparation_and_y_pairing_preserve_native_mass(name):
    bag = mass(BLOOD, name)
    available = carrier_masses()
    assert bag + mass(WEAPONS, "ACME_IVLine") in available
    saline = ACE_FLUID_MASSES + [mass(WEAPONS, "ACME_SalineBag_50"), mass(WEAPONS, "ACME_SalineBag_100")]
    for reserve in saline:
        assert bag + reserve + mass(WEAPONS, "ACME_YTubing") in available


@pytest.mark.parametrize("size", [250, 500])
def test_fresh_blood_and_typed_blood_use_the_same_mass(size):
    assert mass(BLOOD, f"ACM_FreshBloodBag_{size}") == mass(BLOOD, f"ACM_BloodBag_O_{size}")


@pytest.mark.parametrize("name", ["ACM_Vial_Norepinephrine", "ACM_SalineFlush_10", "ACM_Thermometer", "ACM_HPMK", "ACM_EMMA", "ACM_CombatGauze"])
def test_inactive_reference_does_not_hide_a_requested_live_weight(name):
    reference = (ROOT / "addons/acm_extended/CfgWeapons.hpp").read_text()
    assert mass(WEAPONS, name) == mass(reference, name)


def test_fentanyl_weight_matches_across_native_and_active_extended_configs():
    assert mass(CIRCULATION, "ACM_Vial_Fentanyl") == mass(WEAPONS, "ACM_Vial_Fentanyl")
