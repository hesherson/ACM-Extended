"""Execute native writers with explicit object, owner, and CBA transport stand-ins.

These tests validate local decisions, value conservation and publication intent;
they do not emulate Arma network delivery, the real medical GUI, or AI targeting.
"""
import re
import pytest
from test_menu_death_lifecycle import ROOT, adapt, execute, read


def source_engine(source, component='core'):
    # Set these before adapt() so ownership remains an independent input.
    for variable in ('_patient', '_unit', '_u'):
        source=source.replace('local '+variable, '_testLocal')
        source=source.replace('owner '+variable, '_ownerNum')
    source=source.replace('isServer', '_testServer').replace('serverTime','CBA_missionTime')
    # Namespace objects cannot broadcast: record the actual intent then adapt
    # just the engine's third setVariable argument, not the native writer logic.
    for variable,key in (('_patient','_key'),('_unit','_var'),('_patient','_var'),('_object','"ace_cargo_canLoad"')):
        old=f'{variable} setVariable [{key}, _value, _public];'
        if old in source:
            source=source.replace(old,f'_publications pushBack [{key}, _value, _public]; {variable} setVariable [{key}, _value];')
    source=re.sub(r'(setVariable\s*\[[^]\n]+),\s*_public\s*\]', r'\1]', source)
    # SQF-VM lacks these commands. Exercise the same missing-key default with
    # native HashMap membership/get; all numeric fixtures here are finite.
    for mapping in ('_clotted','_open'):
        source=source.replace(mapping+' getOrDefault [_part, []]',
            '(if (_part in '+mapping+') then {'+mapping+' get _part} else {[]})')
    source=re.sub(r'\bfinite (_\w+)', r'(\1 isEqualType 0)', source)
    # Pinned SQF-VM returns nil for an absent typed boolean param. Preserve
    # Arma's documented false default for these valid three/four-field rows.
    source=source.replace('_x param [3, false, [true]]',
        '(if (count _x > 3) then {_x select 3} else {false})')
    return adapt(source,component)


def native(component,name):
    return source_engine((ROOT/'addons'/component/'functions'/f'fnc_{name}.sqf').read_text(),component)


def setup():
    return '''
        private _testLocal=true; private _testServer=true; private _publications=[];
        CBA_fnc_removePerFrameHandler={_removed pushBack (_this select 0);};
    ''' + ''.join(f'ACM_{component}_fnc_{name}={{'+native(component,name)+'};' for component,name in (
        ('damage','setWoundState'),('circulation','setRuntimeState'),
        ('core','setAceMedicalState'),('gui','retireMedicalMenuPFH'),
        ('core','registerDownedProtectionReason'),('core','suppressPhysicalBandageReopening'),
    ))


@pytest.mark.parametrize('field,key',[('clottedWounds','ACM_damage_ClottedWounds'),('bandageProgress','ACM_damage_BandageProgress')])
@pytest.mark.parametrize('public',[False,True])
def test_damage_writer_preserves_the_ledger_and_publication_mode(field,key,public):
    execute(setup()+f'''
        private _ledger=createHashMapFromArray [["leftarm",[[7,0.6,0.1,2]]]];
        private _n=[_patient,[["{field}",_ledger]],{str(public).lower()}] call ACM_damage_fnc_setWoundState;
        [_n==1,"accepted ledger count"] call _check;
        [(_patient getVariable ["{key}",createHashMap]) isEqualTo _ledger,"ledger contents changed"] call _check;
        [count _publications==1 && {{(_publications select 0) isEqualTo ["{key}",_ledger,{str(public).lower()}]}},"publication intent changed"] call _check;
        [isNil {{_patient getVariable "ace_medical_bandagedWounds"}},"physical bandage storage touched"] call _check;
    ''')


@pytest.mark.parametrize('changes',[
    '[["clottedWounds",[]]]','[["bandageProgress",3]]','[["clottedWounds",nil]]',
    '[["unknown",createHashMap]]','[["ace_medical_bandagedWounds",createHashMap]]',
    '[[42,createHashMap]]','[[nil,createHashMap]]','[["clottedWounds"]]','[false,[],["clottedWounds",createHashMap,true]]',
])
def test_damage_writer_rejects_malformed_and_unapproved_changes(changes):
    execute(setup()+f'''
        private _n=[_patient,{changes},true] call ACM_damage_fnc_setWoundState;
        [_n==0 && {{count _publications==0}},"invalid ledger or field published"] call _check;
    ''')


@pytest.mark.parametrize('patient,local', [('_patient',False),('objNull',True),('objNull',False)])
def test_damage_writer_cannot_mutate_null_or_nonlocal_patients(patient,local):
    execute(setup()+f'''
        _testLocal={str(local).lower()};
        private _n=[{patient},[["clottedWounds",createHashMap]],true] call ACM_damage_fnc_setWoundState;
        [_n==0 && {{count _publications==0}},"rejected patient wrote state"] call _check;
    ''')


@pytest.mark.parametrize('fraction,expected',[(0.01,0.05),(0.15,0.15),(0.9,0.25)])
def test_partial_clot_reopen_conserves_wounds_and_never_changes_dressings(fraction,expected):
    pop=read('popClots').replace('alive _unit','true').replace('local _unit','_testLocal')
    execute(setup()+'''
        private _refresh=0;private _visual=0;
        ace_medical_status_fnc_updateWoundBloodLoss={_refresh=_refresh+1;};
        ace_medical_engine_fnc_updateBodyPartVisuals={_visual=_visual+1;};
        ace_medical_engine_fnc_updateDamageEffects={};
        private _physical=createHashMapFromArray [["leftarm",[[99,2,0,0]]]];
        { _patient setVariable [_x, _physical]; } forEach ["ace_medical_bandagedWounds","ACM_damage_WrappedWounds","ace_medical_stitchedWounds"];
        _patient setVariable ["ACM_damage_ClottedWounds",createHashMapFromArray [["leftarm",[[7,2,0.1,2],[8,1,0.1,2]]]]];
        _patient setVariable ["ace_medical_openWounds",createHashMap];
        private _pop={'''+source_engine(pop)+f'''}};
        private _n=[_patient,{fraction},"leftarm",7] call _pop;
        private _clots=(_patient getVariable "ACM_damage_ClottedWounds") get "leftarm";
        private _open=(_patient getVariable "ace_medical_openWounds") get "leftarm";
        [_n==1 && {{_refresh==1}} && {{_visual==1}},"one-clot event or refresh count changed"] call _check;
        [count _open==1 && {{abs ((_open select 0 select 1)-{expected})<0.00001}},"wrong partial reopen fraction"] call _check;
        [abs ((_clots select 0 select 1)+(_open select 0 select 1)-2)<0.00001 && {{(_clots select 1 select 1)==1}},"clot quantity lost or other clot changed"] call _check;
        {{[(_patient getVariable _x) isEqualTo _physical,"physical dressing changed"] call _check;}} forEach ["ace_medical_bandagedWounds","ACM_damage_WrappedWounds","ace_medical_stitchedWounds"];
        [count _publications==2,"expected clotted and open ledger publication"] call _check;
    ''')


@pytest.mark.parametrize('healthy',[False,True])
def test_reconciler_cpr_fallback_obeys_grace_and_native_writer(healthy):
    text=read('transientStateReconcile')
    pre=text[:text.index('// BVM reservation.')]
    block=text[text.index('// CPR reservation.'):text.index('// Hang Bag claim.')]
    execute(setup()+f'''
        ACM_circulation_fnc_cprSessionValid={{{str(healthy).lower()}}};
        ACM_circulation_fnc_cprRelease={{false}};
        _patient setVariable ["ACM_circulation_CPR_Medic",_medic];
        _patient setVariable ["ace_medical_CPR_provider",_medic];
        _patient setVariable ["ACM_circulation_CPR_session",[_medic,7]];
        private _repair={{'''+source_engine(pre+block)+f'''count _repairs;}};
        [_patient] call _repair;
        [count _publications==0,"reconciliation ignored grace"] call _check;
        CBA_missionTime=CBA_missionTime+4;
        private _n=[_patient] call _repair;
    '''+('''
        [_n==0 && {count _publications==0},"healthy CPR cleared"] call _check;
        [(_patient getVariable "ace_medical_CPR_provider") isEqualTo _medic,"healthy provider lost"] call _check;
    ''' if healthy else '''
        [_n==1 && {count _publications==3},"fallback did not publish all three native CPR fields"] call _check;
        [(_patient getVariable "ace_medical_CPR_provider") isEqualTo objNull,"ACE CPR provider not cleared"] call _check;
        [(_patient getVariable "ACM_circulation_CPR_Medic") isEqualTo objNull,"native CPR medic not cleared"] call _check;
        [(_patient getVariable "ACM_circulation_CPR_session") isEqualTo [],"native CPR session not cleared"] call _check;
        [_patient] call _repair;
        [count _publications==3,"repeated repair republished cleared fields"] call _check;
    '''))


@pytest.mark.parametrize('old,protected,removed', [('19','20','[19]'),('20','20','[]'),('-1','20','[]'),('"legacy"','20','[]'),('false','20','[]'),('0','20','[0]')])
def test_retiring_stock_renderer_preserves_live_handler_and_is_idempotent(old,protected,removed):
    execute(setup()+f'''
        missionNamespace setVariable ["ace_medical_gui_menuPFH",{old}];
        private _former=[{protected}] call ACM_gui_fnc_retireMedicalMenuPFH;
        [_former isEqualTo {old},"former handle not returned"] call _check;
        [(_removed isEqualTo {removed}),"wrong renderer removed"] call _check;
        [(missionNamespace getVariable ["ace_medical_gui_menuPFH",999])==-1,"stock handle not retired"] call _check;
        [{protected}] call ACM_gui_fnc_retireMedicalMenuPFH;
        [_removed isEqualTo {removed},"duplicate retirement removed a handler"] call _check;
    ''')


@pytest.mark.parametrize('server',[False,True])
@pytest.mark.parametrize('original',['[]','["ace-existing"]','["ace-existing","acme_medical_downed"]'])
def test_reason_registration_preserves_ace_indices_and_is_server_serialized(server,original):
    expected='["ace-existing","acme_medical_downed"]' if server and original=='["ace-existing"]' else original
    ready=expected!='[]' and 'acme_medical_downed' in expected
    execute(setup()+f'''
        _testServer={str(server).lower()};
        missionNamespace setVariable ["ace_common_statusEffects_setHidden",{original}];
        private _first=call ACM_core_fnc_registerDownedProtectionReason;
        private _second=call ACM_core_fnc_registerDownedProtectionReason;
        [_first isEqualTo {str(ready).lower()} && {{_second isEqualTo _first}},"reason readiness changed"] call _check;
        [(missionNamespace getVariable "ace_common_statusEffects_setHidden") isEqualTo {expected},"reason indices changed or duplicate added"] call _check;
    ''')


def test_physical_bandage_invariant_is_reassertable_without_changing_patient_wounds():
    execute(setup()+'''
        private _wounds=createHashMapFromArray [["body",[[4,1,0,0]]]];
        _patient setVariable ["ace_medical_bandagedWounds",_wounds];
        missionNamespace setVariable ["ace_medical_treatment_woundReopenChance",0.5];
        call ACM_core_fnc_suppressPhysicalBandageReopening;
        [(missionNamespace getVariable "ace_medical_treatment_woundReopenChance")==-1,"initial invariant missing"] call _check;
        missionNamespace setVariable ["ace_medical_treatment_woundReopenChance",0.7];
        call ACM_core_fnc_suppressPhysicalBandageReopening;
        [(missionNamespace getVariable "ace_medical_treatment_woundReopenChance")==-1,"post-settings invariant missing"] call _check;
        [(_patient getVariable "ace_medical_bandagedWounds") isEqualTo _wounds,"invariant rewrote patient wounds"] call _check;
    ''')
