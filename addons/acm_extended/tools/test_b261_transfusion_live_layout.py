"""B261: Transfuse Fluids geometry and live mL cannot overlap or churn selection."""
from pathlib import Path
from test_menu_death_lifecycle import adapt, execute

F = Path(__file__).resolve().parents[1] / "functions"


def text(name):
    return (F / f"fn_{name}.sqf").read_text(encoding="utf-8-sig")


def _geometry():
    source = text("updateTransfusionControls")
    begin = source.index("private _titleH = _buttonH * 0.85;")
    end = source.index('[_ctrlLeftList,"position"', begin)
    return adapt(source[begin:end].replace("safeZoneH", "1"))


def test_adjust_infusion_has_its_own_nonoverlapping_row():
    execute("""
        private _buttonH=0.025;
        private _rowStep=0.05;
        private _ly=0.228;
        private _lh=0.612;
    """ + _geometry() + r"""
        private _normalBottom = _ly + _normalH;
        [(_adjustY - _normalBottom) > 0.005,
            "Adjust Infusion still covers normal fluid rows"] call _check;
        [_infTitleY >= (_adjustY + _buttonH),
            "Adjust Infusion overlaps infusion header"] call _check;
        [_infListY >= (_infTitleY + _titleH),
            "active infusion rows overlap title"] call _check;
        [abs ((_infListY + _infListH) - (_ly + _lh)) < 0.0001,
            "infusion rows exceed the original pane"] call _check;
    """)


def _signature():
    source=text("updateTransfusionControls")
    start=source.index("private _signature = str (_infusionLabels apply {")
    end=source.index("if ((uiNamespace getVariable", start)
    return adapt(source[start:end])


def test_live_volume_change_does_not_rebuild_active_infusions():
    expr=_signature()
    execute(r"""
        private _infusionLabels=[[0,"(infusing) Calcium | 250 mL remaining",
            250,"Saline",-1,500,"CalciumGluconate",4]];
        private _structural={ """ + expr + r""" _signature; };
        private _first=call _structural;
        _infusionLabels set [0,[0,"(infusing) Calcium | 240 mL remaining",
            240,"Saline",-1,500,"CalciumGluconate",4]];
        [call _structural isEqualTo _first,
            "fluid-only mL change still triggers full list rebuild"] call _check;
        _infusionLabels set [0,[0,"(paused) Calcium | 240 mL remaining",
            240,"Saline",-1,500,"CalciumGluconate",4]];
        [!(call _structural isEqualTo _first),
            "infusion status change failed to trigger structural rebuild"] call _check;
    """)


def test_infusion_display_tracks_physical_bag_volume_not_stale_drug_snapshot():
    src=text("updateTransfusionControls")
    assert "private _infusionName = [_bestEntry," in src
    assert "private _liveLabel = [_infusionName, _sRemaining] call ACME_fnc_fluidLabelVolume;" in src
    assert "_infusionLabels pushBack [_selIndex, _liveLabel, _sRemaining" in src
    # The native hung-bag list still refreshes in place.
    native=(F.parents[1] / "circulation" / "functions" /
            "fnc_TransfusionMenu_UpdateBagList.sqf").read_text(encoding="utf-8-sig")
    assert "call ACME_fnc_fluidLabelVolume" in native
    assert "_ctrlBagPanel lbSetText [_row, _liveLabel];" in native


def test_per_row_updates_do_not_replay_list_selection():
    src=text("updateTransfusionControls")
    start=src.index("// Volumes repaint at the existing menu tick rate.")
    end=src.index("} forEach _infusionLabels;",start)
    section=src[start:end]
    assert "_ctrlActiveInfList lbValue _r" in section
    assert "_ctrlActiveInfList lbSetText [_row, _label];" in section
    assert "_ctrlActiveInfList lbSetTooltip" in section
    assert "lbClear" not in section
    assert "lbSetCurSel" not in section
    assert "(_ctrlActiveInfList lbText _row) isNotEqualTo _label" in section


def test_active_list_rebuilds_when_topology_changes_not_when_ml_changes():
    src=text("updateTransfusionControls")
    signature=src[src.index("private _signature = str (_infusionLabels apply {"):
                  src.index("if ((uiNamespace getVariable",src.index("private _signature = str (_infusionLabels apply {"))]
    assert 'private _cut = _name find " | ";' in signature
    assert "_x select 2" not in signature
    assert "_x select 7" in signature
    assert "(lbSize _ctrlActiveInfList) != (count _infusionLabels)" in src
    assert 'if ((lbSize _ctrlActiveInfList) > 0) then {' in src
