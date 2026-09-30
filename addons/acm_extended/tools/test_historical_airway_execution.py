"""Batch 2 source-derived airway/aftercare and stored-medication execution.

The reviewed SQF runs with explicit owner, item, transport and presentation
stand-ins. Volume arithmetic, epoch/receipt/session checks and branch ordering
are not substituted. Does not execute Arma networking or dose kinetics.
"""
import pytest
from test_historical_cardiac_execution import F, code, function, setup
from test_menu_death_lifecycle import execute


def suction_setup():
    # Object identity uses namespace stand-ins in SQF-VM, where == is not
    # defined for namespaces. isEqualTo preserves the tested identity relation.
    drain=function('laryngoFluidDrainLocal',extended=True).replace('(_x select 1) == _medic','(_x select 1) isEqualTo _medic')
    return setup()+function('laryngoFluidState',extended=True)+function('setAirwayState','airway')+drain+'''
        ACM_airway_fnc_clearAirwayCheckedTime={};
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_State",2];
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",1];
        _patient setVariable ["ACME_laryngo_secretions",["secretions-1",2]];
        _patient setVariable ["ACME_suctionSessions",[["session",_medic,100,"electric"]]];
        private _stamp=([_patient] call ACME_fnc_laryngoFluidState) select 0;
    '''


def test_suction_debits_once_and_clears_only_the_current_compartment():
    execute(suction_setup()+'''
        [_patient,_medic,1,"a",_stamp,3,"session"] call ACME_fnc_laryngoFluidDrainLocal;
        [(([_patient] call ACME_fnc_laryngoFluidState) select 2)==1,"partial suction amount wrong"] call _check;
        [_patient,_medic,1,"a",_stamp,3,"session"] call ACME_fnc_laryngoFluidDrainLocal;
        [(([_patient] call ACME_fnc_laryngoFluidState) select 2)==1,"duplicate suction debited again"] call _check;
        [_patient,_medic,1,"b",_stamp,1,"session"] call ACME_fnc_laryngoFluidDrainLocal;
        [(_patient getVariable ["ACM_airway_AirwayObstructionVomit_State",-1])==0,"vomit not cleared"] call _check;
        [(_patient getVariable ["ACM_airway_AirwayObstructionBlood_State",-1])==1,"vomit suction cleared blood"] call _check;
        private _blood=[_patient] call ACME_fnc_laryngoFluidState;
        [(_blood select 1)=="b" && {(_blood select 2)==2},"blood compartment not preserved"] call _check;
        [_patient,_medic,1,"c",_blood select 0,2,"session"] call ACME_fnc_laryngoFluidDrainLocal;
        [(_patient getVariable ["ACM_airway_AirwayObstructionBlood_State",-1])==0,"blood not cleared"] call _check;
        private _secretions=[_patient] call ACME_fnc_laryngoFluidState;
        [(_secretions select 1)=="s" && {(_secretions select 2)==2},"blood suction cleared secretions"] call _check;
        private _total=(_patient getVariable ["ACME_suctionTotals",[]]) select 0;
        [(_total select 1)==300,"suction total did not conserve volume"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_patient setVariable ["ACME_suctionSessions",[]];',
    '_patient setVariable ["ACME_suctionSessions",[["session",_medic,9,"electric"]]];',
    '_patient setVariable ["ACM_airway_AirwayObstructionVomit_State",3];',
    '_patientAlive=false;', '_alive=false;', '_distance=6;',
    '_medic setVariable ["ACE_isUnconscious",true];',
])
def test_stale_or_invalid_suction_has_no_receipt_debit_or_native_clear(change):
    if change == '_patientAlive=false;':
        # B208 explicitly permits physical removal of retained airway contents
        # after engine death. Keep this historical case identity while verifying
        # the newly requested behavior and the one-debit receipt fence.
        execute(suction_setup()+change+'''
            [_patient,_medic,1,"a",_stamp,4,"session"] call ACME_fnc_laryngoFluidDrainLocal;
            [_patient,_medic,1,"a",_stamp,4,"session"] call ACME_fnc_laryngoFluidDrainLocal;
            [(_patient getVariable ["ACM_airway_AirwayObstructionVomit_State",-1])==0,"corpse suction did not clear retained vomit"] call _check;
            [(_patient getVariable ["ACM_airway_AirwayObstructionBlood_State",-1])==1,"corpse suction cleared a different compartment"] call _check;
            [count (_patient getVariable ["ACME_laryngoEventReceipts",[]])==1,"corpse suction duplicated its receipt"] call _check;
            [(((_patient getVariable ["ACME_suctionTotals",[]]) select 0) select 1)==200,"corpse suction debited more than retained volume"] call _check;
        ''')
        return
    execute(suction_setup()+change+'''
        private _before=[_patient] call ACME_fnc_laryngoFluidState;
        [_patient,_medic,1,"a",_stamp,4,"session"] call ACME_fnc_laryngoFluidDrainLocal;
        [([_patient] call ACME_fnc_laryngoFluidState) isEqualTo _before,"invalid suction changed volume"] call _check;
        [(_patient getVariable ["ACME_laryngoEventReceipts",[]]) isEqualTo [],"invalid suction created receipt"] call _check;
        [(_patient getVariable ["ACME_suctionTotals",[]]) isEqualTo [],"invalid suction debited"] call _check;
    ''')


@pytest.mark.parametrize('amount',[-1,0,10.01])
def test_suction_rejects_invalid_amounts(amount):
    execute(suction_setup()+f'[_patient,_medic,1,"a",_stamp,{amount},"session"] call ACME_fnc_laryngoFluidDrainLocal;'+'''
        [(_patient getVariable ["ACME_suctionTotals",[]]) isEqualTo [],"invalid amount debited"] call _check;
    ''')


def test_manual_suction_caps_at_available_capacity_without_double_debit():
    execute(suction_setup()+'''
        _patient setVariable ["ACME_suctionSessions",[["session",_medic,100,"manual"]]];
        _medic setVariable ["ACME_suctionManualSession",[0,0,975]];
        [_patient,_medic,1,"a",_stamp,4,"session"] call ACME_fnc_laryngoFluidDrainLocal;
        [(([_patient] call ACME_fnc_laryngoFluidState) select 2)==3.5,"manual capacity overdraw"] call _check;
        [_patient,_medic,1,"b",_stamp,4,"session"] call ACME_fnc_laryngoFluidDrainLocal;
        [(([_patient] call ACME_fnc_laryngoFluidState) select 2)==3.5,"full suction container kept draining"] call _check;
        private _total=(_patient getVariable ["ACME_suctionTotals",[]]) select 0;
        [(_total select 1)==25 && {(_total select 2)==25},"manual totals wrong"] call _check;
    ''')


def epi_setup():
    return setup()+function('narcStoreCommit',extended=True)+function('epinephrinePushStored',extended=True)+'''
        private _hasIV=true; private _hasIO=false;
        private _requests=[]; private _storeAtDispatch=[];
        ACM_circulation_fnc_hasIV={_hasIV && {count _this<4 || {(_this select 3)==3}}};
        ACM_circulation_fnc_hasIO={_hasIO};
        ACME_fnc_medicationRequest={_storeAtDispatch pushBack (+(_medic getVariable ["ACME_narcStore",[]])); _requests pushBack _this;};
        _medic setVariable ["ACME_narcStore",[["EpinephrineCardiac",10,1,"label",9,[],"epiMixB12"],["unrelated"]]];
    '''


@pytest.mark.parametrize('push',[1,2,10])
@pytest.mark.parametrize('alive',[True,False])
def test_measured_epinephrine_debits_before_request_and_conserves_remainder_and_refund(push,alive):
    execute(epi_setup()+f'_patientAlive={str(alive).lower()}; private _push={push};'+'''
        private _result=[_medic,_patient,"leftarm",0,_push,3,3] call ACME_fnc_epinephrinePushStored;
        [_result && {count _requests==1},"valid measured push rejected"] call _check;
        private _request=_requests select 0;
        private _dose=((_request select 3) select 0) select 1;
        [abs (_dose-(_push*0.01))<0.000001,"measured dose changed"] call _check;
        private _remaining=_medic getVariable ["ACME_narcStore",[]];
        [(_storeAtDispatch select 0) isEqualTo _remaining,"medication sent before inventory debit"] call _check;
        private _refund=((_request select 6) select 1) select 0;
        [abs (((_refund select 2)+(_refund select 4))-_push)<0.000001,"refund differs from removed volume"] call _check;
        if (_push==10) then {[_remaining isEqualTo [["unrelated"]],"full push removed wrong row"] call _check;} else {
            [abs ((((_remaining select 0) select 2)+((_remaining select 0) select 4))-(10-_push))<0.000001,"remainder not conserved"] call _check;
        };
    ''')


@pytest.mark.parametrize('push,site,change',[
    (-1,3,''),(0,3,''),(11,3,''),(1,2,''),(1,-1,''),
    (1,3,'_hasIV=false;'),(1,3,'_distance=6;'),
])
def test_invalid_epinephrine_push_changes_neither_inventory_nor_dispatch(push,site,change):
    execute(epi_setup()+change+'''
        private _before=+(_medic getVariable ["ACME_narcStore",[]]);
    '''+f'private _result=[_medic,_patient,"leftarm",0,{push},{site},3] call ACME_fnc_epinephrinePushStored;'+'''
        [!_result && {count _requests==0},"invalid push dispatched"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo _before,"invalid push consumed inventory"] call _check;
    ''')


def aftercare_setup():
    return setup()+function('thoraAftercareLocal',extended=True)+'''
        private _effects=0; private _logs=0; private _writes=[]; private _permitted=true;
        ACME_fnc_procedureAllowed={_permitted};
        ACME_fnc_chestSealBurpReady={true};
        ACME_fnc_thoraSideStateCommit={params ["_p","_side","_field","_value"]; _writes pushBack _this; _p setVariable [format ["ACME_thora_%1_%2",_field,_side],_value];};
        ACME_fnc_thoraBumpVer={};
        ACME_fnc_ptxTreat={_effects=_effects+1;};
        ACM_breathing_fnc_updateLungState={};
        ACME_fnc_chestSealLogOnce={_logs=_logs+1;true};
        ace_medical_treatment_fnc_addToLog={_logs=_logs+1;};
        _patient setVariable ["ACME_thora_incision_left",[1,2,3]];
        _patient setVariable ["ACME_thora_open_left","sealed"];
        _patient setVariable ["ACME_thora_sealed_left",true];
        _patient setVariable ["ACME_thora_closed_left",true];
        _patient setVariable ["ACME_thora_tube_right",true];
        _patient setVariable ["ACME_CS_holeData",["external wound evidence"]];
    '''


@pytest.mark.parametrize('alive',[True,False])
@pytest.mark.parametrize('operation',['peel','burp','sweep'])
def test_aftercare_remains_available_on_dead_patients_without_resuming_physiology(alive,operation):
    prepare=''
    if operation=='sweep':prepare='_patient setVariable ["ACME_thora_open_left","finger"]; _patient setVariable ["ACME_thora_sealed_left",false]; _patient setVariable ["ACME_thora_closed_left",false];'
    execute(aftercare_setup()+prepare+f'_patientAlive={str(alive).lower()};'+
        f'[_patient,_medic,"left","{operation}",1] call ACME_fnc_thoraAftercareLocal;'+
        f'[_effects=={int(alive)} && {{_logs==1}},"aftercare availability/physiology mismatch"] call _check;'+
        f'[count _writes=={3 if operation=="peel" else 0},"wrong tract mutation"] call _check;'+'''
        [_patient getVariable ["ACME_thora_tube_right",false],"opposite-side tube cleared"] call _check;
        [(_patient getVariable ["ACME_CS_holeData",[]]) isEqualTo ["external wound evidence"],"aftercare modified unrelated wound seals"] call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_patientLocal=false;', '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_alive=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_distance=6;', '_permitted=false;',
    '_patient setVariable ["ACME_thora_tube_left",true];',
    '_patient setVariable ["ACME_thora_incision_left",[]];',
])
def test_aftercare_rejects_invalid_owner_episode_provider_or_tract(change):
    execute(aftercare_setup()+change+'''
        [_patient,_medic,"left","peel",1] call ACME_fnc_thoraAftercareLocal;
        [_effects==0 && {_logs==0} && {count _writes==0},"invalid aftercare changed patient"] call _check;
    ''')


def chest_effect_setup():
    # Localization and triage rendering are presentation boundaries only.
    effect=function('chestSealEffectLocal',extended=True).replace('localize "STR_ACM_Breathing_ChestSeal"','"ChestSeal"')
    return aftercare_setup()+effect+'''
        private _injuries=0; private _wholeChestSeals=0; private _nativeChanges=[];
        ACME_fnc_ptxInjury={_injuries=_injuries+1;};
        ACME_fnc_ptxEnsure={};
        ACM_breathing_fnc_applyChestSealLocal={_wholeChestSeals=_wholeChestSeals+1;};
        ACM_breathing_fnc_setRuntimeState={_nativeChanges append (_this select 1);};
        ace_medical_treatment_fnc_addToTriageCard={};
    '''


@pytest.mark.parametrize('blocked,revision,accepted',[(False,4,True),(False,3,False),(False,2,False),(True,4,False)])
def test_seal_peel_rejects_stale_effects_and_never_creates_a_new_injury(blocked,revision,accepted):
    execute(chest_effect_setup()+'''
        _patient setVariable ["ACME_CS_lastSealEffectRev",3];
    '''+('_patient setVariable ["ACME_CS_blockedEffectEpoch","workspace"];' if blocked else '')+
        f'[_patient,_medic,"peel",[false],"workspace",0,{revision}] call ACME_fnc_chestSealEffectLocal;'+
        f'[_effects=={int(accepted)} && {{_injuries==0}},"peel created injury or accepted stale effect"] call _check;'+
        f'[count _nativeChanges=={int(accepted)},"wrong native seal change"] call _check;')


@pytest.mark.parametrize('epoch,tube,tract,accepted',[(1,False,'finger',True),(2,False,'finger',False),(1,True,'finger',False),(1,False,'sealed',False)])
def test_surgical_seal_is_side_scoped_and_cannot_cover_external_wounds(epoch,tube,tract,accepted):
    execute(chest_effect_setup()+f'_patient setVariable ["ACME_thora_open_left","{tract}"]; _patient setVariable ["ACME_thora_tube_left",{str(tube).lower()}];'+
        f'[_patient,_medic,"thoraSeal",["left",{epoch}]] call ACME_fnc_chestSealEffectLocal;'+
        f'[count _writes=={3 if accepted else 0} && {{_effects=={int(accepted)}}},"surgical seal accepted invalid tract/epoch"] call _check;'+'''
        [_wholeChestSeals==0 && {count _nativeChanges==0},"surgical seal changed whole-chest coverage"] call _check;
        [_patient getVariable ["ACME_thora_tube_right",false],"surgical seal changed opposite tube"] call _check;
        [(_patient getVariable ["ACME_CS_holeData",[]]) isEqualTo ["external wound evidence"],"external wounds changed"] call _check;
    ''')


def test_instructor_chest_clear_removes_episode_and_worker_but_retains_equipment():
    execute(setup()+function('megacodeChestInjury',extended=True)+'''
        private _nativeChanges=[]; private _ended=[];
        ACM_breathing_fnc_setRuntimeState={_nativeChanges append (_this select 1);};
        ACM_breathing_fnc_setChestInjuryState={}; ACM_breathing_fnc_updateLungState={};
        CBA_fnc_removePerFrameHandler={_ended pushBack (_this select 0);};
        _patient setVariable ["ACM_breathing_Pneumothorax_PFH",12];
        _patient setVariable ["ACME_ptx_state",[1,4,1]];
        _patient setVariable ["ACME_ptx_tensionSeverity",1];
        _patient setVariable ["ACME_ptx_tensionProgress",8];
        _patient setVariable ["ACME_CS_holeData",["wound"]];
        _patient setVariable ["ACME_thora_tube_left",true];
        _patient setVariable ["ACME_ncd_placed",["catheter"]];
        [_patient,"ncd"] call ACME_fnc_megacodeChestInjury;
        [_ended isEqualTo [12],"old native worker not retired"] call _check;
        { [isNil {_patient getVariable _x},"old chest episode survived"] call _check; }
            forEach ["ACME_ptx_state","ACME_ptx_tensionSeverity","ACME_ptx_tensionProgress"];
        [(["pneumothoraxPFH",-1] in _nativeChanges) && {["hardcorePneumothorax",false] in _nativeChanges},"native clear request missing"] call _check;
        [_patient getVariable ["ACME_thora_tube_left",false],"clear removed tube"] call _check;
        [(_patient getVariable ["ACME_ncd_placed",[]]) isEqualTo ["catheter"],"clear removed catheter"] call _check;
        [(_patient getVariable ["ACME_CS_holeData",[]]) isEqualTo ["wound"],"clear removed wound evidence"] call _check;
    ''')
