"""Execute battery transactions through real reservation, owner and ACK code.

Arma object/inventory/transport and CBA schedules are controlled boundaries.
Production request identity, owner dispatch, decisions, receipt adoption,
refund-once and locality retirement execute in SQF-VM. This does not certify
native packet delivery or arbitrary third-party inventory implementations.
"""
from pathlib import Path
import re

import pytest

from source_scan import lex, matching
from test_b281_flight_scheduler import adapt
from test_b282_owner_recovery_execution import setup as recovery_setup
from test_menu_death_lifecycle import execute

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / "functions" / f"fn_{name}.sqf").read_text(encoding="utf-8-sig")


def engine(text):
    # Namespace objects retain independent locality/liveness/charge/quantity.
    text = re.sub(r'(\([^()]*\)|_\w+)\s+isEqualType objNull',
                  r'(\1 isEqualTo objNull || {\1 isEqualType profileNamespace})', text)
    text = re.sub(r'objNull,\s*\[objNull\]', 'objNull, [profileNamespace]', text)
    text = re.sub(r'\bowner (_\w+)', r'(\1 getVariable ["fixtureOwner",7])', text)
    text = re.sub(r'\blocal (_\w+)', r'(\1 getVariable ["fixtureLocal",true] && {!_isMultiplayer || {(\1 getVariable ["fixtureOwner",7])==_machineID}})', text)
    text = text.replace("clientOwner", "_machineID").replace("serverTime", "_serverNow")
    text = re.sub(r'\bisServer\b', '_isServer', text)
    text = re.sub(r'\bisMultiplayer\b', '_isMultiplayer', text)
    text = re.sub(r'objectParent (_\w+)', 'objNull', text)
    text = text.replace("itemCargo _vehicle", "[]")
    text = text.replace('_vehicle addItemCargoGlobal [_item, 1]', '[_vehicle,_item] call _addItem')
    text = re.sub(r'finite \(([^\n]+?)\)', r'(\1 call _finite)', text)
    text = text.replace("hasInterface", "false").replace("displayNull", "objNull")
    text = re.sub(r'\bisNull (\([^()\n]*\))', r'(\1 isEqualTo objNull)', text)
    text = re.sub(r'\bvalues (_\w+)', r'((keys \1) apply {\1 get _x})', text)
    text = text.replace('getNumber (configFile >> "CfgWeapons" >> _value >> "ACME_batteryCharge")',
                        '_chargeConfig getOrDefault [_value,-1]')
    return adapt(text)


def function(name):
    return "ACME_fnc_" + name + "={" + engine(source(name)) + "};\n"


def setup(begin=True):
    ack = source("ownerInit").split('["ACME_ventBatteryExchangeResult", {', 1)[1].split('}] call CBA_fnc_addEventHandler;', 1)[0]
    server = source("ownerInit").split('["ACME_ventBatteryDispositionClaim", {', 1)[1].split('}] call CBA_fnc_addEventHandler;', 1)[0]
    # Execute actual incoming Local ownership-generation and escrow recovery
    # code. Unrelated existing provider custody APIs are the parent fixture's
    # established boundaries; no battery branch is replaced.
    local = source("ownerInit")
    start = local.index('    _unit setVariable ["ACME_providerLocalityEpoch"')
    end = local.index('    // B268:', start)
    local = local[start:end]
    close = source("ventPanelClose")
    close = 'private _batterySupply =' + close.split('private _batterySupply =', 1)[1].split('if (!isNull _serviceParent)', 1)[0]
    variants = (ROOT / "vent_battery_items.hpp").read_text()
    charges = re.findall(r'class (ACME_VentBattery_\d+): ACME_VentBattery.*?ACME_batteryCharge = (\d+);', variants)
    assert len(charges) == 100
    assert {int(pct) for name, pct in charges} == set(range(100))
    assert all(name == f"ACME_VentBattery_{pct}" for name, pct in charges)
    assert variants.count('scope = 2; scopeArsenal = 0;') == 100
    assert 'ACME_batteryCharge = 100;' in (ROOT / 'config.cpp').read_text()
    config = '["ACME_VentBattery",100],' + ','.join(f'["{name}",{pct}]' for name, pct in charges)
    result = recovery_setup() + 'private _chargeConfig=createHashMapFromArray [' + config + '];\n' + r'''
        private _machineID=7;
        private _isServer=false;
        private _isMultiplayer=true;
        private _serverNow=10;
        private _distanceNow=1;
        private _dropCommands=true;
        private _dropResults=false;
        private _dropCertificates=false;
        private _commands=[];
        private _acks=[];
        private _refunds=[];
        private _serverClaims=[];
        private _donor=_patient;
        private _vehicleDonor=objNull;
        private _takeSource=_patient;
        private _addItem={params ["_unit","_item"];
            _refunds pushBack [_unit,_item];
            _unit setVariable ["fixtureBatteryQty",1+(_unit getVariable ["fixtureBatteryQty",0])];
            private _stock=_unit getVariable ["fixtureBatteryStock",createHashMap];
            _stock set [_item,1+([_stock,[_item,0]] call _mapDefault)];
            _unit setVariable ["fixtureBatteryStock",_stock];
        };
        ace_common_fnc_addToInventory=_addItem;
        ace_common_fnc_isAwake={(_this select 0) getVariable ["fixtureAwake",true]};
        ace_common_fnc_getCountOfItem={(_this select 0) getVariable ["fixtureVentCount",1]};
        ACME_fnc_patientInteractionDistance={_distanceNow};
        ace_medical_treatment_fnc_useItem={
            private _stock=_takeSource getVariable ["fixtureBatteryStock",createHashMap];
            private _items=_this select 2;
            private _index=_items findIf {([_stock,[_x,0]] call _mapDefault)>0};
            if (_index < 0) exitWith {[objNull,"",false]};
            private _item=_items select _index;
            _stock set [_item,(_stock get _item)-1];
            _takeSource setVariable ["fixtureBatteryQty",(_takeSource getVariable ["fixtureBatteryQty",0])-1];
            [_donor,_item,true,_vehicleDonor]
        };
        _patient setVariable ["ACME_vent_onPatient",true];
        _patient setVariable ["ACME_vent_custodyId","vent-original"];
        _patient setVariable ["ACME_vent_battery",42];
        _patient setVariable ["ACME_vent_spareBattery",98];
        _patient setVariable ["fixtureBatteryQty",1];
        _patient setVariable ["fixtureBatteryStock",createHashMapFromArray [["ACME_VentBattery_98",1]]];
        _medic setVariable ["ACME_vent_spareBattery",17];
        _medic setVariable ["ACME_providerLocalityEpoch",0];
        _patient setVariable ["fixtureOwner",7];_medic setVariable ["fixtureOwner",7];
        ACME_supplyReceipts=createHashMap;
        ACME_supplyReceiptSerial=0;
        ACME_vent_batteryDispositionJournal=createHashMap;
        ACME_vent_batteryDispositionConfirmPending=createHashMap;
        ACME_vent_batteryDispositionConfirmWorker=-1;
        CBA_fnc_serverEvent={
            if ((_this select 0)=="ACME_ventBatteryDispositionClaim") then {
                private _wasServer=_isServer;private _wasOwner=_machineID;
                _serverClaims pushBack (_this select 1);
                _isServer=true;if (_isMultiplayer) then {_machineID=2;};(_this select 1) call _serverHandler;
                _isServer=_wasServer;_machineID=_wasOwner;
            } else {_events pushBack _this;};
        };
        CBA_fnc_targetEvent={
            if ((_this select 0)=="ACME_ventBatteryExchangeResult") then {
                private _payload=_this select 1;_acks pushBack +_payload;
                if (!_dropResults && {!_dropCertificates || {count _payload < 5} || {(_payload select 4) isEqualTo []}}) then {
                    private _wasOwner=_machineID;private _wasServer=_isServer;
                    if (_isMultiplayer) then {_machineID=(_payload select 0 select 1) getVariable ["fixtureOwner",7];};_isServer=_machineID==2;
                    _payload call _ackHandler;_machineID=_wasOwner;_isServer=_wasServer;
                };
            } else {_events pushBack _this;};
        };
    '''
    result += "".join(function(name) for name in (
        "ventBatteryItems", "ventBatteryCharge",
        "treatmentSupplyOrder", "treatmentSupplyTake", "treatmentSupplyRefund",
        "ventBatteryExchange", "ventBatteryRequest", "ventBatteryAck", "clinicalNeedsTick", "ownerRegisterNeedsRecovery",
    ))
    result += "private _ownerDispatch={" + engine(source("ownerDispatch")) + "};\n"
    result += "private _ackHandler={" + engine(ack) + "};\n"
    result += "private _serverHandler={" + engine(server) + "};\n"
    result += "private _localRecovery={params [\"_unit\",\"_isLocal\"];" + engine(local) + "};\n"
    result += "private _closePanel={" + engine(close) + "};\n"
    result += r'''
        ACME_fnc_ownerDispatch={
            _commands pushBack _this;
            if (!_dropCommands) then {
                private _wasOwner=_machineID;private _wasServer=_isServer;
                if (_isMultiplayer) then {_machineID=(_this select 0) getVariable ["fixtureOwner",7];};_isServer=_machineID==2 || {!_isMultiplayer};
                _this call _ownerDispatch;_machineID=_wasOwner;_isServer=_wasServer;
            };
        };
        private _reserve={[_medic,_patient,call ACME_fnc_ventBatteryItems] call ACME_fnc_treatmentSupplyTake};
        private _begin={params ["_supply"];
            ["start",_medic,[_patient,_supply,[_supply select 1] call ACME_fnc_ventBatteryCharge,
                [_patient] call ACME_fnc_clinicalEpoch,_patient getVariable ["ACME_vent_custodyId",""],_takeSource,_serverNow,
                _patient getVariable ["ACME_vent_batterySwapOwnerPeriod",[7,0]]]] call ACME_fnc_ventBatteryRequest;
        };
        private _runWorker={private _h=_handlers select _this;[_h select 1,_this] call (_h select 0);};
        private _requestOf={((_medic getVariable ["ACME_vent_batterySwapEscrow",createHashMap]) get _this) select 0;};
        private _apply={params ["_request"];[_request select 0,"ventBatteryExchange",["apply",_request]] call ACME_fnc_ownerDispatch;};
        private _firstRequest={private _pending=_medic getVariable ["ACME_vent_batterySwapEscrow",createHashMap];
            (_pending get ((keys _pending) select 0)) select 0;};
    '''
    if not begin:
        return result + 'private _supply=[];private _request=[];\n'
    return result + r'''
        private _supply=call _reserve;
        [count _supply==4,"real supply reservation failed"] call _check;
        [(_patient getVariable ["fixtureBatteryQty",-1])==0,"physical battery was not reserved"] call _check;
        [[_supply] call _begin,"immutable request was not created"] call _check;
        private _request=call _firstRequest;
        [count _request==10 && {count _handlers==1},"panel-independent request worker missing"] call _check;
    '''


def flip_setup():
    text = re.sub(r'^#define.*$', '', source("ventFlip"), flags=re.M)
    text = text.replace('disableSerialization;', '').replace('diag_tickTime', '_uiNow')
    text = re.sub(r'(?:_\w+|\([^;\n]+?\))\s+displayCtrl\s+(\w+)', 'uiNamespace', text)
    control = r'(?:_\w+|\(uiNamespace\)|uiNamespace)'
    text = re.sub(control + r'\s+ctrlSetText\s+([^;]+);', r'_uiTexts pushBack (\1);', text)
    text = re.sub(control + r'\s+ctrlShow\s+[^;]+;', '', text)
    text = re.sub(control + r'\s+ctrlSetPosition\s+[^;]+;', '', text)
    text = re.sub(control + r'\s+ctrlCommit\s+[^;]+;', '', text)
    text = text.replace('ctrlText _tip', '""')
    text = text.replace('getMousePosition', '[0,0]')
    text = re.sub(r'playSound\s+([^;]+);', r'_sounds pushBack (\1);', text)
    constants = re.findall(r'^#define\s+(\w+)\s+([0-9.]+)$', source("ventFlip"), flags=re.M)
    assert len([row for row in constants if row[0] == "SWAP_SECS"]) == 1
    return setup(begin=False) + ''.join(f'{name}={value};\n' for name, value in constants) + r'''
        private _uiNow=10;private _uiTexts=[];private _sounds=[];private _hardStops=[];
        uiNamespace setVariable ["ACME_vent_dlg",uiNamespace];
        uiNamespace setVariable ["ACME_vent_target",_patient];
        uiNamespace setVariable ["ACME_vent_flipped",true];
        ACME_fnc_ventStopHard={_hardStops pushBack _this;};
    ''' + 'ACME_fnc_ventFlip={' + engine(text) + '};\n'


def scenario_exact_donor_ack(accepted):
    invalid = '' if accepted else '_patient setVariable ["ACME_vent_custodyId","replacement"];'
    execute(setup() + invalid + r'''
        // The old provider remains the transaction owner after control switches.
        ACE_player=missionNamespace;
        missionNamespace setVariable ["ACME_vent_spareBattery",17];
        _dropCommands=false;[_request] call _apply;
        [_request] call _apply;
        [count _refunds==1 && {((_refunds select 0) select 0) isEqualTo _patient},"physical donor changed or refunded twice"] call _check;
        [(_patient getVariable ["fixtureBatteryQty",-1])==1,"physical spare was lost or duplicated"] call _check;
        [(_medic getVariable ["ACME_vent_spareBattery",-1])==17
            && {(missionNamespace getVariable ["ACME_vent_spareBattery",-1])==17},"control switch received another donor's charge"] call _check;
    ''' + f'''
        [(_patient getVariable ["ACME_vent_spareBattery",-1])=={42 if accepted else 98},"donor charge disagrees with owner decision"] call _check;
        [(_patient getVariable ["ACME_vent_battery",-1])=={98 if accepted else 42},"owner battery changed incorrectly"] call _check;
    ''')


@pytest.mark.parametrize("accepted", [True, False])
def test_exact_physical_donor_receipt_and_charge_settle_once_after_control_switch(accepted):
    scenario_exact_donor_ack(accepted)


def test_lost_result_retries_same_request_after_close_stall_epoch_and_device_change():
    execute(setup() + r'''
        _dropCommands=false;_dropResults=true;[_request] call _apply;
        [count _refunds==0,"lost result manufactured inventory settlement"] call _check;
        call _closePanel;
        [(_patient getVariable ["fixtureBatteryQty",-1])==0,"closing refunded an undecided reservation"] call _check;
        _serverNow=240;_patient setVariable ["ACME_clinicalEpoch",2];
        _patient setVariable ["ACME_vent_custodyId","replacement"];
        _patient setVariable ["ACME_vent_battery",13];
        _dropResults=false;0 call _runWorker;
        [count _refunds==1 && {(_patient getVariable ["ACME_vent_spareBattery",-1])==42},"old accepted decision was not replayed"] call _check;
        [(_patient getVariable ["ACME_vent_battery",-1])==13,"retry re-swapped the replacement device"] call _check;
        private _escrow=(_medic getVariable "ACME_vent_batterySwapEscrow") get (_request select 2);
        [(_escrow select 0) isEqualTo _request && {(_escrow select 1)>=2},"retry changed identity or failed owner confirmation"] call _check;
    ''')


def test_dead_provider_worker_settles_when_provider_is_absent_from_owned_patient_list():
    execute(setup() + r'''
        _dropCommands=false;_dropResults=true;[_request] call _apply;
        _medic setVariable ["fixtureAlive",false];ACME_clinical_ownedUnits=[];
        ACE_player=_patient;_dropResults=false;0 call _runWorker;
        [count _refunds==1,"dead provider lost its pending disposition"] call _check;
        [(_patient getVariable ["ACME_vent_spareBattery",-1])==42,"dead provider refunded incoming charge after an accepted swap"] call _check;
    ''')


@pytest.mark.parametrize("dead", [False, True])
def test_actual_local_recovery_adopts_original_receipt_and_old_callback_cannot_clear_new_worker(dead):
    death = '_medic setVariable ["fixtureAlive",false];' if dead else ''
    execute(setup() + r'''
        _dropCommands=false;_dropResults=true;[_request] call _apply;
    ''' + death + r'''
        _medic setVariable ["fixtureLocal",false];[_medic,false] call _localRecovery;
        _machineID=9;_medic setVariable ["fixtureOwner",9];ACME_supplyReceipts=createHashMap;
        _medic setVariable ["fixtureLocal",true];[_medic,true] call _localRecovery;
        private _newStamp=+(_medic getVariable "ACME_vent_batterySwapWorker");
        [(_newStamp select 0)==9 && {(_newStamp select 1)==2},"incoming ownership did not create a current worker"] call _check;
        0 call _runWorker;
        [(_medic getVariable "ACME_vent_batterySwapWorker") isEqualTo _newStamp,"stale callback cleared replacement worker"] call _check;
        _dropResults=false;(_newStamp select 2) call _runWorker;
        [count _refunds==1,"incoming owner could not adopt the exact original mission-local receipt"] call _check;
        [count ACME_supplyReceipts==0,"settled receipt remained spendable"] call _check;
    ''')


def test_result_before_public_escrow_and_decision_waits_for_reconciliation():
    execute(setup() + r'''
        _dropCommands=false;_dropResults=true;[_request] call _apply;
        private _saved=_medic getVariable "ACME_vent_batterySwapEscrow";
        _medic setVariable ["ACME_vent_batterySwapEscrow",createHashMap];
        (_acks select 0) call _ackHandler;
        [count _refunds==0,"ACK without escrow adopted arbitrary physical supply"] call _check;
        _medic setVariable ["ACME_vent_batterySwapEscrow",_saved];
        private _decisions=_patient getVariable "ACME_vent_batterySwapReceipts";
        _patient setVariable ["ACME_vent_batterySwapReceipts",createHashMap];
        (_acks select 0) call _ackHandler;
        [count _refunds==0,"ACK without replicated owner decision settled early"] call _check;
        _patient setVariable ["ACME_vent_batterySwapReceipts",_decisions];
        _dropResults=false;0 call _runWorker;
        [count _refunds==1,"late public transaction evidence did not reconcile"] call _check;
    ''')


@pytest.mark.parametrize("late", ["escrow", "decision"])
def test_observed_ack_keeps_dead_incoming_provider_retrying_after_local_retry_window(late):
    field = "ACME_vent_batterySwapEscrow" if late == "escrow" else "ACME_vent_batterySwapReceipts"
    actor = "_medic" if late == "escrow" else "_patient"
    execute(setup() + r'''
        _dropCommands=false;_dropResults=true;[_request] call _apply;
        _dropCommands=true;_medic setVariable ["fixtureAlive",false];ACME_clinical_ownedUnits=[];
    ''' + f'''
        private _evidence={actor} getVariable "{field}";
        {actor} setVariable ["{field}",createHashMap];
    ''' + r'''
        _medic setVariable ["fixtureLocal",false];[_medic,false] call _localRecovery;
        _machineID=9;_medic setVariable ["fixtureOwner",9];ACME_supplyReceipts=createHashMap;
        _medic setVariable ["ACME_vent_batterySwapAwait",createHashMap];
        _medic setVariable ["fixtureLocal",true];[_medic,true] call _localRecovery;
        (_acks select 0) call _ackHandler;
        private _stamp=+(_medic getVariable ["ACME_vent_batterySwapWorker",[]]);
        [count _stamp==3 && {(_stamp select 0)==9}
            && {count (_medic getVariable ["ACME_vent_batterySwapAwait",createHashMap])==1},"observed ACK did not enroll dead incoming provider"] call _check;
        _serverNow=35;(_stamp select 2) call _runWorker;
        [count _refunds==0 && {count ACME_supplyReceipts==0},"opaque ACK invented receipt authority before public evidence"] call _check;
    ''' + f'''
        {actor} setVariable ["{field}",_evidence];
    ''' + r'''
        _dropCommands=false;_dropResults=false;(_stamp select 2) call _runWorker;
        (_stamp select 2) call _runWorker;
        [count _refunds==1 && {(_patient getVariable ["ACME_vent_spareBattery",-1])==42},"late public evidence stranded/doubled dead provider disposition"] call _check;
        [count (_medic getVariable ["ACME_vent_batterySwapAwait",createHashMap])==0,"proven observation did not retire"] call _check;
    ''')


def test_queued_ack_to_former_provider_owner_routes_exact_tuple_without_adoption():
    execute(setup() + r'''
        _dropCommands=false;_dropResults=true;[_request] call _apply;
        _medic setVariable ["fixtureLocal",false];
        (_acks select 0) call _ackHandler;
        [count _refunds==0 && {count _acks==2},"former owner adopted or failed to forward queued ACK"] call _check;
        private _forwarded=if (count _acks==2) then {_acks select 1} else {[]};
        [count _forwarded==4 && {(_forwarded select 0) isEqualTo _request}
            && {(_forwarded select 3)==1},"locality forwarding changed immutable ACK identity"] call _check;
        _machineID=9;_medic setVariable ["fixtureOwner",9];ACME_supplyReceipts=createHashMap;
        _medic setVariable ["fixtureLocal",true];_dropResults=false;
        _forwarded call _ackHandler;
        [count _refunds==1,"current owner could not settle forwarded exact decision"] call _check;
    ''')


def test_opaque_observed_ack_queue_is_bounded_and_conflicting_observation_cannot_refund():
    execute(setup() + r'''
        private _escrows=_medic getVariable "ACME_vent_batterySwapEscrow";
        _medic setVariable ["ACME_vent_batterySwapEscrow",createHashMap];
        for "_i" from 0 to 64 do {
            private _unknown=+_request;private _rid=format ["opaque:%1",_i];
            _unknown set [2,"vent-battery:"+_rid];
            _unknown set [7,[_patient,_supply select 1,objNull,_rid]];
            [_unknown,true,42] call _ackHandler;
        };
        [count (_medic getVariable ["ACME_vent_batterySwapAwait",createHashMap])==64
            && {count _refunds==0},"opaque queue exceeded bound or manufactured inventory authority"] call _check;
        _medic setVariable ["ACME_vent_batterySwapAwait",createHashMap];
        [_request,false,98] call _ackHandler;
        _medic setVariable ["ACME_vent_batterySwapEscrow",_escrows];
        _dropCommands=false;[_request] call _apply;
        [count _refunds==1 && {(_patient getVariable ["ACME_vent_spareBattery",-1])==42},"conflicting observation blocked or altered proven disposition"] call _check;
        [count (_medic getVariable ["ACME_vent_batterySwapAwait",createHashMap])==0,"proven ACK left a contradictory opaque observation active"] call _check;
    ''')


@pytest.mark.parametrize("mutation", [
    '_request set [3,80];', '_request set [5,2];', '_request set [6,"different-device"];',
    '_request set [8,_medic];',
])
def test_changed_request_cannot_replay_or_refund_another_reservation(mutation):
    execute(setup() + r'''
        _dropCommands=false;_dropResults=true;[_request] call _apply;
        private _original=+_request;_request=+_request;
    ''' + mutation + r'''
        [_request,true,42] call _ackHandler;[_request] call _apply;
        [count _refunds==0,"altered immutable request settled another reservation"] call _check;
        _dropResults=false;[_original] call _apply;
        [count _refunds==1,"valid immutable request was blocked by conflicting retry"] call _check;
    ''')


@pytest.mark.parametrize("invalid", [
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_patient setVariable ["ACME_vent_custodyId","different"];',
    '_medic setVariable ["fixtureAlive",false];',
    '_medic setVariable ["fixtureAwake",false];',
    '_distanceNow=20;',
    '_patient setVariable ["ACME_vent_recovering",true];',
    '_patient setVariable ["ACME_vent_onPatient",false];',
    '_serverNow=240;',
    '_serverNow=7;',
])
def test_unknown_invalid_request_gets_retained_rejection_and_original_charge(invalid):
    execute(setup() + invalid + r'''
        _dropCommands=false;[_request] call _apply;[_request] call _apply;
        [(_patient getVariable ["ACME_vent_battery",-1])==42,"invalid request changed fitted battery"] call _check;
        [(_patient getVariable ["ACME_vent_spareBattery",-1])==98 && {count _refunds==1},"rejection lost original charge or refunded twice"] call _check;
        private _result=(_patient getVariable "ACME_vent_batterySwapReceipts") get (_request select 2);
        [!(_result select 1) && {_result select 3},"rejection was not retained and physically confirmed"] call _check;
    ''')


def test_failed_supply_refund_keeps_disposition_unsettled_and_retries_without_lost_charge():
    execute(setup() + r'''
        private _refund=ACME_fnc_treatmentSupplyRefund;
        ACME_fnc_treatmentSupplyRefund={ACME_supplyReceipts deleteAt ((_this select 0) select 3);false};
        _dropCommands=false;[_request] call _apply;
        private _row=(_medic getVariable "ACME_vent_batterySwapEscrow") get (_request select 2);
        [(_row select 1)==0 && {count _refunds==0},"failed physical return was marked complete"] call _check;
        [(_patient getVariable ["ACME_vent_spareBattery",-1])==98,"failed return corrupted spare charge"] call _check;
        ACME_fnc_treatmentSupplyRefund=_refund;0 call _runWorker;
        [count _refunds==1 && {(_patient getVariable ["ACME_vent_spareBattery",-1])==42},"failed disposition lost exact adoption/return evidence"] call _check;
    ''')


def test_ledger_capacity_defers_without_evicting_live_accepted_decisions_or_refunding():
    execute(setup() + r'''
        private _rows=createHashMap;
        for "_i" from 0 to 127 do {
            private _prior=+_request;_prior set [2,format ["old:%1",_i]];
            _rows set [_prior select 2,[_prior,true,42,false,10]];
        };
        _patient setVariable ["ACME_vent_batterySwapReceipts",_rows];
        _dropCommands=false;[_request] call _apply;
        [count _rows==128 && {count _refunds==0} && {count _acks==0},"full ledger evicted/guessed a pending disposition"] call _check;
        [(_patient getVariable ["ACME_vent_battery",-1])==42,"full ledger still installed a battery"] call _check;
        _rows deleteAt "old:0";0 call _runWorker;
        [count _rows==128 && {count _refunds==1},"deferred immutable request did not proceed when capacity freed"] call _check;
        [(_patient getVariable ["ACME_vent_battery",-1])==98,"deferred request lost its captured incoming charge"] call _check;
    ''')


def test_discarded_confirmed_decision_blocks_stale_escrow_reswap_and_second_refund():
    execute(setup() + r'''
        _dropCommands=false;[_request] call _apply;
        [count _refunds==1,"original transaction did not physically settle"] call _check;
        _serverNow=400;
        private _next=+_request;_next set [2,"vent-battery:7:999"];
        _next set [4,400];_next set [7,[_patient,_supply select 1,objNull,"7:999"]];
        private _escrows=_medic getVariable "ACME_vent_batterySwapEscrow";
        _escrows set [_next select 2,[_next,0,[]]];
        _dropResults=true;[_next] call _apply;
        [!((_request select 2) in (_patient getVariable "ACME_vent_batterySwapReceipts")),"old confirmed receipt did not expire"] call _check;
        _escrows set [_request select 2,[_request,0,[]]];
        ACME_supplyReceipts=createHashMap;
        _patient setVariable ["ACME_vent_battery",13];_dropResults=false;
        [_request] call _apply;[_request,true,42] call _ackHandler;[_request,false,98] call _ackHandler;
        [count _refunds==1 && {(_patient getVariable ["ACME_vent_battery",-1])==13},"discarded receipt authorized reswap/refund"] call _check;
        [((_escrows get (_request select 2)) select 1)==0,"uncertain stale disposition was guessed settled"] call _check;
    ''')


def test_missing_original_receipt_is_adopted_only_with_matching_owner_decision():
    execute(setup() + r'''
        ACME_supplyReceipts=createHashMap;
        [_request,true,42] call _ackHandler;
        [count _refunds==0 && {count ACME_supplyReceipts==0},"unproven ACK adopted an original receipt"] call _check;
        _dropCommands=false;[_request] call _apply;
        [count _refunds==1 && {count ACME_supplyReceipts==0},"decided public escrow could not adopt exact receipt"] call _check;
    ''')


def test_conflicting_local_receipt_cannot_be_overwritten_by_ack_adoption():
    execute(setup() + r'''
        private _other=[_medic,"ACME_VentBattery",objNull,_supply select 3];
        ACME_supplyReceipts set [_supply select 3,_other];
        _dropCommands=false;[_request] call _apply;
        [count _refunds==0 && {(ACME_supplyReceipts get (_supply select 3)) isEqualTo _other},"ACK overwrote a conflicting local custody receipt"] call _check;
    ''')


def test_confirmed_owner_receipt_repairs_old_provider_state_without_refunding_twice():
    execute(setup() + r'''
        _dropCommands=false;[_request] call _apply;
        private _escrows=_medic getVariable "ACME_vent_batterySwapEscrow";
        _escrows set [_request select 2,[_request,0,[]]];ACME_supplyReceipts=createHashMap;
        [_request] call _apply;
        [count _refunds==1 && {((_escrows get (_request select 2)) select 1)>=2},"late provider replica refunded an already-confirmed receipt"] call _check;
    ''')


def test_retry_identity_does_not_depend_on_ui_request_or_current_player():
    execute(setup() + r'''
        uiNamespace setVariable ["ACME_vent_batterySwapRequest",""];
        uiNamespace setVariable ["ACME_vent_batterySwapSupply",[]];ACE_player=missionNamespace;
        _dropCommands=false;0 call _runWorker;
        [count _refunds==1,"cleared UI/current-player context stranded the original request"] call _check;
        [((_commands select 0) select 2) isEqualTo ((_commands select 1) select 2),"worker refreshed immutable request identity"] call _check;
    ''')


def test_actual_hatch_and_timer_keep_original_provider_target_and_charge():
    execute(flip_setup() + r'''
        ["swap"] call ACME_fnc_ventFlip;
        [(_patient getVariable ["fixtureBatteryQty",-1])==0 && {count _hardStops==1},"hatch did not reserve battery and stop machine"] call _check;
        [count _handlers==0,"unfinished hatch dispatched a request"] call _check;
        ACE_player=missionNamespace;uiNamespace setVariable ["ACME_vent_target",missionNamespace];
        _dropCommands=false;_uiNow=15;["tick"] call ACME_fnc_ventFlip;
        [(_patient getVariable ["ACME_vent_battery",-1])==98 && {count _refunds==1},"control/target switch retargeted hatch exchange"] call _check;
        private _originalPending=_medic getVariable ["ACME_vent_batterySwapEscrow",createHashMap];
        [count _originalPending==1,"hatch request belongs to another provider"] call _check;
        private _request=if (count _originalPending==1) then {call _firstRequest} else {[]};
        [count _request==10 && {(_request select 0) isEqualTo _patient} && {(_request select 1) isEqualTo _medic}
            && {(_request select 3)==98} && {(_request select 4)==10},"hatch intent refreshed immutable context"] call _check;
    ''')


def test_actual_unfinished_hatch_cancels_once_and_never_dispatches_after_close():
    execute(flip_setup() + r'''
        ["swap"] call ACME_fnc_ventFlip;call _closePanel;call _closePanel;
        [count _refunds==1 && {(_patient getVariable ["fixtureBatteryQty",-1])==1},"unfinished hatch cancellation lost/duplicated supply"] call _check;
        _dropCommands=false;_uiNow=15;["tick"] call ACME_fnc_ventFlip;
        [count _commands==0 && {count _handlers==0},"cancelled hatch resumed a transaction"] call _check;
    ''')


def test_actual_local_hatch_ack_banner_is_not_overwritten_as_still_verifying():
    execute(flip_setup() + r'''
        _dropCommands=false;["swap"] call ACME_fnc_ventFlip;
        _uiNow=15;["tick"] call ACME_fnc_ventFlip;
        [count _refunds==1 && {!("VERIFYING SWAP" in _uiTexts)},"synchronously settled hatch returned to verifying UI"] call _check;
    ''')


def test_vehicle_supply_receipt_keeps_original_vehicle_charge_and_inventory():
    execute(setup(begin=False) + r'''
        _vehicleDonor=missionNamespace;_takeSource=missionNamespace;
        missionNamespace setVariable ["fixtureBatteryQty",1];
        missionNamespace setVariable ["fixtureBatteryStock",createHashMapFromArray [["ACME_VentBattery_63",1]]];
        missionNamespace setVariable ["ACME_vent_spareBattery",63];
        _supply=call _reserve;[[_supply] call _begin,"vehicle request did not reserve"] call _check;
        _request=call _firstRequest;_dropCommands=false;[_request] call _apply;[_request] call _apply;
        [count _refunds==1 && {((_refunds select 0) select 0) isEqualTo missionNamespace},"vehicle battery moved to a unit"] call _check;
        [(missionNamespace getVariable ["fixtureBatteryQty",-1])==1
            && {(missionNamespace getVariable ["ACME_vent_spareBattery",-1])==42},"vehicle spare charge/quantity changed"] call _check;
        [(_patient getVariable ["ACME_vent_battery",-1])==63
            && {(_patient getVariable ["ACME_vent_spareBattery",-1])==98},"vehicle exchange used patient's spare metadata"] call _check;
    ''')


def test_simultaneous_distinct_donors_are_serialized_with_exact_winner_and_rejection():
    execute(setup() + r'''
        private _first=+_request;
        _medic=missionNamespace;_donor=_medic;_vehicleDonor=parsingNamespace;_takeSource=parsingNamespace;
        parsingNamespace setVariable ["fixtureBatteryQty",1];
        parsingNamespace setVariable ["fixtureBatteryStock",createHashMapFromArray [["ACME_VentBattery_63",1]]];
        parsingNamespace setVariable ["ACME_vent_spareBattery",63];
        _supply=call _reserve;[[_supply] call _begin,"second provider did not reserve"] call _check;
        private _second=call _firstRequest;
        _dropCommands=false;[_first] call _apply;[_second] call _apply;
        [count _refunds==2 && {(_patient getVariable ["ACME_vent_battery",-1])==98},"concurrent viewers both replaced fitted charge"] call _check;
        [(_patient getVariable ["ACME_vent_spareBattery",-1])==42
            && {(parsingNamespace getVariable ["ACME_vent_spareBattery",-1])==63},"winner or losing donor charge was reassigned"] call _check;
        [(_patient getVariable ["fixtureBatteryQty",-1])==1
            && {(parsingNamespace getVariable ["fixtureBatteryQty",-1])==1},"concurrent reservation was lost/duplicated"] call _check;
    ''')


def test_late_public_provider_escrow_beyond_local_retries_is_discovered_without_a_panel():
    execute(setup() + r'''
        // The old machine's local worker does not replicate. The provider's
        // public reservation arrives after the bounded Local-event retries.
        (_handlers select 0) set [2,false];
        _medic setVariable ["ACME_vent_batterySwapWorker",[]];
        ACME_clinical_ownedUnits=[_medic];
        missionNamespace setVariable ["ACME_ownerRecoveryNextAt",1000];
        CBA_missionTime=40;_serverNow=40;
        _dropCommands=false;call _sharedTick;
        [count _refunds==1 && {count _handlers==2},"late public escrow stranded a known provider"] call _check;
        [count _registerCalls==1,"late escrow recovery did not stay bounded to missing work"] call _check;
    ''')


def test_shared_owner_recovery_repairs_negative_provider_worker_handle():
    execute(setup() + r'''
        (_handlers select 0) set [2,false];
        _medic setVariable ["ACME_ownerRegisterSeen",7];
        _medic setVariable ["ACME_vent_batterySwapWorker",[7,0,-1]];
        ACME_clinical_ownedUnits=[_medic];
        missionNamespace setVariable ["ACME_ownerRecoveryNextAt",1000];
        _dropCommands=false;call _sharedTick;
        [count _refunds==1 && {count _handlers==2} && {count _registerCalls==1},"current-generation negative worker handle stranded public reservation"] call _check;
    ''')


def test_two_fresh_cells_and_returned_depleted_cell_keep_independent_physical_charges():
    execute(flip_setup() + r'''
        _patient setVariable ["fixtureBatteryQty",2];
        _patient setVariable ["fixtureBatteryStock",createHashMapFromArray [["ACME_VentBattery",2]]];
        _patient setVariable ["ACME_vent_battery",10];
        _patient setVariable ["ACME_vent_spareBattery",7];
        _dropCommands=false;["swap"] call ACME_fnc_ventFlip;
        _uiNow=15;["tick"] call ACME_fnc_ventFlip;
        private _stock=_patient getVariable "fixtureBatteryStock";
        [(_stock get "ACME_VentBattery")==1 && {([_stock,["ACME_VentBattery_10",0]] call _mapDefault)==1}
            && {(_patient getVariable "ACME_vent_battery")==100},"first exchange conflated a fresh cell and returned depleted cell"] call _check;
        _serverNow=12;["swap"] call ACME_fnc_ventFlip;
        _uiNow=20;["tick"] call ACME_fnc_ventFlip;if (count _handlers>0) then {0 call _runWorker;};
        [(_patient getVariable "ACME_vent_battery")==100
            && {(_stock get "ACME_VentBattery")==1} && {([_stock,["ACME_VentBattery_10",0]] call _mapDefault)==1}
            && {(_patient getVariable "fixtureBatteryQty")==2},"second fresh cell inherited another cell's depleted charge"] call _check;
    ''')


def test_used_cell_charge_survives_inventory_transfer_and_vehicle_cargo_selection():
    execute(flip_setup() + r'''
        _patient setVariable ["fixtureBatteryStock",createHashMapFromArray [["ACME_VentBattery",1]]];
        _patient setVariable ["ACME_vent_battery",37];_dropCommands=false;
        ["swap"] call ACME_fnc_ventFlip;_uiNow=15;["tick"] call ACME_fnc_ventFlip;
        private _stock=_patient getVariable "fixtureBatteryStock";
        [(_stock get "ACME_VentBattery_37")==1,"returned cell did not carry its own charge"] call _check;
        // Engine/mod transfer moves the actual physical class, without copying
        // patient/source metadata. The receiving cargo has unrelated aliases.
        missionNamespace setVariable ["fixtureBatteryStock",_stock];
        missionNamespace setVariable ["fixtureBatteryQty",1];
        missionNamespace setVariable ["ACME_vent_spareBattery",99];
        _patient setVariable ["fixtureBatteryStock",createHashMap];
        _patient setVariable ["fixtureBatteryQty",0];
        _vehicleDonor=missionNamespace;_takeSource=missionNamespace;_serverNow=12;
        ["swap"] call ACME_fnc_ventFlip;_uiNow=20;["tick"] call ACME_fnc_ventFlip;0 call _runWorker;
        [(_patient getVariable "ACME_vent_battery")==37
            && {(_stock get "ACME_VentBattery")==1} && {(_stock get "ACME_VentBattery_37")==0}
            && {(missionNamespace getVariable "fixtureBatteryQty")==1},"transferred cargo cell used source metadata or lost inventory"] call _check;
    ''')


@pytest.mark.parametrize("reverse", [False, True])
def test_concurrent_source_ack_orders_return_each_cell_charge_and_exact_quantity(reverse):
    order = "[1,0]" if reverse else "[0,1]"
    execute(setup(begin=False) + r'''
        _vehicleDonor=missionNamespace;_takeSource=missionNamespace;
        missionNamespace setVariable ["fixtureBatteryQty",2];
        missionNamespace setVariable ["fixtureBatteryStock",createHashMapFromArray [["ACME_VentBattery",2]]];
        missionNamespace setVariable ["ACME_vent_spareBattery",7];
        _patient setVariable ["ACME_vent_battery",10];
        _supply=call _reserve;[[_supply] call _begin,"first source reservation failed"] call _check;
        private _first=call _firstRequest;
        _patient=parsingNamespace;_medic=parsingNamespace;
        _patient setVariable ["ACME_vent_onPatient",true];
        _patient setVariable ["ACME_vent_custodyId","second-device"];
        _patient setVariable ["ACME_vent_battery",30];
        _supply=call _reserve;[[_supply] call _begin,"second source reservation failed"] call _check;
        private _second=call _firstRequest;
        [(_first select 3)==100 && {(_second select 3)==100}
            && {(missionNamespace getVariable "fixtureBatteryQty")==0},"concurrent removals shared stale source charge or quantity"] call _check;
        _dropCommands=false;_dropResults=true;[_first] call _apply;[_second] call _apply;
    ''' + f'{{(_acks select _x) call _ackHandler;}} forEach {order};\n' + r'''
        // Confirmation replies are captured but physical duplicate ACKs remain
        // harmless in either order, even though both return to the same cargo.
        (_acks select 0) call _ackHandler;(_acks select 1) call _ackHandler;
        private _stock=missionNamespace getVariable "fixtureBatteryStock";
        [count _refunds==2 && {(missionNamespace getVariable "fixtureBatteryQty")==2}
            && {(_stock get "ACME_VentBattery")==0} && {([_stock,["ACME_VentBattery_10",0]] call _mapDefault)==1}
            && {([_stock,["ACME_VentBattery_30",0]] call _mapDefault)==1},"concurrent source ACKs conflated returned cells or duplicated quantity"] call _check;
        [((_first select 0) getVariable "ACME_vent_battery")==100
            && {((_second select 0) getVariable "ACME_vent_battery")==100},"concurrent fresh cells inherited returned metadata"] call _check;
    ''')


@pytest.mark.parametrize("charge,expected", [(0,0), (10.999,10), (99.999,99), (100,100)])
def test_physical_cell_charge_rounds_down_without_creating_energy(charge, expected):
    execute(setup(begin=False) + f'''
        private _item=[{charge}] call ACME_fnc_ventBatteryCharge;
        [([_item] call ACME_fnc_ventBatteryCharge)=={expected},"physical charge quantization created energy"] call _check;
    ''')


def test_optional_refund_class_cannot_substitute_arbitrary_item_or_nonbattery_receipt():
    execute(setup() + r'''
        [!([_supply,true,"ACME_Ventilator"] call ACME_fnc_treatmentSupplyRefund)
            && {count ACME_supplyReceipts==1} && {count _refunds==0},"arbitrary refund class consumed/changed battery receipt"] call _check;
        private _other=[_patient,"ACME_XStat",objNull,"other:1"];
        ACME_supplyReceipts set ["other:1",_other];
        [!([_other,true,"ACME_VentBattery_10"] call ACME_fnc_treatmentSupplyRefund)
            && {count ACME_supplyReceipts==2} && {count _refunds==0},"battery substitution consumed unrelated supply receipt"] call _check;
    ''')


@pytest.mark.parametrize("patient_moves", [False, True])
def test_server_disposition_prevents_duplicate_after_held_public_state_and_provider_patient_local_moves(patient_moves):
    move = r'''
        _patient setVariable ["fixtureLocal",false];_machineID=7;[_patient,false] call _localRecovery;
        _patient setVariable ["fixtureOwner",11];_patient setVariable ["fixtureLocal",true];
        _machineID=11;[_patient,true] call _localRecovery;
    ''' if patient_moves else ''
    execute(setup() + r'''
        private _nativeDispatch=ACME_fnc_ownerDispatch;private _holdSettled=true;
        ACME_fnc_ownerDispatch={
            if (_holdSettled && {((_this select 2) select 0)=="settled"}) then {_commands pushBack _this;}
            else {_this call _nativeDispatch;};
        };
        _dropCommands=false;_dropResults=true;[_request] call _apply;
        private _oldResult=+((_patient getVariable "ACME_vent_batterySwapReceipts") get (_request select 2));
        (_acks select 0) call _ackHandler;(_acks select 0) call _ackHandler;
        [count _refunds==1,"old owner did not perform one granted physical return"] call _check;
        private _physical=+((_medic getVariable "ACME_vent_batterySwapEscrow") get (_request select 2));
        private _stale=createHashMapFromArray [[_request select 2,[_request,0,[]]]];
        _medic setVariable ["fixtureLocal",false];_machineID=7;[_medic,false] call _localRecovery;
        _medic setVariable ["fixtureOwner",9];_medic setVariable ["fixtureLocal",true];
        _machineID=9;ACME_supplyReceipts=createHashMap;
        _medic setVariable ["ACME_vent_batterySwapEscrow",_stale];
        [_medic,true] call _localRecovery;
    ''' + move + r'''
        // Both public provider state1 and patient settled confirmation are held.
        // Even the public claim receipt is held; only server authority survives.
        _patient setVariable ["ACME_vent_batterySwapReceipts",createHashMapFromArray [[_request select 2,_oldResult]]];
        _patient setVariable ["ACME_vent_batterySwapDispositions",createHashMap];
        _machineID=9;(_acks select 0) call _ackHandler;(_acks select 0) call _ackHandler;
        [count _refunds==1 && {(_patient getVariable "fixtureBatteryQty")==1},"new owner adopted/refunded an uncertain old physical grant twice"] call _check;
        private _journal=(ACME_vent_batteryDispositionJournal get (_request select 0)) select 0;
        private _grant=_journal get (_request select 2);
        [(_grant select [3,2]) isEqualTo [7,0] && {!(_grant select 5)},"server reassigned an unconfirmed immutable physical grant"] call _check;
        _medic setVariable ["ACME_vent_batterySwapEscrow",createHashMapFromArray [[_request select 2,_physical]]];
        _holdSettled=false;_dropResults=false;
        private _stamp=_medic getVariable "ACME_vent_batterySwapWorker";
        (_stamp select 2) call _runWorker;
        [count _refunds==1 && {((_journal get (_request select 2)) select 5)},"late physical evidence did not reconcile original grant without another return"] call _check;
    ''')


@pytest.mark.parametrize("issued", [10,11])
def test_actual_patient_local_certificate_holds_unknown_same_time_or_future_skew_request_then_replays_known(issued):
    execute(setup(begin=False) + f'_serverNow={issued};\n' + r'''
        _patient setVariable ["fixtureBatteryStock",createHashMapFromArray [["ACME_VentBattery",1]]];
        _patient setVariable ["ACME_vent_battery",10];
        _supply=call _reserve;[[_supply] call _begin,"pre-transfer reservation failed"] call _check;
        _request=call _firstRequest;_serverNow=10;
        _dropCommands=false;_dropResults=true;[_request] call _apply;
        private _committed=_patient getVariable "ACME_vent_batterySwapReceipts";
        [(_patient getVariable "ACME_vent_battery")==100,"old owner did not apply original fresh cell"] call _check;
        _patient setVariable ["fixtureLocal",false];[_patient,false] call _localRecovery;
        _patient setVariable ["fixtureOwner",11];_patient setVariable ["fixtureLocal",true];
        _machineID=11;[_patient,true] call _localRecovery;
        _patient setVariable ["ACME_vent_batterySwapReceipts",createHashMap];
        _patient setVariable ["ACME_vent_batterySwapOwnerPeriod",_request select 9];
        _patient setVariable ["ACME_vent_battery",10];_dropResults=false;
        [_request] call _apply;
        [count (_patient getVariable "ACME_vent_batterySwapReceipts")==0 && {count _refunds==0}
            && {(_patient getVariable "ACME_vent_battery")==10},"stale public owner-period or clock equality permitted an unknown replay/refund"] call _check;
        _patient setVariable ["ACME_vent_batterySwapReceipts",_committed];
        _patient setVariable ["ACME_vent_battery",100];[_request] call _apply;
        private _stock=_patient getVariable "fixtureBatteryStock";
        [count _refunds==1 && {(_patient getVariable "ACME_vent_battery")==100}
            && {([_stock,["ACME_VentBattery_10",0]] call _mapDefault)==1},"known original decision failed replay before patient period check"] call _check;
    ''')


@pytest.mark.parametrize("deleted", [False,True])
def test_held_prior_patient_period_or_deleted_target_blocks_only_its_receipt_not_new_funded_cell(deleted):
    change = '_old set [0,objNull];' if deleted else '_patient setVariable ["ACME_providerLocalityEpoch",2];_patient setVariable ["ACME_vent_batterySwapOwnerPeriod",[7,2]];'
    execute(setup() + r'''
        private _old=+_request;
    ''' + change + r'''
        _medic setVariable ["ACME_vent_batterySwapEscrow",createHashMapFromArray [[_old select 2,[_old,0,[]]]]];
        [!( ["blocked",_medic] call ACME_fnc_ventBatteryRequest),"irrecoverable held receipt blocked all new funded stock"] call _check;
        _patient setVariable ["fixtureBatteryQty",1];
        _patient setVariable ["fixtureBatteryStock",createHashMapFromArray [["ACME_VentBattery",1]]];
        _supply=call _reserve;
        [[_supply] call _begin,"new funded physical cell was rejected by another held receipt"] call _check;
        private _new=("vent-battery:"+(_supply select 3)) call _requestOf;
        _dropCommands=false;[_new] call _apply;
        [count _refunds==1 && {(_patient getVariable "ACME_vent_battery")==100},"new valid cell could not settle independently of old held custody"] call _check;
        private _escrows=_medic getVariable "ACME_vent_batterySwapEscrow";
        [((_escrows get (_old select 2)) select 1)==0,"old unresolved receipt was guessed disposed"] call _check;
    ''')


def test_initial_registration_publishes_patient_period_and_remote_missing_period_returns_unsubmitted_cell():
    execute(flip_setup() + r'''
        [(_patient getVariable ["ACME_vent_batterySwapOwnerPeriod",[]]) isEqualTo [7,0],"initial registration did not publish a remote-readable patient period"] call _check;
        _patient setVariable ["fixtureOwner",11];_patient setVariable ["ACME_vent_batterySwapOwnerPeriod",[]];
        ["swap"] call ACME_fnc_ventFlip;
        [count _commands==0 && {count _handlers==0} && {count _refunds==1}
            && {(_patient getVariable "fixtureBatteryQty")==1},"missing remote certificate dispatched or lost an unsubmitted cell"] call _check;
    ''')


def test_singleplayer_claim_uses_local_authority_when_engine_owner_differs_from_zero_client_owner():
    execute(flip_setup() + r'''
        _isMultiplayer=false;_isServer=true;_machineID=0;
        _patient setVariable ["fixtureOwner",42];_medic setVariable ["fixtureOwner",42];
        _dropCommands=false;["swap"] call ACME_fnc_ventFlip;
        _uiNow=15;["tick"] call ACME_fnc_ventFlip;
        [count _refunds==1 && {(_patient getVariable "ACME_vent_battery")==98},"SP applied MP-only engine owner verification or rejected local owner zero"] call _check;
        private _request=call _firstRequest;
        [(_request select 9) isEqualTo [0,0],"SP certificate ignored current local authority"] call _check;
    ''')


def test_server_confirmation_before_public_replication_retries_without_inventory_effect():
    execute(setup() + r'''
        private _nativeServer=CBA_fnc_serverEvent;private _holdPublic=true;
        CBA_fnc_serverEvent={
            if (_holdPublic && {(_this select 0)=="ACME_ventBatteryDispositionClaim"} && {((_this select 1) select 2)=="confirm"}) then {
                _holdPublic=false;
                private _receipts=_patient getVariable "ACME_vent_batterySwapReceipts";
                private _escrows=_medic getVariable "ACME_vent_batterySwapEscrow";
                _patient setVariable ["ACME_vent_batterySwapReceipts",createHashMap];
                _medic setVariable ["ACME_vent_batterySwapEscrow",createHashMapFromArray [[_request select 2,[_request,0,[]]]]];
                _this call _nativeServer;
                _patient setVariable ["ACME_vent_batterySwapReceipts",_receipts];
                _medic setVariable ["ACME_vent_batterySwapEscrow",_escrows];
            } else {_this call _nativeServer;};
        };
        _dropCommands=false;[_request] call _apply;
        private _rows=(ACME_vent_batteryDispositionJournal get _patient) select 0;
        [count _refunds==1 && {!((_rows get (_request select 2)) select 5)}
            && {count ACME_vent_batteryDispositionConfirmPending==1},"early confirmation guessed completion or lost retry evidence"] call _check;
        private _handle=ACME_vent_batteryDispositionConfirmWorker;
        [_handle>=0,"early confirmation did not create bounded independent retry"] call _check;
        _machineID=2;_isServer=true;_handle call _runWorker;
        [(_rows get (_request select 2)) select 5 && {count ACME_vent_batteryDispositionConfirmPending==0}
            && {ACME_vent_batteryDispositionConfirmWorker==-1} && {count _refunds==1},"late publications did not settle journal and retire retry read-only"] call _check;
    ''')


def test_server_confirmation_worker_bounds_fair_rotation_and_retires_deleted_actors_without_pruning_claims():
    execute(setup() + r'''
        private _rows=createHashMap;private _receipts=createHashMap;private _escrows=createHashMap;
        _machineID=2;_isServer=true;
        for "_i" from 0 to 36 do {
            private _request=+_request;private _rid=format ["fair:%1",_i];private _id="vent-battery:"+_rid;
            _request set [2,_id];_request set [7,[_patient,_supply select 1,objNull,_rid]];
            _rows set [_id,[_request,true,42,7,0,false,10,false]];
            _receipts set [_id,[_request,true,42,true,10]];
            _escrows set [_id,[_request,3,[true,42,[7,0]]]];
            ACME_vent_batteryDispositionJournal set [_patient,[_rows,-1]];
            ["confirm",_request,[true,42,[7,0]]] call ACME_fnc_ventBatteryExchange;
        };
        private _pending=ACME_vent_batteryDispositionConfirmPending;
        {private _row=_pending get _x;private _copy=+(_row select 0);
            _copy set [if (_forEachIndex==0) then {0} else {1},objNull];
            _pending set [_x,[_copy,_row select 1]];
        } forEach ["vent-battery:fair:35","vent-battery:fair:36"];
        _patient setVariable ["ACME_vent_batterySwapReceipts",_receipts];
        _medic setVariable ["ACME_vent_batterySwapEscrow",_escrows];
        private _handle=ACME_vent_batteryDispositionConfirmWorker;
        _handle call _runWorker;
        [count ACME_vent_batteryDispositionConfirmPending>=21
            && {({(_rows get _x) select 5} count keys _rows)<=16},"one confirmation tick exceeded16 bounded records"] call _check;
        _handle call _runWorker;_handle call _runWorker;
        [count ACME_vent_batteryDispositionConfirmPending==0
            && {({(_rows get _x) select 5} count keys _rows)==35}
            && {count _rows==37} && {ACME_vent_batteryDispositionConfirmWorker==-1}
            && {ACME_vent_batteryDispositionConfirmCursor==0} && {count _refunds==0},"fair retry starved records, retained deleted work or guessed deleted disposition"] call _check;
    ''')


def test_server_disposition_capacity_keeps_live_claims_and_prunes_only_confirmed_with_closed_fence():
    execute(setup() + r'''
        _dropCommands=false;_dropResults=true;[_request] call _apply;
        private _rows=createHashMap;
        for "_i" from 0 to 127 do {
            private _old=+_request;private _rid=format ["old:%1",_i];private _id="vent-battery:"+_rid;
            _old set [2,_id];_old set [4,0];_old set [7,[_patient,_supply select 1,objNull,_rid]];
            _rows set [_id,[_old,true,42,7,0,false,0,false]];
        };
        ACME_vent_batteryDispositionJournal set [_patient,[_rows,-1]];
        _isServer=true;_machineID=2;
        ["authorize",_request,[7,0]] call ACME_fnc_ventBatteryExchange;
        [count _rows==128 && {!((_request select 2) in _rows)} && {count _refunds==0},"full server ledger evicted or granted over unconfirmed custody"] call _check;
        private _unacknowledged=_rows get "vent-battery:old:0";_unacknowledged set [5,true];
        private _settled=_rows get "vent-battery:old:1";private _pruned=+(_settled select 0);_settled set [5,true];_settled set [7,true];
        _serverNow=400;["authorize",_request,[7,0]] call ACME_fnc_ventBatteryExchange;
        [count _rows==128 && {(_request select 2) in _rows} && {!("vent-battery:old:1" in _rows)} && {"vent-battery:old:0" in _rows}
            && {((ACME_vent_batteryDispositionJournal get _patient) select 1)==0},"confirmed-only prune lost pending claim or closed-before fence"] call _check;
        private _results=_patient getVariable "ACME_vent_batterySwapReceipts";
        _results set [_pruned select 2,[_pruned,true,42,false,0]];
        ["authorize",_pruned,[7,0]] call ACME_fnc_ventBatteryExchange;
        [count _rows==128 && {!((_pruned select 2) in _rows)} && {count _refunds==0},"pruned server grant was resurrected from stale public evidence"] call _check;
    ''')


def test_confirmed_patient_result_before_claim_and_provider_replica_recovers_exact_stamp_without_second_refund():
    execute(setup() + r'''
        private _nativeServer=CBA_fnc_serverEvent;private _holdConfirmation=true;
        CBA_fnc_serverEvent={
            if ((_this select 0)=="ACME_ventBatteryDispositionClaim" && {((_this select 1) select 2)=="confirm"}
                && {_holdConfirmation}) then {_events pushBack _this;}
            else {_this call _nativeServer;};
        };
        _dropCommands=false;[_request] call _apply;
        private _rows=(ACME_vent_batteryDispositionJournal get _patient) select 0;
        [count _refunds==1 && {!((_rows get (_request select 2)) select 5)},"initial journal confirmation was not held"] call _check;
        _patient setVariable ["ACME_vent_batterySwapDispositions",createHashMap];
        _medic setVariable ["ACME_vent_batterySwapEscrow",createHashMapFromArray [[_request select 2,[_request,0,[]]]]];
        _medic setVariable ["fixtureLocal",false];[_medic,false] call _localRecovery;
        _machineID=9;_medic setVariable ["fixtureOwner",9];_medic setVariable ["fixtureLocal",true];
        ACME_supplyReceipts=createHashMap;_dropResults=true;[_medic,true] call _localRecovery;
        _holdConfirmation=false;_dropResults=false;[_request,true,42] call _ackHandler;
        private _escrow=(_medic getVariable "ACME_vent_batterySwapEscrow") get (_request select 2);
        [(_escrow select 1)>=2 && {((_escrow select 2) select 2) isEqualTo [7,0]}
            && {(_rows get (_request select 2)) select 5} && {count _refunds==1},"confirmed result lost original stamp or stranded journal after claim packet delay"] call _check;
    ''')


def test_server_certificate_loss_retains_physical_proof_past300_then_reconciles_without_patient_receipt():
    execute(setup() + r'''
        _dropCommands=false;_dropCertificates=true;[_request] call _apply;
        private _rows=(ACME_vent_batteryDispositionJournal get _patient) select 0;
        private _physical=(_medic getVariable "ACME_vent_batterySwapEscrow") get (_request select 2);
        [(_physical select 1)==2 && {(_rows get (_request select 2)) select 5}
            && {!((_rows get (_request select 2)) select 7)} && {count _refunds==1},"lost server certificate prematurely discarded completion proof"] call _check;
        _serverNow=500;
        _patient setVariable ["ACME_vent_batterySwapReceipts",createHashMap];
        _patient setVariable ["ACME_vent_batterySwapDispositions",createHashMap];
        // A fresh funded cell may be reserved while state2 proof is retained.
        _patient setVariable ["fixtureBatteryQty",2];
        private _stock=_patient getVariable "fixtureBatteryStock";_stock set ["ACME_VentBattery",1];
        _supply=call _reserve;
        [[_supply] call _begin,"server ACK loss blocked unrelated funded stock"] call _check;
        private _escrows=_medic getVariable "ACME_vent_batterySwapEscrow";
        private _held=[_escrows,[_request select 2,[]]] call _mapDefault;
        [count _held==3 && {(_held select 1)==2},"start purged unacknowledged physical proof after300s"] call _check;
        private _handle=ACME_vent_batteryDispositionConfirmWorker;
        _machineID=2;_isServer=true;_handle call _runWorker;
        [(_rows get (_request select 2)) select 5 && {!((_rows get (_request select 2)) select 7)}
            && {count _refunds==1},"long server stall/expired patient receipt guessed final acknowledgement"] call _check;
        _dropCertificates=false;_handle call _runWorker;
        _escrows=_medic getVariable "ACME_vent_batterySwapEscrow";
        private _settled=[_escrows,[_request select 2,[]]] call _mapDefault;
        [count _settled==3 && {(_settled select 1)==3} && {(_rows get (_request select 2)) select 7}
            && {count _refunds==1} && {count ACME_vent_batteryDispositionConfirmPending==0},"replayed server certificate lost original physical proof or refunded again"] call _check;
    ''')


def test_server_disposition_decision_cannot_be_replaced_by_unproven_ack_when_public_receipt_is_late():
    execute(setup() + r'''
        _dropCommands=false;_dropResults=true;[_request] call _apply;
        (_acks select 0) call _ackHandler;
        private _receipts=_patient getVariable "ACME_vent_batterySwapReceipts";
        _patient setVariable ["ACME_vent_batterySwapReceipts",createHashMap];
        ACME_supplyReceipts=createHashMap;
        [_request,true,99] call _ackHandler;
        [count _refunds==0 && {count ACME_supplyReceipts==0},"unproven ACK changed a decided cell charge before receipt replication"] call _check;
        _patient setVariable ["ACME_vent_batterySwapReceipts",_receipts];
        _dropResults=false;[_request,true,42] call _ackHandler;
        [count _refunds==1 && {(_patient getVariable "ACME_vent_spareBattery")==42},"valid original decision could not settle exact donor charge"] call _check;
    ''')


def test_server_certificate_before_late_dead_provider_escrow_waits_then_repairs_without_refund():
    execute(setup() + r'''
        _dropCommands=false;_dropCertificates=true;[_request] call _apply;
        private _certificate=[];
        {if (count _x==5) then {_certificate=+_x;};} forEach _acks;
        [count _certificate==5 && {count _refunds==1},"server did not produce one completed physical certificate"] call _check;
        _medic setVariable ["fixtureLocal",false];[_medic,false] call _localRecovery;
        _machineID=9;_medic setVariable ["fixtureOwner",9];_medic setVariable ["fixtureLocal",true];
        _medic setVariable ["fixtureAlive",false];_medic setVariable ["ACME_vent_batterySwapEscrow",createHashMap];
        ACME_supplyReceipts=createHashMap;ACME_clinical_ownedUnits=[];[_medic,true] call _localRecovery;
        _dropCertificates=false;_certificate call _ackHandler;
        private _awaits=_medic getVariable "ACME_vent_batterySwapAwait";
        [count _awaits==1 && {count (_awaits get (_request select 2))==5}
            && {count _refunds==1},"early completed certificate lost opaque dead-provider observation or refunded"] call _check;
        _serverNow=500;
        _patient setVariable ["ACME_vent_batterySwapReceipts",createHashMap];
        _medic setVariable ["ACME_vent_batterySwapEscrow",createHashMapFromArray [[_request select 2,[_request,0,[]]]]];
        private _stamp=_medic getVariable "ACME_vent_batterySwapWorker";
        (_stamp select 2) call _runWorker;
        private _escrow=(_medic getVariable "ACME_vent_batterySwapEscrow") get (_request select 2);
        [(_escrow select 1)==3 && {count _refunds==1} && {count ACME_supplyReceipts==0}
            && {count (_medic getVariable "ACME_vent_batterySwapAwait")==0},"late stale escrow made completed server certificate donate another cell"] call _check;
    ''')


def test_terminal_provider_receipt_retires_late_ordinary_ack_after_patient_receipt_prunes_read_only():
    execute(setup() + r'''
        _dropCommands=false;[_request] call _apply;
        private _escrow=(_medic getVariable "ACME_vent_batterySwapEscrow") get (_request select 2);
        [(_escrow select 1)==3 && {count _refunds==1},"physical disposition did not reach certified terminal state"] call _check;
        _patient setVariable ["ACME_vent_batterySwapReceipts",createHashMap];
        _patient setVariable ["ACME_vent_batterySwapDispositions",createHashMap];
        _serverNow=500;
        private _handlersBefore=count _handlers;private _acksBefore=count _acks;private _serverBefore=count _serverClaims;
        _medic setVariable ["ACME_vent_batterySwapAwait",createHashMapFromArray [[_request select 2,[_request,true,42]]]];
        [[_request,true,42] call ACME_fnc_ventBatteryAck,"terminal ordinary ACK no longer recognized exact completed decision"] call _check;
        [!([_request,true,99] call ACME_fnc_ventBatteryAck),"terminal receipt accepted conflicting returned charge"] call _check;
        [count (_medic getVariable "ACME_vent_batterySwapAwait")==0 && {count _handlers==_handlersBefore}
            && {count _acks==_acksBefore} && {count _serverClaims==_serverBefore} && {count _refunds==1},"terminal ACK queued completed work or emitted another inventory/transport effect"] call _check;
    ''')
