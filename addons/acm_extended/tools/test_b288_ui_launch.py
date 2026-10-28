"""Execute Narc Box launch ownership and constructor-failure cleanup.

The native draw constructor/display controls are engine boundaries. Launch
capture, generation rejection, time deadline and exact flow cleanup execute.
"""
import re

import pytest

from test_menu_death_lifecycle import adapt, execute, read


def setup(native_available=True):
    text=read('skOpenDraw').replace('findDisplay 84000','_nativeDisplay').replace('isNull (_nativeDisplay)','(_nativeDisplay isEqualTo objNull)')
    text=text.replace('local _medic','_providerLocal')
    text=text.replace('_drawDisplayB51 displayCtrl 84012','objNull').replace('_drawDisplayB51 closeDisplay 2;','_nativeDisplay=objNull;')
    text=re.sub(r'playSound "[^"]+";','',text)
    return r'''
        private _nativeDisplay=objNull;
        private _providerLocal=true;
        private _controlled=_medic;
        private _createSuccess=false;
        private _injected=0;private _patched=0;private _resumes=[];
        private _flow=["pause",_patient,_medic,"flow-A","leftarm",true,0,7,"bag-A",2,3];
        private _context=["active",_patient];
        ACME_infusion_pendingPausedFlow=+_flow;
        ACME_infusion_pendingContext=+_context;
        ACME_fnc_controlledProvider={_controlled};
        ACME_fnc_restorePausedFlow={
            _resumes pushBack +(missionNamespace getVariable ["ACME_infusion_pendingPausedFlow",[]]);
            ACME_infusion_pendingPausedFlow=nil;
        };
        ACME_fnc_skInject={_injected=_injected+1;_nativeDisplay setVariable ["ACME_SK_Provider",_controlled];_nativeDisplay setVariable ["ACME_SK_CloseEpoch",1];};
        ACME_fnc_patchDrawDialog={_patched=_patched+1;};
        ACME_fnc_skPendingTagEnsure={};ACME_fnc_skPendingTagRender={};
        ACME_fnc_skCompoundBegin={};
        ACM_circulation_fnc_Syringe_Draw={if (_createSuccess) then {_nativeDisplay=missionNamespace;};};
        private _run={params ["_index"];private _h=_handlers select _index;
            if (_h select 2) then {[_h select 1,_index]call(_h select 0);};};
    ''' + ('' if native_available else 'ACM_circulation_fnc_Syringe_Draw=nil;') + \
        'ACME_fnc_skOpenDraw={' + adapt(text) + '};'


def test_native_constructor_failure_expires_by_time_and_releases_exact_pause():
    execute(setup() + r'''
        [10,_patient,"leftarm"]call ACME_fnc_skOpenDraw;
        [count _handlers==1 && {count _resumes==0},"launch did not await constructor"]call _check;
        _nowTime=14.9;[0]call _run;
        [count _resumes==0,"launch deadline fired early"]call _check;
        _nowTime=15;[0]call _run;[0]call _run;
        [count _resumes==1 && {(_resumes select 0)isEqualTo _flow},"failed constructor leaked/duplicated pause release"]call _check;
        [isNil "ACME_infusion_pendingContext","failed constructor retained infusion context"]call _check;
        [!(uiNamespace getVariable ["ACME_SK_DrawLaunch",[]]isNotEqualTo[]),"failed launch retained injector ownership"]call _check;
    ''')


def test_missing_native_draw_api_releases_pause_before_unload_can_exist():
    execute(setup(False) + r'''
        [10,_patient,"leftarm"]call ACME_fnc_skOpenDraw;
        [count _handlers==0 && {count _resumes==1},"missing API left patient paused"]call _check;
    ''')


@pytest.mark.parametrize('change',[
    '_controlled=missionNamespace;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_alive=false;', '_providerLocal=false;',
    '_medic setVariable ["ACME_persistenceFrozen",true];',
])
def test_cancelled_provider_launch_cannot_inject_but_releases_its_pause(change):
    execute(setup() + '[10,_patient,"leftarm"]call ACME_fnc_skOpenDraw;' + change + r'''
        _nativeDisplay=missionNamespace;[0]call _run;
        [_injected==0 && {count _resumes==1},"stale provider injected or stranded pause"]call _check;
    ''')


def test_successful_synchronous_constructor_is_injected_and_leaves_pause_for_dialog_teardown():
    execute(setup() + r'''
        _createSuccess=true;
        [10,_patient,"leftarm"]call ACME_fnc_skOpenDraw;[0]call _run;[0]call _run;
        [_injected==1 && {_patched==1},"successful constructor was not injected exactly once"]call _check;
        [count _resumes==0,"successful open released live mixing pause"]call _check;
        [(uiNamespace getVariable ["ACME_SK_DrawLaunch",[]])isEqualTo[],"completed injector retained launch"]call _check;
    ''')


def test_old_injector_never_consumes_new_launch_or_new_pending_flow():
    execute(setup() + r'''
        [10,_patient,"leftarm"]call ACME_fnc_skOpenDraw;
        _flow set[3,"flow-B"];ACME_infusion_pendingPausedFlow=+_flow;
        _context=["active",_patient,"new"];ACME_infusion_pendingContext=+_context;
        [5,_patient,"leftarm"]call ACME_fnc_skOpenDraw;
        _nativeDisplay=missionNamespace;[0]call _run;
        [_injected==0 && {count _resumes==0},"old injector adopted/released new launch"]call _check;
        [1]call _run;
        [_injected==1 && {count _resumes==0},"new launch lost ownership"]call _check;
    ''')


def test_timeout_never_clears_newer_flow_even_if_pending_context_changed_independently():
    execute(setup() + r'''
        [10,_patient,"leftarm"]call ACME_fnc_skOpenDraw;
        _flow set[3,"flow-B"];ACME_infusion_pendingPausedFlow=+_flow;
        ACME_infusion_pendingContext=["replacement"];
        _nowTime=16;[0]call _run;
        [count _resumes==0,"old failure released newer flow"]call _check;
        [(missionNamespace getVariable ["ACME_infusion_pendingContext",[]])isEqualTo["replacement"],"old failure cleared newer context"]call _check;
    ''')


def test_native_display_without_successful_acme_injection_cannot_strand_pause():
    execute(setup() + r'''
        _createSuccess=true;ACME_fnc_skInject={};
        [10,_patient,"leftarm"]call ACME_fnc_skOpenDraw;[0]call _run;
        [count _resumes==1 && {_patched==0},"refused injection left patient paused or patched unowned dialog"]call _check;
        [_nativeDisplay isEqualTo objNull,"failed injection left orphan native dialog"]call _check;
    ''')
