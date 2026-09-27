"""Execute actual preparation, donor settlement, plunger and partial-push SQF.

UI controls, engine inventory, ACE useItem and transport are explicit fixtures.
Source leases, owner queues, dose arithmetic and stop/ACK settlement execute;
these checks do not claim live rendering or real multiplayer transport coverage.
"""
import re
import pytest
from test_menu_death_lifecycle import execute, adapt
from test_historical_medication_preparation import commit_setup, transaction_setup, prep_code, ui_setup, ui_code
from test_historical_vial_execution import F, source, setup


def test_saved_flush_cannot_debit_a_second_flush_before_delayed_feedback_finishes():
    execute(commit_setup()+'''
        _inventoryCounts set ["ACM_SalineFlush_10",2];
        uiNamespace setVariable ["ACME_SK_CompoundComponents",[["Ketamine",2]]];
        call ACME_fnc_skFlushSave;
        call ACME_fnc_skFlushSave;
        [_storeWrites==1,"repeat flush save created a duplicate syringe"] call _check;
        [(_inventoryCounts get "ACM_SalineFlush_10")==1,"repeat flush save consumed another container"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==18,"repeat flush save consumed another source dose"] call _check;
    ''')


def test_last_hundredth_waits_for_its_requested_push_time_before_moving():
    tick=prep_code(source('hardcorePushTick').replace('_patient distance _medic','_distance'))
    execute(setup()+'ACME_fnc_hardcorePushTick={'+tick+'};'+'''
        _drawDisplay=objNull;
        private _stops=[];
        ACME_fnc_hardcorePushStop={_stops pushBack _this;};
        ACME_fnc_hardcorePushOverlay={};
        ACME_fnc_hardcorePushSendBatch={true};
        ACME_fnc_medicationLineIdentity={[0,1,1]};
        ACME_fnc_medicationLineBloodBusy={false};
        missionNamespace setVariable ["ACME_hcEff_medications",true];
        private _row=["Ketamine",1,0.01,"",0,[],"","none","","","","slow-final"];
        _medic setVariable ["ACME_narcStore",[_row]];
        private _job=createHashMapFromArray [
            ["medic",_medic],["patient",_patient],["flowing",true],
            ["identity",[0,1,1]],["stableId","slow-final"],
            ["targetMl",0.01],["rateMlSec",0.01/300],
            ["pushedMl",0],["carryMl",0],["lastTick",10]
        ];
        missionNamespace setVariable ["ACME_HCMedPushJob",_job];
        _nowTime=10.05;
        call ACME_fnc_hardcorePushTick;
        private _remaining=(_medic getVariable ["ACME_narcStore",[]]) select 0 select 2;
        [_remaining==0.01 && {count _stops==0},"last aliquot ignored the typed push duration"] call _check;
        _job=missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
        _job set ["carryMl",0.01-(0.01/300*0.05)];
        _nowTime=10.10;
        call ACME_fnc_hardcorePushTick;
        private _finished=(_medic getVariable ["ACME_narcStore",[]]) select 0 select 2;
        [abs _finished<0.000001 && {count _stops==1},"final aliquot failed to finish after its time accrued"] call _check;
    ''')


def test_patient_vial_and_container_receipts_refund_the_same_donors_after_close_once():
    execute(transaction_setup()+'''
        private _chosenHolder=_patient; ACME_fnc_vialHolder={_chosenHolder};
        private _returned=[];
        ACME_fnc_treatmentSupplyTake={params ["_m","_p","_items"];
            [_p isEqualTo _patient,"container did not receive the selected patient"] call _check;
            [_p,_items select 0] call _removeItem; [_p,_items select 0,objNull,"patient-container"]};
        ACME_fnc_treatmentSupplyRefund={params ["_r",["_refund",true]];
            if (_refund) then {_returned pushBack _r; [_r select 0,_r select 1] call ace_common_fnc_addToInventory;}; true};
        uiNamespace setVariable ["ACME_SK_Patient",_patient];
        missionNamespace setVariable ["ACME_vialLeaseAccepted",[_patient,"lease",20]];
        _inventoryCounts set ["ACM_Vial_Ketamine",0];
        _medic setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",3]]];
        _patient setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",5]]];
        private _receipt=[_medic,"Ketamine",2.5,10] call ACME_fnc_infusionTakeSupplies;
        [count _receipt==4,"selected patient preparation rejected"] call _check;
        [([_patient,"Ketamine"] call ACME_fnc_infusionVialVolume)==2.5,"selected patient was not debited"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==3,"provider vial was debited instead"] call _check;
        missionNamespace setVariable ["ACME_vialLeaseAccepted",[]];
        ACE_player=missionNamespace;
        [_receipt] call ACME_fnc_infusionRefundSupplies;
        [_receipt] call ACME_fnc_infusionRefundSupplies;
        [([_patient,"Ketamine"] call ACME_fnc_infusionVialVolume)==5,"late or duplicate ACK changed source mass"] call _check;
        [count _returned==1 && {((_returned select 0) select 0) isEqualTo _patient},"late refund changed or duplicated container donor"] call _check;
        [(_inventoryCounts get "ACM_Syringe_10")==1,"late container refund lost or created stock"] call _check;
    ''')


def test_missing_patient_lease_does_not_consume_the_container_or_another_vial():
    execute(transaction_setup()+'''
        private _chosenHolder=_patient; ACME_fnc_vialHolder={_chosenHolder};
        _patient setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",5]]];
        private _receipt=[_medic,"Ketamine",2,10] call ACME_fnc_infusionTakeSupplies;
        [_receipt isEqualTo [] && {_stockWrites==0} && {_inventoryDebits==0},"unleased patient source was consumed"] call _check;
    ''')


def test_container_race_rolls_back_exact_source_volume():
    execute(transaction_setup()+'''
        ACME_fnc_treatmentSupplyTake={[]};
        private _receipt=[_medic,"Ketamine",2,10] call ACME_fnc_infusionTakeSupplies;
        [_receipt isEqualTo [],"missing container accepted"] call _check;
        [([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)==20,"late missing container lost source volume"] call _check;
        [(_inventoryCounts get "ACM_Syringe_10")==1,"failed container reservation changed container"] call _check;
    ''')


@pytest.mark.parametrize('dose,ammo',[(1.237,124),(1.231,123),(0.004,0)])
def test_native_preparation_debits_the_exact_stored_magazine_volume(dose,ammo):
    native=(F.parents[1]/'circulation/functions/fnc_Syringe_PrepareFinish.sqf').read_text()
    execute(transaction_setup()+'private _prepare={'+prep_code(native)+'};'+'''
        private _magazines=[];
        ace_common_fnc_addToInventory={_magazines pushBack _this;};
    '''+f'[_medic,"Ketamine",{dose},10] call _prepare;'+f'''
        [count _magazines=={int(ammo>0)},"wrong filled magazine count"] call _check;
        [abs (([_medic,"Ketamine"] call ACME_fnc_infusionVialVolume)-(20-{ammo}/100))<0.000001,"vial debit differs from stored volume"] call _check;
    '''+(f'[((_magazines select 0) select 3)=={ammo},"wrong stored magazine volume"] call _check;' if ammo else ''))


@pytest.mark.parametrize('opened_size,current_size',[(10,1),(1,10),(10,3),(3,5)])
def test_native_drag_uses_current_in_place_barrel_capacity(opened_size,current_size):
    native=(F.parents[1]/'circulation/functions/fnc_Syringe_Draw.sqf').read_text()
    mover=native.split('if (GVAR(SyringeDraw_Moving)) then {',1)[1].split('\n    };\n}, true',1)[0]
    mover=mover.replace('_display displayCtrl IDC_SYRINGEDRAW_PLUNGER','_hitCtrl')
    mover=mover.replace('_display displayCtrl GVAR(SyringeDraw_Ctrl_PlungerVisual)','_visualCtrl')
    mover=mover.replace('ctrlPosition _ctrlPlungerVisual','(_visualCtrl getVariable ["position",[]])')
    mover=mover.replace('ctrlPosition _ctrlPlunger','(_hitCtrl getVariable ["position",[]])')
    mover=mover.replace('getResolution','[0,0,0,0,0,0.55]').replace('getMousePosition','[0.5,0.51]').replace('pixelH','0.001')
    mover=re.sub(r'setMousePosition \[[^;]*;','',mover)
    mover=ui_code(adapt(mover,'circulation'))
    execute(ui_setup()+f'''
        private _size={opened_size};
        ACM_circulation_SyringeDraw_Size={current_size};
        ACM_circulation_SyringeDraw_MaxDose=10;
        ACM_circulation_SyringeDraw_Medication="Ketamine";
        ACM_circulation_SyringeDraw_DrawnAmount=0;
        uiNamespace setVariable ["ACM_circulation_SyringeDraw_DLG",_drawDisplay];
        ACME_fnc_vialSession={{10}};
    '''+mover+f'''
        [abs (ACM_circulation_SyringeDraw_DrawnAmount-{current_size})<0.000001,"drag used the originally opened size"] call _check;
        [abs (((_hitCtrl getVariable ["position",[]]) select 1)-0.5)<0.000001,"full current barrel stopped at old-size geometry"] call _check;
        [abs (((_visualCtrl getVariable ["position",[]]) select 1)-0.47)<0.000001,"current plunger art diverged from fill"] call _check;
    ''')


@pytest.mark.parametrize('state',[
    'ACM_circulation_SyringeDraw_DrawnAmount=1;',
    'uiNamespace setVariable ["ACME_SK_CompoundComponents",[["Ketamine",1]]];',
])
def test_source_cannot_change_while_drawn_solution_belongs_to_it(state):
    native=(F.parents[1]/'circulation/functions/fnc_Syringe_SwitchTargetInventory.sqf').read_text()
    execute('private _switch={'+adapt(native,'circulation')+'};'+'''
        ACM_circulation_SyringeDraw_Target=_patient;
        ACM_circulation_SyringeDraw_InventorySelection=1;
        ACM_circulation_SyringeDraw_DrawnAmount=0;
        private _released=0; ACME_fnc_vialLeaseRelease={_released=_released+1;};
    '''+state+'''
        call _switch;
        [ACM_circulation_SyringeDraw_InventorySelection==1 && {_released==0},"drawn source switched before settlement"] call _check;
    ''')


@pytest.mark.parametrize('closed',[False,True])
def test_patient_source_fallback_cannot_debit_provider_for_an_existing_draw(closed):
    execute(transaction_setup()+'''
        _drawDisplay=missionNamespace;
        _drawDisplay setVariable ["ACME_SK_VialHolder",_patient];
        uiNamespace setVariable ["ACME_SK_VialHolder",_patient];
        // The resolver falls back to Self when the selected patient is gone.
        ACME_fnc_vialHolder={_medic};
    '''+('_drawDisplay=objNull;' if closed else '')+'''
        [!([_medic,[["Ketamine",2]],"ACM_Syringe_10",true] call ACME_fnc_medicationTakeSources),"source fallback silently changed donor"] call _check;
        [_stockWrites==0 && {_inventoryDebits==0},"source fallback consumed another kit"] call _check;
    ''')


@pytest.mark.parametrize('reason,accepted',[('manual',True),('manual',False),('access',False),('leash',False),('provider',False)])
def test_partial_push_settles_once_and_preserves_exact_resume_contents(reason,accepted):
    names=('hardcorePushTick','hardcorePushStop','hardcorePushSendBatch',
           'hardcorePushAck','hardcorePushFinalize','hardcorePushRestoreDelta')
    functions=''
    for name in names:
        text=source(name).replace('_patient distance _medic','_distance')
        # Adapt the nested engine map lookup before the general outer-lookup adapter.
        text=text.replace('_job getOrDefault ["med","Medication"]','([_job,["med","Medication"]] call _mapDefault)')
        text=text.replace('getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _source >> "concentration")','([_source,"concentration"] call _configNumber)')
        text=text.replace('isClass (configFile >> "ACM_Medication" >> "Medications" >> _class)','true')
        text=text.replace('isClass (configFile >> "ACM_Medication" >> "Medications" >> _source)','true')
        functions+='ACME_fnc_'+name+'={'+prep_code(text)+'};'
    execute(setup()+functions+'''
        private _requests=[];
        ACME_fnc_medicationRequest={_requests pushBack _this; true};
        ACME_fnc_narcStoreCommit={params ["_p","_rows"]; _p setVariable ["ACME_narcStore",_rows];};
        ACME_fnc_hardcorePushOverlay={};
        ACME_fnc_medicationRouteAllowed={true};
        ACME_fnc_medicationLineIdentity={[0,1,1]};
        ACME_fnc_medicationLineBloodBusy={false};
        missionNamespace setVariable ["ACME_hcEff_medications",true];
        private _row=["Ketamine",3,2,"mix",0,[["Ketamine",2]],"compoundB13","none","","","","partial"];
        _medic setVariable ["ACME_narcStore",[_row]];
        private _job=createHashMapFromArray [
            ["medic",_medic],["patient",_patient],["flowing",true],
            ["identity",[0,1,1]],["stableId","partial"],["session","session"],
            ["virtual",true],["kind","compoundB13"],["med","Ketamine"],
            ["targetMl",2],["rateMlSec",2],["pushedMl",0],["carryMl",0],["lastTick",10]
        ];
        missionNamespace setVariable ["ACME_HCMedPushJob",_job];
        _nowTime=10.25;
        call ACME_fnc_hardcorePushTick;
        private _half=(_medic getVariable ["ACME_narcStore",[]]) select 0;
        [abs ((_half select 2)-1.5)<0.000001 && {count _requests==0},"partial tick did not reserve the precise unsent tail"] call _check;
    '''+f'["{reason}"] call ACME_fnc_hardcorePushStop;'+('''
        [count _requests==1,"manual partial stop failed to submit its tail"] call _check;
        private _request=_requests select 0;
        [abs ((((_request select 3) select 0) select 1)-25)<0.000001,"partial dose differs from plunger volume"] call _check;
        private _meta=_request select 7;
    '''+f'[_medic,_meta,{str(accepted).lower()},"test"] call ACME_fnc_hardcorePushAck;'+f'[_medic,_meta,{str(accepted).lower()},"test"] call ACME_fnc_hardcorePushAck;' if reason=='manual' else '''
        [count _requests==0,"disconnected tail was submitted"] call _check;
    ''')+f'''
        private _remaining=(_medic getVariable ["ACME_narcStore",[]]) select 0;
        [abs ((_remaining select 2)-{1.5 if reason=='manual' and accepted else 2})<0.000001,"partial stop lost or duplicated resume volume"] call _check;
        [abs ((((_remaining select 5) select 0) select 1)-(_remaining select 2))<0.000001,"resume composition differs from plunger"] call _check;
        [count (missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap])==0,"partial transaction remained active after settlement"] call _check;
    ''')


@pytest.mark.parametrize('mode,allowed',[(0,True),(1,True),(2,False)])
def test_real_source_lease_and_supply_helpers_share_patient_policy_and_settle_donor(mode,allowed):
    functions=''
    for name in ('treatmentSupplyOrder','treatmentSupplyCount','treatmentSupplyTake','treatmentSupplyRefund','vialHolder'):
        text=source(name).replace('objectParent _x','objNull').replace('itemCargo _vehicle','[]')
        functions+='ACME_fnc_'+name+'={'+prep_code(text)+'};'
    execute(transaction_setup()+functions+'''
        private _sourcePatient=_patient;
        ace_common_fnc_getCountOfItem={params ["_p","_item"]; {_x==_item} count (_p getVariable ["testInventory",[]])};
        ace_common_fnc_addToInventory={params ["_p","_item"]; private _items=+(_p getVariable ["testInventory",[]]); _items pushBack _item; _p setVariable ["testInventory",_items];};
        ace_medical_treatment_fnc_useItem={
            params ["_m","_p","_items"]; private _used=[objNull,""];
            {
                private _unit=_x;
                private _stock=+(_unit getVariable ["testInventory",[]]);
                {
                    private _index=_stock find _x;
                    if (_index >= 0) exitWith {_stock deleteAt _index; _unit setVariable ["testInventory",_stock]; _used=[_unit,_x];};
                } forEach _items;
                if ((_used select 1)!="") exitWith {};
            } forEach ([_m,_p] call ACME_fnc_treatmentSupplyOrder);
            _used
        };
        ACM_circulation_fnc_setLocalUiState={};
        _medic setVariable ["testInventory",[]];
        _patient setVariable ["testInventory",["ACM_Syringe_10"]];
        _inventoryCounts set ["ACM_Vial_Ketamine",0];
        _patient setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",5]]];
        uiNamespace setVariable ["ACME_SK_Patient",_patient];
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_Target",_patient];
        missionNamespace setVariable ["ACM_circulation_SyringeDraw_InventorySelection",1];
        missionNamespace setVariable ["ACME_vialLeaseAccepted",[_patient,"lease",20]];
    '''+f'missionNamespace setVariable ["ace_medical_treatment_allowSharedEquipment",{mode}];'+'''
        private _receipt=[_medic,"Ketamine",2,10] call ACME_fnc_infusionTakeSupplies;
    '''+( '''
        [count _receipt==4,"valid source/ACE policy preparation rejected"] call _check;
        [((_receipt select 1) select 0 select 0) isEqualTo _sourcePatient,"container donor was not patient"] call _check;
        [(_sourcePatient getVariable ["testInventory",[]]) isEqualTo [],"patient container not consumed"] call _check;
        [([_sourcePatient,"Ketamine"] call ACME_fnc_infusionVialVolume)==3,"patient solution debit wrong"] call _check;
        missionNamespace setVariable ["ACME_vialLeaseAccepted",[]];
        ACE_player=missionNamespace;
        [_receipt] call ACME_fnc_infusionRefundSupplies;
        [_receipt] call ACME_fnc_infusionRefundSupplies;
    ''' if allowed else '''
        [_receipt isEqualTo [],"medic-only mode used patient equipment"] call _check;
    ''')+'''
        [(_sourcePatient getVariable ["testInventory",[]]) isEqualTo ["ACM_Syringe_10"],"source policy/refund duplicated or lost container"] call _check;
        [([_sourcePatient,"Ketamine"] call ACME_fnc_infusionVialVolume)==5,"source policy/refund changed patient volume"] call _check;
        [(_medic getVariable ["testInventory",[]]) isEqualTo [],"patient equipment moved to provider"] call _check;
    ''')


@pytest.mark.parametrize('settle',['release','expiry'])
def test_source_owner_queues_refund_until_second_provider_finishes_without_overwriting_draw(settle):
    execute(setup()+'''
        _inventoryCounts set ["ACM_Vial_Ketamine",0];
        _patient setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",10]]];
        _patient setVariable ["ACME_vialLease",[_medic,"provider-b",14]];
        missionNamespace setVariable ["ACME_vialLeaseAccepted",[_patient,"provider-b",14]];
        [_patient,"provider-a-refund",[["Ketamine",2]]] call ACME_fnc_vialRefundLocal;
        [_patient,"provider-a-refund",[["Ketamine",2]]] call ACME_fnc_vialRefundLocal;
        [_stockWrites==0 && {count _waits==1},"refund wrote through live second-provider lease or duplicated wake"] call _check;
        [[_patient,"Ketamine",3,_medic] call ACME_fnc_vialTake,"second provider draw rejected"] call _check;
        [([_patient,"Ketamine"] call ACME_fnc_infusionVialVolume)==7,"second-provider draw changed"] call _check;
    '''+('[_patient,_medic,"release","provider-b"] call ACME_fnc_vialLeaseCommit;' if settle=='release' else '''
        _serverTime=15;
        // A third provider arrives before the old wake-up. Its lease grant must
        // first settle the queued delta against the latest second-provider map.
        [_patient,missionNamespace,"claim","provider-c"] call ACME_fnc_vialLeaseCommit;
    ''')+'''
        [([_patient,"Ketamine"] call ACME_fnc_infusionVialVolume)==9,"refund overwrote another provider's debit"] call _check;
        [(_patient getVariable ["ACME_vialRefundQueue",[1]]) isEqualTo [],"settled source refund remained queued"] call _check;
        [_patient,"provider-a-refund",[["Ketamine",2]]] call ACME_fnc_vialRefundLocal;
        [_patient] call ACME_fnc_vialRefundLocal;
        [_stockWrites==2 && {([_patient,"Ketamine"] call ACME_fnc_infusionVialVolume)==9},"replayed owner refund duplicated solution"] call _check;
    ''')


def test_queued_source_refund_follows_locality_and_stale_owner_wake_is_inert():
    execute(setup()+'''
        _inventoryCounts set ["ACM_Vial_Ketamine",0];
        _patient setVariable ["ACME_infusion_openVials",createHashMapFromArray [["Ketamine",3]]];
        _patient setVariable ["ACME_vialLease",[_medic,"drawing",14]];
        [_patient,"migrating-refund",[["Ketamine",2]]] call ACME_fnc_vialRefundLocal;
        [count _waits==1 && {_stockWrites==0},"live lease failed to queue refund"] call _check;
        _holderLocal=false;
        private _oldWake=_waits select 0;
        (_oldWake select 1) call (_oldWake select 0);
        [count _events==1 && {((_events select 0) select 1)=="vialRefund"},"old-owner wake did not route to current owner"] call _check;
        [_stockWrites==0,"old owner modified migrated source"] call _check;
        _holderLocal=true; _serverTime=15;
        private _forward=_events select 0;
        [_forward select 0] call ACME_fnc_vialRefundLocal;
        [_patient,"migrating-refund",[["Ketamine",2]]] call ACME_fnc_vialRefundLocal;
        [_stockWrites==1 && {([_patient,"Ketamine"] call ACME_fnc_infusionVialVolume)==5},"migrated/replayed refund was lost or duplicated"] call _check;
    ''')
