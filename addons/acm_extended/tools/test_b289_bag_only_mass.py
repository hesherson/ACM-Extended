"""Run bag-only native carrier mass, custody and restart metadata together.

Native cargo, item weights/capacity and network transport are explicit engine
boundaries. Selector, registration, materialization, transfer, source receipts,
snapshot and restoration execute production SQF. No native Gear test is claimed.
"""
import re

import pytest

import test_menu_death_lifecycle as lifecycle
from test_b280_prepared_native_pipeline import setup as native_setup
from test_b279_inventory_ledger import adapted
from test_b288_inventory_persistence import source as persistence_source
from test_b289_empty_line_ui import ui
from test_menu_death_lifecycle import ROOT, execute, read


@pytest.fixture(autouse=True)
def no_native_boundary_warnings(monkeypatch):
    original = lifecycle.subprocess.run

    def checked(*args, **kwargs):
        result = original(*args, **kwargs)
        assert "[WRN]" not in result.stdout + result.stderr, result.stdout + result.stderr
        return result

    monkeypatch.setattr(lifecycle.subprocess, "run", checked)


def setup(sync=False):
    config = (ROOT / "addons/acm_extended/config.cpp").read_text()
    declared = re.findall(
        r'class (ACME_UnspikedBag_M\w+): ACME_UnspikedBag \{ mass = ([\d.Ee+-]+); \};', config)
    assert "ACME_UnspikedBag_M50" in dict(declared)
    masses = "\n".join(f'_carrierMass set ["{name}",{float(value):.12g}];' for name, value in declared)
    base = native_setup(sync)
    # Inventory initialization also registers its machine identity. Retain that
    # production handler so synchronous registration is not an undefined fixture.
    machine = "ACME_fnc_syringeDeliveryMachine={" + adapted(read("syringeDeliveryMachine")) + "};\n"
    base = base.replace("call ACME_fnc_inventoryLedgerInit;", machine + "call ACME_fnc_inventoryLedgerInit;")
    return base + masses + r'''
        private _bagID="bag-only";
        private _bagSet=[_bagID,"ACM_SalineBag_500","SalineIV_500","","","","Saline 500 mL",false,"bagOnly",500,0];
        private _bagPayload=[_bagID,_bagSet,[]];
        private _issueBag={[_medic,"prepared",[_bagPayload]] call ACME_fnc_inventoryLedgerCommit;call _flush;};
        private _bagTuple={(_uniform getVariable ["cargo",[]]) param [0,[]]};
        private _bagToken={(call _bagTuple) select 1};
        private _bagRecord={missionNamespace getVariable [format ["ACME_inventoryToken_%1",call _bagToken],[]]};
    '''


@pytest.mark.parametrize("source,weight,expected", [
    ("ACM_SalineBag_500", 5, "ACME_UnspikedBag_M50"),
    ("ACM_BloodBag_ON_500", 12.9, "ACME_UnspikedBag_M129"),
    ("ACM_Vial_Propofol", 1.65, "ACME_UnspikedBag_M1_65"),
    ("ACME_HTSBag", 6.2, "ACME_UnspikedBag_M62"),
])
def test_bag_only_selector_preserves_exact_fluid_mass_without_tubing(source, weight, expected):
    execute(setup() + f'''
        _bagSet set [1,"{source}"];
        private _class=["prepared",_bagPayload] call ACME_fnc_inventoryLedgerClass;
        [_class=="{expected}" && {{abs ((_carrierMass get _class)-{weight})<0.00001}},"bag-only carrier included tubing or changed fluid mass"] call _check;
        _bagSet set [8,"saline"];
        private _spiked=["prepared",_bagPayload] call ACME_fnc_inventoryLedgerClass;
        [abs ((_carrierMass get _spiked)-({weight}+0.1))<0.00001,"ordinary prepared-set mass lost its real IV line"] call _check;
    ''')


@pytest.mark.parametrize("source", ["UnknownBag", "MissingBag"])
def test_unsupported_bag_only_mass_is_refused_without_inventing_an_opaque_heavier_or_lighter_carrier(source):
    execute(setup() + f'''
        _bagSet set [1,"{source}"];
        [["prepared",_bagPayload] call ACME_fnc_inventoryLedgerClass=="","unsupported bag-only mass silently fell back to a fitted set"] call _check;
        _bagSet set [8,"saline"];
        [["prepared",_bagPayload] call ACME_fnc_inventoryLedgerClass=="ACME_PreparedIVSet","legacy unknown prepared-set fallback changed"] call _check;
        [(_uniform getVariable "cargo") isEqualTo [] && {{(_medic getVariable "ACME_preparedIVSets") isEqualTo []}},"mass lookup materialized or debited equipment"] call _check;
    ''')


@pytest.mark.parametrize("sync", [False, True])
def test_nearly_full_container_admits_the_actual_bag_mass_without_charging_or_creating_a_line(sync):
    execute(setup(sync) + r'''
        _medic setVariable ["containerMax",49.9];
        _medic setVariable ["fixtureStock",["HeavyKit","ACM_SalineBag_500"]];
        private _receipt=[_medic,_patient,"ACM_SalineBag_500",0,objNull] call ACME_fnc_transfusionTakeSelected;
        [count _receipt==4 && {(_receipt select 1)=="ACM_SalineBag_500"},"selected fluid did not fund its bag-only carrier"] call _check;
        [_receipt,false] call ACME_fnc_treatmentSupplyRefund;
        [[_medic,"ACME_UnspikedBag_M50",1,true] call _canAddNative,"5.0 mass fluid did not fit at the exact 49.9 edge"] call _check;
        [!([_medic,"ACME_PreparedIVSet_M51",1,true] call _canAddNative),"fixture did not distinguish the unwanted 0.1 tubing charge"] call _check;
        call _issueBag;
        private _tuple=call _bagTuple;
        [count _tuple==2 && {(_tuple select 0)=="ACME_UnspikedBag_M50"},"registered bag-only carrier used fitted-tubing mass/class"] call _check;
        [(_medic getVariable "fixtureStock") isEqualTo ["HeavyKit"] && {_holdersCreated==0},"bag was lost/spilled or an IV line was charged/invented"] call _check;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [_bagSet],"native projection changed unspiked bag custody"] call _check;
        [str (_patient getVariable "ACM_circulation_IV_Bags")==_initialBagText,"carried bag materialization hung a patient fluid"] call _check;
    ''')


def test_native_transfer_claim_and_return_keep_bag_only_kind_class_and_volume():
    execute(setup() + r'''
        call _issueBag;
        private _tuple=call _bagTuple;
        _receiver setVariable ["cargo",[_tuple]];_uniform setVariable ["cargo",[]];
        [_medic,_receiver,_tuple select 0] call (_classEvents get "Put");
        [_receiver,_uniform,_tuple select 0] call (_classEvents get "Take");call _flush;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo []
            && {(_receiver getVariable "ACME_preparedIVSets") isEqualTo [_bagSet]},"unspiked bag transfer lost or duplicated metadata"] call _check;
        private _receipt=[_receiver,"prepared",_bagID,"return-unspiked"] call ACME_fnc_inventoryLedgerReserve;
        [count _receipt==2 && {(_receiver getVariable "cargo") isEqualTo []},"bag-only carrier could not be reserved by exact native class"] call _check;
        [_receiver,"return-unspiked",{},[]] call ACME_fnc_inventoryLedgerClaim;call _flush;
        [_receiver,"return-unspiked",false] call ACME_fnc_inventoryLedgerSettle;call _flush;
        [(_receiver getVariable "cargo") isEqualTo [_tuple]
            && {(_receiver getVariable "ACME_preparedIVSets") isEqualTo [_bagSet]},"returned bag gained tubing, changed identity or lost remaining volume"] call _check;
        [_receiver,"return-unspiked",false] call ACME_fnc_inventoryLedgerSettle;call _flush;
        [(_receiver getVariable "cargo") isEqualTo [_tuple],"duplicate return minted another bag-only carrier"] call _check;
    ''')


def persistence_setup():
    return setup() + r'''
        private _nativePairs={params ["_o"];([_o] call _cargoDestination) getVariable ["cargo",[]]};
        ACME_fnc_clinicalObjectRef={params ["_mode","_ref"];if (_mode=="decode") then {objNull} else {["patient","session","stable-patient"]}};
    ''' + "\n".join(persistence_source(name) for name in (
        "inventorySnapshotValid", "inventorySnapshot", "inventoryRestore"))


def test_snapshot_and_restart_import_preserve_bag_only_kind_and_native_mass_class():
    execute(persistence_setup() + r'''
        call _issueBag;
        private _old=call _bagTuple;
        private _snapshot=[_medic] call ACME_fnc_inventorySnapshot;
        [count _snapshot==2 && {count (_snapshot select 1)==1},"bag-only native carrier could not be snapshotted"] call _check;
        private _saved=(_snapshot select 1) select 0;
        [(_saved select 2)=="ACME_UnspikedBag_M50" && {(_saved select 3 select 1 select 8)=="bagOnly"}
            && {(_saved select 3 select 1 select 9)==500},"save metadata relabeled the bag as spiked or changed fluid volume"] call _check;
        [([_medic,_snapshot] call ACME_fnc_inventoryRestore),"bag-only save import was refused"] call _check;
        call _flush;
        private _new=call _bagTuple;
        [(_new select 0)=="ACME_UnspikedBag_M50" && {(_new select 1)!=(_old select 1)},"restore reused identity or changed physical mass/class"] call _check;
        private _restored=(_medic getVariable "ACME_preparedIVSets") select 0;
        [(_restored select 8)=="bagOnly" && {(_restored select 9)==500}
            && {(_restored select 1)=="ACM_SalineBag_500"},"restore fabricated tubing or changed the unspiked fluid"] call _check;
        [([_medic,_snapshot] call ACME_fnc_inventoryRestore),"completed bag-only import replay refused"] call _check;call _flush;
        [(call _bagTuple) isEqualTo _new && {count (_uniform getVariable "cargo")==1},"save replay minted a second unspiked bag"] call _check;
    ''')


@pytest.mark.parametrize("kind,expected", [("bagOnly", "IV line required"), ("saline", "IV line fitted"), ("yset", "Y tubing fitted")])
def test_prepared_card_does_not_claim_an_unspiked_fluid_has_tubing(kind, expected):
    source = read("transfusionCardData")
    replacements = {
        "_list lbText _row": '"Saline 500 mL"', "_list lbColor _row": "[1,1,1,1]",
        "_list lbPictureRight _row": '""', "_list lbPicture _row": '"bag.paa"',
        "_list lbData _row": '"bag-only"', "ctrlIDC _list": "86145",
    }
    for before, after in sorted(replacements.items(), key=lambda item: -len(item[0])):
        source = source.replace(before, after)
    source = re.sub(r'getText \(configFile >> "CfgWeapons" >>[^;]+? >> "picture"\)', '"bag.paa"', source)
    execute(setup() + f'_bagSet set [8,"{kind}"];_medic setVariable ["ACME_preparedIVSets",[_bagSet]];' +
            "ACME_fnc_transfusionCardData={" + ui(source) + "};" + r'''
        private _data=[missionNamespace,0] call ACME_fnc_transfusionCardData;
    ''' + f'[(_data select 1)=="{expected}","prepared card falsely advertised installed tubing"] call _check;')
