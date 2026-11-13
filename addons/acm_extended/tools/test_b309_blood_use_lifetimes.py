"""Run portable clocks, canonical blood flow, returns and persistence in SQF-VM."""
import pytest
from test_menu_death_lifecycle import ROOT, execute, read, adapt
from test_b275_piggyback import delivery_setup
from test_b288_clinical_persistence import ref_function
from b288_resource_return_fixture import definitions
from test_b289_empty_line_attach import setup as attach_setup
from test_b289_bag_only_returns import fixture as used_fixture
from test_b308_patient_equipment import setup as equipment_setup, converted
from test_b230_prepared_infusion_transaction import setup as native_setup

PRESET='missionNamespace setVariable ["ACME_clinicalTiming",[1,true,true,true]];'


@pytest.mark.parametrize('kind,row',[
    ('native','["Blood",350,1,0,true,0,500,-1,"bag",500,[],"bagOnly","foreign"]'),
    ('used','["used","Blood",350,1,0,500,"Blood",-1]'),
    ('prepared','["set","ACM_BloodBag_ON_500","BloodBag_ON_500","","","","Blood",false,"blood"]'),
])
def test_live_clock_does_not_restart_on_repeat_or_paused_save_restore(kind,row):
    execute(PRESET+f'private _row={row};private _kind="{kind}";'+'''
      private _nativeBefore=+_row;
      CBA_missionTime=100;
      _row=[_row,_kind] call ACME_fnc_bloodUseRow;
      CBA_missionTime=1100;
      _row=[_row,_kind] call ACME_fnc_bloodUseRow;
      private _clock=[_row,_kind,"get"] call ACME_fnc_bloodUseRow;
      [[_clock,"age"] call ACME_fnc_bloodUseClock==1000,"repeated start reset age"] call _check;
      private _saved=[_row,_kind,"snapshot"] call ACME_fnc_bloodUseRow;
      CBA_missionTime=5;
      private _restored=[_saved,_kind,"restore",300] call ACME_fnc_bloodUseRow;
      private _clock=[_restored,_kind,"get"] call ACME_fnc_bloodUseRow;
      [[_clock,"age"] call ACME_fnc_bloodUseClock==1300,"restart/offline time lost"] call _check;
      if (_kind=="native") then {
        [(_restored select [0,count _nativeBefore]) isEqualTo _nativeBefore,"foreign tail/capacity changed"] call _check;
      };
    ''')


@pytest.mark.parametrize('at,expired',[(14399,False),(14400,True),(18000,True)])
def test_expiry_boundary_has_no_synthetic_interval_age(at,expired):
    execute(PRESET+f'''
      CBA_missionTime=0;private _clock=[[]] call ACME_fnc_bloodUseClock;
      CBA_missionTime={at};
      [[_clock,"expired"] call ACME_fnc_bloodUseClock isEqualTo {str(expired).lower()},"wrong use deadline"] call _check;
      [[_clock,"age"] call ACME_fnc_bloodUseClock=={at},"clock guessed callback delta"] call _check;
    ''')


@pytest.mark.parametrize('mode',['paused','open','detached','warmer','no-perfusion'])
def test_expired_canonical_bag_never_drains_credits_blood_or_warms_patient(mode):
    change={'paused':'_openFlow=0;','open':'','detached':'_patient setVariable ["ACME_detachedBags",["primary"]];',
            'warmer':'','no-perfusion':'_perfusing=false;'}[mode]
    execute(delivery_setup(False,'Blood',mode=='warmer')+PRESET+'''
      CBA_missionTime=0;
      private _map=_patient getVariable "ACM_circulation_IV_Bags";
      _primary=[_primary] call ACME_fnc_bloodUseRow;
      _map set ["leftarm",[_primary]];
      CBA_missionTime=14400;
    '''+change+'''
      private _before=+(_map get "leftarm" select 0);
      private _result=call _integrate;
      private _after=(_result select 0) select 0;
      [(_after select [0,12]) isEqualTo (_before select [0,12]),"expired blood drained or lost metadata"] call _check;
      [(_result select 1)==0 && {(_result select 4)==0},"expired blood credited physiology"] call _check;
    ''')


@pytest.mark.parametrize('setting',[1,2])
def test_disabling_policy_preserves_existing_blood_flow(setting):
    execute(delivery_setup(False,'Blood',False)+PRESET+'''
      ACM_circulation_fnc_isBloodTypeCompatible={true};
      CBA_missionTime=0;_primary=[_primary] call ACME_fnc_bloodUseRow;
      (_patient getVariable "ACM_circulation_IV_Bags") set ["leftarm",[_primary]];
      CBA_missionTime=15000;
    '''+f'(missionNamespace getVariable "ACME_clinicalTiming") set [{setting},false];'+'''
      private _result=call _integrate;
      [((_result select 0) select 0) select 1<420,"policy off still stopped usable blood"] call _check;
    ''')


def test_medical_roundtrip_preserves_expired_attached_blood_without_refilling():
    execute(PRESET+'private _finiteRef={_this isEqualType 0};'+ref_function('clinicalFreshBlood')+'''
      CBA_missionTime=100;
      private _row=[["Blood",123.5,1,0,true,0,500,-1,"uid",500,[],"bagOnly"]] call ACME_fnc_bloodUseRow;
      private _bags=createHashMapFromArray [["leftarm",[_row]]];
      CBA_missionTime=14000;
      private _saved=[_bags,"snapshot"] call ACME_fnc_clinicalFreshBlood;
      CBA_missionTime=2;
      private _restored=[_saved,"restore",600] call ACME_fnc_clinicalFreshBlood;
      private _bag=(_restored get "leftarm") select 0;
      [[_bag,"native","expired"] call ACME_fnc_bloodUseRow,"medical restore renewed expired blood"] call _check;
      [(_bag select 1)==123.5 && {(_bag select 9)==500} && {(_bag select 11)=="bagOnly"},"medical restore altered blood/tubing"] call _check;
    ''')


@pytest.mark.parametrize('mode',['remove','pull','discard'])
def test_return_keeps_exact_volume_and_clock_in_used_inventory(mode):
    execute(PRESET+definitions()+'''
      CBA_missionTime=0;
      private _bag=[["Blood",123.5,1,0,true,0,500,-1,"uid",500,[],"bagOnly"]] call ACME_fnc_bloodUseRow;
      CBA_missionTime=14400;
    '''+f'private _result=["{mode}",_patient,"clock-return",[_bag]] call ACME_fnc_resourceReturnProducts;'+'''
      [_result select 0,"clocked return invalid"] call _check;
      private _product=(_result select 1) select 0;
      [(_product select 0)=="used","return stripped clock to a fresh native item"] call _check;
      private _row=_product select 1;
      [(_row select 2)==123.5 && {(_row select 5)==500} && {(_row select 9)=="bagOnly"},"return rounded blood or lost apparatus marker"] call _check;
      [[_row,"used","expired"] call ACME_fnc_bloodUseRow,"return renewed spoiled blood"] call _check;
    ''')


@pytest.mark.parametrize('kind,row',[
    ('native','["Blood",123.5,1,0,true,0,500,-1,"uid"]'),
    ('used','["used","Blood",123.5,1,0,500,"Blood",-1]'),
    ('prepared','["set","ACM_BloodBag_ON_500","BloodBag_ON_500","","","","Blood",false,"blood"]'),
])
def test_spoilage_is_permanent_after_policy_change_and_restart(kind,row):
    execute(PRESET+f'private _kind="{kind}";private _row={row};'+'''
      CBA_missionTime=0;_row=[_row,_kind] call ACME_fnc_bloodUseRow;
      CBA_missionTime=14400;_row=[_row,_kind] call ACME_fnc_bloodUseRow;
      missionNamespace setVariable ["ACME_clinicalTiming",[1,false,false,true]];
      [[_row,_kind,"expired"] call ACME_fnc_bloodUseRow,"spoiled blood became usable after policy change"] call _check;
      private _saved=[_row,_kind,"snapshot"] call ACME_fnc_bloodUseRow;
      CBA_missionTime=1;_row=[_saved,_kind,"restore"] call ACME_fnc_bloodUseRow;
      [[_row,_kind,"expired"] call ACME_fnc_bloodUseRow,"restart revived spoiled blood"] call _check;
    ''')


def test_prepared_owner_inherits_clock_and_rejects_expiry_after_network_delay():
    execute(attach_setup()+PRESET+'''
      _fixtureType="Blood";CBA_missionTime=0;
      ACM_circulation_Fluids_Array pushBack "ACM_BloodBag_ON_500";ACM_circulation_Fluids_Array_Data pushBack "BloodBag_ON_500";
      _medic setVariable ["fixtureStock",["ACM_BloodBag_ON_500"]];
      ["ACM_BloodBag_ON_500","BloodBag_ON_500","ivhub-one"] call ACME_fnc_attachBagToLine;
      call _flush;
      CBA_missionTime=1200;call _complete;
      private _bag=(call _bags) select 0;
      private _clock=[_bag,"native","get"] call ACME_fnc_bloodUseRow;
      [[_clock,"age"] call ACME_fnc_bloodUseClock==1200,"hang reset prepared exposure"] call _check;
    ''')
    execute(attach_setup()+PRESET+'''
      _fixtureType="Blood";CBA_missionTime=0;
      ACM_circulation_Fluids_Array pushBack "ACM_BloodBag_ON_500";ACM_circulation_Fluids_Array_Data pushBack "BloodBag_ON_500";
      _medic setVariable ["fixtureStock",["ACM_BloodBag_ON_500"]];
      ["ACM_BloodBag_ON_500","BloodBag_ON_500","ivhub-one"] call ACME_fnc_attachBagToLine;
      call _flush;call _runUntil;call _flush;
      CBA_missionTime=14400;call _deliverOwner;call _deliverResult;call _flush;
      [_factoryCalls==0 && {count (_medic getVariable ["ACME_preparedIVSets",[]])==1},"delayed expired hang created blood or lost its source"] call _check;
    ''')


def test_used_owner_preserves_live_clock_and_refuses_expired_record():
    execute(used_fixture()+PRESET+'''
      CBA_missionTime=0;
      private _record=[["used","Blood",183.25,1,0,500,"Blood",-1,[],"bagOnly"],"used"] call ACME_fnc_bloodUseRow;
      CBA_missionTime=1200;
      [[_patient,_medic,"leftarm",true,0,"used",_record,1,"rehang",false,100,"paid-line"] call ACME_fnc_rehangUsedBagCommit,"live blood rehang refused"] call _check;
      private _bag=((_patient getVariable "ACM_circulation_IV_Bags") get "leftarm") select 0;
      private _clock=[_bag,"native","get"] call ACME_fnc_bloodUseRow;
      [[_clock,"age"] call ACME_fnc_bloodUseClock==1200 && {(_bag select 1)==183.25},"rehang renewed clock or refilled blood"] call _check;
    ''')
    execute(used_fixture()+PRESET+'''
      CBA_missionTime=0;
      private _record=[["used","Blood",183.25,1,0,500,"Blood",-1,[],"bagOnly"],"used"] call ACME_fnc_bloodUseRow;
      CBA_missionTime=14400;
      [!([_patient,_medic,"leftarm",true,0,"used",_record,1,"rehang",false,100,"paid-line"] call ACME_fnc_rehangUsedBagCommit),"expired blood reattached"] call _check;
    ''')


def test_equipment_death_after_debit_refunds_instead_of_placing():
    execute(equipment_setup()+'''
      [_medic,_patient,"accu"] call ACME_fnc_equipmentRequest;
      _caller=2;(_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
      _actorAlive=false;_caller=7;(_acks select 0) call ACME_fnc_equipmentAck;
      [_spawnCount==0 && {count _refundMessages==1},"dead provider completed setup instead of refunding"] call _check;
    ''')


def test_deleted_provider_releases_its_reservation_and_pickup_lock():
    execute(equipment_setup()+'ACME_fnc_equipmentTick={'+converted('equipmentTick')+'''};
      _deviceFixture setVariable ["ACME_eq_busy",true];
      private _r=createHashMapFromArray [["actor",objNull],["device",_deviceFixture],["phase","give"]];
      missionNamespace setVariable ["ACME_eqPending",createHashMapFromArray [["deleted",_r]]];
      call ACME_fnc_equipmentTick;
      [count (missionNamespace getVariable "ACME_eqPending")==0,"deleted provider stranded reservation"] call _check;
      [!(_deviceFixture getVariable ["ACME_eq_busy",true]),"deleted provider locked pickup forever"] call _check;
    ''')


def test_legacy_seven_field_blood_gains_clock_without_nil_or_capacity_changes():
    execute(PRESET+'''
      private _old=["Blood",123.5,1,0,true,0,500];
      private _new=[_old] call ACME_fnc_bloodUseRow;
      [(_new select [0,7]) isEqualTo _old && {(_new select 7)==-1} && {(_new select 8)==""} && {(_new select 9)==500},"legacy native fields changed"] call _check;
      [(_new findIf {isNil "_x"})<0,"legacy migration manufactured nil padding"] call _check;
      [[[_new,"native","get"] call ACME_fnc_bloodUseRow,"validLive"] call ACME_fnc_bloodUseClock,"legacy use clock invalid"] call _check;
    ''')


@pytest.mark.parametrize('meta',['["bloodUseAgeV1",-1]','["bloodUseAgeV1","old"]','["bloodUseAgeV1",1,2]','["unknown",0]'])
def test_invalid_saved_clock_cannot_restore_usable_blood(meta):
    execute(PRESET+f'private _bad={meta};'+'''
      [!([_bad,"validSaved"] call ACME_fnc_bloodUseClock),"invalid clock passed schema"] call _check;
      private _restored=[_bad,"restore"] call ACME_fnc_bloodUseClock;
      [[_restored,"expired"] call ACME_fnc_bloodUseClock,"invalid clock restored usable blood"] call _check;
    ''')


def test_empty_y_placeholder_does_not_inherit_a_spoiled_blood_caption():
    execute(PRESET+'''
      CBA_missionTime=0;
      private _row=[["Blood",500,1,0,true,0,500,-1,"uid"]] call ACME_fnc_bloodUseRow;
      _row set [0,"ACME_Empty"];_row set [1,0];CBA_missionTime=20000;
      [!([_row,"native","expired"] call ACME_fnc_bloodUseRow),"empty Y placeholder marked spoiled"] call _check;
    ''')


@pytest.mark.parametrize('source,mode',[('_medic',0),('_patient',1)])
def test_spiking_preserves_exposure_from_the_actual_selected_inventory(source,mode):
    execute(attach_setup()+PRESET+f'''
      _fixtureType="Blood";CBA_missionTime=0;
      ACM_circulation_Fluids_Array pushBack "ACM_BloodBag_ON_500";ACM_circulation_Fluids_Array_Data pushBack "BloodBag_ON_500";
      {source} setVariable ["fixtureStock",["ACM_BloodBag_ON_500"]];
      {source} setVariable ["ACME_bloodExposure",[[["ACM_BloodBag_ON_500",500,10000]],_nowTime]];
      missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory",{mode}];
      [["ACM_BloodBag_ON_500","BloodBag_ON_500","ivhub-one"] call ACME_fnc_attachBagToLine,"source attach did not begin"] call _check;
      call _complete;
      private _bag=(call _bags) select 0;
      private _clock=[_bag,"native","get"] call ACME_fnc_bloodUseRow;
      [[_clock,"age"] call ACME_fnc_bloodUseClock==10000,"spiking washed source warm exposure"] call _check;
      CBA_missionTime=4400;
      [[_bag,"native","expired"] call ACME_fnc_bloodUseRow,"prior warm exposure did not shorten use window"] call _check;
    ''')


@pytest.mark.parametrize('explicit',[True,False])
def test_native_iv_event_and_actual_owner_factory_preserve_use_exposure(explicit):
    s=(ROOT/'addons/core/overrides/fnc_ivBag.sqf').read_text()
    s=s.replace('FBTK_ARRAY_DATA','[]').replace('ALL_BODY_PARTS','ACME_infusion_bodyParts')
    s=s.replace('LELSTRING(circulation,GUI_BeganTransfusing)','"started transfusion"')
    execute(native_setup()+PRESET+'''
      _configuredType="Blood";_configuredVolume=500;
      private _wire=[];
      CBA_fnc_targetEvent={_wire pushBack _this;};
      ace_medical_treatment_fnc_addToTriageCard={};ace_medical_treatment_fnc_addToLog={};
      ace_common_fnc_getName={"Medic"};ACM_core_fnc_getBodyPartString={"arm"};ACM_circulation_fnc_getFluidBagString={"Blood"};
      ACM_circulation_fnc_getAccessType={1};
      _patient setVariable ["ACME_bloodExposure",[[["ACM_BloodBag_ON_500",500,10000]],_nowTime]];
      CBA_missionTime=100;
      private _nativeIv={'''+adapt(s)+'''};
    '''+f'private _clock={"[\"bloodUseV1\",10000,0]" if explicit else "[]"};'+'''
      [_medic,_patient,"leftarm","BloodIV_ON_500",_patient,"ACM_BloodBag_ON_500",true,0,_clock] call _nativeIv;
      private _event=(_wire select 0) select 1;
      [count _event==11,"native IV handoff lost clock field"] call _check;
      _event call _nativeCarrier;
      private _bag=((_patient getVariable "ACM_circulation_IV_Bags") get "leftarm") select 0;
      private _clock=[_bag,"native","get"] call ACME_fnc_bloodUseRow;
    '''+f'[[ _clock,"age"] call ACME_fnc_bloodUseClock=={10100 if explicit else 10000},"native owner delivery renewed use exposure"] call _check;')
