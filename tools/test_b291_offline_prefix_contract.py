"""Keep DD1380's public virtual paths without weakening native prefix checks."""
from pathlib import Path

import pytest

from test_fork_phase91_offline_build_gate import ADDONS, validate_prefix, virtual


@pytest.mark.parametrize(("folder", "prefix"), [
    ("card", r"z\DD1380\addons\card"),
    ("card_main", r"z\DD1380\addons\main"),
])
def test_public_card_prefix_migration_requires_scoped_declaration(tmp_path, folder, prefix):
    addon = tmp_path / folder
    addon.mkdir()
    (addon / "$PBOPREFIX$").write_text(prefix)
    with pytest.raises(AssertionError, match="addon-scoped prefix declaration"):
        validate_prefix(addon)
    (addon / "addon.toml").write_text("ignore_pboprefix = false\n")
    with pytest.raises(AssertionError, match="exactly once"):
        validate_prefix(addon)
    (addon / "addon.toml").write_text("ignore_pboprefix = true\n")
    validate_prefix(addon)


@pytest.mark.parametrize(("folder", "wrong_prefix"), [
    ("card", r"x\ACM\addons\card"),
    ("card_main", r"z\DD1380\addons\card_main"),
    ("core", r"z\DD1380\addons\core"),
    ("acm_extended", r"x\ACM\addons\acm_extended"),
])
def test_prefix_exception_does_not_allow_renamed_or_native_paths(tmp_path, folder, wrong_prefix):
    addon = tmp_path / folder
    addon.mkdir()
    (addon / "$PBOPREFIX$").write_text(wrong_prefix)
    (addon / "addon.toml").write_text("ignore_pboprefix = true\n")
    with pytest.raises(AssertionError):
        validate_prefix(addon)


@pytest.mark.parametrize(("path", "target"), [
    (r"\z\DD1380\addons\main\script_mod.hpp", Path("card_main/script_mod.hpp")),
    (r"\z\DD1380\addons\card\functions\fnc_setData.sqf", Path("card/functions/fnc_setData.sqf")),
    (r"\x\ACM\addons\core\script_component.hpp", Path("core/script_component.hpp")),
])
def test_virtual_include_maps_to_the_actual_addon_owner(path, target):
    assert virtual(path) == ADDONS / target
