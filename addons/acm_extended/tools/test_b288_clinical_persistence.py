"""Execute restart clocks and safe object restoration from production SQF.

Native objects, IDs, mission clocks and unrelated workers are explicit engine
boundaries. These cases do not certify native savegames or network delivery.
"""
import re

import pytest

from test_b271_ptx_stability import execute, function, restore_setup
from test_historical_medication_rows import iteration_scopes
from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import F, ROOT, adapt


def ref_function(name):
    text = (F / f"fn_{name}.sqf").read_text()
    text = text.replace("netId _value", '(_value getVariable ["fixtureNetId","0:0"])')
    text = text.replace("objectFromNetId _net", "([_net] call _objectFromNetId)")
    text = text.replace('_ref isEqualTypeAll ""', '(_ref findIf {!(_x isEqualType "")}) < 0')
    text = text.replace('switch (typeName _value)',
                        'switch (if (_value isEqualType profileNamespace) then {"OBJECT"} else {typeName _value})')
    text = re.sub(r'(\b_\w+) isEqualType objNull',
                  r'(\1 isEqualTo objNull || {\1 isEqualType profileNamespace})', text)
    text = re.sub(r'\bfinite (\([^\n]*?\)|_\w+)', r'(\1 call _finiteRef)', text)
    return 'ACME_fnc_' + name + '={' + adapt(map_defaults(iteration_scopes(text))) + '};\n'


def ref_setup():
    return r'''
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        private _finiteRef={_this isEqualType 0};
        private _nativeIds=createHashMapFromArray [["7:1",_patient],["7:2",_medic]];
        private _objectFromNetId={params ["_id"];[_nativeIds,[_id,objNull]] call _mapDefault};
        missionNamespace setVariable ["ACME_clinicalPersistenceSession","mission-A"];
        missionNamespace setVariable ["ACME_clinicalObjectBindings",createHashMap];
        missionNamespace setVariable ["ACME_clinicalObjectResolver",{objNull}];
        _patient setVariable ["fixtureNetId","7:1"];
        _medic setVariable ["fixtureNetId","7:2"];
    ''' + ''.join(ref_function(n) for n in ('clinicalObjectRef', 'clinicalEncodedValid', 'clinicalCodec'))


def test_same_mission_object_roundtrip_keeps_the_live_reference():
    execute(ref_setup() + r'''
        private _encoded=[_patient,true] call ACME_fnc_clinicalCodec;
        [_encoded isEqualTo ["O","7:1","mission-A",""],"object missed incarnation metadata"] call _check;
        [([_encoded,false] call ACME_fnc_clinicalCodec) isEqualTo _patient,"same-session live object was detached"] call _check;
    ''')


@pytest.mark.parametrize('server', [False, True])
def test_only_server_creates_and_publishes_one_mission_incarnation(server):
    text=(F/'fn_clinicalPersistenceInit.sqf').read_text()
    text=text.replace('isServer','_fixtureServer').replace('systemTimeUTC','[2026,10,28,0,0,0,0]')
    text=text.replace('missionNamespace setVariable ["ACME_clinicalPersistenceSession", _session, true];',
                      'missionNamespace setVariable ["ACME_clinicalPersistenceSession", _session];_sessionPublications pushBack _session;')
    execute(r'''
        missionNamespace setVariable ["ACME_clinicalPersistenceSession",nil];
        private _sessionPublications=[];
    ''' + f'private _fixtureServer={str(server).lower()};' +
        'private _initialize={' + adapt(text) + '};call _initialize;call _initialize;' + f'''
        [count _sessionPublications=={1 if server else 0},"client minted a competing incarnation or server republished it"] call _check;
        {'[count ACME_clinicalPersistenceSession>0,"server incarnation missing"] call _check;' if server else '[isNil "ACME_clinicalPersistenceSession","client invented an incarnation"] call _check;'}
    ''')


@pytest.mark.parametrize('legacy', [False, True])
def test_recycled_netid_cannot_bind_a_previous_mission_reference(legacy):
    execute(ref_setup() + f'''
        private _encoded={ '["O","7:1"]' if legacy else '[_patient,true] call ACME_fnc_clinicalCodec' };
        missionNamespace setVariable ["ACME_clinicalPersistenceSession","mission-B"];
        _nativeIds set ["7:1",_medic];
        [([_encoded,false] call ACME_fnc_clinicalCodec) isEqualTo objNull,"old ID attached an unrelated recreated object"] call _check;
    ''')


def test_durable_id_rebinds_recreated_object_and_rejects_duplicate_bind():
    execute(ref_setup() + r'''
        [["bind",_patient,"casualty-123"] call ACME_fnc_clinicalObjectRef,"initial stable binding failed"] call _check;
        private _encoded=[_patient,true] call ACME_fnc_clinicalCodec;
        [!(["bind",_medic,"casualty-123"] call ACME_fnc_clinicalObjectRef),"duplicate stable ID replaced live custody"] call _check;
        missionNamespace setVariable ["ACME_clinicalPersistenceSession","mission-B"];
        missionNamespace setVariable ["ACME_clinicalObjectBindings",createHashMap];
        _nativeIds set ["7:1",objNull];
        [["bind",_medic,"casualty-123"] call ACME_fnc_clinicalObjectRef,"recreated stable object failed to bind"] call _check;
        [([_encoded,false] call ACME_fnc_clinicalCodec) isEqualTo _medic,"stable ID did not resolve across restart"] call _check;
    ''')


@pytest.mark.parametrize('wrong_marker', [False, True])
def test_adapter_resolver_requires_exact_marked_id(wrong_marker):
    execute(ref_setup() + f'''
        _patient setVariable ["ACME_persistenceId","provider-7"];
        private _encoded=[[_patient],true] call ACME_fnc_clinicalCodec;
        missionNamespace setVariable ["ACME_clinicalPersistenceSession","mission-B"];
        _medic setVariable ["ACME_persistenceId","{'wrong-provider' if wrong_marker else 'provider-7'}"];
        missionNamespace setVariable ["ACME_clinicalObjectResolver",{{_medic}}];
        private _decoded=[_encoded,false] call ACME_fnc_clinicalCodec;
        [(_decoded select 0) isEqualTo {'objNull' if wrong_marker else '_medic'},"resolver accepted wrong identity or lost exact mapping"] call _check;
    ''')


def test_legacy_object_requires_explicit_same_mission_context():
    execute(ref_setup() + r'''
        private _encoded=["A",[["O","7:1"]]];
        [(([_encoded,false,"",0,"mission-A"] call ACME_fnc_clinicalCodec) select 0) isEqualTo _patient,"explicit same-mission legacy reference was lost"] call _check;
        [(([_encoded,false,"",0,"mission-old"] call ACME_fnc_clinicalCodec) select 0) isEqualTo objNull,"wrong legacy context reused a live ID"] call _check;
    ''')


@pytest.mark.parametrize('encoded,valid', [
    ('["O","7:1"]', True), ('["O","7:1","mission-A","case"]', True),
    ('["O","7:1","mission-A"]', False), ('["O","7:1",17,"case"]', False),
    ('["O","7:1","mission-A",[]]', False),
])
def test_object_encoding_preflight_rejects_malformed_extensions(encoded, valid):
    execute(ref_setup() + f'''
        [([{encoded}] call ACME_fnc_clinicalEncodedValid) isEqualTo {str(valid).lower()},"object encoding preflight mismatch"] call _check;
    ''')


@pytest.mark.parametrize('legacy', [False, True])
def test_full_snapshot_restore_rebases_acid_clock_then_real_handler_advances(legacy):
    from test_b286_clinical_retirement import setup as circ_setup

    # Production circHandle and ownerRegister execute with the retained B286
    # engine fixture, followed by the full snapshot/validator/restore pipeline.
    code = restore_setup() + circ_setup() + 'private _circSetVarNet=ACME_fnc_setVarNet;' + restore_setup() + iteration_scopes(function('clinicalSnapshot'))
    code += r'''
        // The two retained fixtures pass finite's scalar to their adapter in
        // different wrappers; both are the same native primitive boundary.
        _finite={private _v=if (_this isEqualType []) then {_this select 0} else {_this};_v isEqualType 0};
        ACME_fnc_setVarNet=_circSetVarNet;
        ACME_fnc_ownerRegister={_registerCalls pushBack (_this select 0);_this call _ownerRegister;};
        CBA_missionTime=7200;
        _patient setVariable ["ACE_isUnconscious",true];
        _patient setVariable ["ACME_circ_State",createHashMapFromArray [
            ["lastTick",7200],["acidLastTick",7200],["acidTickDt",3],
            ["totalAcidosis",0.3],["paCO2",45]
        ]];
        private _snapshot=[_patient] call ACME_fnc_clinicalSnapshot;
    '''
    if legacy:
        code += r'''
            private _circRow=(_snapshot select 1) select (((_snapshot select 1) apply {_x select 0}) find "ACME_circ_State");
            {if ((_x select 0)=="acidLastTick") then {_x set [1,["V",7200]];};} forEach ((_circRow select 1) select 1);
        '''
    else:
        code += r'''
            private _circRow=(_snapshot select 1) select (((_snapshot select 1) apply {_x select 0}) find "ACME_circ_State");
            private _acid=((((_circRow select 1) select 1) select {(_x select 0)=="acidLastTick"}) select 0) select 1;
            [_acid isEqualTo ["T","cba",0],"new snapshot retained an absolute acid clock"] call _check;
        '''
    code += r'''
        CBA_missionTime=12;
        _patient setVariable ["ACME_clock_clinicalMaintenance",nil];
        _patient setVariable ["ACME_clinicalMaintenanceDormant",false];
        [_patient,_snapshot,7] call ACME_fnc_clinicalRestore;
        private _restored=_patient getVariable "ACME_circ_State";
        [(_restored get "acidLastTick")==12 && {(_restored get "acidTickDt")==0},"restore retained old acid timing"] call _check;
        [(_restored get "totalAcidosis")==0.3 && {(_restored get "paCO2")==45},"clock fix reset clinical disease"] call _check;
        CBA_missionTime=16;call ACME_fnc_circHandle;
        private _after=_patient getVariable "ACME_circ_State";
        [(_after get "acidLastTick")==16 && {(_after get "acidTickDt")>0},"real handler stalled until previous mission uptime"] call _check;
    '''
    code = re.sub(r'\bfinite (\([^()\n]*\))', r'([\1] call _finite)', code)
    execute(code)


def test_legacy_patient_data_restores_with_unsafe_object_detached():
    execute(restore_setup() + ref_setup() + r'''
        ACME_fnc_circStateCommit={params ["_p","_state"];_p setVariable ["ACME_circ_State",_state];};
        private _payload=[3,[
            ["ACME_vent_operator",["O","7:1"]],
            ["ACME_circ_State",["M",[["totalAcidosis",["V",0.25]],["acidLastTick",["V",7200]]]]]
        ]];
        [_patient,_payload,7] call ACME_fnc_clinicalRestore;
        [(_patient getVariable "ACME_vent_operator") isEqualTo objNull,"legacy restore rebound unsafe provider"] call _check;
        [((_patient getVariable "ACME_circ_State") get "totalAcidosis")==0.25,"legacy restore discarded valid disease state"] call _check;
    ''')


def fresh_setup():
    return ref_setup() + ref_function('clinicalFreshBlood') + r'''
        CBA_missionTime=7200;
        private _bag=["FreshBlood",370,1,0,true,3,500,12,"saved-bag",500];
        private _map=createHashMapFromArray [["leftarm",[_bag]]];
        missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [[12,[_medic,500,3,true,5400]]]];
    '''


def test_hung_fresh_blood_roundtrip_carries_provenance_and_age_without_registry_collision():
    execute(fresh_setup() + r'''
        private _before=str _map;
        private _saved=[_map,"snapshot"] call ACME_fnc_clinicalFreshBlood;
        private _savedBag=(_saved get "leftarm") select 0;
        [(_savedBag select 10) isEqualTo ["freshAgeV1",true,1800,3],"fresh blood did not capture donor evidence and age"] call _check;
        [(_savedBag select 9)==500 && {(_savedBag select 1)==370},"fresh metadata changed manufacturer capacity/remaining volume"] call _check;
        [str _map==_before,"medical snapshot changed the live hung bag"] call _check;
        // The restarted registry reuses numeric ID 12 for another donor.
        CBA_missionTime=12;
        missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMapFromArray [[12,[_patient,1000,3,false,11]]]];
        private _restored=[_saved,"restore"] call ACME_fnc_clinicalFreshBlood;
        private _restoredBag=(_restored get "leftarm") select 0;
        [(_restoredBag select 10) isEqualTo ["freshV1",true,-1788,3],"restart rebound collided donor ID or lost collection age"] call _check;
        [(_restoredBag select 7)==-1,"restored hung bag retained previous mission donor ID"] call _check;
        private _again=[_restored,"snapshot"] call ACME_fnc_clinicalFreshBlood;
        [(((_again get "leftarm") select 0) select 10) isEqualTo (_savedBag select 10),"paused restart accumulated artificial blood aging"] call _check;
    ''')


def test_inline_fresh_record_overrides_recycled_live_registry_and_preserves_row_tail():
    execute(fresh_setup() + r'''
        _bag set [10,["freshV1",false,7000,3]];
        _bag set [11,"foreign-tail"];
        private _saved=[_map,"snapshot"] call ACME_fnc_clinicalFreshBlood;
        private _row=(_saved get "leftarm") select 0;
        [(_row select 10) isEqualTo ["freshAgeV1",false,200,3],"inline evidence was replaced by registry"] call _check;
        [(_row select 11)=="foreign-tail","fresh persistence truncated unrelated bag metadata"] call _check;
    ''')


@pytest.mark.parametrize('mode', ['snapshot', 'restore'])
def test_missing_registry_or_legacy_restore_is_fenced_even_when_numeric_id_exists(mode):
    execute(fresh_setup() + f'''
        {'missionNamespace setVariable ["ACM_circulation_FreshBloodList",createHashMap];' if mode == 'snapshot' else ''}
        private _saved=[_map,"{mode}"] call ACME_fnc_clinicalFreshBlood;
        [(((_saved get "leftarm") select 0) select 10) isEqualTo ["freshMissingV1"],"unresolved saved ID could bind a different donor"] call _check;
    ''')


@pytest.mark.parametrize('meta', [
    '["freshMissingV1"]', '["freshAgeV1",true,-2,3]',
    '["freshAgeV1",true,100,7]', '["freshV1",true,7200,3]',
])
def test_bad_or_unnormalized_saved_fresh_metadata_cannot_fall_back_to_registry(meta):
    execute(fresh_setup() + f'''
        _bag set [10,{meta}];
        private _restored=[_map,"restore"] call ACME_fnc_clinicalFreshBlood;
        [(((_restored get "leftarm") select 0) select 10) isEqualTo ["freshMissingV1"],"invalid fresh metadata borrowed current donor registry"] call _check;
    ''')


@pytest.mark.parametrize('blood_type', [-1, 8, 3.5])
@pytest.mark.parametrize('mode,tag', [('snapshot','freshV1'),('restore','freshAgeV1')])
def test_invalid_fresh_blood_type_is_fenced_without_rejecting_other_patient_bags(blood_type,mode,tag):
    execute(fresh_setup()+f'''
        _bag set [5,{blood_type}];
        _bag set [10,["{tag}",true,100,{blood_type}]];
        private _result=[_map,"{mode}"] call ACME_fnc_clinicalFreshBlood;
        [_result isEqualType createHashMap,"invalid donor type erased other clinical state"] call _check;
        [(((_result get "leftarm") select 0) select 10) isEqualTo ["freshMissingV1"],"out-of-domain donor type remained usable"] call _check;
    ''')


def test_legacy_seven_field_nonfresh_bag_remains_compatible():
    execute(fresh_setup() + r'''
        private _plain=["Saline",250,1,0,true,-1,500];
        _map set ["leftarm",[_plain]];
        private _saved=[_map,"snapshot"] call ACME_fnc_clinicalFreshBlood;
        private _restored=[_saved,"restore"] call ACME_fnc_clinicalFreshBlood;
        [(_restored get "leftarm") isEqualTo [_plain],"new metadata requirement broke legacy plain fluid saves"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_map set ["leftarm",[[]]];', '_map set ["leftarm",17];',
    '_bag set [4,"not-a-boolean"];', '_bag set [7,[]];',
    '_bag set [8,33];', '_bag set [9,[]];',
])
def test_malformed_native_bag_collections_fail_preflight_without_source_changes(change):
    execute(fresh_setup() + change + r'''
        private _before=str _map;
        [([_map,"restore"] call ACME_fnc_clinicalFreshBlood) isEqualTo [],"malformed native bag collection entered patient write plan"] call _check;
        [str _map==_before,"invalid collection changed before rejection"] call _check;
    ''')


def test_native_serializer_and_restore_write_plans_call_fresh_normalizer_before_teardown():
    serialize=(ROOT/'addons/core/overrides/fnc_serializeState.sqf').read_text()
    snapshot=serialize[serialize.index('private _nativeSnapshotOK'):serialize.index('// Versioned timestamp metadata.')]
    deserialize=(ROOT/'addons/core/overrides/fnc_deserializeState.sqf').read_text()
    start=deserialize.index('private _writes = [];')
    stop=deserialize.index('} forEach _variableList;', start)+len('} forEach _variableList;')
    restore=deserialize[start:stop]
    assert deserialize.index('ACME_fnc_clinicalFreshBlood') < deserialize.index('call ACME_fnc_clearAllAilments')
    code=fresh_setup() + r'''
        private _unit=_patient;
        private _state=_medic;
        private _variableList=[["ACM_circulation_IV_Bags",createHashMap]];
        _unit setVariable ["ACM_circulation_IV_Bags",_map];
    ''' + adapt(map_defaults(iteration_scopes(snapshot))) + r'''
        private _stored=_state getVariable "ACM_circulation_IV_Bags";
        [(((_stored get "leftarm") select 0) select 10) isEqualTo ["freshAgeV1",true,1800,3],"native serializer omitted inline provenance"] call _check;
        CBA_missionTime=12;
    ''' + adapt(map_defaults(iteration_scopes(restore))) + r'''
        [_invalid=="","native restore rejected valid normalized bag"] call _check;
        private _restored=(_writes select 0) select 1;
        [(((_restored get "leftarm") select 0) select 10) isEqualTo ["freshV1",true,-1788,3],"native restore write plan retained old mission clock"] call _check;
    '''
    code=re.sub(r'\bfinite (_\w+)', r'(\1 call _finiteRef)',code)
    execute(code)
