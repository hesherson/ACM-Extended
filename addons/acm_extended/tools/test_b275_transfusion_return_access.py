"""Run the native opener's selection decisions before its first UI boundary.

SQF-VM executes the checked-out opener prefix and live piggyback picker helper.
Dialog creation, access presence, inventory drawing and owner transport are
explicit engine boundaries; this does not certify native rendering.
"""
import pytest

from test_b156_procedure_supplies import primitives
from test_b273_transfusion_actions import gui
from test_historical_core_boundaries import block_at
from test_menu_death_lifecycle import ROOT, adapt, execute, read


OPEN = ROOT / "addons/circulation/functions/fnc_openTransfusionMenu.sqf"


def opener_prefix(restore=True):
    source = OPEN.read_text().split("createDialog QGVAR(TransfusionMenu_Dialog);", 1)[0]
    if not restore:
        # Negative control preserves the real fallback selection while removing
        # only the new exact-route handoff, reproducing restoration after paint.
        start = source.index("if (count _returnAccess == 2)")
        opening = source.index("{", start)
        body = block_at(source, opening)
        end = opening + len(body)
        source = source[:start] + source[end:]
    source = source.replace("IDC_TRANSFUSIONMENU", "86000")
    source = source.replace("isNull findDisplay 86000", "true")
    source = source.replace("CBA_FUNC(getKeybind)", "CBA_fnc_getKeybind")
    source = source.replace("ALL_BODY_PARTS", '["head","body","leftarm","rightarm","leftleg","rightleg"]')
    return adapt(source, "circulation")


def setup(restore=True):
    return r'''
        private _displayFixture=missionNamespace;
        private _inventoryPaints=[];
        private _recoverCalls=[];
        private _liveEpoch=7;
        CBA_fnc_getKeybind={private _binding=[];_binding set [5,[[44]]];_binding};
        ACME_fnc_piggybackRecover={_recoverCalls pushBack ["pib",_this select 0];};
        ACME_fnc_lineWarmerRecover={_recoverCalls pushBack ["warmer",_this select 0];};
        ACM_circulation_fnc_hasIV={params ["_unit","_part","_minimum",["_site",-1]];
            [_part,_site] in _ivPresent
        };
        ACM_circulation_fnc_hasIO={params ["_unit","_part"];_part in _ioPresent};
        ACME_fnc_clinicalEpoch={_liveEpoch};
        ACME_fnc_piggybackEligible={true};
        ACME_fnc_piggybackWorkflow={params ["_operation"];
            if (_operation=="cancel") then {missionNamespace setVariable ["ACME_piggybackPending",[]];};
        };
        ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory={
            _inventoryPaints pushBack [ACM_circulation_TransfusionMenu_Target,
                ACM_circulation_TransfusionMenu_Selected_BodyPart,
                ACM_circulation_TransfusionMenu_SelectIV,
                ACM_circulation_TransfusionMenu_Selected_AccessSite];
        };
        uiNamespace setVariable ["ACME_preparedListMode",true];
        missionNamespace setVariable ["ACME_yPending",""];
        missionNamespace setVariable ["ACME_yPendingSaline",""];
        _displayFixture setVariable ["ACME_txPickerSignature",""];
    ''' + "private _openBeforeUi={" + opener_prefix(restore) + "};" + \
        "ACME_fnc_transfusionFilterInventory={" + primitives(gui(read("transfusionFilterInventory"))) + "};"


@pytest.mark.parametrize("part,iv,site", [
    ("leftarm", True, 1), ("leftarm", True, 2),
    ("rightarm", True, 2), ("head", True, 1),
    ("leftarm", False, 0), ("rightleg", False, 0),
])
def test_exact_return_is_selected_before_first_picker_and_preserves_preparation_intent(part, iv, site):
    execute(setup() + f'''
        private _ivPresent=[["{part}",0],["{part}",{site}]];
        private _ioPresent=["{part}"];
        private _intent=[_patient,"{part}",{str(iv).lower()},{site},"primary",7];
        missionNamespace setVariable ["ACME_piggybackPending",_intent];
        [_medic,_patient,"{part}",[{str(iv).lower()},{site}]] call _openBeforeUi;
        call ACME_fnc_transfusionFilterInventory;
        [_inventoryPaints isEqualTo [[_patient,"{part}",{str(iv).lower()},{site}]],"first picker painted a fallback access"] call _check;
        [(missionNamespace getVariable "ACME_piggybackPending") isEqualTo _intent,"valid prepared piggyback intent was cancelled before restoring access"] call _check;
        [count _recoverCalls==2,"exact-route return abandoned outstanding owner transactions"] call _check;
    ''')


def test_old_first_site_selection_reproduces_prep_intent_loss_before_late_restore():
    execute(setup(False) + r'''
        private _ivPresent=[["leftarm",0],["leftarm",2]];
        private _ioPresent=[];
        private _intent=[_patient,"leftarm",true,2,"primary",7];
        missionNamespace setVariable ["ACME_piggybackPending",_intent];
        [_medic,_patient,"leftarm",[true,2]] call _openBeforeUi;
        call ACME_fnc_transfusionFilterInventory;
        [ACM_circulation_TransfusionMenu_Selected_AccessSite==0,"negative control did not select first site"] call _check;
        [(missionNamespace getVariable "ACME_piggybackPending") isEqualTo [],"negative control did not reproduce prematurely cancelled intent"] call _check;
        ACM_circulation_TransfusionMenu_Selected_AccessSite=2;
        call ACME_fnc_transfusionFilterInventory;
        [(missionNamespace getVariable "ACME_piggybackPending") isEqualTo [],"late restore should not recreate a cancelled intent"] call _check;
    ''')


def test_missing_return_access_uses_real_fallback_and_cancels_stale_intent():
    execute(setup() + r'''
        private _ivPresent=[["leftarm",0]];
        private _ioPresent=[];
        private _intent=[_patient,"leftarm",true,2,"primary",7];
        missionNamespace setVariable ["ACME_piggybackPending",_intent];
        [_medic,_patient,"leftarm",[true,2]] call _openBeforeUi;
        call ACME_fnc_transfusionFilterInventory;
        [ACM_circulation_TransfusionMenu_Selected_AccessSite==0,"missing exact site was invented"] call _check;
        [(missionNamespace getVariable "ACME_piggybackPending") isEqualTo [],"removed exact site kept old piggyback intent"] call _check;
    ''')


@pytest.mark.parametrize("iv,site", [(True,2),(False,0)])
def test_delayed_reopen_passes_exact_route_into_the_first_native_selection(iv, site):
    reopen = read("reopenTransfusion").replace("findDisplay 84000","objNull").replace("findDisplay 86200","objNull")
    execute(setup() + "private _reopen={" + adapt(reopen) + "};" + f'''
        private _ivPresent=[["rightarm",0],["rightarm",2]];
        private _ioPresent=["rightarm"];
        private _openArguments=[];
        ACM_circulation_fnc_openTransfusionMenu={{
            _openArguments=+_this;
            _this call _openBeforeUi;
            call ACME_fnc_transfusionFilterInventory;
        }};
        private _intent=[_patient,"rightarm",{str(iv).lower()},{site},"primary",7];
        missionNamespace setVariable ["ACME_piggybackPending",_intent];
        [[_medic,_patient,"rightarm",{str(iv).lower()},{site}]] call _reopen;
        [count _waits==1,"reopen was not scheduled once after source-dialog unload"] call _check;
        (_waits select 0 select 1) call (_waits select 0 select 0);
        [_openArguments isEqualTo [_medic,_patient,"rightarm",[{str(iv).lower()},{site}]],"reopen dropped exact route from the native opener call"] call _check;
        [_inventoryPaints isEqualTo [[_patient,"rightarm",{str(iv).lower()},{site}]],"delayed reopen painted a different route"] call _check;
        [(missionNamespace getVariable "ACME_piggybackPending") isEqualTo _intent,"delayed reopen lost a valid preparation intent"] call _check;
    ''')
