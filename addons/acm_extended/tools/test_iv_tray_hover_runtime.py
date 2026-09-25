"""Execute tray hover SQF with opaque UI handles and recorded commit boundaries.

Inventory and native UI commands are fixtures. Each timed commit records its
starting/target rectangle and fade, so a reveal from the default UI origin is
detectable without pretending that SQF-VM renders Arma controls or text.
"""
import re

import pytest

from test_bounded_selector_lifetime import ui_commands
from test_menu_death_lifecycle import ROOT, execute


def hover_source(text=None):
    if text is None:
        text = (ROOT / 'addons/acm_extended/functions/fn_ivTrayHover.sqf').read_text()
    text = re.sub(r'\bparseText\s+', '', text)
    text = text.replace('finite _ease', '(_ease isEqualType 0)')
    text = re.sub(r'_d displayCtrl (\w+)', r'([\1] call _lookup)', text)
    text = re.sub(r'ctrlPosition (_\w+)', r'([\1] call _position)', text)
    return ui_commands(text)


def setup(gauge, stock):
    background = {14: 86540, 16: 86544, 18: 86548, 20: 86556}[gauge]
    return f'''
        private _display=missionNamespace;
        private _created=[]; private _writes=[]; private _reveals=[]; private _visibleText=[];
        private _positions=createHashMap; private _pendingPositions=createHashMap;
        private _fades=createHashMap; private _pendingFades=createHashMap;
        private _visible=createHashMap;
        private _stock={stock}; private _stockReads=[];
        private _slot=[1.60,0.35,0.14,0.08];
        private _base=[1.58,0.23,0.18,0.32];
        private _staleSlot=[0.10,0.10,0.10,0.10];
        private _getDefault={{params ["_map","_args"]; _args params ["_key","_default"];
            if (_key in _map) then {{_map get _key}} else {{_default}}}};
        private _lookup={{_this select 0}};
        private _position={{[_positions,[str (_this select 0),[0,0,0.1,0.05]]] call _getDefault}};
        private _create={{
            params ["_class","_idc"];
            private _handle=90000 + count _created;
            _created pushBack [_handle,_class];
            _positions set [str _handle,[0,0,0.1,0.05]];
            _fades set [str _handle,0];
            _visible set [str _handle,true];
            _handle
        }};
        private _write={{
            params ["_handle","_command","_value"];
            _writes pushBack _this;
            private _key=str _handle;
            if (_command=="ctrlSetPosition") then {{_pendingPositions set [_key,+_value];}};
            if (_command=="ctrlSetFade") then {{_pendingFades set [_key,_value];}};
            if (_command=="ctrlShow") then {{_visible set [_key,_value];}};
            if (_command=="ctrlSetStructuredText"
                && {{[_visible,[_key,true]] call _getDefault}}
                && {{([_fades,[_key,0]] call _getDefault)<1}}) then {{
                _visibleText pushBack [_handle,[_handle] call _position];
            }};
            if (_command=="ctrlCommit") then {{
                private _from=[_positions,[_key,[0,0,0.1,0.05]]] call _getDefault;
                private _to=[_pendingPositions,[_key,+_from]] call _getDefault;
                private _fade=[_pendingFades,[_key,[_fades,[_key,0]] call _getDefault]] call _getDefault;
                if (_fade<1 && {{_value>0}} && {{[_visible,[_key,true]] call _getDefault}}) then {{
                    _reveals pushBack [_handle,+_from,+_to,_value];
                }};
                _positions set [_key,+_to];
                _fades set [_key,_fade];
            }};
        }};
        private _closeRect={{
            params ["_actual","_expected"];
            private _same=true;
            for "_i" from 0 to 3 do {{if (abs ((_actual select _i)-(_expected select _i))>0.00001) then {{_same=false;}};}};
            _same
        }};
        ACME_fnc_treatmentSupplyCount={{_stockReads pushBack _this; _stock}};
        uiNamespace setVariable ["ACME_IV_DLG",_display];
        uiNamespace setVariable ["ACME_IV_Medic",_medic];
        uiNamespace setVariable ["ACME_IV_Patient",_patient];
        uiNamespace setVariable ["ACME_IV_NeedleRects",[[{gauge},_staleSlot,_base,88000]]];
        _positions set ["{background}",+_slot];
        _positions set ["88000",+_base];
    ''' + 'ACME_fnc_ivTrayHover={' + hover_source() + '};'


@pytest.mark.parametrize('gauge', [14, 16, 18, 20])
@pytest.mark.parametrize('stock', [0, 1, 5, 6, 20])
def test_hover_stock_count_badge_uses_live_tile_and_collapses_on_exit(gauge, stock):
    execute(setup(gauge, stock) + f'''
        ["needle",{gauge},true] call ACME_fnc_ivTrayHover;
        private _fan=_display getVariable ["ACME_IV_TrayFan_{gauge}",[]];
        [count _fan==5 && {{count _created==1}},"fan creation lost a control"] call _check;
        private _badge=_fan select 4;
        private _expected=[1.60+0.14*0.08,0.35+0.08*0.055,0.14*0.18,0.08*0.22];
        [[[_badge] call _position,_expected] call _closeRect,"badge is not inside live tile"] call _check;
        [(_fades get str _badge)=={0 if stock > 5 else 1},"wrong badge stock threshold"] call _check;
        private _shownClones=(_fan select [0,4]) select {{(_fades get str _x)==0}};
        [count _shownClones=={max(0, min(stock, 5) - 1)},"wrong stock fan size"] call _check;
        [(_stockReads select 0) isEqualTo [_medic,_patient,"ACM_IV_{gauge}g"],"stock read used wrong treatment/item"] call _check;
        ["needle",{gauge},false] call ACME_fnc_ivTrayHover;
        [count _created==1,"exit recreated fan controls"] call _check;
        {{[(_fades get str _x)==1,"exit left fan visible"] call _check;}} forEach _fan;
        {{[[[_x] call _position,_base] call _closeRect,"exit did not collapse clone"] call _check;}} forEach (_fan select [0,4]);
    ''')


@pytest.mark.parametrize('gauge', [14, 16, 18, 20])
def test_first_badge_reveal_never_animates_from_ui_origin(gauge):
    execute(setup(gauge, 6) + f'''
        ["needle",{gauge},true] call ACME_fnc_ivTrayHover;
        private _badge=(_display getVariable "ACME_IV_TrayFan_{gauge}") select 4;
        private _transitions=_reveals select {{(_x select 0)==_badge}};
        {{
            [[_x select 1,_x select 2] call _closeRect,"badge reveals while moving from UI origin"] call _check;
        }} forEach _transitions;
        {{
            private _position=_x select 1;
            [(_position select 0)>=(_slot select 0) && {{(_position select 1)>=(_slot select 1)}},
                "visible badge text written before tile placement"] call _check;
        }} forEach (_visibleText select {{(_x select 0)==_badge}});
        [(_fades get str _badge)==0,"badge never became visible"] call _check;
    ''')


@pytest.mark.parametrize('gauge', [14, 16, 18, 20])
def test_fan_uses_original_color_with_progressively_lower_opacity(gauge):
    first_idc = {14: 86580, 16: 86584, 18: 86588, 20: 86592}[gauge]
    execute(setup(gauge, 6) + f'''
        ["needle",{gauge},true] call ACME_fnc_ivTrayHover;
        private _fan=_display getVariable ["ACME_IV_TrayFan_{gauge}",[]];
        private _expectedAlpha=[0.72,0.52,0.34,0.18];
        for "_i" from 0 to 3 do {{
            private _control=_fan select _i;
            [_control=={first_idc}+_i,"fan did not use its predeclared layer"] call _check;
            private _colorWrites=_writes select {{(_x select 0)==_control && {{(_x select 1)=="ctrlSetTextColor"}}}};
            private _rgba=(_colorWrites select ((count _colorWrites)-1)) select 2;
            [_rgba isEqualTo [1,1,1,_expectedAlpha select _i],"fan is tinted or distance alpha is wrong"] call _check;
        }};
        [count (_writes select {{(_x select 0)==88000 && {{(_x select 1)=="ctrlSetTextColor"}}}})==0,
            "hover overwrote the main logo inventory state"] call _check;
        for "_j" from 1 to 25 do {{
            ["needle",{gauge},false] call ACME_fnc_ivTrayHover;
            ["needle",{gauge},true] call ACME_fnc_ivTrayHover;
        }};
        [count _created==1,"repeated hover recreated controls above the real logo"] call _check;
    ''')


@pytest.mark.parametrize('gauge', [14, 16, 18, 20])
def test_config_layers_stock_back_to_front_beneath_real_inventory_logo(gauge):
    config = (ROOT / 'addons/acm_extended/config.cpp').read_text()
    controls = {}
    for match in re.finditer(r'class (IV_G\d+(?:BG|Logo|Fan[1-4]))\s*:\s*\w+\s*\{((?:[^{}]|\{[^{}]*\})*)\}', config):
        controls[match[1]] = (match.start(), match[2])
    first_idc = {14: 86580, 16: 86584, 18: 86588, 20: 86592}[gauge]
    previous = controls[f'IV_G{gauge}BG'][0]
    for distance in (4, 3, 2, 1):
        position, body = controls[f'IV_G{gauge}Fan{distance}']
        assert position > previous
        assert int(re.search(r'idc\s*=\s*(\d+)', body)[1]) == first_idc + distance - 1
        previous = position
    position, body = controls[f'IV_G{gauge}Logo']
    assert position > previous
    assert re.search(r'colorText\[\]\s*=\s*\{\s*1,\s*1,\s*1,\s*1\s*\}', body)
