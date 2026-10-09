"""Execute ACCESS packet order, duplicate admission and bounded cancellation.

Production event/retirement/acquire decisions and delayed callbacks execute;
native gear/props, UI, transport and callback delivery are explicit adapters.
Public-variable records are checked, but atomic delivery/real replication are
not emulated. Tombstones expire after 180s or FIFO eviction at 64 records.

ACME_B269_BASELINE=<B268 commit> loads the pre-change event/integration sources
through Git. The new retirement helper remains compiled in the fixture but is
unused by those old callers; this is a controlled source comparison, not an
execution of every subsystem at that commit.
"""
import os
import subprocess
from unittest.mock import patch

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute
import test_b268_delayed_carrier_access as access
import test_b267_carrier_kit_boundary as kit
import test_historical_chest_workspace as workspace


def source(name):
    core = name in ('carrierKitChanged', 'carrierRetireToWorld', 'carrierLegacySnapshot')
    path = (f'addons/core/functions/fnc_{name}.sqf' if core
            else f'addons/acm_extended/functions/fn_{name}.sqf')
    revision = os.environ.get('ACME_B269_BASELINE')
    if revision and name != 'chestAccessLeaseRetire':
        text = subprocess.check_output(['git', 'show', f'{revision}:{path}'], cwd=ROOT, text=True)
    else:
        text = (ROOT / path).read_text()
    return text.split('#include "..\\script_component.hpp"', 1)[-1] if core else text


def function(name):
    with patch.object(access, 'source', source):
        return access.function(name)


def setup():
    with patch.object(access, 'source', source):
        text = access.setup()
    return text + function('chestAccessLeaseRetire') + r'''
        private _acquireRequests=[];
        private _productionAcquire=ACME_fnc_chestAccessVestAcquire;
        ACME_fnc_chestAccessVestAcquire={
            _acquireRequests pushBack (+_this); _this call _productionAcquire
        };
        private _closed={
            params ["_id"];
            ((_patient getVariable ["ACME_chestAccess_closedLeases",[]]) findIf {
                (_x select 0)==_id && {(_x select 1)>_serverClock}
            })>=0
        };
    '''


@pytest.mark.parametrize('worn', [False, True])
@pytest.mark.parametrize('classname', ['cpr', 'checkbreathing', 'thoracostomy'])
def test_stop_before_start_never_removes_or_publishes_readiness(worn, classname):
    execute(setup() + f'_vest="{("Vest_A" if worn else "")}";' + r'''
        _blocked=true;
        _patient setVariable ["ACME_chestAccess_readyServer",333];
    ''' + f'''
        [_patient,_medic,"canceled",false,"{classname}"] call ACME_fnc_chestAccessVestEvent;
        [_patient,_medic,"canceled",true,"{classname}"] call ACME_fnc_chestAccessVestEvent;
    ''' + r'''
        [["canceled"] call _closed,"stop-before-start did not remember canceled episode"] call _check;
        [count _acquireRequests==0 && {count _waits==0} && {count _commits==0},"late canceled start began preparation"] call _check;
        [(_patient getVariable ["ACME_chestAccess_readyServer",0])==333,"late canceled start replaced readiness"] call _check;
        [(count (_patient getVariable ["ACME_chestAccess_leases",createHashMap]))==0
            && {(_patient getVariable ["ACME_chestAccess_requestToken",""])==""},"late canceled start reenrolled"] call _check;
    ''' + f'[_vest=="{("Vest_A" if worn else "")}","late canceled start changed gear"] call _check;')


def test_start_stop_reordered_retry_cannot_reenroll_or_finish():
    execute(setup() + access.begin() + r'''
        [_patient,objNull,"first",false,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        _patient setVariable ["ACME_chestAccess_readyServer",333];
        _acquireRequests=[]; _waits=[];
        for "_i" from 1 to 3 do {
            [_patient,objNull,"first",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        };
        [_old] call _deliver;
        [count _acquireRequests==0 && {count _waits==0} && {count _commits==0},"canceled retry or old callback restarted preparation"] call _check;
        [_vest=="Vest_A" && {(_patient getVariable ["ACME_chestAccess_readyServer",0])==333},"canceled retry removed or ACKed"] call _check;
    ''')


def test_canceled_id_and_duplicate_stop_leave_concurrent_member_untouched():
    execute(setup() + access.begin() + r'''
        private _token=_patient getVariable ["ACME_chestAccess_requestToken",""];
        [_patient,_medic,"second",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [_patient,objNull,"first",false,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        private _closedBefore=+(_patient getVariable ["ACME_chestAccess_closedLeases",[]]);
        _acquireRequests=[];
        [_patient,objNull,"first",false,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [_patient,objNull,"first",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [count _acquireRequests==0 && {count _restores==0},"closed first member reacquired or returned shared gear"] call _check;
        [(_patient getVariable ["ACME_chestAccess_requestToken",""])==_token
            && {(_patient getVariable ["ACME_chestAccess_readyLease",""])=="second"},"closed first member disturbed shared request"] call _check;
        [(_patient getVariable ["ACME_chestAccess_closedLeases",[]]) isEqualTo _closedBefore,"duplicate stop refreshed/reordered tombstone"] call _check;
        [_old] call _deliver; call _drain;
        [count _commits==1 && {_vest==""},"valid remaining member lost or duplicated removal"] call _check;
    ''')


def test_canceling_latest_ready_member_keeps_earlier_member_ready():
    execute(setup() + access.begin() + r'''
        [_patient,_medic,"second",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [_old] call _deliver; call _drain;
        private _token=_patient getVariable ["ACME_chestAccess_requestToken",""];
        private _ready=_patient getVariable ["ACME_chestAccess_readyServer",-1];
        _acquireRequests=[];
        [_patient,_medic,"second",false,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [(_patient getVariable ["ACME_chestAccess_readyLease",""])=="first"
            && {(_patient getVariable ["ACME_chestAccess_readyServer",-2])==_ready}
            && {(_patient getVariable ["ACME_chestAccess_requestToken",""])==_token},"last joiner cancellation stranded earlier member readiness"] call _check;
        [_patient,_medic,"second",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [count _restores==0 && {count _acquireRequests==0}
            && {(_patient getVariable ["ACME_chestAccess_readyLease",""])=="first"},"retired joiner displaced surviving ready member"] call _check;
    ''')


@pytest.mark.parametrize('ready', [False, True])
def test_active_duplicate_start_is_idempotent_for_pending_and_ready_shared_episode(ready):
    execute(setup() + access.begin() + (r'''
        [_old] call _deliver;
        _patient setVariable ["ACME_chestAccess_readyServer",333];
    ''' if ready else '') + r'''
        private _token=_patient getVariable ["ACME_chestAccess_requestToken",""];
        private _stamp=+(_patient getVariable ["ACME_chestAccess_requestOwner",[]]);
        private _readyBefore=_patient getVariable ["ACME_chestAccess_readyServer",-1];
        private _queued=count _waits; _acquireRequests=[];
        for "_i" from 1 to 3 do {
            [_patient,objNull,"first",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        };
        [count _acquireRequests==0 && {count _waits==_queued},"same-owner duplicate START repeated acquisition"] call _check;
        [(_patient getVariable ["ACME_chestAccess_readyServer",-2])==_readyBefore
            && {(_patient getVariable ["ACME_chestAccess_requestToken",""])==_token}
            && {(_patient getVariable ["ACME_chestAccess_requestOwner",[]]) isEqualTo _stamp},"same-owner duplicate START changed ready authority"] call _check;
    ''')


def test_existing_cpr_id_stays_accepted_across_bvm_handoff_then_final_cancel():
    execute(setup() + r'''
        _parent=missionNamespace;
        [_patient,_medic,"maneuver",true,"cpr"] call ACME_fnc_chestAccessVestEvent;
        private _token=_patient getVariable ["ACME_chestAccess_requestToken",""];
        private _ready=_patient getVariable ["ACME_chestAccess_readyServer",-1];
        _acquireRequests=[];
        [_patient,_medic,"maneuver",true,"usebvm"] call ACME_fnc_chestAccessVestEvent;
        [_patient,_medic,"maneuver",true,"cpr","new-preflight"] call ACME_fnc_chestAccessVestEvent;
        [count _acquireRequests==0 && {!(["maneuver"] call _closed)},"live maneuver handoff was retired or reacquired"] call _check;
        [(_patient getVariable ["ACME_chestAccess_requestToken",""])==_token
            && {(_patient getVariable ["ACME_chestAccess_readyServer",-2])==_ready},"live maneuver lost carrier readiness"] call _check;
        [_patient,_medic,"maneuver",false,"cpr"] call ACME_fnc_chestAccessVestEvent;
        [_patient,_medic,"maneuver",true,"cpr"] call ACME_fnc_chestAccessVestEvent;
        [["maneuver"] call _closed && {count _acquireRequests==0},"final cancellation failed to end exact maneuver"] call _check;
    ''')


def test_explicit_new_owner_invocation_resumes_active_id_without_old_callback_authority():
    execute(setup() + access.begin() + r'''
        private _oldToken=_patient getVariable ["ACME_chestAccess_requestToken",""];
        _patient setVariable ["ACME_providerLocalityEpoch",2];
        _patient setVariable ["ACME_chestAccess_requestToken",""];
        [_patient,objNull,"first",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        private _new=_waits deleteAt ((count _waits)-1);
        [(_patient getVariable ["ACME_chestAccess_requestToken",""])!=_oldToken,"new owner reused previous captured request"] call _check;
        [_old] call _deliver;
        [count _commits==0,"old-owner callback removed gear after new acceptance"] call _check;
        [_new] call _deliver;
        [count _commits==1 && {(_patient getVariable ["ACME_chestAccess_readyServer",0])==1000},"fresh owner could not resume surviving active lease"] call _check;
    ''')


def test_forwarded_stop_delivered_before_start_survives_owner_handoff():
    execute(setup() + function('ownerDispatch') + r'''
        _patientLocal=false;
        [_patient,_medic,"packet",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [_patient,_medic,"packet",false,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [count _events==2 && {isNil {_patient getVariable "ACME_chestAccess_closedLeases"}},"nonowner changed local cancellation memory"] call _check;
        private _startPacket=(_events select 0) select 1;
        private _stopPacket=(_events select 1) select 1;
        _patientLocal=true; _patient setVariable ["ACME_providerLocalityEpoch",2];
        _stopPacket call ACME_fnc_ownerDispatch;
        _startPacket call ACME_fnc_ownerDispatch;
        [["packet"] call _closed && {count _acquireRequests==0},"owner handoff lost stop-before-start ordering"] call _check;
    ''')


def test_old_kit_packet_cannot_record_cancellation_in_new_kit():
    execute(setup() + function('ownerDispatch') + r'''
        _patientLocal=false;
        [_patient,_medic,"old-kit",false,"cpr"] call ACME_fnc_chestAccessVestEvent;
        private _packet=(_events select 0) select 1;
        _patientLocal=true; _patient setVariable ["ACME_equipmentKitEpoch",1];
        _packet call ACME_fnc_ownerDispatch;
        [!(["old-kit"] call _closed),"stale-kit packet wrote cancellation into successor kit"] call _check;
    ''')


def test_ttl_is_exact_and_duplicate_stop_does_not_extend_protection():
    execute(setup() + r'''
        [_patient,_medic,"ttl",false,"cpr"] call ACME_fnc_chestAccessVestEvent;
        private _record=+(_patient getVariable ["ACME_chestAccess_closedLeases",[]]);
        _serverClock=1100;
        [_patient,_medic,"ttl",false,"cpr"] call ACME_fnc_chestAccessVestEvent;
        [(_patient getVariable ["ACME_chestAccess_closedLeases",[]]) isEqualTo _record,"duplicate cancel extended TTL"] call _check;
        _serverClock=1179.99;
        [_patient,_medic,"ttl",true,"cpr"] call ACME_fnc_chestAccessVestEvent;
        [count _acquireRequests==0,"unexpired cancellation admitted replay"] call _check;
        _serverClock=1180; _parent=missionNamespace;
        [_patient,_medic,"ttl",true,"cpr"] call ACME_fnc_chestAccessVestEvent;
        [count _acquireRequests==1,"expired bounded tombstone became permanent denial"] call _check;
        [_patient,["next"]] call ACME_fnc_chestAccessLeaseRetire;
        [(_patient getVariable ["ACME_chestAccess_closedLeases",[]]) isEqualTo [["next",1360]],"expiration cleanup retained expired record"] call _check;
    ''')


def test_capacity_eviction_is_fifo_and_duplicate_stops_do_not_move_old_ids():
    execute(setup() + r'''
        for "_i" from 0 to 63 do {
            [_patient,_medic,format ["id%1",_i],false,"cpr"] call ACME_fnc_chestAccessVestEvent;
        };
        [_patient,_medic,"id0",false,"cpr"] call ACME_fnc_chestAccessVestEvent;
        [_patient,_medic,"id64",false,"cpr"] call ACME_fnc_chestAccessVestEvent;
        private _records=_patient getVariable ["ACME_chestAccess_closedLeases",[]];
        [count _records==64 && {(_records select 0 select 0)=="id1"}
            && {(_records select 63 select 0)=="id64"},"bounded cancellation FIFO changed"] call _check;
        [_patient,_medic,"id64",true,"cpr"] call ACME_fnc_chestAccessVestEvent;
        [count _acquireRequests==0,"retained tombstone admitted start"] call _check;
        _parent=missionNamespace;
        [_patient,_medic,"id0",true,"cpr"] call ACME_fnc_chestAccessVestEvent;
        [count _acquireRequests==1,"evicted ID was treated as permanently retired"] call _check;
    ''')


def test_retirement_helper_is_owner_only_and_changes_no_custody_or_clinical_state():
    execute(setup() + r'''
        _patient setVariable ["ACME_chestAccess_vestLoadout",["Vest_A",[["seal",2]]]];
        _patient setVariable ["ACME_Thora_ChestAccessActive",true];
        _patient setVariable ["ACME_chestAccess_readyServer",333];
        _patientLocal=false;
        [!([_patient,["closed"]] call ACME_fnc_chestAccessLeaseRetire),"nonowner wrote retirement memory"] call _check;
        [isNil {_patient getVariable "ACME_chestAccess_closedLeases"},"nonowner created retirement records"] call _check;
        _patientLocal=true;
        [[_patient,["closed","",0]] call ACME_fnc_chestAccessLeaseRetire,"owner could not retire valid ID"] call _check;
        [(_patient getVariable ["ACME_chestAccess_closedLeases",[]]) isEqualTo [["closed",1180]],"invalid ID was recorded"] call _check;
        [(_patient getVariable ["ACME_chestAccess_vestLoadout",[]]) isEqualTo ["Vest_A",[["seal",2]]]
            && {_patient getVariable ["ACME_Thora_ChestAccessActive",false]}
            && {(_patient getVariable ["ACME_chestAccess_readyServer",0])==333},"memory helper performed clinical/gear teardown"] call _check;
    ''')


def manual_setup():
    permission=function('manualPlateCarrierCanToggle').replace('(_patient isKindOf "CAManBase")', 'true')
    return setup() + permission + function('manualPlateCarrierCommit') + function('manualPlateCarrierAutoReturn') + r'''
        private _restoreAllowed=false; private _sequences=[];
        ace_common_fnc_isAwake={true};
        ACME_fnc_headElevMedicSeq={_sequences pushBack _this;};
        ACME_fnc_chestAccessVestRestore={
            _restores pushBack _this;
            if (_restoreAllowed) then {_vest="Vest_A"; _patient setVariable ["ACME_chestAccess_vestLoadout",[]];};
            _restoreAllowed
        };
        _patient setVariable ["ACME_manualPlateCarrierState","off"];
        _patient setVariable ["ACME_manualPlateCarrierLease","manual"];
        _patient setVariable ["ACME_manualPlateCarrierProvider",_medic];
        _patient setVariable ["ACME_chestAccess_leases",createHashMapFromArray [["manual",[_medic,10,"manualplatecarrier"]]]];
        _patient setVariable ["ACME_chestAccess_vestLoadout",["Vest_A",[["seal",2]]]];
        _vest="";
    '''


def test_manual_replace_retires_only_id_without_ordinary_access_teardown():
    execute(manual_setup() + r'''
        [[_medic,_patient,true,[1,2,3,4,5]] call ACME_fnc_manualPlateCarrierCommit,"manual replacement was rejected"] call _check;
        [count _restores==1 && {count _sequences==1},"manual retirement changed authored replacement policy"] call _check;
        _acquireRequests=[];
        [_patient,_medic,"manual",true,"manualplatecarrier"] call ACME_fnc_chestAccessVestEvent;
        [["manual"] call _closed && {count _acquireRequests==0},"late manual start reopened replaced lease"] call _check;
    ''')


def test_failed_manual_force_return_keeps_custody_and_allows_explicit_retry():
    execute(manual_setup() + r'''
        [!([_patient,"state","manual"] call ACME_fnc_manualPlateCarrierAutoReturn),"failed physical return was reported successful"] call _check;
        [["manual"] call _closed,"failed manual cancellation lost ordering memory"] call _check;
        [(_patient getVariable ["ACME_chestAccess_vestLoadout",[]]) isEqualTo ["Vest_A",[["seal",2]]]
            && {(_patient getVariable ["ACME_manualPlateCarrierLease",""])=="manual"}
            && {"manual" in keys (_patient getVariable ["ACME_chestAccess_leases",createHashMap])},"failed return discarded recovery custody"] call _check;
        _acquireRequests=[];
        [_patient,_medic,"manual",true,"manualplatecarrier"] call ACME_fnc_chestAccessVestEvent;
        [count _acquireRequests==0,"retained internal recovery lease admitted canceled external preparation"] call _check;
        _restoreAllowed=true;
        [[_patient,"state","manual"] call ACME_fnc_manualPlateCarrierAutoReturn,"explicit restoration retry blocked by tombstone"] call _check;
        [_vest=="Vest_A" && {(_patient getVariable ["ACME_manualPlateCarrierLease",""])==""}
            && {(_patient getVariable ["ACME_chestAccess_vestLoadout",[1]]) isEqualTo []},"explicit retry lost exact saved carrier"] call _check;
    ''')


def object_function(name):
    text=source(name).replace('objNull, [objNull]', 'objNull')
    text=text.replace('local _patient','_ownerLocal').replace('serverTime','_clock')
    return 'ACME_fnc_'+name+'={'+adapt(text)+'};'


def kit_setup():
    with patch.object(kit, 'src', source):
        text=kit.setup()
    return text + object_function('chestAccessLeaseRetire') + object_function('chestAccessVestEvent') + r'''
        private _acquireRequests=[];
        ACME_fnc_chestAccessVestAcquire={_acquireRequests pushBack _this;};
        ACME_fnc_chestAccessVestRestore={};
    ''' + kit.custody()


def test_successful_kit_archive_remembers_old_access_ids_without_returning_old_gear():
    execute(kit_setup() + r'''
        [[_patient] call ACM_core_fnc_carrierKitChanged,"physical archive failed"] call _check;
        [_patient,_medic,"old-manual",true,"manualplatecarrier"] call ACME_fnc_chestAccessVestEvent;
        [count _acquireRequests==0 && {_wornVest=="NewCarrier"},"late old-kit start acquired replacement gear"] call _check;
        [str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents,"kit tombstone changed live archived supplies"] call _check;
        [_patient,_medic,"fresh",true,"manualplatecarrier"] call ACME_fnc_chestAccessVestEvent;
        [count _acquireRequests==1,"new valid ID was blocked by old-kit cancellation memory"] call _check;
    ''')


def test_failed_kit_archive_does_not_discard_old_membership_or_recovery_evidence():
    execute(kit_setup() + r'''
        _cargo setVariable ["ACME_carrierPatient",_medic];
        [!([_patient] call ACM_core_fnc_carrierKitChanged),"foreign custody archive accepted"] call _check;
        [isNil {_patient getVariable "ACME_chestAccess_closedLeases"}
            && {"old-manual" in keys (_patient getVariable ["ACME_chestAccess_leases",createHashMap])},"failed archive retired retained references"] call _check;
        [(_patient getVariable ["ACME_carrierCargo",objNull]) isEqualTo _cargo
            && {str ([_cargo] call ACME_fnc_carrierCargoSnapshot)==_contents},"failed archive lost recovery evidence"] call _check;
    ''')


@pytest.mark.parametrize('surviving', [False, True])
def test_watchdog_expiry_retires_id_and_preserves_other_live_members(surviving):
    text=source('chestAccessVestAcquire')
    body=text.split('    private _pfh = [{',1)[1].split('    }, 0.20, [_p,_ctx,_savedVar,_pfhVar]]',1)[0]
    with patch.object(workspace,'source',lambda _:body):
        body=workspace.code('watchdog',server_clock='_serverClock')
    execute(setup() + 'private _watchdog={'+body+'};' + r'''
        _patient setVariable ["ACME_chestAccess_vestLoadout",["Vest_A",[]]];
        private _members=createHashMapFromArray [["expired",[_medic,-1000,"cpr"]]];
    ''' + ('_members set ["live",[_medic,CBA_missionTime,"thoracostomy"]];' if surviving else '') + r'''
        _patient setVariable ["ACME_chestAccess_leases",_members];
        _patient setVariable ["ACME_chestAccess_requestToken","shared"];
        _patient setVariable ["ACME_chestAccess_readyLease","expired"];
        [[_patient,"access","ACME_chestAccess_vestLoadout","ACME_chestAccess_vestPFH"],3] call _watchdog;
        [_patient,_medic,"expired",true,"cpr"] call ACME_fnc_chestAccessVestEvent;
        [["expired"] call _closed && {count _acquireRequests==0},"watchdog-removed ID could reenroll"] call _check;
    ''' + (r'''
        ["live" in keys (_patient getVariable ["ACME_chestAccess_leases",createHashMap])
            && {count _restores==0} && {(_patient getVariable ["ACME_chestAccess_requestToken",""])=="shared"}
            && {(_patient getVariable ["ACME_chestAccess_readyLease",""])=="live"},"expiry destroyed surviving shared custody/readiness"] call _check;
    ''' if surviving else r'''
        [count _restores==1 && {(_patient getVariable ["ACME_chestAccess_requestToken","bad"])==""}
            && {(_patient getVariable ["ACME_chestAccess_readyLease","bad"])==""},"last expiry kept retired authority or failed ordinary return"] call _check;
    '''))


def test_hard_heal_reset_remembers_all_old_ids_without_blocking_fresh_episode():
    text=source('clearAllAilments')
    block=text[text.index('[_patient, true] call ACME_fnc_chestAccessVestRestore;'):text.index('private _hePropObj')]
    execute(setup() + r'''
        _patient setVariable ["ACME_chestAccess_leases",createHashMapFromArray [["old-a",[_medic,10,"cpr"]],["old-b",[_medic,10,"checkbreathing"]]]];
    ''' + adapt(block) + r'''
        [_patient,_medic,"old-a",true,"cpr"] call ACME_fnc_chestAccessVestEvent;
        [_patient,_medic,"old-b",true,"checkbreathing"] call ACME_fnc_chestAccessVestEvent;
        [count _acquireRequests==0 && {["old-a"] call _closed} && {["old-b"] call _closed},"hard reset accepted retired ACCESS requests"] call _check;
        _parent=missionNamespace;
        [_patient,_medic,"fresh",true,"cpr"] call ACME_fnc_chestAccessVestEvent;
        [count _acquireRequests==1,"hard reset blocked fresh clinical episode"] call _check;
    ''')


def test_retirement_memory_is_registered_and_public_for_owner_handoff():
    cfg=(ROOT/'addons/acm_extended/config.cpp').read_text()
    assert cfg.count('class chestAccessLeaseRetire {};')==1
    assert '_patient setVariable ["ACME_chestAccess_closedLeases", _closed, true];' in source('chestAccessLeaseRetire')
