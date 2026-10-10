"""B233: actual owner transactions/geometry and change-only UI execution.

SQF-VM cannot render Arma or transport network packets. Pixel metrics, native
controls, inventory and scheduled/event delivery are explicit fixture boundaries.
"""
import json
import math
import re
import hashlib
import numpy as np
import pytest
from test_menu_death_lifecycle import ROOT, read, adapt, execute
from test_historical_vial_execution import map_defaults
from test_b232_iv_finish import SETUP, rules, START_SETUP, geometry_source
from test_b230_prepared_infusion_transaction import setup as carrier_setup, adapted
from test_bounded_selector_lifetime import ui_commands
from paa import read_paa


def fn(name):
    text=read(name)
    text=re.sub(r'\b_p\b','_patient',text)
    text=re.sub(r'\b_m\b','_medic',text)
    text=text.replace('serverTime','_clock')
    return 'ACME_fnc_'+name+'={'+adapted(text)+'};\n'


# Transform verification uses independently calculated pixel-space socket offsets,
# the real SQF transform, and actual target selection. Not a screenshot emulation.
FAMILIES={
    '':([.49166,.44434],[.49246,.50391],[0,-1]),
    '_15_left':([.47928,.44580],[.49867,.50244],[-.228,-.9737]),
    '_15_right':([.50434,.44482],[.48559,.50195],[.2301,-.9732]),
    '_30_left':([.46821,.44971],[.50242,.49951],[-.4642,-.8857]),
    '_30_right':([.51542,.45020],[.48117,.50049],[.468,-.8837]),
    '_ej':([.48588,.55127],[.48510,.49170],[-.0036,1]),
    '_ej_15_left':([.49876,.55127],[.47936,.49463],[.228,.9737]),
    '_ej_15_right':([.47418,.54883],[.49293,.49170],[-.2301,.9732]),
}

@pytest.mark.parametrize('family',list(FAMILIES))
@pytest.mark.parametrize('angle',[-15,0,15])
@pytest.mark.parametrize('aspect',[1050/1680,1440/5120])
def test_socket_and_port_share_catheter_transform(family,angle,aspect):
    anchor,hub,axis=FAMILIES[family]
    rad=math.radians(angle);theta=math.atan2(axis[0],-axis[1])+rad
    h=.8*.62;w=h*aspect
    x=.1+.7*.5+w*((hub[0]-anchor[0])*math.cos(rad)-(hub[1]-anchor[1])*math.sin(rad))
    y=.05+.8*.5+h*((hub[0]-anchor[0])*math.sin(rad)+(hub[1]-anchor[1])*math.cos(rad))
    du=(1033.02-1006.5)/2048;dv=(1386.52-1052)/2048
    px=x+w*(du*math.cos(theta)-dv*math.sin(theta));py=y+h*(du*math.sin(theta)+dv*math.cos(theta))
    execute(SETUP+rules()+START_SETUP+f'''
        _testPixelW={aspect};_testPixelH=1;_testAxis={json.dumps(axis)};
        _row set [6,"{family}"];_row set [13,{angle}];
        _patient setVariable ["ACME_IV_Marks",[_row]];
        uiNamespace setVariable ["ACME_IV_BodyRect",[.1,.05,.7,.8]];
        uiNamespace setVariable ["ACME_IV_FrameAnchors",createHashMapFromArray [["{family}",{json.dumps(anchor)}]]];
        uiNamespace setVariable ["ACME_IV_LineAnchors",createHashMapFromArray [["{family}",{json.dumps(hub)}]]];
        private _g=[_row] call ACME_fnc_ivFinishGeometry;
        [abs ((_g select 0)-{x})<0.00001 && {{abs ((_g select 1)-{y})<0.00001}},"real hub socket"] call _check;
        [abs (((_g select 2)/(_g select 3))-{aspect})<0.00001,"physical square"] call _check;
        private _port=[_row,[1033.02/2048,1386.52/2048],[1006.5/2048,1052/2048]] call ACME_fnc_ivFinishPoint;
        [abs ((_port select 0)-{px})<0.00001 && {{abs ((_port select 1)-{py})<0.00001}},"real distal socket"] call _check;
        private _hit=[{px},{py},"flush"] call ACME_fnc_ivFinishTarget;
        [count _hit==3 && {{((_hit select 0) select 14)=="ivhub:7:1"}},"same magnet and click target"] call _check;
    ''')

@pytest.mark.parametrize('tool,uv', [('extension',[1006.5,1032]),('flush',[1033.02,1386.52]),('dressing',[1006.5,1032]),('line',[1033.02,1386.52])])
def test_magnet_selects_exact_nearest_current_view_hub(tool,uv):
    execute(SETUP+rules()+START_SETUP+f'''
        private _other=+_row;_other set [2,0.9];_other set [14,"other"];
        private _back=+_row;_back set [1,"back"];_back set [14,"back"];
        _patient setVariable ["ACME_IV_Marks",[_other,_back,_row]];
        private _point=[_row,[{uv[0]}/2048,{uv[1]}/2048]] call ACME_fnc_ivFinishPoint;
        private _hit=[(_point select 0)+.01*0.5625,_point select 1,"{tool}"] call ACME_fnc_ivFinishTarget;
        [((_hit select 0) select 14)=="ivhub:7:1","closest valid view"] call _check;
        [([0,0,"{tool}"] call ACME_fnc_ivFinishTarget) isEqualTo [],"no global last-hub snap"] call _check;
    ''')

@pytest.mark.parametrize('action,wanted,unplugs', [
    ('removeExtension',[False]*4,1),('removeDressing',[True,True,False,True],0),('removeLine',[True,True,True,False],1)])
def test_exact_owner_component_cascade_and_replay(action,wanted,unplugs):
    expected=json.dumps(wanted).lower()
    execute(SETUP+rules()+f'''
        private _unplugs=[];ACME_fnc_ivAccessoryUnplug={{_unplugs pushBack _this;true}};
        _row set [15,[true,true,true,true]];
        private _other=+_row;_other set [14,"other"];_other set [10,"upper"];
        _patient setVariable ["ACME_IV_Marks",[_row,_other]];
        ["begin","{action}","remove"] call _invoke;
        _serverTime=101;["finish","{action}","remove"] call _invoke;
        ["finish","{action}","remove"] call _invoke;
        [(call _getState) isEqualTo {expected},"dependency cascade"] call _check;
        [count _unplugs=={unplugs},"single clinical disconnect"] call _check;
        [((call _getRow) select 4)=="hub","catheter preserved"] call _check;
        [(((_patient getVariable "ACME_IV_Marks") select 1) select 15) isEqualTo [true,true,true,true],"other site preserved"] call _check;
        [count (call _credits)==0,"removal gives no saline"] call _check;
    ''')

@pytest.mark.parametrize('change',['_testClinicalEpoch=8;','_distance=4;','_alive=false;','_hasIV=false;'])
def test_stale_accessory_pull_cannot_change_new_action(change):
    execute(SETUP+rules()+r'''
        private _unplugs=[];ACME_fnc_ivAccessoryUnplug={_unplugs pushBack _this;true};
        _row set [15,[true,true,true,true]];_patient setVariable ["ACME_IV_Marks",[_row]];
        ["begin","removeExtension","remove"] call _invoke;
    '''+change+r'''
        _serverTime=101;["finish","removeExtension","remove"] call _invoke;
        [(call _getState) isEqualTo [true,true,true,true] && {count _unplugs==0},"invalid completion did not yank"] call _check;
    ''')


def disconnect_setup():
    return carrier_setup()+fn('ivAccessoryUnplug')+r'''
        private _clock=100;private _settled=[];private _lineWrites=[];
        ACME_fnc_infusionDeliver={_settled pushBack _this;};
        ACME_fnc_detachedBagsCommit={params ["_p","_ids"];_p setVariable ["ACME_detachedBags",_ids];true};
        ACME_fnc_yLinesCommit={params ["_p","_lines"];_p setVariable ["ACME_YLines",_lines];_lineWrites pushBack _lines;true};
        private _a=["Saline",63,1,0,true,-1,100,-1,"a"];
        private _b=["Blood",123,1,1,true,0,500,-1,"b"];
        private _io=["Saline",77,1,0,false,-1,100,-1,"io"];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[_a,_b,_io]]]];
        private _med=[];_med resize 24;_med set [23,"a"];
        _patient setVariable ["ACME_infusion_BagMedications",[_med]];
        _patient setVariable ["ACME_YLines",["leftarm#true#0","leftarm#true#1"]];
        _patient setVariable ["ACME_yFlushJobs",createHashMapFromArray [["leftarm#true#0",[1]],["leftarm#true#1",[2]]]];
    '''


def test_unplug_keeps_remaining_volume_and_dose_custody_without_phantom_delivery():
    execute(disconnect_setup()+r'''
        [_patient,"leftarm",0] call ACME_fnc_ivAccessoryUnplug;
        [(_patient getVariable "ACME_IV_DisconnectedBagUIDs") isEqualTo ["a"],"exact IV only"] call _check;
        [(_patient getVariable "ACME_detachedBags") isEqualTo ["a"],"remaining bag retained but detached"] call _check;
        [((_patient getVariable "ACM_circulation_IV_Bags") get "leftarm") isEqualTo [_a,_b,_io],"no volume edit"] call _check;
        [count _settled==1 && {((_settled select 0) select 2)},"settle delivered dose only"] call _check;
        [(_patient getVariable "ACME_infusion_BagMedications") isEqualTo [_med],"remaining drug not discarded or converted"] call _check;
        [(_patient getVariable "ACME_YLines") isEqualTo ["leftarm#true#1"],"other Y access kept"] call _check;
        [keys (_patient getVariable "ACME_yFlushJobs") isEqualTo ["leftarm#true#1"],"exact service retired"] call _check;
    ''')

@pytest.mark.parametrize('physical',[False,True])
def test_native_positive_flow_cannot_reconnect_a_yanked_line(physical):
    s=(ROOT/'addons/circulation/functions/fnc_getBloodVolumeChange.sqf').read_text()
    start=s.index('            private _detached =')
    end=s.index('            };',start)+len('            };')
    code=adapt(s[start:end]).replace('_unit','_patient')
    execute(carrier_setup()+f'''
        private _bagUid="a";private _partIndex=2;private _iv=true;private _accessSite=0;
        _patient setVariable ["ACME_detachedBags",["a"]];
        _patient setVariable ["ACME_IV_DisconnectedBagUIDs",{ '["a"]' if physical else '[]'}];
        ACM_circulation_fnc_getIVFlowRate={{1}};
    '''+code+f'''
        [_heldDetached=={str(physical).lower()},"positive access flow respects physical disconnect"] call _check;
    ''')

@pytest.mark.parametrize('case',['normal','duplicate','new_uid','range','epoch'])
def test_catheter_yank_uses_exact_current_uid_and_removes_all_children(case):
    body=SETUP+rules()+r'''
        private _patientLocal=true;private _clock=100;private _removed=[];private _unplug=[];private _logs=[];
        ACME_fnc_ivAccessoryUnplug={_unplug pushBack _this;true};
        ACM_circulation_fnc_setIVLocal={_removed pushBack _this;};
        ACME_fnc_ivLogSite={"left arm"};ace_common_fnc_getName={"Medic"};
        ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
        _row set [15,[true,true,true,true]];_patient setVariable ["ACME_IV_Marks",[_row]];
    '''+fn('ivCatheterPull')
    if case=='new_uid': body+='_row set [14,"new"];_patient setVariable ["ACME_IV_Marks",[_row]];'
    if case=='range': body+='_distance=4;'
    if case=='epoch': body+='_testClinicalEpoch=8;'
    body+='[_patient,_medic,"ivhub:7:1",7] call ACME_fnc_ivCatheterPull;'
    if case=='duplicate':body+='[_patient,_medic,"ivhub:7:1",7] call ACME_fnc_ivCatheterPull;'
    count=1 if case in ['normal','duplicate'] else 0
    body+=f'[count _removed=={count} && {{count _unplug=={count}}} && {{count _logs=={count}}},"exactly one or no removal"] call _check;'
    if count:body+='[(((call _getRow) select 4)=="removed") && {(call _getState) isEqualTo [false,false,false,false]},"all accessory children removed"] call _check;'
    execute(body)


def fbtk_setup(capacity=250):
    s=carrier_setup().replace('case (_classname in []):','case (_classname in ["FieldBloodTransfusionKit_250","FieldBloodTransfusionKit_500"]):')
    return s+fn('fbtkHangCommit')+fn('fbtkHangReply')+fn('fbtkHangRetry')+r'''
        ACME_fnc_patientInteractionDistance={_distance};
        private _clock=100;private _generated=0;private _settlements=[];
        ace_common_fnc_getName={"Medic"};
        ACM_circulation_fnc_generateBloodType={_generated=_generated+1;_patient setVariable ["ACM_circulation_BloodType",0];};
        ACME_fnc_treatmentSupplyRefund={_settlements pushBack _this;};
        _patient setVariable ["ACM_circulation_BloodType",-1];
    '''+f'private _req=[_patient,_medic,"leftarm",0,"ACM_FieldBloodTransfusionKit_{capacity}","fbtk:1",1,110];'

@pytest.mark.parametrize('capacity',[250,500])
@pytest.mark.parametrize('case',['normal','nil_return','duplicate','expired','bad_epoch','no_iv','occupied','y_line','out_of_range','unconscious','wrong_class','future'])
def test_native_fbtk_attaches_once_immediately_or_preserves_state(capacity,case):
    body=fbtk_setup(capacity)
    changes={'nil_return':'_returnMode="nil";', 'expired':'_clock=111;', 'bad_epoch':'_req set [6,2];',
       'no_iv':'_validAccess=false;', 'y_line':'_hasY=true;', 'out_of_range':'_distance=4;',
       'unconscious':'_medic setVariable ["ACE_isUnconscious",true];', 'wrong_class':'_req set [4,"ACE_salineIV"];',
       'future':'_req set [7,1000];', 'occupied':'(_patient getVariable "ACM_circulation_IV_Bags") set ["leftarm",[["Saline",99,1,0,true,-1,100,-1,"old"]]];'}
    body+=changes.get(case,'')+'_req call ACME_fnc_fbtkHangCommit;'
    if case=='duplicate':body+='_req call ACME_fnc_fbtkHangCommit;'
    good=case in ['normal','nil_return','duplicate']
    body+=f'[count _logs=={int(good)},"single collection log"] call _check;'
    body+=f'[_factoryCalls=={int(good)},"single native factory call"] call _check;'
    if good:
        body+=f'''
            private _bags=(_patient getVariable "ACM_circulation_IV_Bags") get "leftarm";
            [count _bags==1 && {{((_bags select 0) select [0,7]) isEqualTo ["FBTK",0,1,0,true,-1,{capacity}]}},"empty native collection bag not saline"] call _check;
            [_patient getVariable ["ACM_circulation_IV_Bags_Active",false],"collection master running"] call _check;
            [(((_patient getVariable "ACM_circulation_FluidBagsFlow_IV") select 2) select 0)==1,"actual site running"] call _check;
            [count _waits==0,"no attachment timer"] call _check;
        '''
    else:body+='[count _bagWrites==0 && {count _activeWrites==0},"rejected without mutation"] call _check;'
    execute(body)

@pytest.mark.parametrize('ok',[False,True])
def test_fbtk_ack_settles_only_matching_pending_receipt_once(ok):
    execute(fbtk_setup()+f'''
        private _receipt=[_medic,"ACM_FieldBloodTransfusionKit_250",objNull,"stock1"];
        _medic setVariable ["ACME_fbtkPending",[_patient,"fbtk:1",_receipt,[],objNull]];
        [_medic,_patient,"wrong",true,""] call ACME_fnc_fbtkHangReply;
        [count _settlements==0,"unsolicited ACK inert"] call _check;
        [_medic,_patient,"fbtk:1",{str(ok).lower()},""] call ACME_fnc_fbtkHangReply;
        [_medic,_patient,"fbtk:1",{str(ok).lower()},""] call ACME_fnc_fbtkHangReply;
        [count _settlements==1 && {{((_settlements select 0) select 1)=={str(not ok).lower()}}},"only rejected receipt refunded"] call _check;
    ''')


def ui_setup():
    text=read('transfusionUiSet')
    for command,prop in [('ctrlPosition','position'),('ctrlShown','show'),('ctrlEnabled','enable'),('ctrlTextColor','color'),('ctrlText','text')]:
        text=text.replace(f'{command} _c',f'(_state get "{prop}")')
    text=ui_commands(adapt(text))
    return r'''
        private _state=createHashMapFromArray [["position",[0,0,1,1]],["show",true],["enable",true],["text","same"],["color",[1,1,1,1]]];
        private _writes=[];
        private _write={params ["_c","_cmd","_value"];_writes pushBack _this;
            private _prop=switch (_cmd) do {case "ctrlSetPosition":{"position"};case "ctrlShow":{"show"};case "ctrlEnable":{"enable"};case "ctrlSetText":{"text"};case "ctrlSetTextColor":{"color"};default {"commit"};};
            if (_prop!="commit") then {_state set [_prop,_value];};
        };
    '''+'ACME_fnc_transfusionUiSet={'+text+'};'

@pytest.mark.parametrize('property,value,new', [('position','[0,0,1,1]','[1,1,1,1]'),('show','true','false'),('enable','true','false'),('text','"same"','"new"'),('color','[1,1,1,1]','[1,0,0,1]')])
def test_static_buttons_do_not_recommit_or_toggle_every_frame(property,value,new):
    execute(ui_setup()+f'''
        for "_i" from 0 to 50 do {{[_medic,"{property}",{value}] call ACME_fnc_transfusionUiSet;}};
        [count _writes==0,"stable frame caused UI churn"] call _check;
        [_medic,"{property}",{new}] call ACME_fnc_transfusionUiSet;
        [count _writes=={2 if property=='position' else 1},"one changed property"] call _check;
        private _n=count _writes;
        [_medic,"{property}",{new}] call ACME_fnc_transfusionUiSet;
        [count _writes==_n,"no repeated hit-rectangle commit"] call _check;
    ''')


def test_hotspot_hover_does_not_reenter_full_renderer():
    source=read('updateTransfusionAccessHotspots')
    for event in ('MouseEnter','MouseExit'):
        match=re.search(r'ctrlAddEventHandler \["'+event+r'",\s*\{(.*?)\}\];',source,re.S)
        assert match
        assert 'ACME_fnc_updateTransfusionAccessHotspots' not in match[1]
        assert 'ctrlSetPosition' not in match[1]
    assert 'ACME_fnc_transfusionUiSet' in source
    assert 'ACME_fnc_transfusionUiSet' in read('updateTransfusionControls')


def test_transfuse_action_has_left_icon_and_immediate_inventory_path():
    config=(ROOT/'addons/acm_extended/config.cpp').read_text()
    assert 'ACME_LBTN(ACE_salineIV_500)' in config
    assert r'\z\ace\addons\medical_treatment\ui\salineIV_ca.paa' in config
    treatment=(ROOT/'addons/core/overrides/fnc_treatment.sqf').read_text()
    block=treatment.split('if (_classname == "OpenTransfusionMenu") exitWith {',1)[1].split('\n};',1)[0]
    assert 'ACM_circulation_fnc_openTransfusionMenu' in block
    assert 'progressBar' not in block and 'weaponAway' not in block
    assert 'canTreatCached' in block and 'canInteractWith' in block and '_rangeOkay' in block
    assert 'opentransfusionmenu' in (ROOT/'addons/gui/overrides/fnc_updateActions.sqf').read_text()


def test_fbtk_never_requires_an_external_administration_set_or_native_five_seconds():
    spike=read('transfusionSpikeOrAdd')
    assert spike.index('call ACME_fnc_fbtkHang')<spike.index('"ACME_IVLine"')
    for name in ('fbtkHang','fbtkHangCommit'):
        assert 'ACME_IVLine' not in read(name)
        assert 'progressBar' not in read(name)
    native=(ROOT/'addons/circulation/functions/fnc_TransfusionMenu_AddBag.sqf').read_text()
    assert native.index('call ACME_fnc_fbtkHang')<native.index('progressBar')
    assert '"Hang Bag"' in read('updateTransfusionControls')


def test_flush_switch_reuses_display_and_checks_flush_not_empty_syringe_stock():
    pick=read('skPickFlush');size=read('skApplySize')
    assert '[10, _flushClass] call ACME_fnc_skApplySize' in pick
    assert 'closeDisplay' not in pick and 'skOpenDraw' not in pick and 'waitAndExecute' not in pick
    assert 'call ACME_fnc_skWasteBegin' in pick
    assert '"ACM_SalineFlush_10"' in size
    assert '_flushClass == ""' in size and '_flushClass != ""' in size
    assert 'call ACME_fnc_skCompoundCommit' in size

@pytest.mark.parametrize('tool',['extension','flush','dressing','line'])
def test_runtime_preview_paa_is_registered_square_and_nonempty(tool):
    base=ROOT/'addons/acm_extended/ui/iv/finish';name=f'cursor_{tool}_ca.paa'
    rgb,a=read_paa(base/name)
    assert a.shape==(1024,1024)
    assert a.max()>32 and (a==0).any() # translucent dressing must remain translucent
    manifest=json.loads((base/'manifest.json').read_text())
    assert hashlib.sha256((base/name).read_bytes()).hexdigest()==manifest['files'][name]
    assert '"ACME_IV_CathCursor"' in read('ivHeldRaise')


def test_complete_syringe_preview_includes_projecting_shaft_and_thumbpad():
    base=ROOT/'addons/acm_extended/ui/iv/finish'
    _,full=read_paa(base/'cursor_flush_ca.paa');_,frame=read_paa(base/'blood_return_flush_0047_ca.paa')
    assert np.abs(full[697:].astype(float)-frame[697:].astype(float)).mean()<.5
    assert full[:690].max()==0
    _,icon=read_paa(base/'icon_flush_ca.paa');ys,xs=(icon>127).nonzero()
    assert ys.min()>=4 and ys.max()<252
    assert ys.max()-ys.min()>220
    assert icon[8:70].max()>128 and icon[170:245].max()>128
    # Top segment contains narrow projecting shaft with thumbpad, not just barrel.
    narrow=[int((icon[y]>127).sum()) for y in range(30,80)]
    assert min(narrow)>0 and max(narrow)<20


def test_syringe_pull_and_accessory_pull_have_separate_patient_bound_targets():
    click=read('ivMinigameClick');stop=read('ivMinigamePullStop')
    assert 'ACME_fnc_ivFinishSyringeHit' in click and 'ACME_IV_FlushPullPin' in click
    assert 'ACME_IV_PullUID' in stop and 'ACME_IV_PullKind' in stop
    assert '"ivCatheterPull"' in stop
    assert '[0,0,_kind,_uid] call ACME_fnc_ivFinishStart' in stop
    assert '0.035*_h' in read('ivFinishTick')
    assert 'ACME_IV_FlushPullPin' in read('ivFinishAbort')
