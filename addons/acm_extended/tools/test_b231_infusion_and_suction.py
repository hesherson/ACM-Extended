"""B231 production SQF transactions and airway state with explicit engine mocks.

No Arma UI, frame rendering, network transport or clinical rate calibration is
claimed. Exact-source arithmetic, custody, guards and native PFH bodies execute.
"""
import re
import subprocess
from pathlib import Path
import pytest
from test_menu_death_lifecycle import ROOT, F, adapt, execute
from test_historical_vial_execution import map_defaults, setup as vial_setup, code as vial_code, function as vial_function
from test_historical_laryngoscopy_execution import setup as airway_setup, code as airway_code, function as airway_function
from test_historical_cardiac_execution import code as clinical_code
from test_b230_prepared_infusion_transaction import setup as attach_setup, adapted as attach_code, function as attach_function

BASE = '1e004396d1ca6644be121a757cbb004f2da03a88'

def raw(name, before=False):
    path = f'addons/acm_extended/functions/fn_{name}.sqf'
    if before:
        return subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=ROOT,text=True)
    return (ROOT/path).read_text()


def resolve_setup():
    return '''private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};'''+\
        'ACME_fnc_infusionDrawResolve={'+re.sub(r'\bfinite (_\w+)',r'(\1 call _finite)',raw('infusionDrawResolve'))+'};'

@pytest.mark.parametrize('remaining',[1.9551,1.957,1.9599,1.96,1.964,0.6652,0.019,4.9997,9.996])
def test_exact_vial_endpoint_never_rounds_above_stock_or_leaves_a_fraction(remaining):
    execute(resolve_setup()+f'''
        private _r=[{remaining},{remaining}, {remaining}, 10] call ACME_fnc_infusionDrawResolve;
        [_r select 0,"remaining vial falsely rejected"] call _check;
        [abs ((_r select 1)-{remaining})<0.0000001,"endpoint volume was rounded or invented"] call _check;
    ''')

@pytest.mark.parametrize('args', ['[2,1.5,10,5]','[2,10,1.5,5]','[6,10,10,5]','[0,10,10,5]', '[-1,10,10,5]','[1,10,0,5]','[1,10,10,0]', '["1",10,10,5]'])
def test_resolver_does_not_hide_actual_stock_loss_or_invalid_draws(args):
    execute(resolve_setup()+f'[!(({args} call ACME_fnc_infusionDrawResolve) select 0),"invalid draw accepted"] call _check;')


def injection_setup(before=False):
    text=vial_setup()+r'''
        _drawDisplay=missionNamespace;
        private _holder=_medic;private _notices=[];private _corrections=[];private _refunds=[];private _syringes=2;
        private _lookupStock=1.957;
        _inventoryCounts=createHashMap;
        _medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",_lookupStock]]];
        ACME_fnc_vialHolder={_holder};
        ACME_fnc_treatmentSupplyCount={_syringes};
        ACME_fnc_treatmentSupplyTake={_syringes=_syringes-1;["syringe-receipt"]};
        ACME_fnc_treatmentSupplyRefund={true};
        ACME_fnc_infusionRefundSupplies={_refunds pushBack _this;};
        ACME_fnc_clinicalNotice={_notices pushBack _this;};
        ACME_fnc_syringeDrawSetAmount={params ["_ml"];_corrections pushBack _ml;ACM_circulation_SyringeDraw_DrawnAmount=_ml;true};
        ACME_fnc_infusionRefreshTally={};
        ACME_fnc_formatPreparedLabel={"fixture label"};
        ACME_infusion_defaultDropSet=20;
        ACME_infusion_allowedMedications=["Ketamine"];
        private _set=["set1","saline100","SalineIV_100","","","","fixture",false,"saline",100];
        _medic setVariable ["ACME_preparedIVSets",[_set]];
        private _context=["prepared",_patient,"leftarm",true,0];_context resize 21;_context set [20,"set1"];
        missionNamespace setVariable ["ACME_infusion_pendingContext",_context];
        ACM_circulation_SyringeDraw_Medication="Ketamine";
        ACM_circulation_SyringeDraw_Size=5;
        ACM_circulation_SyringeDraw_Moving=false;
        ACM_circulation_SyringeDraw_DrawnAmount=_lookupStock;
    '''
    for name in ['vialSession','medicationTakeSources','infusionTakeSupplies','preparedComponents','registerPreparedBag']:
        text+=vial_function(name)
    text+=resolve_setup()
    src=raw('injectIntoBag',before)
    src=src.replace('getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _med >> "concentration")','50')
    src=src.replace('_display displayCtrl 84006','objNull')
    text+='ACME_fnc_injectIntoBag={'+vial_code(src)+'};'
    return map_defaults(text)


def test_old_full_used_vial_failure_reproduces_at_rounded_endpoint():
    execute(injection_setup(True)+r'''
        call ACME_fnc_injectIntoBag;call ACME_fnc_injectIntoBag;
        [count _notices==2,"old confirmation loop not reproduced"] call _check;
        [(_medic getVariable ["ACME_infusion_PreparedBags",[]]) isEqualTo [],"old bug unexpectedly delivered drug"] call _check;
        [abs (([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)-1.957)<0.000001,"old rejection debited stock"] call _check;
    ''')

@pytest.mark.parametrize('remaining',[1.957,1.9599,1.96,1.964,0.6652,4.998])
def test_full_used_vial_injects_exact_solution_and_drug_once(remaining):
    execute(injection_setup()+f'''
        _medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",{remaining}]]];
        ACM_circulation_SyringeDraw_DrawnAmount={remaining};
    '''+r'''
        call ACME_fnc_injectIntoBag;
        [count _notices==0,"endpoint still needs confirmation"] call _check;
        private _bags=_medic getVariable ["ACME_infusion_PreparedBags",[]];
        [count _bags==1,"mixture missing"] call _check;
        private _b=_bags select 0;
    '''+f'''
        [abs ((_b select 10)-100-{remaining})<0.0001,"solution accounting incorrect"] call _check;
        [abs ((_b select 4)-50*{remaining})<0.0001,"drug mass incorrect"] call _check;
    '''+r'''
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==0,"empty vial retained fluid"] call _check;
        [_syringes==1 && {ACM_circulation_SyringeDraw_DrawnAmount==0},"syringe did not settle once"] call _check;
        call ACME_fnc_injectIntoBag;
        [_syringes==1 && {count _refunds==1},"repeated click duplicated settlement"] call _check;
    ''')


def test_partial_source_depleted_by_another_change_still_requires_reconfirmation():
    execute(injection_setup()+r'''
        ["select","Ketamine",0,_drawDisplay] call ACME_fnc_vialSession;
        _medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",1.2]]];
        call ACME_fnc_injectIntoBag;
        [count _notices==1 && {_syringes==2},"real stock loss was ignored"] call _check;
        [(_medic getVariable ["ACME_infusion_PreparedBags",[]]) isEqualTo [],"stock loss injected unconfirmed dose"] call _check;
        call ACME_fnc_injectIntoBag;
        [count (_medic getVariable ["ACME_infusion_PreparedBags",[]])==1,"confirmed correction still loops"] call _check;
    ''')

@pytest.mark.parametrize('stock',[0,2])
def test_full_open_vial_does_not_silently_open_a_spare(stock):
    execute(injection_setup()+f'_inventoryCounts=createHashMapFromArray [["ACM_Vial_Ketamine",{stock}]];'+r'''
        call ACME_fnc_injectIntoBag;
        [_inventoryDebits==0,"endpoint consumed a sealed spare"] call _check;
    '''+f'[_inventoryCounts get "ACM_Vial_Ketamine"=={stock},"spare count changed"] call _check;')

@pytest.mark.parametrize('iv,site,bag_iv,bag_site,blocked',[(True,0,True,0,True),(True,0,True,1,False),(True,0,False,0,False),(False,-1,False,-1,True),(False,-1,True,0,False)])
@pytest.mark.parametrize('volume',[0,0.01,50,100])
def test_preflight_only_blocks_the_exact_occupied_route_even_if_clamped_or_empty(iv,site,bag_iv,bag_site,blocked,volume):
    execute(attach_setup()+f'''
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[["Saline",{volume},1,{bag_site},{str(bag_iv).lower()},-1,100,-1,"bag"]]]]];
        private _why=[_patient,"LeftArm",{str(iv).lower()},{site}] call ACME_fnc_preparedAttachBlockReason;
        [_why=="{'line-occupied' if blocked else ''}","wrong line occupancy result"] call _check;
        if (_why!="") then {{[([_why] call ACME_fnc_preparedAttachMessage) == "There is already a bag on this line.","not concise"] call _check;}};
    ''')


def request_setup():
    src=raw('preparedAttachRequest').replace('findDisplay 86000','objNull')
    src=src.replace('values _inflight','((keys _inflight) apply {_inflight get _x})')
    return attach_setup()+r'''
        private _takenCount=0;
        ACME_fnc_itemTake={_takenCount=_takenCount+1;true};
        ACME_fnc_ownerDispatch={_events pushBack _this;};
    '''+'ACME_fnc_preparedAttachRequest={'+attach_code(src)+'};'

@pytest.mark.parametrize('legacy',[False,True])
def test_occupied_request_never_debits_sends_closes_or_waits(legacy):
    execute(request_setup()+(' _prepared set [15,""];' if legacy else '')+r'''
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[["Saline",100,1,0,true,-1,100,-1,"bag"]]]]];
        [_request] call ACME_fnc_preparedAttachRequest;
        [_takenCount==0 && {count _events==0} && {count _waits==0},"occupied request did work"] call _check;
        [(_notices select 0 select 1)=="There is already a bag on this line.","wrong immediate explanation"] call _check;
    ''')

@pytest.mark.parametrize('legacy',[False,True])
def test_free_line_dispatches_immediately_once_without_timer(legacy):
    execute(request_setup()+(' _prepared set [15,""];' if legacy else '')+r'''
        [_request] call ACME_fnc_preparedAttachRequest;
        [_request] call ACME_fnc_preparedAttachRequest;
        [count _events==1 && {count _waits==0},"not exactly one immediate dispatch"] call _check;
    '''+f'[_takenCount=={1 if legacy else 0},"incorrect pre-ACK custody"] call _check;')


def test_owner_race_rejects_with_same_occupied_message_and_no_orphan():
    execute(attach_setup()+r'''
        [([_patient,"leftarm",true,0] call ACME_fnc_preparedAttachBlockReason)=="","initial local check failed"] call _check;
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[["Saline",50,1,0,true,-1,100,-1,"other"]]]]];
        call _pending;call _send;
        [!(call _ack select 1) && {(call _ack select 3)=="line-occupied"},"owner race ignored"] call _check;
        (call _ack) call ACME_fnc_preparedAttachAck;
        [(_notices select 0 select 1)=="There is already a bag on this line.","race got generic message"] call _check;
        [_factoryCalls==0 && {count (call _stock)==1},"orphan carrier created"] call _check;
    ''')


def suction_setup():
    text=airway_setup()+r'''
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_Count",0];
        _patient setVariable ["ACME_suctionSessions",[["token",_medic,10000,"hand",1,[],[]]]];
        private _serial=0;
        private _drain={params ["_amount"];_serial=_serial+1;
            [_patient,_medic,1,str _serial,([_patient] call ACME_fnc_laryngoFluidState) select 0,_amount,"token"] call ACME_fnc_laryngoFluidDrainLocal;};
        ACME_fnc_sedationOnBoard={0};
    '''+airway_function('laryngoFluidDrainLocal')+airway_function('laryngoIrritationTick')
    src=(ROOT/'addons/airway/functions/fnc_handleAirwayObstruction_Blood.sqf').read_text()
    src=src.replace('IS_UNCONSCIOUS(_patient)','(_patient getVariable ["ACE_isUnconscious",false])').replace('GET_HEART_RATE(_patient)','80')
    src=re.sub(r'\brandom (\d+(?:\.\d+)?)',r'(\1 * _draw)',src)
    text+='ACM_airway_fnc_handleAirwayObstruction_Blood={'+clinical_code(src,'airway')+'};'
    text+=r'''
        private _bleeding=true;
        ACM_damage_fnc_isBodyPartBleeding={_bleeding};
        ACM_damage_fnc_getBodyPartBleeding={0.5};
        ACM_airway_airwayObstructionBloodChance=1;
        private _bloodTick={private _i=_patient getVariable ["ACM_airway_AirwayObstructionBlood_PFH",-1];
            private _h=_handlers select _i;if (_h select 2) then {[_h select 1,_i] call (_h select 0);};};
    '''
    return text.replace('== _medic', 'isEqualTo _medic').replace('== _patient', 'isEqualTo _patient')

@pytest.mark.parametrize('t',[10,10.1,15,30,39.99])
def test_head_wound_does_not_refill_immediately_after_actual_suction(t):
    execute(suction_setup()+r'''
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",2];
        [_patient,1] call ACM_airway_fnc_handleAirwayObstruction_Blood;
        [4] call _drain;
    '''+f'CBA_missionTime={t};call _bloodTick;'+r'''
        [([_patient] call ACME_fnc_laryngoFluidState select 2)==0,"suctioned head blood immediately returned"] call _check;
        [_bleeding,"suction treated the head wound"] call _check;
    ''')


def test_ongoing_head_bleed_returns_one_increment_after_grace_not_a_catchup_pool():
    execute(suction_setup()+r'''
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",3];
        [_patient,1] call ACM_airway_fnc_handleAirwayObstruction_Blood;
        [6] call _drain;CBA_missionTime=70;call _bloodTick;
        [([_patient] call ACME_fnc_laryngoFluidState select 2)==2,"missed time generated catch-up blood"] call _check;
        CBA_missionTime=75;call _bloodTick;
        [([_patient] call ACME_fnc_laryngoFluidState select 2)==2,"new source refilled every 5 seconds"] call _check;
        CBA_missionTime=100;call _bloodTick;
        [([_patient] call ACME_fnc_laryngoFluidState select 2)==4,"ongoing bleeding stopped permanently"] call _check;
    ''')

@pytest.mark.parametrize('hide',[False,True])
def test_partial_blood_suction_is_not_undone_by_a_new_native_increment(hide):
    execute(suction_setup()+r'''
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",2];
        [3.5] call _drain;
    '''+(r'''
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_State",1];
        private _v=[_patient] call ACME_fnc_laryngoFluidState;
        _patient setVariable ["ACME_laryngo_pool",[_v select 0,_v select 2]];
    ''' if hide else '')+r'''
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",3];
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_State",0];
        [abs (([_patient] call ACME_fnc_laryngoFluidState select 2)-2.5)<.000001,"new blood restored removed fluid"] call _check;
    ''')

@pytest.mark.parametrize('t',[11,20,39.99])
def test_irritation_secretions_respect_suction_grace_without_stopping_reflex_episode(t):
    execute(suction_setup()+r'''
        _patient setVariable ["ACME_laryngo_irritationUntil",200];
        _patient setVariable ["ACME_laryngo_secretions",["old",2]];
        [2] call _drain;
    '''+f'CBA_missionTime={t};'+r'''
        [_patient] call ACME_fnc_laryngoIrritationTick;
        [(_patient getVariable ["ACME_laryngo_secretions",[]]) isEqualTo [],"secretions refilled on gag cadence"] call _check;
        [(_patient getVariable ["ACME_laryngo_irritationUntil",0])==200,"episode was erased"] call _check;
    ''')


def test_irritation_recollection_is_bounded_after_clearance():
    execute(suction_setup()+r'''
        _patient setVariable ["ACME_laryngo_irritationUntil",200];
        _patient setVariable ["ACME_laryngo_secretions",["old",2]];[2] call _drain;
        CBA_missionTime=40;[_patient] call ACME_fnc_laryngoIrritationTick;
        [(_patient getVariable "ACME_laryngo_secretions" select 1)==1,"missing gradual recurrence"] call _check;
        CBA_missionTime=45;[_patient] call ACME_fnc_laryngoIrritationTick;
        [(_patient getVariable "ACME_laryngo_secretions" select 1)==1,"rapid repeated recollection"] call _check;
    ''')

@pytest.mark.parametrize('bad',['token','epoch','far','duplicate','empty'])
def test_invalid_or_empty_suction_cannot_keep_resetting_refill_deadline(bad):
    changes={'token':'_token="wrong";','epoch':'_epoch=2;','far':'_distance=6;',
             'duplicate':'_patient setVariable ["ACME_laryngoEventReceipts",["request"]];',
             'empty':'_patient setVariable ["ACM_airway_AirwayObstructionBlood_State",0];'}[bad]
    execute(suction_setup()+r'''
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",2];
        private _token="token";private _epoch=1;
    '''+changes+r'''
        [_patient,_medic,_epoch,"request",([_patient] call ACME_fnc_laryngoFluidState) select 0,1,_token] call ACME_fnc_laryngoFluidDrainLocal;
        [isNil {_patient getVariable "ACME_airwayBloodRefillAt"},"invalid suction reset grace"] call _check;
    ''')

@pytest.mark.parametrize('why',['awake','bleed-controlled','recovery','sga'])
def test_native_protective_conditions_still_stop_recollection(why):
    change={'awake':'_patient setVariable ["ACE_isUnconscious",false];','bleed-controlled':'_bleeding=false;',
            'recovery':'_patient setVariable ["ACM_airway_RecoveryPosition_State",true];',
            'sga':'_patient setVariable ["ACM_airway_AirwayItem_Oral","SGA"];'}[why]
    execute(suction_setup()+r'''
        [_patient,1] call ACM_airway_fnc_handleAirwayObstruction_Blood;
    '''+change+r'''
        CBA_missionTime=100;call _bloodTick;
        [(_patient getVariable ["ACM_airway_AirwayObstructionBlood_State",0])==0,"native blocker ignored"] call _check;
    ''')


def test_no_connection_timer_and_shared_preflight_precedes_source_debit():
    for n in ['givePreparedBag','givePremixedSet']:
        s=raw(n)
        assert 'progressBarAction' not in s
        assert s.index('ACME_fnc_preparedAttachBlockReason') < s.index('ACME_fnc_preparedAttachRequest')
    s=raw('preparedAttachRequest')
    assert s.index('values _inflight') < s.index('ACME_fnc_itemTake')
    assert s.index('ACME_fnc_preparedAttachBlockReason') < s.index('ACME_fnc_itemTake')


def test_refill_fields_are_replicated_save_aware_and_reset_by_clinical_registry():
    s=raw('clinicalFields')
    assert '["ACME_airwayBloodRefillAt", "cba", true]' in s
    assert '["ACME_airwaySecretionRefillAt", "cba", true]' in s
    assert '["ACME_laryngo_bloodRemaining", "", true]' in s


def test_debug_renderer_unchanged_from_b230():
    assert raw('debugMenuClinical') == raw('debugMenuClinical',True)


def test_new_native_blood_after_external_clear_does_not_reuse_old_partial_volume():
    execute(suction_setup()+r'''
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",1];[1.5] call _drain;
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",0];
        [_patient,1] call ACM_airway_fnc_handleAirwayObstruction_Blood;
        CBA_missionTime=40;call _bloodTick;
        [([_patient] call ACME_fnc_laryngoFluidState select 2)==2,"new bleed reused an old partial pool"] call _check;
    ''')


def test_airway_writer_clears_partial_ledger_at_a_compartment_restart():
    execute(suction_setup()+r'''
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",1];[1.5] call _drain;
        [_patient,[["blood",0]],true] call ACM_airway_fnc_setAirwayState;
        [(_patient getVariable ["ACME_laryngo_bloodRemaining",[]]) isEqualTo [],"clear retained old pool"] call _check;
        [_patient,[["blood",1]],true] call ACM_airway_fnc_setAirwayState;
        [([_patient] call ACME_fnc_laryngoFluidState select 2)==2,"fresh traumatic contamination suppressed"] call _check;
    ''')


def test_clearing_blood_does_not_restore_partly_suctioned_overlying_vomit():
    execute(suction_setup()+r'''
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_State",1];
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",1];
        [1.5] call _drain;
        [_patient,[["blood",0]],true] call ACM_airway_fnc_setAirwayState;
        private _state=[_patient] call ACME_fnc_laryngoFluidState;
        [(_state select 1)=="v" && {(_state select 2)==0.5},"clearing blood reset another fluid compartment"] call _check;
    ''')


def test_post_suction_grace_does_not_block_new_explicit_vomit():
    execute(suction_setup()+r'''
        _patient setVariable ["ACM_airway_AirwayObstructionBlood_State",2];[4] call _drain;
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_Count",1];
        CBA_missionTime=11;
        [_patient,_medic,1,"fresh-event","awakeTube"] call ACME_fnc_laryngoConsequenceLocal;
        [([_patient] call ACME_fnc_laryngoFluidState select 1)=="v","suction created global contamination immunity"] call _check;
        [(_patient getVariable "ACME_airwayBloodRefillAt")==40,"new vomit erased blood grace"] call _check;
    ''')
