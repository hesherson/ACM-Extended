"""Execute ACME targeting protection with the supplied ACE status-effect code.

ACE reason bitmasks, aggregate change decisions, event selection and visibility
restore execute unchanged. Objects, traits, engine groups and CBA transport are
explicit fixtures; these tests do not simulate actual AI targeting or networking.
"""
import re

import pytest

from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute, read

FIXTURES = ROOT / 'tools/fixtures/ace_ai_protection'


def engine(text):
    tokens=lex(text);pairs=matching(tokens);edits=[]
    for index,token in enumerate(tokens):
        if token.kind=='ident' and token.value in ('addEventHandler','removeEventHandler'):
            opening=index+1
            if tokens[opening].value!='[' or opening not in pairs:continue
            end=pairs[opening]
            unit=tokens[index-1]
            assert unit.kind=='ident'
            call='_addObjectEH' if token.value=='addEventHandler' else '_removeObjectEH'
            edits.append((unit.offset,tokens[end].offset+1,
                          '(['+unit.value+','+text[tokens[opening].offset:tokens[end].offset+1]+'] call '+call+')'))
    for start,end,value in reversed(edits):text=text[:start]+value+text[end:]
    text = re.sub(r'\blocal (_\w+)', r'((\1 getVariable ["TEST_owner",7]) == _machine)', text)
    text = re.sub(r'\balive (_\w+)', r'(\1 getVariable ["TEST_alive",true])', text)
    text = re.sub(r'\bisPlayer (_\w+)', r'(\1 getVariable ["TEST_player",true])', text)
    text = re.sub(r'\banimationState (_\w+)', r'(\1 getVariable ["TEST_animation","acm_lyingstate"])', text)
    text = re.sub(r'\bobjectParent (_\w+)', r'(\1 getVariable ["TEST_vehicle",objNull])', text)
    text = re.sub(r'\bcurrentWeapon (_\w+)', r'(\1 getVariable ["TEST_weapon",""])', text)
    text = re.sub(r'(_\w+) getUnitTrait "camouflageCoef"', r'(\1 getVariable ["TEST_camouflage",1])', text)
    text = re.sub(r'(_\w+) setUnitTrait \["camouflageCoef",\s*([^\]]+)\];', r'_traitWrites=_traitWrites+1;\1 setVariable ["TEST_camouflage",\2];', text)
    text = text.replace('hashValue _object', '17')
    text = text.replace('side group _object', '"west"').replace('side _x', '"east"')
    text = text.replace('_x forgetTarget _object;', '_forgotten pushBack _object;')
    text = text.replace('allGroups', '([] call _allGroups)')
    text = text.replace('clientOwner', '_machine').replace('isServer', '(_machine==2)')
    text = text.replace('diag_tickTime', '_clock').replace('serverTime', '_clock')
    text = text.replace('allUnits', '_units').replace('hasInterface', 'true')
    # SQFVM does not model the scheduled/unscheduled engine execution context.
    text = text.replace('canSuspend', 'false')
    # The two vanilla roll classes are an engine-config boundary, not shipped source.
    text = text.replace('configFile >> "CfgMovesMaleSdr" >> "States" >> _animation', '_animation')
    text = re.sub(r'getNumber \(_state >> "(disableWeapons|canPullTrigger)"\)',
                  r'([_state,"\1"] call _getMoveConfig)', text)
    text = text.replace('[objNull]', '[profileNamespace]')
    text = text.replace('_object == _objectRef', '_object isEqualTo _objectRef')
    text = text.replace('isNull (_unit getVariable ["TEST_vehicle",objNull])', '((_unit getVariable ["TEST_vehicle",objNull]) isEqualTo objNull)')
    return adapt(text)


def ace(name):
    text = (FIXTURES / ('fnc_' + name + '.sqf')).read_text()
    text = re.sub(r'TRACE_\d+\([^;\n]*\);', '', text)
    text = re.sub(r'LOG\([^;\n]*\);', '', text)
    text = re.sub(r'QGVAR\(([^)]+)\)', lambda m: '"ace_common_' + m[1] + '"', text)
    text = re.sub(r'GVAR\(([^)]+)\)', lambda m: 'ace_common_' + m[1], text)
    text = re.sub(r'FUNC\(([^)]+)\)', lambda m: 'ace_common_fnc_' + m[1], text)
    return engine(text)


def setup():
    text = '''
        private _machine=7; private _clock=10; private _traitWrites=0;
        private _groupScans=0; private _forgotten=[]; private _broadcasts=[]; private _targeted=[];
        private _objectEvents=[];private _removedObjectEvents=[];private _globalHandlers=createHashMap;
        private _moveConfig=createHashMap;private _moveConfigQueries=[];
        private _getMoveConfig={params ["_animation","_field"];_moveConfigQueries pushBack [_animation,_field];
            private _key=_animation+"_"+_field;if (_key in _moveConfig) then {_moveConfig get _key} else {0}};
        private _addObjectEH={params ["_unit","_event"];_objectEvents pushBack [_unit,_event];count _objectEvents-1};
        private _removeObjectEH={_removedObjectEvents pushBack _this;};
        private _units=[_patient]; private _allGroups={_groupScans=_groupScans+1;[missionNamespace]};
        _patient setVariable ["TEST_owner",7];_medic setVariable ["TEST_owner",8];
        ace_common_settingsInitFinished=true;ace_common_runAtSettingsInitialized=[];
        ace_common_statusEffects=createHashMapFromArray [["sethidden",[true,false,"ace_common_setHidden"]]];
        missionNamespace setVariable ["ace_common_statusEffects_setHidden",["ace_unconscious","acme_medical_downed","third_party"]];
        CBA_fnc_targetEvent={_targeted pushBack _this;};
        CBA_fnc_addEventHandler={_globalHandlers set [_this select 0,_this select 1];};
        CBA_fnc_globalEvent={_broadcasts pushBack _this;
            if ((_this select 0)=="ace_common_setHidden") then {(_this select 1) call _hiddenEvent;};
            if ((_this select 0) in _globalHandlers) then {(_this select 1) call (_globalHandlers get (_this select 0));};};
        CBA_fnc_globalEventJIP={_broadcasts pushBack _this;};
        CBA_fnc_removeGlobalEventJIP={};
    '''
    for name in ('binarizeNumber', 'toBitmask', 'statusEffect_resetVariables', 'statusEffect_get', 'statusEffect_set', 'statusEffect_sendEffects'):
        text += 'ace_common_fnc_' + name + '={' + ace(name) + '};'
    hidden = (FIXTURES / 'setHidden_event.sqf').read_text()
    hidden = hidden.split('[QGVAR(setHidden), {', 1)[1].rsplit('}] call CBA_fnc_addEventHandler;', 1)[0]
    hidden = re.sub(r'TRACE_\d+\([^;\n]*\);', '', hidden)
    hidden = hidden.replace('QGVAR(oldVisibility)', '"ace_common_oldVisibility"')
    text += 'private _hiddenEvent={' + engine(hidden) + '};'
    return text


def production():
    bridge = (ROOT / 'addons/core/functions/fnc_registerDownedProtectionReason.sqf').read_text()
    return setup() + 'ACM_core_fnc_registerDownedProtectionReason={' + engine(bridge) + '};' + ''.join('ACME_fnc_' + name + '={' + engine(read(name)) + '};'
                             for name in ('aiProtectionWanted', 'aiProtectionSync', 'aiProtectionTick', 'aiProtectionInit'))


@pytest.mark.parametrize('state,wanted', [
    ('_patient setVariable ["ACE_isUnconscious",true];', True),
    ('_patient setVariable ["ACM_core_Lying_State",true];', True),
    ('_patient setVariable ["ACM_core_Lying_State",true];_patient setVariable ["TEST_animation","acme_obtundedback"];', True),
    ('_patient setVariable ["ACE_isUnconscious",true];_patient setVariable ["TEST_vehicle",missionNamespace];', True),
    ('_patient setVariable ["TEST_animation","amovppnemstpsraswrfldnon"];', False),
    ('_patient setVariable ["ACME_AAJT_zone3",true];_patient setVariable ["TEST_animation","ainjppnemstpsnonwrfldnon"];', False),
    ('_patient setVariable ["ACME_obtunded",true];_patient setVariable ["TEST_animation","amovpercmstpsnonwnondnon"];', False),
    ('_patient setVariable ["ACM_core_Lying_State",true];_patient setVariable ["TEST_animation","amovppnemstpsraswrfldnon"];', False),
    ('_patient setVariable ["ACM_core_Lying_State",true];_patient setVariable ["TEST_vehicle",missionNamespace];', False),
    ('_patient setVariable ["ACM_core_Lying_State",true];_patient setVariable ["TEST_animation","acme_headelevproviderlift"];', False),
])
def test_wanted_distinguishes_medical_downing_from_conscious_combat_postures(state, wanted):
    execute(production() + state + f'''
        [[_patient] call ACME_fnc_aiProtectionWanted isEqualTo {str(wanted).lower()},"wrong downed protection eligibility"] call _check;
    ''')


@pytest.mark.parametrize('pose', ['Grab', 'Hold', 'Release'])
@pytest.mark.parametrize('lying', [False, True])
def test_semi_fowler_patient_poses_require_the_medical_lying_state(pose, lying):
    execute(production() + f'''
        _patient setVariable ["ACM_core_Lying_State",{str(lying).lower()}];
        _patient setVariable ["TEST_animation","ACME_HeadElevPatient{pose}"];
        [[_patient] call ACME_fnc_aiProtectionWanted isEqualTo {str(lying).lower()},
            "Semi-Fowler eligibility ignored the medical lying state"] call _check;
    ''')


@pytest.mark.parametrize('pose', ['ace_medical_engine_uncon_anim_1', 'acm_recoveryposition'])
@pytest.mark.parametrize('lying', [False, True])
def test_facedown_and_recovery_patient_poses_require_the_medical_lying_state(pose, lying):
    execute(production() + f'''
        _patient setVariable ["ACM_core_Lying_State",{str(lying).lower()}];
        _patient setVariable ["TEST_animation","{pose}"];
        [[_patient] call ACME_fnc_aiProtectionWanted isEqualTo {str(lying).lower()},
            "facedown/recovery eligibility ignored the medical lying state"] call _check;
    ''')


@pytest.mark.parametrize('pose', ['ainjppnemstpsnonwrfldnon_rolltofront', 'ainjppnemstpsnonwrfldnon_rolltoback'])
@pytest.mark.parametrize('disabled', [0, 1])
@pytest.mark.parametrize('trigger', [0, 1])
def test_exact_native_patient_rolls_require_loaded_config_to_prevent_weapon_fire(pose, disabled, trigger):
    execute(production() + f'''
        _patient setVariable ["ACM_core_Lying_State",true];
        _patient setVariable ["TEST_animation","{pose}"];
        _moveConfig set ["{pose}_disableWeapons",{disabled}];
        _moveConfig set ["{pose}_canPullTrigger",{trigger}];
        [[_patient] call ACME_fnc_aiProtectionWanted isEqualTo {str(disabled > 0 and trigger == 0).lower()},
            "native patient roll ignored loaded weapon constraints"] call _check;
        [count _moveConfigQueries>0,"native roll did not inspect its loaded config"] call _check;
    ''')


@pytest.mark.parametrize('pose,lying', [
    ('ainjppnemstpsnonwrfldnon_rolltofront', False),
    ('ainjppnemstpsnonwrfldnon_rolltoback', False),
    ('third_party_disabled_combat_pose', True),
])
def test_native_roll_config_cannot_expand_protection_to_unrelated_or_nonmedical_postures(pose, lying):
    execute(production() + f'''
        _patient setVariable ["ACM_core_Lying_State",{str(lying).lower()}];
        _patient setVariable ["TEST_animation","{pose}"];
        _moveConfig set ["{pose}_disableWeapons",1];
        _moveConfig set ["{pose}_canPullTrigger",0];
        [!([_patient] call ACME_fnc_aiProtectionWanted),"unrelated/nonmedical posture acquired protection"] call _check;
        [count _moveConfigQueries==0,"unrelated/nonmedical posture consulted the native roll exception"] call _check;
    ''')


@pytest.mark.parametrize('pose', ['Grab', 'Hold', 'Release'])
def test_eligible_semi_fowler_patient_config_disables_weapon_fire(pose):
    # Restrict assertions to each exact class body, not similarly named providers.
    text = (ROOT / 'addons/acm_extended/config.cpp').read_text()
    tokens = lex(text)
    pairs = matching(tokens)
    index = next(i for i, token in enumerate(tokens)
                 if token.value == 'ACME_HeadElevPatient' + pose and tokens[i - 1].value == 'class')
    opening = next(i for i in range(index, len(tokens)) if tokens[i].value == '{')
    body = tokens[opening + 1:pairs[opening]]
    values = {body[i].value: body[i + 2].value for i in range(len(body) - 2)
              if body[i].kind == 'ident' and body[i + 1].value == '='}
    assert {name: values.get(name) for name in (
        'disableWeapons', 'disableWeaponsLong', 'disableWeaponsShort', 'canPullTrigger'
    )} == {'disableWeapons': '1', 'disableWeaponsLong': '1',
           'disableWeaponsShort': '1', 'canPullTrigger': '0'}


def test_supplied_ace_reason_composition_preserves_other_modules_and_restores_visibility():
    execute(setup() + '''
        _patient setVariable ["TEST_camouflage",0.73];
        [_patient,"setHidden","ace_unconscious",true] call ace_common_fnc_statusEffect_set;
        [_patient,"setHidden","acme_medical_downed",true] call ace_common_fnc_statusEffect_set;
        [_patient,"setHidden","ace_unconscious",false] call ace_common_fnc_statusEffect_set;
        [count _broadcasts==1 && {_traitWrites==1} && {_groupScans==1},"ACE handoff replayed or restored visibility"] call _check;
        [(_patient getVariable "TEST_camouflage")==0,"medical reason did not retain invisibility"] call _check;
        [_patient,"setHidden","third_party",true] call ace_common_fnc_statusEffect_set;
        [_patient,"setHidden","acme_medical_downed",false] call ace_common_fnc_statusEffect_set;
        [count _broadcasts==1,"ACME removal cleared another reason"] call _check;
        [_patient,"setHidden","third_party",false] call ace_common_fnc_statusEffect_set;
        [count _broadcasts==2 && {(_patient getVariable "TEST_camouflage")==0.73},"final ACE removal lost original visibility"] call _check;
    ''')


def test_ace_unconscious_to_awake_acm_lying_handoff_preserves_protection_then_getup_releases_only_ours():
    execute(production() + '''
        _patient setVariable ["TEST_camouflage",0.73];
        _patient setVariable ["ACE_isUnconscious",true];
        [_patient,"setHidden","ace_unconscious",true] call ace_common_fnc_statusEffect_set;
        [_patient] call ACME_fnc_aiProtectionSync;
        _patient setVariable ["ACM_core_Lying_State",true];
        _patient setVariable ["ACE_isUnconscious",false];
        [_patient,"setHidden","ace_unconscious",false] call ace_common_fnc_statusEffect_set;
        [_patient] call ACME_fnc_aiProtectionSync;
        [(_patient getVariable "TEST_camouflage")==0,"wake-to-lying restored visibility"] call _check;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["acme_medical_downed"],
            "awake lying reason did not survive ACE cleanup"] call _check;
        [_patient,"setHidden","third_party",true] call ace_common_fnc_statusEffect_set;
        [_patient,"reset"] call ACME_fnc_aiProtectionSync;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["third_party"],
            "Get Up removed another module's protection"] call _check;
        [(_patient getVariable "TEST_camouflage")==0,"another module's visibility reason was overridden"] call _check;
        [_patient,"setHidden","third_party",false] call ace_common_fnc_statusEffect_set;
        [abs ((_patient getVariable "TEST_camouflage")-0.73)<0.00001,"original camouflage was not restored"] call _check;
    ''')


def test_actual_fired_handler_releases_awake_episode_until_new_downing():
    execute(production() + '''
        _patient setVariable ["ACM_core_Lying_State",true];
        [_patient] call ACME_fnc_aiProtectionSync;
        private _handler=(_objectEvents select {((_x select 1) select 0)=="FiredMan"}) select 0;
        [_patient] call ((_handler select 1) select 1);
        [_patient] call ACME_fnc_aiProtectionSync;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo [],"firing did not retire awake protection"] call _check;
        [(_patient getVariable ["TEST_camouflage",1])==1,"firing left combat-capable patient hidden"] call _check;
        _patient setVariable ["ACE_isUnconscious",true];
        [_patient] call ACME_fnc_aiProtectionSync;
        ["acme_medical_downed" in ([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1),"new true unconscious episode stayed blocked"] call _check;
    ''')


@pytest.mark.parametrize('reason', ['death', 'restoring', 'getup', 'combat_animation'])
def test_eligibility_exit_removes_only_owned_effect(reason):
    state = {
        'death':'_patient setVariable ["TEST_alive",false];',
        'restoring':'_patient setVariable ["ACME_clinicalRestoring",true];',
        'getup':'_patient setVariable ["ACM_core_Lying_State",false];',
        'combat_animation':'_patient setVariable ["TEST_animation","amovppnemstpsraswrfldnon"];',
    }[reason]
    execute(production() + '''
        _patient setVariable ["ACM_core_Lying_State",true];
        [_patient] call ACME_fnc_aiProtectionSync;
    ''' + state + '''
        [_patient] call ACME_fnc_aiProtectionSync;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo [],"stale protection survived eligibility exit"] call _check;
        [(_patient getVariable ["TEST_camouflage",1])==1,"eligibility exit failed to restore camouflage"] call _check;
    ''')


def test_reset_waits_for_actual_unconscious_clear_before_accepting_new_episode():
    execute(production() + '''
        _patient setVariable ["ACE_isUnconscious",true];_patient setVariable ["ACM_core_Lying_State",true];
        [_patient,"setHidden","ace_unconscious",true] call ace_common_fnc_statusEffect_set;
        [_patient] call ACME_fnc_aiProtectionSync;
        [_patient,"reset"] call ACME_fnc_aiProtectionSync;
        [_patient] call ACME_fnc_aiProtectionSync;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["ace_unconscious"],
            "reset cleared ACE reason or re-added from stale unconscious flag"] call _check;
        _patient setVariable ["ACE_isUnconscious",false];
        [_patient] call ACME_fnc_aiProtectionSync;
        [!([_patient] call ACME_fnc_aiProtectionWanted),"reset awake lying episode reactivated"] call _check;
        _patient setVariable ["ACE_isUnconscious",true];
        [_patient] call ACME_fnc_aiProtectionSync;
        ["acme_medical_downed" in ([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1),"new unconscious episode rejected"] call _check;
    ''')


def test_owner_transfer_retires_local_callbacks_and_adopts_without_clearing_shared_reason():
    execute(production() + '''
        _patient setVariable ["ACM_core_Lying_State",true];
        [_patient] call ACME_fnc_aiProtectionSync;
        private _mask=_patient getVariable "ace_common_effect_setHidden";
        private _sent=count _broadcasts;
        _patient setVariable ["TEST_owner",8];
        [_patient,"retire"] call ACME_fnc_aiProtectionSync;
        [_patient,"reset"] call ACME_fnc_aiProtectionSync;
        [(_patient getVariable "ace_common_effect_setHidden")==_mask && {count _broadcasts==_sent},"former owner cleared shared reason"] call _check;
        [(missionNamespace getVariable ["ACME_aiProtection_candidates",[]]) isEqualTo [] && {count _removedObjectEvents==2},"former owner retained active callbacks"] call _check;
        _machine=8;_patient setVariable ["ACME_providerLocalityEpoch",2];
        [_patient] call ACME_fnc_aiProtectionSync;
        [_patient] call ACME_fnc_aiProtectionSync;
        [count _broadcasts==_sent+1,"new owner did not replay exactly once"] call _check;
        [(_patient getVariable "ace_common_effect_setHidden")==_mask,"adoption changed aggregate reasons"] call _check;
    ''')


def test_reset_latch_survives_adoption_without_the_previous_owners_local_history():
    execute(production() + '''
        _patient setVariable ["ACE_isUnconscious",true];_patient setVariable ["ACM_core_Lying_State",true];
        [_patient] call ACME_fnc_aiProtectionSync;
        [_patient,"reset"] call ACME_fnc_aiProtectionSync;
        _patient setVariable ["TEST_owner",8];
        [_patient,"retire"] call ACME_fnc_aiProtectionSync;
        // Machine-local history is absent on the acquiring machine; the public episode latches survive.
        // SQFVM retains namespace keys assigned nil; false represents getVariable's absent-key default.
        _patient setVariable ["ACME_aiProtection_lastUnconscious",false];
        _machine=8;_patient setVariable ["ACME_providerLocalityEpoch",2];
        [_patient] call ACME_fnc_aiProtectionSync;
        [(_patient getVariable ["ACME_aiProtection_resetPending",false]) && {
            _patient getVariable ["ACME_aiProtection_awakeBlocked",false]},"adoption erased the reset episode latch"] call _check;
        _patient setVariable ["ACE_isUnconscious",false];
        [_patient] call ACME_fnc_aiProtectionSync;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo [],
            "old reset episode became hidden on the new owner"] call _check;
        [!([_patient] call ACME_fnc_aiProtectionWanted),"stale lying reactivated after reset ownership transfer"] call _check;
        _patient setVariable ["ACE_isUnconscious",true];
        [_patient] call ACME_fnc_aiProtectionSync;
        ["acme_medical_downed" in ([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1),
            "a genuine later unconscious episode was rejected"] call _check;
    ''')


def test_completed_state_restore_accepts_unconscious_episode_without_an_intermediate_awake_tick():
    execute(production() + '''
        _patient setVariable ["ACE_isUnconscious",true];_patient setVariable ["ACM_core_Lying_State",true];
        [_patient,"setHidden","ace_unconscious",true] call ace_common_fnc_statusEffect_set;
        [_patient] call ACME_fnc_aiProtectionSync;
        [_patient,"reset"] call ACME_fnc_aiProtectionSync;
        _patient setVariable ["ACME_clinicalRestoring",true];
        [_patient,"restore"] call ACME_fnc_aiProtectionSync;
        [(_patient getVariable ["ACME_aiProtection_resetPending",false]) && {
            _patient getVariable ["ACME_aiProtection_awakeBlocked",false]},"in-progress restore cleared the episode latches"] call _check;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["ace_unconscious"],
            "in-progress restore changed ACE's reason or re-added ACME early"] call _check;
        _patient setVariable ["ACME_clinicalRestoring",false];
        [_patient,"restore"] call ACME_fnc_aiProtectionSync;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["ace_unconscious","acme_medical_downed"],
            "completed unconscious restore lost ACE's reason or failed to add ACME"] call _check;
        [!(_patient getVariable ["ACME_aiProtection_resetPending",false]) && {
            !(_patient getVariable ["ACME_aiProtection_awakeBlocked",false])},"completed restore retained stale episode latches"] call _check;
    ''')


def test_healthy_reset_does_not_block_a_later_conscious_lying_episode():
    execute(production() + '''
        [_patient,"reset"] call ACME_fnc_aiProtectionSync;
        [!(_patient getVariable ["ACME_aiProtection_awakeBlocked",false]),"healthy reset latched a nonexistent lying episode"] call _check;
        [(missionNamespace getVariable ["ACME_aiProtection_candidates",[]]) isEqualTo [],"healthy reset retained a periodic worker"] call _check;
        _patient setVariable ["ACM_core_Lying_State",true];
        [_patient] call ACME_fnc_aiProtectionSync;
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo ["acme_medical_downed"],
            "a fresh conscious lying episode stayed blocked after healthy reset"] call _check;
    ''')


def test_stale_animation_callback_recomputes_the_current_pose_and_respects_owner_loss():
    execute(production() + '''
        _patient setVariable ["ACM_core_Lying_State",true];
        [_patient] call ACME_fnc_aiProtectionSync;
        private _handler=(_objectEvents select {((_x select 1) select 0)=="AnimChanged"}) select 0;
        _patient setVariable ["TEST_animation","amovppnemstpsraswrfldnon"];
        [_patient,"acm_lyingstate"] call ((_handler select 1) select 1);
        [([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo [],
            "queued old animation re-enabled protection for a combat pose"] call _check;
        _patient setVariable ["TEST_owner",8];
        _patient setVariable ["TEST_animation","acm_lyingstate"];
        private _sent=count _broadcasts;
        [_patient,"acm_lyingstate"] call ((_handler select 1) select 1);
        [count _broadcasts==_sent && {([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo []},
            "former owner's queued callback changed the shared protection"] call _check;
    ''')


def test_unready_owner_retains_unknown_inherited_effect_until_it_can_safely_clear_its_reason():
    execute(production() + '''
        _patient setVariable ["ACM_core_Lying_State",true];
        [_patient] call ACME_fnc_aiProtectionSync;
        _patient setVariable ["ACM_core_Lying_State",false];
        missionNamespace setVariable ["ace_common_statusEffects_setHidden",["ace_unconscious"]];
        [_patient] call ACME_fnc_aiProtectionSync;
        [_patient in (missionNamespace getVariable ["ACME_aiProtection_candidates",[]]),
            "unready owner abandoned an inherited unknown effect"] call _check;
        private _sent=count (_broadcasts select {(_x select 0)=="ace_common_setHidden"});
        missionNamespace setVariable ["ace_common_statusEffects_setHidden",["ace_unconscious","acme_medical_downed","third_party"]];
        [] call ACME_fnc_aiProtectionTick;
        [count (_broadcasts select {(_x select 0)=="ace_common_setHidden"})==_sent+1 && {([_patient,"setHidden"] call ace_common_fnc_statusEffect_get select 1) isEqualTo []},
            "late reason registration left a stale inherited ACME reason"] call _check;
        [(missionNamespace getVariable ["ACME_aiProtection_candidates",[]]) isEqualTo [],
            "settled healthy patient remained in the candidate worker"] call _check;
    ''')


def test_external_camouflage_overwrite_repairs_at_bounded_cadence_and_steady_ticks_are_quiet():
    execute(production() + '''
        [] call ACME_fnc_aiProtectionInit;
        _patient setVariable ["ACM_core_Lying_State",true];
        [_patient] call ACME_fnc_aiProtectionSync;
        private _sent=count _broadcasts;private _scans=_groupScans;
        for "_n" from 1 to 50 do {_clock=10+_n;[] call ACME_fnc_aiProtectionTick;};
        [count _broadcasts==_sent && {_groupScans==_scans},"steady tick broadcast or scanned groups"] call _check;
        _patient setVariable ["TEST_camouflage",0.8];
        [] call ACME_fnc_aiProtectionTick;
        [count _broadcasts==_sent+1 && {(_patient getVariable "TEST_camouflage")==0},"external overwrite was not repaired"] call _check;
        _patient setVariable ["TEST_camouflage",0.8];_clock=61;
        [] call ACME_fnc_aiProtectionTick;
        [count _broadcasts==_sent+1,"repeated overwrite caused unbounded replay"] call _check;
        _clock=65;[] call ACME_fnc_aiProtectionTick;
        [count _broadcasts==_sent+2 && {_groupScans==_scans+2},"bounded repair failed or rescanned without an overwrite"] call _check;
    ''')


@pytest.mark.parametrize('server', [False, True])
def test_reason_registration_waits_for_ace_and_is_server_owned(server):
    execute(production() + f'_machine={2 if server else 7};' + '''
        missionNamespace setVariable ["ace_common_settingsInitFinished",false];
        missionNamespace setVariable ["ace_common_statusEffects_setHidden",["ace_unconscious"]];
        [] call ACME_fnc_aiProtectionInit;[] call ACME_fnc_aiProtectionInit;
        [count _broadcasts==0,"announced before ACE was ready"] call _check;
        missionNamespace setVariable ["ace_common_settingsInitFinished",true];
        [] call ACME_fnc_aiProtectionInit;[] call ACME_fnc_aiProtectionInit;
    ''' + f'''
        [count (missionNamespace getVariable ["ace_common_statusEffects_setHidden",[]])=={2 if server else 1},"wrong machine changed reason indices"] call _check;
        [count _broadcasts=={int(server)},"ready announcement was missing, early or repeated"] call _check;
    ''' + ('' if server else '''
        missionNamespace setVariable ["ace_common_statusEffects_setHidden",["ace_unconscious","acme_medical_downed"]];
        [] call ACME_fnc_aiProtectionInit;[] call ACME_fnc_aiProtectionInit;
        [count _broadcasts==1,"late client readiness was not announced exactly once"] call _check;
    '''))


def test_late_observer_announcements_coalesce_and_replay_current_aggregate_once():
    execute(production() + '''
        [] call ACME_fnc_aiProtectionInit;
        _patient setVariable ["ACE_isUnconscious",true];
        [_patient,"setHidden","ace_unconscious",true] call ace_common_fnc_statusEffect_set;
        [_patient] call ACME_fnc_aiProtectionSync;
        private _mask=_patient getVariable "ace_common_effect_setHidden";
        private _sent=count _broadcasts;private _scans=_groupScans;
        [] call (_globalHandlers get "ACME_aiProtectionObserverReady");
        [] call (_globalHandlers get "ACME_aiProtectionObserverReady");
        _clock=11;[] call ACME_fnc_aiProtectionTick;
        [count _broadcasts==_sent,"observer storm bypassed replay cooldown"] call _check;
        _clock=15;[] call ACME_fnc_aiProtectionTick;[] call ACME_fnc_aiProtectionTick;
        [count _broadcasts==_sent+1 && {_groupScans==_scans},"observer replay duplicated or rescanned groups"] call _check;
        [((_broadcasts select _sent) select 1) isEqualTo [_patient,_mask],"replay lost aggregate ACE/ACME reasons"] call _check;
    ''')
