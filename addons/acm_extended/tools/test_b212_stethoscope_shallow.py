"""Execute directional breath gain and the production stethoscope mixer in SQF-VM.

Airway/breathing physiology, geometry, channel selection, smoothing and cadence
are production SQF. Display, cursor and audio engine commands are explicit
stand-ins; this verifies channel gains, not real Arma sound propagation.
"""
import re

import pytest

from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute, read


def linear_primitive(source):
    # This SQFVM lacks the engine's affine primitive; retain its production arguments.
    tokens = lex(source)
    pairs = matching(tokens)
    edits = []
    for index, token in enumerate(tokens[:-1]):
        if token.kind == 'ident' and token.value == 'linearConversion':
            assert tokens[index + 1].value == '['
            end = tokens[pairs[index + 1]].offset + 1
            edits.append((token.offset, end,
                          '(' + source[tokens[index + 1].offset:end] + ' call _linear)'))
    for start, end, value in reversed(edits):
        source = source[:start] + value + source[end:]
    return source


def setup():
    source = r'''
        private _linear={params ["_lo","_hi","_x","_a","_b",["_clamp",false]];
            private _f=(_x-_lo)/(_hi-_lo);if (_clamp) then {_f=(_f max 0) min 1;};_a+_f*(_b-_a)};
    '''
    for component, name in [('airway', 'getAirwayState'), ('breathing', 'getBreathingState')]:
        native = (ROOT / f'addons/{component}/functions/fnc_{name}.sqf').read_text()
        source += f'ACM_{component}_fnc_{name}={{' + adapt(linear_primitive(native)) + '};'
    for name in ('stethoscopeBreathGain', 'stethoscopeWeights'):
        source += 'ACME_fnc_' + name + '={' + adapt(linear_primitive(read(name))) + '};'
    return source


def tick_engine():
    source = read('stethoscopeTick')
    source = source.replace('disableSerialization;', '')
    source = source.replace('findDisplay 81000', 'missionNamespace')
    source = source.replace('isGameFocused', 'true')
    source = source.replace('getMousePosition', '_mousePosition')
    source = re.sub(r'_display displayCtrl (\d+)', r'\1', source)
    source = source.replace('ctrlPosition (81003)', '[0,0,11.5,22]')
    source = source.replace('_bell ctrlSetPosition ', '_bellPosition = ')
    source = source.replace('_bell ctrlCommit 0;', '')
    source = source.replace('_emitter setPosASL (AGLToASL (positionCameraToWorld [0,_distance,0]));',
                            '_emitterDistances set [_forEachIndex,_distance];')
    source = source.replace('deleteVehicle _oldSound;', '_deletedSounds pushBack _oldSound;')
    source = source.replace('_emitter say3D [_class,20,_pitch,true]',
                            '([_index,_class,_pitch] call _say3D)')
    return adapt(linear_primitive(source))


def audio_engine(source):
    """Adapt only native UI voice commands; production ownership/phase code runs."""
    source = re.sub(r'\bsoundParams\s+(_\w+)', r'(\1 call _soundParams)', source)
    source = re.sub(r'\bstopSound\s+(\([^;]+?\)|_\w+);', r'[\1] call _stopSound;', source)
    tokens = lex(source)
    pairs = matching(tokens)
    edits = []
    for index, token in enumerate(tokens[:-1]):
        if token.kind == 'ident' and token.value == 'playSoundUI':
            assert tokens[index + 1].value == '['
            end = tokens[pairs[index + 1]].offset + 1
            edits.append((token.offset, end,
                          '(' + source[tokens[index + 1].offset:end] + ' call _playSoundUI)'))
    for start, end, value in reversed(edits):
        source = source[:start] + value + source[end:]
    return adapt(source)


def audio_helpers():
    return ''.join('ACME_fnc_' + name + '={' + audio_engine(read(name)) + '};'
                   for name in ('stethoscopeAudioOwned', 'stethoscopeAudioStop', 'stethoscopeAudioUpdate'))


def mixer():
    return setup() + audio_helpers() + 'ACME_fnc_stethoscopeTick={' + tick_engine() + '};' + r'''
        private _mousePosition=[7,6.6];
        private _bellPosition=[]; private _emitterDistances=[];
        private _played=[]; private _deletedSounds=[];
        private _say3D={_played pushBack _this;objNull};
        private _playSoundUI={_played pushBack _this;-1};
        private _soundParams={[]}; private _stopSound={_deletedSounds pushBack (_this select 0);};
        ACME_fnc_clinicalEpoch={0};
        missionNamespace setVariable ["ACME_stethPatient",_patient];
        missionNamespace setVariable ["ACME_stethPressed",true];
        missionNamespace setVariable ["ACME_stethNextBeat",100];
        missionNamespace setVariable ["ACME_stethNextBreath",100];
        private _resetChannels={
            private _channels=[];
            for "_i" from 0 to 7 do {_channels pushBack [-1,"",0,1,0,0,[],-1,0,0,0];};
            missionNamespace setVariable ["ACME_stethChannels",_channels];
            missionNamespace setVariable ["ACME_stethLastFrame",_nowTime-0.1];
        };
        private _mix={
            params ["_view",["_x",15.5],["_y",1.3]];
            missionNamespace setVariable ["ACME_stethView",_view];
            _mousePosition=[_x-8.5,_y+5.3];
            missionNamespace setVariable ["ACME_stethCursor",_mousePosition];
            call _resetChannels;
            [_patient] call ACME_fnc_stethoscopeTick;
            (missionNamespace getVariable "ACME_stethChannels") apply {_x select 2}
        };
    '''


def test_normal_spontaneous_breaths_keep_existing_loudness_in_both_views():
    execute(setup() + r'''
        [([_patient] call ACME_fnc_stethoscopeBreathGain) isEqualTo [1,1],
            "normal breathing was attenuated"] call _check;
        _patient setVariable ["ACM_breathing_RespirationRate",8];
        [([_patient] call ACME_fnc_stethoscopeBreathGain) isEqualTo [1,1],
            "slow breathing alone was incorrectly classified as shallow"] call _check;
    ''')


@pytest.mark.parametrize('state', [
    '_patientAlive=false;',
    '_patient setVariable ["ACM_breathing_RespirationRate",0];',
    '_patient setVariable ["ACM_breathing_RespirationRate",0.9];',
    '_patient setVariable ["ACM_breathing_Hemothorax_Fluid",3];',
    '_patient setVariable ["ACE_isUnconscious",true];_patient setVariable ["ACM_airway_AirwayObstructionBlood_State",1];',
    '_patient setVariable ["ACE_isUnconscious",true];_patient setVariable ["ACM_airway_AirwayCollapse_State",3];',
    '_patient setVariable ["ACME_vent_driving",true];_patient setVariable ["ACME_vent_vte",0];',
])
def test_zero_airflow_or_absent_breaths_cannot_be_made_audible_from_the_back(state):
    execute(setup() + state + r'''
        [([_patient] call ACME_fnc_stethoscopeBreathGain) isEqualTo [0,0],
            "posterior listening created sounds without airflow"] call _check;
    ''')


@pytest.mark.parametrize('field,values', [
    ('ACM_breathing_Pneumothorax_State', [1,3,6,8]),
    ('ACM_breathing_Hemothorax_Fluid', [.4,.7,1.0,1.3]),
    ('ACM_CBRN_BreathingAbility_State', [.9,.7,.5,.3]),
])
def test_native_restriction_grades_front_more_than_back_without_boosting_either(field, values):
    execute(setup() + f'''
        private _previous=[1,1];
        {{
            _patient setVariable ["{field}",_x];
            private _current=[_patient] call ACME_fnc_stethoscopeBreathGain;
            [(_current select 0)<(_current select 1),"front was not harder to hear"] call _check;
            [(_current select 0)<=(_previous select 0) && {{(_current select 1)<=(_previous select 1)}},
                "greater shallowness made breath sounds louder"] call _check;
            [(_current select 0)>=0 && {{(_current select 1)<=1}},"gain exceeded normal limits"] call _check;
            _previous=_current;
        }} forEach {values};
    ''')


@pytest.mark.parametrize('collapse', [0,1,2])
def test_unprotected_unconscious_airway_attenuates_front_more_than_back(collapse):
    execute(setup() + f'''
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACM_airway_AirwayCollapse_State",{collapse}];
        private _gains=[_patient] call ACME_fnc_stethoscopeBreathGain;
        [(_gains select 0)>0 && {{(_gains select 0)<(_gains select 1)}} && {{(_gains select 1)<1}},
            "native partial airway obstruction did not grade listening difficulty"] call _check;
    ''')


def test_established_airway_and_adequate_ventilation_do_not_use_paralysis_as_shallowness():
    execute(setup() + r'''
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACME_roc_paralyzed",true];
        _patient setVariable ["ACME_resp_neuralRR",0];
        _patient setVariable ["ACM_airway_AirwayCollapse_State",3];
        _patient setVariable ["ACME_ETT_Inserted",true];
        _patient setVariable ["ACME_vent_driving",true];
        _patient setVariable ["ACME_vent_vte",500];
        [([_patient] call ACME_fnc_stethoscopeBreathGain) isEqualTo [1,1],
            "adequate delivered breaths were attenuated by paralysis"] call _check;
        _patient setVariable ["ACME_vent_vte",150];
        private _gains=[_patient] call ACME_fnc_stethoscopeBreathGain;
        [abs ((_gains select 0)-0.25)<0.0001 && {abs ((_gains select 1)-0.70)<0.0001},
            "shallow transmission bounds changed"] call _check;
        _patient setVariable ["ACME_vent_vte",25];
        private _tiny=[_patient] call ACME_fnc_stethoscopeBreathGain;
        [(_tiny select 0)<(_gains select 0) && {(_tiny select 1)<(_gains select 1)},
            "near-zero tidal volume retained a positive floor"] call _check;
    ''')


@pytest.mark.parametrize('view,expected_side', [('front',0),('back',1)])
def test_full_mixer_preserves_anatomical_lung_and_cardiac_channels(view, expected_side):
    execute(mixer() + f'''
        private _normal=["{view}"] call _mix;
        _patient setVariable ["ACM_CBRN_BreathingAbility_State",0.3];
        _nowTime=_nowTime+1;
        private _shallow=["{view}"] call _mix;
        private _expected=[0.25,0.7] select {expected_side};
        [(_normal select {expected_side})>0,"listening point missed its anatomical lung"] call _check;
        [abs ((_shallow select {expected_side})/(_normal select {expected_side})-_expected)<0.0001,
            "full mixer ignored directional attenuation"] call _check;
        [(_shallow select {1-expected_side})==0,"gain created sound in the opposite lung"] call _check;
        [(_shallow select 2)==(_normal select 2),"breath depth altered cardiac gain"] call _check;
    ''')


def test_flipping_within_the_cached_interval_uses_the_new_view_immediately():
    execute(mixer() + r'''
        _patient setVariable ["ACM_CBRN_BreathingAbility_State",0.3];
        ["front"] call _mix;
        private _frontCached=missionNamespace getVariable "ACME_stethBreathGains";
        private _rear=["back",25,1.5] call _mix;
        private _weights=[25,1.5,"back"] call ACME_fnc_stethoscopeWeights;
        private _smooth=1-exp (-0.1/0.08);
        [abs ((_rear select 0)/((_weights select 0)*_smooth)-0.7)<0.0001,
            "back view reused the anterior cached gain"] call _check;
        [(missionNamespace getVariable "ACME_stethBreathGains") isEqualTo _frontCached,
            "flipping unnecessarily rebuilt the gain cache"] call _check;
        [count _events==1,"flipping dispatched another owner refresh inside the interval"] call _check;
    ''')


@pytest.mark.parametrize('view,x', [('front',13),('back',27)])
def test_unilateral_hemo_crackles_are_attenuated_without_crossing_to_the_other_lung(view, x):
    execute(mixer() + f'''
        _patient setVariable ["ACM_breathing_Stethoscope_LungState",[2,0]];
        _patient setVariable ["ACM_breathing_Hemothorax_Fluid",1.2];
        private _gains=["{view}",{x},10] call _mix;
        [(_gains select 3)>0,"existing basal crackles were lost"] call _check;
        [(_gains select 1)==0 && {{(_gains select 4)==0}},"unilateral finding leaked into the other lung"] call _check;
        _patient setVariable ["ACM_breathing_RespirationRate",0];
        private _silent=["{view}",{x},10] call _mix;
        [(_silent select 0)==0 && {{(_silent select 1)==0}} && {{(_silent select 3)==0}} && {{(_silent select 4)==0}},
            "cached depth or basal crackles bypassed immediate apnea silence"] call _check;
    ''')


def test_released_bell_remains_silent_even_with_a_cached_rear_gain():
    execute(mixer() + r'''
        ["back"] call _mix;
        missionNamespace setVariable ["ACME_stethPressed",false];
        private _silent=["back"] call _mix;
        [(_silent findIf {_x != 0})==-1,"released bell still produced audio"] call _check;
    ''')
