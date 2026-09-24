"""Run repeated seal burps and real Carry Assist input callbacks in SQF-VM.

The engine clock, display events, animation and physiology effects are simulated.
The production wheel handlers, ownership checks, transactions and cancellation paths run.
"""
import re

import pytest

from test_menu_death_lifecycle import ROOT, adapt, core, execute, read


def burp_source(name):
    source = read(name).replace('serverTime', '_serverNow').replace('local _patient', '_patientLocal')
    # Keep the record's clock-domain tag a string, unchanged by the command mock.
    source = source.replace('"_serverNow"', '"serverTime"')
    source = re.sub(r'\bfinite _\w+', 'true', source)
    source = re.sub(r'(setVariable \[[^;\n]*,[^;\n]*),\s*(?:true|false)(\])', r'\1\2', source)
    return adapt(source)


def burp_setup(kind):
    code = '''
        private _serverNow = 100;
        private _patientLocal = true;
        private _epoch = 1;
        private _effects = 0;
        private _logs = 0;
        private _burpRequests = 0;
        private _gestures = 0;
        ACME_fnc_clinicalEpoch = {_epoch};
        ACME_fnc_ptxTreat = {_effects = _effects + 1;};
        ACME_fnc_chestSealLogOnce = {_logs = _logs + 1;};
        ACME_fnc_chestSealSealAt = {0};
        ACME_fnc_thoraSealAt = {true};
        ACME_fnc_procedureAllowed = {true};
        ACME_fnc_chestSealSnd = {};
        ACME_fnc_chestSealRender = {};
        ACME_fnc_thoraRenderTube = {};
        ACM_breathing_fnc_updateLungState = {};
        uiNamespace setVariable ["ACME_CS_Patient", _patient];
        uiNamespace setVariable ["ACME_CS_Medic", _medic];
        uiNamespace setVariable ["ACME_Thora_Patient", _patient];
        uiNamespace setVariable ["ACME_Thora_Medic", _medic];
        _patient setVariable ["ACME_thora_incision_right", [0,0,0]];
        _patient setVariable ["ACME_thora_open_right", "sealed"];
        _patient setVariable ["ACME_thora_sealed_right", true];
    '''
    for name in ['chestSealBurpReady', 'chestSealBurp', 'thoraAftercareLocal', 'chestSealScroll', 'thoraSealScroll']:
        code += f'ACME_fnc_{name} = {{' + burp_source(name) + '};\n'
    code += '''
        ACME_fnc_ownerDispatch = {
            if ((_this select 1) == "thoraAftercare") then {
                _burpRequests = _burpRequests + 1;
                (_this select 2) call ACME_fnc_thoraAftercareLocal;
            } else {_gestures = _gestures + 1;};
        };
        private _burp = ACME_fnc_chestSealBurp;
        ACME_fnc_chestSealBurp = {_burpRequests = _burpRequests + 1; _this call _burp;};
    '''
    # Burping remains inside the existing chest workspace/aftercare theatre. medic3 is reserved
    # for actual seal placement, so neither burp path requests a separate placement gesture.
    code += 'private _gesturePerBurp = 0;'
    code += f'private _wheel = {{[objNull, _this select 0] call ACME_fnc_{"chestSealScroll" if kind == "trauma" else "thoraSealScroll"};}};'
    code += 'private _lift = {for "_i" from 1 to 5 do {_this call _wheel;};};'
    return code


@pytest.mark.parametrize('kind', ['trauma', 'thora'])
@pytest.mark.parametrize('direction', [-1, 1])
def test_same_corner_can_burp_repeatedly_without_advancing_time(kind, direction):
    execute(burp_setup(kind) + f'private _direction = {direction};' + '''
        [_direction] call _lift;
        [_logs == 1 && {_effects == 1} && {_gestures == _gesturePerBurp},"first burp failed"] call _check;
        for "_i" from 1 to 4 do {[_direction] call _wheel;};
        [_logs == 1 && {_burpRequests == 1},"partial peel repeated treatment"] call _check;
        [_direction] call _wheel;
        [_logs == 2 && {_effects == 2} && {_gestures == (2 * _gesturePerBurp)},"immediate second burp remained blocked"] call _check;
        [_direction] call _lift;
        [_logs == 3 && {_burpRequests == 3},"immediate third cycle failed"] call _check;
    ''')


@pytest.mark.parametrize('kind', ['trauma', 'thora'])
def test_can_lower_seal_then_immediately_burp_again(kind):
    frame = '(uiNamespace getVariable ["ACME_CS_BurpFrame",-1])' if kind == 'trauma' else '((uiNamespace getVariable ["ACME_Thora_Burp",[]]) select 1)'
    execute(burp_setup(kind) + '''
        [1] call _lift;
        [-1] call _lift;
    ''' + f'[{frame} == 0,"could not lay seal flat"] call _check;' + '''
        [_logs == 1,"lowering repeated treatment"] call _check;
        [1] call _lift;
        [_logs == 2 && {_effects == 2},"flat seal could not burp immediately"] call _check;
    ''')


def test_both_seal_types_and_providers_can_burp_without_waiting():
    execute(burp_setup('trauma') + '''
        [_medic,_patient] call ACME_fnc_chestSealBurp;
        [_patient,missionNamespace,"right","burp",1] call ACME_fnc_thoraAftercareLocal;
        [_logs == 2 && {_effects == 2},"other seal/provider was blocked"] call _check;
        [_patient,missionNamespace,"right","burp",1] call ACME_fnc_thoraAftercareLocal;
        [_medic,_patient] call ACME_fnc_chestSealBurp;
        [_logs == 4 && {_effects == 4},"repeated treatment was blocked"] call _check;
    ''')


def test_readiness_ignores_clocks_but_still_requires_owner_for_treatment():
    execute(burp_setup('trauma') + '''
        CBA_missionTime = -500;
        [_medic,_patient] call ACME_fnc_chestSealBurp;
        _patientLocal = false;
        CBA_missionTime = 800;
        [[_patient] call ACME_fnc_chestSealBurpReady,"client could not peel seal"] call _check;
        [!([_patient,true] call ACME_fnc_chestSealBurpReady),"non-owner could apply treatment"] call _check;
        _patientLocal = true;
        [[_patient,true] call ACME_fnc_chestSealBurpReady,"owner could not repeat immediately"] call _check;
    ''')


@pytest.mark.parametrize('kind', ['trauma', 'thora'])
def test_corpse_seals_remain_reusable_without_restarting_physiology(kind):
    execute(burp_setup(kind) + '''
        _patientAlive = false;
        [1] call _lift;
        [1] call _lift;
        [_logs == 2 && {_gestures == (2 * _gesturePerBurp)},"corpse seal became unusable"] call _check;
        [_effects == 0,"burp restarted corpse physiology"] call _check;
    ''')


def test_existing_cooldown_record_cannot_block_repeated_burps():
    execute(burp_setup('trauma') + '''
        _patient setVariable ["ACME_CS_burpCooldown", [1, 10000, "serverTime"]];
        [1] call _lift;
        [1] call _lift;
        [_logs == 2 && {_effects == 2},"old cooldown record blocked a burp"] call _check;
    ''')


def carry_setup():
    source = (ROOT / 'addons/core/functions/fnc_beginCarryAssist.sqf').read_text()
    source = source.replace('findDisplay 46', '_mainDisplayMock')
    source = source.replace('_main displayAddEventHandler', 'call _addDisplayEvent')
    # Convert the binary engine command into a function without changing callback code.
    source = source.replace('call _addDisplayEvent ["MouseButtonDown", _mouseCode]', '["MouseButtonDown", _mouseCode] call _addDisplayEvent')
    source = source.replace('call _addDisplayEvent ["KeyDown", _escapeCode]', '["KeyDown", _escapeCode] call _addDisplayEvent')
    source = source.replace('_oldDisplay displayRemoveEventHandler [_event, _id];', '[_event, _id] call _removeDisplayEvent;')
    source = source.replace('_main displayRemoveEventHandler [_event, _id];', '[_event, _id] call _removeDisplayEvent;')
    return '''
        private _mainDisplayMock = missionNamespace;
        private _displayEvents = [];
        private _removedDisplayEvents = [];
        private _addDisplayEvent = {_displayEvents pushBack _this; count _displayEvents - 1};
        private _removeDisplayEvent = {_removedDisplayEvents pushBack _this;};
    ''' + 'ACM_core_fnc_continuousHoldRelease = {' + core('continuousHoldRelease') + '}; ACM_core_fnc_beginContinuousAction = {' + core('beginContinuousAction') + '}; private _start = {' + adapt(source) + '};' + '''
        private _input = {
            params ["_event","_key"];
            private _match = _displayEvents select {_x select 0 == _event};
            [missionNamespace,_key] call ((_match select (count _match - 1)) select 1)
        };
        private _freed = {
            [!ACM_core_ContinuousAction_Active,"continuous gate stuck"] call _check;
            [!(_patient getVariable ["ACM_core_CarryAssist_State",true]),"patient carry hold stuck"] call _check;
            [(_patient getVariable ["ACM_core_CarryAssist_State_Session",[]]) isEqualTo [],"session not released"] call _check;
            [_stanceFreed && {(_moves select (count _moves - 1)) == "AmovPknlMstpSnonWnonDnon"},"movable crouch not requested"] call _check;
        };
    '''


@pytest.mark.parametrize('event,key', [('MouseButtonDown', 0), ('KeyDown', 1)])
def test_actual_carry_cancel_input_releases_and_allows_restart(event, key):
    execute(carry_setup() + f'private _event = "{event}"; private _key = {key};' + '''
        [_medic,_patient] call _start;
        [[_event,_key] call _input,"cancel input not consumed"] call _check;
        call _tick; call _freed;
        [count _removed == 2 && {count _removedDisplayEvents == 2},"input cleanup incomplete"] call _check;
        [_medic,_patient] call _start;
        [[_event,_key] call _input,"repeat cancellation failed"] call _check;
        call _tick; call _freed;
    ''')


def test_escape_is_consumed_even_if_cba_cancel_ran_first():
    execute(carry_setup() + '''
        [_medic,_patient] call _start;
        ACM_core_ContinuousAction_Active = false;
        [["KeyDown",1] call _input,"Escape leaked to pause menu after CBA cancel"] call _check;
        call _tick; call _freed;
    ''')


def test_old_carry_mouse_callback_cannot_cancel_new_session():
    execute(carry_setup() + '''
        [_medic,_patient] call _start;
        private _old = (_displayEvents select 0) select 1;
        ["MouseButtonDown",0] call _input; call _tick;
        [_medic,_patient] call _start;
        [!([missionNamespace,0] call _old),"old callback consumed new input"] call _check;
        [ACM_core_ContinuousAction_Active,"old callback cancelled new session"] call _check;
        [!( ["MouseButtonDown",1] call _input),"right click cancelled carry assist"] call _check;
        [!(["KeyDown",2] call _input),"unrelated key cancelled carry assist"] call _check;
        ["KeyDown",1] call _input; call _tick; call _freed;
    ''')


def test_cba_cancel_still_works_without_main_display():
    execute(carry_setup() + '''
        _mainDisplayMock = objNull;
        [_medic,_patient] call _start;
        private _id = ACM_core_CarryAssistCancel_MouseID;
        private _key = (_keys select {_x select 0 == _id}) select 0;
        call (_key select 1);
        call _tick; call _freed;
    ''')
