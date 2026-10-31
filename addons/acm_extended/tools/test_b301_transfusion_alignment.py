"""Warm-state presentation, stable topology, inventory source routing and mirrored native geometry."""
import re
from pathlib import Path
import pytest
from test_menu_death_lifecycle import ROOT,adapt,execute,read
from test_b275_transfusion_presentation import presentation_setup
from test_b278_transfusion_geometry import renderer_setup,renderer_source
from test_b273_transfusion_layout import fixed_layout

BASE='4944aaa6bae41fb06a4576c925805d657d386294'

@pytest.mark.parametrize('second,tail',[(30,'.'),(31,'..'),(32,'...'),(33,'.')])
@pytest.mark.parametrize('kind',['Saline','ACME_Propofol','Magnesium'])
def test_flowing_supported_infusion_has_orange_ascii_warmer_and_native_dots(kind,second,tail):
    execute(presentation_setup()+f'''
        _secondary set [0,"{kind}"];_nowTime={second};
        private _result=[_patient,"leftarm",_secondary,"Carrier"] call ACME_fnc_transfusionBagPresentation;
        [(_result select 2)=="LW Quantum / Warming{tail}" && {{(_result select 1) isEqualTo [1,.55,.13,1]}},"flowing infusion lost orange warming status/dots"] call _check;
        private _held=[_patient,"leftarm",_primary,"Saline"] call ACME_fnc_transfusionBagPresentation;
        [!(_held select 4) && {{(_held select 2)=="LW Quantum / Inline"}},"held primary falsely claims warming"] call _check;
    ''')


def paint_function():
    source=read('paintTransfusionYBracket')
    a=source.index('private _ensure =');b=source.index('private _controls =',a)
    source=source[:a]+'private _ensure={_this select 0};\n'+source[b:]
    source=source.replace('_display displayCtrl 86004','86004').replace('_display displayCtrl 86160','86160')
    source=source.replace('isNull _list','false').replace('ctrlPosition _list','(_positions get _list)')
    source=source.replace('lbSize _list','(_counts get _list)').replace('_list lbValue _row','_row').replace('_list lbValue _x','_x')
    source=source.replace('ctrlShown _list','false')
    for a,b in [('safeZoneW','1.7777778'),('safeZoneH','1'),('pixelW','(1/1920)'),('pixelH','(1/1080)')]:source=source.replace(a,b)
    from test_historical_vial_execution import map_defaults
    return 'ACME_fnc_paintTransfusionYBracket={'+map_defaults(adapt(source))+'};'


def topology_setup():
    return renderer_setup()+r'''
        _counts set [86004,2];_counts set [86129,1];_counts set [86005,0];_counts set [86145,0];_counts set [86127,0];
        ACME_fnc_transfusionCardIdentity={params ["_l","_r"];if (_r<0) exitWith {[]};["active","leftarm",true,0,if (_l==86004) then {["a","b"] select _r} else {"c"}]};
        private _a=[];_a set [9,"a"];private _b=[];_b set [9,"b"];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags",[_a,_b]];
        ACME_fnc_transfusionYRows={[[0,1],"leftarm#true#0"]};
        ACME_fnc_piggybackLine={["a","c",1]};
    '''+paint_function()

@pytest.mark.parametrize('menu',['bag','infusion',''])
def test_y_and_piggyback_rails_keep_the_same_live_endpoints_during_popovers(menu):
    execute(topology_setup()+r'''
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        [missionNamespace] call ACME_fnc_paintTransfusionYBracket;
        private _before=str (missionNamespace getVariable "ACME_txCardEndpoints");
        private _railBefore=+(_controlValues get "86220:position");
    '''+f'missionNamespace setVariable ["ACME_txActionMenu","{menu}"];'+r'''
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        [missionNamespace] call ACME_fnc_paintTransfusionYBracket;
        [_before==str (missionNamespace getVariable "ACME_txCardEndpoints"),"popover discarded a physical UID endpoint"] call _check;
        {[_controlValues get format["%1:show",_x],"opening actions hid a live connector"] call _check;} forEach [86184,86185,86186,86220,86221,86222,86223,86224,86225,86226,86227];
        [(_controlValues get "86220:position") isEqualTo _railBefore,"rail jumped when card face hid"] call _check;
    ''')


def test_removed_carrier_drops_its_endpoint_instead_of_caching_an_old_line():
    execute(topology_setup()+r'''
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        _counts set [86129,0];
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        [missionNamespace] call ACME_fnc_paintTransfusionYBracket;
        [!("c" in (missionNamespace getVariable "ACME_txCardEndpoints")),"removed carrier retained stale endpoint"] call _check;
        [!(_controlValues get "86220:show"),"orphaned piggyback rail remained"] call _check;
    ''')

@pytest.mark.parametrize('aspect',[4/3,16/9,21/9,32/9])
def test_column_pairs_are_exact_mirrors_and_share_header_list_and_action_rows(aspect):
    rects=fixed_layout();canvas=min(aspect,1.7777778)
    for a,b in [(86160,86161),(86004,86145),(86129,86127),(86128,86130)]:
        left,right=rects[a],rects[b]
        assert left[1:]==pytest.approx(right[1:])
        assert (left[0]+right[0]+left[2])*canvas==pytest.approx(canvas)
    for pair in [(86006,86170),(86214,86144),(86131,86172)]:
        a,b=(rects[x] for x in pair)
        assert a[1:]==b[1:] and b[0]-a[0]-a[2]==pytest.approx(.004)
    assert rects[86006][1:]==rects[86214][1:]
    assert rects[86131][1]==rects[86122][1] and rects[86131][3]==rects[86122][3]
    footer=rects[86171]
    assert footer[0]==rects[86129][0] and footer[2]==rects[86129][2] and footer[1]>.801
    assert not {86003,86037}.intersection(rects)


def test_native_cards_are_centered_and_scrollbars_face_outward_without_browser_drift():
    execute(renderer_setup()+r'''
        _positions set [86004,[.125*1.7777778,.228,.212*1.7777778,.210]];
        _positions set [86005,[.663*1.7777778,.228,.212*1.7777778,.210]];
        [missionNamespace] call ACME_fnc_updateTransfusionCards;
        private _left=_controlValues get "86500:position";private _right=_controlValues get "86520:position";
        [abs ((_left select 0)+(_right select 0)+(_left select 2)-1.7777778)<.00001,"card surfaces not mirrored"] call _check;
        [(_left select 1)==(_right select 1) && {(_left select 3)>(_right select 3)},"compact fluid row lost its shared top or density"] call _check;
        private _ls=_controlValues get "86610:position";private _rs=_controlValues get "86614:position";
        [(_ls select 0)<(_left select 0) && {(_rs select 0)>(_right select 0)+(_right select 2)},"scrollbars encroach on mirrored card areas"] call _check;
    '''+'ACME_fnc_reactMedicalRect={'+renderer_source('reactMedicalRect')+'};'+r'''
        private _layout=(missionNamespace getVariable "ACME_txCardLayout") get 86004;
        private _browser=[_layout] call ACME_fnc_reactMedicalRect;
        [abs ((_browser select 0)-(_left select 0))<.00001 && {abs ((_browser select 2)-(_left select 2))<.00001},"browser and native card changed horizontal origin"] call _check;
    ''')


def switch_setup():
    source=(ROOT/'addons/circulation/functions/fnc_TransfusionMenu_SwitchTargetInventory.sqf').read_text()
    source=source[source.index('// Native button callbacks'):source.index('private _cachedItems')]
    source=source.replace('objectParent _medic','_mounted').replace('private _display = uiNamespace getVariable [QGVAR(TransfusionMenu_DLG), displayNull];','private _display=missionNamespace;').replace('_display displayCtrl 86214','86214')
    source=adapt(source,component='circulation').replace('_medic == ACM_circulation_TransfusionMenu_Target','_medic isEqualTo ACM_circulation_TransfusionMenu_Target')
    return r'''
      private _mounted=objNull;private _labels=[];ACE_player=_medic;
      ACME_fnc_controlledProvider={_medic};
      missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Medic",_medic];
      missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",_patient];
      ACM_circulation_TransfusionMenu_Selected_Inventory=0;
      ACME_fnc_transfusionUiSet={params ["_c","_op","_text"];_labels pushBack [_c,_text];};
    '''+'ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory={'+source+'};'


def test_inventory_source_cycles_on_one_button_and_false_refresh_does_not_advance():
    execute(switch_setup()+r'''
      [false] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
      [ACM_circulation_TransfusionMenu_Selected_Inventory==0 && {(_labels select 0 select 1)=="Inventory (Self)"},"refresh advanced or lost self source"] call _check;
      [true] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
      [ACM_circulation_TransfusionMenu_Selected_Inventory==1 && {(_labels select 1 select 1)=="Inventory (Patient)"},"button failed to select patient inventory"] call _check;
      [true] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
      [ACM_circulation_TransfusionMenu_Selected_Inventory==0,"unavailable vehicle was not skipped"] call _check;
      _mounted=uiNamespace;
      [true] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
      [true] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
      [ACM_circulation_TransfusionMenu_Selected_Inventory==2 && {(_labels select ((count _labels)-1) select 1)=="Inventory (Vehicle)"},"existing vehicle inventory was lost"] call _check;
    ''')


def test_inventory_click_returns_from_prepared_view_before_advancing_source():
    source=read('layoutTransfusionMenu');a=source.index('_inventoryTab ctrlAddEventHandler ["ButtonClick",{')
    a=source.index('{',a);from test_historical_core_boundaries import block_at
    callback=block_at(source,a)
    execute(r'''
      private _cycle=0;private _refresh=0;
      ACME_fnc_togglePreparedSets={uiNamespace setVariable ["ACME_preparedListMode",_this select 0];};
      ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory={_cycle=_cycle+1;};
      ACME_fnc_updateTransfusionControls={_refresh=_refresh+1;};
      uiNamespace setVariable ["ACME_preparedListMode",true];
    '''+'private _click='+callback+';'+r'''
      call _click;
      [_cycle==0 && {!(uiNamespace getVariable "ACME_preparedListMode")},"returning to inventory unexpectedly changed source"] call _check;
      call _click;
      [_cycle==1 && {_refresh==1},"inventory press did not cycle through the native handler once"] call _check;
    ''')


def test_removed_target_controls_are_inert_and_only_own_ascii_status_changes():
    source=read('layoutTransfusionMenu');assert 'forEach [86003,86037]' in source
    dialog=(ROOT/'addons/circulation/TransfusionMenu_Dialog.hpp').read_text()
    for name in ['SelectedInventoryText','SwitchTargetInventory']:
        body=dialog[dialog.index('class '+name+':'):];body=body[:body.index('};')]
        assert 'w = QUOTE(0);' in body and 'h = QUOTE(0);' in body
    assert 'LW Quantum ·' not in read('transfusionBagPresentation')
    assert 'LW Quantum / Warming' in read('transfusionBagPresentation')
    assert '[".","..","..."]' in read('transfusionBagPresentation')


def test_b301_scope_keeps_ace_clinical_inventory_custody_and_original_body_art_exact():
    import subprocess
    def baseline(path):
        return subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
    protected=['addons/gui','addons/acm_extended/ui/iv','addons/acm_extended/ui/transfusion']
    assert not subprocess.check_output(['git','diff','--name-only',BASE,'de71fb771a30ae4e3cc25e1c115b65e7753a47d2','--',*protected],cwd=ROOT).strip()
    native='addons/circulation/functions/fnc_TransfusionMenu_SwitchTargetInventory.sqf'
    marker=b'private _cachedItems'
    assert (ROOT/native).read_bytes().split(marker,1)[1]==baseline(native).split(marker,1)[1]
    for name in ['updateTransfusionControls','updateTransfusionAccessHotspots','transfusionTagLeader','transfusionTagRect','piggybackAttachRequest','piggybackAttachLocal','reactMedicalMessage','reactMedicalValid']:
        path='addons/acm_extended/functions/fn_'+name+'.sqf'
        assert (ROOT/path).read_bytes()==baseline(path)
    dialog='addons/circulation/TransfusionMenu_Dialog.hpp'
    from source_scan import lex,matching
    def class_block(source,name):
        fragment=source[source.index("class "+name+":"):];tokens=lex(fragment)
        start=next(i for i,t in enumerate(tokens) if t.value=="{");end=matching(tokens)[start]
        return fragment[tokens[start].offset:tokens[end].offset]
    old=baseline(dialog).decode();new=subprocess.check_output(['git','show','de71fb771a30ae4e3cc25e1c115b65e7753a47d2:'+dialog],cwd=ROOT,text=True)
    for name in ['BodyBackground','BodyBackground_IO_Torso','BodyBackground_Tourniquet_RightArm','StopTransfusionButton']:
        # Stop height follows the shared row; its handler must remain byte-exact.
        a=class_block(old,name);b=class_block(new,name)
        if name=='StopTransfusionButton':b=b.replace('0.033','0.029')
        assert a==b
