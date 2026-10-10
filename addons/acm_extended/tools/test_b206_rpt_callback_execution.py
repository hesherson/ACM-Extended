"""Execute the RPT's numeric Eden positions and full ACE HPMK callback arguments.

The production SQF runs with namespace actors and queued CBA events. SQF-VM lacks
finite, so that engine predicate is adapted for the finite fixtures below; the
numeric/string conversion and parameter decoding remain production code.
"""
import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read


MODULES = [
    ("mission", "moduleInitFullHealFacility_Eden", "initFullHealFacility", 2),
    ("evacuation", "moduleCreateEvacuationPoint", "defineEvacuationPoint", 3),
]


@pytest.mark.parametrize("component,name,callee,position_index", MODULES)
@pytest.mark.parametrize("value,expected", [
    ("[0,0,0]", "[0,0,0]"),
    ("[1.25,-3,9]", "[1.25,-3,9]"),
    ('"[1.25, -3, 9]"', "[1.25,-3,9]"),
    ('["1.25",-3,"9"]', "[1.25,-3,9]"),
    ('[[],true,"3"]', "[0,0,3]"),
    ("[]", "[0,0,0]"),
    ("false", "[0,0,0]"),
])
def test_eden_positions_preserve_numbers_and_parse_only_strings(component, name, callee, position_index, value, expected):
    source = (ROOT / "addons" / component / "functions" / f"fnc_{name}.sqf").read_text()
    source = adapt(source, component).replace("finite _component", "true")
    execute(f'''
        private _applied = [];
        ACM_evacuation_enable = true;
        ACM_{component}_fnc_{callee} = {{_applied pushBack _this;}};
        private _inputPosition = {value};
        missionNamespace setVariable ["InteractionPosition", _inputPosition];
        [missionNamespace, [_patient], true] call {{{source}}};
        [count _applied == 1, "module did not register its interaction"] call _check;
        [((_applied select 0) select {position_index}) isEqualTo {expected}, "invalid or changed interaction position"] call _check;
        [(missionNamespace getVariable "InteractionPosition") isEqualTo _inputPosition, "module changed its source attribute"] call _check;
    ''')


def hpmk_setup():
    prep = adapt(read("hpmkPrep").replace("local _patient", "_patientLocal"))
    remove = adapt(read("hpmkRemove").replace("local _patient", "_patientLocal").replace("allPlayers", "[]"))
    return r'''
        private _patientLocal = true;
        private _takeCount = 0;
        private _settled = [];
        private _notices = [];
        private _receipt = [_medic, "ACM_HPMK", objNull, "7:receipt"];
        ACME_fnc_treatmentSupplyTake = {_takeCount = _takeCount + 1; +_receipt};
        ACME_fnc_hpmkStateCommit = {(_this select 0) setVariable ["ACME_hpmk_state", _this select 1];};
        ACME_fnc_netNotice = {_notices pushBack _this;};
        CBA_fnc_ownerEvent = {_settled pushBack _this;};
        _patient setVariable ["ACE_isUnconscious", true];
    ''' + "ACME_fnc_hpmkPrep = {" + prep + "};\nACME_fnc_hpmkRemove = {" + remove + "};\n"


def test_full_ace_prep_callback_debits_once_and_preserves_receipt_during_owner_delivery():
    # ACE medical_treatment/fnc_treatmentSuccess calls the callback with all seven
    # arguments, including bodyPart/classname in slots used by internal HPMK calls.
    execute(hpmk_setup() + r'''
        _patientLocal = false;
        [_medic,_patient,"body","ACME_PrepHPMK",_medic,"",false] call ACME_fnc_hpmkPrep;
        [_takeCount == 1 && {count _events == 1}, "ACE prep failed or spent kit twice"] call _check;
        private _request = _events select 0;
        private _args = _request select 2;
        [(_request select 1) == "hpmkPrep" && {(_args select 2) isEqualTo true}, "owner request lost inventory reservation"] call _check;
        [(_args select 3) isEqualTo _receipt, "owner request lost donor receipt"] call _check;
        _patientLocal = true;
        _args call ACME_fnc_hpmkPrep;
        [_takeCount == 1, "owner repeated inventory debit"] call _check;
        [(_patient getVariable "ACME_hpmk_state") == "prepped", "owner did not commit prep"] call _check;
        [count _settled == 1 && {((_settled select 0) select 1) isEqualTo [_receipt,false]}, "prep did not settle exact donor receipt"] call _check;
    ''')


def test_full_ace_remove_callback_stays_manual_and_returns_one_kit():
    execute(hpmk_setup() + r'''
        _patient setVariable ["ACME_hpmk_state", "wrapped"];
        _patientLocal = false;
        [_medic,_patient,"body","ACME_RemoveHPMK",_medic,"",false] call ACME_fnc_hpmkRemove;
        [count _events == 1, "ACE removal did not reach owner"] call _check;
        private _request = _events select 0;
        private _args = (_request select 1) select 2;
        [(_args select 2) isEqualTo false, "manual removal became automatic"] call _check;
        _patientLocal = true;
        _args call ACME_fnc_hpmkRemove;
        _args call ACME_fnc_hpmkRemove;
        [count _events == 2 && {((_events select 1) select 0) == "ACME_hpmkReturnItem"}, "removal lost or duplicated kit"] call _check;
        [(_patient getVariable "ACME_hpmk_state") == "", "removal left state active"] call _check;
        [!(_patient getVariable "ACME_hpmk_returnPending") && {count _waits == 0}, "manual removal took automatic cleanup path"] call _check;
        [count _notices == 1, "manual removal lost notice"] call _check;
    ''')


def test_internal_automatic_removal_keeps_delayed_return_guard():
    execute(hpmk_setup() + r'''
        _patient setVariable ["ACME_hpmk_state", "wrapped"];
        [_medic,_patient,true] call ACME_fnc_hpmkRemove;
        [count _events == 1 && {(_patient getVariable "ACME_hpmk_returnPending")}, "automatic removal lost return guard"] call _check;
        [count _waits == 1 && {count _notices == 0}, "automatic flag was discarded"] call _check;
        private _wait = _waits select 0;
        (_wait select 1) call (_wait select 0);
        [!(_patient getVariable "ACME_hpmk_returnPending"), "return guard was stranded"] call _check;
    ''')
