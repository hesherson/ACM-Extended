"""Execute FiO2 authorization at every edit entry and mutation boundary.

Production ventilator handlers, NRB reserve selection and equipment-sharing
order run in SQF-VM. Engine inventory reads are supplied by fixtures; native
dialog rendering remains an Arma check.
"""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read


def function(name):
    text = read(name)
    if name == "nrbOxygenSource":
        text = text.replace(
            "[uniformContainer _unit, vestContainer _unit, backpackContainer _unit]",
            "([_unit] call ACME_test_containers)",
        ).replace("magazinesAmmoCargo _x", "_x")
    if name == "ventOxygenGate":
        # Native null-object predicate, with namespaces standing in for units.
        text = text.replace(
            '!isNull ([ACE_player, _patient] call ACME_fnc_nrbOxygenSource)',
            '!(([ACE_player, _patient] call ACME_fnc_nrbOxygenSource) isEqualTo objNull)',
        )
    # No native display exists in the VM. All source eligibility, flag clearing
    # and callback routing still run; the dialog takes its no-interface exit.
    text = text.replace("hasInterface", "_testHasInterface")
    text = re.sub(r'playSound "[^"]+";', "", text)
    text = text.replace("disableSerialization;", "")
    adapted = adapt(text)
    if name == "ventOxygenGate":
        # The shared fixture adapts mission HandleDisconnect returns. This is
        # an unrelated native display callback and must retain its closing.
        adapted = adapted.replace('    false\n}] select 1);', '    false\n}];')
    return "ACME_fnc_" + name + "={" + adapted + "};"


def fixture():
    return r'''
        private _testHasInterface = false;
        private _cargoMedic = [];
        private _cargoPatient = [];
        private _kitMedic = 0;
        private _kitPatient = 0;
        private _fieldWrites = [];
        ACME_test_containers = {
            if ((_this select 0) isEqualTo ACE_player) then {_cargoMedic} else {_cargoPatient}
        };
        ACME_fnc_itemCount = {
            if ((_this select 0) isEqualTo ACE_player) then {_kitMedic} else {_kitPatient}
        };
        ace_medical_treatment_fnc_isMedic = {true};
        ACME_fnc_ventPanelListRefresh = {};
        ACME_fnc_ventPanelShowScreen = {uiNamespace setVariable ["ACME_vent_screen", _this select 0];};
        ACME_fnc_ventPanelSetValue = {_fieldWrites pushBack _this;};
        ACME_fnc_ventLogbookAdd = {};
        ACME_fnc_ventFormatIE = {str (_this select 0)};
        uiNamespace setVariable ["ACME_vent_target", _patient];
        uiNamespace setVariable ["ACME_vent_powered", true];
        uiNamespace setVariable ["ACME_vent_flipped", false];
        uiNamespace setVariable ["ACME_vent_screen", "params"];
        uiNamespace setVariable ["ACME_vent_paramsPage", 0];
        uiNamespace setVariable ["ACME_vent_paramsNav", [false,false,false,false,false]];
        uiNamespace setVariable ["ACME_vent_listCount", 5];
        uiNamespace setVariable ["ACME_vent_selIdx", 0];
        uiNamespace setVariable ["ACME_vent_editingParam", -1];
        uiNamespace setVariable ["ACME_vent_editingFio2", false];
        uiNamespace setVariable ["ACME_vent_fio2", 40];
        _patient setVariable ["ACME_vent_fio2", 40];
        missionNamespace setVariable ["ACME_vent_simpleMode", false];
        missionNamespace setVariable ["ace_medical_treatment_allowSharedEquipment", 0];
        missionNamespace setVariable ["ACME_vent_scrollCooldown", 0];
    ''' + "".join(function(name) for name in [
        "treatmentSupplyOrder", "nrbOxygenSource", "ventOxygenGate",
        "ventPanelKnob", "ventPanelListClick", "ventPanelActivateSel",
    ])


@pytest.mark.parametrize("screen,entry", [
    ("params", "[0] call ACME_fnc_ventPanelListClick;"),
    ("o2", "[0] call ACME_fnc_ventPanelListClick;"),
    ("o2", "call ACME_fnc_ventPanelActivateSel;"),
])
def test_no_tank_refuses_each_fio2_edit_entry(screen, entry):
    execute(fixture() + f'uiNamespace setVariable ["ACME_vent_screen", "{screen}"];' + entry + r'''
        [(uiNamespace getVariable ["ACME_vent_editingParam",-1]) == -1,
            "no tank opened PARAMS oxygen editor"] call _check;
        [!(uiNamespace getVariable ["ACME_vent_editingFio2",false]),
            "no tank opened legacy oxygen editor"] call _check;
        [_patient getVariable ["ACME_vent_fio2",0] == 40,
            "denied edit changed stored oxygen setting"] call _check;
    ''')


@pytest.mark.parametrize("screen", ["params", "o2"])
@pytest.mark.parametrize("direction", [-1, 1])
def test_removing_tank_during_edit_refuses_wheel_write_and_preserves_setting(screen, direction):
    execute(fixture() + r'''
        _cargoMedic = [[["ACM_OxygenTank_425", 9]]];
        [0] call ACME_fnc_ventPanelListClick;
        [(uiNamespace getVariable "ACME_vent_editingParam") == 0,
            "usable oxygen did not authorize edit"] call _check;
        _cargoMedic = [];
    ''' + f'''
        uiNamespace setVariable ["ACME_vent_screen", "{screen}"];
        uiNamespace setVariable ["ACME_vent_editingFio2", true];
        [{direction}] call ACME_fnc_ventPanelKnob;
    ''' + r'''
        [_patient getVariable ["ACME_vent_fio2",0] == 40
            && {uiNamespace getVariable ["ACME_vent_fio2",0] == 40},
            "tank loss still allowed a FiO2 write"] call _check;
        [count _fieldWrites == 0, "denied wheel repainted an authorized value"] call _check;
        [(uiNamespace getVariable "ACME_vent_editingParam") == -1
            && {!(uiNamespace getVariable "ACME_vent_editingFio2")},
            "tank loss left stale oxygen editing flags"] call _check;
    ''')


@pytest.mark.parametrize("cargo,allowed", [
    ('[[["ACM_OxygenTank_425", 0]]]', False),
    ('[[["ACM_OxygenTank_425_Empty", 100]]]', False),
    ('[[["ACM_OxygenTank_425", 1]]]', True),
])
def test_only_positive_compatible_portable_reserve_authorizes_fio2(cargo, allowed):
    execute(fixture() + f'''
        _cargoMedic = {cargo};
        [call ACME_fnc_ventOxygenGate isEqualTo {str(allowed).lower()},
            "wrong cylinder reserve eligibility"] call _check;
        [_cargoMedic isEqualTo {cargo}, "setting gate drew oxygen charge"] call _check;
    ''')


@pytest.mark.parametrize("sharing,allowed", [(0, True), (1, True), (2, False), (3, True)])
def test_patient_tank_uses_actual_ace_supply_sharing(sharing, allowed):
    execute(fixture() + f'''
        _cargoPatient = [[["ACM_OxygenTank_425", 12]]];
        missionNamespace setVariable ["ace_medical_treatment_allowSharedEquipment", {sharing}];
        [call ACME_fnc_ventOxygenGate isEqualTo {str(allowed).lower()},
            "FiO2 bypassed actual supply sharing"] call _check;
    ''')


@pytest.mark.parametrize("donor", ["Medic", "Patient"])
def test_efak_tank_counts_after_empty_loose_tank_and_never_draws_charge(donor):
    execute(fixture() + f'''
        private _draws = 0;
        efak_medical_fnc_drawCharge = {{_draws = _draws + 1; 10}};
        _kit{donor} = 1;
        _cargo{donor} = [[["ACM_OxygenTank_425", 0]]];
        [call ACME_fnc_ventOxygenGate, "EFAK source rejected behind empty loose tank"] call _check;
        [_draws == 0 && {{_kit{donor} == 1}}, "FiO2 adjustment consumed packed cylinder"] call _check;
    ''')


@pytest.mark.parametrize("screen", ["params", "o2"])
@pytest.mark.parametrize("initial,direction,want", [(40,1,41),(40,-1,39),(95,1,95),(21,-1,21)])
def test_authorized_wheel_stays_within_sparrow_range(screen, initial, direction, want):
    execute(fixture() + f'''
        _cargoMedic = [[["ACM_OxygenTank_425", 9]]];
        uiNamespace setVariable ["ACME_vent_screen", "{screen}"];
        uiNamespace setVariable ["ACME_vent_editingParam", 0];
        uiNamespace setVariable ["ACME_vent_editingFio2", true];
        uiNamespace setVariable ["ACME_vent_fio2", {initial}];
        _patient setVariable ["ACME_vent_fio2", {initial}];
        [{direction}] call ACME_fnc_ventPanelKnob;
        [_patient getVariable ["ACME_vent_fio2",0] == {want}
            && {{uiNamespace getVariable ["ACME_vent_fio2",0] == {want}}},
            "authorized FiO2 dial changed range or ignored tank"] call _check;
        [_cargoMedic isEqualTo [[["ACM_OxygenTank_425", 9]]],
            "FiO2 writer consumed oxygen"] call _check;
    ''')


@pytest.mark.parametrize("row,key,initial", [
    (1,"ie",2), (2,"peep",5), (3,"psup",10), (4,"trigSensCmH2O",-2),
])
def test_no_oxygen_tank_does_not_gate_other_parameter_edits(row, key, initial):
    execute(fixture() + f'''
        _patient setVariable ["ACME_vent_{key}", {initial}];
        [{row}] call ACME_fnc_ventPanelListClick;
        [(uiNamespace getVariable "ACME_vent_editingParam") == {row},
            "no oxygen tank blocked another parameter's editor"] call _check;
        [1] call ACME_fnc_ventPanelKnob;
        [_patient getVariable ["ACME_vent_{key}",{initial}] != {initial},
            "no oxygen tank blocked another parameter's writer"] call _check;
    ''')


def test_denied_oxygen_attempt_does_not_lock_next_parameter_edit():
    execute(fixture() + r'''
        [0] call ACME_fnc_ventPanelListClick;
        [(uiNamespace getVariable "ACME_vent_editingParam") == -1,
            "denied FiO2 entry left an active edit"] call _check;
        _patient setVariable ["ACME_vent_peep", 5];
        [2] call ACME_fnc_ventPanelListClick;
        [1] call ACME_fnc_ventPanelKnob;
        [_patient getVariable ["ACME_vent_peep",0] == 6,
            "denied FiO2 attempt locked subsequent ventilation adjustment"] call _check;
        uiNamespace setVariable ["ACME_vent_editingParam", 3];
        [!(call ACME_fnc_ventOxygenGate), "no tank accidentally authorized oxygen"] call _check;
        [(uiNamespace getVariable "ACME_vent_editingParam") == 3,
            "oxygen denial cleared unrelated pressure support edit"] call _check;
    ''')


def test_dialog_closes_to_parent_and_has_exact_message_without_patient_writes():
    source = read("ventOxygenGate")
    assert '_parent createDisplay "RscDisplayEmpty"' in source
    assert '_message ctrlSetText "An O2 tank is required.";' in source
    assert '_accept ctrlSetText "OK";' in source
    assert '_accept ctrlAddEventHandler ["ButtonClick"' in source
    assert '_key in [1, 28, 156]' in source
    assert '_prompt displayAddEventHandler ["Unload"' in source
    assert '_parent setVariable ["ACME_vent_oxygenPrompt", displayNull]' in source
    assert 'class ventOxygenGate {};' in (ROOT / 'addons/acm_extended/config.cpp').read_text()
    assert 'closeDialog' not in source
    assert 'useOxygenTankReserve' not in source
    assert not re.search(r'_patient\s+setVariable', source)


def test_every_existing_fio2_writer_has_gate_at_its_branch_boundary():
    source = read("ventPanelKnob")
    param = source[source.index('case 0: {  // o2 ENRICHMENT'):source.index('case 1: {  // the i:e ratio ladder.')]
    legacy = source[source.index('if ((_screen == "o2") &&'):source.index('// the o2 screen when not editing.')]
    for branch in (param, legacy):
        assert branch.index('call ACME_fnc_ventOxygenGate') < branch.index('setVariable ["ACME_vent_fio2"')
        assert 'if !(call ACME_fnc_ventOxygenGate) exitWith {};' in branch
