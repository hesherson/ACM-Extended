"""Execute owner-local carrier return retry and publication throttling.

Production AutoReturn and cargo snapshot/populate/restore execute. Engine cargo,
locality and transport are explicit boundaries; no mod-rendering claim is made.
"""
import pytest
from test_b218_carrier_inventory import setup as cargo_setup, remove
from test_menu_death_lifecycle import adapt, execute, read
from source_scan import lex, matching


def tracked_writes(text):
    ts=lex(text); pairs=matching(ts); edits=[]
    for i,t in enumerate(ts):
        if t.kind!='ident' or t.value!='setVariable': continue
        if ts[i-1].value!='_patient': continue
        a=i+1; assert ts[a].value=='[' and a in pairs
        b=pairs[a]
        receiver=ts[i-1].offset
        args=text[ts[a].offset:ts[b].offset+1]
        edits.append((receiver,ts[b].offset+1,'[_patient,'+args+'] call _trackedWrite'))
    for a,b,new in reversed(edits): text=text[:a]+new+text[b:]
    return text


def setup():
    text=read('manualPlateCarrierAutoReturn')
    text=text.replace('local _patient','_isLocal').replace('vest _patient','_wornVest')
    # This fixture uses actual VM objects for cargo; retain the native object
    # default instead of the namespace-only adapter used by unrelated suites.
    text=text.replace('["_patient", objNull, [objNull]]','["_patient", objNull]')
    text=text.replace('["_expectedLease", "", [""]]','["_expectedLease", ""]')
    text=text.replace('netId _patient','"casualty"').replace('diag_log format ', '_diagnostics pushBack format ')
    text=tracked_writes(text)
    return cargo_setup() + r'''
    private _isLocal=true;
    private _publics=[]; private _writes=[]; private _diagnostics=[]; private _acks=[]; private _providerStops=[];
    private _restoreCalls=0; private _restoreTimes=[]; private _retireCalls=0; private _activity=[];
    private _trackedWrite={params ["_object","_args"];
        _writes pushBack (_args select 0);
        if (count _args>2 && {_args select 2}) then {_publics pushBack (_args select 0)};
        _object setVariable [_args select 0,_args select 1];};
    CBA_missionTime=0;
    CBA_fnc_targetEvent={_acks pushBack _this};
    CBA_fnc_localEvent={};
    ACME_fnc_ownerDispatch={_providerStops pushBack _this;};
    ACME_fnc_chestAccessLeaseRetire={_retireCalls=_retireCalls+1;true};
    ACME_fnc_chestAccessVestRestore={
        _restoreCalls=_restoreCalls+1; _restoreTimes pushBack CBA_missionTime;
        [_this select 0,(_this select 0) getVariable ["ACME_chestAccess_vestLoadout",[]],"ACME_chestAccess_vestLoadout"] call ACME_fnc_carrierInventoryRestore
    };
    ace_medical_treatment_fnc_addToLog={_activity pushBack _this};
    _patient setVariable ["ACME_chestAccess_vestLoadout",_saved];
    [_wornContainer,["life-saving-supply",3]] call _addItem;
    [_wornContainer,["partial-magazine",1,7]] call _addMagazine;
    ''' + remove() + r'''
    private _exact=[_cargo] call ACME_fnc_carrierCargoSnapshot;
    _wornVest="OtherModVest";
    _patient setVariable ["ACME_manualPlateCarrierState","off"];
    _patient setVariable ["ACME_manualPlateCarrierLease","manual:current"];
    _patient setVariable ["ACME_manualPlateCarrierProvider",_medic];
    _patient setVariable ["ACME_chestAccess_leases",createHashMapFromArray [["manual:current",[_medic,0,"manualplatecarrier"]],["unrelated",[_medic,0,"other"]]]];
    _patient setVariable ["ACME_chestAccess_readyLease","manual:current"];
    '''+'ACME_fnc_manualPlateCarrierAutoReturn={'+adapt(text)+'};'


def test_unchanged_foreign_vest_failure_has_bounded_attempts_and_zero_repeated_publications():
    execute(setup()+r'''
    [!([_patient,"awake"] call ACME_fnc_manualPlateCarrierAutoReturn),"foreign vest was overwritten"] call _check;
    private _firstPublics=count _publics;
    for "_i" from 1 to 200 do {CBA_missionTime=_i*0.2; [_patient,"awake"] call ACME_fnc_manualPlateCarrierAutoReturn;};
    [_restoreCalls<=21 && {_restoreCalls>1},"watchdog did not bound physical retries to2s"] call _check;
    for "_i" from 1 to (count _restoreTimes-1) do {
        [((_restoreTimes select _i)-(_restoreTimes select (_i-1)))>=1.999,"retry interval was shorter than2s"] call _check;
    };
    [count _publics==_firstPublics,"identical failed return rebroadcast custody/state"] call _check;
    [count _diagnostics==2 && {count _acks==1} && {count _providerStops==1},"identical failure spammed log/ACK/provider teardown"] call _check;
    [_wornVest=="OtherModVest" && {!isNull _cargo},"replacement/original cargo lost"] call _check;
    [([_cargo] call ACME_fnc_carrierCargoSnapshot) isEqualTo _exact,"parked cargo changed during retry"] call _check;
    ["unrelated" in (_patient getVariable "ACME_chestAccess_leases"),"retry discarded another lease"] call _check;
    ''')


def test_external_vest_removal_bypasses_retry_delay_and_preserves_live_cargo():
    execute(setup()+r'''
    [_patient,"awake"] call ACME_fnc_manualPlateCarrierAutoReturn;
    CBA_missionTime=0.2; _wornVest="";
    [[_patient,"awake"] call ACME_fnc_manualPlateCarrierAutoReturn,"vest removal waited behind failed retry deadline"] call _check;
    [_restoreCalls==2 && {_wornVest=="Vest_A"} && {isNull _cargo},"immediate return failed or duplicated cargo"] call _check;
    [([_wornContainer] call ACME_fnc_carrierCargoSnapshot) isEqualTo _exact,"return restored stale or lost live supplies"] call _check;
    [(_patient getVariable ["ACME_manualPlateCarrierReturnRetry",[]]) isEqualTo [],"success kept retry evidence"] call _check;
    private _donePublic=count _publics; private _doneWrites=count _writes;
    for "_i" from 1 to 100 do {[_patient,"awake"] call ACME_fnc_manualPlateCarrierAutoReturn;};
    [count _publics==_donePublic && {count _writes==_doneWrites} && {_restoreCalls==2},"healthy completed patient retained churn"] call _check;
    ''')


@pytest.mark.parametrize('change', [
    '_wornVest="AnotherModVest";',
    '_patient setVariable ["ACME_manualPlateCarrierLease","manual:new"];',
    '_patient setVariable ["ACME_equipmentKitEpoch",1];',
    '_patient setVariable ["ACME_clinicalEpoch",1];',
    '_patient setVariable ["ACME_providerLocalityEpoch",2];',
])
def test_changed_equipment_or_generation_retries_immediately_without_overwrite(change):
    execute(setup()+r'''
    [_patient,"awake"] call ACME_fnc_manualPlateCarrierAutoReturn;
    CBA_missionTime=0.2;
    '''+change+r'''
    private _currentVest=_wornVest;
    [_patient,"awake"] call ACME_fnc_manualPlateCarrierAutoReturn;
    [_restoreCalls==2 && {count _diagnostics==2},"changed equipment/generation did not bypass deadline"] call _check;
    [_wornVest==_currentVest && {!isNull _cargo},"changed equipment/generation lost replacement or custody"] call _check;
    [([_cargo] call ACME_fnc_carrierCargoSnapshot) isEqualTo _exact,"changed generation lost parked supplies"] call _check;
    ''')


def test_successful_same_key_physical_retry_retires_only_manual_lease():
    execute(setup()+r'''
    _wornVest="";
    private _realPopulate=ACME_fnc_carrierCargoPopulate;
    ACME_fnc_carrierCargoPopulate={};
    [_patient,"transport"] call ACME_fnc_manualPlateCarrierAutoReturn;
    [!isNull _cargo && {_wornVest==""},"failed population destroyed original cargo"] call _check;
    ACME_fnc_carrierCargoPopulate=_realPopulate;
    CBA_missionTime=2;
    [[_patient,"transport"] call ACME_fnc_manualPlateCarrierAutoReturn,"bounded same-key retry failed"] call _check;
    private _leases=_patient getVariable "ACME_chestAccess_leases";
    [!("manual:current" in _leases) && {"unrelated" in _leases},"successful retry kept manual or lost foreign lease"] call _check;
    [([_wornContainer] call ACME_fnc_carrierCargoSnapshot) isEqualTo _exact,"retry changed live cargo"] call _check;
    ''')


def test_nonowner_and_stale_timeout_never_touch_local_retry_or_equipment():
    execute(setup()+r'''
    _isLocal=false;
    [_patient,"awake"] call ACME_fnc_manualPlateCarrierAutoReturn;
    [count _writes==0 && {_restoreCalls==0},"nonowner touched retry/equipment"] call _check;
    _isLocal=true;
    [!([_patient,"replace-timeout","old-lease"] call ACME_fnc_manualPlateCarrierAutoReturn),"stale timeout accepted"] call _check;
    [count _writes==0 && {_restoreCalls==0} && {!isNull _cargo},"stale timeout touched custody"] call _check;
    ''')


@pytest.mark.parametrize('mutation', ['deadline','gear_key','public_teardown','log_cadence'])
def test_semantic_mutations_fail_existing_execution_cases(monkeypatch, mutation):
    import test_b282_carrier_return_retry as own
    real_read=own.read
    replacements={
        'deadline': ('if (_retrying && {_now < (_retry select 1)}) exitWith {false};',''),
        'gear_key': ('vest _patient, _patient getVariable ["ACME_carrierCargo", objNull],','"unchanging", _patient getVariable ["ACME_carrierCargo", objNull],'),
        'public_teardown': ('if (!_retrying) then {','if (true) then {'),
        'log_cadence': ('if (!_retrying || {_now >= _nextLog}) then {','if (true) then {'),
    }
    old,new=replacements[mutation]
    assert old in real_read('manualPlateCarrierAutoReturn')
    def changed(name):
        text=real_read(name)
        return text.replace(old,new,1) if name=='manualPlateCarrierAutoReturn' else text
    monkeypatch.setattr(own,'read',changed)
    case=test_external_vest_removal_bypasses_retry_delay_and_preserves_live_cargo if mutation=='gear_key' else test_unchanged_foreign_vest_failure_has_bounded_attempts_and_zero_repeated_publications
    reason={'deadline':'did not bound physical retries','gear_key':'vest removal waited','public_teardown':'rebroadcast custody/state','log_cadence':'spammed log/ACK'}[mutation]
    with pytest.raises(AssertionError,match=reason): case()
