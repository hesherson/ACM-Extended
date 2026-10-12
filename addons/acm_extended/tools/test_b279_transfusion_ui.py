"""Execute B279 controls, physical graduation data, and owner flow actions in SQF-VM.

Drawing/config lookup is an engine fixture boundary. The production view model,
actual action entry points, three-stage Y recipe, and owner mutations execute.
Arma pointer acceptance remains a separate in-game check.
"""
import re
import subprocess

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read
from test_b156_procedure_supplies import primitives
from test_b274_transfusion_preparation import stage_setup
from test_b278_transfusion_geometry import renderer_setup, renderer_source
from test_b230_prepared_infusion_transaction import setup as mixture_setup

BASELINE = "e9eb266"


def flow_setup(source=None):
    source = source or read('transfusionFlowToggleCommit')
    native = (ROOT / 'addons/circulation/functions/fnc_TransfusionMenu_ToggleIVFlow.sqf').read_text()
    return r'''
        private _commands=[];private _publications=[];private _validAccess=true;
        ACME_infusion_bodyParts=["head","body","leftarm","rightarm","leftleg","rightleg"];
        ACME_fnc_clinicalEpoch={4};ACME_fnc_transfusionAccessValid={_validAccess};
        ACM_circulation_fnc_hasIV={_validAccess};ACM_circulation_fnc_hasIO={_validAccess};
        ACME_fnc_clinicalNotice={};ace_common_fnc_displayTextStructured={};
        ACM_circulation_fnc_setRuntimeState={params ["_p","_changes"];{
            _x params ["_key","_value"];private _name=["ACM_circulation_FluidBagsFlow_IO","ACM_circulation_FluidBagsFlow_IV"] select (_key=="fluidBagsFlowIV");
            _p setVariable [_name,_value];_publications pushBack [_key,+_value];
        }forEach _changes;};
        ACM_circulation_TransfusionMenu_Target=_patient;
        ACM_circulation_TransfusionMenu_Selected_BodyPart="leftarm";
        ACM_circulation_TransfusionMenu_Selected_AccessSite=1;
        ACM_circulation_TransfusionMenu_SelectIV=true;
    ''' + 'ACME_fnc_transfusionFlowToggleCommit={' + primitives(adapt(source)) + '};' + r'''
        ACME_fnc_ownerDispatch={_commands pushBack _this;(_this select 2) call ACME_fnc_transfusionFlowToggleCommit;};
    ''' + 'ACM_circulation_fnc_TransfusionMenu_ToggleIVFlow={' + primitives(adapt(native,'circulation')) + '};'


@pytest.mark.parametrize('iv,initial', [(True,'[]'),(True,'[[0,1,0],[1,0,1],[]]'),(False,'[]'),(False,'[0,1]')])
def test_native_stop_then_start_materializes_missing_flow_without_losing_existing_sites(iv,initial):
    var = 'ACM_circulation_FluidBagsFlow_' + ('IV' if iv else 'IO')
    read_value = '(_flow select 2) select 1' if iv else '_flow select 2'
    execute(flow_setup() + f'''
        ACM_circulation_TransfusionMenu_SelectIV={str(iv).lower()};
        _patient setVariable ["{var}",{initial}];
        []call ACM_circulation_fnc_TransfusionMenu_ToggleIVFlow;
        private _flow=_patient getVariable "{var}";
        [{read_value}==0,"Stop silently failed for a valid access with missing flow row"]call _check;
        [count _commands==1 && {{count _publications==1}},"native button failed to dispatch exactly one owner mutation"]call _check;
        []call ACM_circulation_fnc_TransfusionMenu_ToggleIVFlow;
        _flow=_patient getVariable "{var}";
        [{read_value}==1 && {{count _commands==2}},"Start did not reopen the same exact site"]call _check;
        if ({str(iv).lower()} && {{count {initial}>0}}) then {{[(_flow select 0) isEqualTo [0,1,0] && {{(_flow select 1) isEqualTo [1,0,1]}},"repair changed another existing IV site"]call _check;}};
    ''')


def test_baseline_reproduces_valid_access_stop_noop_when_flow_state_is_missing():
    previous = subprocess.check_output(['git','show',f'{BASELINE}:addons/acm_extended/functions/fn_transfusionFlowToggleCommit.sqf'],cwd=ROOT,text=True)
    execute(flow_setup(previous) + r'''
        private _accepted=[_patient,"leftarm",true,1,4,_medic]call ACME_fnc_transfusionFlowToggleCommit;
        [_accepted && {_publications isEqualTo []},"baseline no longer reproduces the silent valid-access failure"]call _check;
    ''')


@pytest.mark.parametrize('change', ['_validAccess=false;','ACM_circulation_TransfusionMenu_Selected_BodyPart="missing";'])
def test_invalid_stop_target_never_publishes_a_flow_change(change):
    execute(flow_setup() + change + '[]call ACM_circulation_fnc_TransfusionMenu_ToggleIVFlow;[_publications isEqualTo [],"unavailable access mutated flow"]call _check;')


def test_expired_owner_epoch_does_not_toggle_the_successor_access():
    execute(flow_setup() + 'private _r=[_patient,"leftarm",true,1,3,_medic]call ACME_fnc_transfusionFlowToggleCommit;[!_r && {_publications isEqualTo []},"stale clamp command reached the next clinical epoch"]call _check;')


@pytest.mark.parametrize('reopen',[False,True])
def test_actual_y_button_action_keeps_three_steps_with_no_patient_access(reopen):
    config = (ROOT/'addons/acm_extended/config.cpp').read_text()
    button = config.split('class ACME_YTubingButton:',1)[1].split('};',1)[0]
    action = re.search(r'action = "([^"]+)";',button).group(1)
    execute(stage_setup() + r'''
        ACM_circulation_TransfusionMenu_Selected_AccessSite=-1;
        _rowData=["ACM_BloodBag_ON_500|BloodIV_ON_500","ACM_SalineBag_500|SalineIV_500"];
        _medic setVariable ["fixtureStock",["ACM_BloodBag_ON_500","ACM_SalineBag_500","ACME_YTubing"]];
    ''' + action + ';' + r'''
        [(missionNamespace getVariable "ACME_yPending")=="ACM_BloodBag_ON_500" && {count _waits==0},"first native click skipped or failed the blood stage"]call _check;
    ''' + ('_display=profileNamespace;' if reopen else '') + '_selection=1;' + action + ';' + r'''
        [(missionNamespace getVariable "ACME_yPendingSaline")=="ACM_SalineBag_500" && {count _waits==0},"saline click skipped or failed the pairing stage"]call _check;
    ''' + action + ';' + r'''
        [count _waits==1,"third click did not schedule the physical Y assembly"]call _check;
        (_waits select 0 select 1)call (_waits select 0 select 0);
        [count (_medic getVariable ["ACME_preparedIVSets",[]])==1 && {(_medic getVariable "fixtureStock") isEqualTo []},"three-stage action did not produce exactly one complete set"]call _check;
        [uiNamespace getVariable ["ACME_preparedListMode",false],"completed set stayed invisible in the inventory pane"]call _check;
        [str (_patient getVariable "ACM_circulation_IV_Bags")==_initialBagText,"Y preparation altered active patient bags"]call _check;
    ''')


@pytest.mark.parametrize('volume,values',[(50,[0,10,20,30,40,50]),(100,[0,20,40,60,80,100]),(250,[0,50,100,150,200,250]),(500,[0,100,200,300,400,500]),(1000,list(range(0,1001,100)))])
def test_production_bag_graduations_follow_printed_capacity(volume,values):
    execute('ACME_fnc_transfusionGraduations={' + adapt(read('transfusionGraduations').replace('finite _volume','true')) + '};' + f'private _marks=[{volume}]call ACME_fnc_transfusionGraduations;[(_marks apply {{_x select 1}})isEqualTo{values},"wrong printed graduation interval"]call _check;'.replace("'",'"'))


def data_setup():
    source=read('transfusionCardData')
    for before,after in {'_list lbText _row':'"Saline"','_list lbColor _row':'[1,1,1,1]','_list lbPictureRight _row':'"vial.paa"','_list lbPicture _row':'"bag.paa"','_list lbValue _row':'0','ctrlIDC _list':'86004'}.items():
        source=source.replace(before,after)
    return r'''
        private _mapDefault={params["_m","_a"];_a params["_k","_d"];if(_k in _m)then{_m get _k}else{_d}};
        private _bag=["Saline",125,1,0,true,-1,270,-1,"bag",250];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray [["leftarm",[_bag]]]];
        private _med=[];_med set [11,"Calcium"];_med set [13,1000];_med set [14,150];_med set [23,"bag"];
        _patient setVariable ["ACME_infusion_BagMedications",[_med]];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Target",_patient];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart","leftarm"];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",0];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_SelectIV",true];
        missionNamespace setVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags",[["Saline",125,1,0,true,-1,270,-1,0,"bag"]]];
        ACME_fnc_transfusionBagPresentation={["Saline (125 mL)",[1,1,1,1],"LW Quantum · Inline","",true]};
        ACME_fnc_infusionTitle={"Calcium"};ACME_fnc_infusionName={"Calcium"};ACME_fnc_formatDose={str(_this select 1)};
        ACME_fnc_isYLineAccess={false};
    ''' + 'ACME_fnc_transfusionCardData={' + primitives(adapt(source)) + '};'


def test_card_keeps_original_dose_and_physical_capacity_after_diluent_and_delivery():
    execute(data_setup()+r'''
        private _data=[missionNamespace,0]call ACME_fnc_transfusionCardData;
        [(_data select 1)=="125 mL · Calcium 1000 added","card disclosed remaining drug instead of initially added dose"]call _check;
        [(_data select 8)==250 && {(_data select 7)==.5},"added diluent changed manufacturer graduation scale"]call _check;
        _med set[14,5];_bag set[1,50];
        _data=[missionNamespace,0]call ACME_fnc_transfusionCardData;
        [(_data select 1)=="50 mL · Calcium 1000 added" && {(_data select 8)==250},"delivery changed the fixed medication label or capacity"]call _check;
    ''')


def test_renderer_shares_tracks_and_aligns_status_and_thermal_without_overlap():
    setup=renderer_setup().replace('"Running","",','"Running","LW Quantum · Inline",').replace('"native-vial.paa",.5]','"native-vial.paa",.5,250]')
    # Engine viewport sizes use real canvas fractions (the legacy fixture uses unit canvas).
    setup=setup.replace('[.1,.2,.212,.21]','[.1,.2,.212*1.7777778,.21]').replace('[.1,.55,.212,.187]','[.1,.55,.212*1.7777778,.187]').replace('[.67,.279,.202,.235]','[.67,.279,.202*1.7777778,.235]')
    execute(setup+r'''
        [missionNamespace]call ACME_fnc_updateTransfusionCards;
        private _track=_controlValues get "[86500,16]:position";
        private _right=_controlValues get "[86520,16]:position";
        [abs((_track select 2)-(_right select 2))<.00001,"left and right fluid scales use different physical widths"]call _check;
        private _viewport=_positions get 86004;private _rail=_controlValues get "86610:position";
        [(_rail select 0)+(_rail select 2)<=(_viewport select 0)+(_viewport select 2)+.00001,"centering a card moved its rail outside the native viewport"]call _check;
        private _name=_controlValues get "[86500,10]:position";
        private _status=_controlValues get "[86500,12]:position";
        private _thermal=_controlValues get "[86500,13]:position";
        [(_status select 0)==(_name select 0),"Running floated left of the title/detail column"]call _check;
        [(_status select 1)+(_status select 3)<=(_thermal select 1)+.00001,"status and LW label overlap"]call _check;
        [abs((_thermal select 0)+(_thermal select 2)-((_track select 0)+(_track select 2)))<.00001,"LW label does not end with its scale"]call _check;
        [(_controlValues get "[86500,34]:text")=="250","physical scale marks are absent"]call _check;
    ''')


def hidden_inventory_cards():
    """Only native UI handles/selection writes are replaced; identity resolution executes intact."""
    source=read('transfusionCardSelect')
    source=source.replace('ctrlParent _hit','_display').replace('findDisplay 86200','objNull').replace('findDisplay 84000','objNull')
    source=source.replace('_display displayCtrl _idc','_rightFixture').replace('lbCurSel _list','_selection').replace('lbSize _list','count _rowData')
    source=source.replace('_list lbSetCurSel _row;','_selection=_row;')
    identity=read('transfusionCardIdentity').replace('ctrlIDC _list','86005').replace('lbSize _list','count _rowData').replace('_list lbValue _row','0').replace('_list lbData _row','(_rowData select _row)')
    resolver=read('transfusionCardResolve').replace('lbSize _list','count _rowData')
    return r'''
        private _hit=uiNamespace;
        _hit setVariable ["ACME_txListIDC",86005];_hit setVariable ["ACME_txCapacity",3];
        _hit setVariable ["ACME_txPatient",_patient];
        ACME_fnc_updateTransfusionCards={};
    ''' + 'ACME_fnc_transfusionCardIdentity={' + primitives(adapt(identity)) + '};' + \
        'ACME_fnc_transfusionCardResolve={' + primitives(adapt(resolver)) + '};' + \
        'ACME_fnc_transfusionCardSelect={' + primitives(adapt(source)) + '};'


def test_hidden_inventory_card_selection_survives_reorder_before_all_three_y_clicks():
    execute(stage_setup()+hidden_inventory_cards()+r'''
        private _paints=0;ACME_fnc_updateTransfusionControls={_paints=_paints+1;};
        ACM_circulation_TransfusionMenu_Selected_AccessSite=-1;
        _medic setVariable ["fixtureStock",["ACM_BloodBag_ON_500","ACM_SalineBag_500","ACME_YTubing"]];
        private _blood="ACM_BloodBag_ON_500|BloodIV_ON_500";private _saline="ACM_SalineBag_500|SalineIV_500";
        _rowData=[_blood,_saline];_selection=-1;
        _hit setVariable ["ACME_txIdentity",["inventory",_blood]];
        [_hit]call ACME_fnc_transfusionCardSelect;
        [_selection==0,"card did not write the hidden native blood list selection"]call _check;
        []call ACME_fnc_transfusionYTubing;
        [_paints==2,"first Y stage did not immediately repaint its saline picker/action"]call _check;
        // Reopened presentation and reordered native inventory must resolve the same stored item identity.
        _display=profileNamespace;_rowData=[_saline,_blood];_selection=-1;
        _hit setVariable ["ACME_txIdentity",["inventory",_saline]];
        [_hit]call ACME_fnc_transfusionCardSelect;
        [_selection==0,"reordered saline card selected a neighbouring blood row"]call _check;
        []call ACME_fnc_transfusionYTubing;
        [_paints==4,"paired saline did not immediately reveal the third build step"]call _check;
        []call ACME_fnc_transfusionYTubing;
        [count _waits==1,"hidden native selection never reached the third build click"]call _check;
        (_waits select 0 select 1)call (_waits select 0 select 0);
        private _set=(_medic getVariable ["ACME_preparedIVSets",[]])param[0,[]];
        [(_set param[1,""])=="ACM_BloodBag_ON_500" && {(_set param[3,""])=="ACM_SalineBag_500"},"card handoff assembled another component identity"]call _check;
        [(_medic getVariable "fixtureStock")isEqualTo[] && {uiNamespace getVariable ["ACME_preparedListMode",false]},"hidden-list build did not consume/open exactly one staged set"]call _check;
    ''')


def test_added_diluent_keeps_legacy_carrier_capacity_across_real_registration():
    execute(mixture_setup()+r'''
        private _bag=["Saline",250,1,0,true,-1,250,-1,"capacity-bag"];
        _patient setVariable ["ACM_circulation_IV_Bags",createHashMapFromArray[["leftarm",[_bag]]]];
        private _context=[_patient,"leftarm",0,"Saline",1,0,true,-1,250,-1,250];
        private _result=[_context,"CalciumChloride",1000,600,20,0,0,"dose1","capacity-bag",1,20]call ACME_fnc_infusionRegisterCore;
        [_result!="","real registration rejected the capacity fixture"]call _check;
        _bag=(_patient getVariable "ACM_circulation_IV_Bags" get "leftarm")select 0;
        [(_bag param[9,0])==250 && {(_bag select 6)==270},"first diluent addition replaced nominal carrier capacity"]call _check;
        _context set[8,270];_context set[10,270];
        _result=[_context,"CalciumChloride",500,600,20,0,0,"dose2","capacity-bag",1,10]call ACME_fnc_infusionRegisterCore;
        _bag=(_patient getVariable "ACM_circulation_IV_Bags" get "leftarm")select 0;
        [(_bag param[9,0])==250 && {(_bag select 6)==280},"repeat addition rescaled the manufacturer marks"]call _check;
    ''')


def test_active_bag_injection_tally_and_done_confirmation_show_added_dose():
    tally=read('infusionRefreshTally').replace('findDisplay 84000','missionNamespace').replace('_display displayCtrl 84361','uiNamespace').replace('_display displayCtrl 84362','objNull')
    tally=tally.replace('_ctrl ctrlSetStructuredText parseText (_lines joinString "<br/>");','_painted=_lines joinString "<br/>";')
    done=read('infusionDone');done=done[done.index('private _confirmedRows = [];'):done.index('private _return =')]
    execute(data_setup()+r'''
        private _context=[];_context set[0,"active"];_context set[1,_patient];_context set[21,"bag"];
        missionNamespace setVariable ["ACME_infusion_pendingContext",_context];
        private _painted="";private _confirmed="";
        ACME_fnc_clinicalNotice={_confirmed=_this select 1;};
        _med set[10,125];_med set[27,1];
    '''+primitives(adapt(tally))+primitives(adapt(done))+r'''
        [(_painted find "1000 added")>=0 && {(_painted find "150")<0},"drawer bag tally disclosed remaining medication"]call _check;
        [(_confirmed find "1000")>=0 && {(_confirmed find "150")<0},"Done confirmation disclosed remaining dose"]call _check;
    ''')


@pytest.mark.parametrize('width,height,canvas',[(1280,960,4/3),(1920,1080,16/9)])
def test_thousand_ml_endpoint_labels_remain_centered_separate_and_inside_card(width,height,canvas):
    setup=renderer_setup().replace('"native-vial.paa",.5]','"native-vial.paa",.5,1000]')
    setup=setup.replace('(1/1920)',f'(1/{width})').replace('(1/1080)',f'(1/{height})').replace('1.7777778',str(canvas))
    execute(setup+r'''
        [missionNamespace]call ACME_fnc_updateTransfusionCards;
        private _card=_controlValues get "86500:position";private _previousEnd=-1;
        for "_mark" from 0 to 10 do {
            private _label=_controlValues get format["%1:position",[86500,29+_mark]];
            private _tick=_controlValues get format["%1:position",[86500,18+_mark]];
            [abs((_label select 0)+(_label select 2)/2-((_tick select 0)+1/''' + str(width) + r'''/2))<.00001,"endpoint label left its actual printed tick"]call _check;
            [(_label select 0)>=0 && {(_label select 0)+(_label select 2)<=(_card select 2)+.00001},"endpoint label escaped the card's padding"]call _check;
            [(_label select 0)>=_previousEnd-.00001,"900 and 1000 or zero and next graduation labels overlap"]call _check;
            _previousEnd=(_label select 0)+(_label select 2);
        };
        [(_controlValues get "[86500,39]:text")=="1000","full bag endpoint is illegible/missing"]call _check;
    ''')
