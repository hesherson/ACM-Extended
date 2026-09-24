"""Run the actual registration prefix and full Narc Box teardown.

Namespace displays and recorded delegate calls do not simulate engine destruction,
compound inventory writes, real leases, rendering or persistent medication delivery.
"""
import re
import pytest
from test_menu_death_lifecycle import adapt, execute, ROOT
from test_bounded_normal_push_lifetime import setup as push_setup

F = ROOT / 'addons/acm_extended/functions'


def registration():
    text = (F / 'fn_skInject.sqf').read_text().split("// Mirror ACM's medication list", 1)[0]
    text = text.replace('findDisplay 84000', '_drawDisplay')
    text = text.replace('(_display displayCtrl 84130)', '_sizeControl')
    old = '_display displayAddEventHandler ["Unload", {_this call ACME_fnc_skClose}];'
    assert text.count(old) == 1
    text = text.replace(old, '_registrations pushBack [_display, {_this call ACME_fnc_skClose}];')
    return 'private _register = {' + adapt(text) + '};\n'


def setup():
    return push_setup() + '''
        private _registrations=[]; private _effects=[]; private _sizeControl=objNull;
        ACME_fnc_uiCanvas={[0,0,1,1]};
        ACME_fnc_skPendingTagCommit={_effects pushBack ["tag",+_this];};
        ACME_fnc_skCompoundCommit={_effects pushBack ["compound",+_this];};
        ACME_fnc_vialLeaseRelease={_effects pushBack ["lease",+_this];};
        ACME_fnc_restorePausedFlow={_effects pushBack ["flow",+_this];};
        ACME_fnc_restoreMedicationList={_effects pushBack ["list",+_this];};
        ACME_fnc_reopenMedicalMenu={_effects pushBack ["medical",+_this];};
        ACME_fnc_reopenTransfusion={_effects pushBack ["transfusion",+_this];};
        private _seed={
            uiNamespace setVariable ["ACME_SK_WasteStage","compound"];
            uiNamespace setVariable ["ACME_SK_WasteMoving",true];
            uiNamespace setVariable ["ACME_SK_TagEditMode",true];
            uiNamespace setVariable ["ACME_SK_CarouselZoneHover",true];
            uiNamespace setVariable ["ACME_SK_PendingInjection",["rightleg",2,"vascular"]];
            uiNamespace setVariable ["ACME_SK_DiscardArmedId","new-id"];
            uiNamespace setVariable ["ACME_SK_WastePFH",11];
            uiNamespace setVariable ["ACME_SK_PulsePFH",12];
            uiNamespace setVariable ["ACME_SK_suppressReturn",true];
            missionNamespace setVariable ["ACME_infusion_pendingContext",["new-bag"]];
            missionNamespace setVariable ["ACME_infusion_bagTally",["new-tally"]];
            ace_medical_gui_pendingReopen=true;
        };
        private _snapshot={[
            uiNamespace getVariable ["ACME_SK_WasteStage",""],
            uiNamespace getVariable ["ACME_SK_WasteMoving",false],
            uiNamespace getVariable ["ACME_SK_TagEditMode",false],
            uiNamespace getVariable ["ACME_SK_CarouselZoneHover",false],
            uiNamespace getVariable ["ACME_SK_PendingInjection",[]],
            uiNamespace getVariable ["ACME_SK_DiscardArmedId",""],
            uiNamespace getVariable ["ACME_SK_WastePFH",-1],
            uiNamespace getVariable ["ACME_SK_PulsePFH",-1],
            uiNamespace getVariable ["ACME_SK_suppressReturn",false],
            missionNamespace getVariable ["ACME_infusion_pendingContext",[]],
            missionNamespace getVariable ["ACME_infusion_bagTally",[]],
            ace_medical_gui_pendingReopen
        ]};
    ''' + registration() + '''call _register;
        private _original=_drawDisplay;
        private _closeOriginal={[_original,2] call ((_registrations select 0) select 1);};
    '''


@pytest.mark.parametrize('new_closed',[False,True])
@pytest.mark.parametrize('new_context',['plain','infusion','switch'])
def test_old_unload_preserves_new_workspace_and_calls_no_delegates(new_closed,new_context):
    prepare = {'plain':'', 'infusion':'missionNamespace setVariable ["ACME_infusion_pendingContext",["active",_patient,"leftarm"]];',
               'switch':'uiNamespace setVariable ["ACME_SK_RestoreMouse",[0.2,0.3]];'}[new_context]
    execute(setup()+prepare+'''
        _drawDisplay=parsingNamespace; call _register;
    '''+('[_drawDisplay] call ACME_fnc_skClose;' if new_closed else '')+'''
        call _seed; private _before=call _snapshot;
        _effects=[];_sounds=[];_removed=[];
        call _closeOriginal;
        [(call _snapshot) isEqualTo _before,"stale close rewrote current workspace"] call _check;
        [count _effects==0 && {count _removed==0} && {count _sounds==0},"stale close dispatched cleanup"] call _check;
    ''')


@pytest.mark.parametrize('repeat',[False,True])
@pytest.mark.parametrize('mode',['plain','compound','infusion','switch','suppressed','hardcore'])
def test_current_teardown_retains_exact_routing_and_duplicate_close_does_nothing(mode,repeat):
    extra = {
        'plain':'',
        'compound':'uiNamespace setVariable ["ACME_SK_WasteStage","compound"];',
        'infusion':'_drawDisplay setVariable ["ACME_SK_Return",[_medic,_patient,"leftarm",true,1]]; uiNamespace setVariable ["ACME_SK_WasteStage","compound"];',
        'switch':'uiNamespace setVariable ["ACME_SK_RestoreMouse",[0.2,0.3]]; uiNamespace setVariable ["ACME_SK_WasteStage","compound"];',
        'suppressed':'uiNamespace setVariable ["ACME_SK_suppressReturn",true];',
        'hardcore':'missionNamespace setVariable ["ACME_HCMedPushJob",createHashMapFromArray [["flowing",true]]]; uiNamespace setVariable ["ACME_SK_InjectionBusy",true];uiNamespace setVariable ["ACME_SK_CarouselBusy",true];',
    }[mode]
    expected = ('["tag","compound","lease","flow","list","medical"]' if mode=='compound' else
                '["lease"]' if mode=='switch' else
                '["lease","flow","list","transfusion"]' if mode=='infusion' else
                '["lease","flow","list"]' if mode in ['hardcore','suppressed'] else
                '["lease","flow","list","medical"]')
    execute(setup()+extra+'''
        uiNamespace setVariable ["ACME_SK_WastePFH",11];
        uiNamespace setVariable ["ACME_SK_PulsePFH",12];
        call _closeOriginal;
    '''+f'''
        [(_effects apply {{_x select 0}}) isEqualTo {expected},"current routing/commit dispatch changed"] call _check;
        [_removed isEqualTo [11,12],"current handler retirement changed"] call _check;
        [count _sounds=={0 if mode=='switch' else 1},"close sound changed"] call _check;
    '''+('''
        [uiNamespace getVariable ["ACME_SK_InjectionBusy",false],"persistent push unlocked"] call _check;
        [uiNamespace getVariable ["ACME_SK_CarouselBusy",false],"persistent carousel unlocked"] call _check;
        [count (missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap])==1,"persistent job changed"] call _check;
    ''' if mode=='hardcore' else '')+('''
        private _priorEffects=+_effects; private _priorRemoved=+_removed;private _priorSounds=+_sounds;
        call _seed; private _before=call _snapshot;
        call _closeOriginal;
        [(call _snapshot) isEqualTo _before,"duplicate close changed workspace"] call _check;
        [_effects isEqualTo _priorEffects && {_removed isEqualTo _priorRemoved} && {_sounds isEqualTo _priorSounds},"duplicate close dispatched cleanup"] call _check;
    ''' if repeat else ''))


@pytest.mark.parametrize('boundary',['start','commit'])
def test_late_old_unload_does_not_clear_target_or_handlers_of_new_normal_push(boundary):
    execute(setup()+'''
        _drawDisplay=parsingNamespace; call _register;
        call ACME_fnc_skConfirmInjection;
    '''+('0 call _runWait;' if boundary=='commit' else '')+'''
        private _job=+(uiNamespace getVariable ["ACME_SK_NormalPush",[]]);
        private _pfh=uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1];
        private _pending=+(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]);
        uiNamespace setVariable ["ACME_SK_WastePFH",11];
        uiNamespace setVariable ["ACME_SK_PulsePFH",12];
        call _closeOriginal;
        [(uiNamespace getVariable ["ACME_SK_NormalPush",[]]) isEqualTo _job,"new job changed"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PendingInjection",[]]) isEqualTo _pending,"new target cleared"] call _check;
        [uiNamespace getVariable ["ACME_SK_InjectionBusy",false],"new injection lock lost"] call _check;
        [(uiNamespace getVariable ["ACME_SK_PushAnimPFH",-1])==_pfh,"new plunger handle lost"] call _check;
        [count _removed==0,"new handler retired by old close"] call _check;
    '''+('' if boundary=='commit' else '0 call _runWait;')+'''
        1 call _runWait;
        [count _delivered==1,"new current push lost normal completion"] call _check;
    ''')


def test_registration_is_once_per_display_and_uninitialized_close_is_inert():
    execute(setup()+'''
        private _epoch=uiNamespace getVariable ["ACME_SK_CloseEpoch",0];
        _sizeControl=84130;call _register;
        [count _registrations==1,"duplicate Unload registration"] call _check;
        [(uiNamespace getVariable ["ACME_SK_CloseEpoch",0])==_epoch,"duplicate injection advanced owner"] call _check;
        call _seed;private _before=call _snapshot;
        [parsingNamespace] call ACME_fnc_skClose;
        [(call _snapshot) isEqualTo _before && {count _effects==0},"unregistered close changed workspace"] call _check;
    ''')


def test_reentrant_compound_delegate_cannot_run_unload_twice():
    execute(setup()+'''
        uiNamespace setVariable ["ACME_SK_WasteStage","compound"];
        private _commitsCount=0;
        ACME_fnc_skCompoundCommit={_commitsCount=_commitsCount+1; if (_commitsCount==1) then {call _closeOriginal;};};
        call _closeOriginal;
        [_commitsCount==1,"compound saved twice by reentrant Unload"] call _check;
        [count (_effects select {(_x select 0)=="lease"})==1,"lease released twice"] call _check;
    ''')
