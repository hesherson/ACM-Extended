"""Execute real IV/laryngoscopy/suction commit paths and supply policy in SQF-VM.

Only engine inventory, UI/rendering and the external ACE useItem debit are fixtures.
Original donor, no-stock and repeated-callback invariants run through checked-out SQF.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, F, adapt, execute
from test_historical_cardiac_execution import code as engine_code
from test_historical_laryngoscopy_execution import setup as laryngo_setup, code as laryngo_code
from test_historical_procedure_trays import source, ui_code


def primitives(text):
    ts=lex(text);pairs=matching(ts);reverse={v:k for k,v in pairs.items()};edits=[]
    for i,t in enumerate(ts[:-1]):
        if t.kind!='ident' or t.value!='getOrDefault':continue
        left=i-1
        if ts[left].value in (')',']'):left=reverse[left]
        right=pairs[i+1]
        edits.append((ts[left].offset,ts[right].offset+1,'(['+text[ts[left].offset:t.offset].strip()+','+text[ts[i+1].offset:ts[right].offset+1] + '] call _mapDefault)'))
    for a,b,value in reversed(edits):text=text[:a]+value+text[b:]
    return text


def supply_setup():
    functions=''
    for name in ('treatmentSupplyOrder','treatmentSupplyCount','treatmentSupplyTake','treatmentSupplyRefund'):
        text=source(name).replace('objectParent _x','(_x getVariable ["fixtureParent",objNull])')
        text=text.replace('itemCargo _vehicle','(_vehicle call _cargoFor)')
        text=text.replace('_vehicle addItemCargoGlobal [_item, 1]','[_vehicle,_item] call _addCargo')
        functions+='ACME_fnc_'+name+'={'+primitives(adapt(text))+'};'
    return '''
        private _debits=[]; private _refunds=[];
        private _cargoFor={if (_this isEqualTo objNull) exitWith {[]};_this getVariable ["fixtureCargo",[]]};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];private _value=_map get _key;if (isNil "_value") exitWith {_default};_value};
        private _addCargo={params ["_v","_item"];private _row=+(_v getVariable ["fixtureCargo",[]]);_row pushBack _item;_v setVariable ["fixtureCargo",_row];_refunds pushBack [_v,_item];};
        ace_medical_treatment_allowSharedEquipment=0;
        ace_medical_treatment_fnc_isMedic={true};
        ace_common_fnc_getCountOfItem={params ["_u","_item"];{_x==_item} count (_u getVariable ["fixtureStock",[]])};
        ace_common_fnc_addToInventory={params ["_u","_item"];private _row=+(_u getVariable ["fixtureStock",[]]);_row pushBack _item;_u setVariable ["fixtureStock",_row];_refunds pushBack [_u,_item];};
        ace_medical_treatment_fnc_useItem={
            params ["_m","_p","_items"];
            private _result=[objNull,"",false];
            {
                private _u=_x;private _v=_u getVariable ["fixtureParent",objNull];
                {
                    private _item=_x;
                    private _cargo=+(_v call _cargoFor);private _index=_cargo find _item;
                    if (_index>=0) exitWith {_cargo deleteAt _index;_v setVariable ["fixtureCargo",_cargo];_result=[_u,_item,false];};
                    private _row=+(_u getVariable ["fixtureStock",[]]);_index=_row find _item;
                    if (_index>=0) exitWith {_row deleteAt _index;_u setVariable ["fixtureStock",_row];_result=[_u,_item,true];};
                } forEach _items;
                if ((_result select 1)!="") exitWith {};
            } forEach ([_m,_p] call ACME_fnc_treatmentSupplyOrder);
            if ((_result select 1)!="") then {_debits pushBack _result;};
            _result
        };
    '''+functions


@pytest.mark.parametrize('sharing',[0,2])
def test_tube_passage_uses_patient_stock_only_when_allowed(sharing):
    execute(laryngo_setup()+supply_setup()+f'ace_medical_treatment_allowSharedEquipment={sharing};'+'''
        _patient setVariable ["fixtureStock",["ACME_ETTube"]];
        _effects=[0,1,0,0,1,1];_draw=0.99;
        call ACME_fnc_laryngoPassTube;call ACME_fnc_laryngoPassTube;
    '''+f'[count _debits=={int(sharing==0)},"tube debit ignores sharing policy or repeats"] call _check;'+
        f'[(uiNamespace getVariable ["ACME_laryngo_tubePassed",false]) isEqualTo {str(sharing==0).lower()},"tube passage ignores supply result"] call _check;'+'''
        [count _refunds==0,"successful/missing tube path invented refund"] call _check;
        if (ace_medical_treatment_allowSharedEquipment==2) then {
            [count _placements==0 && {count _dispatches==0} && {count _sounds==0},"missing supply still changed airway"] call _check;
        } else {[((_debits select 0) select 0) isEqualTo _patient,"provider debited instead of patient"] call _check;};
    ''')


def test_tube_passage_rechecks_failed_debit_before_any_consequence():
    execute(laryngo_setup()+supply_setup()+'''
        _patient setVariable ["fixtureStock",["ACME_ETTube"]];
        ace_medical_treatment_fnc_useItem={[objNull,"",false]};
        call ACME_fnc_laryngoPassTube;
        [!(uiNamespace getVariable ["ACME_laryngo_tubePassed",false]) && {count _placements==0} && {count _dispatches==0} && {count _sounds==0},"failed final debit still placed/gagged tube"] call _check;
    ''')


def test_existing_tube_requires_no_new_disposable():
    execute(laryngo_setup()+supply_setup()+'''
        _patient setVariable ["ACME_ETT_Inserted",true];
        _effects=[0,1,0,0,1,1];_draw=0.99;
        call ACME_fnc_laryngoPassTube;
        [uiNamespace getVariable ["ACME_laryngo_tubePassed",false],"existing tube cannot resume with empty stock"] call _check;
        [count _debits==0 && {count _placements>0},"existing tube consumed new equipment"] call _check;
    ''')


def iv_setup():
    return laryngo_setup()+supply_setup()+'''
        ACME_fnc_ivUiValid={true};ACME_fnc_ivSiteIndex={0};ACME_fnc_ivLogSite={"upper arm"};
        ACME_fnc_ivExtravasationCheck={false};ACME_fnc_ivEnforceSite={};
        private _nativePlacements=[];
        CBA_fnc_localEvent={_nativePlacements pushBack _this;};
        CBA_fnc_targetEvent={if ((_this select 0)=="ACME_supplySettle") then {(_this select 1) call ACME_fnc_treatmentSupplyRefund;};};
        CBA_fnc_ownerEvent=CBA_fnc_targetEvent;
        ACME_fnc_ownerDispatch={_dispatches pushBack _this;};
        uiNamespace setVariable ["ACME_IV_Medic",_medic];
        uiNamespace setVariable ["ACME_IV_Patient",_patient];
        uiNamespace setVariable ["ACME_IV_InsGauge",16];
        uiNamespace setVariable ["ACME_IV_BodyPart","leftarm"];
        uiNamespace setVariable ["ACME_IV_InsSite","upper"];
    '''+'ACME_fnc_ivPlacementLocal={'+engine_code(source('ivPlacementLocal'))+'};'+\
        'private _register={'+adapt(source('ivMinigameRegister'))+'};'


@pytest.mark.parametrize('stock',[False,True])
def test_iv_registration_cannot_commit_without_final_stock(stock):
    execute(iv_setup()+f'_patient setVariable ["fixtureStock",{["ACM_IV_16g"] if stock else []}];'.replace("'",'"')+'''
        call _register;
    '''+f'[(uiNamespace getVariable ["ACME_IV_RegOK",false]) isEqualTo {str(stock).lower()},"IV reports success without supply"] call _check;'+\
        f'[count _debits=={int(stock)} && {{count _dispatches=={2 if stock else 0}}},"IV did not reserve exactly one catheter before owner request"] call _check;')


@pytest.mark.parametrize('cargo',[False,True])
@pytest.mark.parametrize('rejected',[False,True])
def test_iv_owner_acceptance_settles_exact_patient_or_vehicle_receipt_once(cargo,rejected):
    seed='_patient setVariable ["fixtureParent",missionNamespace]; missionNamespace setVariable ["fixtureCargo",["ACM_IV_16g"]];' if cargo else '_patient setVariable ["fixtureStock",["ACM_IV_16g"]];'
    execute(iv_setup()+seed+'''
        call _register;
        private _request=(_dispatches select 0) select 2;
        _patient setVariable ["fixtureParent",objNull];
    '''+('_patient setVariable ["ACME_clinicalEpoch",2];' if rejected else '')+'''
        _request call ACME_fnc_ivPlacementLocal;
        _request call ACME_fnc_ivPlacementLocal;
    '''+f'[count _refunds=={int(rejected)},"IV rejection refund duplicated or valid insertion refunded"] call _check;'+\
        (f'[((_refunds select 0) select 0) isEqualTo {"missionNamespace" if cargo else "_patient"},"IV refund changed original donor"] call _check;' if rejected else '')+'''
        [([_medic,"ACM_IV_16g"] call ace_common_fnc_getCountOfItem)==0,"IV transferred casualty supply to provider"] call _check;
        [count (missionNamespace getVariable ["ACME_supplyReceipts",createHashMap])==0,"IV receipt was never settled"] call _check;
    ''')


def io_setup():
    text=(ROOT/'addons/circulation/functions/fnc_setIV.sqf').read_text()
    text=re.sub(r'LELSTRING\([^)]*\)','"native hint"',text)
    text=text.replace('GET_BODYPART_INDEX(_bodyPart)','0').replace('GET_BODYPART_DAMAGE(_patient)','[0,0,0,0,0,0]')
    text=text.replace('HAS_TOURNIQUET_APPLIED_ON(_patient,_partIndex)','false')
    text=text.replace('["ACME_ioSupplySource", nil]', '["ACME_ioSupplySource", []]')
    text=text.replace('_refundVehicle addItemCargoGlobal [_refundItem, 1]','[_refundVehicle,_refundItem] call _addCargo')
    config=(ROOT/'addons/acm_extended/config.cpp').read_text().split('class InsertIO_FAST1: InsertIV_16_Upper {',1)[1].split('class InsertIO_EZ:',1)[0]
    callbacks={key:re.search(key+r'\s*=\s*"([^"]+)";',config)[1] for key in ['callbackStart','callbackSuccess','callbackFailure']}
    start=callbacks['callbackStart'].replace('isNull objectParent _itemUser','((_itemUser getVariable ["fixtureParent",objNull]) isEqualTo objNull)').replace('objectParent _itemUser','(_itemUser getVariable ["fixtureParent",objNull])')
    callbacks['callbackFailure']=callbacks['callbackFailure'].replace("['ACME_ioSupplySource', nil]","['ACME_ioSupplySource', []]")
    return laryngo_setup()+supply_setup()+'''
        private _bodyPart="body";private _itemUser=_patient;private _usedItem="ACM_IO_FAST";private _createLitter=true;private _isInZeus=false;
        private _occupied=true;private _nativePlacements=[];
        ACM_IV_14G_M=2;ACM_IO_FAST1_M=4;ACM_IO_EZ_M=3;
        ACM_circulation_fnc_hasIO={_occupied};ACM_circulation_fnc_hasIV={false};
        ACM_core_fnc_getBodyPartString={"body"};
        ace_medical_status_fnc_getMedicationCount={0};
        ace_medical_fnc_adjustPainLevel={};ace_medical_feedback_fnc_playInjuredSound={};
        CBA_fnc_targetEvent={_nativePlacements pushBack _this;};
    '''+'ACM_circulation_fnc_setIV={'+engine_code(text)+'};'+\
        'private _ioStart={'+adapt(start)+'};'+\
        'private _ioSuccess={'+adapt(callbacks['callbackSuccess'])+'};'+\
        'private _ioFailure={'+adapt(callbacks['callbackFailure'])+'};'


@pytest.mark.parametrize('cargo',[False,True])
@pytest.mark.parametrize('occupied',[False,True])
def test_native_io_uses_ace_debit_and_refunds_original_source_once(cargo,occupied):
    seed='_patient setVariable ["fixtureParent",missionNamespace];missionNamespace setVariable ["fixtureCargo",["ACM_IO_FAST"]];' if cargo else '_patient setVariable ["fixtureStock",["ACM_IO_FAST"]];'
    execute(io_setup()+seed+f'_occupied={str(occupied).lower()};'+'''
        private _native=[_medic,_patient,["ACM_IO_FAST"]] call ace_medical_treatment_fnc_useItem;
        _native params ["_itemUser","_usedItem","_createLitter"];
        call _ioStart;
        _patient setVariable ["fixtureParent",objNull];
        call _ioSuccess;call _ioSuccess;
        [count _debits==1,"IO callback spent additional supply"] call _check;
    '''+f'[count _refunds=={int(occupied)},"IO rejection refund missing or duplicated"] call _check;'+\
        f'[count _nativePlacements=={int(not occupied)},"IO acceptance repeated or rejection placed access"] call _check;'+\
        (f'[((_refunds select 0) select 0) isEqualTo {"missionNamespace" if cargo else "_patient"},"IO refunded replacement/current actor instead of original donor"] call _check;' if occupied else '')+'''
        [([_medic,"ACM_IO_FAST"] call ace_common_fnc_getCountOfItem)==0,"IO transferred patient supply to provider"] call _check;
    ''')


def test_native_io_cancel_keeps_ace_refund_and_rejects_late_success():
    execute(io_setup()+'''
        _patient setVariable ["fixtureStock",["ACM_IO_FAST"]];
        private _native=[_medic,_patient,["ACM_IO_FAST"]] call ace_medical_treatment_fnc_useItem;
        _native params ["_itemUser","_usedItem","_createLitter"];
        call _ioStart;
        // ACE treatmentFailure refunds before its callbackFailure hook.
        [_itemUser,_usedItem] call ace_common_fnc_addToInventory;
        call _ioFailure;call _ioSuccess;
        [count _refunds==1 && {count _nativePlacements==0},"late IO callback duplicated ACE cancellation refund"] call _check;
    ''')


def test_native_io_no_consumed_item_cannot_create_access_or_refund():
    execute(io_setup()+'''
        _itemUser=objNull;_usedItem="";_createLitter=false;_occupied=false;
        call _ioStart;call _ioSuccess;
        [count _nativePlacements==0 && {count _refunds==0},"missing ACE item created an IO or free kit"] call _check;
    ''')


def suction_setup():
    bulb=source('suctionBulb')
    bulb=re.sub(r'\[_pat, \(_dev getOrDefault \["sfxSqueeze"[^;]+ remoteExec \["ACME_fnc_remoteSay3D", 0\];','_sounds pushBack "squeeze";',bulb)
    state=source('suctionStateLocal').replace('(_proof param [0, objNull]) == _patient','(_proof param [0, objNull]) isEqualTo _patient')
    return laryngo_setup()+supply_setup()+'''
        private _drained=[];private _published=[];
        ACME_fnc_suctionSfxStop={};ACME_fnc_traySlotState={};ACME_fnc_ownerRegister={};
        ACME_fnc_zeroPad={str (_this select 0)};
        ACME_fnc_laryngoFluidDrain={_drained pushBack _this;};
        ACME_fnc_suctionPublish={_published pushBack _this;};
        ACME_fnc_clinicalTickDelta={1};ACME_fnc_setVarNet={params ["_p","_key","_v"];_p setVariable [_key,_v];};
        uiNamespace setVariable ["ACME_laryngo_held","suction"];
        uiNamespace setVariable ["ACME_laryngo_sucInMouth",true];
        uiNamespace setVariable ["ACME_laryngo_fluidKind","v"];
        uiNamespace setVariable ["ACME_suctionToken","bag-session"];
    '''+'ACME_fnc_suctionDevice={'+primitives(adapt(source('suctionDevice')))+'};'+\
        'ACME_fnc_suctionSelectDevice={'+primitives(ui_code(source('suctionSelectDevice')))+'};'+\
        'ACME_fnc_suctionBulb={'+primitives(ui_code(bulb))+'};'+\
        'ACME_fnc_suctionStateLocal={'+primitives(engine_code(state))+'};'+\
        'ACME_fnc_suctionPhysiologyTick={'+primitives(engine_code(source('suctionPhysiologyTick')))+'};'


@pytest.mark.parametrize('sharing',[0,2])
def test_manual_suction_spends_one_patient_bag_only_at_first_squeeze(sharing):
    execute(suction_setup()+f'ace_medical_treatment_allowSharedEquipment={sharing};'+'''
        _patient setVariable ["fixtureStock",["ACM_SuctionBag"]];
        private _device=[true] call ACME_fnc_suctionSelectDevice;
        [count _debits==0,"selecting manual suction spent disposable"] call _check;
        ["squeeze"] call ACME_fnc_suctionBulb;
        uiNamespace setVariable ["ACME_suction_sqT0",-1];
        ["squeeze"] call ACME_fnc_suctionBulb;
    '''+f'[count _debits=={int(sharing==0)} && {{count _drained=={2 if sharing==0 else 0}}},"manual suction ignored stock/sharing or consumed bag again"] call _check;'+'''
        [count _refunds==0,"used suction bag was refunded"] call _check;
    ''')


def test_accuvac_patient_stock_has_priority_and_stays_reusable():
    execute(suction_setup()+'''
        _medic setVariable ["fixtureStock",["ACM_SuctionBag"]];
        _patient setVariable ["fixtureStock",["ACM_ACCUVAC"]];
        [([true] call ACME_fnc_suctionSelectDevice)==1,"shared ACCUVAC did not take priority"] call _check;
        [_patient,_medic,1,"pump-session",1,"hand",[0.1,0.2],1] call ACME_fnc_suctionStateLocal;
        [_patient] call ACME_fnc_suctionPhysiologyTick;
        [count (_patient getVariable ["ACME_suctionSessions",[]])==1,"patient-stock ACCUVAC session rejected by owner"] call _check;
        [count _debits==0 && {([_patient,"ACM_ACCUVAC"] call ace_common_fnc_getCountOfItem)==1},"ACCUVAC consumed or moved"] call _check;
        _patient setVariable ["fixtureStock",[]];
        [_patient] call ACME_fnc_suctionPhysiologyTick;
        [count (_patient getVariable ["ACME_suctionSessions",[]])==0,"lost shared device retained suction session"] call _check;
    ''')
