"""Run AAJT provider lifetimes and AED chest-access event custody in production SQF.

Arma RTM rendering, engine stance/weapons, native progress UI and transport remain
explicit boundaries. Actual pose/controller/token/cancellation code executes.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_historical_pose_lifecycle import setup as pose_setup, pose_source
from test_chestseal_preparation_progress import setup as patient_setup, function
from test_b65_zone3_reboa_smart_bandage import cfg_class


AAJT = [(f"ACME_{operation}AAJT_{site}", part)
        for operation in ("Apply", "Remove")
        for site, part in (("Inguinal", "LeftLeg"), ("Axilla", "LeftArm"), ("Zone3", "Body"))]


def setup():
    code = pose_setup()
    for name in ("aajtTreatmentStart", "aajtTreatmentFinish"):
        code += f"ACME_fnc_{name}={{" + pose_source(name) + "};"
    native = (ROOT / "addons/core/functions/fnc_treatmentNative.sqf").read_text()
    # Execute exactly the production callback-start and binding block; ACE progress UI is the boundary.
    start = native.index("_callbackArgs call _callbackStart;")
    end = native.index('["ace_treatmentStarted"', start)
    code += 'private _bind={' + adapt(native[start:end]) + '};'
    return code


def begin(classname="ACME_ApplyAAJT_Inguinal", part="LeftLeg"):
    return f'''
        private _classname="{classname}";
        private _callbackArgs=[_medic,_patient,"{part}",_classname,objNull,"",false];
        private _callbackStart=ACME_fnc_aajtTreatmentStart;
        call _bind;
        private _record=+(_medic getVariable ["ACME_aajtTreatment",[]]);
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_state select 5;
        _animation=toLower (_state select 2); [_id] call _poseTick;
    '''


def success_callback(classname):
    body=cfg_class((ROOT/'addons/acm_extended/config.cpp').read_text(), classname)
    callback=re.search(r'callbackSuccess\s*=\s*"([^"]+)";',body)
    assert callback, classname
    return '''
        private _clinical=[];
        ACME_fnc_aajtApply={_clinical pushBack ["apply",+_this]; true};
        ACME_fnc_aajtRemove={_clinical pushBack ["remove",+_this]; true};
        private _successCallback={'''+callback[1]+'''};
    '''


@pytest.mark.parametrize("classname,part", AAJT)
def test_duplicate_success_callback_commits_clinical_action_only_once(classname,part):
    execute(setup()+begin(classname,part)+success_callback(classname)+'''
        _callbackArgs call _successCallback;
        [count _clinical==1,"valid successful action did not reach clinical commit"] call _check;
        _callbackArgs call _successCallback;
        [count _clinical==1,"duplicate successful callback repeated clinical action"] call _check;
    ''')


@pytest.mark.parametrize("classname,part", AAJT)
def test_stale_success_callback_cannot_apply_or_remove_aajt(classname,part):
    execute(setup()+begin(classname,part)+success_callback(classname)+'''
        private _old=+_callbackArgs;
        _callbackArgs resize 7; call _bind;
        private _new=+(_medic getVariable ["ACME_aajtTreatment",[]]);
        _old call _successCallback;
        [count _clinical==0,"stale successful callback changed clinical AAJT state"] call _check;
        [(_medic getVariable ["ACME_aajtTreatment",[]]) isEqualTo _new,"stale callback retired current action"] call _check;
        _callbackArgs call _successCallback;
        [count _clinical==1,"current successful action was blocked after stale callback"] call _check;
    ''')


@pytest.mark.parametrize("classname,part", AAJT)
def test_failed_provider_presentation_does_not_block_valid_clinical_success(classname,part):
    execute(setup()+success_callback(classname)+f'''
        _blocked=true;
        private _classname="{classname}";
        private _callbackArgs=[_medic,_patient,"{part}",_classname,objNull,"",false];
        private _callbackStart=ACME_fnc_aajtTreatmentStart;
        call _bind;
        [((_medic getVariable ["ACME_aajtTreatment",[]]) select 4)==-1 && {{count _moves==0}},"fixture did not reject provider presentation"] call _check;
        _callbackArgs call _successCallback;
        [count _clinical==1,"failed animation prevented valid clinical treatment"] call _check;
        _callbackArgs call _successCallback;
        [count _clinical==1,"failed-animation action committed twice"] call _check;
    ''')


@pytest.mark.parametrize("classname,part", AAJT)
def test_each_aajt_action_runs_until_actual_native_completion_not_a_gesture_timeout(classname, part):
    execute(setup() + begin(classname, part) + '''
        [(_callbackArgs select 7)==(_record select 0),"native callback did not bind exact episode"] call _check;
        [(_state select 2)=="ACME_JunctionalWork" && {_speed==1.5},"wrong medic4 work or rate"] call _check;
        [count _waits==0,"AAJT scheduled an independent gesture cutoff"] call _check;
        {CBA_missionTime=_x; [_id] call _poseTick;} forEach [12.4,14,30,50,80];
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo _state,"clinical timer outlived AAJT pose"] call _check;
        [count _moves==1 && {_preps==1},"running work replayed or holstered repeatedly"] call _check;
        [_callbackArgs,true] call ACME_fnc_aajtTreatmentFinish;
        [(_medic getVariable ["ACME_treatmentPoseState",[1]]) isEqualTo [],"success retained work"] call _check;
        [(_medic getVariable ["ACME_aajtTreatment",[1]]) isEqualTo [],"success retained episode"] call _check;
        [(_moves select (count _moves-1)) isEqualTo [_medic,"AmovPknlMstpSnonWnonDnon",1],"exit drew a weapon"] call _check;
    ''')


@pytest.mark.parametrize("success", [False, True])
def test_old_callback_cannot_clear_replacement_or_stop_new_pose(success):
    execute(setup() + begin() + '''
        private _old=+_callbackArgs;
        _callbackArgs resize 7;
        call _bind;
        private _new=+(_medic getVariable ["ACME_aajtTreatment",[]]);
        private _newPose=+(_medic getVariable ["ACME_treatmentPoseState",[]]);
        _events=[]; _moves=[];
    ''' + f'[_old,{str(success).lower()}] call ACME_fnc_aajtTreatmentFinish;' + '''
        [(_medic getVariable ["ACME_aajtTreatment",[]]) isEqualTo _new,"stale callback cleared newer record"] call _check;
        [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo _newPose,"stale callback stopped replacement pose"] call _check;
        [count _events==0 && {count _moves==0},"stale callback dispatched clinical clear or animation"] call _check;
    ''')


@pytest.mark.parametrize("stance,animation", [("PRONE", "amovppnemstpsnonwnondnon"), ("UNDEFINED", "acm_pronecontinuous")])
def test_aajt_prone_safe_through_full_work_and_cancellation(stance, animation):
    execute(setup() + f'_stance="{stance}"; _animation="{animation}";' + begin() + '''
        [(_state select 2)=="ACM_ProneContinuous" && {(_state select 20)},"AAJT raised prone provider"] call _check;
        CBA_missionTime=35; [_id] call _poseTick;
        [_callbackArgs,false] call ACME_fnc_aajtTreatmentFinish;
        [(_positions find "MIDDLE")<0,"AAJT entry/exit requested crouch"] call _check;
        [(_moves select (count _moves-1)) isEqualTo [_medic,"AmovPpneMstpSnonWnonDnon",1],"AAJT prone exit unsupported"] call _check;
        [{(_x param [1,""]) isEqualTo "aajtApplying" && {!((_x select 2) select 1)}} count _events==1,"cancel did not clear owner applying marker exactly once"] call _check;
    ''')


def test_finite_engine_exit_reenters_work_only_after_state_drift_without_reholster():
    execute(setup() + begin() + '''
        _moves=[]; CBA_missionTime=17; [_id] call _poseTick;
        [count _moves==0,"ongoing animation restarted"] call _check;
        _animation="amovpknlmstpsnonwnondnon"; [_id] call _poseTick;
        [count _moves==1 && {_preps==1},"exited engine cycle did not resume work or reholstered"] call _check;
        CBA_missionTime=17.1; [_id] call _poseTick;
        [count _moves==1,"entry request was spammed"] call _check;
    ''')


@pytest.mark.parametrize("weapon", ["rifle", "pistol"])
def test_real_weapon_preflight_stows_once_before_aajt_and_never_redraws(weapon):
    prep=pose_source("medicAnimationPrep").replace('handgunWeapon _medic','"pistol"')
    # Avoid shadowing the harness's engine currentWeapon stand-in with this helper's local snapshot.
    prefix,tail=prep.split('private _weapon = _weapon;',1)
    prep=prefix+'private _selectedWeapon = _weapon;'+re.sub(r'\b_weapon\b','_selectedWeapon',tail)
    execute(setup() + 'ACME_fnc_medicAnimationPrep={' + prep + '};' + f'''
        _weapon="{weapon}"; _animation="amovpknlmstpsrasw{weapon}dnon";
        private _holsters=0;
        ace_weaponselect_fnc_putWeaponAway={{_holsters=_holsters+1; _weapon=""; _animation="weapon_stowing";}};
        private _classname="ACME_ApplyAAJT_Inguinal";
        private _callbackArgs=[_medic,_patient,"LeftLeg",_classname,objNull,"",false];
        private _callbackStart=ACME_fnc_aajtTreatmentStart;
        call _bind;
        private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
        private _id=_state select 5;
        [count _moves==0 && {{_holsters==1}},"medical work preceded visible weapon stow"] call _check;
        CBA_missionTime=10.4; [_id] call _poseTick;
        [count _moves==0 && {{_holsters==1}},"stow was repeated or work entered under visible weapon"] call _check;
        _animation="amovpknlmstpsnonwnondnon"; CBA_missionTime=10.8; [_id] call _poseTick;
        [count _moves==1 && {{_holsters==1}},"ready empty hands did not enter medical work"] call _check;
        _animation="acme_junctionalwork"; [_id] call _poseTick;
        _animation="amovpknlmstpsnonwnondnon"; CBA_missionTime=30; [_id] call _poseTick;
        [_callbackArgs,true] call ACME_fnc_aajtTreatmentFinish;
        [_weapon=="" && {{_holsters==1}},"work/exit repeated weapon swap or redrew weapon"] call _check;
    ''')


def test_matching_finish_cannot_stop_a_later_non_aajt_pose():
    execute(setup() + begin() + '''
        private _newEpoch=[_medic,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;
        _moves=[]; [_callbackArgs,false] call ACME_fnc_aajtTreatmentFinish;
        [((_medic getVariable ["ACME_treatmentPoseState",[]]) select 0)==_newEpoch && {count _moves==0},"old AAJT finish stopped new intervention"] call _check;
    ''')


@pytest.mark.parametrize("operation", ["Apply", "Remove"])
def test_vehicle_care_has_token_but_never_starts_on_foot_pose(operation):
    execute(setup() + f'''
        _parent=missionNamespace;
        private _classname="ACME_{operation}AAJT_Inguinal";
        private _callbackArgs=[_medic,_patient,"LeftLeg",_classname,objNull,"",false];
        private _callbackStart=ACME_fnc_aajtTreatmentStart;
        call _bind;
        [count _moves==0 && {{_preps==0}},"seated AAJT used on-foot animation"] call _check;
        [(_callbackArgs select 7)>=0,"seated AAJT lacks episode binding"] call _check;
        [_callbackArgs,false] call ACME_fnc_aajtTreatmentFinish;
        [(_medic getVariable ["ACME_aajtTreatment",[1]]) isEqualTo [],"seated completion leaked episode"] call _check;
    ''')


def event_setup():
    return '''
        private _eventHandlers=[]; private _leases=[];
        CBA_fnc_addEventHandler={_eventHandlers pushBack _this;};
        ACME_fnc_chestAccessVestEvent={_leases pushBack _this;};
        private _emit={params ["_event","_args"]; {if ((_x select 0)==_event) then {_args call (_x select 1);};} forEach _eventHandlers;};
    ''' + adapt(read("registerChestAccessVestRuntime").replace('netId _medic','"provider"')).replace(') != _patient', ') isNotEqualTo _patient')


@pytest.mark.parametrize("event", ["ace_treatmentSucceded", "ace_treatmentFailed"])
def test_aed_pads_acquire_and_release_exact_chest_custody(event):
    execute(event_setup() + '''
        private _args=[_medic,_patient,"Body","AED_ApplyPads"];
        ["ace_treatmentStarted",_args] call _emit;
        [count _leases==1 && {(_leases select 0) select 3},"AED pads omitted carrier acquisition"] call _check;
        private _id=(_leases select 0) select 2;
        ["ace_treatmentStarted",_args] call _emit;
        [count _leases==1,"duplicate start acquired a second lease"] call _check;
    ''' + f'["{event}",_args] call _emit;' + '''
        [count _leases==2 && {!((_leases select 1) select 3)} && {((_leases select 1) select 2)==_id},"AED completion released wrong custody"] call _check;
    ''')


@pytest.mark.parametrize("classname", ["AED_RemovePads", "AED_ConnectPulseOximeter", "AED_DisconnectPulseOximeter", "AED_ConnectPressureCuff", "AED_DisconnectPressureCuff", "AED_ConnectCapnograph", "AED_DisconnectCapnograph"])
def test_other_aed_descendants_do_not_acquire_chest_access(classname):
    execute(event_setup() + f'''
        ["ace_treatmentStarted",[_medic,_patient,"Body","{classname}"]] call _emit;
        [count _leases==0,"unrelated inherited AED action removed carrier"] call _check;
    ''')


def test_aed_owner_preparation_removes_carrier_before_publishing_readiness():
    execute(patient_setup() + function("chestAccessVestAcquire") + function("chestAccessVestEvent") + '''
        // Provider engine entry/readiness is an explicit network boundary here.
        ACME_fnc_ownerDispatch={
            params ["_owner","_operation","_args"];
            if (_operation=="chestAccessVestProvider") then {
                (_args select 0) setVariable ["ACME_chestAccessProviderReady",[_args select 4,1]];
            };
        };
        _vest="Vest_A"; _loadout set [4,["Vest_A",[]]];
        [_patient,_medic,"pads:1",true,"aed_applypads"] call ACME_fnc_chestAccessVestEvent;
        [(_patient getVariable ["ACME_chestAccess_readyServer",0])==-1,"pads marked ready before carrier removal"] call _check;
        call _drain;
        [count _commits==1 && {_vest==""},"pads did not perform chest carrier transaction"] call _check;
        [(_patient getVariable ["ACME_chestAccess_readyLease",""])=="pads:1" && {(_patient getVariable ["ACME_chestAccess_readyServer",-1])==1000},"pads lacked completed exact-lease readiness"] call _check;
    ''')


@pytest.mark.parametrize("classname,part", AAJT)
def test_configuration_routes_all_aajt_callbacks_and_suppresses_native_weapon_queue(classname, part):
    body=cfg_class((ROOT/'addons/acm_extended/config.cpp').read_text(), classname)
    for text in ('ACME_suppressNativeTreatmentAnim = 1;',
                 'callbackStart = "_this call ACME_fnc_aajtTreatmentStart";',
                 'callbackFailure = "[_this, false] call ACME_fnc_aajtTreatmentFinish";',
                 'callbackSuccess = "if ([_this, true] call ACME_fnc_aajtTreatmentFinish) then {'):
        assert text in body
    assert ('ACME_fnc_aajtApply' if '_Apply' in classname else 'ACME_fnc_aajtRemove') in body
    assert f'treatmentTime = {20 if "_Apply" in classname else 4};' in body


def test_aajt_bridge_bypasses_bounded_torso_gesture_and_native_rate_lease():
    source=(ROOT/'addons/core/overrides/fnc_treatment.sqf').read_text()
    start=source.index('private _classKey = toLowerANSI _classname;')
    end=source.index('private _ownsProviderAnim',start)
    block=source[start:end]
    for classname,part in AAJT:
        execute(f'private _classname="{classname}"; private _category="bandage"; private _bodyPart="{part}"; private _part=toLower _bodyPart;'+adapt(block)+'''
            [_aajtOwned && {_mode==""} && {_exactAnim==""},"AAJT got a second bounded gesture owner"] call _check;
        ''')
    assert 'if (_mode == "" && {!_headOwned} && {!_aajtOwned}' in source
    loop=cfg_class((ROOT/'addons/acm_extended/config.cpp').read_text(),'ACME_JunctionalWork')
    assert ': AinvPknlMstpSnonWnonDnon_medic4' in loop and 'looped = 1;' in loop
