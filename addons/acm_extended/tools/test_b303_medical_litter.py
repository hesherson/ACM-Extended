"""Registered-only server removal and finite kneel/Putdown pickup choreography.

Native object handles/positions, input, rendering and transport are explicit engine boundaries;
production registry selection, claims, replay checks and animation transitions execute in SQF-VM.
"""
import re,subprocess
import pytest
from test_menu_death_lifecycle import ROOT,read,adapt,execute
from test_b156_procedure_supplies import primitives
BASE='d5c8293a2f92f33f53bb4d1ad985711776a3b9c1'


def function(name):
    s=read(name).replace('diag_tickTime','_clock').replace('clientOwner','_clientOwner')
    s=s.replace('isServer','_server').replace('alive _unit','_unitAlive').replace('local _unit','_unitLocal')
    s=s.replace('owner _unit','(_unit getVariable ["owner",7])').replace('netId _unit','(_unit getVariable ["net","unit-a"])')
    s=s.replace('_unit isKindOf "CAManBase"','_isMan').replace('objectParent _unit','_parent')
    s=s.replace('stance _unit','_stance').replace('getPosASL _unit','_position')
    s=s.replace('isSimpleObject _object','(_object in _simple)')
    s=s.replace('_object isEqualType objNull','_object isEqualType 0')
    s=s.replace('_unit distance _object','(_position vectorDistance (_positions get _object))')
    s=s.replace('deleteVehicle _x','_deleted pushBack _x')
    s=s.replace('animationState _unit','_animation').replace('currentWeapon _unit','_weapon')
    s=s.replace('inputAction _x','_input')
    s=s.replace('_unit setUnitPos','_stances pushBack')
    s=s.replace('(findDisplay 46) displayRemoveEventHandler ["KeyDown",_key]','_removedKeys pushBack _key')
    s=s.replace('(findDisplay 46) displayAddEventHandler ["KeyDown",','(["key",')
    if '(["key",' in s:s=s.replace('}];\n_unit setVariable ["ACME_litterKey"','}] call _keyCreate);\n_unit setVariable ["ACME_litterKey"')
    return 'ACME_fnc_'+name+'={'+primitives(adapt(s))+'};'


def setup(*extra):
    return r'''
      private _clock=10;private _clientOwner=7;private _server=true;private _isMan=true;
      private _unitAlive=true;private _unitLocal=true;private _parent=objNull;private _stance="CROUCH";
      private _position=[0,0,0];private _animation="AmovPknlMstpSnonWnonDnon";private _weapon="";private _input=0;
      private _positions=createHashMap;private _simple=[];private _deleted=[];private _replies=[];
      private _stances=[];private _removedKeys=[];private _sent=[];private _busy=false;private _prep=0;
      private _mapDefault={params["_m","_a"];_a params["_k","_d"];if(_k in _m)then{_m get _k}else{_d}};
      private _keyCreate={99};
      _medic setVariable ["net","unit-a"];_medic setVariable ["owner",7];
      _medic setVariable ["ACE_isUnconscious",false];
      _medic setVariable ["ACME_providerLocalityEpoch",3];_medic setVariable ["ACME_treatmentPoseEpoch",4];_medic setVariable ["ACME_providerTreatmentEpoch",5];
      _medic setVariable ["ACME_litterCollect",[]];
      _patient setVariable ["net","unit-b"];_patient setVariable ["owner",8];
      missionNamespace setVariable ["ACME_litterClaims",createHashMap];
      missionNamespace setVariable ["ACME_litterRemoved",[]];
      missionNamespace setVariable ["ace_medical_treatment_litterObjects",[]];
      missionNamespace setVariable ["ACME_interventionAnimations",true];
      ace_common_fnc_isPlayer={true};
      ACME_fnc_providerStanceOwned={_busy};
      ACME_fnc_medicAnimationPrep={_prep};
      ACME_fnc_providerAnimation={_this select 1};
      ACME_fnc_doAnim={_moves pushBack (_this select 1);};
      CBA_fnc_ownerEvent={_replies pushBack _this;};
      CBA_fnc_serverEvent={_sent pushBack _this;};
    '''+''.join(function(n) for n in ['medicalLitterCanCollect','medicalLitterServer',*extra])


def registry():
    return r'''
      _simple=[1,2,3];_positions set [1,[1,0,0]];_positions set [2,[1.5,0,0]];_positions set [3,[10,0,0]];
      // 4 is usable dropped equipment and is intentionally absent from ACE's registry.
      _positions set [4,[.5,0,0]];
      missionNamespace setVariable ["ace_medical_treatment_litterObjects",[[1,11],[2,22],[3,33]]];
    '''


def claim():
    return r'''
      ["request",_medic,7,"request-a",""] call ACME_fnc_medicalLitterServer;
      private _grant=((_replies select ((count _replies)-1)) select 1) select 3;
    '''


def test_any_player_can_collect_only_registered_litter_preserving_other_entries_and_timestamps():
    execute(setup()+registry()+claim()+r'''
      [count _deleted==0,"claim deleted before kneeling"] call _check;
      _clock=13;["commit",_medic,7,"request-a",_grant] call ACME_fnc_medicalLitterServer;
      [_deleted isEqualTo [1,2],"collection touched unregistered or distant equipment"] call _check;
      [(missionNamespace getVariable "ace_medical_treatment_litterObjects") isEqualTo [[1,11],[2,22],[3,33]],"ACE registry ownership/order/timestamps changed"] call _check;
      [!(_deleted isEqualTo [4]),"usable supply was treated as litter"] call _check;
    ''')


@pytest.mark.parametrize('change',['_server=false;','_unitAlive=false;','_parent=missionNamespace;','_isMan=false;','_medic setVariable ["owner",8];','_medic setVariable ["ACE_isUnconscious",true];'])
def test_invalid_server_claim_cannot_delete_or_grant(change):
    execute(setup()+registry()+change+r'''
      ["request",_medic,7,"request-a",""] call ACME_fnc_medicalLitterServer;
      [count _deleted==0 && {count _replies==0},"invalid provider obtained collection grant"] call _check;
    ''')


@pytest.mark.parametrize('change',[
 '_clock=10.5;', '_clock=26;', '_position=[1,0,0];', '_parent=missionNamespace;', '_unitAlive=false;',
 '_medic setVariable ["ACE_isUnconscious",true];', '_medic setVariable ["owner",8];', '_grant="forged";',
])
def test_commit_rechecks_time_movement_vehicle_life_locality_and_capability(change):
    execute(setup()+registry()+claim()+'_clock=13;'+change+r'''
      ["commit",_medic,7,"request-a",_grant] call ACME_fnc_medicalLitterServer;
      [count _deleted==0 && {count (missionNamespace getVariable "ace_medical_treatment_litterObjects")==3},"invalid/early/stale commit removed litter"] call _check;
    ''')


def test_live_membership_and_distance_are_rechecked_after_ace_cleanup_and_new_litter():
    execute(setup()+registry()+claim()+r'''
      missionNamespace setVariable ["ace_medical_treatment_litterObjects",[[2,22],[3,33],[4,44]]];
      _simple pushBack 4;_positions set [2,[1,0,4]];
      _clock=13;["commit",_medic,7,"request-a",_grant] call ACME_fnc_medicalLitterServer;
      [count _deleted==0,"collection removed new, unclaimed or vertically distant litter"] call _check;
      [(missionNamespace getVariable "ace_medical_treatment_litterObjects") isEqualTo [[2,22],[3,33],[4,44]],"collection rebuilt unrelated registry entries"] call _check;
    ''')


def test_two_collectors_duplicate_entries_and_replayed_commits_delete_each_object_once():
    execute(setup()+registry()+r'''
      missionNamespace setVariable ["ace_medical_treatment_litterObjects",[[1,11],[1,12],[2,22],[3,33]]];
    '''+claim()+r'''
      ["request",_patient,8,"request-b",""] call ACME_fnc_medicalLitterServer;
      private _b=((_replies select 1) select 1) select 3;
      _clock=13;["commit",_medic,7,"request-a",_grant] call ACME_fnc_medicalLitterServer;
      ["commit",_patient,8,"request-b",_b] call ACME_fnc_medicalLitterServer;
      ["commit",_medic,7,"request-a",_grant] call ACME_fnc_medicalLitterServer;
      [_deleted isEqualTo [1,2],"overlapping/replayed collection deleted twice"] call _check;
      [(((_replies select 3) select 1) select 4)==0,"second collector claimed somebody else's removal"] call _check;
    ''')


def test_batch_is_bounded_and_never_scans_unregistered_world_objects():
    execute(setup()+r'''
      private _rows=[];for "_id" from 1 to 30 do {_rows pushBack [_id,_id];_simple pushBack _id;_positions set [_id,[1,0,0]];};
      missionNamespace setVariable ["ace_medical_treatment_litterObjects",_rows];
    '''+claim()+r'''
      _clock=13;["commit",_medic,7,"request-a",_grant] call ACME_fnc_medicalLitterServer;
      [count _deleted==25 && {({!((_x select 0) in _deleted)} count (missionNamespace getVariable "ace_medical_treatment_litterObjects"))==5},"batch exceeded its bounded pickup count"] call _check;
    ''')


def animation_setup():
    return setup('medicalLitterTick','medicalLitterFinish','medicalLitterAnimate','medicalLitterReply')+r'''
      _medic setVariable ["ACME_litterCollect",["request-a","grant-a","request",25,3]];
      [_medic,"request-a","grant-a"] call ACME_fnc_medicalLitterAnimate;
      private _run=(_handlers select 0) select 0;private _args=(_handlers select 0) select 1;
    '''


def test_kneel_then_observed_semifowler_reach_and_return_are_required_before_commit():
    execute(animation_setup()+r'''
      _clock=10.1;[_args,0] call _run;
      [(_moves select 0)=="AmovPknlMstpSnonWnonDnon","pickup did not kneel first"] call _check;
      _clock=10.3;[_args,0] call _run;
      [_moves select 1=="AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown","pickup used a different reach"] call _check;
      _animation="AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown";
      _clock=10.5;[_args,0] call _run;
      _animation="AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon";
      _clock=11;[_args,0] call _run;
      [count _sent==0,"pickup committed before return animation"] call _check;
      _animation="AmovPknlMstpSnonWnonDnon";_clock=12;[_args,0] call _run;
      _clock=12.2;[_args,0] call _run;
      [((_sent select 0) select 1 select 0)=="commit" && {!((_handlers select 0) select 2)},"completed pickup failed to commit or retire worker"] call _check;
      [_stances isEqualTo ["MIDDLE","AUTO"] && {_removedKeys isEqualTo [99]},"pickup stranded stance/input"] call _check;
    ''')


@pytest.mark.parametrize('change',[
 '_input=1;', '_position=[.6,0,0];', '_unitAlive=false;', '_unitLocal=false;', '_parent=missionNamespace;', '_busy=true;',
 '_medic setVariable ["ACE_isUnconscious",true];', '_medic setVariable ["ACME_providerLocalityEpoch",4];',
 '_medic setVariable ["ACME_providerTreatmentEpoch",6];', '_clock=21;', '_stance="PRONE";',
 'private _s=_medic getVariable "ACME_litterCollect";_s set [2,"cancel"];'
])
def test_cancel_or_new_treatment_cannot_commit_or_release_another_owner(change):
    execute(animation_setup()+change+r'''
      [_args,0] call _run;
      [((_sent select 0) select 1 select 0)=="cancel" && {(_medic getVariable "ACME_litterCollect") isEqualTo []},"interrupted pickup committed"] call _check;
      [!((_handlers select 0) select 2),"cancelled pickup leaked animation worker"] call _check;
      if (_busy || {!_unitLocal} || {!_unitAlive} || {_parent isNotEqualTo objNull} || {(_medic getVariable ["ACME_providerTreatmentEpoch",5])!=5} || {(_medic getVariable ["ACME_providerLocalityEpoch",3])!=3}) then {[count _stances==0,"cancel released a newer/seated/dead provider pose"] call _check;};
    ''')


def test_missing_authored_animation_times_out_instead_of_deleting_by_elapsed_time():
    execute(animation_setup()+r'''
      _clock=10.1;[_args,0] call _run;_clock=10.3;[_args,0] call _run;
      _clock=13;[_args,0] call _run;
      [count _sent==0,"missing reach was treated as successful pickup"] call _check;
      _clock=20;[_args,0] call _run;
      [((_sent select 0) select 1 select 0)=="cancel","missing animation did not time out"] call _check;
    ''')


def test_unsolicited_and_duplicate_grants_do_not_replay_animation():
    execute(setup('medicalLitterReply','medicalLitterAnimate','medicalLitterTick','medicalLitterFinish')+r'''
      [_medic,"unasked","grant","token",1] call ACME_fnc_medicalLitterReply;
      [count _handlers==0,"unsolicited grant animated player"] call _check;
      _medic setVariable ["ACME_litterCollect",["request-a","","request",25,3]];
      [_medic,"request-a","grant","token",1] call ACME_fnc_medicalLitterReply;
      [_medic,"request-a","grant","token",1] call ACME_fnc_medicalLitterReply;
      [count _handlers==1,"duplicate grant replayed pickup"] call _check;
    ''')


def test_scope_uses_the_same_animation_names_and_only_registered_litter_deletion():
    own=read('medicalLitterTick');semi=read('headElevMedicSeq')
    for name in ['AmovPknlMstpSnonWnonDnon','AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown','AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon']:
        assert name in own and name in semi
    new=''.join(read(n) for n in ['medicalLitterServer','medicalLitterCanCollect','registerMedicalLitterRuntime'])
    for forbidden in ['nearestObjects','allMissionObjects','nearestTerrainObjects','isMedic','medicalLevel','setUnitLoadout','addItem']:
        assert forbidden not in new
    assert 'ace_medical_treatment_litterObjects' in new
    for path in ['addons/gui','addons/circulation','addons/acm_extended/ui','frontend/medical-ui','addons/acm_extended/functions/fn_headElevMedicSeq.sqf','addons/acm_extended/functions/fn_headElevateStart.sqf','addons/acm_extended/functions/fn_headElevateStop.sqf']:
        assert not subprocess.check_output(['git','diff','--name-only',BASE,'--',path],cwd=ROOT).strip()


def test_cancelled_claim_and_duplicate_request_never_delete_and_do_not_lock_new_pickup():
    execute(setup()+registry()+claim()+r'''
      ["request",_medic,7,"request-a",""] call ACME_fnc_medicalLitterServer;
      [((_replies select 1) select 1 select 3)==_grant,"duplicate request changed its grant"] call _check;
      ["cancel",_medic,7,"request-a",_grant] call ACME_fnc_medicalLitterServer;
      _clock=13;["commit",_medic,7,"request-a",_grant] call ACME_fnc_medicalLitterServer;
      [count _deleted==0,"cancelled claim later deleted litter"] call _check;
      ["request",_medic,7,"request-new",""] call ACME_fnc_medicalLitterServer;
      [(((_replies select ((count _replies)-1)) select 1) select 2)=="grant","cancel stranded pickup reservation"] call _check;
    ''')


def test_new_pickup_skips_pending_deletes_without_mutating_ace_registry():
    execute(setup()+registry()+claim()+r'''
      _clock=13;["commit",_medic,7,"request-a",_grant] call ACME_fnc_medicalLitterServer;
      ["request",_medic,7,"request-new",""] call ACME_fnc_medicalLitterServer;
      [(((_replies select ((count _replies)-1)) select 1) select 2)=="none","deleted handles were offered a second time before native retirement"] call _check;
      [(missionNamespace getVariable "ace_medical_treatment_litterObjects") isEqualTo [[1,11],[2,22],[3,33]],"collector took ownership of ACE's bookkeeping"] call _check;
    ''')


def test_removed_or_superseded_unit_retires_only_its_own_worker_and_key():
    execute(animation_setup()+r'''
      _medic setVariable ["ACME_litterCollect",["new-request","new-token","anim",30,3]];
      [_args,0] call _run;
      [!((_handlers select 0) select 2) && {_removedKeys isEqualTo [99]},"stale callback leaked its own worker/key"] call _check;
      [((_medic getVariable "ACME_litterCollect") select 0)=="new-request" && {count _sent==0},"old callback cancelled a newer pickup"] call _check;
    ''')
    execute(animation_setup()+r'''
      _args set [0,objNull];[_args,0] call _run;
      [!((_handlers select 0) select 2) && {_removedKeys isEqualTo [99]},"despawn leaked animation/input worker"] call _check;
    ''')


def test_animation_setting_disabled_keeps_finite_time_without_forcing_a_pose():
    source=animation_setup().replace('[_medic,"request-a","grant-a"] call ACME_fnc_medicalLitterAnimate;','missionNamespace setVariable ["ACME_interventionAnimations",false];[_medic,"request-a","grant-a"] call ACME_fnc_medicalLitterAnimate;')
    execute(source+r'''
      _clock=11;[_args,0] call _run;[count _sent==0,"disabled presentation skipped collection time"] call _check;
      _clock=12.2;[_args,0] call _run;
      [count _moves==0 && {((_sent select 0) select 1 select 0)=="commit"},"disabled presentation forced authored animation"] call _check;
    ''')


def test_runtime_registers_one_equipment_self_action_for_every_player_and_no_idle_worker():
    execute(setup('registerMedicalLitterRuntime')+r'''
      private _registrations=[];private _created=[];private _installed=[];
      missionNamespace setVariable ["ACME_litterRegistered",false];
      CBA_fnc_addEventHandler={_registrations pushBack _this;};
      ace_interact_menu_fnc_createAction={_created pushBack _this;_this};
      ace_interact_menu_fnc_addActionToClass={_installed pushBack _this;};
      call ACME_fnc_registerMedicalLitterRuntime;call ACME_fnc_registerMedicalLitterRuntime;
      [count _registrations==2 && {count _created==1} && {count _installed==1} && {count _handlers==0},"runtime duplicated action/events or installed idle polling"] call _check;
      [((_installed select 0) select[0,3]) isEqualTo ["CAManBase",1,["ACE_SelfActions","ACE_Equipment"]],"pickup not available to ordinary player self equipment"] call _check;
    ''')


def test_authored_middle_putdown_state_requests_the_same_return_once():
    execute(animation_setup()+r'''
      _clock=10.1;[_args,0] call _run;_clock=10.3;[_args,0] call _run;
      _animation="AmovPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_Putdown";
      _clock=10.5;[_args,0] call _run;
      _animation="AinvPknlMstpSnonWnonDnon_Putdown";
      _clock=10.8;[_args,0] call _run;
      [count _moves==3 && {(_moves select 2)=="AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon"} && {count _sent==0},"middle Putdown was mistaken for interruption or replayed reach"] call _check;
      _animation="AinvPknlMstpSnonWnonDnon_Putdown_AmovPknlMstpSnonWnonDnon";_clock=11;[_args,0] call _run;
      _animation="AmovPknlMstpSnonWnonDnon";_clock=12;[_args,0] call _run;
      _clock=12.2;[_args,0] call _run;
      [((_sent select 0) select 1 select 0)=="commit","authored middle/return path never collected litter"] call _check;
    ''')


@pytest.mark.parametrize('phase,until,epoch,owned',[("anim",20,3,True),("anim",9,3,False),("anim",20,4,False),("request",20,3,False),("commit",20,3,False)])
def test_only_live_local_animation_protects_stance_and_continuation_sees_other_treatments(phase,until,epoch,owned):
    execute(setup()+function('providerStanceOwned')+f'''
      _medic setVariable ["ACME_litterCollect",["request-a","grant-a","{phase}",{until},{epoch}]];
      [[_medic] call ACME_fnc_providerStanceOwned isEqualTo {str(owned).lower()},"expired/pending/locality-stale pickup retained stance"] call _check;
      [!([_medic,false,true] call ACME_fnc_providerStanceOwned),"continuation mistook itself for another owner"] call _check;
      _medic setVariable ["ACME_treatmentPoseState",["new-care"]];
      [[_medic,false,true] call ACME_fnc_providerStanceOwned,"ignoring pickup also concealed newer treatment"] call _check;
    ''')


def test_holster_settle_is_observed_before_kneeling_or_reaching():
    source=animation_setup().replace('[_medic,"request-a","grant-a"] call ACME_fnc_medicalLitterAnimate;','_prep=1;_weapon="pistol";[_medic,"request-a","grant-a"] call ACME_fnc_medicalLitterAnimate;')
    execute(source+r'''
      _clock=10.3;[_args,0] call _run;_clock=11.2;[_args,0] call _run;
      [count _moves==0,"pickup animated underneath selected weapon"] call _check;
      _weapon="";_animation="AmovPknlMstpSrasWpstDnon";_clock=11.3;[_args,0] call _run;
      [count _moves==0,"logical empty hands skipped visible pistol holster"] call _check;
      _animation="AmovPknlMstpSnonWnonDnon";_clock=11.4;[_args,0] call _run;
      [count _moves==1,"settled empty hands failed to enter kneel"] call _check;
    ''')


def test_authoritative_rejection_clears_pending_commit_without_reanimating():
    execute(setup('medicalLitterReply','medicalLitterFinish')+r'''
      _medic setVariable ["ACME_litterCollect",["request-a","grant-a","commit",25,3]];
      [_medic,"request-a","cancelled","grant-a",0] call ACME_fnc_medicalLitterReply;
      [(_medic getVariable "ACME_litterCollect") isEqualTo [] && {count _moves==0},"server rejection stranded request or replayed pose"] call _check;
    ''')


@pytest.mark.parametrize('registry', ['[]','"bad registry"','["bad entry",[],[4,44],[1,11]]'])
def test_empty_malformed_and_non_simple_registry_data_fail_closed(registry):
    execute(setup()+r'''
      _simple=[1];_positions set [1,[1,0,0]];_positions set [4,[.5,0,0]];
    '''+f'missionNamespace setVariable ["ace_medical_treatment_litterObjects",{registry}];'+r'''
      ["request",_medic,7,"request-a",""] call ACME_fnc_medicalLitterServer;
      if (count _replies>0 && {(((_replies select 0) select 1) select 2)=="grant"}) then {
          private _token=((_replies select 0) select 1) select 3;
          _clock=13;["commit",_medic,7,"request-a",_token] call ACME_fnc_medicalLitterServer;
          [_deleted isEqualTo [1],"malformed/non-simple registry entry broadened deletion"] call _check;
      } else {[count _deleted==0,"bad registry deleted a world object"] call _check;};
    ''')
