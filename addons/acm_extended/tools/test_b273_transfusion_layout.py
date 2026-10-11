"""B273 production layout geometry across screen ratios and nested action states.

The assertions consume the authored SQF rectangles, not a separately copied layout.
They verify real interaction bounds; Arma renderer acceptance remains an in-game check.
"""
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[3]
LAYOUT = (ROOT / "addons/acm_extended/functions/fn_layoutTransfusionMenu.sqf").read_text()
DIALOG = (ROOT / "addons/circulation/TransfusionMenu_Dialog.hpp").read_text()


def fixed_layout():
    # The first forEach after _place is the closed main-menu rectangle list.
    start = LAYOUT.index("// The entire BodyBackground rect")
    block = LAYOUT[start:LAYOUT.index("private _yButton", start)]
    rows = re.findall(r"\[(\d+),(0\.\d+),(0\.\d+),(0\.\d+),(0\.\d+)\]", block)
    assert rows, "authored main-menu rectangles not found"
    return {int(row[0]): tuple(float(value) for value in row[1:]) for row in rows}


def rect(idc, aspect, origin=(-0.3, -0.1)):
    # Bag Actions expands into the service slot only when Prime/Flush is absent.
    # Use its widest authored branch for the main-menu interaction bounds.
    x, y, w, h = authored_place(86170, 1) if idc == 86170 else fixed_layout()[idc]
    canvas = min(aspect, 1.7777778)
    canvas_x = origin[0] + (aspect - canvas) / 2
    return canvas_x + canvas * x, origin[1] + y, canvas * w, h


def overlap(a, b):
    x, y, w, h = a
    xx, yy, ww, hh = b
    return min(x + w, xx + ww) > max(x, xx) + 1e-8 and min(y + h, yy + hh) > max(y, yy) + 1e-8


@pytest.mark.parametrize("aspect", [4/3, 16/9, 21/9, 32/9])
def test_all_main_interaction_rectangles_fit_window_and_do_not_overlap(aspect):
    canvas = min(aspect, 1.7777778)
    canvas_x = -0.3 + (aspect - canvas) / 2
    bounds = (canvas_x + 0.11 * canvas, -0.1 + 0.08, 0.78 * canvas, 0.84)
    # Inventory's prepared overlay shares its stock-list rectangle intentionally, and the
    # nonselectable empty captions occupy their owning list; omit only those overlays.
    ids = [86002, 86003, 86037, 86006, 86004, 86170, 86128, 86129, 86131,
           86172, 86144, 86005, 86130, 86127, 86121, 86122, 86171, 86126]
    boxes = [rect(idc, aspect) for idc in ids]
    bx, by, bw, bh = bounds
    for idc, (x, y, w, h) in zip(ids, boxes):
        assert w > 0 and h > 0, idc
        assert bx <= x and by <= y, idc
        assert x + w <= bx + bw + 1e-8 and y + h <= by + bh + 1e-8, idc
    for i, a in enumerate(boxes):
        for j, b in enumerate(boxes[:i]):
            assert not overlap(a, b), (ids[i], ids[j])


def test_fluid_list_preserves_room_for_separate_y_bags_and_bracket():
    fluid = fixed_layout()[86004]
    x, _, w, h = fluid
    # Native list rows remain safeZoneH/20; both blood and saline remain ordinary rows.
    assert h / 0.05 >= 2
    assert int(h / 0.05) >= 4
    assert x - 0.125 >= 0.0119, "bracket consumes the native bag hit target"
    assert x + w <= 0.337 + 1e-8
    assert w >= 0.19


def authored_place(idc, occurrence=0):
    rows = re.findall(rf"\[{idc},(0\.\d+),(0\.\d+),(0\.\d+),(0\.\d+)\] call _place", LAYOUT)
    assert len(rows) > occurrence
    return tuple(float(v) for v in rows[occurrence])


@pytest.mark.parametrize("has_service", [False, True])
def test_line_flow_service_and_details_have_distinct_rows(has_service):
    # B274 restores the native Stop row above Fluids and places service beside
    # Bag Actions. Details stay visible inline below the unchanged body map.
    stop = fixed_layout()[86006]
    details = fixed_layout()[86171]
    assert not overlap(stop, details)
    assert stop[1] + stop[3] <= fixed_layout()[86004][1]
    if has_service:
        service = authored_place(86143)
        actions = authored_place(86170, 0)
        assert not overlap(stop, service)
        assert not overlap(service, details)
        assert not overlap(actions, service)
        assert actions[1:] == service[1:]
    else:
        actions = authored_place(86170, 1)
        assert actions[2] == pytest.approx(fixed_layout()[86004][2] + .012)
        assert not overlap(actions, details)


@pytest.mark.parametrize("mode", ["loose", "prepared", "blood"])
def test_spike_and_y_setup_keep_inventory_list_and_prepared_list_selectable(mode):
    candidates = re.findall(r"\[86141,(0\.\d+),(0\.\d+),(0\.\d+),(0\.\d+)\] call _place", LAYOUT)
    spike = next(tuple(map(float, row)) for row in candidates
                 if (float(row[2]) == .097 if mode == "prepared" else float(row[1]) == (.564 if mode == "blood" else .526) and float(row[2]) == .202))
    assert not overlap(spike, fixed_layout()[86005])
    assert not overlap(spike, fixed_layout()[86130])
    assert not overlap(spike, fixed_layout()[86127])
    if mode == "blood":
        y_setup = authored_place(86142)
        dropdown = authored_place(86212)
        assert not overlap(spike, y_setup)
        assert not overlap(dropdown, y_setup)
        assert not overlap(dropdown, spike)
        assert dropdown[1] == y_setup[1]
    elif mode == "prepared":
        prep = authored_place(86121)
        assert not overlap(spike, prep)
        assert spike[1] == prep[1]


def popover(menu):
    backdrop = authored_place(86173 if menu == "bag" else 86174)
    first = LAYOUT.index('} forEach [86007,86146,86147,86134,86148,86120,86194];' if menu == "bag"
                         else '} forEach [86132,86133,86149];')
    fragment = LAYOUT[:first]
    call = re.findall(r'\[_x,(0\.\d+),(0\.\d+) \+ _forEachIndex \* (0\.\d+),(0\.\d+),(0\.\d+)\] call _place', fragment)[-1]
    x, y, pitch, w, h = map(float, call)
    return backdrop, [(x, y + index * pitch, w, h) for index in range(7 if menu == "bag" else 3)]


@pytest.mark.parametrize("menu", ["bag", "infusion"])
def test_native_action_buttons_fit_popover_without_overlap(menu):
    backdrop, buttons = popover(menu)
    x, y, w, h = backdrop
    for b in buttons:
        assert x <= b[0] and y <= b[1]
        assert b[0] + b[2] <= x + w + 1e-8
        assert b[1] + b[3] <= y + h + 1e-8
    for i, a in enumerate(buttons):
        for b in buttons[:i]:
            assert not overlap(a, b)
    # Popovers stay in the patient pane and leave the body-map destinations clickable.
    assert x + w < 0.35


def test_body_canvas_uses_one_unchanged_native_rect_for_every_overlay():
    block = DIALOG.split("class BodyBackground: RscPictureKeepAspect {", 1)[1].split("};", 1)[0]
    expressions = dict(re.findall(r"\b([xywh]) = QUOTE\((.*?)\);", block))
    env = {"ACM_UI_CANVAS_X": 0, "ACM_UI_CANVAS_W": 1, "safeZoneY": 0, "safeZoneH": 1}
    actual = tuple(eval(expressions[key], {"__builtins__": {}}, env) for key in "xywh")
    assert actual == pytest.approx((0.5 - 1/6.8, 0.5 - 1/3.5, 1/3.4, 1/1.75))
    # IV, IO, and tourniquet artwork retain that same inherited box, with no child-specific offset.
    for name in ["BodyBackground_IO_Torso", "BodyBackground_Tourniquet_RightArm"]:
        block = DIALOG.split(f"class {name}: BodyBackground {{", 1)[1].split("};", 1)[0]
        assert not re.search(r"\b[xywh]\s*=", block)
    assert not re.search(r"\[(?:8601[0-4]|8602\d|8603[0-5]),", LAYOUT)
