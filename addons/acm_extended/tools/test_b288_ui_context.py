"""Execute captured ventilator UI custody and stale-input rejection.

Native display/object/item-count/distance reads are explicit boundaries. The
production context predicate, initial capture, and action handlers execute;
these checks do not certify native Arma rendering or event dispatch.
"""
import re

import pytest

from test_menu_death_lifecycle import adapt, execute, read


INPUTS = (
    "ventPanelActivateSel", "ventPanelKnob", "ventPanelLiveEdit",
    "ventPanelNavClick", "ventPanelListClick", "ventPanelFieldClick",
    "ventPanelStripClick", "ventFlip", "ventManualBreath", "ventPowerOff",
    "ventAlarmSilence", "ventHoldTick",
)


def production(name):
    text = read(name).replace("disableSerialization;", "")
    if name == "ventRecoveryNear":
        text = text.replace("objectParent _medic", "_providerVehicle").replace("objectParent _patient", "_patientVehicle").replace("(_medic distance _patient)", "_reach")
    text = re.sub(r'^#define[^\n]*$', '', text, flags=re.M)
    # Config constants are compile-time definitions, independent of UI custody.
    for key, value in {
        "REV_TEX": '"reverse.paa"', "FRONT_TEX": '"front.paa"',
        "BATT_X0": "0.4697", "BATT_X1": "0.8975", "BATT_Y0": "0.5127", "BATT_Y1": "0.6309",
        "PWR_X0": "0.7588", "PWR_X1": "0.8408", "PWR_Y0": "0.4023", "PWR_Y1": "0.4844", "SWAP_SECS": "4.375",
    }.items():
        text = re.sub(r'\b' + key + r'\b', value, text)
    text = re.sub(r'playSound "[^"]*";', '', text)
    text = text.replace("alive _provider", '(_provider getVariable ["fixtureAlive",true])')
    text = text.replace("local _provider", '(_provider getVariable ["fixtureLocal",true])')
    return adapt(text)


def setup(self_panel=False):
    return r'''
        private _panel=parsingNamespace;
        private _controlled=_medic;
        private _nativeCount=1;
        private _reach=1;
        private _providerVehicle=objNull;
        private _patientVehicle=objNull;
        ACME_fnc_controlledProvider={_controlled};
        ACME_fnc_clinicalEpoch={(_this select 0) getVariable ["fixtureEpoch",7]};
        ace_common_fnc_getCountOfItem={_nativeCount};
        ACME_fnc_ventPanelRefresh={};
        ACME_fnc_ventPanelLiveRefresh={};
        ACME_fnc_ventPanelListRefresh={};
        _medic setVariable ["fixtureAlive",true];
        _medic setVariable ["fixtureLocal",true];
        _medic setVariable ["ACME_equipmentKitEpoch",2];
        _patient setVariable ["ACME_vent_onPatient",true];
        _patient setVariable ["ACME_vent_custodyId","vent-A"];
        _patient setVariable ["ACME_vent_bpm",12];
        uiNamespace setVariable ["ACME_vent_dlg",_panel];
        uiNamespace setVariable ["ACME_vent_target",_patient];
        _panel setVariable ["ACME_vent_viewer",_medic];
    ''' + ('uiNamespace setVariable ["ACME_vent_target",_medic];' if self_panel else '') + r'''
        private _capture={
            private _target=uiNamespace getVariable "ACME_vent_target";
            _panel setVariable ["ACME_vent_context",[_medic,_target,[_target]call ACME_fnc_clinicalEpoch,
                _target getVariable ["ACME_vent_custodyId",""],_medic getVariable ["ACME_equipmentKitEpoch",0]]];
        };
        call _capture;
    ''' + 'ACME_fnc_ventRecoveryNear={' + production('ventRecoveryNear').replace(
        'objectParent _medic', '_providerVehicle').replace('objectParent _patient', '_patientVehicle').replace(
        '(_medic distance _patient)', '_reach') + '};' + \
        'ACME_fnc_ventPanelContext={' + production('ventPanelContext') + '};'


@pytest.mark.parametrize("self_panel", [False, True])
def test_current_captured_device_allows_normal_and_dead_patient_panel(self_panel):
    execute(setup(self_panel) + r'''
        [call ACME_fnc_ventPanelContext,"current panel refused"]call _check;
        _patientAlive=false;
        [call ACME_fnc_ventPanelContext,"dead patient made attached device inaccessible"]call _check;
    ''')


INVALIDATIONS = {
    "provider_switch": '_controlled=missionNamespace;',
    "provider_dead": '_medic setVariable ["fixtureAlive",false];',
    "provider_remote": '_medic setVariable ["fixtureLocal",false];',
    "provider_frozen": '_medic setVariable ["ACME_persistenceFrozen",true];',
    "patient_frozen": '_patient setVariable ["ACME_persistenceFrozen",true];',
    "provider_unconscious": '_medic setVariable ["ACE_isUnconscious",true];',
    "patient_switch": 'uiNamespace setVariable ["ACME_vent_target",missionNamespace];',
    "clinical_reset": '_patient setVariable ["fixtureEpoch",8];',
    "device_replaced": '_patient setVariable ["ACME_vent_custodyId","vent-B"];',
    "device_removed": '_patient setVariable ["ACME_vent_onPatient",false];',
    "recovery_started": '_patient setVariable ["ACME_vent_recovering",true];',
    "out_of_reach": '_reach=6;',
    "display_closed": 'uiNamespace setVariable ["ACME_vent_dlg",objNull];',
    "missing_capture": '_panel setVariable ["ACME_vent_context",[]];',
}


@pytest.mark.parametrize("cause", list(INVALIDATIONS))
def test_context_rejects_replaced_or_unreachable_device(cause):
    execute(setup() + INVALIDATIONS[cause] + '[!(call ACME_fnc_ventPanelContext),"stale panel authorized"]call _check;')


@pytest.mark.parametrize("change", [
    '_nativeCount=0;', '_medic setVariable ["ACME_equipmentKitEpoch",3];',
])
def test_self_preset_requires_original_kit_and_physical_ventilator(change):
    execute(setup(True) + change + '[!(call ACME_fnc_ventPanelContext),"phantom carried device authorized"]call _check;')


def test_same_vehicle_allows_distant_cabin_seats_without_stopping_device():
    execute(setup() + r'''
        _reach=25;_providerVehicle=missionNamespace;_patientVehicle=missionNamespace;
        [call ACME_fnc_ventPanelContext,"same aircraft cabin refused"]call _check;
        _providerVehicle=objNull;
        [!(call ACME_fnc_ventPanelContext),"outside remote operator authorized"]call _check;
        [_patient getVariable ["ACME_vent_onPatient",false],"range check detached device"]call _check;
    ''')


@pytest.mark.parametrize("name", INPUTS)
def test_actual_input_handlers_reject_before_sound_selection_or_patient_write(name):
    # The full checked-out callback compiles and runs. Its invalid context must
    # return before native controls and clinical writers can be reached.
    execute(setup() + r'''
        _patient setVariable ["ACME_vent_custodyId","vent-B"];
        uiNamespace setVariable ["ACME_vent_selIdx",0];
        uiNamespace setVariable ["ACME_vent_bpm",12];
        uiNamespace setVariable ["ACME_vent_powered",true];
        uiNamespace setVariable ["ACME_vent_flipped",false];
        private _called=false;
        private _predicate=ACME_fnc_ventPanelContext;
        ACME_fnc_ventPanelContext={_called=true;call _predicate};
    ''' + 'private _input={' + production(name) + '};[1]call _input;' + r'''
        [_called,"input bypassed captured-context predicate"]call _check;
        [(_patient getVariable ["ACME_vent_bpm",-1])==12,"stale input wrote settings"]call _check;
        [count _events==0,"stale input sent owner mutation"]call _check;
        [(uiNamespace getVariable ["ACME_vent_selIdx",-1])==0,"stale input moved selection"]call _check;
    ''')


def test_onload_captures_target_epoch_custody_and_kit_without_aliasing_later_selection():
    execute(setup() + 'private _init={' + production('ventPanelInit').split('private _oldPFH',1)[0] + '};call _init;' + r'''
        [(_panel getVariable "ACME_vent_context")isEqualTo[_medic,_patient,7,"vent-A",2],"onLoad did not capture device episode"]call _check;
        _patient setVariable ["ACME_vent_custodyId","vent-B"];
        [!(call ACME_fnc_ventPanelContext),"capture followed replacement device"]call _check;
    ''')


@pytest.mark.parametrize('field,index', [('bpm',0),('vt',1)])
def test_field_input_keeps_unified_dial_index_on_exact_selected_value(field,index):
    execute(setup() + r'''
        uiNamespace setVariable ["ACME_vent_selIdx",5];
        uiNamespace setVariable ["ACME_vent_sel","none"];
        uiNamespace setVariable ["ACME_vent_editing",false];
        missionNamespace setVariable ["ACME_vent_simpleMode",false];
    ''' + 'private _field={' + production('ventPanelFieldClick') + '};' + f'["{field}"]call _field;' +
        f'[(uiNamespace getVariable ["ACME_vent_selIdx",-1])=={index},"field input left dial on another value"]call _check;')


@pytest.mark.parametrize('row', [-1, .5, 6])
def test_list_rejects_out_of_range_or_nonintegral_row_before_selection(row):
    execute(setup() + r'''
        uiNamespace setVariable ["ACME_vent_listCount",6];
        uiNamespace setVariable ["ACME_vent_selIdx",2];
    ''' + 'private _rowInput={' + production('ventPanelListClick').replace('finite _row','true') + '};' +
        f'[{row}]call _rowInput;' + '[(uiNamespace getVariable "ACME_vent_selIdx")==2,"invalid row changed selection"]call _check;')


def iv_setup():
    helper = read('ivInteractionValid').replace('local _medic','_providerLocal')
    return setup() + r'''
        private _providerLocal=true;
        uiNamespace setVariable ["ACME_IV_Medic",_medic];
        uiNamespace setVariable ["ACME_IV_Patient",_patient];
        uiNamespace setVariable ["ACME_IV_Session",[_patient,7,1]];
        ACME_fnc_patientInteractionDistance={_reach};
    ''' + 'ACME_fnc_ivInteractionValid={' + adapt(helper) + '};' + \
        'ACME_fnc_ivUiValid={' + adapt(read('ivUiValid')) + '};'


@pytest.mark.parametrize('change', [
    '_reach=4;', '_controlled=missionNamespace;', '_alive=false;',
    '_providerLocal=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_medic setVariable ["ACME_persistenceFrozen",true];', '_patient setVariable ["ACME_persistenceFrozen",true];',
])
def test_iv_interaction_rejects_stale_clinician_while_captured_teardown_keeps_its_session(change):
    execute(iv_setup() + r'''
        [[]call ACME_fnc_ivUiValid,"valid interactive IV context refused"]call _check;
        private _saved=+ (uiNamespace getVariable "ACME_IV_Session");
    ''' + change + r'''
        [!([]call ACME_fnc_ivUiValid),"stale clinician retained IV input"]call _check;
        [[_saved]call ACME_fnc_ivUiValid,"cancelled input lost teardown identity"]call _check;
    ''')


def test_iv_interaction_keeps_dead_patient_supported():
    execute(iv_setup() + '_patientAlive=false;[[]call ACME_fnc_ivUiValid,"dead patient IV access refused"]call _check;')


@pytest.mark.parametrize('move_after_launch', [False, True])
def test_iv_launch_refuses_distant_limb_and_releases_only_its_pending_ecg_lease(move_after_launch):
    from test_pr6_iv_launch_lifecycle import setup as launch_setup
    execute(launch_setup() + 'ACME_fnc_ivInteractionValid={' + adapt(read('ivInteractionValid')) + '};' +
            ('' if move_after_launch else '_distance=9;') + 'call _launch;' +
            ('_distance=9;' if move_after_launch else '') + r'''
        call _frame;call _frame;
        [count _created==0,"distant limb opened IV display"]call _check;
        [(uiNamespace getVariable ["ACME_IV_PendingLaunch",[]])isEqualTo[],"unreachable launch retained pending ownership"]call _check;
    ''' + f'[count _leases=={2 if move_after_launch else 0},"unreachable launch leaked or invented ECG lease"]call _check;' +
        (r'''[((_leases select 0)select 2) && {!((_leases select 1)select 2)},"cancelled launch did not release captured ECG lease"]call _check;''' if move_after_launch else ''))


@pytest.mark.parametrize('change', [
    '', '_patient setVariable ["fixtureEpoch",8];',
    '_patient setVariable ["ACME_vent_custodyId","vent-B"];',
    '_patient setVariable ["ACME_vent_recovering",true];',
    '_reach=6;', '_controlled=missionNamespace;',
    '_medic setVariable ["ACE_isUnconscious",true];',
])
def test_delayed_vent_panel_launch_cannot_capture_a_replacement_device(change):
    text=read('ventPanelOpen')
    start=text.rindex('[{')+2
    body=text[start:text.index('}, [_serial',start)]
    body=body.replace('createDialog "ACME_Ventilator_Dialog";', '_created=_created+1;')
    execute(setup() + r'''
        private _created=0;
        uiNamespace setVariable ["ACME_vent_openSerial",1];
        uiNamespace setVariable ["ACME_vent_openPending",true];
        uiNamespace setVariable ["ACME_vent_dlg",objNull];
    ''' + 'private _launch={' + adapt(body) + '};' + change +
        '[1,_medic,_patient,false,7,"vent-A",2]call _launch;' +
        f'[_created=={0 if change else 1},"delayed launch adopted wrong provider/device/reach"]call _check;' +
        '[!(uiNamespace getVariable ["ACME_vent_openPending",true]),"cancelled launch kept panel locked"]call _check;')


def test_live_vent_callback_rechecks_procedure_tier_before_next_panel_tick():
    execute(setup() + r'''
        ACME_fnc_procedureAllowed={false};
        [!(call ACME_fnc_ventPanelContext),"changed skill policy allowed stale panel input"]call _check;
    ''')


@pytest.mark.parametrize('simple', [False, True])
def test_open_vent_readout_follows_current_device_settings_instead_of_open_time_cache(simple):
    prefix=production('ventPanelRefresh').split('private _sel',1)[0]
    execute(setup() + f'missionNamespace setVariable ["ACME_vent_simpleMode",{str(simple).lower()}];' + r'''
        uiNamespace setVariable ["ACME_vent_bpm",12];
        uiNamespace setVariable ["ACME_vent_vt",500];
        _patient setVariable ["ACME_vent_bpm",30];
        _patient setVariable ["ACME_vent_vt",900];
        ACME_fnc_ventEffectiveSettings={[true,"SIMV VC PS",16,700]};
    ''' + 'private _paint={' + prefix + '[_bpm,_vt]};private _shown=call _paint;' +
        f'[_shown isEqualTo [{16 if simple else 30},{700 if simple else 900}],"open panel kept stale set values"]call _check;' +
        '[(uiNamespace getVariable "ACME_vent_bpm")==(_shown select 0) && {(uiNamespace getVariable "ACME_vent_vt")==(_shown select 1)},"dial cache did not follow displayed device settings"]call _check;')


@pytest.mark.parametrize('key,row,mode,current,expected',[
    ('bpm',0,'SIMV VC PS',30,31),
    ('vt',1,'SIMV VC PS',900,910),
    ('pinsp',1,'SIMV PC',35,36),
])
def test_dial_edit_uses_new_device_value_before_display_refresh(key,row,mode,current,expected):
    execute(setup() + r'''
        missionNamespace setVariable ["ACME_vent_simpleMode",false];
        uiNamespace setVariable ["ACME_vent_bpm",12];
        uiNamespace setVariable ["ACME_vent_vt",500];
        uiNamespace setVariable ["ACME_vent_pinsp",20];
    ''' + f'uiNamespace setVariable ["ACME_vent_selIdx",{row}];_patient setVariable ["ACME_vent_mode","{mode}"];_patient setVariable ["ACME_vent_{key}",{current}];' +
        'private _edit={' + production('ventPanelLiveEdit') + '};[1]call _edit;' +
        f'[(_patient getVariable ["ACME_vent_{key}",-1])=={expected},"dial overwrote current device value from stale cache"]call _check;')


@pytest.mark.parametrize('closed,change,expected',[
    (True,'_reach=6;',1), (False,'_reach=6;',0),
    (True,'_controlled=missionNamespace;',1),
    (True,'_patient setVariable ["fixtureEpoch",8];',0),
    (True,'_patient setVariable ["ACME_persistenceFrozen",true];',0),
])
def test_unload_saves_its_unfinished_iv_work_without_reauthorizing_interactive_input(closed,change,expected):
    prefix=production('ivMinigameSaveState').split('private _bp',1)[0]
    execute(iv_setup() + r'''
        private _saves=0;
        uiNamespace setVariable ["ACME_IV_DLG",_panel];
        _panel setVariable ["ACME_IV_Session",[_patient,7,1]];
    ''' + f'_panel setVariable ["ACME_IV_Closed",{str(closed).lower()}];' + change +
        'private _save={'+prefix+'_saves=_saves+1;};[]call _save;' +
        f'[_saves=={expected},"teardown lost its saved work or wrote a replacement/frozen episode"]call _check;')
