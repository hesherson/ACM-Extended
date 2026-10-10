"""Execute native provider stance selection and BVM lifecycle, with engine boundaries mocked."""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, execute
from test_bvm_startup import setup as bvm_setup


def controller_source():
    text = (ROOT / 'addons/core/functions/fnc_beginContinuousAction.sqf').read_text()
    text = text.replace('animationState _medic', '_providerAnimation')
    text = text.replace('stance _medic', '_providerStance')
    text = text.replace('local _medic', '_providerLocal')
    text = text.replace('objectParent _medic', '_medicParent').replace('objectParent _patient', '_patientParent')
    return adapt(text)


def setup():
    return bvm_setup() + '''
        private _providerStance="PRONE"; private _providerLocal=true; private _providerAnimation="";
        private _medicParent=objNull; private _patientParent=objNull;
        private _cancelled=0;
        private _drainWaits={private _pending=+_waits;_waits=[];{(_x select 1) call (_x select 0);} forEach _pending;};
    ''' + 'ACM_core_fnc_beginContinuousAction={' + controller_source() + '};'


@pytest.mark.parametrize('legacy_allow', ['', ',false', ',true'])
@pytest.mark.parametrize('stance,main,end', [
    ('PRONE', 'ACM_ProneContinuous', 'AmovPpneMstpSnonWnonDnon'),
    ('CROUCH', 'ACM_GenericContinuous', 'AmovPknlMstpSnonWnonDnon'),
    ('STAND', 'ACM_GenericContinuous', 'AmovPknlMstpSnonWnonDnon'),
])
def test_generic_continuous_start_and_cancel_preserve_prone(legacy_allow, stance, main, end):
    execute(setup() + f'_providerStance="{stance}";' + '''
        private _accepted=[[_medic,_patient,"head"],{},{_cancelled=_cancelled+1;},{}''' + legacy_allow + '''] call ACM_core_fnc_beginContinuousAction;
        call _drainWaits;
    ''' + f'''
        [_accepted && {{"{main}" in _moves}},"wrong continuous work animation"] call _check;
        ACM_core_ContinuousAction_Active=false;call _tick;
        [_cancelled==1 && {{(_moves select (count _moves-1))=="{end}"}},"wrong cancellation pose"] call _check;
    ''' + ('''[(_moves findIf {(toLower _x find "pknl")>=0 || {_x=="ACM_GenericContinuous"}})<0,"prone episode requested kneeling"] call _check;''' if stance == 'PRONE' else ''))


@pytest.mark.parametrize('oxygen,portable', [(False, False), (True, False), (True, True)])
@pytest.mark.parametrize('cpr', [False, True])
def test_real_bvm_start_breath_and_cancel_never_request_kneeling(oxygen, portable, cpr):
    execute(setup() + f'_cprActive={str(cpr).lower()};' + f'''
        [_medic,_patient,{str(oxygen).lower()},{str(portable).lower()}] call ACM_breathing_fnc_useBVM;
        [ACM_core_ContinuousAction_Active && {{"ACM_ProneContinuous" in _moves}},"prone BVM was not admitted"] call _check;
        CBA_missionTime=13;call _tick;CBA_missionTime=20;call _tick;
        [_squeezes==2,"prone BVM failed clinical breaths"] call _check;
        private _cancel=(_keys select {{(_x select 0)==ACM_breathing_BVMCancel_MouseID}}) select 0;
        call (_cancel select 1);call _tick;call _drainWaits;
        [!ACM_core_ContinuousAction_Active,"BVM cancel did not retire controller"] call _check;
        [(_moves select (count _moves-1))=="AmovPpneMstpSnonWnonDnon","BVM cancellation raised provider"] call _check;
        [(_moves findIf {{(toLower _x find "pknl")>=0 || {{_x=="ACM_GenericContinuous"}}}})<0,"BVM requested a kneeling animation"] call _check;
    ''')


def test_prone_change_during_pending_standing_entry_and_exit_is_preserved():
    execute(setup() + '''
        _providerStance="STAND";
        [[_medic,_patient,"head"],{},{},{}] call ACM_core_fnc_beginContinuousAction;
        _providerStance="PRONE";_moves=[];call _drainWaits;
        [_moves isEqualTo ["ACM_ProneContinuous"],"delayed standing entry forced kneel after going prone"] call _check;
        ACM_core_ContinuousAction_Active=false;call _tick;
        [(_moves select (count _moves-1))=="AmovPpneMstpSnonWnonDnon","late-prone cancellation raised provider"] call _check;
    ''')


@pytest.mark.parametrize('reason', ['cancelled', 'replaced', 'ownership'])
def test_old_delayed_continuous_entry_cannot_animate_after_retirement(reason):
    retire = {'cancelled':'ACM_core_ContinuousAction_Active=false;call _tick;',
              'replaced':'ACM_core_ContinuousAction_Epoch=ACM_core_ContinuousAction_Epoch+1;',
              'ownership':'_providerLocal=false;'}[reason]
    execute(setup() + '''
        _providerStance="STAND";
        [[_medic,_patient,"head"],{},{},{}] call ACM_core_fnc_beginContinuousAction;
    ''' + retire + '''
        _providerStance="PRONE";_moves=[];call _drainWaits;
        [_moves isEqualTo [],"old delayed entry animated replacement/locality-lost provider"] call _check;
    ''')


def test_same_vehicle_continuous_action_preserves_seated_animation():
    execute(setup() + '''
        _medicParent=missionNamespace;_patientParent=missionNamespace;
        [[_medic,_patient,"head"],{},{},{}] call ACM_core_fnc_beginContinuousAction;
        call _tick;[ACM_core_ContinuousAction_Active,"same-vehicle hold rejected"] call _check;
        ACM_core_ContinuousAction_Active=false;call _tick;call _drainWaits;
        [_moves isEqualTo [],"seated provider received ground animation"] call _check;
    ''')


def ai_source():
    text = (ROOT / 'addons/core/overrides/fnc_playTreatmentAnim.sqf').read_text()
    text = re.sub(r'^\s*(?:TRACE|WARNING)_\d\([^;]+;', '', text, flags=re.M)
    text = text.replace('animationState _medic', '_providerAnimation')
    text = text.replace('stance _medic', '_providerStance').replace('objectParent _medic', '_medicParent')
    text = text.replace('IS_UNCONSCIOUS(_patient)', 'false')
    text = text.replace('configFile >> QACEGVAR(medical_treatment,actions) >> _actionName', 'missionNamespace')
    text = text.replace('getText (_config >> _configProperty)', '(_configValues getVariable [_configProperty, ""])')
    return adapt(text)


def native_provider_source():
    text = (ROOT / 'addons/core/functions/fnc_treatmentNative.sqf').read_text()
    # Execute the complete provider branch from selection through queued work/end animations;
    # item consumption, patient positioning and progressBar remain outside this presentation test.
    text = text[text.index('    // Get treatment animation for the medic'):text.index('    // Play a random treatment sound globally')]
    text = re.sub(r'TRACE_\d\([^;]+;', '', text)
    text = re.sub(r'WARNING_\d\([^;]+;', '', text)
    text = text.replace('animationState _medic', '_providerAnimation')
    text = text.replace('stance _medic', '_providerStance').replace('objectParent _medic', '_medicParent')
    text = re.sub(r'getText \(_config >> (\[[^\n]+?\] select \([^\n]+?\))\)', r'(_configValues getVariable [\1, ""])', text)
    text = text.replace('isNumber (_config >> "ACME_suppressNativeTreatmentAnim")', '_suppressConfig')
    text = text.replace('getNumber (_config >> "ACME_suppressNativeTreatmentAnim")', '1')
    text = text.replace('getNumber (_config >> "ACME_normalSpeedAnimation")', '(_configValues getVariable ["ACME_normalSpeedAnimation",0])')
    text = text.replace('weaponState _medic', '[]').replace('animationState _medic', '_providerAnimation')
    text = text.replace('binocular _medic', '""').replace('weaponLowered _medic', 'false')
    for command in ('primaryWeapon', 'secondaryWeapon', 'handgunWeapon'):
        text = text.replace(command + ' _medic', '""')
    text = text.replace('ANIMATION_SPEED_MIN_COEFFICIENT', '0.5').replace('ANIMATION_SPEED_MAX_COEFFICIENT', '2.5')
    text = text.replace('ACEGVAR(medical_treatment,animDurations) get toLowerANSI _medicAnim', '5')
    text = text.replace('QUOTE(ACE_ADDON(Medical_Treatment))', '"nativeTreatment"')
    text = text.replace('_medic selectWeapon "";', '')
    return adapt(text)


def selection_setup():
    return '''
        private _providerStance="PRONE";private _medicParent=objNull;private _providerAnimation="";
        private _configValues=parsingNamespace;private _kneels=0;private _suppressConfig=false;
        ace_common_fnc_goKneeling={_kneels=_kneels+1;};
        CBA_fnc_replace={params ["_str","_from","_to"];private _i=_str find _from;
            if (_i<0) exitWith {_str};(_str select [0,_i])+_to+(_str select [_i+count _from])};
        private _config=missionNamespace;private _treatmentTime=5;private _ignoreAnimCoef=false;
        private _bodyPart="Head";private _classname="InsertNPA";
    '''


@pytest.mark.parametrize('is_self', [False, True])
@pytest.mark.parametrize('configured', [
    'AinvPknlMstpSnonWnonDr_medic4',
    'AmovPknlMstpSrasWpstDnon_AmovPknlMstpSrasWpstDnon_gear',
    'ACME_ChestInspectWork',
    'AinvPpneMstpSlayW[wpn]Dnon_medicOther',
    '',
])
@pytest.mark.parametrize('path', ['ai', 'native'])
def test_native_and_ai_config_selection_has_no_prone_kneel_fallback(is_self, configured, path):
    expected = configured.replace('[wpn]', 'non') if ('Ppne' in configured or not configured) else 'AinvPpneMstpSlayWnonDnon_' + ('medic' if is_self else 'medicOther')
    key = 'animationMedicSelfProne' if is_self else 'animationMedicProne'
    source = ('private _invoke={' + ai_source() + '};[_medic,_patient,"InsertNPA",_isSelf] call _invoke;') if path == 'ai' else ('call {' + native_provider_source() + '};')
    execute(selection_setup() + f'private _isSelf={str(is_self).lower()};_configValues setVariable ["{key}","{configured}"];' + source + f'''
        [_kneels==0,"native/AI fallback requested kneeling"] call _check;
        [(_moves param [0,""])=="{expected}","wrong prone native animation"] call _check;
    ''' + ('''[(_moves select 1)=="AmovPpneMstpSnonWnonDnon","native treatment end raised provider"] call _check;''' if path == 'native' and configured else ''))


@pytest.mark.parametrize('path', ['ai', 'native'])
def test_prone_normalization_preserves_cpr_forced_animation(path):
    source = ('private _invoke={' + ai_source() + '};[_medic,_patient,"CPR",false] call _invoke;') if path == 'ai' else ('call {' + native_provider_source() + '};')
    execute(selection_setup() + '''
        private _isSelf=false;_classname="CPR";
        _configValues setVariable ["animationMedicProne","ACM_CPR"];
    ''' + source + '''
        [(_moves select 0)=="ACM_CPR","CPR compressor exception was replaced"] call _check;
    ''')


def test_native_suppressed_controller_does_not_gain_generic_prone_animation():
    execute(selection_setup() + '''
        private _isSelf=false;_suppressConfig=true;
        _configValues setVariable ["animationMedicProne","ACME_ChestInspectWork"];
    ''' + 'call {' + native_provider_source() + '};' + '''
        [_moves isEqualTo [],"native animation overrode ACME-owned prone controller"] call _check;
    ''')


@pytest.mark.parametrize('classname,expected_length', [('CheckAirway',8),('CheckBreathing',8),('CHECKBREATHING',8),('InsertNPA',7)])
@pytest.mark.parametrize('epoch', [-1, 17])
def test_assessment_callback_payload_captures_exact_episode_without_changing_other_actions(classname, expected_length, epoch):
    text = (ROOT/'addons/core/functions/fnc_treatmentNative.sqf').read_text()
    text = text[text.index('private _callbackArgs ='):]
    text = text.replace('getText (_config >> "displayNameProgress")', '"Checking"')
    execute('''
        private _bodyPart="Head";private _itemUser=objNull;private _usedItem="";private _createLitter=false;
        private _treatmentTime=2;private _startedArgs=[];private _progressArgs=[];private _startedEvent=[];private _assessmentProgress=false;
        private _callbackStart={_startedArgs=+_this;};private _callbackProgress={true};
        ace_medical_treatment_fnc_treatmentSuccess={};ace_medical_treatment_fnc_treatmentFailure={};
        ace_common_fnc_progressBar={_progressArgs=+(_this select 1);};
        ACME_fnc_assessmentProgressBar={_progressArgs=+(_this select 1);_assessmentProgress=true;};
        CBA_fnc_localEvent={_startedEvent=_this select 1;};
    '''+f'private _classname="{classname}";_medic setVariable ["ACME_assessment",[{epoch}]];'+
        'call {'+adapt(text)+'};'+f'''
        _medic setVariable ["ACME_assessment",[99]];
        [count _startedArgs=={expected_length} && {{count _progressArgs=={expected_length}}},"callback shape changed"] call _check;
        [_startedArgs isEqualTo _progressArgs,"start and progress bound different assessment episode"] call _check;
        [count _startedEvent==7,"global treatment-start contract changed"] call _check;
        [_assessmentProgress isEqualTo {str(expected_length==8).lower()},"assessment progress helper leaked to another native treatment"] call _check;
    '''+(f'[(_progressArgs select 7)=={epoch},"old progress callback adopted replacement epoch"] call _check;' if expected_length==8 else ''))


@pytest.mark.parametrize('animation', ['ACM_ProneContinuous', 'AinvPpneMstpSlayWnonDnon_medicOther'])
def test_continuous_undefined_stance_in_known_prone_animation_preserves_start_and_end(animation):
    execute(setup()+f'_providerStance="UNDEFINED";_providerAnimation="{animation}";'+'''
        [[_medic,_patient,"head"],{},{},{}] call ACM_core_fnc_beginContinuousAction;
        [_moves isEqualTo ["ACM_ProneContinuous"],"custom prone stance did not start prone hold"] call _check;
        ACM_core_ContinuousAction_Active=false;call _tick;
        [(_moves select (count _moves-1))=="AmovPpneMstpSnonWnonDnon","custom prone cancellation raised provider"] call _check;
    ''')


@pytest.mark.parametrize('animation', ['ACM_ProneContinuous', 'AinvPpneMstpSlayWnonDnon_medicOther'])
@pytest.mark.parametrize('path', ['ai','native'])
def test_native_undefined_stance_in_known_prone_animation_selects_prone_config(animation,path):
    source=('private _invoke={'+ai_source()+'};[_medic,_patient,"InsertNPA",false] call _invoke;') if path=='ai' else ('call {'+native_provider_source()+'};')
    execute(selection_setup()+f'_providerStance="UNDEFINED";_providerAnimation="{animation}";'+'''
        private _isSelf=false;
        _configValues setVariable ["animationMedic","ACME_ChestInspectWork"];
        _configValues setVariable ["animationMedicProne","AinvPpneMstpSlayW[wpn]Dnon_medicOther"];
    '''+source+'''
        [(_moves select 0)=="AinvPpneMstpSlayWnonDnon_medicOther","known prone animation selected kneeling config"] call _check;
    '''+('''[(_moves select 1)=="AmovPpneMstpSnonWnonDnon","known prone animation ended kneeling"] call _check;''' if path=='native' else ''))


def test_delayed_continuous_entry_and_cleanup_adopt_known_prone_animation_with_undefined_stance():
    execute(setup()+'''
        _providerStance="STAND";
        [[_medic,_patient,"head"],{},{},{}] call ACM_core_fnc_beginContinuousAction;
        _providerStance="UNDEFINED";_providerAnimation="ACM_ProneContinuous";_moves=[];call _drainWaits;
        [_moves isEqualTo ["ACM_ProneContinuous"],"delayed callback raised custom prone provider"] call _check;
        ACM_core_ContinuousAction_Active=false;call _tick;
        [(_moves select (count _moves-1))=="AmovPpneMstpSnonWnonDnon","late custom prone cancellation raised provider"] call _check;
    ''')
