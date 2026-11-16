"""Transport role and recovery regression tests using the shared SQF-VM fixture."""
import re

from test_menu_death_lifecycle import ROOT, adapt, execute

SKED = ROOT / "addons/acme_sked_ace"
TALON = ROOT / "addons/acme_talon"


def read(name):
    return (SKED / f"functions/fn_{name}.sqf").read_text()


def test_team_limits_and_hatchet_preference():
    limits = read("bearerLimits").replace(
        'getNumber (configOf _litter >> "acmeLitterExtraCrew")', "_extraCrew"
    )
    preferred = read("preferredLitter").replace("objNull, [objNull]", "objNull").replace(
        '_vehicle isKindOf "vtx_H60_base"', "_hatchet"
    )
    execute("private _limits = {" + adapt(limits) + "};"
            "private _preferred = {" + adapt(preferred) + "};" + r"""
        private _extraCrew = 0;
        private _hatchet = false;
        missionNamespace setVariable ["acme_sked_bearersRequired", 4];
        [([_medic] call _limits) isEqualTo [2, 2], "legacy 4-person SKED setting allowed"] call _check;
        missionNamespace setVariable ["acme_sked_bearersRequired", 1];
        [([_medic] call _limits) isEqualTo [1, 2], "single rescuer SKED setting ignored"] call _check;
        _extraCrew = 1;
        [([_medic] call _limits) isEqualTo [3, 4], "Talon crew size drifted"] call _check;
        [([1] call _preferred) isEqualTo "ACME_SKED_Open", "solo SKED not recommended"] call _check;
        [([2] call _preferred) isEqualTo "ACME_SKED_Open", "pair SKED not recommended"] call _check;
        [([3, _medic] call _preferred) isEqualTo "ACME_Talon_Open", "extra crew did not prefer Talon"] call _check;
        _hatchet = true;
        [([2, _medic] call _preferred) isEqualTo "ACME_Talon_Open", "Hatchet did not prefer Talon"] call _check;
    """)


def test_guard_repairs_old_dragger_and_leaves_seated_casualty_alone():
    root = read("patientRoot").replace("attachedTo _litter", "_litterParent")
    guard = read("poseGuard").replace("objectParent _patient", "_seat").replace(
        "attachedTo _patient", "_patientParent"
    )
    execute("acme_sked_fnc_patientRoot = {" + adapt(root) + "};"
            "private _guard = {" + adapt(guard) + "};" + r"""
        private _pfh = {};
        CBA_fnc_addPerFrameHandler = {_pfh = _this select 0; 5};
        private _litterParent = objNull;
        private _patientParent = _medic;
        private _seat = objNull;
        private _patientAlive = false;
        private _repaired = 0;
        acme_sked_fnc_reattach = {_repaired = _repaired + 1; _patientParent = [_this select 1] call acme_sked_fnc_patientRoot};
        missionNamespace setVariable ["acme_sked_attach", [[0, 0, 0]]];
        _patient setVariable ["acme_sked_litter", missionNamespace];
        [_patient] call _guard;
        [[_patient], 5] call _pfh;
        [_repaired isEqualTo 1 && {_patientParent isEqualTo missionNamespace}, "release left patient on old dragger"] call _check;
        _litterParent = _medic;
        [[_patient], 5] call _pfh;
        [_repaired isEqualTo 2 && {_patientParent isEqualTo _medic}, "drag start did not transfer patient"] call _check;
        [[_patient], 5] call _pfh;
        [_repaired isEqualTo 2, "stable drag was needlessly reattached"] call _check;
        _litterParent = objNull;
        _seat = _medic;
        [[_patient], 5] call _pfh;
        [_repaired isEqualTo 2, "seated patient was reattached"] call _check;
    """)


def test_litter_runtime_points_and_materials_have_asset_dependencies():
    for config, model in (
        (ROOT / "addons/acme_sked/config.cpp", ROOT / "addons/acme_sked/sked_wrapped.p3d"),
        (SKED / "Talon.hpp", TALON / "talon_open.p3d"),
    ):
        source = config.read_text()
        handles = re.search(r'acmeLitterHandles\[\] = \{([^}]+)\}', source).group(1)
        chest = re.search(r'acmeLitterChestPoint = "([^"]+)"', source).group(1)
        points = re.findall(r'"([^"]+)"', handles)
        assert len(set(points)) == 4
        data = model.read_bytes()
        assert data.startswith(b"MLOD")
        for point in points + [chest]:
            assert point.encode() + b"\0" in data

    for material in ("hw", "mesh", "web"):
        for suffix in ("co", "nohq", "smdi"):
            assert (TALON / "data" / f"talon_{material}_{suffix}.paa").stat().st_size > 0


def test_server_release_can_detach_known_root_after_bearer_locality_change():
    source = read("srvLetGo").replace("attachedTo _unit", "_unitParent").replace(
        "detach _unit", "_detached = true"
    ).replace("alive _x", "true").replace(
        'getNumber (_cfg >> "ace_dragging_canDrag")', '1'
    ).replace(
        'getArray (_cfg >> "ace_dragging_dragPosition")', '[]'
    ).replace(
        'getNumber (_cfg >> "ace_dragging_dragDirection")', '0'
    ).replace("configOf _litter", "configNull")
    execute("private _release = {" + adapt(source) + "};" + r"""
        private _unitParent = _patient;
        private _detached = false;
        acme_sked_fnc_sendLocal = {};
        acme_sked_fnc_traceTransport = {};
        _patient setVariable ["acme_sked_bearers", [_medic, missionNamespace]];
        _medic setVariable ["acme_sked_bearing", _patient];
        [_medic] call _release;
        [_detached, "server left the bearer attached to the litter"] call _check;
        _detached = false;
        _unitParent = missionNamespace;
        _patient setVariable ["acme_sked_bearers", [_medic, missionNamespace]];
        _medic setVariable ["acme_sked_bearing", _patient];
        [_medic] call _release;
        [!_detached, "server detached an unrelated attachment"] call _check;
    """)
