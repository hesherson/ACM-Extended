"""B274: run the clamp redraw with explicit native-control boundaries.

Production rate formatting and redraw decisions execute in SQF-VM. The fixture
records control writes; it does not render Arma or certify input propagation.
"""
import re

import pytest

from test_bounded_selector_lifetime import ui_commands
from test_menu_death_lifecycle import ROOT, execute, read


def redraw_setup():
    text = read("updateClampDialog")
    text = text.replace("findDisplay 86200", "_clampDisplay")
    text = re.sub(r"_display displayCtrl (\d+)", r"\1", text)
    text = re.sub(r"ctrlText (_\w+)", r"([\1] call _text)", text)
    text = ui_commands(text)
    return r'''
        private _clampDisplay=missionNamespace;
        private _uiWrites=[];private _uiTexts=createHashMap;
        private _wheelMoves=[];private _selected=[];
        private _write={params ["_id","_command","_value"];
            _uiWrites pushBack _this;
            if (_command=="ctrlSetText") then {_uiTexts set [str _id,_value];};
        };
        private _text={private _key=str (_this select 0);
            if (_key in _uiTexts) then {_uiTexts get _key} else {""}
        };
        _clampDisplay setVariable ["ACME_clampReadoutReady",false];
        ACME_fnc_onClampLoad={};
        ACME_fnc_getSelectedInfusionEntryIndexes={_selected};
        ACME_fnc_infusionName={"Epi"};
        ACME_fnc_placeClampWheel={_wheelMoves pushBack _this;};
        missionNamespace setVariable ["ACME_infusion_defaultDropSet",20];
        missionNamespace setVariable ["ACME_infusion_clampCurve",2];
        missionNamespace setVariable ["ACME_infusion_maxDropsPerMinute",120];
        uiNamespace setVariable ["ACME_RollerClamp_Flash",["",-1]];
        uiNamespace setVariable ["ACME_RollerClamp_MedName",""];
        uiNamespace setVariable ["ACME_RollerClamp_DropSet",20];
    ''' + "\n".join(
        f"ACME_fnc_{name}={{" + read(name) + "};"
        for name in ("clampPositionToDrops", "dropsToClampPosition", "formatRate")
    ) + "\nACME_fnc_updateClampDialog={" + text + "};\n"


@pytest.mark.parametrize("has_entry,position,dragging", [
    (False, 0, False), (False, 0.5, False), (True, 1, False),
    (True, 0.3, True),
])
def test_native_bottom_strip_is_the_only_live_rate_readout(has_entry, position, dragging):
    entry = r'''
        private _entry=[];_entry resize 24;
        _entry set [10,100];_entry set [11,"Epinephrine"];
        _entry set [14,10];_entry set [20,20];_entry set [21,120];
        _entry set [22,1];_entry set [23,"bag1"];
        _patient setVariable ["ACME_infusion_BagMedications",[_entry]];
        _selected=[_patient,[0]];
    ''' if has_entry else ""
    execute(redraw_setup() + entry + f'''
        uiNamespace setVariable ["ACME_RollerClamp_Position",{position}];
        uiNamespace setVariable ["ACME_RollerClamp_Dragging",{str(dragging).lower()}];
        call ACME_fnc_updateClampDialog;
        private _bottom=_uiTexts get "86206";
        [(_bottom find "gtt/mL")>=0 && {{(_bottom find "gtt/min")>=0}}
            && {{(_bottom find "mL/min")>=0}} && {{(_bottom find "% open")>=0}},
            "native rate strip lost its statistics"] call _check;
        [(_uiWrites findIf {{(_x select 0)==86210}})<0,
            "backdrop was changed into a duplicate readout"] call _check;
        [(_uiWrites findIf {{(_x select 1)=="ctrlSetText"
            && {{(_x select 0) in [86201,86202,86203]}}}})<0,
            "redraw changed clamp artwork or drag overlay"] call _check;
        [count _wheelMoves=={0 if dragging else 1},
            "wheel mover ownership changed while dragging"] call _check;
    ''')


def test_unchanged_redraw_keeps_native_texts_without_repeated_writes():
    execute(redraw_setup() + r'''
        uiNamespace setVariable ["ACME_RollerClamp_Position",0.5];
        uiNamespace setVariable ["ACME_RollerClamp_Dragging",false];
        call ACME_fnc_updateClampDialog;
        _uiWrites=[];
        for "_i" from 1 to 30 do {call ACME_fnc_updateClampDialog;};
        [count _uiWrites==0,"unchanged redraw rewrote native text or tooltips"] call _check;
        [count _wheelMoves==31,"non-dragging wheel updates lost"] call _check;
    ''')


def test_clamp_backdrop_remains_blank_and_no_second_readout_is_created():
    config = (ROOT / "addons/acm_extended/config.cpp").read_text()
    backdrop = config.split("class ACME_RollerClamp_Dialog {", 1)[1]
    backdrop = backdrop.split("class ACME_Backdrop: RscText {", 1)[1].split("};", 1)[0]
    assert 'idc = 86210;' in backdrop and 'text = "";' in backdrop
    source = read("updateClampDialog")
    assert "ctrlCreate" not in source
    assert '"Roller clamp:' not in source
    assert 'private _ctrlRate = _display displayCtrl 86206;' in source
    assert 'if (ctrlText _ctrlRate != _rateText)' in source
