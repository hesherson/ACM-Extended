"""Execute the real vial-holder resolver and native UI writer after published batch 3.

Only engine object/control and owner-transport boundaries use the existing VM
stand-ins. Crucially, the native writer executes instead of a mock assuming that
its nested argument shape is correct. No inventory or pharmacokinetic claim.
"""
from pathlib import Path
import pytest
from test_historical_vial_execution import F, setup, function, code
from test_menu_death_lifecycle import execute, adapt


def holder_setup():
    native=(F.parents[1]/'circulation/functions/fnc_setLocalUiState.sqf').read_text()
    return setup()+function('vialHolder')+'private _uiNative={'+adapt(native, 'circulation')+'};'+'''
        private _uiWrites=[];
        ACME_fnc_treatmentSupplyOrder={_this};
        ACM_circulation_fnc_setLocalUiState={_uiWrites pushBack _this; _this call _uiNative};
    '''


@pytest.mark.parametrize('selection',[1,2])
def test_missing_patient_or_vehicle_source_normalizes_the_real_selector(selection):
    execute(holder_setup()+f'private _found=[_medic,{selection}] call ACME_fnc_vialHolder;'+'''
        [_found isEqualTo _medic,"missing source did not fall back to self"] call _check;
        [(missionNamespace getVariable ["ACM_circulation_SyringeDraw_InventorySelection",-1])==0,"native selector not normalized"] call _check;
        [_stockWrites==0 && {_inventoryDebits==0},"fallback consumed inventory"] call _check;
    ''')


def test_reachable_dead_patient_source_waits_for_ack_and_does_not_silently_select_self():
    execute(holder_setup()+'''
        _holderAlive=false;
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_Target",_patient];
        private _found=[_medic,1] call ACME_fnc_vialHolder;
        [_found isEqualTo objNull && {count _uiWrites==0},"pending shared source became self"] call _check;
        private _pending=missionNamespace getVariable "ACME_vialLeasePending";
        [_patient,_pending select 1,true,14,""] call ACME_fnc_vialLeaseResult;
        [([_medic,1] call ACME_fnc_vialHolder) isEqualTo _patient,"acknowledged dead-patient source not usable"] call _check;
        [_stockWrites==0 && {_inventoryDebits==0},"source resolution consumed inventory"] call _check;
    ''')


def test_unreachable_source_releases_its_old_lease_and_normalizes_the_selector():
    execute(holder_setup()+'''
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_Target",_patient];
        missionNamespace setVariable ["ACME_vialLeaseAccepted",[_patient,"old",20]];
        _distance=6;
        [([_medic,1] call ACME_fnc_vialHolder) isEqualTo _medic,"unreachable source retained"] call _check;
        [count _events==1 && {(((_events select 0) select 2) select 1)=="release"},"fallback stranded old lease"] call _check;
        [(missionNamespace getVariable ["ACME_vialLeaseAccepted",[]]) isEqualTo [],"fallback retained acknowledgement"] call _check;
        [(missionNamespace getVariable ["ACM_circulation_SyringeDraw_InventorySelection",-1])==0,"unreachable selector not normalized"] call _check;
    ''')
