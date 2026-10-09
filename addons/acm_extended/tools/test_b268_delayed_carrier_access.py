"""Execute production ACCESS acceptance/callbacks with controlled CBA delivery.

Only Arma inventory/prop staging, vehicle identity and rendered animation are
engine boundaries. Production acceptance, concurrent leases, captured authority,
vehicle revalidation and delayed success/timeout code execute in SQF-VM. These
tests do not prove actual vehicle seat replication or network delivery ordering.

Set ACME_B268_BASELINE=5526413e to execute the same cases against unchanged B267.
"""
import os
import subprocess
from unittest.mock import patch

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute
import test_historical_chest_workspace as workspace
import test_chestseal_preparation_progress as prep


def source(name):
    path = f'addons/acm_extended/functions/fn_{name}.sqf'
    revision = os.environ.get('ACME_B268_BASELINE')
    if revision:
        return subprocess.check_output(['git', 'show', f'{revision}:{path}'], cwd=ROOT, text=True)
    return (ROOT / path).read_text()


def function(name):
    with patch.object(workspace, 'source', source):
        text = workspace.code(name, server_clock='_serverClock')
    if name == 'chestAccessVestAcquire':
        start = text.index('private _commitRemoval = {')
        boundary = text.index('    private _class = ', start)
        end = text.index('// Animation is allowed only', boundary)
        # Keep the production locality, seat, existing-custody and standing
        # guards. Only physical inventory/prop staging is one explicit boundary.
        text = text[:boundary] + r'''
            _commits pushBack _serverClock;
            _p setVariable [_savedVar,["Vest_A",[]]];
            _vest=""; _loadout set [4,[]]; true
        };
        ''' + text[end:]
    return 'ACME_fnc_' + name + '={' + text + '};\n'


def setup():
    return prep.setup() + r'''
        private _restores=[];
        // Restoration is independently covered by B267 production cargo tests;
        // cancellation here records its handoff without scheduling unrelated RTM.
        ACME_fnc_chestAccessVestRestore={_restores pushBack _this; true};
    ''' + function('chestAccessVestAcquire') + function('chestAccessVestEvent')


def begin(worn=True, animate=False):
    gear = '_vest="Vest_A"; _loadout set [4,["Vest_A",[]]];' if worn else '_vest=""; _loadout set [4,[]];'
    return gear + f'_blocked={str(not animate).lower()};' + r'''
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_Suspended",true];
        _patient setVariable ["ACME_headElev_suspendReadyAt",11];
        [_patient,objNull,"first",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [count _waits==1,"fixture did not queue delayed ACCESS"] call _check;
        private _old=call _take;
    '''


def test_cancelled_delayed_removal_cannot_strip_or_ack():
    execute(setup() + begin() + r'''
        [_patient,objNull,"first",false,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        _patient setVariable ["ACME_chestAccess_readyServer",333];
        [_old] call _deliver;
        [count _commits==0 && {_vest=="Vest_A"},"cancelled ACCESS removed the carrier"] call _check;
        [(_patient getVariable ["ACME_chestAccess_readyServer",0])==333,"cancelled ACCESS published readiness"] call _check;
    ''')


@pytest.mark.parametrize('timeout', [False, True])
def test_cancelled_bare_chest_success_and_timeout_cannot_ack(timeout):
    execute(setup() + begin(worn=False) + r'''
        [_patient,objNull,"first",false,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        _patient setVariable ["ACME_chestAccess_readyServer",333];
        CBA_missionTime=12;
    ''' + f'[_old,{str(timeout).lower()}] call _deliver;' + r'''
        [(_patient getVariable ["ACME_chestAccess_readyServer",0])==333,"cancelled bare-chest callback published readiness"] call _check;
    ''')


def test_cancel_reopen_same_kit_only_new_request_can_remove_and_ack():
    execute(setup() + begin() + r'''
        [_patient,objNull,"first",false,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [_patient,objNull,"second",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        // Cancel also queues an independent Semi-Fowler resume. The new
        // carrier-removal continuation is the newly appended final job.
        private _new=_waits deleteAt ((count _waits)-1);
        [_old] call _deliver;
        [count _commits==0 && {(_patient getVariable ["ACME_chestAccess_readyServer",0])==-1},"old request completed new same-kit preparation"] call _check;
        [_new] call _deliver;
        [count _commits==1 && {_vest==""},"new valid request lost carrier removal"] call _check;
        [(_patient getVariable ["ACME_chestAccess_readyServer",0])==1000,"new valid request did not publish actual readiness"] call _check;
    ''')


def test_first_provider_cancel_keeps_other_concurrent_lease_preparation():
    execute(setup() + begin() + r'''
        private _token=_patient getVariable ["ACME_chestAccess_requestToken",""];
        [_patient,objNull,"second",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [_patient,objNull,"first",false,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [(_patient getVariable ["ACME_chestAccess_requestToken",""])==_token,"joining/cancelling a member replaced shared preparation"] call _check;
        [_old] call _deliver;
        [count _commits==1 && {(_patient getVariable ["ACME_chestAccess_readyLease",""])=="second"},"remaining lease lost shared carrier preparation"] call _check;
        call _drain;
        [count _commits==1,"concurrent preparation duplicated physical removal"] call _check;
    ''')


@pytest.mark.parametrize('worn', [False, True])
def test_owner_away_back_retires_old_removal_and_readiness(worn):
    execute(setup() + begin(worn=worn) + r'''
        // This is the ownerInit Local handler's existing counter, advanced on
        // both edges even when ownership returns before a scheduled callback.
        _patient setVariable ["ACME_providerLocalityEpoch",2];
        _patient setVariable ["ACME_chestAccess_readyServer",333];
        CBA_missionTime=12;
        [_old] call _deliver;
        [count _commits==0 && {(_patient getVariable ["ACME_chestAccess_readyServer",0])==333},"old-owner continuation survived away/back transfer"] call _check;
    ''')


def test_delayed_no_animation_vehicle_entry_keeps_worn_gear_and_clinical_ready():
    execute(setup() + begin() + r'''
        _parent=missionNamespace;
        [_old] call _deliver;
        [count _commits==0 && {_vest=="Vest_A"},"delayed ACCESS stripped seated casualty"] call _check;
        [count _pins==0 && {count _animRequests==0},"vehicle fallback moved the patient"] call _check;
        [(_patient getVariable ["ACME_chestAccess_readyServer",0])==1000,"valid seated care lost readiness"] call _check;
    ''')


@pytest.mark.parametrize('after_lift', [False, True])
def test_vehicle_entry_during_animated_wait_keeps_worn_gear(after_lift):
    execute(setup() + begin(animate=True) +
            ('[_old] call _deliver; _old=call _take;' if after_lift else '') + r'''
        _parent=missionNamespace; _pins=[]; _animRequests=[];
        [_old] call _deliver;
        [count _commits==0 && {_vest=="Vest_A"},"animated continuation stripped seated casualty"] call _check;
        [count _pins==0 && {count _animRequests==0},"animated continuation took vehicle skeleton"] call _check;
        [(_patient getVariable ["ACME_chestAccess_readyServer",0])==1000,"animated vehicle transition stranded care"] call _check;
        call _drain;
        [count _commits==0,"old lift completion stripped seated casualty later"] call _check;
    ''')


def test_direct_manual_lease_retirement_invalidates_delayed_removal():
    execute(setup() + begin() + r'''
        // Manual Replace/Abort/AutoReturn can edit leases directly. An old
        // request token alone is not evidence of a remaining active member.
        _patient setVariable ["ACME_chestAccess_leases",createHashMap];
        _patient setVariable ["ACME_chestAccess_readyServer",333];
        [_old] call _deliver;
        [count _commits==0 && {(_patient getVariable ["ACME_chestAccess_readyServer",0])==333},"direct lease retirement left pending removal active"] call _check;
    ''')


@pytest.mark.parametrize('foreign', [False, True])
def test_vehicle_lift_abort_releases_only_exact_old_motion(foreign):
    execute(setup() + 'ACME_fnc_patientAnimRelease={' +
            adapt(source('patientAnimRelease')) + '};' + begin(animate=True) + r'''
        [_old] call _deliver;
        private _lift=call _take;
        private _carrierToken=_patient getVariable ["ACME_chestAccess_vestBusy",""];
        private _motionToken=_carrierToken;
    ''' + ('_motionToken="other-motion";' if foreign else '') + r'''
        _patient setVariable ["ACME_patientAnimLock",[_motionToken,"motion",objNull,4,1100,1.5]];
        _patient setVariable ["ACME_patientAnimSpeedToken",_motionToken];
        _testAnimationSpeed=1.5;
        _parent=missionNamespace;
        [_lift] call _deliver;
        [(_patient getVariable ["ACME_chestAccess_removeSpeedToken","bad"])=="","vehicle abort retained old carrier speed marker"] call _check;
    ''' + (r'''
        [((_patient getVariable ["ACME_patientAnimLock",[]]) param [0,""])==_motionToken && {_testAnimationSpeed==1.5},"carrier vehicle abort released newer motion"] call _check;
    ''' if foreign else r'''
        [(_patient getVariable ["ACME_patientAnimLock",[]]) isEqualTo [] && {_testAnimationSpeed==1},"vehicle abort stranded old moving lock/speed"] call _check;
        [(_patient getVariable ["ACME_patientAnimSpeedToken","bad"])=="","vehicle abort stranded old speed custody"] call _check;
    '''))


def local_carrier_block():
    text = source('ownerInit')
    start = text.index('    _unit setVariable ["ACME_providerLocalityEpoch",')
    end = text.index('    // Pending prone-to-Semi-Fowler', start)
    return adapt(text[start:end])


@pytest.mark.parametrize('source_label', ['chest-access-vest', 'chest-access-vest-restore', 'other-procedure'])
def test_local_edges_retire_machine_markers_and_only_old_carrier_animation(source_label):
    execute(setup() + begin() + r'''
        private _unit=_patient; private _isLocal=false;
        _patient setVariable ["ACME_chestAccess_frontBusy","old-front"];
        _patient setVariable ["ACME_chestAccess_vestBusy","old-busy"];
        _patient setVariable ["ACME_CS_frontBusy","old-cs-front"];
        _patient setVariable ["ACME_CS_vestBusy","old-cs-busy"];
    ''' + f'_patient setVariable ["ACME_patientAnimLock",["owned","{source_label}",objNull,4,1100,1.5]];' +
            local_carrier_block() + '_isLocal=true;' + local_carrier_block() + r'''
        [(_patient getVariable ["ACME_providerLocalityEpoch",0])==2,"Local edges did not advance callback authority"] call _check;
        [(["ACME_chestAccess_frontBusy","ACME_chestAccess_vestBusy","ACME_CS_frontBusy","ACME_CS_vestBusy","ACME_chestAccess_requestToken"] findIf {(_patient getVariable [_x,"bad"])!=""})<0,"Local edges retained old carrier markers"] call _check;
        [count (_patient getVariable ["ACME_chestAccess_leases",createHashMap])==1,"Local cleanup destroyed clinical lease membership"] call _check;
    ''' + f'[count _releases=={0 if source_label == "other-procedure" else 1},"Local cleanup released a foreign animation or retained carrier animation"] call _check;' + r'''
        [_old] call _deliver;
        [count _commits==0,"retired Local callback still removed carrier"] call _check;
        [_patient,objNull,"second",true,"thoracostomy"] call ACME_fnc_chestAccessVestEvent;
        [(_patient getVariable ["ACME_chestAccess_requestToken",""])!="","incoming owner failed to accept a fresh preparation"] call _check;
        private _new=call _take; [_new] call _deliver;
        [count _commits==1,"incoming owner fresh preparation could not progress"] call _check;
    ''')


def chest_begin_setup():
    return setup() + function('chestSealPatientBegin') + r'''
        private _preparationAcquires=[];
        // The surrounding production Begin waiter is isolated here from its
        // independently executed Acquire scheduler. A completed physical
        // preparation reports this exact readiness boundary.
        ACME_fnc_chestAccessVestAcquire={
            _preparationAcquires pushBack _this;
            (_this select 0) setVariable ["ACME_CS_vestReadyServer",1000]; true
        };
        [_patient,"viewer",objNull] call ACME_fnc_chestSealPatientBegin;
        private _readyWait=call _take;
    '''


@pytest.mark.parametrize('change', [
    '_patient setVariable ["ACME_providerLocalityEpoch",2];',
    '_patient setVariable ["ACME_equipmentKitEpoch",1];',
])
def test_outer_chest_waiter_cannot_rebind_acquire_or_ack(change):
    execute(chest_begin_setup() + change + r'''
        _vest="Vest_A"; _loadout set [4,["Vest_A",[]]];
        _patient setVariable ["ACME_CS_vestReadyServer",1000];
        _patient setVariable ["ACME_CS_ProcedureReadyAt",333];
        [_readyWait] call _deliver;
        [count _preparationAcquires==1,"obsolete CS waiter recaptured authority and reacquired gear"] call _check;
        [(_patient getVariable ["ACME_CS_ProcedureReadyAt",0])==333,"obsolete CS waiter published readiness"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_patient setVariable ["ACME_providerLocalityEpoch",2];',
    '_patient setVariable ["ACME_equipmentKitEpoch",1];',
])
def test_outer_chest_normalization_retry_cannot_roll_or_ack_after_boundary(change):
    execute(chest_begin_setup() + r'''
        _actualSide="back";
        [_readyWait] call _deliver;
        private _normalization=call _take;
        private _oldRolls=count _rolls;
    ''' + change + r'''
        CBA_missionTime=80;
        _patient setVariable ["ACME_CS_ProcedureReadyAt",333];
        [_normalization] call _deliver;
        [count _rolls==_oldRolls,"obsolete CS normalization restarted body roll"] call _check;
        [(_patient getVariable ["ACME_CS_ProcedureReadyAt",0])==333,"obsolete CS normalization published readiness"] call _check;
    ''')


def test_fresh_begin_after_handoff_resumes_same_token_without_rewriting_custody_snapshot():
    execute(chest_begin_setup() + r'''
        private _original=+(_patient getVariable ["ACME_CS_PreProcedureState",[]]);
        _patient setVariable ["ACME_providerLocalityEpoch",2];
        _patient setVariable ["ACME_CS_vestLoadout",["Vest_A",[]]];
        _patient setVariable ["ACME_CS_ProcedureGrounded",false];
        // Current Grab/Hold geometry is neither the original rest pose nor
        // evidence that the first preparation was grounded.
        _animation="ACME_HeadElevPatientGrab";
        [_patient,"viewer",objNull] call ACME_fnc_chestSealPatientBegin;
        [count _preparationAcquires==2,"explicit same-token Begin did not resume incomplete owner handoff"] call _check;
        [count _restores==0,"owner handoff rewore old shared carrier custody"] call _check;
        [(_patient getVariable ["ACME_CS_PreProcedureState",[]]) isEqualTo _original,"owner handoff overwrote original posture snapshot"] call _check;
        [!(_patient getVariable ["ACME_CS_ProcedureGrounded",true]),"owner handoff recaptured transient grounded state"] call _check;
        [(_patient getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo ["viewer"],"owner handoff duplicated membership"] call _check;
        [((_preparationAcquires select 1) select 6) isEqualTo [0,2,"","viewer"],"new Begin did not supply captured current authority"] call _check;
        private _new=call _take;
        [_readyWait] call _deliver;
        [(_patient getVariable ["ACME_CS_ProcedureReadyAt",0])==-1,"old owner waiter acknowledged resumed preparation"] call _check;
        [_new] call _deliver;
        [(_patient getVariable ["ACME_CS_ProcedureReadyAt",0])==1000,"fresh owner Begin lost readiness"] call _check;
    ''')


@pytest.mark.parametrize('token', ['viewer', 'new-viewer'])
def test_failed_kit_boundary_retained_workspace_cannot_be_adopted(token):
    execute(chest_begin_setup() + r'''
        // Kit retirement can reject ambiguous/malformed custody before it
        // clears workspace references. The accepted prep's old kit stays
        // evidence; a fresh Begin must not bind that record to the new kit.
        _patient setVariable ["ACME_equipmentKitEpoch",1];
        _patient setVariable ["ACME_CS_vestLoadout",["Vest_A",[["old",1]]]];
        _patient setVariable ["ACME_CS_vestLoadoutKitEpoch",0];
        _patient setVariable ["ACME_CS_vestReadyServer",333];
        private _beforeTokens=+(_patient getVariable ["ACME_CS_ProcedureTokens",[]]);
        private _beforeGeneration=_patient getVariable ["ACME_CS_ProcedureGeneration",0];
        private _beforeSnapshot=+(_patient getVariable ["ACME_CS_PreProcedureState",[]]);
    ''' + f'[_patient,"{token}",objNull] call ACME_fnc_chestSealPatientBegin;' + r'''
        [count _preparationAcquires==1 && {count _restores==0},"failed-boundary evidence was adopted/restored to a new kit"] call _check;
        [(_patient getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo _beforeTokens,"failed kit boundary admitted new membership"] call _check;
        [(_patient getVariable ["ACME_CS_ProcedureGeneration",0])==_beforeGeneration,"failed kit boundary rewrote old procedure generation"] call _check;
        [(_patient getVariable ["ACME_CS_PreProcedureState",[]]) isEqualTo _beforeSnapshot,"failed kit boundary rewrote old posture recovery"] call _check;
        [(_patient getVariable ["ACME_CS_vestReadyServer",0])==333 && {(_patient getVariable ["ACME_CS_ProcedureReadyAt",0])==-1},"failed kit boundary was acknowledged as new care"] call _check;
    ''')
