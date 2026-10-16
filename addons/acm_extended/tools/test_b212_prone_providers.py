"""Execute prone DP/Hang Bag/Semi-Fowler provider lifecycles.

Engine poses, keys, clocks and props are explicit boundaries. Production action
and cancellation controllers run in SQF-VM; real RTM rendering remains a live
Arma check. The Hang Bag activation test executes its presentation block, with
prop creation excluded from the fixture.
"""
import re

import pytest

from test_b211_direct_pressure_inputs import setup as pressure_setup
from test_bounded_head_provider_sequence import setup as head_setup
from test_bounded_head_provider_consciousness import setup as head_cancel_setup
from test_b156_animation_choreography import manual_support_setup
from test_menu_death_lifecycle import adapt, execute, read


@pytest.mark.parametrize("part", ["body", "leftarm", "head"])
@pytest.mark.parametrize("movement", ["MoveForward", "MoveLeft", "Evasive"])
def test_prone_pressure_resumes_without_raising_provider_then_right_click_releases(part, movement):
    execute(pressure_setup() + f'''
        _providerStance="PRONE";
        ["{part}"] call _start;
        [(_medic getVariable ["ACME_DP_Pose",""])=="ACM_ProneContinuous","prone pressure pose not selected"] call _check;
        private _id=_medic getVariable "ACME_DP_PFH";
        _animation="acm_pronecontinuous"; _inputActions=["{movement}"];
        CBA_missionTime=CBA_missionTime+0.2; call _pressTick;
        [_medic getVariable ["ACME_DP_Active",false],"prone movement cancelled clinical pressure"] call _check;
        _inputActions=[]; _animation="amovppnemrunsnonwnondf";
        CBA_missionTime=CBA_missionTime+0.016; call _pressTick;
        [!(_medic getVariable ["ACME_DP_InPose",false]),"prone pressure skipped quiet interval"] call _check;
        CBA_missionTime=(_medic getVariable "ACME_DP_IdleStart")+2; call _pressTick;
        [_medic getVariable ["ACME_DP_InPose",false],"prone pressure did not resume after two quiet seconds"] call _check;
        _moves=[]; (count _handlers-1) call _tick;
        [count _moves==1 && {{((_moves select 0) select 1)=="ACM_ProneContinuous"}},"resume requested kneeling hold"] call _check;
        // An exact expected-state comparison must not keep restarting the fallback.
        _animation="acm_pronecontinuous"; _moves=[];
        CBA_missionTime=CBA_missionTime+1; call _pressTick;
        [count _moves==0,"valid prone hold was treated as pose drift"] call _check;
        [_display] call ACME_fnc_installRmbCancelGuard;
        [_display,1] call _mouse; call _runCancel;
        [!(_medic getVariable ["ACME_DP_Active",true]),"right click left prone pressure active"] call _check;
        [!('MIDDLE' in _stances),"pressure set prone provider to crouch"] call _check;
        [((_moves select ((count _moves)-1)) select 1)=="AmovPpneMstpSnonWnonDnon","cancel returned to kneeling idle"] call _check;
    ''')


def test_pressure_can_adopt_prone_during_an_existing_kneeling_hold():
    execute(pressure_setup() + '''
        ["leftarm"] call _start;
        _providerStance="PRONE"; _animation="amovppnemstpsnonwnondnon"; _moves=[];
        CBA_missionTime=CBA_missionTime+1; call _pressTick;
        [(_medic getVariable ["ACME_DP_Pose",""])=="ACM_ProneContinuous","live prone stance did not replace kneeling target"] call _check;
        (count _handlers-1) call _tick;
        [((_moves select 0) select 1)=="ACM_ProneContinuous","live stance change pulled provider back up"] call _check;
    ''')


@pytest.mark.parametrize("local_only", [False, True], ids=["patient-default", "provider"])
def test_held_retry_adopts_late_prone_only_for_explicit_provider_requests(local_only):
    execute(pressure_setup() + f'''
        [_medic,"ACME_DirectPressureHold",1.1,1,{str(local_only).lower()}] call ACME_fnc_doAnimHeld;
        _providerStance="PRONE"; _animation="other";
        0 call _tick;
        [((_moves select 0) select 1)=="{'ACM_ProneContinuous' if local_only else 'ACME_DirectPressureHold'}",
            "held retry ignored provider posture or changed patient choreography"] call _check;
        [(((_handlers select 0) select 1) select 1)=="{'ACM_ProneContinuous' if local_only else 'ACME_DirectPressureHold'}",
            "held retry did not retain expected state"] call _check;
    ''')


@pytest.mark.parametrize("animation,expected", [
    ("acm_pronecontinuous", "ACM_ProneContinuous"),
    ("amovppnemstpsnonwnondnon", "ACM_ProneContinuous"),
    ("amovppnemstpsnonwnondnon_amovpknlmstpsnonwnondnon", "ACME_DirectPressureHold"),
])
def test_undefined_engine_stance_uses_current_known_prone_state(animation, expected):
    execute(pressure_setup() + f'''
        _providerStance="UNDEFINED"; _animation="{animation}";
        private _resolved=[_medic,"ACME_DirectPressureHold"] call ACME_fnc_providerAnimation;
        [_resolved=="{expected}","undefined stance lost posture or misread prone-to-kneel transition"] call _check;
    ''')


def test_pressure_restarted_from_custom_prone_state_captures_prone_cleanup():
    execute(pressure_setup() + '''
        _providerStance="UNDEFINED"; _animation="acm_pronecontinuous";
        ["leftarm"] call _start;
        [_medic getVariable ["ACME_DP_PoseProne",false],"custom-prone entry lost captured posture"] call _check;
        _animation="interpolating";
        [true,_medic] call ACME_fnc_directPressureStop;
        [((_moves select ((count _moves)-1)) select 1)=="AmovPpneMstpSnonWnonDnon","custom-prone cancel forced kneel"] call _check;
    ''')


def test_prone_head_cancel_preserves_posture_and_old_release_cannot_touch_restart():
    execute(head_cancel_setup() + '''
        _providerStance="PRONE";
        [_medic,"elevate"] call ACME_fnc_headElevMedicSeq;
        call ACME_fnc_headElevateCancelSeq;
        [((_moves select ((count _moves)-1)) select 1)=="AmovPpneMstpSnonWnonDnon","head cancel returned to crouch"] call _check;
        [!('MIDDLE' in _stances),"head cancel forced prone provider up"] call _check;
        private _old=_waits select 0;
        [_medic,"lower"] call ACME_fnc_headElevMedicSeq;
        _moves=[]; _stances=[];
        [_old] call _deliver;
        [count _moves==0 && {count _stances==0},"old head cancel changed replacement episode"] call _check;
    ''')


@pytest.mark.parametrize("mode", ["elevate", "lower", "contactexit"])
def test_prone_head_provider_sequence_completes_without_waiting_on_kneeling_edges(mode):
    execute(head_setup() + f'''
        _providerStance="PRONE";
        [_medic,"{mode}"] call ACME_fnc_headElevMedicSeq;
        private _job=_jobs select 0;
        CBA_missionTime=10.2; [_job] call _tick;
        _anim="amovppnemstpsnonwnondnon"; [_job] call _tick;
    ''' + ('''
        _anim="acm_pronecontinuous"; [_job] call _tick;
        CBA_missionTime=11.61; [_job] call _tick;
        _anim="amovppnemstpsnonwnondnon"; [_job] call _tick;
    ''' if mode != "contactexit" else '') + '''
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"prone sequence waited for nonexistent Putdown transition"] call _check;
        [count _removed==1,"prone sequence leaked provider worker"] call _check;
        [!('MIDDLE' in _stances),"prone head procedure forced crouch"] call _check;
        [(_moves findIf {((_x select 1) find "Pknl")>=0})<0,"prone provider received kneeling RTM"] call _check;
        [_waits select 0] call _deliver;
        [(_stances select ((count _stances)-1))=="AUTO","prone completion retained stance lock"] call _check;
    ''')


def test_prone_manual_head_support_freezes_and_exits_to_prone():
    execute(manual_support_setup() + '''
        _stance="PRONE";
        [_medic,_patient,"head","support",true] call ACME_fnc_headElevHoldStart;
        private _id=_medic getVariable ["ACME_headElev_manualAnimPFH",-1];
        [_id] call _poseTick;
        _animation="acm_pronecontinuous"; [_id] call _poseTick;
        private _holdPackets=_events select {(_x select 0)=="ACME_treatmentPoseSync" && {((_x select 1) select 2)=="hold"}};
        [count _holdPackets==1 && {_speed==0},"prone manual support did not freeze"] call _check;
        [(((_holdPackets select 0) select 1) select 3)=="ACM_ProneContinuous","observer received kneeling manual hold"] call _check;
        ACM_core_ContinuousAction_Active=false;
        (_continuous select 0) call (_continuous select 2);
        [_waits select 0] call _deliver;
        [!('MIDDLE' in _positions),"manual support exit forced crouch"] call _check;
        [(_positions select ((count _positions)-1))=="AUTO","manual support retained stance lock"] call _check;
    ''')


def test_head_provider_adopts_prone_during_weapon_prep_and_waits_for_work_phase():
    execute(head_setup() + '''
        [_medic,"elevate"] call ACME_fnc_headElevMedicSeq;
        private _job=_jobs select 0;
        _providerStance="PRONE";
        CBA_missionTime=10.2; [_job] call _tick;
        _anim="amovppnemstpsnonwnondnon"; [_job] call _tick;
        // The engine can still show entry idle for several frames. It is not
        // evidence that the requested medical work and return already completed.
        [_job] call _tick;
        [((_job select 2) select 7)==1,"prone entry idle skipped medical work"] call _check;
        _anim="acm_pronecontinuous"; [_job] call _tick;
        CBA_missionTime=11.61; [_job] call _tick;
        _anim="amovppnemstpsnonwnondnon"; [_job] call _tick;
        [!(_medic getVariable ["ACME_headElev_seqActive",true]),"late-prone sequence stranded provider"] call _check;
        [!('MIDDLE' in _stances),"late-prone sequence forced crouch"] call _check;
        [(_moves findIf {((_x select 1) find "Pknl")>=0})<0,"late-prone sequence used cached kneeling state"] call _check;
    ''')


@pytest.mark.parametrize("after_freeze", [False, True])
def test_manual_support_adopts_prone_and_advances_already_published_pose_episode(after_freeze):
    execute(manual_support_setup() + '''
        [_medic,_patient,"head","support",true] call ACME_fnc_headElevHoldStart;
        private _id=_medic getVariable ["ACME_headElev_manualAnimPFH",-1];
        private _oldEpoch=_medic getVariable "ACME_headElev_manualPoseEpoch";
    ''' + ('''
        [_id] call _poseTick;
        _animation="ainvpknlmstpsnonwnondnon_putdown"; [_id] call _poseTick;
        [_speed==0,"initial manual sample did not freeze"] call _check;
    ''' if after_freeze else '') + '''
        _stance="PRONE"; _positions=[];
        [_id] call _poseTick;
        _animation="acm_pronecontinuous"; [_id] call _poseTick;
        private _newEpoch=_medic getVariable "ACME_headElev_manualPoseEpoch";
        private _holds=_events select {(_x select 0)=="ACME_treatmentPoseSync" && {((_x select 1) select 2)=="hold"}};
        private _last=(_holds select ((count _holds)-1)) select 1;
        [(_last select 3)=="ACM_ProneContinuous" && {_speed==0},"late-prone support did not publish prone freeze"] call _check;
    ''' + ('''
        [_newEpoch>_oldEpoch && {(_last select 1)==_newEpoch},"changed frozen pose reused cached observer epoch"] call _check;
    ''' if after_freeze else '''
        [_newEpoch==_oldEpoch,"unpublished entry needlessly replaced pose episode"] call _check;
    ''') + '''
        [!('MIDDLE' in _positions),"late-prone support requested crouch"] call _check;
    ''')


def hang_source(name, text=None):
    s = read(name) if text is None else text
    s = re.sub(r'\bstance (_medic|_m)\b', '_stance', s)
    s = re.sub(r'\banimationState (_medic|_m)\b', '_animation', s)
    s = re.sub(r'\bobjectParent (_medic|_m)\b', 'objNull', s)
    s = re.sub(r'_(?:medic|m) setUnitPos ([^;]+);', r'_stances pushBack (\1);', s)
    s = re.sub(r'_(?:medic|m) (?:enableAI|selectWeapon) "[^"]*";', '', s)
    s = s.replace('serverTime', 'CBA_missionTime')
    return adapt(s)


def hang_setup():
    s = '''
        private _stance="PRONE"; private _animation="acm_pronecontinuous";
        private _stances=[]; private _held=[]; private _restores=0; private _stops=0;
        missionNamespace setVariable ["ACME_hang_removeWeapon",false];
        ACME_fnc_medicAnimationPrep={0};
        ACME_fnc_doAnimHeld={_held pushBack _this;};
        ACME_fnc_doAnim={_moves pushBack _this;};
        ACME_fnc_hangBagRestoreWeapons={_restores=_restores+1;};
        ACME_fnc_hangBagInputLock={}; ACME_fnc_hangBagHint={};
        ACME_fnc_providerStanceOwned={false};
        ACME_fnc_clinicalEpoch={0}; ACME_fnc_ownerDispatch={};
        CBA_fnc_removeGlobalEventJIP={};
        CBA_fnc_removePerFrameHandler={_removed pushBack (_this select 0);};
        private _activate={
            _medic setVariable ["ACME_hang_Active",true];
            _medic setVariable ["ACME_hang_Claimed",true];
            _medic setVariable ["ACME_hang_Start",10];
            _medic setVariable ["ACME_hang_PFH",7];
            _medic setVariable ["ACME_hang_Patient",_patient];
            _medic setVariable ["ACME_hang_ClaimOwner",7];
            _medic setVariable ["ACME_hang_ClaimEpoch",0];
            _medic setVariable ["ACME_hang_ClaimRequestedAt",10];
            _medic setVariable ["ACME_hang_ClaimAckAt",10];
        };
        private _deliver={params ["_job"]; (_job select 1) call (_job select 0);};
    '''
    for name in ("providerAnimation", "hangBagPrep", "hangBagPrepStop", "hangBagTick", "hangBagStop"):
        s += f'ACME_fnc_{name}={{' + hang_source(name) + '};'
    activation = read("hangBagActivate").split('private _prone =', 1)[1].split('// the patient-side rope helper', 1)[0]
    s += 'private _presentation={' + hang_source("hangBagActivate", 'params ["_medic"]; private _prone ='+activation) + '};'
    return s


def test_prone_hang_bag_prep_hold_tick_and_cancel_never_raise_provider():
    execute(hang_setup() + '''
        [_medic] call ACME_fnc_hangBagPrep;
        [count _held==1 && {((_held select 0) select 1)=="ACM_ProneContinuous"},"prone hang prep raised provider"] call _check;
        [count _waits==0,"prone prep scheduled kneel transition"] call _check;
        call _activate; [_medic] call _presentation;
        [(_medic getVariable ["ACME_hang_Pose",""])=="ACM_ProneContinuous","hang expected state remained kneeling"] call _check;
        CBA_missionTime=11; [[_medic,_patient],7] call ACME_fnc_hangBagTick;
        [_medic getVariable ["ACME_hang_Active",false],"valid prone bag hold cancelled"] call _check;
        [true,_medic] call ACME_fnc_hangBagStop;
        [!(_medic getVariable ["ACME_hang_Active",true]),"bag cancel failed"] call _check;
        [!('MIDDLE' in _stances),"hang workflow forced crouch"] call _check;
        [((_moves select ((count _moves)-1)) select 1)=="AmovPpneMstpSnonWnonDnon","bag exit requested kneeling RTM"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '_medic setVariable ["ACME_hang_Start",11];',
    '_medic setVariable ["ACME_providerLocalityEpoch",1];',
    '_medic setVariable ["ACME_hang_Active",false];',
])
def test_delayed_bag_hold_repair_cannot_touch_new_or_transferred_episode(change):
    execute(hang_setup() + '''
        call _activate; [_medic] call _presentation;
        [count _waits==1,"activation did not schedule bounded repair"] call _check;
        _animation="other"; _moves=[];
    ''' + change + '''
        [_waits select 0] call _deliver;
        [count _moves==0,"old bag repair modified replacement episode"] call _check;
    ''')


def test_bag_prep_delayed_by_standing_entry_adopts_prone_before_hold():
    execute(hang_setup() + '''
        _stance="STAND"; _animation="standing-idle"; [_medic] call ACME_fnc_hangBagPrep;
        [count _waits==1,"standing entry failed to schedule work pose"] call _check;
        _stance="PRONE"; _held=[];
        [_waits select 0] call _deliver;
        [count _held==1 && {((_held select 0) select 1)=="ACM_ProneContinuous"},"late prep replayed cached kneeling hold"] call _check;
        [_medic getVariable ["ACME_hang_Prone",false],"late prone prep was not captured for cleanup"] call _check;
    ''')


def test_bag_cancel_uses_actual_prone_pose_before_delayed_capture_catches_up():
    execute(hang_setup() + '''
        _stance="UNDEFINED"; _animation="acm_pronecontinuous";
        _medic setVariable ["ACME_hang_Prone",false];
        call _activate;
        [true,_medic] call ACME_fnc_hangBagStop;
        [!('MIDDLE' in _stances),"bag cancel trusted stale stance capture and raised provider"] call _check;
        [((_moves select ((count _moves)-1)) select 1)=="AmovPpneMstpSnonWnonDnon","bag cancel lost actual prone posture"] call _check;
    ''')
