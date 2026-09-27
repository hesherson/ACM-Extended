"""Execute actual source-funded preparation, refund and syringe-control boundaries.

Config/inventory/UI/transport primitives are explicit stand-ins; transaction
validation, aggregation, rollback, source identity and numeric bounds are real
SQF. No clinical dose or chemical-compatibility claim is made.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import execute
from test_historical_vial_execution import F, source, code, function, setup


def map_loops(text):
    # SQF-VM lacks forEach HASHMAP. Retain the body and expose the same key/value
    # variables while iterating real map keys. These specific bodies contain no break.
    ts=lex(text); pairs=matching(ts); rev={v:k for k,v in pairs.items()};edits=[]
    for i,t in enumerate(ts[:-1]):
        if t.value=='forEach' and ts[i+1].value=='_needByMed':
            assert ts[i-1].value=='}'; opening=rev[i-1]
            edits.append((ts[opening].offset+1,ts[opening].offset+1,'private _y = _needByMed get _x;'))
            edits.append((ts[i+1].offset,ts[i+1].offset+len('_needByMed'),'(keys _needByMed)'))
    for a,b,new in sorted(edits,reverse=True):text=text[:a]+new+text[b:]
    return text


def prep_code(text):
    text=map_loops(text)
    # VM rejects an isNil CODE body ending in a void assignment. Its Boolean
    # result is unused here; a terminal sentinel preserves the same scope/writes.
    text=text.replace('_result = true;\n};', '_result = true;\nfalse\n};')
    text=text.replace('finite (_x select 1)','((_x select 1) call _finite)')
    text=re.sub(r'(_\w+) displayCtrl \d+','objNull',text)
    text=text.replace('_medic removeItem _container;','[_medic,_container] call _removeItem;')
    text=text.replace('getMousePosition','[0.5,0.5]')
    return code(text)


def prep_function(name):return 'ACME_fnc_'+name+'={'+prep_code(source(name))+'};\n'


def transaction_setup():
    return setup()+'''
        _inventoryCounts set ["ACM_Vial_Propofol",1];
        _inventoryCounts set ["ACM_Syringe_10",1];
        _inventoryCounts set ["ACM_SalineFlush_10",1];
        _configNumber={params ["_med","_field"];
            if !(_med in ["Ketamine","Propofol"]) exitWith {0};
            if (_field=="volume") then {10} else {if (_med=="Ketamine") then {50} else {10}}};
        ace_common_fnc_getCountOfItem={[_inventoryCounts,[_this select 1,0]] call _mapDefault};
        ace_common_fnc_addToInventory={params ["_p","_item"]; _inventoryCounts set [_item,([_inventoryCounts,[_item,0]] call _mapDefault)+1];};
        ACME_fnc_vialHolder={_medic};
        ACME_fnc_treatmentSupplyCount={[_this select 0,_this select 2] call ace_common_fnc_getCountOfItem};
        ACME_fnc_treatmentSupplyTake={params ["_m","_p","_items"]; private _item=_items select 0;
            if (([_m,_item] call ace_common_fnc_getCountOfItem)<1) exitWith {[]};
            [_m,_item] call _removeItem; [_m,_item,objNull,"item-receipt"]};
        ACME_fnc_treatmentSupplyRefund={params ["_receipt",["_refund",true]];
            if (_refund) then {[_receipt select 0,_receipt select 1] call ace_common_fnc_addToInventory;}; true};
        ACME_fnc_ownerDispatch={_events pushBack _this; params ["_holder","_op","_args"];
            if (_op=="vialRefund") then {[_holder,_args param [0,""],_args param [1,[]]] call ACME_fnc_vialRefundLocal;};};
    '''+''.join(prep_function(n) for n in ('medicationTakeSources','infusionTakeSupplies','infusionRefundSupplies'))


@pytest.mark.parametrize('parts',[
    '[]','[["",1]]','[["Ketamine",0]]','[["Ketamine",-1]]','[["Ketamine"]]',
    '[["Unknown",1]]','[["Ketamine",5],["Propofol",11]]','[["Ketamine",12],["Ketamine",10]]'])
def test_complete_source_validation_precedes_any_component_or_container_debit(parts):
    execute(transaction_setup()+f'private _result=[_medic,{parts},"ACM_Syringe_10",true] call ACME_fnc_medicationTakeSources;'+'''
        [!_result,"invalid complete batch accepted"] call _check;
        [_stockWrites==0 && {_inventoryDebits==0},"failed validation consumed some inventory"] call _check;
        [(_inventoryCounts get "ACM_Syringe_10")==1,"failed batch consumed barrel"] call _check;
    ''')


@pytest.mark.parametrize('consume',[False,True])
def test_repeated_components_aggregate_before_debit_and_reusable_container_is_retained(consume):
    execute(transaction_setup()+f'private _consume={str(consume).lower()};'+'''
        private _okResult=[_medic,[["Ketamine",2],["Propofol",3],["Ketamine",4]],"ACM_Syringe_10",_consume] call ACME_fnc_medicationTakeSources;
        [_okResult,"funded combination rejected"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==14,"repeated ketamine component not aggregated"] call _check;
        [([_medic,"Propofol"] call ACME_fnc_infusionVialVolume)==7,"propofol debit wrong"] call _check;
        [(_inventoryCounts get "ACM_Syringe_10")==([1,0] select _consume),"reusable/disposable container rule changed"] call _check;
        [_stockWrites==2,"same drug debited separately instead of complete aggregated need"] call _check;
    ''')


def test_missing_container_rejects_without_touching_source_even_when_reusable():
    execute(transaction_setup()+'''
        _inventoryCounts set ["ACM_Syringe_10",0];
        [!([_medic,[["Ketamine",2]],"ACM_Syringe_10",false] call ACME_fnc_medicationTakeSources),"missing reusable barrel accepted"] call _check;
        [_stockWrites==0 && {_inventoryDebits==0},"missing barrel consumed medication"] call _check;
    ''')


def test_late_component_failure_refunds_previously_debited_solution_and_preserves_barrel():
    execute(transaction_setup()+'''
        private _realTake=ACME_fnc_vialTake; private _calls=0;
        ACME_fnc_vialTake={_calls=_calls+1; if (_calls==2) exitWith {false}; _this call _realTake};
        private _result=[_medic,[["Ketamine",2],["Propofol",3]],"ACM_Syringe_10",true] call ACME_fnc_medicationTakeSources;
        [!_result && {_calls==2},"late failure not reported"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==20,"rollback lost ketamine"] call _check;
        [([_medic,"Propofol"] call ACME_fnc_infusionVialVolume)==10,"rollback lost propofol"] call _check;
        [(_inventoryCounts get "ACM_Syringe_10")==1,"rollback lost barrel"] call _check;
    ''')


@pytest.mark.parametrize('reusable',[False,True])
def test_preparation_receipt_refunds_original_provider_after_control_switch(reusable):
    execute(transaction_setup()+f'missionNamespace setVariable ["ACM_circulation_reusableSyringe",{str(reusable).lower()}];'+'''
        private _receipt=[_medic,"Ketamine",3,10] call ACME_fnc_infusionTakeSupplies;
        [count _receipt==4,"supplies receipt missing"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==17,"supplies not debited"] call _check;
        ACE_player=_patient;
        [_receipt] call ACME_fnc_infusionRefundSupplies;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==20,"late receipt lost original provider medication"] call _check;
        [(_inventoryCounts get "ACM_Syringe_10")==1,"late receipt lost/duplicated barrel"] call _check;
        [count (keys (_patient getVariable ["ACME_infusion_openVials",createHashMap]))==0,"refund went to newly controlled patient"] call _check;
    ''')


def commit_setup():
    return transaction_setup()+''.join(prep_function(n) for n in ('skCompoundCommit','skFlushSave','skWasteDraw'))+'''
        _drawDisplay=missionNamespace;
        private _storeWrites=0; private _specialEpiCalls=0;
        private _limit=20;
        ACME_fnc_vialSession={if ((_this select 0)=="clear") then {0} else {_limit}};
        ACME_fnc_skCompoundLabel={"Generic compound label"};
        ACME_fnc_skApplyPendingTag={_this select 0};
        ACME_fnc_skPendingTagCommit={}; ACME_fnc_skRefreshDrawn={};
        ACME_fnc_narcStoreCommit={params ["_p","_s"];_p setVariable ["ACME_narcStore",_s];_storeWrites=_storeWrites+1;};
        ACME_fnc_epinephrineRecipe={false};
        ACME_fnc_epinephrinePrepare={_specialEpiCalls=_specialEpiCalls+1;true};
        uiNamespace setVariable ["ACME_SK_WasteCap",10];
        uiNamespace setVariable ["ACME_SK_WasteNS",5];
        uiNamespace setVariable ["ACME_SK_WasteStage","draw"];
    '''


@pytest.mark.parametrize('capacity,parts',[(2,'[["Ketamine",1]]'),(10,'[["Ketamine",10.01]]'),(10,'[["Ketamine",0]]')])
def test_invalid_compound_capacity_or_components_cannot_reach_inventory_or_store(capacity,parts):
    execute(commit_setup()+f'uiNamespace setVariable ["ACME_SK_WasteCap",{capacity}]; uiNamespace setVariable ["ACME_SK_CompoundComponents",{parts}];'+'''
        [!(call ACME_fnc_skCompoundCommit),"invalid compound accepted"] call _check;
        [_stockWrites==0 && {_storeWrites==0} && {_inventoryDebits==0},"invalid compound mutated inventory"] call _check;
    ''')


def test_compound_save_commits_every_component_once_and_repeated_save_does_not_duplicate():
    execute(commit_setup()+'''
        private _parts=[["Ketamine",2],["Propofol",3],["Ketamine",1]];
        uiNamespace setVariable ["ACME_SK_CompoundComponents",_parts];
        [call ACME_fnc_skCompoundCommit,"compound commit rejected"] call _check;
        [!(call ACME_fnc_skCompoundCommit),"same compound committed twice"] call _check;
        private _store=_medic getVariable ["ACME_narcStore",[]];
        [count _store==1 && {_storeWrites==1},"duplicate saved syringe"] call _check;
        private _row=_store select 0;
        [(_row select 2)==6 && {(_row select 5) isEqualTo _parts} && {(_row select 6)=="compoundB13"},"compound payload lost composition"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==17 && {([_medic,"Propofol"] call ACME_fnc_infusionVialVolume)==7},"wrong component debit"] call _check;
    ''')


def test_flush_draw_only_stages_and_save_funds_all_components_and_saline_carrier():
    execute(commit_setup()+'''
        uiNamespace setVariable ["ACME_SK_WasteFloorMl",5];
        uiNamespace setVariable ["ACME_SK_WasteFill",7];
        ACM_circulation_SyringeDraw_DrawnAmount=7;
        ACM_circulation_SyringeDraw_Medication="Ketamine";
        call ACME_fnc_skWasteDraw;
        [_inventoryDebits==0 && {_stockWrites==0},"draw stage consumed before save"] call _check;
        uiNamespace setVariable ["ACME_SK_WasteFill",8];
        ACM_circulation_SyringeDraw_Medication="Propofol";
        call ACME_fnc_skWasteDraw;
        call ACME_fnc_skFlushSave;
        private _row=(_medic getVariable ["ACME_narcStore",[]]) select 0;
        [(_row select 2)==3 && {(_row select 4)==5} && {(_row select 5) isEqualTo [["Ketamine",2],["Propofol",1]]},"flush lost saline or components"] call _check;
        [(_row select 6)=="dilutionB13" && {(_row select 12)=="flush"},"flush marker lost"] call _check;
        [(_inventoryCounts get "ACM_SalineFlush_10")==0 && {(_inventoryCounts get "ACM_Syringe_10")==1},"flush consumed wrong container"] call _check;
        [_specialEpiCalls==0,"generic mixture redirected through named-recipe gate"] call _check;
    ''')


def test_flush_session_limit_rejection_cannot_consume_carrier_or_source():
    execute(commit_setup()+'''
        _limit=1;
        uiNamespace setVariable ["ACME_SK_CompoundComponents",[["Ketamine",2]]];
        call ACME_fnc_skFlushSave;
        [_stockWrites==0 && {_storeWrites==0} && {_inventoryDebits==0},"flush exceeded selected vial quota"] call _check;
    ''')


def ui_code(text):
    # The unsupported affine primitive is mocked with its same arguments.
    ts=lex(text); pairs=matching(ts); edits=[]
    for i,t in enumerate(ts[:-1]):
        if t.kind=='ident' and t.value=='linearConversion':
            assert ts[i+1].value=='[';end=pairs[i+1]
            edits.append((t.offset,ts[end].offset+1,'('+text[ts[i+1].offset:ts[end].offset+1]+' call _linear)'))
    for a,b,new in reversed(edits):text=text[:a]+new+text[b:]
    text=text.replace('ctrlPosition _hit','(_hit getVariable ["position",[]])').replace('ctrlPosition _visual','(_visual getVariable ["position",[]])')
    text=text.replace('_display displayCtrl 84009','_hitCtrl').replace('_display displayCtrl _visualIdc','_visualCtrl')
    text=re.sub(r'(_\w+) ctrlSetPosition (\[[^;]+\]);',r'\1 setVariable ["position",\2];',text)
    text=re.sub(r'_\w+ ctrlCommit 0;','',text)
    return code(text)


def ui_setup():
    return setup()+'''
        _drawDisplay=missionNamespace;
        private _hitCtrl=uiNamespace; private _visualCtrl=profileNamespace;
        _hitCtrl setVariable ["position",[0.2,0.1,0.05,0.02]];
        _visualCtrl setVariable ["position",[0.25,0.07,0.08,0.06]];
        private _linear={params ["_lo","_hi","_x","_a","_b","_clamp"];
            private _f=(_x-_lo)/(_hi-_lo); if (_clamp) then {_f=(_f max 0) min 1;}; _a+(_f*(_b-_a))};
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitTop",0.1];
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitBottom",0.5];
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_Ctrl_PlungerVisual",84010];
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_Ctrl_PlungerAdjustment",0.03];
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_Moving",true];
    '''+'ACME_fnc_syringeDrawSetAmount={'+ui_code(source('syringeDrawSetAmount'))+'};'


@pytest.mark.parametrize('size',[1,3,5,10])
@pytest.mark.parametrize('fraction',[-0.2,0,0.25,1,1.2])
def test_syringe_amount_correction_keeps_hitbox_art_and_numeric_fill_together(size,fraction):
    expected=max(0,min(size,size*fraction))
    execute(ui_setup()+f'missionNamespace setVariable ["ACM_circulation_SyringeDraw_Size",{size}];'+
        f'private _result=[{size*fraction},_drawDisplay,true] call ACME_fnc_syringeDrawSetAmount;'+
        f'private _expected={expected};'+'''
        [_result,"amount correction rejected"] call _check;
        private _amount=missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount",-1];
        private _hitY=(_hitCtrl getVariable ["position",[]]) select 1;
        private _visualY=(_visualCtrl getVariable ["position",[]]) select 1;
        [abs (_amount-_expected)<0.000001,"numeric amount wrong"] call _check;
        [abs (_hitY-(0.1+0.4*(_expected/(missionNamespace getVariable ["ACM_circulation_SyringeDraw_Size",10]))))<0.000001,"hitbox not aligned with amount"] call _check;
        [abs (_visualY-(_hitY-0.03))<0.000001,"visible plunger not aligned with hitbox"] call _check;
        [!(missionNamespace getVariable ["ACM_circulation_SyringeDraw_Moving",true]),"forced correction left draw moving"] call _check;
    ''')


def inject_setup():
    text=source('injectIntoBag')
    text=text.replace('getNumber (_med >> "concentration")','([_med,"concentration"] call _configNumber)')
    # Replace this specific config read before the common concentration-node adapter.
    text=text.replace('getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _med >> "concentration")','([_med,"concentration"] call _configNumber)')
    return transaction_setup()+'ACME_fnc_injectIntoBag={'+prep_code(text)+'};'+'''
        _drawDisplay=missionNamespace;
        private _clamps=[]; private _bagWrites=[]; private _notices=0;
        private _limit=10; private _bagAccept=true;
        ACME_fnc_vialHolder={_medic};
        ACME_fnc_vialSession={_limit};
        ACME_fnc_syringeDrawSetAmount={_clamps pushBack _this;};
        ACME_fnc_clinicalNotice={_notices=_notices+1;};
        ACME_fnc_registerPreparedBag={_bagWrites pushBack _this;_bagAccept};
        ACME_fnc_infusionRefreshTally={};
        private _context=["prepared"];
        _context resize 22;_context set [1,_patient];_context set [20,"bag-1"];
        _medic setVariable ["ACME_preparedIVSets",[["bag-1"]]];
        missionNamespace setVariable ["ACME_infusion_pendingContext",_context];
        missionNamespace setVariable ["ACME_infusion_allowedMedications",["Ketamine","Propofol"]];
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_Size",10];
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_Medication","Ketamine"];
    '''


@pytest.mark.parametrize('limit,stock,drawn',[(2,20,3),(10,2,3),(1,20,1.5)])
def test_bag_injection_over_available_stock_or_explicit_quota_requires_reconfirmation(limit,stock,drawn):
    execute(inject_setup()+f'_limit={limit}; _inventoryCounts set ["ACM_Vial_Ketamine",0];'+
        f'_medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",{stock}]]];'+
        f'missionNamespace setVariable ["ACM_circulation_SyringeDraw_DrawnAmount",{drawn}];'+'''
        call ACME_fnc_injectIntoBag;
        [_stockWrites==0 && {_inventoryDebits==0} && {count _bagWrites==0},"overdraw silently administered"] call _check;
        [count _clamps==1 && {_notices==1},"overdraw was not corrected for reconfirmation"] call _check;
    '''+f'[((_clamps select 0) select 0)=={min(limit,stock,10)},"wrong correction limit"] call _check;')


@pytest.mark.parametrize('blocked',[
    'missionNamespace setVariable ["ACM_circulation_SyringeDraw_Moving",true];',
    'missionNamespace setVariable ["ACME_infusion_pendingInject","pending"];',
    '_medic setVariable ["ACME_preparedIVSets",[]];',
    '_inventoryCounts set ["ACM_Syringe_10",0];',
])
def test_bag_injection_refuses_inflight_missing_bag_or_missing_barrel_before_debit(blocked):
    execute(inject_setup()+'''
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_DrawnAmount",2];
    '''+blocked+'''
        call ACME_fnc_injectIntoBag;
        [_stockWrites==0 && {_inventoryDebits==0} && {count _bagWrites==0},"invalid injection changed inventory or bag"] call _check;
    ''')


@pytest.mark.parametrize('accept',[False,True])
def test_bag_injection_preserves_selected_identity_rounds_source_ml_before_debit_and_refunds_rejection(accept):
    execute(inject_setup()+f'_bagAccept={str(accept).lower()};'+'''
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_DrawnAmount",1.237];
        call ACME_fnc_injectIntoBag;
        [count _bagWrites==1,"bag request missing"] call _check;
        private _request=_bagWrites select 0;
        [(_request select 1)=="Ketamine","source identity changed"] call _check;
        [abs ((_request select 2)-62)<0.000001 && {abs ((_request select 3)-1.24)<0.000001},"source volume/dose disagree"] call _check;
        private _expected=if (_bagAccept) then {18.76} else {20};
        [abs (([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)-_expected)<0.000001,"bag source mass lost/created"] call _check;
        [(_inventoryCounts get "ACM_Syringe_10")==([1,0] select _bagAccept),"rejected bag lost container or accepted one retained it"] call _check;
        [count _clamps==([0,1] select _bagAccept),"rejected request cleared UI dose"] call _check;
    ''')


def line_setup():
    # Reuse only the primitive adapter for real linearConversion arguments.
    # The whole owner settlement function, receipts and flush queue run unchanged.
    return ui_setup()+'ACME_fnc_medicationLineLocal={'+ui_code(source('medicationLineLocal').replace('finite (_x select 1)','((_x select 1) call _finite)'))+'};'+'''
        private _lineIdentity=[0,3,100]; private _fraction=1;
        private _deliveries=[]; private _leaks=[]; private _runtime=[]; private _enrolments=0;
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",1]};
        ACME_fnc_medicationRouteAllowed={true};
        ACME_fnc_medicationLineIdentity={_lineIdentity};
        ACME_fnc_medicationLineBloodBusy={false};
        ACME_fnc_medicationLineFraction={_fraction};
        ACME_fnc_medicationLeak={_leaks pushBack _this;};
        ace_medical_treatment_fnc_medicationLocal={_deliveries pushBack _this;};
        ACM_circulation_fnc_setRuntimeState={_runtime append (_this select 1);};
        ace_medical_treatment_fnc_addToTriageCard={};
        ACME_fnc_ownerRegister={_enrolments=_enrolments+1;};
        ACME_fnc_ioPainResponse={};
        missionNamespace setVariable ["ACME_flushReqMeds",["Ketamine","Propofol"]];
    '''


@pytest.mark.parametrize('iv',[True,False])
@pytest.mark.parametrize('fraction',[0,0.6,1])
def test_actual_route_and_prepared_metadata_survive_owner_delivery_without_dose_duplication(iv,fraction):
    execute(line_setup()+f'private _iv={str(iv).lower()}; _fraction={fraction};'+'''
        missionNamespace setVariable ["ACME_flushReqEnabled",false];
        private _doses=[["Ketamine_IV",2,_iv,"mix",30,true,["rate","first"]],["Propofol_IV",3,_iv,"mix",30,true,["rate","second"]]];
        private _site=if (_iv) then {0} else {-2};
        private _identity=if (_iv) then {_lineIdentity} else {[]};
        [_patient,_medic,1,"dose-1","administer","leftarm",_doses,_site,_identity] call ACME_fnc_medicationLineLocal;
        [_patient,_medic,1,"dose-1","administer","leftarm",_doses,_site,_identity] call ACME_fnc_medicationLineLocal;
        private _effective=if (_iv) then {_fraction} else {1};
        [count _deliveries==([0,2] select (_effective>0)),"duplicate or missing delivery"] call _check;
        private _sum=0;
        {
            _sum=_sum+(_x select 3);
            [(_x select 4) isEqualTo _iv,"route flag changed"] call _check;
            private _meta=_x select 6;
            [(_meta select 0)==_site && {(_meta select 1) isEqualTo _identity} && {(_meta select 2)==30} && {(_meta select 4)},"catheter/duration/mixture metadata lost"] call _check;
            [count (_meta select 5)==2,"rate metadata dropped"] call _check;
        } forEach _deliveries;
        [abs (_sum-(5*_effective))<0.000001,"systemic dose wrong"] call _check;
        private _lost=0; {_lost=_lost+(_x select 4);} forEach _leaks;
        [abs (_sum+_lost-5)<0.000001,"systemic/leaked mass not conserved"] call _check;
        [_enrolments==1,"duplicate request re-enrolled patient"] call _check;
    ''')


def test_flush_queue_preserves_actual_route_mixture_and_rate_metadata_and_drains_once():
    execute(line_setup()+'''
        private _doses=[["Ketamine_IV",2,true,"mix",30,true,["rate","first"]],["Propofol_IV",3,true,"mix",20,true,["rate","second"]]];
        [_patient,_medic,1,"park","administer","leftarm",_doses,0,_lineIdentity] call ACME_fnc_medicationLineLocal;
        [count _deliveries==0 && {count (_patient getVariable ["ACME_pendingFlush",[]])==2},"parked drug delivered before flush"] call _check;
        [_patient,_medic,1,"flush","flush","leftarm",[],0,_lineIdentity] call ACME_fnc_medicationLineLocal;
        [_patient,_medic,1,"flush","flush","leftarm",[],0,_lineIdentity] call ACME_fnc_medicationLineLocal;
        [count _deliveries==2 && {(_patient getVariable ["ACME_pendingFlush",[]]) isEqualTo []},"flush duplicated or retained dose"] call _check;
        {
            private _meta=_x select 6;
            [(_x select 4) && {(_meta select 4)} && {count (_meta select 5)==2},"flush lost route/mixture/rate metadata"] call _check;
        } forEach _deliveries;
        [count _runtime==1 && {((_runtime select 0) select 1)==0.01},"duplicate flush double-credited saline"] call _check;
    ''')


@pytest.mark.parametrize('mutation',[
    '_lineIdentity=[0,4,101];',
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_alive=false;',
    '_medic setVariable ["ACE_isUnconscious",true];',
])
def test_replaced_catheter_or_new_episode_cannot_release_queued_medication(mutation):
    execute(line_setup()+'''
        private _original=+_lineIdentity;
        [_patient,_medic,1,"park","administer","leftarm",[["Ketamine_IV",2,true,"mix",30,true]],0,_original] call ACME_fnc_medicationLineLocal;
        private _pending=+(_patient getVariable ["ACME_pendingFlush",[]]);
    '''+mutation+'''
        [_patient,_medic,1,"flush","flush","leftarm",[],0,_original] call ACME_fnc_medicationLineLocal;
        [count _deliveries==0 && {count _runtime==0},"invalid flush delivered medication/carrier"] call _check;
        [(_patient getVariable ["ACME_pendingFlush",[]]) isEqualTo _pending,"invalid flush discarded queued medication"] call _check;
    ''')


def test_postmortem_medication_acknowledges_once_without_adding_physiology():
    execute(line_setup()+'''
        _patientAlive=false;
        [_patient,_medic,1,"dead","administer","leftarm",[["Ketamine_IV",2,true,"mix",30,true]],0,_lineIdentity] call ACME_fnc_medicationLineLocal;
        [_patient,_medic,1,"dead","administer","leftarm",[["Ketamine_IV",2,true,"mix",30,true]],0,_lineIdentity] call ACME_fnc_medicationLineLocal;
        [count _deliveries==0 && {count _leaks==0} && {count _runtime==0} && {_enrolments==0},"corpse treatment restarted physiology"] call _check;
        [count (keys (_patient getVariable ["ACME_medicationReceiptsB14",createHashMap]))==1,"duplicate corpse receipt"] call _check;
        [count _events==2 && {(((_events select 0) select 1) select 2)},"corpse transaction not acknowledged"] call _check;
    ''')


def test_compound_save_reuses_the_same_dialog_and_does_not_recommit_on_repeated_event():
    execute(commit_setup()+prep_function('skCompoundSave')+'''
        private _begins=0;private _refreshes=0;private _resets=0;
        ACME_fnc_skCompoundBegin={_begins=_begins+1;};
        ACME_fnc_skListRefresh={_refreshes=_refreshes+1;};
        ACME_fnc_skPendingTagReset={_resets=_resets+1;};
        ACME_fnc_skPendingTagRender={};
        uiNamespace setVariable ["ACME_SK_WasteStage","compound"];
        uiNamespace setVariable ["ACME_SK_CompoundComponents",[["Ketamine",2]]];
        _dialog=true;
        call ACME_fnc_skCompoundSave;
        [_dialog && {_begins==1} && {_refreshes==1} && {_resets==1},"save closed dialog or delayed fresh draw state"] call _check;
        call ACME_fnc_skCompoundSave;
        [_storeWrites==1 && {_begins==1},"repeat save duplicated dose or reset fresh state"] call _check;
        [count _waits==0,"headless-control save introduced blocking delay"] call _check;
    ''')
