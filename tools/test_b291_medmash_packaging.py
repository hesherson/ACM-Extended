"""B290-to-B291 installation upgrades retain exact artifacts and rollback safety."""
import pytest

from test_b236_deployment_transaction import m, setup, snapshot


BASE = {f"acm_{name}.pbo" for name in (
    "acm_extended", "airway", "breathing", "cbrn", "circulation", "core", "damage",
    "disability", "evacuation", "gui", "itemtext", "main", "mission", "zeus")}
ADDITIONS = {f"acm_{name}.pbo" for name in ("burns", "infection", "ophthalmology", "card", "card_main")}
# B306 on: the ACME equipment addons ship in the same release (12 PBOs), so a release is 19 + 12 = 31.
EQUIPMENT = {f"acm_acme_{name}.pbo" for name in (
    "accuvac", "atak", "bloodcooler", "deltabag", "equipment", "hpmk", "sked", "sked_ace", "talon",
    "tempus", "tempusls", "ventway")}


def test_release_requires_exact_nineteen_pbos_without_fak_or_duplicate_dd1380():
    assert m.PBO_NAMES == BASE | ADDITIONS | EQUIPMENT
    assert len(m.PBO_NAMES) == 31


def remove_new_addons(target):
    for name in ADDITIONS:
        (target / "addons" / name).unlink()
        (target / "addons" / (name + ".test.bisign")).unlink()


def test_upgrade_from_fourteen_addons_installs_the_complete_clinical_set(setup):
    release, targets, root, keys = setup
    for target in targets:
        remove_new_addons(target)
    result = m.deploy(release, targets, root, keys)
    assert result["state"] == "VERIFIED"
    for target in targets:
        assert {p.name for p in (target / "addons").glob("*.pbo")} == BASE | ADDITIONS | EQUIPMENT
        for name in ADDITIONS:
            assert (target / "addons" / name).read_bytes() == (release / "addons" / name).read_bytes()


def test_old_fourteen_addon_release_cannot_be_deployed_as_b291(setup):
    release, targets, root, keys = setup
    remove_new_addons(release)
    before = snapshot(targets + [keys])
    with pytest.raises(m.DeployError, match="exact 31"):
        m.deploy(release, targets, root, keys)
    assert snapshot(targets + [keys]) == before


def test_failed_upgrade_removes_only_new_artifacts_and_restores_originals(setup):
    release, targets, root, keys = setup
    for target in targets:
        remove_new_addons(target)
    before = snapshot(targets + [keys])
    def fault(phase, index):
        if phase == "verify":
            raise OSError("integrated upgrade interrupted")
    with pytest.raises(OSError, match="upgrade interrupted"):
        m.deploy(release, targets, root, keys, hook=fault)
    assert snapshot(targets + [keys]) == before
    assert not (root / "active.json").exists()
