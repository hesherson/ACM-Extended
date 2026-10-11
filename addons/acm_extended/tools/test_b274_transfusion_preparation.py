"""Execute staged-bag completion and temporary saline picking in production SQF.

Arma display/config/inventory primitives are explicit fixtures. Preparation,
receipt settlement, mode selection and native inventory-row decisions run from
the current sources; native rendering/network transport remain acceptance work.
"""
import re

import pytest

from test_b156_procedure_supplies import primitives, supply_setup
from test_b226_transfusion_presentation import switch_ui_setup
from test_menu_death_lifecycle import ROOT, adapt, execute, read


def gui(source):
    source = source.replace("findDisplay 86000", "_display")
    source = source.replace("isNull (_display)", "(_display isEqualTo objNull)")
    source = source.replace("_display displayCtrl 86005", "_rightFixture")
    source = source.replace("lbCurSel _right", "_selection")
    source = source.replace("lbSize _right", "count _rowData")
    source = re.sub(r"_right lbData (_\w+)", r"(_rowData select \1)", source)
    source = source.replace("_medic distance _target", "_distance")
    source = source.replace("objectParent ACE_player", "objNull")
    source = re.sub(r'getText \(_[a-zA-Z]+ >> "(?:displayName|shortName)"\)', '"Fixture bag"', source)
    source = re.sub(r'isText \(_[a-zA-Z]+ >> "shortName"\)', 'false', source)
    source = re.sub(r'(private _[a-zA-Z]+ = )configFile >> "CfgWeapons" >> _(?:class|blood);', r'\1configNull;', source)
    return primitives(adapt(source))


def compiled(name):
    return f"ACME_fnc_{name}={{" + gui(read(name)) + "};"


def picker_setup():
    return r'''
      private _display=missionNamespace;
      private _refreshes=[];
      // Native inventory was already painted for this baseline context.
      _display setVariable ["ACME_txPickerSignature",str [false,[]]];
      ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory={_refreshes pushBack _this;};
      uiNamespace setVariable ["ACME_preparedListMode",false];
      missionNamespace setVariable ["ACME_yPending",""];
      missionNamespace setVariable ["ACME_yPendingSaline",""];
      missionNamespace setVariable ["ACME_piggybackPending",[]];
    ''' + compiled("transfusionFilterInventory") + compiled("togglePreparedSets")


@pytest.mark.parametrize("leave", ["selected", "cancel", "prepared"])
def test_saline_picker_refreshes_only_on_step_transitions_and_restores_inventory(leave):
    ending = {
        "selected": 'missionNamespace setVariable ["ACME_yPendingSaline","SalineIV_500"];',
        "cancel": 'missionNamespace setVariable ["ACME_yPending",""];',
        "prepared": '[true] call ACME_fnc_togglePreparedSets;',
    }[leave]
    execute(picker_setup() + r'''
      [!call ACME_fnc_transfusionFilterInventory && {_refreshes isEqualTo []},"normal inventory unexpectedly rebuilt"] call _check;
      missionNamespace setVariable ["ACME_yPending","BloodIV_500"];
      [call ACME_fnc_transfusionFilterInventory,"pending blood did not enter saline picker"] call _check;
      [call ACME_fnc_transfusionFilterInventory && {_refreshes isEqualTo [[false]]},"steady selector churned list or advanced inventory"] call _check;
    ''' + ending + r'''
      [!call ACME_fnc_transfusionFilterInventory,"saline picker survived its step"] call _check;
      [!call ACME_fnc_transfusionFilterInventory && {_refreshes isEqualTo [[false],[false]]},"normal inventory did not restore once"] call _check;
      [(uiNamespace getVariable "ACME_usedRowSig")=="__force__" && {(uiNamespace getVariable "ACME_coolerRowSig")=="__force__"},"overlay inventory signatures remained stale"] call _check;
    ''')


@pytest.mark.parametrize("caller", ["[]", "[uiNamespace]"])
def test_manual_toggle_and_explicit_completion_open_prepared_view_idempotently(caller):
    execute(picker_setup() + caller + r''' call ACME_fnc_togglePreparedSets;
      [uiNamespace getVariable ["ACME_preparedListMode",false],"manual button did not open prepared sets"] call _check;
      [true] call ACME_fnc_togglePreparedSets;[true] call ACME_fnc_togglePreparedSets;
      [uiNamespace getVariable ["ACME_preparedListMode",false],"repeated successful spike toggled view closed"] call _check;
      [(_display getVariable ["ACME_txActivePane",""])=="prepared","prepared pane not selected"] call _check;
      [] call ACME_fnc_togglePreparedSets;
      [!(uiNamespace getVariable ["ACME_preparedListMode",true]) && {(_display getVariable ["ACME_txActivePane",""])=="inventory"},"manual return to loose bags failed"] call _check;
    ''')


@pytest.mark.parametrize("mode", [0, 1, 2])
def test_native_inventory_only_shows_saline_while_pairing_and_restores_all_sources(mode):
    execute(switch_ui_setup() + compiled("isSalineItem") + f'''
      uiNamespace setVariable ["ACME_preparedListMode",false];
      _vehicleNow=missionNamespace;
      ACM_circulation_TransfusionMenu_Selected_Inventory={mode};
      _medic setVariable ["stock",["SalineIV","BloodIV","PlasmaIV","ACME_PlasmaLyteBag_500","ACM_Vial_Propofol"]];
      _patient setVariable ["stock",["SalineIV","BloodIV","PlasmaIV","ACME_PlasmaLyteBag_500","ACM_Vial_Propofol"]];
      _vehicleCargo=[["SalineIV","BloodIV","PlasmaIV","ACME_PlasmaLyteBag_500","ACM_Vial_Propofol"],[1,1,1,1,1]];
      missionNamespace setVariable ["ACME_yPending","BloodIV"];
      missionNamespace setVariable ["ACME_yPendingSaline",""];
      [false] call _switchInventory;
      [_rows isEqualTo ["SalineIV"],"non-saline offered during flush-saline selection"] call _check;
      [ACM_circulation_TransfusionMenu_Selected_Inventory=={mode},"filter changed selected inventory source"] call _check;
      missionNamespace setVariable ["ACME_yPendingSaline","SalineIV"];
      [false] call _switchInventory;
      [count _rows==5 && {{"BloodIV" in _rows}} && {{"PlasmaIV" in _rows}} && {{"ACM_Vial_Propofol" in _rows}},"ordinary inventory not restored"] call _check;
    ''')


@pytest.mark.parametrize("own", [False, True])
@pytest.mark.parametrize("selecting", [False, True])
def test_production_cooler_and_used_overlay_inputs_obey_the_temporary_saline_filter(own, selecting):
    controller = read("updateTransfusionControls")
    cooler = controller[controller.index("private _store ="):controller.index("private _wantKeys = keys _want;")]
    cooler = cooler.replace("((uniformItems ACE_player) + (vestItems ACE_player) + (backpackItems ACE_player))", "_heldInventory")
    cooler = re.sub(r'nearestObjects \[ACE_player, \[[^\n]+?\], 6\]', '_nearbyBoxes', cooler)
    cooler = cooler.replace("itemCargo _bx", '(_bx getVariable ["fixtureCargo",[]])')
    used = controller[controller.index("private _usedBags ="):controller.index("private _usedSig =")]
    execute(r'''
      private _display=missionNamespace;
      private _heldInventory=["ACME_BloodCooler_CSWB1U"];
      private _nearbyBoxes=[missionNamespace];
      missionNamespace setVariable ["fixtureCargo",["ACM_BloodBag_ON_500"]];
      private _coolerStock=createHashMapFromArray [["ACME_BloodCooler_CSWB1U",[["ACM_BloodBag_ON_500",500]]]];
      ACE_player setVariable ["ACME_coolerStore",_coolerStock];
      private _usedStock=[["blood","Blood",400],["saline","Saline",150],["y-saline","ACME_SalineY",75],["plasma","Plasma",100],["plasmalyte","PlasmaLyte",200]];
      ACE_player setVariable ["ACME_usedBags",_usedStock];
      private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    ''' + f'private _ownInventory={str(own).lower()};private _selectingSalineInventoryB274={str(selecting).lower()};private _selectingPiggyback=false;' + primitives(adapt(cooler + used)) + f'''
      [count _want=={int(own and not selecting)},"cooler blood leaked into saline picker or another source"] call _check;
      [count _usedBags=={(2 if selecting else 5) if own else 0},"used overlay ignored source or saline filter"] call _check;
      if (_selectingSalineInventoryB274) then {{[(_usedBags findIf {{!((_x select 1) in ["Saline","ACME_SalineY"])}})<0,"used non-saline shown during picker"] call _check;}};
      [(ACE_player getVariable "ACME_usedBags") isEqualTo _usedStock,"temporary UI filter consumed used bag custody"] call _check;
      [((ACE_player getVariable "ACME_coolerStore") get "ACME_BloodCooler_CSWB1U") isEqualTo [["ACM_BloodBag_ON_500",500]],"temporary UI filter consumed cooler stock"] call _check;
    ''')


def stage_setup():
    return supply_setup() + picker_setup() + r'''
      private _rightFixture=missionNamespace;
      private _rowData=[];private _selection=0;private _bagRefreshes=0;
      private _initialBags=createHashMapFromArray [["leftarm",[["Plasma",300,1,1,true,-1,500,-1,"existing-line"]]]];
      _patient setVariable ["ACM_circulation_IV_Bags",_initialBags];
      private _initialBagText=str _initialBags;
      ACM_circulation_TransfusionMenu_Target=_patient;
      ACM_circulation_TransfusionMenu_Selected_BodyPart="leftarm";
      ACM_circulation_TransfusionMenu_Selected_AccessSite=0;
      ACM_circulation_TransfusionMenu_SelectIV=true;
      ACM_circulation_TransfusionMenu_Selected_Inventory=0;
      ACME_fnc_updateTransfusionControls={};
      ACM_circulation_fnc_TransfusionMenu_UpdateBagList={_bagRefreshes=_bagRefreshes+1;};
      ACME_fnc_carrierSupplyTake={[objNull,"",false,objNull]};
      ACME_fnc_itemTake={params ["_u","_c"];private _a=+(_u getVariable ["fixtureStock",[]]);private _i=_a find _c;if (_i<0) exitWith {false};_a deleteAt _i;_u setVariable ["fixtureStock",_a];true};
    ''' + compiled("isSalineItem") + compiled("transfusionTakeSelected") + compiled("treatmentSupplyTakeMany") + compiled("transfusionSpikeOrAdd") + compiled("transfusionYTubing")


@pytest.mark.parametrize("bag,action,kind", [
    ("ACM_SalineBag_500", "SalineIV_500", "saline"),
    ("ACM_BloodBag_ON_500", "BloodIV_ON_500", "blood"),
    ("ACME_PlasmaLyteBag_500", "PlasmaLyteIV_500", "premixed"),
])
def test_successful_single_bag_spike_opens_prepared_sets_without_hanging(bag, action, kind):
    execute(stage_setup() + f'''
      _rowData=["{bag}|{action}"];
      _medic setVariable ["fixtureStock",["{bag}","ACME_IVLine"]];
      [] call ACME_fnc_transfusionSpikeOrAdd;
      [!(uiNamespace getVariable ["ACME_preparedListMode",true]) && {{count _waits==1}},"prepared pane opened before successful commit"] call _check;
      (_waits select 0 select 1) call (_waits select 0 select 0);
      private _sets=_medic getVariable ["ACME_preparedIVSets",[]];
      [count _sets==1 && {{(_sets select 0 select 1)=="{bag}"}} && {{(_sets select 0 select 8)=="{kind}"}},"spiked physical bag missing from carried prepared custody"] call _check;
      [(_medic getVariable "fixtureStock") isEqualTo [],"bag/one IV line not consumed exactly once"] call _check;
      [uiNamespace getVariable ["ACME_preparedListMode",false],"successful spike did not reveal Prepared IV Sets"] call _check;
      [str (_patient getVariable "ACM_circulation_IV_Bags")==_initialBagText && {{_events isEqualTo []}} && {{_bagRefreshes==0}},"preparation changed patient Fluids or hung the bag early"] call _check;
    ''')


@pytest.mark.parametrize("missing", ["bag", "line"])
def test_disappearing_single_bag_components_do_not_switch_view_or_create_a_set(missing):
    remaining = '["ACME_IVLine"]' if missing == "bag" else '["ACM_SalineBag_500"]'
    execute(stage_setup() + r'''
      _rowData=["ACM_SalineBag_500|SalineIV_500"];
      _medic setVariable ["fixtureStock",["ACM_SalineBag_500","ACME_IVLine"]];
      [] call ACME_fnc_transfusionSpikeOrAdd;
    ''' + f'_medic setVariable ["fixtureStock",{remaining}];' + r'''
      (_waits select 0 select 1) call (_waits select 0 select 0);
      [(_medic getVariable ["ACME_preparedIVSets",[]]) isEqualTo [],"failed spike invented prepared custody"] call _check;
      [!(uiNamespace getVariable ["ACME_preparedListMode",true]),"failed spike switched to prepared sets"] call _check;
      [str (_patient getVariable "ACM_circulation_IV_Bags")==_initialBagText && {_events isEqualTo []},"failed preparation changed patient bags"] call _check;
    ''')


def test_complete_y_build_opens_prepared_sets_and_leaves_existing_fluids_untouched():
    execute(stage_setup() + r'''
      _rowData=["ACM_BloodBag_ON_500|BloodIV_ON_500","ACM_SalineBag_500|SalineIV_500"];
      _medic setVariable ["fixtureStock",["ACM_BloodBag_ON_500","ACM_SalineBag_500","ACME_YTubing"]];
      [] call ACME_fnc_transfusionYTubing;
      [call ACME_fnc_transfusionFilterInventory && {!(uiNamespace getVariable ["ACME_preparedListMode",true])},"blood arm skipped saline picker"] call _check;
      _selection=1;[] call ACME_fnc_transfusionYTubing;
      [!call ACME_fnc_transfusionFilterInventory && {!(uiNamespace getVariable ["ACME_preparedListMode",true])},"saline selection prematurely opened prepared sets"] call _check;
      [] call ACME_fnc_transfusionYTubing;
      [count _waits==1,"Y build did not schedule one completion"] call _check;
      (_waits select 0 select 1) call (_waits select 0 select 0);
      private _sets=_medic getVariable ["ACME_preparedIVSets",[]];
      [count _sets==1 && {(_sets select 0 select 8)=="yset"},"Y build missing from prepared custody"] call _check;
      [(_medic getVariable "fixtureStock") isEqualTo [],"Y components not consumed exactly once"] call _check;
      [uiNamespace getVariable ["ACME_preparedListMode",false],"Y completion did not reveal Prepared IV Sets"] call _check;
      [str (_patient getVariable "ACM_circulation_IV_Bags")==_initialBagText && {_events isEqualTo []} && {_bagRefreshes==0},"Y preparation changed existing active Fluids or hung early"] call _check;
      [(missionNamespace getVariable ["ACME_yPending",""])=="" && {!(call ACME_fnc_transfusionFilterInventory)},"completed Y set left saline picker armed"] call _check;
    ''')
