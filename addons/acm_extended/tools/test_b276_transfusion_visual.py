"""B276 native card views execute production custody binding and viewport math.

Adapters model Arma list/control primitives; original selection callbacks stay
separate so these cases assert UI identity, not native rendering certification.
"""
from pathlib import Path
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute
from test_b156_procedure_supplies import primitives
from test_b275_transfusion_presentation import presentation_setup

FUN = ROOT / "addons/acm_extended/functions"


def code(name):
    source = (FUN / f"fn_{name}.sqf").read_text()
    source = source.replace('ctrlIDC _list', '(_list getVariable ["idc",-1])')
    source = source.replace('lbSize _list', 'count (_list getVariable ["rows",[]])')
    source = source.replace('_list lbValue _row', '((_list getVariable "rows") select _row select 0)')
    source = source.replace('_list lbData _row', '((_list getVariable "rows") select _row select 1)')
    source = source.replace('ctrlParent _hit', 'missionNamespace').replace('_display displayCtrl _idc', 'profileNamespace')
    source = source.replace('findDisplay 86200', 'objNull').replace('findDisplay 84000', 'objNull')
    source = source.replace('lbCurSel _list', '(_list getVariable ["sel",-1])')
    source = source.replace('_list lbSetCurSel _row;', '_list setVariable ["sel",_row];')
    return primitives(adapt(source))


def setup():
    return r'''
      private _mapDefault={params["_map","_args"];_args params["_key","_default"];private _value=_map get _key;if(isNil "_value")exitWith{_default};_value};
      private _list=profileNamespace;private _hit=missionNamespace;
      private _selectedCalls=0;private _refreshCalls=0;
      ACME_fnc_updateTransfusionControls={_selectedCalls=_selectedCalls+1;};
      ACME_fnc_updateTransfusionCards={_refreshCalls=_refreshCalls+1;};
      _list setVariable["idc",86004];_list setVariable["rows",[[0,""],[1,""]]];_list setVariable["sel",-1];
      missionNamespace setVariable["ACM_circulation_TransfusionMenu_Target",_patient];
      missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_BodyPart","leftarm"];
      missionNamespace setVariable["ACM_circulation_TransfusionMenu_SelectIV",true];
      missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_AccessSite",0];
      private _a=["Saline",500,1,0,true,-1,500,-1,0,"uid-a"];
      private _b=["Saline",500,1,0,true,-1,500,-1,1,"uid-b"];
      missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selection_IVBags",[_a,_b]];
      _patient setVariable["ACM_circulation_IV_Bags",createHashMapFromArray[["leftarm",[
        ["Saline",500,1,0,true,-1,500,-1,"uid-a"],
        ["Saline",500,1,0,true,-1,500,-1,"uid-b"]]]]];
      _hit setVariable["ACME_txListIDC",86004];_hit setVariable["ACME_txCapacity",2];_hit setVariable["ACME_txPatient",_patient];
    ''' + '\n'.join('ACME_fnc_' + name + '={' + code(name) + '};' for name in (
        'transfusionCardIdentity', 'transfusionCardResolve', 'transfusionCardWindow', 'transfusionCardSelect'))


@pytest.mark.parametrize('change,selected', [
    ('_list setVariable["rows",[[1,""],[0,""]]];', 1),
    ('_list setVariable["rows",[[1,""]]];', -1),
    ('_list setVariable["rows",[[0,""],[0,""]]];', -1),
    ('_patient setVariable["ACM_circulation_IV_Bags",createHashMapFromArray[["leftarm",[["Saline",500,1,0,true,-1,500,-1,"uid-b"]]]]];', -1),
    ('_patient setVariable["ACM_circulation_IV_Bags",createHashMapFromArray[["leftarm",[["Saline",500,1,1,true,-1,500,-1,"uid-a"]]]]];', -1),
    ('_hit setVariable["ACME_txPatient",uiNamespace];', -1),
])
def test_card_click_resolves_exact_live_uid_and_rejects_stale_identity(change, selected):
    execute(setup() + r'''
      _hit setVariable["ACME_txIdentity",[_list,0] call ACME_fnc_transfusionCardIdentity];
    ''' + change + f'''
      [_hit] call ACME_fnc_transfusionCardSelect;
      [(_list getVariable "sel")=={selected},"card selected a replaced/reordered neighbour"] call _check;
      [_selectedCalls=={int(selected >= 0)},"rejected card delegated native selection"] call _check;
    ''')


def test_prepared_infusions_bind_custody_id_across_storage_index_changes():
    execute(setup() + r'''
      _list setVariable["idc",86127];_list setVariable["rows",[[0,""],[1,""]]];
      _medic setVariable["ACME_infusion_PreparedBags",[["prepared-a"],["prepared-b"]]];
      private _identity=[_list,0] call ACME_fnc_transfusionCardIdentity;
      _medic setVariable["ACME_infusion_PreparedBags",[["prepared-b"],["prepared-a"]]];
      [([_list,_identity] call ACME_fnc_transfusionCardResolve)==1,"prepared storage index became identity"] call _check;
      _medic setVariable["ACME_infusion_PreparedBags",[["prepared-b"]]];
      _list setVariable["rows",[[0,""]]];
      [([_list,_identity] call ACME_fnc_transfusionCardResolve)==-1,"removed prepared bag rebound to neighbour"] call _check;
    ''')


def test_set_and_inventory_cards_keep_original_source_data():
    execute(setup() + r'''
      {
        _list setVariable["idc",_x];_list setVariable["rows",[[0,"set-a"],[1,"set-b"]]];
        private _identity=[_list,0] call ACME_fnc_transfusionCardIdentity;
        _list setVariable["rows",[[0,"set-b"],[1,"set-a"]]];
        [([_list,_identity] call ACME_fnc_transfusionCardResolve)==1,"source data replaced by visible slot"] call _check;
        _list setVariable["rows",[[0,"set-a"],[1,"set-a"]]];
        [([_list,_identity] call ACME_fnc_transfusionCardResolve)==-1,"ambiguous staged/source data accepted"] call _check;
      } forEach [86005,86145];
    ''')


@pytest.mark.parametrize('args,wanted', [
    ('[9,3,99]', '[6,[6,7,8],true,false]'),
    ('[1,3,6]', '[0,[0,-1,-1],false,false]'),
    ('[9,3,0,8,true]', '[6,[6,7,8],true,false]'),
    ('[0,3,9]', '[0,[-1,-1,-1],false,false]'),
    ('[8,2,6,1,true]', '[1,[1,2],true,true]'),
    ('[2,2,-10]', '[0,[0,1],false,false]'),
])
def test_viewport_clamps_overflow_filter_and_keyboard_reveal(args, wanted):
    execute(setup() + f'[{args} call ACME_fnc_transfusionCardWindow isEqualTo {wanted},"viewport clamping lost a live row"] call _check;')


@pytest.mark.parametrize('key,wanted', [(208,0), (207,1), (199,0), (209,1), (200,0)])
def test_keyboard_delegates_original_selection_and_reveals_row(key, wanted):
    execute(setup() + f'''
        [_hit,"key",{key}] call ACME_fnc_transfusionCardSelect;
        [(_list getVariable "sel")=={wanted} && {{_selectedCalls==1}},"keyboard failed native selection"] call _check;
    ''')


def test_wheel_changes_only_card_viewport_and_consumes_parent_scroll():
    execute(setup() + r'''
        private _consumed=[_hit,"wheel",-1] call ACME_fnc_transfusionCardSelect;
        [_consumed && {(_list getVariable "sel")==-1} && {_selectedCalls==0} && {_refreshCalls==1},"wheel changed clinical selection or escaped parent"] call _check;
    ''')


@pytest.mark.parametrize("scope", ["current", "removed", "moved", "site", "iv", "patient", "limb"])
def test_card_medication_title_and_dose_belong_to_same_physical_uid(scope):
    source = (FUN / 'fn_transfusionCardData.sqf').read_text()
    replacements = {
        'ctrlIDC _list': '86129', '_list lbText _row': '"Saline (100 mL)"',
        '_list lbColor _row': '[1,1,1,1]', '_list lbPicture _row': '"native-saline.paa"',
        '_list lbPictureRight _row': '"native-vial.paa"', '_list lbValue _row': '1',
    }
    for before, after in sorted(replacements.items(), key=lambda item: -len(item[0])):
        source = source.replace(before, after)
    # Native CfgWeapons is the engine art lookup boundary; supplied list icons remain intact.
    source = re.sub(r'getText \(configFile >> "CfgWeapons" >>[^;]+\)', '""', source)
    presentation = presentation_setup().replace('private _cfg = configFile >> "CfgWeapons" >> _class;', 'private _cfg = configFile;')
    presentation = presentation.replace('getText (_cfg >> "shortName")', '""').replace('getText (_cfg >> "displayName")', '""')
    fixture = presentation + 'ACME_fnc_infusionTitle={' + primitives(adapt((FUN / 'fn_infusionTitle.sqf').read_text())) + '};' + r'''
        ACM_circulation_fnc_formatFluidBagName={"Fixture"};
        ACME_fnc_infusionName={_this select 0};ACME_fnc_formatDose={format ["%1 mcg",_this select 1]};
        private _list=profileNamespace;private _row=0;
        private _selection=[+_primary,+_secondary];
        {private _uid=_x param[8,""];_x set[8,_forEachIndex];_x set[9,_uid];}forEach _selection;
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Target",_patient];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_BodyPart","leftarm"];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_SelectIV",true];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_AccessSite",0];
        missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selection_IVBags",_selection];
        private _entry=[];for "_i" from 0 to 23 do {_entry pushBack 0;};_entry set[11,"Epinephrine"];_entry set[14,995.1];_entry set[20,20];_entry set[21,60];_entry set[22,-1];_entry set[23,"secondary"];
        _patient setVariable["ACME_infusion_BagMedications",[_entry]];
        private _before=str(_patient getVariable "ACM_circulation_IV_Bags");
    ''' + 'ACME_fnc_transfusionCardData={' + primitives(adapt(source)) + '};'
    changes = {
        "current": "",
        "removed": '_patient setVariable["ACM_circulation_IV_Bags",createHashMapFromArray[["leftarm",[]]]];',
        "moved": '_secondary set[3,1];',
        "site": 'missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_AccessSite",1];',
        "iv": 'missionNamespace setVariable["ACM_circulation_TransfusionMenu_SelectIV",false];',
        "patient": 'missionNamespace setVariable["ACM_circulation_TransfusionMenu_Target",_medic];',
        "limb": 'missionNamespace setVariable["ACM_circulation_TransfusionMenu_Selected_BodyPart","rightarm"];',
    }
    fixture += changes[scope] + '_before=str(_patient getVariable "ACM_circulation_IV_Bags");private _data=[_list,0]call ACME_fnc_transfusionCardData;'
    if scope != "current":
        execute(fixture + r'''
            [(_data select [0,4])isEqualTo["","","",""],"stale patient/access/UID leaked medication or warmer metadata"]call _check;
            [(_data select 5)==""&&{(_data select 6)==""}&&{(_data select 7)==-1},"stale metadata retained another bag's artwork/progress"]call _check;
            [_before==str(_patient getVariable "ACM_circulation_IV_Bags"),"read-only stale guard mutated custody"]call _check;
        ''')
        return
    fixture += r'''
        [(_data select 0)=="Epinephrine infusion [PiB]","infusion card was labeled saline instead of medication"]call _check;
        [(_data select 1)find"995.1 mcg remaining">=0,"dose was stranded outside its infusion card"]call _check;
        [(_data select 2)=="Piggyback Secondary","medication card lost its secondary role label"]call _check;
        [(_data select 5)=="native-saline.paa"&&{(_data select 6)=="native-vial.paa"},"native art replaced"]call _check;
        [_before==str(_patient getVariable "ACM_circulation_IV_Bags"),"presentation mutated patient fluid custody"]call _check;
    '''
    execute(fixture)


def test_native_window_is_rounded_and_draws_before_body_and_overlays():
    dialog = (ROOT / 'addons/circulation/TransfusionMenu_Dialog.hpp').read_text()
    assert dialog.index('class MenuBackground: RscControlsGroupNoScrollbars') < dialog.index('class BodyBackground:')
    assert 'idc = 86400;' in dialog
    assert 'ACME_TxWindow' not in (ROOT / 'addons/acm_extended/TransfusionMenu_Chrome.hpp').read_text()
    assert dialog.count('ui\\transfusion\\window_') == 9
    assert 'class BodyBackground: RscPictureKeepAspect' in dialog


def test_card_rendering_is_bounded_change_only_and_preserves_popup_guards():
    render = (FUN / 'fn_updateTransfusionCards.sqf').read_text()
    layout = (FUN / 'fn_layoutTransfusionMenu.sqf').read_text()
    assert '[[86004,2,' in render and '[86129,2,' in render and '[86005,3,' in render and '[86145,3,' in render and '[86127,2,' in render
    assert render.index('findDisplay 86200') < render.index('ctrlCreate')
    assert render.index('findDisplay 84000') < render.index('ctrlCreate')
    assert 'if (isNull _group) then {' in render
    assert 'addPerFrameHandler' not in render + layout
    assert 'lbClear' not in render and 'lbDelete' not in render
    assert 'call ACME_fnc_updateTransfusionCards' in layout
    assert '[86126,86213,86176,86177,86178]' in layout
    assert 'ctrlParentControlsGroup' in render


@pytest.mark.parametrize("width,height", [(1280,960),(1920,1080),(3440,1440),(5120,1440)])
def test_nine_slice_radius_is_circular_and_edges_have_no_gaps(width, height):
    source = (FUN / "fn_transfusionRoundedFrame.sqf").read_text()
    source = source.replace('isNull _group', 'false')
    source = source.replace('_group controlsGroupCtrl _i', '_i')
    source = source.replace('_piece ctrlEnable false;', '')
    source = source.replace('safeZoneH', '1').replace('pixelW', str(1 / width)).replace('pixelH', str(1 / height))
    execute(r'''
        private _group=profileNamespace;private _pieces=[];private _writes=0;
        ACME_fnc_transfusionUiSet={params["_c","_property","_value"];
            if(_property=="position"&&{_c isEqualType 0})then{_pieces set[_c,_value];_writes=_writes+1;};true};
    ''' + 'ACME_fnc_transfusionRoundedFrame={' + adapt(source) + '};' + f'''
        [_group,[0,0,.78,.84],"window",.012]call ACME_fnc_transfusionRoundedFrame;
        [count _pieces==9,"nine slice geometry incomplete"]call _check;
        private _rx=(_pieces select 0)select 2;private _ry=(_pieces select 0)select 3;
        [abs(_rx*{width}-_ry*{height})<.0001,"rounded corner radius stretched with screen aspect"]call _check;
        [abs(((_pieces select 2)select 0)+((_pieces select 2)select 2)-.78)<.0001,"right edge seam"]call _check;
        [abs(((_pieces select 8)select 1)+((_pieces select 8)select 3)-.84)<.0001,"bottom edge seam"]call _check;
        [abs(((_pieces select 1)select 0)+((_pieces select 1)select 2)-((_pieces select 2)select 0))<.0001,"top edge has a gap"]call _check;
        [_group,[0,0,.78,.84],"window",.012]call ACME_fnc_transfusionRoundedFrame;
        [_writes==9,"unchanged frame recommitted every refresh"]call _check;
    ''')


def test_default_rounded_profile_points_to_shipped_native_assets():
    source = (FUN / "fn_transfusionRoundedFrame.sqf").read_text()
    default = re.search(r'\["_profile","([^"]+)"\]', source).group(1)
    assets = ROOT / "addons/acm_extended/ui/transfusion"
    for part in ("tl", "top", "tr", "left", "center", "right", "bl", "bottom", "br"):
        assert (assets / f"{default}_{part}_ca.paa").is_file()
    render = (FUN / "fn_updateTransfusionCards.sqf").read_text()
    assert '[_name,_detail,_status,_thermal,_list lbTooltip _row]' in render


@pytest.mark.parametrize("width,height,idc,thermal", [(1280,960,86004,"LW Quantum · Warming..."),(1440,1080,86129,"LW Quantum · Warming..."),(1920,1080,86129,"LW Quantum · Warming..."),(5120,1440,86127,"")])
def test_narrow_active_metadata_stacks_full_labels_above_progress(width, height, idc, thermal):
    source = (FUN / "fn_updateTransfusionCards.sqf").read_text()
    begin = source.index('private _stackMeta =')
    end = source.index('// Native icon and fill geometry', begin)
    geometry = source[begin:end].replace('safeZoneH', '1').replace('pixelW', str(1 / width)).replace('pixelH', str(1 / height))
    card_width = .2 if idc == 86004 else .212
    execute(f'''
        private _idc={idc};private _thermal="{thermal}";private _w={card_width};private _rowH=.09;
        private _pad=_w*.045;private _textX=_w*.15;private _textW=_w*.75;
    ''' + geometry + r'''
        if(_stackMeta)then{
            private _name=_metaPositions select 0 select 1;private _dose=_metaPositions select 1 select 1;
            private _status=_metaPositions select 2 select 1;private _warm=_metaPositions select 3 select 1;
            [(_name select 1)+(_name select 3)<=(_dose select 1)+.00001,"name/dose text boxes overlap"]call _check;
            [(_dose select 1)+(_dose select 3)<=(_status select 1),"dose/role text boxes overlap"]call _check;
            [(_status select 1)+(_status select 3)<=(_warm select 1),"role/temperature boxes overlap"]call _check;
            [(_warm select 1)+(_warm select 3)<_trackY,"warming ellipsis collides with progress track"]call _check;
            [(_warm select 2)>=_w*.90,"narrow warmer label still confined to half the card"]call _check;
        }else{
            [(_metaPositions select 2 select 1 select 1)==(_metaPositions select 3 select 1 select 1),"wide metadata lost its shared baseline"]call _check;
        };
    ''')


def test_native_button_tab_focus_keeps_visible_frame_and_no_treatment_action():
    source = (FUN / "fn_layoutTransfusionMenu.sqf").read_text()
    focus = re.search(r'_button ctrlAddEventHandler \["SetFocus",(\{[^\n]+\})\];', source).group(1)
    blur = re.search(r'_button ctrlAddEventHandler \["KillFocus",(\{[^\n]+\})\];', source).group(1)
    expression = re.search(r'(\["button","selected"\] select .*?),0\.006,ctrlShown', source).group(1)
    focus = focus.replace('ctrlParent (_this select 0)', 'missionNamespace')
    blur = blur.replace('ctrlParent (_this select 0)', 'missionNamespace')
    execute(r'''
        private _button=profileNamespace;private _refreshes=0;
        ACME_fnc_layoutTransfusionMenu={_refreshes=_refreshes+1;};
    ''' + '[_button]call ' + focus + ';private _focused=' + expression + ';[_button]call ' + blur + ';private _blurred=' + expression + ';' + r'''
        [_focused=="selected"&&{_blurred=="button"}&&{_refreshes==2},"Tab focus disappeared into transparent native background"]call _check;
    ''')


def test_service_tint_reaches_all_nine_rounded_pieces_and_is_cached():
    source = (FUN / "fn_transfusionRoundedFrame.sqf").read_text()
    source = source.replace('isNull _group', 'false').replace('_group controlsGroupCtrl _i', '_i').replace('_piece ctrlEnable false;', '')
    source = source.replace('safeZoneH', '1').replace('pixelW', '.0005').replace('pixelH', '.001')
    execute(r'''
        private _group=profileNamespace;private _colors=[];private _colorWrites=0;
        ACME_fnc_transfusionUiSet={params["_c","_property","_value"];if(_property=="color"&&{_c isEqualType 0})then{_colors set[_c,_value];_colorWrites=_colorWrites+1;};true};
    '''+'ACME_fnc_transfusionRoundedFrame={'+adapt(source)+'};'+r'''
        private _pulse=[.35,1,.45,.9];
        [_group,[0,0,.2,.03],"button",.006,true,_pulse]call ACME_fnc_transfusionRoundedFrame;
        [count _colors==9&&{(_colors findIf{_x isNotEqualTo _pulse})<0},"Prime/Flush pulse failed to tint rounded skin"]call _check;
        [_group,[0,0,.2,.03],"button",.006,true,_pulse]call ACME_fnc_transfusionRoundedFrame;
        [_colorWrites==9,"unchanged service skin repainted every UI tick"]call _check;
    ''')
    assert '_button getVariable ["ACME_txSkinTint",[1,1,1,1]]' in (FUN / 'fn_layoutTransfusionMenu.sqf').read_text()


@pytest.mark.parametrize("idc,wanted", [(86144,.018),(86141,.020)])
def test_prepared_toggle_font_fits_narrow_screen_and_only_repaints_on_change(idc, wanted):
    source = (FUN / 'fn_layoutTransfusionMenu.sqf').read_text()
    begin = source.index('private _fontHeight =')
    end = source.index('};\n    };\n} forEach _roundButtons', begin) + 2
    font = source[begin:end].replace('safeZoneH', '1').replace('pixelW', '.00075').replace('pixelH', '.001')
    font = font.replace('ctrlIDC _button', str(idc)).replace('ctrlPosition _button', '[0,0,.202,.034]')
    font = font.replace('_button ctrlSetFontHeight _fontHeight;', '_writes pushBack _fontHeight;')
    execute('private _button=profileNamespace;private _writes=[];'+font+font+f'''
        [_writes isEqualTo [{wanted}],"prepared chooser text clipped or unchanged font repainted"]call _check;
    ''')
