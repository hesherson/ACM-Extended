"""Execute controlled-provider identity and captured native draw lifetimes.

ACE's public player resolver and native UI/cargo commands are explicit engine
boundaries. The production resolver, draw timers and receipt cleanup execute.
"""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute, read
from source_scan import lex, matching, split_args
from test_cpr_lifecycle import execute as cpr_execute
from test_bvm_startup import setup as bvm_setup
from test_b212_prone_providers import hang_setup


def resolver():
    source = read('controlledProvider').replace('hasInterface', '_interface')
    source = re.sub(r'\bplayer\b', '_avatar', source)
    return 'ACME_fnc_controlledProvider={' + adapt(source) + '};'


def setup():
    return r'''
    private _interface=true;
    private _avatar=missionNamespace;
    private _controlled=uiNamespace;
    ACE_player=_avatar;
    ace_common_fnc_player={_controlled};
    ''' + resolver()


@pytest.mark.parametrize('controlled', ['uiNamespace', 'profileNamespace', 'objNull'])
def test_public_resolver_uses_current_controlled_unit_instead_of_stale_ace_avatar(controlled):
    expected = '_avatar' if controlled == 'objNull' else controlled
    execute(setup() + f'_controlled={controlled};' +
            f'[(call ACME_fnc_controlledProvider) isEqualTo {expected},"wrong provider"] call _check;' +
            '[ACE_player isEqualTo _avatar,"resolver mutated ACE global"] call _check;')


def test_dedicated_interface_guard_does_not_consult_public_player_resolver():
    execute(setup() + r'''
    _interface=false;
    private _called=false;
    ace_common_fnc_player={_called=true;_controlled};
    [(call ACME_fnc_controlledProvider) isEqualTo objNull,"headless provider exists"] call _check;
    [!_called,"headless resolver read local player"] call _check;
    ''')


@pytest.mark.parametrize('remote', ['uiNamespace', 'objNull'])
def test_missing_ace_api_uses_bi_controlled_unit_and_null_falls_back_to_player(remote):
    expected = '_avatar' if remote == 'objNull' else remote
    execute(setup() + f'''
    ace_common_fnc_player=nil;
    missionNamespace setVariable ["bis_fnc_moduleRemoteControl_unit",{remote}];
    [(call ACME_fnc_controlledProvider) isEqualTo {expected},"fallback used stale identity"] call _check;
    ''')


def draw_setup():
    source = (ROOT / 'addons/circulation/functions/fnc_Syringe_Draw_Button.sqf').read_text()
    source = source.replace('findDisplay 84000', '_displayStub')
    source = re.sub(r'_display displayCtrl (?:_x|\d+)', 'objNull', source)
    source = source.replace('ctrlText _push', '"Push"').replace('ctrlText _draw', '"Draw"')
    source = re.sub(r'playSound "[^"]+";', '', source)
    source = re.sub(r'localize \(format \["STR_ACM_Circulation_Medication_%1", _medication\]\)', '"Ketamine"', source)
    source = source.replace('localize "STR_ACM_Circulation_Syringe_Drawn"', '"Drew %1"')
    source = source.replace('isNull (missionNamespace getVariable ["ACM_circulation_SyringeDraw_Target", objNull])',
                            '((missionNamespace getVariable ["ACM_circulation_SyringeDraw_Target", objNull]) isEqualTo objNull)')
    return setup() + r'''
    private _displayStub=parsingNamespace;
    private _prepared=[];private _injected=[];private _stores=[];
    ACM_circulation_SyringeDraw_Medic=_controlled;
    ACM_circulation_SyringeDraw_DrawnAmount=1.23;
    ACM_circulation_SyringeDraw_Size=3;
    ACM_circulation_SyringeDraw_Medication="Ketamine";
    ACM_circulation_SyringeDraw_Target=_patient;
    ACM_circulation_SyringeDraw_TargetPart="LeftArm";
    ACM_circulation_fnc_Syringe_PrepareFinish={_prepared pushBack +_this;true};
    ACM_circulation_fnc_Syringe_Inject={_injected pushBack +_this;};
    ACME_fnc_skPendingTagCommit={};
    ACME_fnc_skApplyPendingTag={_this select 0};
    ACME_fnc_skRefreshDrawn={};ACME_fnc_skAfterSaveOpenBody={};
    ACME_fnc_narcStoreCommit={_stores pushBack +_this;};
    ''' + 'private _draw={' + adapt(source).replace('local _drawMedic', 'true').replace('alive _drawMedic', 'true') + '};'


def test_native_draw_uses_original_remote_medic_and_exact_hundredths_after_global_selection_changes():
    execute(draw_setup() + r'''
    [0] call _draw;
    ACM_circulation_SyringeDraw_Medication="Morphine";
    ACM_circulation_SyringeDraw_Size=10;
    ACM_circulation_SyringeDraw_DrawnAmount=9;
    private _job=_waits deleteAt 0;(_job select 1) call (_job select 0);
    [_prepared isEqualTo [[uiNamespace,"Ketamine",1.23,3]],"timer retargeted drug or provider"] call _check;
    [count _stores==1 && {((_stores select 0) select 0) isEqualTo uiNamespace},"stored on curator"] call _check;
    ''')


def test_switching_control_before_draw_timer_cannot_consume_or_save_another_units_stock():
    execute(draw_setup() + r'''
    [0] call _draw;
    _controlled=profileNamespace;
    private _job=_waits deleteAt 0;(_job select 1) call (_job select 0);
    [count _prepared==0 && {count _stores==0},"stale timer consumed stock after control switch"] call _check;
    ''')


@pytest.mark.parametrize('switch_control', [False, True])
def test_native_direct_push_keeps_exact_receipt_and_retires_pending_even_when_control_changes(switch_control):
    execute(draw_setup() + r'''
    [1] call _draw;
    private _job=_waits deleteAt 0;(_job select 1) call (_job select 0);
    private _pending=uiNamespace getVariable ["ACME_nativeSyringePending",[]];
    [count _pending==1 && {((_pending select 0) select [0,2]) isEqualTo ["ACM_Syringe_3_Ketamine",123]},"exact pending receipt lost"] call _check;
    ''' + ('_controlled=profileNamespace;' if switch_control else '') + r'''
    ACM_circulation_SyringeDraw_Target=missionNamespace;
    ACM_circulation_SyringeDraw_TargetPart="RightLeg";
    private _job=_waits deleteAt 0;(_job select 1) call (_job select 0);
    [count (uiNamespace getVariable ["ACME_nativeSyringePending",[]])==0,"pending receipt blocked importer"] call _check;
    ''' + (r'''
    [count _injected==0,"push continued after control switch"] call _check;
    ''' if switch_control else r'''
    [count _injected==1 && {((_injected select 0) select [0,5]) isEqualTo [uiNamespace,_patient,"LeftArm","Ketamine",3]},"push retargeted captured patient/drug"] call _check;
    '''))


def menu_predicate():
    source = (ROOT / 'addons/gui/overrides/fnc_canOpenMenu.sqf').read_text()
    source = source.replace('findDisplay 312', 'objNull')
    source = re.sub(r'\bplayer\b', '_avatar', source)
    return 'private _canOpen={' + adapt(source) + '};'


@pytest.mark.parametrize('actor,expected', [('_avatar', 'uiNamespace'), ('profileNamespace', 'profileNamespace')])
def test_menu_predicate_repairs_local_legacy_avatar_without_mutating_global_or_other_actors(actor, expected):
    execute(setup() + r'''
    private _distanceActor=objNull;
    ace_common_fnc_isAwake={true};
    ACME_fnc_patientInteractionDistance={_distanceActor=_this select 0;1};
    ace_medical_gui_enableMedicalMenu=1;
    ''' + menu_predicate() + f'''
    [[{actor},_patient] call _canOpen,"menu rejected controlled provider"] call _check;
    [_distanceActor isEqualTo {expected},"predicate replaced explicit actor or kept stale avatar"] call _check;
    [ACE_player isEqualTo _avatar,"predicate changed ACE global"] call _check;
    ''')


def delayed_audio(name):
    source = read(name)
    tokens = lex(source)
    pairs = matching(tokens)
    result = []
    for i, token in enumerate(tokens):
        if token.value != 'CBA_fnc_waitAndExecute' or i < 2 or tokens[i - 2].value != ']':
            continue
        closing = i - 2
        opening = pairs[closing]
        args = split_args(tokens, opening + 1, closing, pairs)
        if not args or args[0][0].value != '{':
            continue
        begin, end = args[0][0].offset, args[0][-1].offset + 1
        callback = source[begin:end]
        if 'playSound3D' not in callback:
            continue
        callback = re.sub(r'getPosASL (_\w+)', '[0,0,0]', callback)
        callback = re.sub(r'playSound3D (\[[^;]+\]);', r'_heard pushBack \1;', callback)
        result.append(adapt(callback))
    return result


@pytest.mark.parametrize('name,index', [('ventPanelInit', 0), ('ventPanelTick', 0), ('ventPanelTick', 1)])
@pytest.mark.parametrize('change', ['', '_controlled=profileNamespace;',
                                     'uiNamespace setVariable ["ACME_vent_dlg",profileNamespace];'])
def test_delayed_device_audio_keeps_original_viewer_and_dialog(name, index, change):
    callbacks = delayed_audio(name)
    assert len(callbacks) == (1 if name == 'ventPanelInit' else 2)
    args = '[1,_controlled,_dlg]' if name == 'ventPanelInit' else '[_controlled,_dlg]'
    execute(setup() + r'''
    private _heard=[];private _dlg=parsingNamespace;
    uiNamespace setVariable ["ACME_vent_dlg",_dlg];
    uiNamespace setVariable ["ACME_vent_bootT0",1];
    uiNamespace setVariable ["ACME_vent_screen","selftest"];
    ''' + 'private _audio=' + callbacks[index] + ';private _audioArgs=' + args + ';' + change +
            '_audioArgs call _audio;' +
            f'[count _heard=={0 if change else 1},"audio escaped captured device/viewer"] call _check;')


@pytest.mark.parametrize('switch_control', [False, True])
def test_transfusion_watchdog_closes_only_after_its_captured_medic_loses_control(switch_control):
    source = (ROOT / 'addons/circulation/functions/fnc_openTransfusionMenu.sqf').read_text()
    begin = source.index('private _medicCondition =')
    predicate = adapt(source[begin:source.index(';', begin) + 1])
    execute(setup() + ('_controlled=profileNamespace;' if switch_control else '') + predicate +
            f'[_medicCondition isEqualTo {str(switch_control).lower()},"wrong transfusion viewer lifetime"] call _check;')


def test_disabled_pressure_presentation_keeps_pressure_claim_and_never_prepares_weapon_or_stance():
    execute(r'''
    missionNamespace setVariable ["ACME_interventionAnimations",false];
    _medic setVariable ["ACME_DP_Active",true];
    _medic setVariable ["ACME_DP_Paused",false];
    _medic setVariable ["ACME_DP_HeldGeneration",4];
    _medic setVariable ["ACME_dah_gen",4];
    private _prepared=0;
    ACME_fnc_medicAnimationPrep={_prepared=_prepared+1;0};
    ''' + 'ACME_fnc_directPressurePoseRetire={' + adapt(read('directPressurePoseRetire')) + '};' +
            'private _tick={' + adapt(read('directPressurePose')) + '};' +
            'private _enter={' + adapt(read('directPressurePoseEnter')) + '};' +
            'private _exit={' + adapt(read('directPressurePoseExit').replace('_m getUnitMovesInfo 2', '2').replace('_m getUnitMovesInfo 1', '1')) + '};' + r'''
    [_medic,_patient] call _tick;
    [!([_medic,_patient] call _enter),"disabled pressure requested entry"] call _check;
    [!([_medic,false] call _exit),"disabled pressure requested exit"] call _check;
    [_prepared==0 && {count _moves==0},"disabled pressure changed weapon/animation"] call _check;
    [_medic getVariable ["ACME_DP_Active",false],"presentation removed pressure claim"] call _check;
    [!(_medic getVariable ["ACME_DP_Paused",true]),"presentation paused clinical pressure"] call _check;
    [(_medic getVariable ["ACME_dah_gen",-1])==5,"old held worker not retired"] call _check;
    ''')


@pytest.mark.parametrize('enabled', [False, True])
def test_hang_bag_animation_watchdog_does_not_cancel_clinical_hold_when_theatre_is_disabled(enabled):
    source = read('hangBagTick')
    source = source[source.index('private _graceUntil ='):]
    source = source.replace('animationState _medic', '"standing"')
    execute(f'missionNamespace setVariable ["ACME_interventionAnimations",{str(enabled).lower()}];' + r'''
    private _stopped=0;
    ACME_fnc_hangBagStop={_stopped=_stopped+1;};
    _medic setVariable ["ACME_hang_PoseRetryAt",0];
    _medic setVariable ["ACME_hang_Pose","ACME_Acts_JetsCrewaidFCrouchThumbup_loop"];
    ''' + 'call {' + adapt(source) + '};' +
            f'[_stopped=={1 if enabled else 0},"animation watchdog changed disabled clinical hold"] call _check;')


def test_disabled_hang_preparation_keeps_clinical_dp_yield_without_taking_weapon_custody():
    execute(r'''
    missionNamespace setVariable ["ACME_interventionAnimations",false];
    _medic setVariable ["ACME_DP_Active",true];
    private _prepared=0;
    ACME_fnc_providerAnimation={"AmovPknlMstpSnonWnonDnon"};
    ACME_fnc_medicAnimationPrep={_prepared=_prepared+1;0};
    ''' + 'private _prep={' + adapt(read('hangBagPrep')) + '};' + r'''
    [_medic] call _prep;
    [_medic getVariable ["ACME_hang_Raising",false],"disabled theatre skipped raising lifecycle"] call _check;
    [_medic getVariable ["ACME_DP_Paused",false],"disabled theatre skipped clinical DP yield"] call _check;
    [_prepared==0 && {count _moves==0},"disabled theatre prepared weapon or moved provider"] call _check;
    [(_medic getVariable ["ACME_hang_savedWeaponSlots",[]]) isEqualTo [],"disabled theatre took weapon custody"] call _check;
    ''')


@pytest.mark.parametrize('switch_control', [False, True])
def test_live_vent_edit_uses_bound_clinician_and_rejects_stale_panel_before_next_tick(switch_control):
    execute(setup() + r'''
    private _panel=parsingNamespace;
    _panel setVariable ["ACME_vent_viewer",uiNamespace];
    uiNamespace setVariable ["ACME_vent_dlg",_panel];
    uiNamespace setVariable ["ACME_vent_target",_patient];
    uiNamespace setVariable ["ACME_vent_selIdx",0];
    uiNamespace setVariable ["ACME_vent_bpm",12];
    _patient setVariable ["ACME_vent_bpm",12];
    missionNamespace setVariable ["ACME_vent_simpleMode",false];
    ACME_fnc_ventPanelRefresh={};
    ''' + 'private _edit={' + adapt(read('ventPanelLiveEdit')) + '};' +
            ('_controlled=profileNamespace;' if switch_control else '') + '[1] call _edit;' +
            f'[(_patient getVariable ["ACME_vent_bpm",-1])=={12 if switch_control else 13},"stale viewer modified live ventilation"] call _check;')


@pytest.mark.parametrize('switch_control', [False, True])
def test_stop_transfusion_sends_original_provider_to_owner_and_rejects_stale_actor(switch_control):
    source = (ROOT / 'addons/circulation/functions/fnc_TransfusionMenu_ToggleIVFlow.sqf').read_text()
    execute(setup() + r'''
    ACM_circulation_TransfusionMenu_Medic=uiNamespace;
    ACM_circulation_TransfusionMenu_Target=_patient;
    ACM_circulation_TransfusionMenu_Selected_BodyPart="LeftArm";
    ACM_circulation_TransfusionMenu_Selected_AccessSite=1;
    ACM_circulation_TransfusionMenu_SelectIV=true;
    ACME_fnc_transfusionAccessValid={true};
    ACME_fnc_clinicalEpoch={4};
    ''' + 'private _stop={' + adapt(source, component='circulation') + '};' +
            ('_controlled=profileNamespace;' if switch_control else '') + 'call _stop;' +
            f'[count _events=={0 if switch_control else 1},"stale transfusion actor reached owner"] call _check;' +
            ('' if switch_control else r'''
    [((_events select 0) select 2) isEqualTo [_patient,"LeftArm",true,1,4,uiNamespace],"transfusion owner received curator/wrong route"] call _check;
    '''))


@pytest.mark.parametrize('newer_public', [False, True])
@pytest.mark.parametrize('new_speed_owner', [False, True])
def test_disabling_pressure_theatre_releases_observer_rate_even_after_newer_public_episode(newer_public, new_speed_owner):
    source = read('directPressurePoseExitSync')
    for old, new in [('local _medic', 'false'), ('local _m', 'false'), ('owner _m', '7'),
                     ('serverTime', '100'), ('animationState _m', '"ainvpknlmstpsnonwnondnon_medicend"'),
                     ('objectParent _m', 'objNull'),
                     ('getAnimSpeedCoef _m', '_testAnimationSpeed')]:
        source = re.sub(re.escape(old) + (r'\b' if old[-1].isalnum() else ''), lambda _: new, source)
    execute(r'''
    missionNamespace setVariable ["ACME_interventionAnimations",false];
    _testAnimationSpeed=1.5;
    _medic setVariable ["ACME_treatmentPoseEpoch",3];
    _medic setVariable ["ACME_DP_ExitRemote",[[90,0,7],true,-1,true,1]];
    ''' + f'_medic setVariable ["ACME_DP_ExitEpisode",[100,{2 if newer_public else 1},7,true]];' +
            f'ACME_fnc_providerAnimSpeedOwned={{{str(new_speed_owner).lower()}}};' +
            'private _receive={' + adapt(source) + '};' + r'''
    [_medic,[100,1,7],3,2,true] call _receive;
    private _id=count _handlers-1;private _worker=_handlers select _id;
    [_worker select 1,_id] call (_worker select 0);
    [!((_handlers select _id) select 2),"disabled observer worker survived"] call _check;
    [!((_medic getVariable "ACME_DP_ExitRemote") select 3),"observer retained abandoned rate ownership"] call _check;
    ''' + f'[_testAnimationSpeed=={1.5 if new_speed_owner else 1},"disabled observer leaked rate or overwrote successor"] call _check;')


def test_cpr_without_theatre_keeps_clinical_start_pause_resume_and_release_without_animdone_or_rtm():
    cpr_execute(r'''
    missionNamespace setVariable ["ACME_interventionAnimations",false];
    call _start;
    [count _moves==0,"disabled CPR played entry RTM"] call _check;
    call _enter;
    [(_patient getVariable ["ace_medical_CPR_provider",objNull]) isEqualTo _medic,"disabled CPR did not activate provider"] call _check;
    [ACM_circulation_CPRActive && {count _anims==0} && {count _moves==0},"disabled CPR blocked clinical startup or installed theatre"] call _check;
    ["ACM_circulation_CPRToggle_MouseID"] call _key;call _tick;
    [!ACM_circulation_CPRActive,"disabled CPR pause did not reach physiology"] call _check;
    ["ACM_circulation_CPRToggle_MouseID"] call _key;call _tick;
    [ACM_circulation_CPRActive,"disabled CPR resume did not reach physiology"] call _check;
    call _cancel;call _freed;
    [count _anims==0 && {count _moves==0},"disabled CPR emitted pause/resume/exit theatre"] call _check;
    ''')


@pytest.mark.parametrize('oxygen', [False, True])
@pytest.mark.parametrize('cpr', [False, True])
def test_bvm_without_theatre_starts_same_continuous_lifecycle_and_delivers_breaths(oxygen, cpr):
    execute(bvm_setup() + f'''
    missionNamespace setVariable ["ACME_interventionAnimations",false];
    _cprActive={str(cpr).lower()};
    [_medic,_patient,{str(oxygen).lower()},false] call ACM_breathing_fnc_useBVM;
    [ACM_core_ContinuousAction_Active,"disabled BVM failed admission"] call _check;
    for "_i" from 1 to 4 do {{call _tick;}};
    CBA_missionTime=13;call _tick;
    CBA_missionTime=20;call _tick;
    [_squeezes==2 && {{count _moves==0}},"disabled BVM lost breaths or emitted RTM"] call _check;
    [(_patient getVariable ["ACM_breathing_BVM_lastBreath",-1])==20,"disabled BVM failed clinical delivery"] call _check;
    ''')


@pytest.mark.parametrize('provider', ['uiNamespace', 'profileNamespace', 'objNull'])
def test_narc_box_teardown_cannot_autosave_or_reopen_for_foreign_or_deleted_provider(provider):
    source = re.sub(r'playSound "[^"]+";', '', read('skClose'))
    execute(setup() + f'''
    private _display=parsingNamespace;
    private _committed=0;private _returned=[];private _released=[];
    _display setVariable ["ACME_SK_CloseEpoch",1];
    _display setVariable ["ACME_SK_Provider",{provider}];
    _display setVariable ["ACME_SK_ReturnPatient",_patient];
    uiNamespace setVariable ["ACME_SK_CloseEpoch",1];
    uiNamespace setVariable ["ACME_SK_WasteStage","compound"];
    ACME_fnc_skPendingTagCommit={{}};
    ACME_fnc_skCompoundCommit={{_committed=_committed+1;}};
    ACME_fnc_vialLeaseRelease={{_released pushBack (_this select 0);}};
    ACME_fnc_restorePausedFlow={{}};ACME_fnc_restoreMedicationList={{}};
    ACME_fnc_reopenMedicalMenu={{_returned pushBack +_this;}};
    ''' + 'private _close={' + adapt(source) + '};[_display] call _close;' +
            f'[_committed=={1 if provider == "uiNamespace" else 0} && {{count _returned=={1 if provider == "uiNamespace" else 0}}},"foreign teardown saved or reopened another actor"] call _check;' +
            ('' if provider != 'uiNamespace' else r'''
    [((_returned select 0) select 4) isEqualTo uiNamespace,"teardown lost captured return provider"] call _check;
    '''))


@pytest.mark.parametrize('state', ['bag', 'idle'])
@pytest.mark.parametrize('successor', ['', 'ACME_fnc_providerStanceOwned={true};',
    'ACME_fnc_hangBagRestoreWeapons={_medic setVariable ["ACME_hang_Start",11];_medic setVariable ["ACME_hang_Active",true];};'])
def test_mid_toggle_hang_stop_structurally_releases_only_its_original_isolated_bag_skeleton(state, successor):
    expected = state == 'bag' and not successor
    execute(hang_setup() + r'''
    private _structural=[];
    CBA_fnc_globalEvent={
        if ((_this select 0)=="ace_common_switchMove") then {
            _structural pushBack +_this;_animation=toLower (_this select 1 select 1);
        };
    };
    call _activate;
    _stance="CROUCH";
    ''' + ('_animation="acme_acts_jetscrewaidfcrouchthumbup_loop";' if state == 'bag' else '_animation="amovpknlmstpsnonwnondnon";') +
            'missionNamespace setVariable ["ACME_interventionAnimations",false];' + successor + r'''
    [true,_medic] call ACME_fnc_hangBagStop;
    ''' + f'[count _structural=={1 if expected else 0},"teardown stranded bag skeleton or changed successor/noAnim start"] call _check;' +
            ('' if not expected else r'''
    [_animation=="amovpknlmstpsnonwnondnon" && {"AUTO" in _stances},"isolated hold retained skeleton/stance lock"] call _check;
    [!(_medic getVariable ["ACME_hang_Active",true]) && {!(_medic getVariable ["ACME_hang_Claimed",true])},"structural repair retained clinical claim"] call _check;
    '''))


@pytest.mark.parametrize('current_display', [False, True])
def test_real_medical_menu_event_reconciles_stale_curator_even_when_ace_onload_is_final(current_display):
    source = read('registerMedicalMenuOpenRuntime')
    start = source.index('    params ["_medic", "_target", "_display"];', source.index('["ace_medicalMenuOpened", {'))
    end = source.index('    // B169 renderer ownership:', start)
    prefix = source[start:end]
    execute(setup() + r'''
    private _display=parsingNamespace;
    ACME_fnc_respirationStop={};
    ''' + f'uiNamespace setVariable ["ace_medical_gui_menuDisplay",{("_display" if current_display else "profileNamespace")}];' +
            'private _onOpened={' + adapt(prefix) + '_medic};' +
            'private _actual=[_avatar,_patient,_display] call _onOpened;' +
            f'[_actual isEqualTo {("uiNamespace" if current_display else "_avatar")},"local menu kept curator or foreign event replaced explicit actor"] call _check;' +
            f'[ACE_player isEqualTo {("uiNamespace" if current_display else "_avatar")},"wrong ACE global UI boundary"] call _check;')
