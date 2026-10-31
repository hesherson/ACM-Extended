"""B267 before/after cases execute existing carrier functions, not new helpers."""
import pytest
from test_menu_death_lifecycle import execute, adapt, ROOT
import test_b218_carrier_inventory as cargo
import test_chestseal_preparation_progress as prep
import test_historical_chest_workspace as workspace


def test_old_snapshot_does_not_settle_a_new_carrier_container():
    execute(cargo.setup()+cargo.remove()+r'''
        // New live contents are authoritative, but an old callback still has
        // the earlier same-class vest snapshot. It does not own this record.
        _patient setVariable [_savedVar,["Vest_A",[["new",2]]]];
        _cargo setVariable ["items",["current"]];
        [!([_patient,_saved,_savedVar] call ACME_fnc_carrierInventoryRestore),"stale snapshot consumed new carrier custody"] call _check;
        [_wornVest=="" && {!isNull _cargo},"stale restore rewore/deleted current custody"] call _check;
    ''')


def test_delayed_no_animation_removal_cannot_strip_new_kit():
    execute(prep.setup()+prep.function('chestAccessVestAcquire')+r'''
        _vest="OldVest"; _loadout set [4,["OldVest",[]]];
        _blocked=true;
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_Suspended",true];
        _patient setVariable ["ACME_headElev_suspendReadyAt",11];
        [_patient,objNull,"access",true] call ACME_fnc_chestAccessVestAcquire;
        [count _waits==1,"fixture failed to queue no-animation removal"] call _check;
        private _old=call _take;
        _patient setVariable ["ACME_equipmentKitEpoch",1];
        _vest="NewVest"; _loadout set [4,["NewVest",[["fresh",2]]]];
        [_old] call _deliver;
        [count _commits==0 && {_vest=="NewVest"},"old pending removal stripped new kit"] call _check;
    ''')


def test_delayed_empty_chest_readiness_does_not_ack_new_kit():
    execute(prep.setup()+prep.function('chestAccessVestAcquire')+r'''
        _vest=""; _loadout set [4,[]];
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_Suspended",true];
        _patient setVariable ["ACME_headElev_suspendReadyAt",11];
        [_patient,objNull,"access",true] call ACME_fnc_chestAccessVestAcquire;
        [count _waits==1,"fixture failed to queue bare-chest readiness"] call _check;
        private _old=call _take;
        _patient setVariable ["ACME_equipmentKitEpoch",1];
        _patient setVariable ["ACME_chestAccess_readyServer",-1];
        CBA_missionTime=12;
        // Deliver the captured success callback as the real scheduler does;
        // it must recheck ownership even if condition evaluation came earlier.
        (_old select 2) call (_old select 1);
        [(_patient getVariable ["ACME_chestAccess_readyServer",0])==-1,"old no-vest callback falsely prepared new carrier"] call _check;
    ''')


def test_restore_after_denied_roll_stays_bound_to_original_kit():
    execute(workspace.setup()+r'''
        _patient setVariable ["ACME_chestAccess_vestLoadout",["Vest_A",[["old",1]]]];
        [_patient,false,_medic,"access",false] call ACME_fnc_chestAccessVestRestore;
        [count _waits==1,"fixture did not defer denied-roll return"] call _check;
        private _old=_waits select 0; _waits=[];
        _patient setVariable ["ACME_equipmentKitEpoch",1];
        _vest=""; // Intentionally empty replacement kit must stay empty.
        [_old] call _deliver;
        [_vest=="" && {count _loadouts==0},"old denied-roll return outfitted replacement kit"] call _check;
    ''')

@pytest.mark.parametrize('operation',['manualPlateCarrier','chestSealPatientBegin'])
def test_late_owner_packet_does_not_acquire_current_equipment(operation):
    s=(ROOT/'addons/acm_extended/functions/fn_ownerDispatch.sqf').read_text().split('switch (_operation) do {',1)[0]+'_admitted=_admitted+1;'
    s=s.replace('local _patient','_isLocal')
    execute('ACME_fnc_ownerDispatch={'+adapt(s)+'};'+r'''
        private _isLocal=false; private _admitted=0;
        _patient setVariable ["ACME_equipmentKitEpoch",0];
    '''+f'[_patient,"{operation}",[]] call ACME_fnc_ownerDispatch;'+r'''
        private _packet=(_events select 0) select 1;
        _patient setVariable ["ACME_equipmentKitEpoch",1]; _isLocal=true;
        _packet call ACME_fnc_ownerDispatch;
        [_admitted==0,"packet from previous kit acquired new equipment"] call _check;
    ''')
