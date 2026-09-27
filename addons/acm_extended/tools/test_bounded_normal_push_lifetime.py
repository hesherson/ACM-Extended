"""Execute normal-push callbacks and Unload with explicit UI/scheduler fixtures.

The medication handoff is recorded, not administered. No engine UI, dose kinetics,
real inventory/network transport or general stale-Unload behavior is simulated.
"""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute, ROOT
from test_historical_syringe_identity import function as identity_function
from test_historical_medication_rows import iteration_scopes

F = ROOT / 'addons/acm_extended/functions'


def source(name):
    text = (F / ('fn_' + name + '.sqf')).read_text()
    text = text.replace('findDisplay 84000', '_drawDisplay')
    text = re.sub(r'_(?:d|display) displayCtrl (_x|\d+)', r'\1', text)
    text = text.replace('_durCtrl getVariable ["ACME_SK_GhostActive",false]', '_ghost')
    text = text.replace('ctrlText _durCtrl', '_durationText')
    text = text.replace('ctrlPosition _bar', '(_positions get "84420")')
    text = text.replace('ctrlPosition _pl', '(_positions get "84422")')
    text = text.replace('_ctrl ctrlSetPosition [_x,_y,_w,_h];', '_writes pushBack [_x,_y,_w,_h]; _positions set [str _ctrl,[_x,_y,_w,_h]];')
    text = text.replace('_ctrl ctrlCommit 0;', '_commits pushBack _ctrl;')
    text = re.sub(r'_c ctrlEnable (true|false);', r'_enables pushBack [_c,\1];', text)
    text = re.sub(r'playSound ("[^"]*");', r'_sounds pushBack \1;', text)
    text = text.replace('_hcPushClose getOrDefault ["flowing",false]', '([_hcPushClose,"flowing",false] call _lookup)')
    text = text.replace('safeZoneH', '1')
    return adapt(iteration_scopes(text))


def setup():
    return '''
        private _lookup={params ["_map","_key","_default"]; if (_key in _map) then {_map get _key} else {_default}};
        private _drawDisplay=missionNamespace;
        // These push fixtures enter an already-injected draw display.
        uiNamespace setVariable ["ACME_SK_CloseEpoch",1];
        _drawDisplay setVariable ["ACME_SK_CloseEpoch",1];
        private _durationText=""; private _ghost=false;
        private _enables=[]; private _writes=[]; private _commits=[]; private _sounds=[];
        private _delivered=[]; private _hcStarts=0; private _hasAccess=true;
        private _refreshes=0;
        private _positions=createHashMapFromArray [["84420",[0.2,0.3,0.2,0.4]],["84422",[0.2,0.4,0.2,0.4]]];
        private _row=["Ketamine",10,2,"one",0,[["Ketamine",2]],"compoundB13","none","a","b","c","id-one"];
        private _other=["Propofol",5,1,"two",0,[],"","none","","","","id-two"];
        _medic setVariable ["ACME_narcStore",[_row,_other]];
        uiNamespace setVariable ["ACME_SK_Patient",_patient];
        uiNamespace setVariable ["ACME_SK_View","body"];
        uiNamespace setVariable ["ACME_SK_PendingInjection",["leftarm",1,"vascular"]];
        uiNamespace setVariable ["ACME_SK_SiteIdx",1];
        uiNamespace setVariable ["ACME_SK_Route","vascular"];
        uiNamespace setVariable ["ACME_SK_SelectedSyringeId","id-one"];
        uiNamespace setVariable ["ACME_SK_PushAnimPFH",-1];
        _drawDisplay setVariable ["ACME_SK_ReturnPatient",_patient];
        _drawDisplay setVariable ["ACME_SK_CarouselNativeRect",[0.2,0.3,0.2,0.4]];
        ACM_circulation_fnc_hasIV={_hasAccess}; ACM_circulation_fnc_hasIO={_hasAccess};
        ACME_fnc_medicationLineBloodBusy={false};
        ACME_fnc_skDynamicLayout={}; ACME_fnc_skCarouselRender={_refreshes=_refreshes+1;};
        ACME_fnc_skBuildHotspots={}; ACME_fnc_skBodyActionRender={};
        ACME_fnc_hardcorePushStart={_hcStarts=_hcStarts+1; true};
        ACME_fnc_skInjectSite={
            _delivered pushBack [ACE_player,uiNamespace getVariable ["ACME_SK_Patient",ACE_player],
                uiNamespace getVariable ["ACME_SK_SelectedSyringeId",""],+_this,
                uiNamespace getVariable ["ACME_SK_SiteIdx",-9],uiNamespace getVariable ["ACME_SK_Route",""]];
        };
        ACME_fnc_vialLeaseRelease={}; ACME_fnc_restorePausedFlow={}; ACME_fnc_restoreMedicationList={};
        ACME_fnc_reopenMedicalMenu={}; ACME_fnc_reopenTransfusion={};
        ACME_fnc_skCompoundCommit={}; ACME_fnc_skPendingTagCommit={};
        CBA_fnc_waitAndExecute={_waits pushBack +_this;};
        CBA_fnc_removePerFrameHandler={_removed pushBack (_this select 0);};
        private _runWait={private _w=_waits select _this; (_w select 1) call (_w select 0);};
        private _runAnim={private _h=_handlers select _this; [_h select 1,_this] call (_h select 0);};
    ''' + ''.join(identity_function(n) for n in ('narcStoreCommit','skStoreEnsureIds','skSelectedIndex','skSelectStored')) + ''.join(
        'ACME_fnc_'+n+'={'+source(n)+'};\n' for n in ('skBeginInjection','skConfirmInjection','skClose'))


@pytest.mark.parametrize('boundary', ['start','commit'])
@pytest.mark.parametrize('change', ['reopen','patient','provider','page','cancel','editor'])
def test_changed_context_never_hands_off_medication(boundary, change):
    edits = {
        'reopen':'_drawDisplay=parsingNamespace;',
        'patient':'uiNamespace setVariable ["ACME_SK_Patient",missionNamespace];',
        'provider':'ACE_player=profileNamespace;',
        'page':'uiNamespace setVariable ["ACME_SK_View","syringe"];',
        'cancel':'uiNamespace setVariable ["ACME_SK_InjectionBusy",false];',
        'editor':'uiNamespace setVariable ["ACME_SK_TagEditMode",true];',
    }
    execute(setup()+'''
        [call ACME_fnc_skConfirmInjection,"normal push did not start"] call _check;
    '''+('0 call _runWait;' if boundary=='commit' else '')+edits[change]+f'''
        {1 if boundary=='commit' else 0} call _runWait;
        [count _delivered==0,"stale push handed off medication"] call _check;
        [count _waits=={2 if boundary=='commit' else 1},"stale start scheduled a commit"] call _check;
    ''')


@pytest.mark.parametrize('boundary',['start','commit'])
@pytest.mark.parametrize('reopen',[False,True])
def test_old_callback_cannot_unlock_or_retarget_a_new_normal_push(boundary,reopen):
    execute(setup()+'''
        call ACME_fnc_skConfirmInjection;
    '''+('0 call _runWait;' if boundary=='commit' else '')+'''
        uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
    '''+('''
        _drawDisplay=parsingNamespace;
        // skInject also records the shown patient on every initialized replacement display.
        _drawDisplay setVariable ["ACME_SK_ReturnPatient",_patient];
        // The replacement is an injected display, with its own registration epoch.
        private _nextCloseEpoch=(uiNamespace getVariable ["ACME_SK_CloseEpoch",0])+1;
        uiNamespace setVariable ["ACME_SK_CloseEpoch",_nextCloseEpoch];
        _drawDisplay setVariable ["ACME_SK_CloseEpoch",_nextCloseEpoch];
    ''' if reopen else '')+'''
        uiNamespace setVariable ["ACME_SK_PendingInjection",["rightarm",2,"vascular"]];
        [call ACME_fnc_skConfirmInjection,"new push rejected"] call _check;
        private _newJob=+(uiNamespace getVariable ["ACME_SK_NormalPush",[]]);
        private _waitCount=count _waits;
    '''+f'{1 if boundary=="commit" else 0} call _runWait;'+'''
        [count _delivered==0,"old callback committed during new push"] call _check;
        [count _waits==_waitCount,"old callback restarted animation"] call _check;
        [uiNamespace getVariable ["ACME_SK_InjectionBusy",false],"old callback unlocked new push"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo ["rightarm",2,"vascular"],"old callback cleared new site"] call _check;
        [(uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo _newJob,"old callback retired new job"] call _check;
    ''')


@pytest.mark.parametrize('boundary',['start','commit'])
def test_old_normal_callback_leaves_persistent_hardcore_locks(boundary):
    execute(setup()+'''call ACME_fnc_skConfirmInjection;'''+('0 call _runWait;' if boundary=='commit' else '')+'''
        missionNamespace setVariable ["ACME_HCMedPushJob",createHashMapFromArray [["flowing",true]]];
    '''+f'{1 if boundary=="commit" else 0} call _runWait;'+'''
        [count _delivered==0,"normal callback committed over persistent flow"] call _check;
        [uiNamespace getVariable ["ACME_SK_InjectionBusy",false],"persistent injection lock cleared"] call _check;
        [uiNamespace getVariable ["ACME_SK_CarouselBusy",false],"persistent carousel lock cleared"] call _check;
    ''')


@pytest.mark.parametrize('boundary',['start','commit'])
def test_close_cancels_normal_push_and_frees_only_its_animation(boundary):
    execute(setup()+'''call ACME_fnc_skConfirmInjection;'''+('0 call _runWait;' if boundary=='commit' else '')+'''
        [_drawDisplay] call ACME_fnc_skClose;
        [!(uiNamespace getVariable ["ACME_SK_InjectionBusy",true]),"Unload left normal push locked"] call _check;
        [!(uiNamespace getVariable ["ACME_SK_CarouselBusy",true]),"Unload left carousel locked"] call _check;
        [(uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo [],"Unload retained job"] call _check;
    '''+f'{1 if boundary=="commit" else 0} call _runWait;'+'''
        [count _delivered==0,"closed push committed"] call _check;
    '''+('[0 in _removed,"Unload left its plunger PFH"] call _check;' if boundary=='commit' else ''))


def test_duplicate_completion_is_exactly_one_handoff_even_if_the_row_remains():
    execute(setup()+'''
        call ACME_fnc_skConfirmInjection; 0 call _runWait; 1 call _runWait; 1 call _runWait;
        [count _delivered==1,"duplicate completion handed off twice"] call _check;
    ''')


@pytest.mark.parametrize('route,site', [('vascular',1),('vascular',-1),('im',-1)])
@pytest.mark.parametrize('duration', ['', '30'])
def test_current_push_retains_duration_route_target_and_stable_id(route,site,duration):
    expected=3 if route=='im' or not duration else int(duration)
    execute(setup()+f'''
        _durationText="{duration}";
        uiNamespace setVariable ["ACME_SK_PendingInjection",["leftleg",{site},"{route}"]];
        [call ACME_fnc_skConfirmInjection,"current push rejected"] call _check;
        [count _delivered==0 && {{count _waits==1}},"medication handed off before animation"] call _check;
        [((_waits select 0) select 2)==0.14,"settle duration changed"] call _check;
        0 call _runWait;
        [count _delivered==0 && {{((_waits select 1) select 2)=={expected}}},"wrong push duration"] call _check;
        [_medic,[_other,_row]] call ACME_fnc_narcStoreCommit;
        1 call _runWait;
        [_delivered isEqualTo [[_medic,_patient,"id-one",["leftleg",{expected}],{site},"{route}"]],"handoff context changed"] call _check;
        [!(uiNamespace getVariable ["ACME_SK_InjectionBusy",true]),"completed push left lock"] call _check;
        [(_medic getVariable ["ACME_narcStore",[]]) isEqualTo [_other,_row],"callback changed syringe contents"] call _check;
    ''')


def test_return_patient_fallback_is_carried_into_authoritative_handoff():
    execute(setup()+'''
        uiNamespace setVariable ["ACME_SK_Patient",objNull];
        call ACME_fnc_skConfirmInjection; 0 call _runWait; 1 call _runWait;
        [count _delivered==1 && {((_delivered select 0) select 1) isEqualTo _patient},"fallback target lost before handoff"] call _check;
    ''')


@pytest.mark.parametrize('boundary',['start','commit'])
def test_missing_stable_record_aborts_without_selecting_a_replacement(boundary):
    execute(setup()+'''call ACME_fnc_skConfirmInjection;'''+('0 call _runWait;' if boundary=='commit' else '')+'''
        [_medic,[_other]] call ACME_fnc_narcStoreCommit;
    '''+f'{1 if boundary=="commit" else 0} call _runWait;'+'''
        [count _delivered==0,"missing syringe replaced during commit"] call _check;
        [!(uiNamespace getVariable ["ACME_SK_InjectionBusy",true]),"missing syringe left lock"] call _check;
    ''')


@pytest.mark.parametrize('kind',['new-job','closed','completed'])
def test_stale_plunger_retires_itself_without_clearing_a_newer_handle(kind):
    change={
        'new-job':'''uiNamespace setVariable ["ACME_SK_InjectionBusy",false]; call ACME_fnc_skConfirmInjection;''',
        'closed':'_drawDisplay=parsingNamespace;',
        'completed':'1 call _runWait;',
    }[kind]
    execute(setup()+'''call ACME_fnc_skConfirmInjection; 0 call _runWait;'''+change+'''
        uiNamespace setVariable ["ACME_SK_PushAnimPFH",99];
        _writes=[]; 0 call _runAnim;
        [0 in _removed && {count _writes==0},"stale plunger still animated"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1])==99,"stale plunger cleared newer handle"] call _check;
    ''')


def test_normal_plunger_smoothstep_and_end_cleanup_remain():
    execute(setup()+'''
        call ACME_fnc_skConfirmInjection; 0 call _runWait;
        _nowTime=11.5; 0 call _runAnim;
        [abs (((_writes select 0) select 1)-0.35)<0.00001,"midpoint changed"] call _check;
        _nowTime=13; 0 call _runAnim;
        [abs (((_writes select 1) select 1)-0.3)<0.00001,"empty endpoint changed"] call _check;
        [0 in _removed && {(uiNamespace getVariable ["ACME_SK_PushAnimPFH",0]) == -1},"normal PFH did not finish"] call _check;
    ''')


@pytest.mark.parametrize('route', ['vascular','im'])
def test_hardcore_vascular_delegation_and_im_normal_path_are_preserved(route):
    execute(setup()+f'''
        missionNamespace setVariable ["ACME_hcEff_medications",true];
        uiNamespace setVariable ["ACME_SK_PendingInjection",["leftarm",1,"{route}"]];
        call ACME_fnc_skConfirmInjection;
        [_hcStarts=={int(route!='im')} && {{count _waits=={int(route=='im')}}},"persistent/IM routing changed"] call _check;
    ''')


def test_unload_does_not_stop_a_persistent_push():
    execute(setup()+'''
        missionNamespace setVariable ["ACME_HCMedPushJob",createHashMapFromArray [["flowing",true]]];
        uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
        uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
        uiNamespace setVariable ["ACME_SK_PushAnimPFH",99];
        [_drawDisplay] call ACME_fnc_skClose;
        [uiNamespace getVariable ["ACME_SK_InjectionBusy",false],"Unload stopped persistent flow UI"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1])==99,"Unload retired persistent handle"] call _check;
    ''')
