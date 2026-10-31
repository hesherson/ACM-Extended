"""B290-to-B291 installation upgrades retain exact artifacts and rollback safety."""
import pytest

from test_b236_deployment_transaction import m, setup, snapshot


BASE = {f"acm_{name}.pbo" for name in (
    "acm_extended", "airway", "breathing", "cbrn", "circulation", "core", "damage",
    "disability", "evacuation", "gui", "itemtext", "main", "mission", "zeus")}
ADDITIONS = {f"acm_{name}.pbo" for name in ("burns", "infection", "ophthalmology", "card", "card_main")}


def test_release_requires_exact_nineteen_pbos_without_fak_or_duplicate_dd1380():
    assert m.PBO_NAMES == BASE | ADDITIONS
    assert len(m.PBO_NAMES) == 19


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
        assert {p.name for p in (target / "addons").glob("*.pbo")} == BASE | ADDITIONS
        for name in ADDITIONS:
            assert (target / "addons" / name).read_bytes() == (release / "addons" / name).read_bytes()


def test_old_fourteen_addon_release_cannot_be_deployed_as_b291(setup):
    release, targets, root, keys = setup
    remove_new_addons(release)
    before = snapshot(targets + [keys])
    with pytest.raises(m.DeployError, match="exact 19"):
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
