"""Physical-roll permission and deferred chest-workspace restoration.

The actual eligibility, roll, workspace begin/end and carrier restore functions
execute with explicit object/animation/inventory/transport stand-ins. Callbacks
are delivered in controlled orders; no Arma pose or real network is rendered.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute

F=ROOT/'addons/acm_extended/functions'


def source(name):
    return (F/('fn_'+name+'.sqf')).read_text()


def code(name, server_clock='CBA_missionTime'):
    text=source(name)
    for unit in ('_patient','_p'):
        for old,new in [('local '+unit,'_patientLocal'),('alive '+unit,'_patientAlive'),
                        ('objectParent '+unit,'_parent'),('animationState '+unit,'_animation'),
                        ('lifeState '+unit,'_lifeState'),('vest '+unit,'_vest'),
                        ('getUnitLoadout '+unit,'(+_loadout)')]:
            text=re.sub(re.escape(old)+r'\b',lambda m:new,text)
        text=text.replace(unit+' setUnitLoadout [_loadout,false];',
                          '_loadouts pushBack (+_loadout); _vest=(_loadout select 4) select 0;')
    text=text.replace('serverTime',server_clock)
    text=text.replace('finite _rollTime','(_rollTime call _finite)')
    text=text.replace('finite _animSpeed','(_animSpeed call _finite)')
    for key in ('ace_medical_engine_uncon_anim_faceup','ace_medical_engine_uncon_anim_facedown'):
        text=text.replace('_animMap getOrDefault ["'+key+'", []]', '[_animMap,"'+key+'",[]] call _getDefault')
    for var in ('_prop','_headProp'):
        text=text.replace('detach '+var+';', '_detaches pushBack '+var+';')
        text=text.replace('deleteVehicle '+var+';', '_deletes pushBack '+var+';')
    return adapt(text)


def function(name):
    return 'ACME_fnc_'+name+'={'+code(name)+'};\n'


def setup():
    return r'''
        private _patientLocal=true; private _parent=objNull;
        private _animation="amovppnemstpsraswrfldnon"; private _actualSide="back";
        private _lifeState="HEALTHY";
        private _vest=""; private _loadout=[[],[],[],[],[],[],"","",[],[]];
        private _loadouts=[]; private _detaches=[]; private _deletes=[];
        private _rolls=[]; private _animRequests=[]; private _releases=[];
        private _headResume=[]; private _yielded=0; private _acquired=0;
        private _blocked=false; private _leaseAllowed=true;
        private _finite={_this isEqualType 0};
        private _getDefault={params ["_map","_key","_default"]; if (_key in _map) then {_map get _key} else {_default};};
        CBA_fnc_waitAndExecute={_waits pushBack ["delay",_this select 0,_this select 1,_this select 2];};
        CBA_fnc_execNextFrame={_waits pushBack ["frame",_this select 0,_this select 1,0];};
        CBA_fnc_waitUntilAndExecute={_waits pushBack ["condition",_this select 1,_this select 2,_this param [3,-1],_this select 0,_this param [4,{}]];};
        CBA_fnc_globalEvent={_events pushBack _this;};
        CBA_fnc_removePerFrameHandler={_removed pushBack (_this select 0);};
        ACME_fnc_patientAnimRequest={
            _animRequests pushBack _this;
            if (!_leaseAllowed) exitWith {""};
            private _tok=_this select 7;
            (_this select 0) setVariable ["ACME_patientAnimLock",[_tok,_this select 3,"provider",_this select 6,100]];
            _tok
        };
        ACME_fnc_patientAnimRelease={_releases pushBack _this;};
        ACME_fnc_headElevYieldForRoll={_yielded=_yielded+1;};
        ACME_fnc_headElevTryResume={_headResume pushBack _this;};
        ACME_fnc_headElevCollision={}; ACME_fnc_headElevPinPose={};
        ACME_fnc_animBlocked={_blocked};
        ACME_fnc_chestSealParkCarrier={}; ACME_fnc_chestAccessVestPark={};
        ACME_fnc_chestAccessVestAcquire={_acquired=_acquired+1;};
        ACME_fnc_doAnim={_moves pushBack _this;};
        ACM_core_fnc_cprActive={false};
        ACM_core_fnc_bvmActive={false};
        ACME_fnc_chestAccessManeuverActive={([_patient] call ACM_core_fnc_cprActive) || {[_patient] call ACM_core_fnc_bvmActive}};
        // Roll direction and surface classification are tested separately below.
        ACME_fnc_chestSealRoll={_rolls pushBack _this;};
        ACME_fnc_patientRollCancel={_rolls pushBack ["cancel",_this];};
        missionNamespace setVariable ["ace_medical_engine_animations",createHashMapFromArray [
            ["ace_medical_engine_uncon_anim_faceup",["known_up"]],
            ["ace_medical_engine_uncon_anim_facedown",["known_down"]]]];
        private _deliver={
            params ["_job",["_timeout",false]];
            if ((_job select 0)=="condition" && {!_timeout}) then {
                [(_job select 2) call (_job select 4),"success delivered before its condition"] call _check;
            };
            (_job select 2) call (_job select (if (_timeout) then {5} else {1}));
        };
        private _drain={
            for "_round" from 1 to 8 do {
                private _jobs=+_waits; _waits=[];
                if (_jobs isEqualTo []) exitWith {};
                {[_x] call _deliver;} forEach _jobs;
            };
            [count _waits==0,"unbounded deferred work"] call _check;
        };
    '''+function('chestSealCanPhysicalRoll')+function('chestSealPatientBegin')+function('chestSealPatientEnd')+function('chestAccessVestRestore')


@pytest.mark.parametrize('flags,animation,expected',[
    ('','amovppnemstpsraswrfldnon',False),
    ('_patient setVariable ["ACME_CS_ProcedureGrounded",true];','amovppnemstpsraswrfldnon',False),
    ('_patient setVariable ["ACME_obtunded",true];','amovppnemstpsraswrfldnon',False),
    ('_patient setVariable ["ACM_core_Lying_State",true];','amovppnemstpsraswrfldnon',False),
    ('_patient setVariable ["ACE_isUnconscious",true];','unconscious',True),
    ('_patient setVariable ["ace_medical_unconscious",true];','unconscious',True),
    ('_patient setVariable ["ACM_core_Lying_State",true];','ACM_LyingState',True),
    ('_patient setVariable ["ACM_core_Lying_State",1];','known_down',True),
    ('_patient setVariable ["ACM_core_Lying_State",true];','known_up',True),
    ('_patientAlive=false; _patient setVariable ["ACE_isUnconscious",true];','unconscious',False),
    ('_parent=missionNamespace; _patient setVariable ["ACE_isUnconscious",true];','unconscious',False),
])
def test_roll_permission_uses_clinical_state_and_known_rest_not_prone_bookkeeping(flags,animation,expected):
    execute(setup()+flags+f'_animation="{animation}";'+
            f'[([_patient] call ACME_fnc_chestSealCanPhysicalRoll) isEqualTo {str(expected).lower()},"incorrect roll authority"] call _check;')


def workspace():
    return '''
        _patient setVariable ["ACME_CS_ProcedureGeneration",4];
        _patient setVariable ["ACME_CS_ProcedureTokens",["old"]];
        _patient setVariable ["ACME_CS_ProcedureActive",true];
        _patient setVariable ["ACME_CS_PreProcedureState",["back",false,false,false,""]];
        _patient setVariable ["ACME_CS_facing","back"];
    '''


@pytest.mark.parametrize('state',[
    '', '_patient setVariable ["ACME_CS_ProcedureGrounded",true];',
    '_patient setVariable ["ACM_core_Lying_State",true];',
    '_patient setVariable ["ACME_obtunded",true];',
])
@pytest.mark.parametrize('carrier',[False,True])
def test_workspace_close_never_forces_conscious_mobile_prone_into_unconscious_pose(state,carrier):
    gear='_patient setVariable ["ACME_CS_vestLoadout",["Vest_A",[["item",2]]]];' if carrier else ''
    execute(setup()+workspace()+state+gear+'''
        [_patient,"old",_medic] call ACME_fnc_chestSealPatientEnd;
        call _drain;
        [count _events==0 && {count _rolls==0} && {count _animRequests==0},"close seized conscious patient's animation"] call _check;
        [!(_patient getVariable ["ACME_CS_ProcedureActive",true]),"workspace did not close"] call _check;
    '''+( '[count _loadouts==1 && {_vest=="Vest_A"},"conscious casualty carrier not restored"] call _check;' if carrier else '[count _loadouts==0,"invented carrier"] call _check;'))


@pytest.mark.parametrize('context',['access','chestseal'])
@pytest.mark.parametrize('carrier',[False,True])
def test_common_carrier_restore_does_not_override_a_denied_roll(context,carrier):
    key='ACME_CS_vestLoadout' if context=='chestseal' else 'ACME_chestAccess_vestLoadout'
    gear=f'_patient setVariable ["{key}",["Vest_A",[["item",2]]]];' if carrier else ''
    execute(setup()+gear+f'[_patient,false,_medic,"{context}",false] call ACME_fnc_chestAccessVestRestore;'+'''
        call _drain;
        [count _events==0 && {count _rolls==0} && {count _animRequests==0},"denied roll still forced pose"] call _check;
    '''+('[count _loadouts==1 && {_vest=="Vest_A"},"gear was lost on denied roll"] call _check;' if carrier else '[count _loadouts==0,"unexpected inventory write"] call _check;'))


@pytest.mark.parametrize('wait_path,timeout',[('roll',False),('park',False),('park',True),('restore',False),('restore',True)])
def test_deferred_workspace_cleanup_cannot_move_a_newer_viewer_session(wait_path,timeout):
    route={
        'roll':'_patient setVariable ["ACE_isUnconscious",true];',
        'park':'_actualSide="front"; _patient setVariable ["ACME_CS_vestBusy","park:old"];',
        'restore':'_actualSide="front"; _patient setVariable ["ACME_CS_vestLoadout",["Vest_A",[]]]; _patient setVariable ["ACME_CS_vestBusy","restore:old"];',
    }[wait_path]
    execute(setup()+workspace()+route+'''
        [_patient,"old",_medic] call ACME_fnc_chestSealPatientEnd;
        [count _waits==1,"expected pending restore callback"] call _check;
        private _old=_waits select 0; _waits=[];
        [_patient,"new",_medic] call ACME_fnc_chestSealPatientBegin;
        private _pendingNew=+_waits;
        private _newGeneration=_patient getVariable ["ACME_CS_ProcedureGeneration",-1];
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACME_CS_facing","back"];
        _patient setVariable ["ACME_CS_ProcedureReadyAt",222];
        _actualSide="back";
        _events=[]; _rolls=[]; _animRequests=[]; _loadouts=[];
    '''+('' if timeout or wait_path=='roll' else '_patient setVariable ["ACME_CS_vestBusy",""]; _patient setVariable ["ACME_CS_vestLoadout",[]];')+f'[_old,{str(timeout).lower()}] call _deliver;'+'''
        [count _events==0 && {count _rolls==0} && {count _animRequests==0},"old restore moved new session"] call _check;
        [(_patient getVariable ["ACME_CS_facing",""])=="back","old cleanup changed new side"] call _check;
        [(_patient getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo ["new"],"new viewer lost lease"] call _check;
        [(_patient getVariable ["ACME_CS_ProcedureGeneration",0])==_newGeneration,"new generation altered"] call _check;
        [(_patient getVariable ["ACME_CS_ProcedureReadyAt",0])==222,"new readiness altered"] call _check;
        [count _loadouts==0 && {_waits isEqualTo _pendingNew},"old cleanup altered new preparation or resumed custody work"] call _check;
    ''')


@pytest.mark.parametrize('back',[False,True])
@pytest.mark.parametrize('alive',[False,True])
def test_last_viewer_cleanup_retains_supine_exit_and_dead_patient_equipment(back,alive):
    execute(setup()+workspace()+f'_actualSide="{"back" if back else "front"}"; _patientAlive={str(alive).lower()};'+'''
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACME_CS_vestLoadout",["Vest_A",[["item",2]]]];
        [_patient,"old",_medic] call ACME_fnc_chestSealPatientEnd;
    '''+f'[count _rolls=={int(back and alive)},"unneeded roll or missing supine normalization"] call _check;'+'''
        _actualSide="front"; _animation="ACM_LyingState";
        call _drain;
        [!(_patient getVariable ["ACME_CS_ProcedureActive",true]),"last-viewer cleanup incomplete"] call _check;
        [_vest=="Vest_A" && {count _loadouts==1},"saved carrier not returned exactly once"] call _check;
        [((_loadouts select 0) select 4) isEqualTo ["Vest_A",[["item",2]]],"carrier contents changed"] call _check;
        [_patient getVariable ["ACE_isUnconscious",false],"cleanup changed consciousness"] call _check;
    '''+('' if alive else '[count _events==0 && {count _animRequests==0},"corpse animation restarted"] call _check;'))


@pytest.mark.parametrize('token',['wrong',''])
def test_unknown_or_repeated_viewer_departure_has_no_effect(token):
    execute(setup()+workspace()+f'[_patient,"{token}",_medic] call ACME_fnc_chestSealPatientEnd;'+'''
        [(_patient getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo ["old"],"wrong token changed membership"] call _check;
        [count _waits==0 && {count _events==0} && {count _rolls==0},"wrong token started teardown"] call _check;
    ''')


def test_intermediate_viewer_close_preserves_workspace_and_custody():
    execute(setup()+workspace()+'''
        [_patient,"second",_medic] call ACME_fnc_chestSealPatientBegin;
        [_patient,"third",_medic] call ACME_fnc_chestSealPatientBegin;
        [_patient,"old",_medic] call ACME_fnc_chestSealPatientEnd;
        [(_patient getVariable ["ACME_CS_ProcedureTokens",[]]) isEqualTo ["second","third"],"other viewers lost"] call _check;
        [count _waits==0 && {count _events==0} && {count _rolls==0} && {_acquired==0},"intermediate close repeated preparation"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patientLocal=false;', '_parent=missionNamespace;', '_patientAlive=false;',
    '_patient setVariable ["ACE_isUnconscious",false];',
])
def test_loss_of_physical_eligibility_during_restore_never_forces_hold(change):
    execute(setup()+workspace()+'''
        _patient setVariable ["ACE_isUnconscious",true];
        [_patient,"old",_medic] call ACME_fnc_chestSealPatientEnd;
        private _old=_waits select 0; _waits=[];
        _events=[]; _rolls=[];
    '''+change+'''
        [_old] call _deliver;
        [count _events==0 && {count _rolls==0},"lost eligibility still forced a hold"] call _check;
    ''')


@pytest.mark.parametrize('head',[False,True])
def test_semifowler_resume_remains_after_supine_normalization_and_final_custody_release(head):
    execute(setup()+workspace()+f'_patient setVariable ["ACME_CS_PreProcedureState",["back",{str(head).lower()},false,false,""]];'+'''
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACME_headElevated",true];
        _patient setVariable ["ACME_headElev_Suspended",true];
        [_patient,"old",_medic] call ACME_fnc_chestSealPatientEnd;
        [count _headResume==0,"head resumed before front normalization"] call _check;
        _actualSide="front"; call _drain;
    '''+f'[count _headResume=={int(head)},"incorrect head-resume ownership"] call _check;'+'''
        [(_patient getVariable ["ACME_CS_facing",""])=="front","cleanup restored posterior posture"] call _check;
    ''')


@pytest.mark.parametrize('target',['front','back'])
@pytest.mark.parametrize('force',[False,True])
def test_physical_roll_rejects_conscious_prone_even_with_force_or_stale_grounded(target,force):
    execute(setup()+function('chestSealRoll')+'''
        _patient setVariable ["ACME_CS_ProcedureGrounded",true];
        _patient setVariable ["ACME_CS_facing","keep"];
    '''+f'[_patient,"{target}",{str(force).lower()},_medic] call ACME_fnc_chestSealRoll;'+'''
        [count _animRequests==0 && {count _waits==0} && {_yielded==0},"force bypassed owner roll authority"] call _check;
        [(_patient getVariable ["ACME_CS_facing",""])=="keep","denied request wrote patient side"] call _check;
    ''')


@pytest.mark.parametrize('target,transition,hold',[
    ('front','AinjPpneMstpSnonWrflDnon_rolltoback','ACM_LyingState'),
    ('back','AinjPpneMstpSnonWrflDnon_rolltofront','ace_medical_engine_uncon_anim_1'),
])
@pytest.mark.parametrize('engine_started',[False,True])
def test_roll_uses_priority_one_lease_then_only_a_scoped_fallback_and_requested_rest(target,transition,hold,engine_started):
    execute(setup()+function('chestSealRoll')+'''
        _patient setVariable ["ACE_isUnconscious",true];
    '''+f'_actualSide="{"back" if target=="front" else "front"}"; [_patient,"{target}",false,_medic,true] call ACME_fnc_chestSealRoll;'+'''
        [count _animRequests==1 && {count _waits==2},"wrong roll request or callback count"] call _check;
        private _request=_animRequests select 0;
        [(_request select 2)==1,"initial roll did not use transition priority one"] call _check;
        [_yielded==0,"preserved head elevation was yielded"] call _check;
        private _fallback=_waits select 0; private _rest=_waits select 1;
        [(_fallback select 3)==0.15 && {(_rest select 3)==(1.85/1.5)},"roll timing was changed"] call _check;
    '''+f'_animation="{transition if engine_started else "not-started"}";'+'''
        [_fallback] call _deliver;
    '''+f'[count _moves=={int(not engine_started)},"unnecessary or missing scoped fallback"] call _check;'+
        ('' if engine_started else '[((_moves select 0) select 2)==2,"repair priority changed"] call _check;')+'''
        [_rest] call _deliver;
    '''+f'[(_events select 0) isEqualTo ["ace_common_switchMove",[_patient,"{hold}"]],"wrong final rest side"] call _check;'+
        f'[(_patient getVariable ["ACME_CS_facing",""])=="{target}","wrong cached roll side"] call _check;'+'''
        [(_patient getVariable ["ACME_CS_rollToken","bad"])=="","finished roll retained token"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patient setVariable ["ACME_CS_rollToken","new-token"];',
    '_patientLocal=false;', '_patientAlive=false;', '_parent=missionNamespace;',
    '_patient setVariable ["ACE_isUnconscious",false];',
])
def test_delayed_roll_callbacks_recheck_token_and_physical_permission(change):
    execute(setup()+function('chestSealRoll')+'''
        _patient setVariable ["ACE_isUnconscious",true];
        [_patient,"front",false,_medic,true] call ACME_fnc_chestSealRoll;
        _events=[]; _moves=[];
    '''+change+'''
        call _drain;
        [count _events==0 && {count _moves==0},"stale roll callback changed animation"] call _check;
    ''')


@pytest.mark.parametrize('side',['front','back'])
def test_same_side_request_is_a_noop_and_nonlocal_request_is_forwarded(side):
    execute(setup()+function('chestSealRoll')+f'_actualSide="{side}";'+'''
        _patient setVariable ["ACE_isUnconscious",true];
    '''+f'[_patient,"{side}",false,_medic,true] call ACME_fnc_chestSealRoll;'+'''
        [count _animRequests==0 && {count _waits==0},"same-side request invented a roll"] call _check;
        _patientLocal=false;
    '''+f'[_patient,"{side}",true,_medic,true] call ACME_fnc_chestSealRoll;'+'''
        [count _events==1 && {((_events select 0) select 1)=="chestSealRoll"},"nonlocal request not forwarded"] call _check;
        [count _animRequests==0,"nonowner animated patient"] call _check;
    ''')


def side_code():
    text=code('chestSealActualSide')
    for index,(var,selection) in enumerate([('_pel','pelvis'),('_hed','head'),('_ls','leftshoulder'),('_rs','rightshoulder')]):
        old=f'private {var} = _patient modelToWorldVisual (_patient selectionPosition "{selection}");'
        assert text.count(old)==1
        text=text.replace(old,f'private {var} = _points select {index};')
    return 'ACME_fnc_chestSealActualSide={'+text+'};'


@pytest.mark.parametrize('animation,points,cached,expected',[
    ('ACM_LyingState',[[0,0,0],[0,1,0],[1,0,0],[0,0,0]],'back','front'),
    ('ace_medical_engine_uncon_anim_1',[[0,0,0],[0,1,0],[0,0,0],[1,0,0]],'front','back'),
    ('known_up',[[0,0,0]]*4,'back','front'),
    ('known_down',[[0,0,0]]*4,'front','back'),
    ('unknown',[[0,0,0],[0,1,0],[0,0,0],[1,0,0]],'back','front'),
    ('unknown',[[0,0,0],[0,1,0],[1,0,0],[0,0,0]],'front','back'),
    ('unknown',[[0,0,0]]*4,'back','back'),
    ('unknown',[[0,0,0],[0,0,1],[0,0,0],[1,0,0]],'front','front'),
])
def test_actual_surface_reader_prefers_known_pose_then_geometry_then_cached_side(animation,points,cached,expected):
    execute(setup()+side_code()+f'_animation="{animation}"; private _points={points}; _patient setVariable ["ACME_CS_facing","{cached}"];'+
            f'[([_patient,"front"] call ACME_fnc_chestSealActualSide)=="{expected}","surface classification mismatch"] call _check;')


@pytest.mark.parametrize('side',['front','back'])
@pytest.mark.parametrize('dead',[False,True])
def test_ineligible_patient_flip_remains_a_virtual_view_without_physical_control(side,dead):
    execute(setup()+function('chestSealFlip')+f'_patientAlive={str(not dead).lower()};'+'''
        private _renders=0; ACME_fnc_chestSealRender={_renders=_renders+1;};
        uiNamespace setVariable ["ACME_CS_Patient",_patient];
        uiNamespace setVariable ["ACME_CS_Medic",_medic];
    '''+f'uiNamespace setVariable ["ACME_CS_Side","{side}"];'+'''
        [] call ACME_fnc_chestSealFlip;
        [uiNamespace getVariable ["ACME_CS_VirtualFlip",false],"ineligible flip was not view-only"] call _check;
        [count _rolls==0 && {count _animRequests==0} && {count _waits==0},"virtual flip took body control"] call _check;
        [_renders==1,"virtual view was not rendered"] call _check;
    '''+f'[(uiNamespace getVariable ["ACME_CS_Side",""])=="{"back" if side=="front" else "front"}","virtual flip failed"] call _check;')


@pytest.mark.parametrize('side,target,expiry,expected',[
    ('front','back',11,'back'),('back','front',11,'front'),
    ('back','back',11,'back'),('front','back',10,'front'),
    ('back','front',9,'back'),('back','invalid',11,'back'),
])
def test_procedural_canvas_retains_selected_endpoint_without_geometry_reclassification(side,target,expiry,expected):
    text=source('chestSealTick');a=text.index('private _uiSide = ');b=text.index('// the darkness is drawn first',a)
    fragment=text[a:b]
    assert 'chestSealActualSide' not in fragment
    execute(setup()+'''
        private _renders=0; ACME_fnc_chestSealRender={_renders=_renders+1;};
    '''+f'uiNamespace setVariable ["ACME_CS_Side","{side}"]; uiNamespace setVariable ["ACME_CS_FlipTarget","{target}"]; uiNamespace setVariable ["ACME_CS_FlipLockedUntil",{expiry}];'+
        adapt(fragment)+f'[(uiNamespace getVariable ["ACME_CS_Side",""])=="{expected}","canvas changed outside explicit flip"] call _check;'+
        f'[_renders=={int(side!=expected)},"unnecessary canvas refresh"] call _check;')
