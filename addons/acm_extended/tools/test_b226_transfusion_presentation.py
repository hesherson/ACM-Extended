"""B226: production fluid rows, explicit inventory, one-shot suction and dressing lifetimes.
Only engine UI/inventory/audio/animation primitives are replaced in the execution cases.
No claim of native Arma rendered blends, acoustics or network-latency reproduction.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, read, adapt, execute
from test_b156_procedure_supplies import primitives, suction_setup
from test_b222_suction_input import block
from test_historical_pose_lifecycle import setup as pose_setup, pose_source
from test_historical_medication_rows import iteration_scopes


def compiled(name):
    return 'ACME_fnc_'+name+'={'+primitives(adapt(read(name)))+'};'


@pytest.mark.parametrize('kind,empty,volume',[
    ('Blood','ACME_Empty',500),('FreshBlood','ACME_Empty',250),
    ('Saline','ACME_EmptySaline',100),('ACME_SalineY','ACME_EmptySaline',500)])
@pytest.mark.parametrize('iv',[False,True])
@pytest.mark.parametrize('duplicates',[1,3])
def test_native_new_bag_replaces_only_its_exact_phantom_slot(kind,empty,volume,iv,duplicates):
    execute(compiled('yBagReplaceEmpty')+f'''
      private _iv={str(iv).lower()};
      private _old=["{empty}",0,0,0,_iv,-1,500,-1,"old"];
      private _reserve=["Plasma",100,0,0,_iv,-1,500,-1,"reserve"];
      private _otherSite=["{empty}",0,0,1,_iv,-1,500,-1,"other-site"];
      private _otherAccess=["{empty}",0,0,0,!_iv,-1,500,-1,"other-access"];
      private _new=["{kind}",{volume},0,0,_iv,4,{volume},8,"new-stable-uid"];
      private _bags=[_old,_reserve,_otherSite,_otherAccess];
      for "_i" from 2 to {duplicates} do {{_bags pushBack +_old;}};
      _bags pushBack _new;
      private _copy=+_bags;
      private _result=[_bags,count _bags-1] call ACME_fnc_yBagReplaceEmpty;
      [_result isEqualTo [_new,_reserve,_otherSite,_otherAccess],"replacement lost site/order/UID or duplicated live bag"] call _check;
      [_bags isEqualTo _copy,"input state mutated before commit"] call _check;
    ''')


@pytest.mark.parametrize('kind,amount',[('Blood',0),('FreshBlood',.001),('Saline',.5),('Plasma',500),('PlasmaLyte',1000),('FBTK',250)])
def test_nonreplacement_bags_do_not_consume_the_empty_blood_slot(kind,amount):
    execute(compiled('yBagReplaceEmpty')+f'''
      private _bags=[["ACME_Empty",0,0,0,true,-1,500],["{kind}",{amount},0,0,true,-1,500]];
      [[_bags,1] call ACME_fnc_yBagReplaceEmpty isEqualTo _bags,"unrelated bag took phantom slot"] call _check;
      [[_bags,-1] call ACME_fnc_yBagReplaceEmpty isEqualTo _bags,"invalid index modified state"] call _check;
    ''')


@pytest.mark.parametrize('label,amount,want',[
    ('Blood Bag O- (500ml) [Y] [Cooled]',393,'Blood Bag O- (393ml) [Y] [Cooled]'),
    ('Fresh Blood O+ (500ml) [27] [Warmed]',421,'Fresh Blood O+ (421ml) [27] [Warmed]'),
    ('Plasma IV (1000ml)',750,'Plasma IV (750ml)'),
    ('Saline IV (500ml)',22,'Saline IV (22ml)'),
    ('Plasma-Lyte A (500mL)',417,'Plasma-Lyte A (417mL)'),
    ('Magnesium (50 mL)',24,'Magnesium (24 mL)'),
    ('Hypertonic Saline (250 ml)',181.7,'Hypertonic Saline (182 ml)'),
    ('Mannitol (500ml)',-1,'Mannitol (0ml)'),
    ('FBTK (250ml)',42,'FBTK (42ml)'),
    ('Custom fluid',79,'Custom fluid (79 mL)'),
    ('Other (10.5 ml) [tag]',8,'Other (8 ml) [tag]'),
])
def test_volume_formatter_preserves_type_units_tags_and_donor_id(label,amount,want):
    execute(compiled('fluidLabelVolume')+f'[["{label}",{amount}] call ACME_fnc_fluidLabelVolume == "{want}","fluid label changed wrong token"] call _check;')


def bag_ui_setup():
    s=(ROOT/'addons/circulation/functions/fnc_TransfusionMenu_UpdateBagList.sqf').read_text()
    s=s.replace('lbCurSel _ctrlBagPanel','_selected').replace('lbClear _ctrlBagPanel;','_clears=_clears+1;_labels=[];')
    s=s.replace('lbSize _ctrlBagPanel','count _labels')
    s=re.sub(r'_ctrlBagPanel lbValue (_\w+)',r'(_values select \1)',s)
    s=re.sub(r'_ctrlBagPanel lbText (_\w+)',r'(_labels select \1)',s)
    s=s.replace('_ctrlBagPanel lbSetText','_labels set').replace('_ctrlBagPanel lbSetTooltip','_tips set')
    s=s.replace('C_LLSTRING(FreshBloodBag_Short)','"fresh %1"')
    return '''
      private _display=missionNamespace;private _labels=[];private _values=[];private _tips=[];private _selected=0;private _clears=0;private _rebuilds=0;
      uiNamespace setVariable ["ACM_circulation_TransfusionMenu_DLG",_display];
      ACM_circulation_TransfusionMenu_Target=_patient;
      ACM_circulation_TransfusionMenu_Selected_BodyPart="body";
      ACM_circulation_TransfusionMenu_Selected_AccessSite=0;
      ACM_circulation_TransfusionMenu_SelectIV=false;
      ACM_circulation_fnc_TransfusionMenu_UpdateBagList={_rebuilds=_rebuilds+1;};
      private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    '''+compiled('fluidLabelVolume')+'private _updateBags={'+primitives(adapt(s,'circulation'))+'};'


@pytest.mark.parametrize('type',['Plasma','Saline','PlasmaLyte','Blood','FreshBlood','FBTK','MagnesiumIV','MannitolIV'])
@pytest.mark.parametrize('filtered',[False,True])
def test_actual_live_update_uses_lbvalue_after_an_infusion_row_is_hidden(type,filtered):
    # Selection index 0 may be an infusion moved to its own overlay. Visible row 0 then owns index 1.
    execute(bag_ui_setup()+f'''
      private _first=["Epinephrine",49,0,0,false,-1,50,-1,0];
      private _bag=["{type}",393,0,0,false,3,500,27,"stable-uid"];
      _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[_first,_bag]]]];
      ACM_circulation_TransfusionMenu_Selection_IVBags=[_first,["{type}",500,0,0,false,3,500,27,1]];
      _labels={ '["My fluid (500ml) [Y] [Warmed]"]' if filtered else '["Infusion (49ml)","My fluid (500ml) [Y] [Warmed]"]' };
      _values={ '[1]' if filtered else '[0,1]' };
      [true] call _updateBags;
      [(_labels select {0 if filtered else 1})=="My fluid (393ml) [Y] [Warmed]","volume updated wrong rendered row"] call _check;
      [((ACM_circulation_TransfusionMenu_Selection_IVBags select 1) select 1)==393,"selected tuple stale"] call _check;
      [_clears==0 && {{_rebuilds==0}} && {{_selected==0}},"volume change rebuilt list or stole selection"] call _check;
      [true] call _updateBags;
      [(_labels select {0 if filtered else 1})=="My fluid (393ml) [Y] [Warmed]","steady tick changed label"] call _check;
    ''')


def test_update_requests_structural_rebuild_when_a_live_bag_replaces_placeholder():
    execute(bag_ui_setup()+'''
      _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["body",[["ACME_Empty",0,0,0,false,-1,500,-1,"old"],["Blood",498,0,0,false,0,500,-1,"new"]]]]];
      ACM_circulation_TransfusionMenu_Selection_IVBags=[["ACME_Empty",0,0,0,false,-1,500,-1,0]];
      _labels=["[Empty Blood Bag] [Y]"];_values=[0];
      [true] call _updateBags;
      [_rebuilds==1,"old saved phantom not filtered/replaced"] call _check;
    ''')


def selected_setup():
    s=read('transfusionTakeSelected').replace('objectParent _medic','_vehicleNow').replace('_medic distance _donor','_distance')
    s=s.replace('itemCargo _vehicle','(_vehicle getVariable ["stock",[]])').replace('_vehicle addItemCargoGlobal [_class, -1];','[_vehicle,_class] call _take;')
    refund=read('treatmentSupplyRefund').replace('_vehicle addItemCargoGlobal [_item, 1]','[_vehicle,_item] call _give')
    return '''
      private _vehicleNow=missionNamespace;
      private _take={params ["_u","_class"];private _a=+(_u getVariable ["stock",[]]);private _i=_a find _class;if (_i<0) exitWith {false};_a deleteAt _i;_u setVariable ["stock",_a];true};
      private _give={params ["_u","_class"];private _a=+(_u getVariable ["stock",[]]);_a pushBack _class;_u setVariable ["stock",_a];};
      ACME_fnc_itemTake=_take;ace_common_fnc_addToInventory=_give;
      ACME_fnc_carrierSupplyTake={[objNull,"",false,objNull]};
      private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};
    '''+'ACME_fnc_transfusionTakeSelected={'+primitives(adapt(s))+'};ACME_fnc_treatmentSupplyRefund={'+primitives(adapt(refund))+'};'


@pytest.mark.parametrize('mode',[0,1,2])
@pytest.mark.parametrize('refund',[False,True])
def test_explicit_bag_receipt_takes_only_selected_source_and_settles_once(mode,refund):
    execute(selected_setup()+f'''
      {{_x setVariable ["stock",["blood"]];}} forEach [_medic,_patient,missionNamespace];
      private _chosen=[_medic,_patient,missionNamespace] select {mode};
      private _receipt=[_medic,_patient,"blood",{mode},missionNamespace] call ACME_fnc_transfusionTakeSelected;
      [count _receipt==4,"bag debit failed"] call _check;
      [(_chosen getVariable "stock") isEqualTo [],"selected source not debited"] call _check;
      {{if (_x isNotEqualTo _chosen) then {{[(_x getVariable "stock") isEqualTo ["blood"],"another inventory was used"] call _check;}};}} forEach [_medic,_patient,missionNamespace];
      [[_receipt,{str(refund).lower()}] call ACME_fnc_treatmentSupplyRefund,"settlement failed"] call _check;
      [!([_receipt,true] call ACME_fnc_treatmentSupplyRefund),"receipt duplicated"] call _check;
      [count (_chosen getVariable "stock")=={int(refund)},"wrong refund target/count"] call _check;
    ''')


@pytest.mark.parametrize('mode',[0,1,2])
def test_missing_selected_bag_never_falls_back_to_other_person(mode):
    execute(selected_setup()+f'''
      {{_x setVariable ["stock",["blood"]];}} forEach [_medic,_patient,missionNamespace];
      ([_medic,_patient,missionNamespace] select {mode}) setVariable ["stock",[]];
      [[_medic,_patient,"blood",{mode},missionNamespace] call ACME_fnc_transfusionTakeSelected isEqualTo [],"missing bag substituted from other inventory"] call _check;
    ''')


def bandage_setup():
    return pose_setup()+''.join('ACME_fnc_'+n+'={'+pose_source(n).replace('finite _duration','(_duration call _finite)').replace('finite _window','(_window call _finite)')+'};' for n in ['torsoBandageStart','torsoBandageFinish','isTorsoBandage'])


@pytest.mark.parametrize('classname',['FieldDressing','PackingBandage','ElasticBandage','QuikClot','PressureBandage','EmergencyTraumaDressing'])
def test_chest_dressing_work_is_unarmed_and_success_plays_one_placement(classname):
    execute(bandage_setup()+f'''
      [_medic,_patient,"body","{classname}"] call ACME_fnc_isTorsoBandage;
      private _token=[_medic,_patient,"body","{classname}",12] call ACME_fnc_torsoBandageStart;
      private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
      [(_state select 2)=="ACME_JunctionalWork","chest work is armed/not looped"] call _check;
      private _args=[_medic,_patient,"body","{classname}",_medic,"bandage",false,_token];
      private _before=count _moves;
      [_args,true] call ACME_fnc_torsoBandageFinish;
      private _end=_medic getVariable ["ACME_treatmentPoseState",[]];
      [(_end select 1)=="chestSeal","no chest seal placement at completion"] call _check;
      [(_end select 2)=="AinvPknlMstpSnonWnonDnon_medic3","wrong finishing animation"] call _check;
      [_args,true] call ACME_fnc_torsoBandageFinish;
      [(_medic getVariable "ACME_treatmentPoseState") isEqualTo _end,"duplicate completion replayed tail"] call _check;
      [(_moves select [ _before ]) findIf {{(_x select 1)=="AmovPknlMstpSnonWnonDnon"}} < 0,"neutral gap before placement"] call _check;
    ''')


@pytest.mark.parametrize('reason',['failure','replaced','unconscious','far','vehicle','death'])
def test_stale_or_failed_dressing_does_not_start_a_success_placement(reason):
    setup={'failure':'','replaced':'[_medic,"stethoscope",-1,_patient] call ACME_fnc_treatmentPoseStart;',
           'unconscious':'_medic setVariable ["ACE_isUnconscious",true];','far':'_distance=99;',
           'vehicle':'_parent=missionNamespace;','death':'_alive=false;'}[reason]
    execute(bandage_setup()+'''
      private _token=[_medic,_patient,"body","FieldDressing",12] call ACME_fnc_torsoBandageStart;
    '''+setup+f'''
      private _before=count _moves;
      [[_medic,_patient,"body","FieldDressing",_medic,"bandage",false,_token],{str(reason!='failure').lower()}] call ACME_fnc_torsoBandageFinish;
      private _state=_medic getVariable ["ACME_treatmentPoseState",[]];
      [(_state param [1,""])!="chestSeal","failure launched placement"] call _check;
      { '[(_state param [1,""])=="stethoscope","old dressing stopped successor"] call _check;' if reason=='replaced' else '' }
    ''')


@pytest.mark.parametrize('part,class_,self_',[("leftarm","FieldDressing",False),("body","ApplyTourniquet",False),("body","ApplySplint",False),("body","ACME_AAJT",False),("body","FieldDressing",True)])
def test_other_actions_do_not_acquire_chest_dressing_owner(part,class_,self_):
    execute(compiled('isTorsoBandage')+f'[!([_medic,{"_medic" if self_ else "_patient"},"{part}","{class_}"] call ACME_fnc_isTorsoBandage),"unrelated action treated as chest wound dressing"] call _check;')


def test_sound_is_discrete_manual_sample_and_has_finite_local_emitter_cleanup():
    s=read('manualSuctionSound')
    assert '"#dynamicsound" createVehicleLocal' in s
    assert '["ACME_ManualSuction", 25, 1, 2]' in s
    assert 'deleteVehicle _sound' in s and 'deleteVehicle _emitter' in s
    assert '], 1.2] call CBA_fnc_waitAndExecute' in s
    assert 'addPerFrameHandler' not in s and 'createSoundSource' not in s
    source=read('suctionBulb');squeeze=block(source,'case "squeeze":')
    assert squeeze.index('ACME_suction_sqT0", -1') < squeeze.index('call ACME_fnc_manualSuctionSound')
    assert squeeze.index('if (_vol >= _cap)') < squeeze.index('call ACME_fnc_manualSuctionSound')
    assert 'call ACME_fnc_manualSuctionSound' not in block(source,'case "tick":')


def test_native_timer_owns_chest_start_success_failure_and_full_duration():
    native=(ROOT/'addons/core/functions/fnc_treatmentNative.sqf').read_text()
    assert '[_medic, _patient, _bodyPart, _classname, _treatmentTime] call ACME_fnc_torsoBandageStart' in native
    assert native.index('"ace_treatmentStarted"') < native.index('call ACME_fnc_torsoBandageStart')
    assert 'ACEFUNC(medical_treatment,treatmentSuccess);\n        [_this select 0, true] call ACME_fnc_torsoBandageFinish;' in native
    assert 'ACEFUNC(medical_treatment,treatmentFailure);\n        [_this select 0, false] call ACME_fnc_torsoBandageFinish;' in native
    wrapper=(ROOT/'addons/core/overrides/fnc_treatment.sqf').read_text()
    assert '!_torsoDressing' in wrapper
    assert '"ACME_JunctionalWork"' in read('treatmentPoseStart')


def test_empty_inventory_is_cleared_before_no_bags_return_and_extras_follow_selected_source():
    s=(ROOT/'addons/circulation/functions/fnc_TransfusionMenu_SwitchTargetInventory.sqf').read_text()
    assert s.index('lbClear _ctrlInventoryPanel;') < s.index('if (_index < 0) exitWith')
    assert 'ACME_preparedListMode", false' in s
    ui=read('updateTransfusionControls')
    assert 'private _ownInventory' in ui
    assert 'if (_ownInventory) then {ACE_player getVariable ["ACME_coolerStore"' in ui
    assert 'if (_ownInventory) then {ACE_player getVariable ["ACME_usedBags"' in ui
    assert 'call ACME_fnc_transfusionTakeSelected' in read('transfusionSpikeOrAdd')


def switch_ui_setup():
    s=(ROOT/'addons/circulation/functions/fnc_TransfusionMenu_SwitchTargetInventory.sqf').read_text()
    s=s.replace('objectParent ACE_player','_vehicleNow').replace('getItemCargo _vehicle','_vehicleCargo')
    # Engine object equality, represented by namespace identities in this fixture.
    s=s.replace('ACE_player == GVAR(TransfusionMenu_Target)','ACE_player isEqualTo GVAR(TransfusionMenu_Target)')
    s=s.replace('C_LLSTRING(FreshBloodBag_Short)','"fresh %1"')
    s=s.replace('lbClear _ctrlInventoryPanel;','_rows=[];')
    s=s.replace('_ctrlInventoryPanel lbSetCurSel -1;','_sel=-1;')
    s=s.replace('_ctrlInventoryPanel lbAdd _name','(_rows pushBack _name)')
    s=s.replace('_ctrlInventoryPanel lbSetData','_rowData set')
    s=s.replace('_ctrlInventoryPanel lbSetTooltip','_rowTips set')
    s=re.sub(r'_ctrlInventoryPanel lbSetPicture \[[^;]+;', '', s)
    s=s.replace('getNumber (_config >> "uniqueBag")','0').replace('getNumber (_cfg >> "uniqueBag")','0')
    s=re.sub(r'getText \(_config >> "(?:shortName|displayName)"\)','_entry',s)
    return '''
      private _display=missionNamespace;private _vehicleNow=objNull;
      private _rows=["old bag"];private _rowData=[];private _rowTips=[];private _sel=0;
      private _vehicleCargo=[["PlasmaIV"],[1]];
      ACM_circulation_TransfusionMenu_Selected_Inventory=0;
      ACM_circulation_TransfusionMenu_Target=_patient;
      ACM_circulation_Fluids_Array=["SalineIV","BloodIV","PlasmaIV"];
      ACM_circulation_Fluids_Array_Data=["saline","blood","plasma"];
      ACME_fnc_itemList={(_this select 0) getVariable ["stock",[]]};
      ACME_fnc_itemCount={params ["_u","_c"];{_x==_c} count (_u getVariable ["stock",[]])};
      uiNamespace setVariable ["ACM_circulation_TransfusionMenu_DLG",_display];
      uiNamespace setVariable ["ACME_preparedListMode",true];
    '''+'private _switchInventory={'+adapt(iteration_scopes(s),'circulation')+'};'


@pytest.mark.parametrize('patientbags',[[],['BloodIV'],['PlasmaIV','SalineIV']])
def test_actual_inventory_cycle_rebuilds_contents_even_when_patient_is_empty(patientbags):
    execute(switch_ui_setup()+f'_patient setVariable ["stock",{str(patientbags).replace(chr(39),chr(34))}];'+'''
      _medic setVariable ["stock",["SalineIV"]];
      [] call _switchInventory;
      [ACM_circulation_TransfusionMenu_Selected_Inventory==1,"not patient inventory"] call _check;
      [!(_rows isEqualTo ["old bag"]),"stale prior list retained"] call _check;
      [! (uiNamespace getVariable ["ACME_preparedListMode",true]),"prepared provider overlay hides patient list"] call _check;
    '''+f'[count _rows=={len(patientbags)},"wrong patient bag count"] call _check;'+'''
      [] call _switchInventory;
      [ACM_circulation_TransfusionMenu_Selected_Inventory==0,"no-vehicle cycle did not return self"] call _check;
      [_rows isEqualTo ["SalineIV"],"self inventory not restored"] call _check;
      [false] call _switchInventory;
      [ACM_circulation_TransfusionMenu_Selected_Inventory==0 && {_rows isEqualTo ["SalineIV"]},"refresh advanced target"] call _check;
    ''')


def test_actual_inventory_cycle_exposes_vehicle_without_mixing_provider_bags():
    execute(switch_ui_setup()+'''
      _vehicleNow=missionNamespace;
      _patient setVariable ["stock",["BloodIV"]];_medic setVariable ["stock",["SalineIV"]];
      [] call _switchInventory;[] call _switchInventory;
      [ACM_circulation_TransfusionMenu_Selected_Inventory==2 && {_rows isEqualTo ["PlasmaIV"]},"vehicle mixed with provider/patient"] call _check;
      [] call _switchInventory;
      [_rows isEqualTo ["SalineIV"],"vehicle cycle did not return self"] call _check;
    ''')


@pytest.mark.parametrize('warmed,cold,color,tag',[
    (False,False,[1,1,1,1],''),(False,True,[.45,.72,1,1],' [Cooled]'),
    (True,False,[1,.55,.13,1],' [Warmed]'),(True,True,[1,.55,.13,1],' [Warmed]')])
def test_actual_thermal_paint_clears_empty_red_and_uses_patient_temperature(warmed,cold,color,tag):
    s=read('updateTransfusionControls')
    a=s.index('private _ctrlActive = _display displayCtrl 86004;');b=s.index('// cooler blood surfaced',a)
    s=s[a:b].replace('private _ctrlActive = _display displayCtrl 86004;','private _ctrlActive = missionNamespace;')
    s=s.replace('lbSize _ctrlActive','count _labels').replace('_ctrlActive lbValue _r','_r').replace('_ctrlActive lbText _r','(_labels select _r)')
    s=s.replace('_ctrlActive lbSetColor','_colors set').replace('_ctrlActive lbSetText','_labels set')
    s=re.sub(r'_ctrlActive lbSet(?:Picture|Tooltip) \[[^;]+;','',s)
    execute('private _mapDefault={params ["_m","_args"];_args params ["_k","_d"];if (_k in _m) then {_m get _k} else {_d}};'+compiled('lineWarmer')+'''
      private _labels=["Blood O- (498ml) [Y] [Cooled]"];private _colors=[[1,0,0,1]];
      private _targetPatient=_patient;private _lineYd=true;
      missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags",[["Blood",498]]];
      CBA_fnc_replace={params ["_s","_from","_to"];private _i=_s find _from;if (_i<0) exitWith {_s};(_s select [0,_i])+_to+(_s select [_i+count _from])};
    '''+f'_patient setVariable ["ACME_warmedBlood",{str(warmed).lower()}];_patient setVariable ["ACME_coldBlood",{str(cold).lower()}];'+adapt(s)+f'''
      [(_colors select 0) isEqualTo {color},"refilled blood kept red or wrong thermal color"] call _check;
      [(_labels select 0)=="Blood O- (498ml) [Y]{tag}","thermal tag stale/duplicated"] call _check;
    ''')


def sound_setup():
    s=read('manualSuctionSound')
    s=s.replace('hasInterface','_hasInterface').replace('allPlayers','_players').replace('alive _x','true')
    s=s.replace('_x distance _medic','_distance').replace('ACE_player distance _medic','_distance')
    s=s.replace('isNull ACE_player','(ACE_player isEqualTo objNull)')
    s=s.replace('"#dynamicsound" createVehicleLocal (getPosATL _medic)','(call _makeEmitter)')
    s=s.replace('_emitter attachTo [_medic, [0, 0.25, 0.9]];','_attached=_medic;')
    s=s.replace('_emitter say3D ["ACME_ManualSuction", 25, 1, 2]','(["ACME_ManualSuction",25,1,2] call _say)')
    s=s.replace('deleteVehicle _sound;','_deleted pushBack _sound;').replace('deleteVehicle _emitter;','_deleted pushBack _emitter;').replace('detach _emitter;','_detached=true;')
    return '''
      private _hasInterface=true;private _players=[_medic,_medic];private _made=0;
      private _sounds=[];private _deleted=[];private _detached=false;private _attached=objNull;
      private _makeEmitter={_made=_made+1;missionNamespace};
      private _say={_sounds pushBack _this;profileNamespace};
      CBA_fnc_waitAndExecute={_waits pushBack _this;};
    '''+'ACME_fnc_manualSuctionSound={'+adapt(s)+'};'


def test_manual_squeeze_listener_plays_one_shot_and_deletes_source_and_emitter():
    execute(sound_setup()+'''
      [_medic,true] call ACME_fnc_manualSuctionSound;
      [_made==1 && {_attached isEqualTo _medic} && {count _sounds==1},"squeeze did not emit once at provider"] call _check;
      [(_sounds select 0) isEqualTo ["ACME_ManualSuction",25,1,2],"wrong sound/cabin mode"] call _check;
      private _job=_waits select 0;
      [(_job select 2)==1.2,"unbounded sound lifetime"] call _check;
      (_job select 1) call (_job select 0);
      [count _deleted==2 && {_detached},"sound/emitter leaked"] call _check;
    ''')


@pytest.mark.parametrize('reason',['dedicated','far','null-medic'])
def test_squeeze_audio_receiver_does_not_create_unheard_emitters(reason):
    change={'dedicated':'_hasInterface=false;','far':'_distance=26;','null-medic':''}[reason]
    execute(sound_setup()+change+f'[{"objNull" if reason=="null-medic" else "_medic"},true] call ACME_fnc_manualSuctionSound;'+'''[_made==0 && {count _sounds==0},"irrelevant listener spawned emitter"] call _check;''')


def test_bandage_orphan_watchdog_releases_only_work_and_does_not_touch_success_tail():
    execute(bandage_setup()+'''
      private _token=[_medic,_patient,"body","FieldDressing",9] call ACME_fnc_torsoBandageStart;
      private _job=_waits select ((count _waits)-1);
      [(_job select 2)==14,"orphan timeout not tied to treatment time"] call _check;
      (_job select 1) call (_job select 0);
      [(_medic getVariable ["ACME_treatmentPoseState",[]]) isEqualTo [],"orphan work not stopped"] call _check;
      private _token2=[_medic,_patient,"body","FieldDressing",9] call ACME_fnc_torsoBandageStart;
      private _job2=_waits select ((count _waits)-1);
      [[_medic,_patient,"body","FieldDressing",_medic,"bandage",false,_token2],true] call ACME_fnc_torsoBandageFinish;
      private _tail=_medic getVariable "ACME_treatmentPoseState";
      (_job2 select 1) call (_job2 select 0);
      [(_medic getVariable "ACME_treatmentPoseState") isEqualTo _tail,"old orphan guard interrupted placement"] call _check;
    ''')


@pytest.mark.parametrize('lowered',[False,True])
@pytest.mark.parametrize('type',['rifle','pistol'])
def test_crouched_first_contact_lowers_equipped_small_arm_without_replaying_a_lowered_pose(type,lowered):
    from test_b156_menu_pose import setup
    s=setup().replace('weaponLowered _medic','_lowered')
    field='_primaryWeapon' if type=='rifle' else '_handgunWeapon'
    expected='AmovPknlMstpSlowWrflDnon' if type=='rifle' else 'AmovPknlMstpSlowWpstDnon'
    execute(s+f'''
      private _lowered={str(lowered).lower()};_currentWeapon="equipped";{field}="equipped";
      _medic setVariable ["ACME_menuPoseAfterTreatment",objNull];
      [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
      [count _moves=={0 if lowered else 1},"crouch aiming ignored or lower pose replayed unnecessarily"] call _check;
    '''+(f'[(_moves select 0)=="{expected}","weapon still pointed at casualty"] call _check;' if not lowered else ''))


@pytest.mark.parametrize('reason',['normal','mid-squeeze','full','no-bag'])
def test_actual_manual_bulb_emits_audio_only_for_an_accepted_squeeze(reason):
    change={'normal':'','mid-squeeze':'uiNamespace setVariable ["ACME_suction_sqT0",_nowTime];',
            'full':'uiNamespace setVariable ["ACME_suction_bagMl",1000];','no-bag':'_medic setVariable ["fixtureStock",[]];'}[reason]
    execute(suction_setup()+'''
      _medic setVariable ["fixtureStock",["ACM_SuctionBag"]];
      uiNamespace setVariable ["ACME_suctionRequestedDevice","bulb"];
      [true] call ACME_fnc_suctionSelectDevice;
    '''+change+'''
      ["squeeze"] call ACME_fnc_suctionBulb;
      ["squeeze"] call ACME_fnc_suctionBulb;
    '''+f'[count _manualSounds=={int(reason=="normal")},"accepted-squeeze audio missing or duplicate/full/invalid sound"] call _check;')


@pytest.mark.parametrize('type',['launcher','binocular'])
@pytest.mark.parametrize('preempted',[False,True])
def test_menu_stows_other_equipment_then_lowers_without_overwriting_new_treatment(type,preempted):
    from test_b156_menu_pose import setup
    s=setup().replace('weaponLowered _medic','false')
    field='_secondaryWeapon' if type=='launcher' else '_binocular'
    execute(s+f'''
      _currentWeapon="equipped";{field}="equipped";
      _medic setVariable ["ACME_menuPoseAfterTreatment",objNull];
      [_medic,_patient,_display] call ACME_fnc_menuPoseStart;
      [count _moves==0 && {{count _waits==1}},"launcher skipped stow preparation"] call _check;
      { '_medic setVariable ["ACME_treatmentPoseState",[99,"new"]];' if preempted else '' }
      0 call _runWait;
      [count _moves=={0 if preempted else 1},"deferred launcher kneel failed or overwrote successor"] call _check;
      { '[(_moves select 0)=="AmovPknlMstpSnonWnonDnon","launcher still pointed at patient"] call _check;' if not preempted else '' }
    ''')
