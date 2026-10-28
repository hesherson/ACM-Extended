"""Execute actual transfusion observer registrations and their return values.

Arma owns pointer dispatch, native controls, and default config actions. The
boundary below records production registrations, invokes every callback in the
documented reverse order, and invokes a real extracted config action once when
the observers permit it. This is an event-contract simulation, not an in-game
pointer-routing test. In particular it does not assume a true return stops the
remaining scripted handlers.
"""
import re

import pytest

from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute, read


CANCEL_IDS = (86006, 86007, 86146, 86120, 86147, 86134, 86148,
              86132, 86133, 86149, 86131, 86142, 86950, 86951)
DISMISS_IDS = (86007, 86146, 86120, 86147, 86134, 86148, 86132, 86133, 86149)
CONFIG_CLASSES = {
    86006: 'StopTransfusionButton',
    86007: 'MoveBagButton',
    86146: 'ACME_PullBagButton',
    86120: 'ACME_InjectMedicationBagButton',
    86147: 'ACME_InfuseBagButton',
    86134: 'ACME_HangBagButton',
    86148: 'ACME_PressureInfuserButton',
    86132: 'ACME_MoveInfusionButton',
    86133: 'ACME_RemoveInfusionButton',
    86149: 'ACME_InfusionPressureButton',
    86131: 'ACME_AdjustInfusionButton',
    86142: 'ACME_YTubingButton',
}


def observers():
    source = read('layoutTransfusionMenu')
    dismiss = source[source.index('// Closing a local popover'):source.index(
        '_display displayAddEventHandler ["Unload"')]
    cancel = source[source.index('// An unrelated treatment cancels'):source.index(
        '// Returning from Inventory')]
    # Only engine control lookup, EH installation and parent-display lookup are
    # adapted. Distinct display/control stand-ins avoid conflating their types.
    source = dismiss + cancel
    source = source.replace('_display displayCtrl _x',
                            '([objNull,uiNamespace] select (_x == _targetIDC))')
    source = source.replace('_ctrl ctrlAddEventHandler', '_buttonEvents pushBack')
    source = source.replace('ctrlParent _ctrl', 'parsingNamespace')
    return adapt(source)


def setup(target_id, pending=True):
    return f'private _targetIDC={target_id};' + r'''
        private _display=parsingNamespace;
        private _button=uiNamespace;
        private _buttonEvents=[];
        private _deferred=[];
        private _nativeCalls=[];
        private _navCalls=[];
        private _reflows=0;
        private _schedulerReturn=true;
        private _dispatchOrder=[];
        CBA_fnc_execNextFrame={_dispatchOrder pushBack "dismiss";_deferred pushBack +_this;_schedulerReturn};
        ACME_fnc_layoutTransfusionMenu={_reflows=_reflows+1;true};
        ACME_fnc_skPageNavigate={_dispatchOrder pushBack "navigate";_navCalls pushBack +_this;false};
        _display setVariable ["ACME_txActionMenu","bag"];
        uiNamespace setVariable ["ACME_lineWarmerConfirm",["pending"]];
    ''' + ('ACME_piggybackPending=["funded intent"];' if pending else
           'ACME_piggybackPending=[];') + \
        'private _productionWorkflow={' + adapt(read('piggybackWorkflow')) + '};' + \
        'ACME_fnc_piggybackWorkflow={_dispatchOrder pushBack "cancel";_this call _productionWorkflow;};'


def class_body(source, name):
    tokens = lex(source)
    pairs = matching(tokens)
    for i, token in enumerate(tokens[:-2]):
        if token.value != 'class' or tokens[i + 1].value != name:
            continue
        opening = i + 2
        while tokens[opening].value not in (';', '{'):
            opening += 1
        if tokens[opening].value == '{':
            return source[tokens[opening].offset + 1:tokens[pairs[opening]].offset]
    raise AssertionError(f'missing concrete config class {name}')


def config_action(target_id):
    native = target_id in (86006, 86007)
    path = (ROOT / 'addons/circulation/TransfusionMenu_Dialog.hpp' if native else
            ROOT / 'addons/acm_extended/config.cpp')
    body = class_body(path.read_text(), CONFIG_CLASSES[target_id])
    if native:
        action = re.search(r'\baction\s*=\s*QUOTE\((.*?)\);', body).group(1)
        return adapt(action, 'circulation')
    return re.search(r'\baction\s*=\s*"([^"]*)"', body).group(1)


def dispatch(default_action=''):
    # The native default-action decision is an explicit engine boundary. Run
    # ALL scripted handlers, never invent a short-circuit on a true observer.
    return r'''
        private _reversed=+_buttonEvents;
        reverse _reversed;
        private _allowDefault=true;
        {
            private _returned=[_button] call (_x select 1);
            [_returned isEqualTo false,"auxiliary ButtonClick claimed the action"]call _check;
            if (_returned isEqualTo true) then {_allowDefault=false;};
        }forEach _reversed;
    ''' + (f'if (_allowDefault) then {{[_button]call {{{default_action}}};}};' if default_action else '')


@pytest.mark.parametrize('target_id', CANCEL_IDS)
@pytest.mark.parametrize('pending', (False, True))
def test_actual_cleanup_registrations_clear_intent_and_never_claim_click(target_id, pending):
    execute(setup(target_id, pending) + observers() + dispatch() + f'''
        [count _buttonEvents=={1 + (target_id in DISMISS_IDS)},"wrong actual observer registrations"]call _check;
        [ACME_piggybackPending isEqualTo [],"cancel observer left piggyback intent"]call _check;
        [(uiNamespace getVariable "ACME_lineWarmerConfirm")isEqualTo [],"cancel observer left warmer confirmation"]call _check;
        [(uiNamespace getVariable "ACME_preparedRowSig")=="__force__","production cancel branch did not run"]call _check;
        [count _nativeCalls==0 && {{count _navCalls==0}},"observer dispatched a treatment or navigation"]call _check;
    ''')


@pytest.mark.parametrize('target_id', tuple(CONFIG_CLASSES))
def test_actual_config_action_runs_once_after_reverse_order_observers(target_id):
    action = config_action(target_id)
    functions = re.findall(r'\b(?:ACME|ACM_circulation)_fnc_\w+', action)
    assert len(functions) == 1, action
    stub = functions[0] + '={_dispatchOrder pushBack "action";_nativeCalls pushBack [_targetIDC,+_this];};'
    expected = '["cancel","dismiss","action"]' if target_id in DISMISS_IDS else '["cancel","action"]'
    execute(setup(target_id) + stub + observers() + dispatch(action) + r'''
        [count _nativeCalls==1,"native config action was suppressed or duplicated"]call _check;
        [(_nativeCalls select 0)select 0==_targetIDC,"wrong config action dispatched"]call _check;
        [count _navCalls==0,"config treatment navigated unexpectedly"]call _check;
        [count _deferred==count _buttonEvents-1,"dismiss observer was not deferred"]call _check;
        [(_display getVariable "ACME_txActionMenu")=="bag","observer dismissed before config action"]call _check;
    ''' + f'[_dispatchOrder isEqualTo {expected},"observer/default action ordering changed"]call _check;')


@pytest.mark.parametrize('target_id', DISMISS_IDS)
@pytest.mark.parametrize('scheduler_return', ('true', '23'))
def test_dismissal_ignores_scheduler_return_and_reflows_only_after_action(target_id, scheduler_return):
    execute(setup(target_id) + f'_schedulerReturn={scheduler_return};' + observers() + dispatch() + r'''
        [count _deferred==1 && {_reflows==0},"dismissal was not deferred exactly once"]call _check;
        private _queued=_deferred select 0;
        private _result=(_queued select 1)call (_queued select 0);
        [_result isEqualTo false,"deferred observer leaked a helper return"]call _check;
        [_reflows==1 && {(_display getVariable "ACME_txActionMenu")==""},"dismissal did not reflow captured display"]call _check;
    ''')


def navigation_action(direction):
    source = (ROOT / 'addons/circulation/functions/fnc_openTransfusionMenu.sqf').read_text()
    name = '_lb' if direction == 'left' else '_rb'
    pattern = re.escape(name) + r' buttonSetAction "([^"]*)";'
    action = re.search(pattern, source).group(1)
    assert not re.search(re.escape(name) + r' ctrlAddEventHandler \["ButtonClick"', source), \
        'navigation has both a default action and a primary click handler'
    config = (ROOT / 'addons/acm_extended/config.cpp').read_text()
    for class_name in ('ACME_TX_PageButton', 'ACME_SK_PulseButton', 'ACME_SK_StyledButton'):
        inherited = re.search(r'\baction\s*=\s*"([^"]*)"', class_body(config, class_name))
        assert inherited is None or inherited.group(1) == '', \
            'navigation also inherits a nonempty config action'
    return action


@pytest.mark.parametrize('target_id,direction', ((86950, 'left'), (86951, 'right')))
def test_actual_navigation_handler_still_routes_once_with_cleanup(target_id, direction):
    # The current dynamic buttons use the same native default-action boundary
    # as config buttons. buttonSetAction executes with an empty-string _this;
    # the literal direction must be sufficient, without opener-local captures.
    action = navigation_action(direction)
    execute(setup(target_id) + observers() + dispatch() + r'''
        [count _buttonEvents==1 && {count _navCalls==0},"observer replayed navigation"]call _check;
    ''' + f'if (_allowDefault) then {{""call {{{action}}};}};' + f'''
        [_navCalls isEqualTo [["{direction}"]],"native page handler did not route exactly once"]call _check;
        [_dispatchOrder isEqualTo ["cancel","navigate"],"navigation did not follow passive cleanup"]call _check;
        [count _nativeCalls==0 && {{count _deferred==0}},"navigation gained another treatment or dismissal"]call _check;
    ''')


def test_deferred_dismissal_tolerates_destroyed_display_without_claiming_input():
    execute(setup(86148) + observers() + dispatch() + r'''
        private _queued=_deferred select 0;
        private _result=[objNull]call (_queued select 0);
        [_result isEqualTo false && {_reflows==0},"closed display dismissal claimed input or reflowed"]call _check;
    ''')
