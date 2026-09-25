"""Actual catheter queue retirement and suction-to-oxygen target handoff.

Engine/config/inventory/transport and clock-delta boundaries are fixtures. The
full catheter setter and suction debt calculations execute; this does not test
live bag replication, downstream infusion kinetics or complete oxygen physiology.
"""
import json
import re
import pytest
from test_menu_death_lifecycle import ROOT, execute
from test_historical_medication_effects import setup as effects_setup, code

F=ROOT/'addons/acm_extended/functions'
C=ROOT/'addons/circulation/functions'


def catheter_setup():
    text=(C/'fnc_setIVLocal.sqf').read_text()
    text=text.replace('ALL_BODY_PARTS','["head","body","leftarm","rightarm","leftleg","rightleg"]')
    text=text.replace('GET_IV(_patient)','(_patient getVariable ["ACM_circulation_IV_Placement",[]])')
    text=text.replace('GET_IO(_patient)','(_patient getVariable ["ACM_circulation_IO_Placement",[]])')
    text=text.replace('isClass (configFile >> "CfgWeapons" >> _item)','_itemExists')
    identity=(F/'fn_medicationLineIdentity.sqf').read_text()
    return effects_setup()+'''
        private _itemExists=true;
        private _returns=[];private _settled=[];private _updates=[];
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["ACME_clinicalEpoch",1]};
        ACME_fnc_setVarNet={params ["_p","_k","_v"];_p setVariable [_k,_v];};
        ACM_circulation_fnc_getReturnVolume={250};
        ACM_circulation_fnc_formatFluidBagName={"bag_item"};
        ACME_fnc_bagIdentity={params ["_p","_part","_i"]; ((_p getVariable "ACM_circulation_IV_Bags") get _part) select _i select 6;};
        ACME_fnc_infusionDeliver={_settled pushBack _this;};
        ace_common_fnc_addToInventory={_returns pushBack _this;};
        ACME_fnc_clinicalNotice={};
        ACM_circulation_fnc_updateActiveFluidBags={_updates pushBack _this;};
        _patient setVariable ["ACM_circulation_IV_Placement",[[0,0,0],[0,0,0],[1,2,3],[0,0,0],[0,0,0],[0,0,0]]];
        _patient setVariable ["ACM_circulation_IO_Placement",[0,0,4,0,0,0]];
        private _drugEntry={params ["_uid"];private _entry=[];_entry resize 24;_entry set [23,_uid];_entry};
    '''+'ACM_circulation_fnc_setIVLocal={'+code(text)+'};'+\
        'ACME_fnc_medicationLineIdentity={'+code(identity)+'};'


@pytest.mark.parametrize('iv,site',[(True,0),(True,1),(True,2),(False,-1)])
@pytest.mark.parametrize('operation',[0,5])
def test_catheter_change_invalidates_only_exact_line_and_legacy_queue(iv,site,operation):
    removed=1+(2 if site==-1 else site+2)
    execute(catheter_setup()+'''
        private _queue=[
            ["leftarm","legacy",1,0,0,-2],
            ["leftarm","iv0",2,0,0,0],
            ["leftarm","iv1",3,0,0,1],
            ["leftarm","iv2",4,0,0,2],
            ["leftarm","io",2,0,0,-1],
            ["rightarm","other",8,0,0,0]];
        _patient setVariable ["ACME_pendingFlush",_queue];
    '''+f'private _old=[_patient,"leftarm",{site}] call ACME_fnc_medicationLineIdentity;'+
        f'[_medic,_patient,"LeftArm",{operation},{str(iv).lower()},{site},1] call ACM_circulation_fnc_setIVLocal;'+'''
        private _kept=_patient getVariable ["ACME_pendingFlush",[]];
        [count _kept==4,"removed another line or retained old queue"] call _check;
        [["rightarm","other",8,0,0,0] in _kept,"other limb lost pending drugs"] call _check;
        private _discard=_patient getVariable ["ACME_medicationDiscarded",createHashMap];
        private _total=0; {_total=_total+(_discard get _x);} forEach keys _discard;
    '''+f'[_total=={removed},"removed dose not recorded exactly"] call _check;'+
        f'private _new=[_patient,"leftarm",{site}] call ACME_fnc_medicationLineIdentity;'+
        ('[count _new==0,"removed catheter identity survived"] call _check;' if operation==0 else '[(_new select 1)==(_old select 1)+1 && {(_new select 2)==5},"replacement reused old identity"] call _check;')+
        f'[_medic,_patient,"leftarm",0,{str(iv).lower()},{site},1] call ACM_circulation_fnc_setIVLocal;'+'''
        private _again=_patient getVariable "ACME_medicationDiscarded";
        private _totalAgain=0;{_totalAgain=_totalAgain+(_again get _x);} forEach keys _again;
        [_totalAgain==_total,"repeated removal discarded a dose twice"] call _check;
    ''')


@pytest.mark.parametrize('part,iv,site,epoch', [('leftarm',True,3,1),('missing',True,0,1),('leftarm',True,0,2)])
def test_rejected_catheter_change_has_no_queue_generation_or_inventory_effect(part,iv,site,epoch):
    execute(catheter_setup()+'''
        private _before=[["leftarm","drug",2,0,0,0]];
        _patient setVariable ["ACME_pendingFlush",_before];
    '''+f'[_medic,_patient,"{part}",0,{str(iv).lower()},{site},{epoch}] call ACM_circulation_fnc_setIVLocal;'+'''
        [(_patient getVariable "ACME_pendingFlush") isEqualTo _before,"rejected removal lost queue"] call _check;
        [isNil {_patient getVariable "ACME_medicationLineGenerations"},"rejected removal advanced identity"] call _check;
        [count _returns==0 && {count _updates==0} && {count _settled==0},"rejected removal changed bags"] call _check;
    ''')


def test_nonlocal_catheter_request_is_forwarded_without_local_mutation():
    execute(catheter_setup()+'''
        _patientLocal=false;
        [_medic,_patient,"leftarm",0,true,0,1] call ACM_circulation_fnc_setIVLocal;
        [count _events==1 && {isNil {_patient getVariable "ACME_medicationLineGenerations"}},"nonowner mutated catheter"] call _check;
        [(_events select 0) isEqualTo ["ACM_circulation_setIVLocal",[_medic,_patient,"leftarm",0,true,0,1],_patient],"forwarded request changed identity"] call _check;
    ''')


@pytest.mark.parametrize('kind',['ordinary','medicated','FreshBlood','ACME_SalineY','missing-item'])
@pytest.mark.parametrize('alive',[True,False])
def test_access_removal_preserves_special_bag_identity_and_other_line_custody(kind,alive):
    retained=kind!='ordinary'
    bagtype='Saline' if kind in ('ordinary','medicated','missing-item') else kind
    execute(catheter_setup()+f'_patientAlive={str(alive).lower()};_itemExists={str(kind!="missing-item").lower()};'+
        f'private _selected=["{bagtype}",300,1,0,true,0,"chosen"];'+'''
        private _other=["Saline",500,1,1,true,0,"other"];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[_selected,_other]]]];
    '''+('_patient setVariable ["ACME_infusion_BagMedications",[["chosen"] call _drugEntry]];' if kind=='medicated' else '')+'''
        [_medic,_patient,"leftarm",0,true,0,1] call ACM_circulation_fnc_setIVLocal;
        private _rows=(_patient getVariable "ACM_circulation_IV_Bags") get "leftarm";
        [_other in _rows,"unrelated line lost its bag"] call _check;
    '''+f'[_selected in _rows isEqualTo {str(retained).lower()},"special bag was converted or ordinary bag not returned"] call _check;'+
        f'[count _returns=={int(not retained)} && {{count _settled=={int(kind=="medicated")}}},"bag return/settlement count wrong"] call _check;'+
        f'[("chosen" in (_patient getVariable ["ACME_detachedBags",[]])) isEqualTo {str(retained).lower()},"detached UID lost"] call _check;')


def suction_setup():
    text=(F/'fn_suctionPhysiologyTick.sqf').read_text()
    text=text.replace('_medic distance _patient','_distance')
    text=text.replace('objectParent _medic','objNull').replace('objectParent _patient','objNull')
    text=text.replace('(_proof param [0, objNull]) == _patient','(_proof param [0, objNull]) isEqualTo _patient')
    oxygen=(ROOT/'addons/core/overrides/fnc_updateOxygen.sqf').read_text()
    fragment=oxygen[oxygen.index('[_patient] call ACME_fnc_suctionPhysiologyTick;'):oxygen.index('#define IDEAL_PPO2')]
    fragment=fragment.replace('ACM_TARGETVITALS_OXYGEN(_patient)','98')
    return effects_setup()+'''
        private _dt=1;private _equipment=1;
        ACME_fnc_clinicalTickDelta={_dt};
        ACME_fnc_clinicalEpoch={1};
        ACME_fnc_setVarNet={params ["_p","_k","_v"];_p setVariable [_k,_v];};
        ace_common_fnc_getCountOfItem={_equipment};
        ACME_fnc_treatmentSupplyCount={[_this select 0,_this select 2] call ace_common_fnc_getCountOfItem};
        private _session={params ["_mode"];["suction",_medic,1000,_mode,1,0,[.1,.2]]};
    '''+'ACME_fnc_suctionPhysiologyTick={'+code(text)+'};'+\
        'private _oxygenTarget={'+code(fragment,'core')+'_desiredOxygenSaturation};'


@pytest.mark.parametrize('mode,factor,cap',[('hand',1,6),('salad',.15,1)])
@pytest.mark.parametrize('supported',[False,True])
def test_suction_debt_is_computed_before_one_native_target_deduction(mode,factor,cap,supported):
    # Twenty seconds: existing grace 10; sum 1..10 of 0.25*(over/20).
    expected=.6875*factor*(.5 if supported else 1)
    execute(suction_setup()+f'_patient setVariable ["ACME_suctionSessions",[["{mode}"] call _session]];'+
        f'_patient setVariable ["ACME_vent_driving",{str(supported).lower()}];'+'''
        private _value=0;
        for "_i" from 1 to 10 do {_value=call _oxygenTarget;};
        [_value==98,"grace period lost"] call _check;
        for "_i" from 1 to 10 do {_value=call _oxygenTarget;};
        private _debt=_patient getVariable ["ACME_o2Drain_suction",0];
    '''+f'[abs (_debt-{expected})<.00001,"suction dt/support/risk scaling changed"] call _check;'+'''
        [abs (_value-(98-_debt))<.00001,"target penalty missing or applied twice"] call _check;
    ''')


@pytest.mark.parametrize('count',[1,2,3])
def test_simultaneous_suction_providers_do_not_multiply_penalty(count):
    execute(suction_setup()+f'private _sessions=[];for "_i" from 1 to {count} do {{_sessions pushBack (["hand"] call _session);}};_patient setVariable ["ACME_suctionSessions",_sessions];'+'''
        for "_i" from 1 to 20 do {call _oxygenTarget;};
        [abs ((_patient getVariable ["ACME_o2Drain_suction",0])-.6875)<.00001,"provider count multiplied debt"] call _check;
    ''')


@pytest.mark.parametrize('change',['_equipment=0;','_patientAlive=false;','_alive=false;','_distance=6;','CBA_missionTime=1000;','_medic setVariable ["ACE_isUnconscious",true];'])
def test_invalid_suction_session_retires_without_applying_new_debt(change):
    execute(suction_setup()+'''
        _patient setVariable ["ACME_suctionSessions",[["hand"] call _session]];
    '''+change+'''
        private _value=call _oxygenTarget;
        [_value==98 && {(_patient getVariable ["ACME_suctionSessions",[]]) isEqualTo []},"invalid suction retained effect/session"] call _check;
    ''')


def test_native_target_is_the_only_suction_penalty_consumer_in_reviewed_paths():
    oxygen=(ROOT/'addons/core/overrides/fnc_updateOxygen.sqf').read_text()
    assert oxygen.count('getVariable ["ACME_o2Drain_suction", 0]')==1
    for name in ('altitudeTick','ventDriveTick'):
        assert 'ACME_o2Drain_suction' not in (F/('fn_'+name+'.sqf')).read_text()


@pytest.mark.parametrize('iv,site',[(True,0),(False,-1)])
@pytest.mark.parametrize('special',[False,True])
def test_catheter_bag_matching_distinguishes_iv_from_io_even_at_equal_site_values(iv,site,special):
    # Equal site numbers are deliberate: the access-kind guard must discriminate
    # independently rather than accidentally relying on the usual IV/IO sites.
    flag=str(iv).lower();otherflag=str(not iv).lower()
    kind='FreshBlood' if special else 'Saline'
    execute(catheter_setup()+f'private _selected=["{kind}",300,1,{site},{flag},0,"selected"];'+
        f'private _opposite=["Saline",300,1,{site},{otherflag},0,"opposite"];'+'''
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[_opposite,_selected]]]];
    '''+f'[_medic,_patient,"leftarm",0,{flag},{site},1] call ACM_circulation_fnc_setIVLocal;'+'''
        private _bags=(_patient getVariable "ACM_circulation_IV_Bags") get "leftarm";
        [_opposite in _bags,"other access-kind bag removed"] call _check;
    '''+f'[count _returns=={int(not special)},"wrong bag return count"] call _check;'+
        f'[(_selected in _bags) isEqualTo {str(special).lower()},"wrong chosen bag retention"] call _check;')
