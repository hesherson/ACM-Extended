"""Execute B156 supply policy and reservation settlement with simulated engine inventory.

The actual SQF helpers run in SQF-VM. Engine inventory/locality commands and ACE's
external useItem dependency are adapters; live network latency still needs Arma.
"""
import os
import re
from pathlib import Path
import shutil
import subprocess

import pytest

FUNCTIONS = Path(__file__).resolve().parents[1] / "functions"


def execute(scenario):
    vm = os.environ.get("SQFVM") or shutil.which("sqfvm")
    if not vm:
        pytest.skip("SQF-VM is required for supply execution checks")
    definitions = []
    for name in ["treatmentSupplyOrder", "treatmentSupplyCount", "treatmentSupplyTake", "treatmentSupplyRefund", "treatmentSupplyTakeMany"]:
        source = (FUNCTIONS / f"fn_{name}.sqf").read_text()
        for unit in ["_medic", "_patient", "_donor", "_vehicle", "_x"]:
            source = source.replace(f"isNull {unit}", f'({unit} isEqualTo "")')
        source = source.replace("local _medic", "true")
        source = source.replace("_medic removeItem _x", "[_medic, _x] call _remove")
        source = source.replace("objectParent _x", '(_parents getOrDefault [_x, ""])')
        source = source.replace("itemCargo _vehicle", "(_cargo getOrDefault [_vehicle, []])")
        source = source.replace("clientOwner", "42").replace("objNull", '""')
        source = source.replace('_vehicle addItemCargoGlobal [_item, 1]', '[_vehicle, _item] call _addCargo')
        definitions.append(f"ACME_fnc_{name} = {{{source}}};")
    code = r'''
        private _ok = true;
        private _parents = createHashMap;
        private _cargo = createHashMap;
        private _inventory = createHashMapFromArray [["medic", ["seal"]], ["patient", ["seal"]]];
        private _isMedic = false;
        private _nativeCalls = 0;
        private _check = {if !(_this select 0) then {_ok = false; diag_log ("SUPPLY_FAIL " + (_this select 1));};};
        private _remove = {params ["_unit", "_item"]; private _row = +(_inventory getOrDefault [_unit, []]); private _i = _row find _item; if (_i >= 0) then {_row deleteAt _i; _inventory set [_unit, _row];};};
        private _addCargo = {params ["_unit", "_item"]; private _row = +(_cargo getOrDefault [_unit, []]); _row pushBack _item; _cargo set [_unit, _row];};
        ace_medical_treatment_fnc_isMedic = {_isMedic};
        ace_common_fnc_getCountOfItem = {params ["_unit", "_item"]; {_x == _item} count (_inventory getOrDefault [_unit, []])};
        ace_common_fnc_addToInventory = {params ["_unit", "_item"]; private _row = +(_inventory getOrDefault [_unit, []]); _row pushBack _item; _inventory set [_unit, _row];};
        ace_medical_treatment_fnc_useItem = {
            params ["_medic", "_patient", "_items"];
            _nativeCalls = _nativeCalls + 1;
            private _result = ["", "", false];
            {
                private _unit = _x;
                private _vehicle = _parents getOrDefault [_unit, ""];
                {
                    private _item = _x;
                    private _row = +(_cargo getOrDefault [_vehicle, []]);
                    private _index = _row find _item;
                    if (_index >= 0) exitWith {_row deleteAt _index; _cargo set [_vehicle, _row]; _result = [_unit, _item, false];};
                    _row = +(_inventory getOrDefault [_unit, []]);
                    _index = _row find _item;
                    if (_index >= 0) exitWith {_row deleteAt _index; _inventory set [_unit, _row]; _result = [_unit, _item, true];};
                } forEach _items;
                if ((_result select 1) != "") exitWith {};
            } forEach ([_medic, _patient] call ACME_fnc_treatmentSupplyOrder);
            _result
        };
    ''' + "\n".join(definitions) + "\n" + scenario + r'''
        diag_log (if (_ok) then {"SUPPLY_OK"} else {"SUPPLY_FAIL"});
    '''
    # The supplied VM lacks getOrDefault; use its implemented map get/isNil operations.
    code = re.sub(r'(\w+) getOrDefault \[([^,]+), (\[\]|""|0|false|true)\]', r'([\1, \2, \3] call _getDefault)', code)
    code = 'private _getDefault = {params ["_map", "_key", "_default"]; private _value = _map get _key; if (isNil "_value") exitWith {_default}; _value;};' + code
    result = subprocess.run([vm, "--automated", "--suppress-welcome", "--no-execute-print", "--no-work-print", "--sqf", code], capture_output=True, text=True, timeout=20)
    output = result.stdout + result.stderr
    assert result.returncode == 0 and "[ERR]" not in output, output
    assert "SUPPLY_OK" in output and "SUPPLY_FAIL" not in output, output


@pytest.mark.parametrize("mode,is_medic,expected", [(0, False, "patient"), (1, False, "medic"), (2, False, "medic"), (3, False, "patient"), (3, True, "medic")])
def test_native_ace_priority_and_exact_donor_refund(mode, is_medic, expected):
    execute(f'''
        ace_medical_treatment_allowSharedEquipment = {mode};
        _isMedic = {str(is_medic).lower()};
        private _receipt = ["medic", "patient", ["seal"]] call ACME_fnc_treatmentSupplyTake;
        [(_receipt select 0) == "{expected}" && {{_nativeCalls == 1}}, "wrong donor/native debit"] call _check;
        private _copy = +_receipt;
        [_receipt] call ACME_fnc_treatmentSupplyRefund;
        [_copy] call ACME_fnc_treatmentSupplyRefund;
        [(["medic", "seal"] call ace_common_fnc_getCountOfItem) == 1 && {{(["patient", "seal"] call ace_common_fnc_getCountOfItem) == 1}}, "duplicate refund or wrong inventory"] call _check;
    ''')


def test_patient_only_available_and_no_sharing_rejects_without_debit():
    execute('''
        _inventory set ["medic", []];
        ace_medical_treatment_allowSharedEquipment = 2;
        [(["medic", "patient", "seal"] call ACME_fnc_treatmentSupplyCount) == 0, "forbidden patient count"] call _check;
        [(["medic", "patient", ["seal"]] call ACME_fnc_treatmentSupplyTake) isEqualTo [], "forbidden patient debit"] call _check;
        ace_medical_treatment_allowSharedEquipment = 0;
        [(["medic", "patient", "seal"] call ACME_fnc_treatmentSupplyCount) == 1, "patient stock unavailable"] call _check;
        private _receipt = ["medic", "patient", ["seal"]] call ACME_fnc_treatmentSupplyTake;
        [(_receipt select 0) == "patient", "patient stock not debited"] call _check;
        [(["medic", "patient", ["seal"]] call ACME_fnc_treatmentSupplyTake) isEqualTo [], "last item spent twice"] call _check;
        [_receipt, false] call ACME_fnc_treatmentSupplyRefund;
        [_receipt] call ACME_fnc_treatmentSupplyRefund;
        [(["patient", "seal"] call ace_common_fnc_getCountOfItem) == 0, "committed item resurrected"] call _check;
    ''')


def test_vehicle_donor_is_captured_and_shared_vehicle_counted_once():
    execute('''
        ace_medical_treatment_allowSharedEquipment = 0;
        _parents set ["medic", "vehicleA"]; _parents set ["patient", "vehicleA"];
        _cargo set ["vehicleA", ["seal"]];
        [(["medic", "patient", "seal"] call ACME_fnc_treatmentSupplyCount) == 3, "vehicle counted twice"] call _check;
        [(["medic", "medic", "seal"] call ACME_fnc_treatmentSupplyCount) == 2, "self counted twice"] call _check;
        private _receipt = ["medic", "patient", ["seal"]] call ACME_fnc_treatmentSupplyTake;
        [(_receipt select 2) == "vehicleA", "vehicle lost from receipt"] call _check;
        _parents set ["patient", "vehicleB"];
        [_receipt] call ACME_fnc_treatmentSupplyRefund;
        [count (_cargo get "vehicleA") == 1 && {count (_cargo getOrDefault ["vehicleB", []]) == 0}, "refund followed dismount/new vehicle"] call _check;
        [(["patient", "seal"] call ace_common_fnc_getCountOfItem) == 1, "vehicle refund went to patient"] call _check;
    ''')


def test_multi_component_late_failure_rolls_back_all_exact_donors():
    execute('''
        ace_medical_treatment_allowSharedEquipment = 0;
        _inventory set ["patient", ["blood"]];
        _inventory set ["medic", ["line"]];
        private _receipts = ["medic", "patient", ["line", "blood", "saline"]] call ACME_fnc_treatmentSupplyTakeMany;
        [_receipts isEqualTo [], "incomplete set succeeded"] call _check;
        [(_inventory get "patient") isEqualTo ["blood"] && {(_inventory get "medic") isEqualTo ["line"]}, "partial set lost/moved donor items"] call _check;
        _inventory set ["patient", ["blood", "saline"]];
        _receipts = ["medic", "patient", ["line", "blood", "saline"]] call ACME_fnc_treatmentSupplyTakeMany;
        [count _receipts == 3 && {count (_inventory get "patient") == 0} && {count (_inventory get "medic") == 0}, "complete set failed"] call _check;
        {[_x, false] call ACME_fnc_treatmentSupplyRefund;} forEach _receipts;
        {[_x] call ACME_fnc_treatmentSupplyRefund;} forEach _receipts;
        [count (_inventory get "patient") == 0 && {count (_inventory get "medic") == 0}, "committed set duplicated"] call _check;
    ''')


def test_materialized_used_or_cooled_bag_keeps_personal_provenance():
    execute('''
        ace_medical_treatment_allowSharedEquipment = 0;
        _inventory set ["patient", ["blood"]];
        _inventory set ["medic", ["blood"]];
        _parents set ["medic", "vehicleA"];
        _cargo set ["vehicleA", ["blood"]];
        private _receipt = ["medic", "patient", ["blood"], true] call ACME_fnc_treatmentSupplyTake;
        [(_receipt select 0) == "medic" && {(_receipt select 2) == ""} && {_nativeCalls == 0}, "materialized source was substituted"] call _check;
        [count (_inventory get "patient") == 1 && {count (_cargo get "vehicleA") == 1}, "other blood was consumed"] call _check;
        [_receipt] call ACME_fnc_treatmentSupplyRefund;
        [count (_inventory get "medic") == 1 && {count (_cargo get "vehicleA") == 1}, "materialized refund went to vehicle"] call _check;
    ''')


def test_hpmk_owner_rejection_refunds_patient_and_acceptance_commits_once():
    source = (FUNCTIONS / "fn_hpmkPrep.sqf").read_text()
    for unit in ["_medic", "_patient"]:
        source = source.replace(f"isNull {unit}", f'({unit} isEqualTo "")')
    source = source.replace("local _patient", "_patientLocal").replace("objNull", '""')
    source = source.replace('_patient getVariable ["ACM_core_Lying_State", false]', "true")
    source = source.replace('_patient getVariable ["ACE_isUnconscious", false]', "true")
    source = source.replace('_patient getVariable ["ACME_hpmk_state", ""]', "_hpmkState")
    source = source.replace('_patient setVariable ["ACME_hpmk_provider", _medic, true];', "_hpmkProvider = _medic;")
    source = source.replace('_patient setVariable ["ACME_hpmk_returnPending", false, true];', "")
    execute('''
        private _patientLocal = true;
        private _hpmkState = "";
        private _hpmkProvider = "";
        private _queued = [];
        private _settlements = [];
        ACME_fnc_netNotice = {};
        ACME_fnc_hpmkStateCommit = {_hpmkState = _this select 1;};
        ACME_fnc_ownerDispatch = {_queued pushBack (_this select 2);};
        CBA_fnc_ownerEvent = {
            params ["_event", "_args", "_target"];
            if (_event == "ACME_supplySettle") then {
                _settlements pushBack [_target, _args select 1];
                _args call ACME_fnc_treatmentSupplyRefund;
            };
        };
        ACME_fnc_hpmkPrep = {''' + source + '''};
        ace_medical_treatment_allowSharedEquipment = 0;
        _inventory set ["patient", ["ACM_HPMK", "ACM_HPMK"]];
        _inventory set ["medic", []]; _inventory set ["second", []];
        _patientLocal = false;
        ["medic", "patient"] call ACME_fnc_hpmkPrep;
        ["second", "patient"] call ACME_fnc_hpmkPrep;
        [count _queued == 2 && {count (_inventory get "patient") == 0}, "requests did not reserve patient kits"] call _check;
        _patientLocal = true;
        (_queued select 0) call ACME_fnc_hpmkPrep;
        (_queued select 1) call ACME_fnc_hpmkPrep;
        [count (_inventory get "patient") == 1 && {count (_inventory get "medic") == 0} && {count (_inventory get "second") == 0}, "loser kit moved/lost/duplicated"] call _check;
        [_hpmkState == "prepped" && {_hpmkProvider == "medic"}, "loser overwrote winner"] call _check;
        [_settlements isEqualTo [[42, false], [42, true]], "incorrect owner receipt settlement"] call _check;
        (_queued select 1) call ACME_fnc_hpmkPrep;
        [count (_inventory get "patient") == 1, "duplicate rejection refunded twice"] call _check;
    ''')


def test_deleted_ai_vent_donor_falls_back_to_original_operator_at_last_position():
    source = (FUNCTIONS / "fn_ventCustodyTick.sqf").read_text()
    source = 'if (_phase == "attached" && {_gone}) then {' + source.split('if (_phase == "attached" && {_gone}) then {', 1)[1].split('    if (_phase == "finalizing")', 1)[0]
    for unit in ["_patient", "_supplier", "_found"]:
        source = source.replace(f"isNull {unit}", f'({unit} isEqualTo "")')
    source = source.replace("alive _supplier", "true").replace("alive _x", "true")
    source = source.replace("getPlayerUID _supplier", '""').replace("getPlayerUID _x", '""')
    source = source.replace("allPlayers", '["operator"]').replace("objNull", '""')
    execute('''
        private _now = 10; private _phase = "attached"; private _gone = true;
        private _patient = ""; private _id = "vent:1";
        private _r = createHashMapFromArray [["supplier", ""], ["supplierUID", ""],
            ["recoveryOperator", "operator"], ["recoveryOperatorUID", ""], ["phase", "attached"],
            ["lastPos", [1,2,3]], ["lastVehicle", ""]];
        ACME_fnc_ventRecoveryNear = {(_this select 0) == "operator" && {(_this select 2) isEqualTo [1,2,3]}};
        CBA_fnc_targetEvent = {};
    ''' + source + '''
        [(_r get "phase") == "returning" && {(_r get "recipient") == "operator"}, "deleted AI donor stranded device"] call _check;
    ''')


@pytest.mark.parametrize("accepted", [True, False])
def test_battery_exchange_ack_returns_item_and_charge_to_exact_donor_once(accepted):
    source = (FUNCTIONS / "fn_ownerInit.sqf").read_text().split('["ACME_ventBatteryExchangeResult", {', 1)[1].split('}] call CBA_fnc_addEventHandler;', 1)[0]
    source = source.replace("hasInterface", "true").replace("isNull ACE_player", '(ACE_player isEqualTo "")')
    source = source.replace("isNull _source", '(_source isEqualTo "")').replace("isNull (_supply select 2)", '((_supply select 2) isEqualTo "")')
    source = source.replace('_source setVariable ["ACME_vent_spareBattery", _returnedPct, true]', '_charges set [_source, _returnedPct]')
    source = source.replace("objNull", '""').replace("displayNull", '""').replace("isNull _dlg", '(_dlg isEqualTo "")')
    execute('''
        ACE_player = "medic";
        private _charges = createHashMapFromArray [["patient", 98], ["medic", 17]];
        ace_medical_treatment_allowSharedEquipment = 0;
        _inventory set ["patient", ["ACME_VentBattery"]]; _inventory set ["medic", []];
        private _supply = ["medic", "patient", ["ACME_VentBattery"]] call ACME_fnc_treatmentSupplyTake;
        uiNamespace setVariable ["ACME_vent_batterySwapRequest", "exchange:1"];
        uiNamespace setVariable ["ACME_vent_batterySwapSupply", _supply];
        private _ack = {''' + source + '''};
    ''' + f'''
        ["patient", "exchange:1", {str(accepted).lower()}, 42, 98] call _ack;
        ["patient", "exchange:1", {str(accepted).lower()}, 42, 98] call _ack;
        [(_charges get "patient") == {42 if accepted else 98} && {{(_charges get "medic") == 17}}, "charge moved to provider or changed on rejection"] call _check;
        [count (_inventory get "patient") == 1 && {{count (_inventory get "medic") == 0}}, "battery donor changed/duplicated"] call _check;
    ''')


def test_battery_panel_close_refunds_only_unsubmitted_reservation():
    source = (FUNCTIONS / "fn_ventPanelClose.sqf").read_text()
    source = 'private _batterySupply =' + source.split('private _batterySupply =', 1)[1].split('if (!isNull _serviceParent)', 1)[0]
    execute('''
        ace_medical_treatment_allowSharedEquipment = 0;
        _inventory set ["patient", ["ACME_VentBattery"]]; _inventory set ["medic", []];
        private _supply = ["medic", "patient", ["ACME_VentBattery"]] call ACME_fnc_treatmentSupplyTake;
        uiNamespace setVariable ["ACME_vent_batterySupply", _supply];
        private _close = {''' + source + '''};
        call _close; call _close;
        [count (_inventory get "patient") == 1 && {count (_inventory get "medic") == 0}, "cancel duplicated or moved battery"] call _check;
        _supply = ["medic", "patient", ["ACME_VentBattery"]] call ACME_fnc_treatmentSupplyTake;
        uiNamespace setVariable ["ACME_vent_batterySwapSupply", _supply];
        uiNamespace setVariable ["ACME_vent_batterySwapRequest", "submitted"];
        call _close;
        [count (_inventory get "patient") == 0, "closing refunded an unacknowledged completed exchange"] call _check;
    ''')


def test_nrb_cylinder_selection_follows_supply_order_and_actual_reserve():
    source = (FUNCTIONS / "fn_nrbOxygenSource.sqf").read_text().replace("objNull", '""')
    source = source.replace("magazinesAmmoCargo _x", '(_bottles getOrDefault [_x, []])')
    for container in ["uniform", "vest", "backpack"]:
        source = source.replace(f"{container}Container _unit", f'(_unit + ":{container}")')
    execute('''
        private _bottles = createHashMapFromArray [["patient:backpack", [["ACM_OxygenTank_425", 5]]],
            ["medic:uniform", [["ACM_OxygenTank_425", 0]]]];
        ACME_fnc_nrbOxygenSource = {''' + source + '''};
        ace_medical_treatment_allowSharedEquipment = 0;
        [(["medic", "patient"] call ACME_fnc_nrbOxygenSource) == "patient", "patient cylinder unavailable"] call _check;
        ace_medical_treatment_allowSharedEquipment = 2;
        [(["medic", "patient"] call ACME_fnc_nrbOxygenSource) == "", "forbidden sharing or empty cylinder accepted"] call _check;
        _bottles set ["medic:uniform", [["ACM_OxygenTank_425", 8]]];
        ace_medical_treatment_allowSharedEquipment = 3; _isMedic = true;
        [(["medic", "patient"] call ACME_fnc_nrbOxygenSource) == "medic", "medic conditional priority lost"] call _check;
    ''')
