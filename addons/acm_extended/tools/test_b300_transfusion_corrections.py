"""Current UI/native empty ownership and authenticated propofol piggyback execution."""
import importlib.util
import json
import re
import subprocess
import pytest
from test_menu_death_lifecycle import ROOT,execute,read
from test_b275_piggyback_owner import owner_setup
from test_b289_piggyback_fluids import request_chain_setup
from test_b278_transfusion_geometry import renderer_setup
from test_b293_react_bridge import tick_setup

BASE='2e463fd1457905fd1f6bb087bbc87991e08a36ae'
PALETTE='0d1e5fc04a11514ed06ca98d1188699d0c78ea4a'

BOTTLE=r'''
_configuredType="ACME_Propofol";_configuredVolume=50;_validClasses pushBack "Propofol_IV";
_prepared=["set1","ACM_Vial_Propofol","ACME_PropofolIV_50","Propofol",500,600,20,0,0,10,50,0,_medic,objNull,[["Propofol",500,1]],"set1",50,"propofol-bottle"];
_set set [1,"ACM_Vial_Propofol"];_set set [2,"ACME_PropofolIV_50"];_set set [8,"propofol"];_set set [9,50];
_prepared set [1,"ACM_Vial_Propofol"];_prepared set [2,"ACME_PropofolIV_50"];_prepared set [3,"Propofol"];
_prepared set [4,500];_prepared set [10,50];_prepared set [14,[["Propofol",500,1]]];
_prepared set [16,50];_prepared set [17,"propofol-bottle"];
'''

@pytest.mark.parametrize('mode',['normal','nil','bool'])
def test_propofol_secondary_keeps_its_own_bottle_dose_uid_and_primary(mode):
    execute(owner_setup()+BOTTLE+f'_returnMode="{mode}";'+r'''
        _ownerArgs set [9,_set];_ownerArgs set [10,_prepared];call _reserve;
        call _send;
        [call _ack select 3,"genuine propofol bottle rejected"] call _check;
        private _bags=call _stock;private _bottle=_bags select 2;
        [count _bags==3 && {_bags select 0 isEqualTo _primary} && {_bags select 1 isEqualTo _neighbor},"primary or neighboring fluid changed"] call _check;
        [(_bottle select 0)=="ACME_Propofol" && {(_bottle select 1)==50} && {(_bottle select 6)==50},"propofol diluted or changed carrier"] call _check;
        private _entries=call _entries;private _med=_entries select 1;
        [count _entries==2 && {(_med select 11)=="Propofol"} && {(_med select 14)==500} && {(_med select 23)==(_bottle select 8)},"dose lost its exact bottle UID"] call _check;
        [abs ((_med select 26)-10)<.00001,"propofol concentration changed"] call _check;
        [[_patient,"leftarm",true,0,"primary"] call ACME_fnc_piggybackFlow isEqualTo [true,false],"primary not held for secondary"] call _check;
        call _send;
        [_factoryCalls==1 && {count _logs==1} && {count (call _stock)==3},"replay duplicated bottle"] call _check;
    ''')

@pytest.mark.parametrize('change',[
 '_prepared set [17,"other"];', '_prepared set [10,49];', '_set set [9,49];',
 '_prepared set [14,[["Propofol",400,1]]];','_prepared set [14,[["Propofol",500,1],["Lidocaine",1,1]]];',
 '_prepared set [1,"saline100"];','_set set [8,"saline"];','_prepared set [15,"other"];',
 '_configuredVolume=100;', '_primary set [0,"Blood"];','_primary set [0,"Plasma"];',
])
def test_malformed_or_incompatible_propofol_cannot_consume_or_create_a_carrier(change):
    execute(owner_setup()+BOTTLE+change+r'''
        _ownerArgs set [9,_set];_ownerArgs set [10,_prepared];call _reserve;
        call _send;
        [!(call _ack select 3) && {_factoryCalls==0},"invalid bottle reached carrier creation"] call _check;
        call _assertUnchanged;
    ''')

@pytest.mark.parametrize('failure',['','wrong-site','wrong-volume','double'])
def test_full_propofol_request_owner_ack_preserves_exact_inventory_once(failure):
    execute(request_chain_setup()+BOTTLE+f'_returnMode="{failure}";'+r'''
        _medic setVariable ["ACME_preparedIVSets",[_set]];
        _medic setVariable ["ACME_infusion_PreparedBags",[_prepared]];
        ["set1"] call ACME_fnc_piggybackAttachRequest;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [] && {(_medic getVariable "ACME_infusion_PreparedBags") isEqualTo []},"reserved bottle stayed available twice"] call _check;
        private _reply=call _ack;
        _reply call ACME_fnc_piggybackAttachAck;_reply call ACME_fnc_piggybackAttachAck;
        [count _inventorySettlements==1 && {count (_medic getVariable "ACME_piggybackEscrow")==0},"ACK duplicated inventory settlement"] call _check;
    '''+(r'''
        [_reply select 3 && {count (call _stock)==3},"valid bottle failed attachment"] call _check;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [] && {(_medic getVariable "ACME_infusion_PreparedBags") isEqualTo []},"accepted bottle was refunded"] call _check;
    ''' if not failure else r'''
        [!(_reply select 3),"bad native carrier accepted"] call _check;
        [(_medic getVariable "ACME_preparedIVSets") isEqualTo [_set] && {(_medic getVariable "ACME_infusion_PreparedBags") isEqualTo [_prepared]},"rejection lost exact prepared bottle"] call _check;
    '''))


def test_one_native_empty_caption_stays_visible_during_react_handoff_and_updates():
    execute(renderer_setup()+r'''
        _counts set [86004,0];_counts set [86129,0];
        missionNamespace setVariable ["ACME_reactActive",true];
        ACME_fnc_reactMedicalOpen={};
        for "_i" from 0 to 20 do {
            [missionNamespace] call ACME_fnc_updateTransfusionCards;
            [(_controlValues get "86600:show") && {(_controlValues get "86601:show")},"native empty caption hidden by React"] call _check;
            [!(missionNamespace getVariable "ACME_txFluidHasCard"),"empty native list marked occupied"] call _check;
        };
        [_controlValues get "86600:text" == "No fluids at this access","empty text changed"] call _check;
    ''')
    app=(ROOT/'frontend/medical-ui/App.jsx').read_text();css=(ROOT/'frontend/medical-ui/style.css').read_text()
    assert 'No fluids at this access' not in app and '.empty' not in css


def test_empty_browser_is_hidden_without_retiring_the_ready_renderer():
    execute(tick_setup()+r'''
        _view setVariable ["ACME_txFluidHasCard",false];
        [_view] call ACME_fnc_reactMedicalTick;
        [!_browserShown && {!_enabled} && {_view getVariable "ACME_reactActive"},"empty pane intercepted its native caption"] call _check;
        _view setVariable ["ACME_txFluidHasCard",true];_nowTime=_nowTime+.11;
        [_view] call ACME_fnc_reactMedicalTick;
        [_browserShown && {_enabled},"adding a fluid failed to show existing browser"] call _check;
    ''')


def test_stop_and_bag_actions_have_one_equal_width_top_row_and_service_keeps_lower_row():
    source=read('layoutTransfusionMenu')
    placements={}
    for ctrl,x,y,w,h in re.findall(r'\[(86006|86170|86143),([\d.]+),([\d.]+),([\d.]+),([\d.]+)\]',source):
        placements.setdefault(int(ctrl),[]).append(tuple(map(float,[x,y,w,h])))
    assert placements[86006]==[(.125,.188,.102,.033)]
    assert placements[86170]==[(.235,.188,.102,.033)]
    assert placements[86143]==[(.125,.478,.212,.033)]
    assert '[_x' not in source[source.index('// Mirrored top actions and lower footer rows keep both sides on the same grid.'):source.index('[_ctrlFluids,"show"')]


def test_original_flat_material_is_byte_exact_and_no_glass_effect_remains():
    folder=ROOT/'addons/acm_extended/ui/transfusion'
    for p in folder.glob('*_ca.paa'):
        if p.name=='body_gradient_ca.paa':continue
        assert p.read_bytes()==subprocess.check_output(['git','show',PALETTE+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT),p.name
    css=(ROOT/'frontend/medical-ui/style.css').read_text();generator=(ROOT/'tools/generate_transfusion_chrome.py').read_text()
    assert 'backdrop-filter' not in css and 'gradient' not in css and 'animation' not in css and 'transition' not in css
    assert 'window_material' not in generator
    assert 'color-scheme: normal' in css


def test_prepared_propofol_is_not_silently_filtered_and_validated_before_reservation():
    source=read('updateTransfusionControls');a=source.index('private _shownPrepared');b=source.index('private _signature',a)
    block=source[a:b]
    assert 'call ACME_fnc_piggybackPreparedValid' in block and 'propofol-bottle' not in block
    request=read('piggybackAttachRequest')
    assert request.index('call ACME_fnc_piggybackPreparedValid')<request.index('call ACME_fnc_inventoryLedgerReserve')
    assert read('piggybackAttachLocal').index('call ACME_fnc_piggybackPreparedValid')<read('piggybackAttachLocal').index('call ace_medical_treatment_fnc_ivBagLocal')

@pytest.mark.parametrize('piggyback',[False,True])
def test_live_prepared_list_keeps_propofol_and_saline_infusion_without_mutating_stock(piggyback):
    source=read('updateTransfusionControls');block=source[source.index('private _shownPrepared'):source.index('if (!isNull _ctrlPreparedList)',source.index('private _shownPrepared'))]
    block=re.sub(r'private _carrier = [^;]+;', 'private _carrier = if ((_entry param [2,""]) == "ACME_PropofolIV_50") then {"ACME_Propofol"} else {"Saline"};',block)
    block=re.sub(r'private _nominal = [^;]+;', 'private _nominal = if (_carrier == "ACME_Propofol") then {50} else {100};',block)
    from test_b230_prepared_infusion_transaction import adapted
    execute(owner_setup()+r'''
        private _plainSet=+_set;private _plainPrepared=+_prepared;
    '''+BOTTLE+r'''
        _set set [0,"prop"];_prepared set [0,"prop"];_prepared set [15,"prop"];
        _medic setVariable ["ACME_preparedIVSets",[_plainSet,_set]];
        private _preparedEntries=[_plainPrepared,_prepared];
        _medic setVariable ["ACME_infusion_PreparedBags",_preparedEntries];
        private _targetPatient=_patient;private _targetBodyPart="leftarm";private _flIV=true;private _flSite=0;
    '''+f'private _selectingPiggyback={str(piggyback).lower()};'+adapted(block)+r'''
        [count _shownPrepared==2 && {((_shownPrepared select 1) select 1)==1},"entering piggyback hid propofol or changed backing index"] call _check;
        [(_medic getVariable "ACME_infusion_PreparedBags") isEqualTo _preparedEntries,"filter consumed a prepared infusion"] call _check;
    ''')


def test_scope_preserves_ace_handlers_original_art_and_existing_site_flags():
    paths=subprocess.check_output(['git','diff','--name-only',BASE,'4944aaa6bae41fb06a4576c925805d657d386294','--','addons/gui','addons/circulation','addons/acm_extended/ui/iv'],cwd=ROOT,text=True).splitlines()
    dialog='addons/circulation/TransfusionMenu_Dialog.hpp'
    assert paths==[dialog]
    current=subprocess.check_output(['git','show','4944aaa6bae41fb06a4576c925805d657d386294:'+dialog],cwd=ROOT,text=True).replace('w = QUOTE(ACM_UI_CANVAS_W * 0.102);','w = QUOTE(ACM_TRANSFUSION_LEFT_W);',1)
    assert current==subprocess.check_output(['git','show',BASE+':'+dialog],cwd=ROOT,text=True)
    for name in ['updateTransfusionAccessHotspots','transfusionTagLeader','transfusionTagRect','reactMedicalMessage','reactMedicalValid']:
        path='addons/acm_extended/functions/fn_'+name+'.sqf'
        assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
