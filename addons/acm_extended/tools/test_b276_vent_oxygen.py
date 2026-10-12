"""Execute tank-backed ventilation through production SQF, including native reserve debit.

Only inventory cargo, locality/distance, CBA transport and engine clocks are adapters.
Attachment, verification, donor order, debit/ACK receipts, finite prepaid gas and owner
settings authorization execute checked-out SQF. These are not native MP acceptance.
"""
import re
from pathlib import Path
import pytest
from test_menu_death_lifecycle import ROOT, read, adapt, execute
from test_b156_procedure_supplies import primitives
from source_scan import lex, matching

HELPERS = ("ventOxygenReserve", "ventOxygenSource", "ventOxygenState", "ventOxygenFiO2",
           "ventOxygenClear", "ventOxygenRequest", "ventOxygenCommit", "ventOxygenTick",
           "ventOxygenDraw", "ventOxygenAck", "ventOxygenUse", "ventEffectiveSettings")


def code(source):
    source = source.replace("serverTime", "_serverTime")
    source = re.sub(r"objNull,\s*\[objNull\]", "objNull, [profileNamespace]", source)
    source = source.replace("netId _medic", '"operator"').replace("netId ACE_player", '"operator"')
    source = source.replace("local _source", "_sourceLocal")
    source = source.replace("local _patient", "_patientLocal")
    source = source.replace("local _medic", "_medicLocal")
    source = re.sub(r"\bfinite (_\w+)", r"(\1 call _finite)", source)
    for var in ("_source", "_unit"):
        for name, index in (("uniformContainer", 0), ("vestContainer", 1), ("backpackContainer", 2)):
            source = source.replace(name + " " + var, f"[{var},{index}]")
    source = re.sub(r"\bmagazinesAmmoCargo (_\w+)", r"(\1 call _magazines)", source)
    source = source.replace('_container addMagazineAmmoCargo ["ACM_OxygenTank_425", -1, _targetAmmoCount]',
                            '[_container,-1,_targetAmmoCount] call _magazineCargo')
    source = source.replace('_container addMagazineAmmoCargo ["ACM_OxygenTank_425", 1, _newCount]',
                            '[_container,1,_newCount] call _magazineCargo')
    ts = lex(source); pairs = matching(ts); edits = []
    for i, token in enumerate(ts[:-1]):
        if token.kind == "ident" and token.value == "linearConversion":
            end = pairs[i + 1]
            edits.append((token.offset, ts[end].offset + 1,
                          "(" + source[ts[i + 1].offset:ts[end].offset + 1] + " call _linear)"))
    for start, end, replacement in reversed(edits):
        source = source[:start] + replacement + source[end:]
    return primitives(adapt(source, component="breathing"))


def function(name):
    return f"ACME_fnc_{name}={{" + code(read(name)) + "};\n"


def setup():
    native = (ROOT / "addons/breathing/functions/fnc_useOxygenTankReserve.sqf").read_text()
    return r'''
      private _serverTime=100;private _liveEpoch=1;private _patientLocal=true;private _sourceLocal=true;private _medicLocal=true;
      private _sourceNear=true;private _medicNear=true;private _allowed=true;private _awake=true;
      private _events=[];private _debits=0;private _emptyReturns=0;private _kitDraws=0;
      private _linear={params ["_a","_b","_value","_lo","_hi",["_clamp",false]];private _fraction=(_value-_a)/(_b-_a);if (_clamp) then {_fraction=_fraction max 0 min 1;};_lo+(_hi-_lo)*_fraction};
      private _finite={_this isEqualType 0 && {_this > -1e30} && {_this < 1e30}};
      private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];private _value=_map get _key;if (isNil "_value") exitWith {_default};_value};
      private _magazines={params ["_u","_part"];private _bags=_u getVariable ["fixtureTanks",[[],[],[]]];(_bags select _part) apply {["ACM_OxygenTank_425",_x]}};
      private _magazineCargo={params ["_container","_direction","_charge"];_container params ["_u","_part"];private _bags=+(_u getVariable ["fixtureTanks",[[],[],[]]]);private _row=+(_bags select _part);if (_direction<0) then {private _i=_row find _charge;if (_i>=0) then {_row deleteAt _i;_debits=_debits+1;};} else {_row pushBack _charge;};_bags set [_part,_row];_u setVariable ["fixtureTanks",_bags];};
      ACME_fnc_clinicalEpoch={_liveEpoch};
      ACME_fnc_ventRecoveryNear={params ["_u","_p"];if (_u isEqualTo _medic) then {_sourceNear && {_medicNear}} else {true}};
      ACME_fnc_procedureAllowed={_allowed};ace_common_fnc_isAwake={_awake};
      ACME_fnc_setVarNet={params ["_p","_key","_value"];_p setVariable [_key,_value];};
      CBA_fnc_targetEvent={_events pushBack _this;};
      ACME_fnc_ownerDispatch={(_this select 2) call ACME_fnc_ventOxygenCommit;};
      ace_medical_treatment_allowSharedEquipment=0;ace_medical_treatment_fnc_isMedic={true};
      ace_common_fnc_getCountOfItem={params ["_u","_class"];if (_class=="ACM_OxygenTank_425_Empty") exitWith {_u getVariable ["fixtureEmpty",0]};private _n=0;{_n=_n+({_x>0} count _x);} forEach (_u getVariable ["fixtureTanks",[[],[],[]]]);_n};
      ACME_fnc_itemCount=ace_common_fnc_getCountOfItem;
      ace_common_fnc_addToInventory={params ["_u","_class"];if (_class=="ACM_OxygenTank_425_Empty") then {_emptyReturns=_emptyReturns+1;_u setVariable ["fixtureEmpty",(_u getVariable ["fixtureEmpty",0])+1];};};
      _patient setVariable ["fixtureTanks",[[],[],[]]];_medic setVariable ["fixtureTanks",[[283],[],[]]];
      _patient setVariable ["ACME_vent_custodyId","device"];
      _patient setVariable ["ACME_vent_onPatient",true];
      _patient setVariable ["ACME_vent_fio2",95];
      private _drawLast={private _all=_events select {(_x select 0)=="ACME_ventOxygenDraw"};(_all select ((count _all)-1)) select 1};
      private _ackLast={private _all=_events select {(_x select 0)=="ACME_ownerCommand"};((_all select ((count _all)-1)) select 1) select 2};
      private _roundtrip={call _drawLast call ACME_fnc_ventOxygenDraw;call _ackLast call ACME_fnc_ventOxygenAck;};
      private _attach={[_patient,"attach",_medic,95,_medic,"device",_liveEpoch,"",1] call ACME_fnc_ventOxygenCommit;call _roundtrip;};
      private _prepay={[_patient,0.5,95] call ACME_fnc_ventOxygenUse;call _roundtrip;};
    ''' + 'ACME_fnc_treatmentSupplyOrder={' + code(read("treatmentSupplyOrder")) + '};\n' + \
        'ACM_breathing_fnc_useOxygenTankReserve={' + code(native) + '};\n' + "".join(function(n) for n in HELPERS)


def test_attachment_verifies_real_source_without_consuming_or_mutating_other_choices():
    execute(setup() + r'''
      _patient setVariable ["ACME_vent_bpm",17];_patient setVariable ["ACME_vent_vt",620];_patient setVariable ["ACME_vent_peep",8];
      call _attach;
      private _state=[_patient] call ACME_fnc_ventOxygenState;
      [_state select 0 && {_state select 1},"real cylinder not verified"] call _check;
      [_debits==0 && {_emptyReturns==0} && {(_patient getVariable "ACME_vent_o2Credit")==0},"attachment debited supplies"] call _check;
      [[_patient,"fio2",_medic,40,objNull,"device",1,_patient getVariable "ACME_vent_o2Session",2] call ACME_fnc_ventOxygenCommit,"verified FiO2 rejected"] call _check;
      [(_patient getVariable "ACME_vent_fio2")==40 && {(_patient getVariable "ACME_vent_bpm")==17} && {(_patient getVariable "ACME_vent_vt")==620} && {(_patient getVariable "ACME_vent_peep")==8},"oxygen edit changed ventilation parameters"] call _check;
      [[_patient] call ACME_fnc_ventOxygenFiO2==21,"unpaid oxygen delivered before a breath"] call _check;
    ''')


@pytest.mark.parametrize("bad", ["epoch", "custody", "awake", "role", "distance", "no_device"])
def test_owner_attach_and_edit_revalidate_live_authority(bad):
    mutate = {"epoch": "_liveEpoch=2;", "custody": '_patient setVariable ["ACME_vent_custodyId","other"];',
              "awake": "_awake=false;", "role": "_allowed=false;", "distance": "_medicNear=false;",
              "no_device": '_patient setVariable ["ACME_vent_onPatient",false];'}[bad]
    execute(setup() + mutate + r'''
      [!([_patient,"attach",_medic,95,_medic,"device",1,"",1] call ACME_fnc_ventOxygenCommit),"stale/unauthorized oxygen accepted"] call _check;
      [count _events==0 && {_debits==0},"rejected supply attempt debited cargo"] call _check;
      [!([_patient,"fio2",_medic,60,objNull,"device",1,"",2] call ACME_fnc_ventOxygenCommit),"unverified FiO2 accepted"] call _check;
    ''')


def test_real_prepaid_gas_formula_pending_and_duplicate_draw_ack():
    execute(setup() + r'''
      call _attach;
      [[_patient,0.5,95] call ACME_fnc_ventOxygenUse==21,"first breath borrowed unspent gas"] call _check;
      private _draw=call _drawLast;_draw call ACME_fnc_ventOxygenDraw;
      private _ack=call _ackLast;_ack call ACME_fnc_ventOxygenAck;
      private _paid=_patient getVariable "ACME_vent_o2Credit";
      _draw call ACME_fnc_ventOxygenDraw;_ack call ACME_fnc_ventOxygenAck;
      [_debits==1 && {abs ((_patient getVariable "ACME_vent_o2Credit")-_paid)<0.00001},"duplicate gas debit/credit"] call _check;
      [[_patient,0.5,95] call ACME_fnc_ventOxygenUse==95,"paid oxygen not delivered"] call _check;
      [abs ((_patient getVariable "ACME_vent_o2Credit")-((425/283)-(0.5*0.74/0.79)))<0.00001,"incorrect cylinder mixing volume"] call _check;
      private _remaining=_patient getVariable "ACME_vent_o2Credit";
      [[_patient,0,95] call ACME_fnc_ventOxygenUse==21 && {(_patient getVariable "ACME_vent_o2Credit")==_remaining},"held/no delivered gas consumed oxygen"] call _check;
      [[_patient,2,21] call ACME_fnc_ventOxygenUse==21 && {(_patient getVariable "ACME_vent_o2Credit")==_remaining},"room air consumed cylinder"] call _check;
    ''')


def test_final_loose_charge_is_credited_even_native_returns_false_and_depletion_keeps_circuit():
    execute(setup() + r'''
      _medic setVariable ["fixtureTanks",[[1],[],[]]];
      _patient setVariable ["ACME_vent_connected",true];_patient setVariable ["ACME_vent_configured",true];
      call _attach;call _prepay;
      [_debits==1 && {_emptyReturns==1},"last charge not debited exactly once"] call _check;
      [[_patient,1,95] call ACME_fnc_ventOxygenUse==95,"last actual paid gas discarded"] call _check;
      _patient setVariable ["ACME_vent_effectiveFiO2",95];
      [[_patient,1,95] call ACME_fnc_ventOxygenUse==21,"depleted tank supplied unspent gas"] call _check;call _roundtrip;
      [[_patient] call ACME_fnc_ventOxygenFiO2==21,"depletion left enriched physiological readout"] call _check;
      [(_patient getVariable "ACME_vent_connected") && {_patient getVariable "ACME_vent_configured"} && {(_patient getVariable "ACME_vent_fio2")==95},"depletion stopped turbine or overwrote choices"] call _check;
    ''')


def test_missing_replicated_intent_receipt_race_and_long_delayed_ack_are_retriable():
    execute(setup() + r'''
      call _attach;[_patient,0.5,95] call ACME_fnc_ventOxygenUse;
      private _draw=call _drawLast;private _pending=+(_patient getVariable "ACME_vent_o2Pending");
      _patient setVariable ["ACME_vent_o2Pending",[]];_draw call ACME_fnc_ventOxygenDraw;
      [_debits==0 && {(_patient getVariable "ACME_vent_o2Status")=="DRAWING"},"missing intent became depletion"] call _check;
      _patient setVariable ["ACME_vent_o2Pending",_pending];_draw call ACME_fnc_ventOxygenDraw;
      private _ack=call _ackLast;private _ledger=_medic getVariable "ACME_vent_o2DrawLedger";
      _medic setVariable ["ACME_vent_o2DrawLedger",createHashMap];_ack call ACME_fnc_ventOxygenAck;
      [(_patient getVariable "ACME_vent_o2Credit")==0 && {count (_patient getVariable "ACME_vent_o2Pending")==4},"uncertified ACK granted oxygen"] call _check;
      _medic setVariable ["ACME_vent_o2DrawLedger",_ledger];_serverTime=400;
      _draw call ACME_fnc_ventOxygenDraw;call _ackLast call ACME_fnc_ventOxygenAck;
      [_debits==1 && {abs ((_patient getVariable "ACME_vent_o2Credit")-(425/283))<0.00001},"late delivery duplicated or lost charge"] call _check;
    ''')


@pytest.mark.parametrize("change", ["epoch", "custody", "detach", "death", "distance"])
def test_pending_request_cannot_debit_after_ending_or_moving_source(change):
    mutate = {"epoch": "_liveEpoch=2;", "custody": '_patient setVariable ["ACME_vent_custodyId","next"];',
              "detach": '[_patient] call ACME_fnc_ventOxygenClear;', "death": "_patientAlive=false;",
              "distance": "_sourceNear=false;"}[change]
    execute(setup() + r'''
      call _attach;[_patient,0.5,95] call ACME_fnc_ventOxygenUse;private _draw=call _drawLast;
    ''' + mutate + r'''
      _draw call ACME_fnc_ventOxygenDraw;
      [_debits==0,"stale/remote supply request consumed cylinder"] call _check;
      [!([_patient] call ACME_fnc_ventOxygenState select 1) || {!_patientAlive},"invalid supply stayed usable"] call _check;
    ''')


def test_source_locality_forward_retry_and_patient_owner_transfer_preserve_single_receipt():
    execute(setup() + r'''
      call _attach;[_patient,0.5,95] call ACME_fnc_ventOxygenUse;private _draw=call _drawLast;
      _sourceLocal=false;_draw call ACME_fnc_ventOxygenDraw;
      [_debits==0 && {((call _drawLast) select 5)==1},"nonowner mutated source inventory"] call _check;
      _sourceLocal=true;call _drawLast call ACME_fnc_ventOxygenDraw;private _ack=call _ackLast;
      _patientLocal=false;_ack call ACME_fnc_ventOxygenAck;
      [(_patient getVariable "ACME_vent_o2Credit")==0,"nonowner granted gas"] call _check;
      _patientLocal=true;_serverTime=102;[_patient] call ACME_fnc_ventOxygenTick;call _roundtrip;
      [_debits==1 && {(_patient getVariable "ACME_vent_o2Credit")>1.5},"owner transfer lost or duplicated debit"] call _check;
    ''')


@pytest.mark.parametrize("sharing, expected", [(0, "_patient"), (1, "_medic"), (2, "_medic")])
def test_source_uses_native_donor_priority_and_skips_zero_charge(sharing, expected):
    execute(setup() + f'ace_medical_treatment_allowSharedEquipment={sharing};' + r'''
      _patient setVariable ["fixtureTanks",[[0],[4],[]]];
      private _source=[_medic,_patient] call ACME_fnc_ventOxygenSource;
    ''' + f'[_source isEqualTo {expected},"donor order changed"] call _check;' + r'''
      _medic setVariable ["fixtureTanks",[[0],[],[]]];_patient setVariable ["fixtureTanks",[[0],[],[]]];
      [[_medic,_patient] call ACME_fnc_ventOxygenSource isEqualTo objNull,"zero tank exposed oxygen"] call _check;
    ''')


def test_efak_packed_charge_integration_attach_readonly_last_charge_once():
    execute(setup() + r'''
      _medic setVariable ["fixtureTanks",[[],[],[]]];_medic setVariable ["fixtureKitCharge",1];
      ACME_fnc_itemCount={params ["_u","_class"];if (_class=="ACM_OxygenTank_425") exitWith {if ((_u getVariable ["fixtureKitCharge",0])>0) then {1} else {0}};[_u,_class] call ace_common_fnc_getCountOfItem};
      efak_medical_fnc_drawCharge={params ["_u","_class"];private _charge=_u getVariable ["fixtureKitCharge",0];if (_charge<=0) exitWith {-1};_kitDraws=_kitDraws+1;_u setVariable ["fixtureKitCharge",_charge-1];_charge-1};
      call _attach;[_kitDraws==0,"packed tank consumed on attach"] call _check;
      call _prepay;private _draw=call _drawLast;_draw call ACME_fnc_ventOxygenDraw;call _ackLast call ACME_fnc_ventOxygenAck;
      [_kitDraws==1 && {_emptyReturns==1} && {(_patient getVariable "ACME_vent_o2Credit")>1.5},"packed final charge mishandled"] call _check;
    ''')


def test_simple_and_advanced_physiology_read_actual_paid_quality_and_keep_settings():
    execute(setup() + r'''
      _patient setVariable ["ACME_vent_bpm",18];_patient setVariable ["ACME_vent_vt",650];_patient setVariable ["ACME_vent_peep",9];
      missionNamespace setVariable ["ACME_vent_simpleMode",true];
      private _air=[_patient] call ACME_fnc_ventEffectiveSettings;
      [(_air select 4)==21 && {(_air select 2)==18},"Simple invented oxygen or changed rate"] call _check;
      call _attach;call _prepay;
      _patient setVariable ["ACME_vent_effectiveFiO2",[_patient,0.5,95] call ACME_fnc_ventOxygenUse];
      [([_patient] call ACME_fnc_ventEffectiveSettings select 4)==95,"paid delivery missing in Simple"] call _check;
      _patient setVariable ["ACME_vent_o2Credit",0.01];
      _patient setVariable ["ACME_vent_effectiveFiO2",[_patient,0.5,95] call ACME_fnc_ventOxygenUse];
      [([_patient] call ACME_fnc_ventEffectiveSettings select 4)==21,"insufficient positive credit falsely delivered95"] call _check;
      missionNamespace setVariable ["ACME_vent_simpleMode",false];
      private _normal=[_patient] call ACME_fnc_ventEffectiveSettings;
      [(_normal select 4)==21 && {(_normal select 3)==650} && {(_normal select 5)==9},"oxygen fallback reset other choices"] call _check;
    ''')


def test_runtime_supply_credit_excluded_from_snapshots_and_cleanup_has_no_refund():
    fields = read("clinicalFields")
    for name in ("Session", "Source", "Medic", "Custody", "Epoch", "Sequence", "Credit", "Pending", "Status", "VerifiedUntil", "ReserveUnits"):
        assert re.search(rf'\["ACME_vent_o2{name}",\s*"",\s*true,\s*false\]', fields)
    for name in ("clinicalReset", "clinicalRestore", "ventPatientClear"):
        assert "call ACME_fnc_ventOxygenClear" in read(name)
    execute(setup() + r'''
      call _attach;call _prepay;[_patient] call ACME_fnc_ventOxygenClear;[_patient] call ACME_fnc_ventOxygenClear;
      [_debits==1 && {_emptyReturns==0} && {(_patient getVariable "ACME_vent_o2Credit")==0},"cleanup minted oxygen/refund"] call _check;
      [!([_patient] call ACME_fnc_ventOxygenState select 0),"cleanup retained source"] call _check;
    ''')


def test_actual_delivered_inspiratory_gas_and_manual_breaths_have_one_consumption_site():
    drive = read("ventDriveTick")
    consumption = drive.index("call ACME_fnc_ventOxygenUse")
    assert drive.index("private _vti =") < consumption < drive.index("call ACME_fnc_ventOxygenation")
    assert "((_mandatoryBpm * _vtiMand) + (_spontBpm * _vtiSpont)) * _dt / 60000" in drive
    assert drive.count("call ACME_fnc_ventOxygenUse") == 1
    for name, volume in (("ventManualBreathCommit", "_vti/1000"), ("ventSimpleManualBreath", "_vt/1000")):
        body = read(name)
        assert body.count("call ACME_fnc_ventOxygenUse") == 1
        assert volume in body
        assert body.index("manualBreathT") < body.index("call ACME_fnc_ventOxygenUse")
        assert '["bvmConnectedOxygen", true]' not in body


def test_stale_control_session_and_provider_order_cannot_touch_replacement_supply():
    execute(setup() + r'''
      call _attach;private _old=_patient getVariable "ACME_vent_o2Session";
      [[_patient,"detach",_medic,21,objNull,"device",1,_old,3] call ACME_fnc_ventOxygenCommit,"detach rejected"] call _check;
      [!([_patient,"attach",_medic,95,_medic,"device",1,"",2] call ACME_fnc_ventOxygenCommit),"delayed older attach reopened supply"] call _check;
      [[_patient,"attach",_medic,95,_medic,"device",1,"",4] call ACME_fnc_ventOxygenCommit,"fresh attach rejected"] call _check;
      call _roundtrip;private _new=_patient getVariable "ACME_vent_o2Session";
      [_new!=_old,"reconnect reused supply identity"] call _check;
      [!([_patient,"detach",_medic,21,objNull,"device",1,_old,5] call ACME_fnc_ventOxygenCommit),"old session detached new supply"] call _check;
      [!([_patient,"fio2",_medic,40,objNull,"device",1,_old,6] call ACME_fnc_ventOxygenCommit),"old control changed replacement FiO2"] call _check;
      [(_patient getVariable "ACME_vent_o2Session")==_new && {(_patient getVariable "ACME_vent_fio2")==95},"stale command mutated replacement"] call _check;
    ''')


def test_expired_verification_stalls_enrichment_without_inventing_depletion():
    execute(setup() + r'''
      call _attach;call _prepay;private _paid=_patient getVariable "ACME_vent_o2Credit";
      _serverTime=104;[_patient] call ACME_fnc_ventOxygenTick;
      [[_patient,0.5,95] call ACME_fnc_ventOxygenUse==21,"stale source verification delivered enriched gas"] call _check;
      [(_patient getVariable "ACME_vent_o2Credit")==_paid && {(_patient getVariable "ACME_vent_o2Status")=="READY"},"missing reply discarded paid gas or invented depletion"] call _check;
      call _roundtrip;
      [[_patient,0.5,95] call ACME_fnc_ventOxygenUse==95 && {_debits==1},"verification recovery debited again"] call _check;
    ''')


def test_retired_sessions_pruned_live_pending_certificate_retained():
    execute(setup() + r'''
      call _attach;private _old=_patient getVariable "ACME_vent_o2Session";
      _medic setVariable ["ACME_vent_o2DrawLedger",createHashMapFromArray [["retired",[1,"draw",true,200,_patient]],[_old,[1,"probe",true,283,_patient]]]];
      [_patient,0.5,95] call ACME_fnc_ventOxygenUse;call _roundtrip;
      private _ledger=_medic getVariable "ACME_vent_o2DrawLedger";
      [count keys _ledger==1 && {_old in _ledger},"probe ledger grew retired history or lost live receipt"] call _check;
      private _draw=call _drawLast;_draw call ACME_fnc_ventOxygenDraw;
      [_debits==1,"live pending certificate pruned before duplicate retry"] call _check;
    ''')


def delivery_setup():
    return setup() + r'''
      private _gasWrites=[];private _driveDelta=0.25;
      ACME_fnc_setVarNetApprox=ACME_fnc_setVarNet;
      ACME_fnc_clinicalTickDelta={_driveDelta};
      ACME_fnc_ventNivEligible={true};
      ACM_breathing_fnc_setRuntimeState={_gasWrites pushBack _this;};
      ACM_core_fnc_setTargetVitalsState={};ACM_core_fnc_setAceMedicalState={};
      ACME_fnc_ventShuntCommit={params ["_p","_value"];_p setVariable ["ACME_vent_shunt",_value];};
      _patient setVariable ["ACME_ETT_Inserted",true];
      _patient setVariable ["ACME_vent_circuit",true];_patient setVariable ["ACME_vent_powerOn",true];
      _patient setVariable ["ACME_vent_configured",true];_patient setVariable ["ACME_vent_connected",true];
      _patient setVariable ["ACME_vent_iface","INVASIVE"];
      missionNamespace setVariable ["ACME_vent_batteryEnabled",false];
    ''' + function("ventManualClaim") + function("ventManualBreathCommit") + function("ventSimpleManualBreath") + \
        'ACME_fnc_ventDriveTick={' + code(read("ventDriveTick").replace('_patient isKindOf "CAManBase"', 'true')) + '};\n' + \
        function("ventOxygenation")


@pytest.mark.parametrize("simple", [False, True])
def test_actual_manual_commit_charges_one_accepted_inspiratory_breath_and_replay_none(simple):
    command = '[_patient,_medic,"device",1,-999,"ventManual:operator:1:device:1:1",1,0,1]' if simple else '[_patient,_medic,"device",1,"ventManual:operator:1:device:1:1",1,1]'
    worker = "ventSimpleManualBreath" if simple else "ventManualBreathCommit"
    execute(delivery_setup() + f'missionNamespace setVariable ["ACME_vent_simpleMode",{str(simple).lower()}];' + r'''
      _patient setVariable ["ACME_vent_simpleEpisode",[missionNamespace getVariable "ACME_vent_simpleMode",1]];
      call _attach;call _prepay;private _before=_patient getVariable "ACME_vent_o2Credit";
    ''' + command + f' call ACME_fnc_{worker};' + r'''
      private _after=_patient getVariable "ACME_vent_o2Credit";
      [abs ((_before-_after)-(0.5*0.74/0.79))<0.00001,"manual commit did not charge actual volume"] call _check;
      [(_patient getVariable "ACME_vent_effectiveFiO2")==95,"accepted manual breath not enriched"] call _check;
    ''' + command + f' call ACME_fnc_{worker};' + r'''
      [(_patient getVariable "ACME_vent_o2Credit")==_after && {_debits==1},"replayed manual breath charged twice"] call _check;
    ''')


@pytest.mark.parametrize("compliance", [1, 0.2])
def test_actual_drive_consumes_pressure_limited_gas_and_excludes_rolling_manual_volumes(compliance):
    execute(delivery_setup() + f'_patient setVariable ["ACME_vent_complianceMult",{compliance}];' + r'''
      missionNamespace setVariable ["ACME_vent_simpleMode",true];
      _patient setVariable ["ACME_vent_simpleManualVolumes",[[CBA_missionTime,485]]];
      call _attach;call _prepay;private _before=_patient getVariable "ACME_vent_o2Credit";
      [_patient] call ACME_fnc_ventDriveTick;
      private _actualVti=_patient getVariable "ACME_vent_vti";
      private _used=_before-(_patient getVariable "ACME_vent_o2Credit");
      // Rounded presentation allows <=0.5mL; actual accounting retains unrounded volume.
      [abs (_used-(_actualVti*12*0.25/60000*0.74/0.79))<0.00003,"drive charged a dial setting or old manual volumes"] call _check;
      [_patient getVariable "ACME_vent_driving" && {(_patient getVariable "ACME_vent_effectiveFiO2")==95},"paid oxygen disabled ventilation"] call _check;
      private _paid=_patient getVariable "ACME_vent_o2Credit";
      _patient setVariable ["ACME_vent_connected",false];[_patient] call ACME_fnc_ventDriveTick;
      [(_patient getVariable "ACME_vent_o2Credit")==_paid && {(_patient getVariable "ACME_vent_effectiveFiO2")==21},"paused circuit consumed gas or retained quality"] call _check;
    ''')


def test_actual_mask_cpap_with_no_spontaneous_breath_delivers_no_tank_gas():
    execute(delivery_setup() + r'''
      missionNamespace setVariable ["ACME_vent_simpleMode",false];
      _patient setVariable ["ACME_vent_mode","CPAP PS HF"];_patient setVariable ["ACME_vent_iface","NON-INVASIVE"];
      _patient setVariable ["ACME_vent_nivMask",true];_patient setVariable ["ACME_vent_psup",0];
      _patient setVariable ["ACME_resp_neuralRR",0];_patient setVariable ["ACME_vent_trigSensCmH2O",0];
      call _attach;call _prepay;private _before=_patient getVariable "ACME_vent_o2Credit";
      [_patient] call ACME_fnc_ventDriveTick;
      [(_patient getVariable "ACME_vent_o2Credit")==_before && {(_patient getVariable "ACME_vent_effectiveFiO2")==21},"apneic CPAP received free oxygen or consumed gas"] call _check;
      [(_patient getVariable "ACME_vent_vti")==0 && {(_patient getVariable "ACME_vent_effectiveRR")==0},"apneic CPAP invented breaths"] call _check;
    ''')


@pytest.mark.parametrize("simple", [False, True])
def test_65_rejected_commands_never_reenable_an_accepted_manual_breath(simple):
    command = '[_patient,_medic,"device",1,0,_id,1,0,_seq]' if simple else '[_patient,_medic,"device",1,_id,_seq,1]'
    worker = "ventSimpleManualBreath" if simple else "ventManualBreathCommit"
    execute(delivery_setup() + f'missionNamespace setVariable ["ACME_vent_simpleMode",{str(simple).lower()}];' + r'''
      _patient setVariable ["ACME_vent_simpleEpisode",[missionNamespace getVariable "ACME_vent_simpleMode",1]];
      call _attach;call _prepay;private _seq=1;private _id="ventManual:operator:1:device:1:1";
    ''' + command + f' call ACME_fnc_{worker};' + r'''
      private _paid=_patient getVariable "ACME_vent_o2Credit";
      _patient setVariable ["ACME_vent_connected",false];
      for "_seq" from 2 to 66 do {
        private _id=format ["ventManual:operator:1:device:1:%1",_seq];
    ''' + command + f' call ACME_fnc_{worker};' + r'''
      };
      _patient setVariable ["ACME_vent_connected",true];CBA_missionTime=13;
      _seq=1;_id="ventManual:operator:1:device:1:1";
    ''' + command + f' call ACME_fnc_{worker};' + r'''
      [(_patient getVariable "ACME_vent_o2Credit")==_paid && {_debits==1} && {count (_patient getVariable "ACME_vent_manualBreathTimes")==1},"65 rejected commands made accepted breath replayable"] call _check;
      _seq=67;_id="ventManual:operator:1:device:1:67";
    ''' + command + f' call ACME_fnc_{worker};' + r'''
      [count (_patient getVariable "ACME_vent_manualBreathTimes")==2 && {(_patient getVariable "ACME_vent_o2Credit")<_paid},"high-water guard blocked a fresh valid breath"] call _check;
    ''')


@pytest.mark.parametrize("simple", [False, True])
def test_65_accepted_breaths_and_locality_transfer_never_allow_old_sequence(simple):
    command = '[_patient,_medic,"device",1,0,_id,1,0,_seq]' if simple else '[_patient,_medic,"device",1,_id,_seq,1]'
    worker = "ventSimpleManualBreath" if simple else "ventManualBreathCommit"
    execute(delivery_setup() + f'missionNamespace setVariable ["ACME_vent_simpleMode",{str(simple).lower()}];' + r'''
      _patient setVariable ["ACME_vent_simpleEpisode",[missionNamespace getVariable "ACME_vent_simpleMode",1]];
      call _attach;call _prepay;
      for "_seq" from 1 to 66 do {
        CBA_missionTime=10+_seq*2;
        private _id=format ["ventManual:operator:1:device:1:%1",_seq];
    ''' + command + f' call ACME_fnc_{worker};' + r'''
        private _pending=_patient getVariable ["ACME_vent_o2Pending",[]];
        if (count _pending==4) then {call _roundtrip;};
      };
      private _paid=_patient getVariable "ACME_vent_o2Credit";
      private _count=count (_patient getVariable "ACME_vent_manualBreathTimes");
      private _debitsBefore=_debits;private _seq=1;private _id="ventManual:operator:1:device:1:1";
      _patientLocal=false;_patientLocal=true;CBA_missionTime=CBA_missionTime+3;
    ''' + command + f' call ACME_fnc_{worker};' + r'''
      [(_patient getVariable "ACME_vent_o2Credit")==_paid && {_debits==_debitsBefore} && {count (_patient getVariable "ACME_vent_manualBreathTimes")==_count},"late accepted-command replay survived receipt eviction/locality"] call _check;
      [count keys (_patient getVariable "ACME_vent_manualCommands")==1,"manual high-water history grew per breath"] call _check;
    ''')


@pytest.mark.parametrize("simple", [False, True])
def test_manual_producer_mints_monotonic_provider_commands_across_panel_reopen(simple):
    execute(delivery_setup() + function("ventManualBreath") + f'missionNamespace setVariable ["ACME_vent_simpleMode",{str(simple).lower()}];' + r'''
      private _requests=[];ACME_fnc_ownerDispatch={_requests pushBack (_this select 2);};
      _patient setVariable ["ACME_vent_simpleEpisode",[missionNamespace getVariable "ACME_vent_simpleMode",1]];
      uiNamespace setVariable ["ACME_vent_target",_patient];
      call ACME_fnc_ventManualBreath;
      uiNamespace setVariable ["ACME_vent_manualRequestSerial",0];
      call ACME_fnc_ventManualBreath;
      [_medic getVariable "ACME_vent_manualCommandSerial"==2,"panel reset replayed provider sequence"] call _check;
      if (missionNamespace getVariable "ACME_vent_simpleMode") then {
        private _all=_events select {(_x select 0)=="ACME_ventSimpleManualBreath"};
        private _first=(_all select 0) select 1;private _second=(_all select 1) select 1;
        [(_first select 8)==1 && {(_second select 8)==2} && {(_first select 5)=="ventManual:operator:1:device:1:1"},"Simple producer omitted canonical identity/sequence"] call _check;
      } else {
        private _first=_requests select 0;private _second=_requests select 1;
        [(_first select 5)==1 && {(_second select 5)==2} && {(_first select 4)=="ventManual:operator:1:device:1:1"} && {(_first select 6)==1},"advanced producer omitted episode/sequence"] call _check;
      };
    ''')


def test_manual_claim_rejects_legacy_identity_wrong_episode_and_nonpositive_sequence():
    execute(delivery_setup() + r'''
      _patient setVariable ["ACME_vent_simpleEpisode",[false,1]];
      [!([_patient,_medic,"device",1,1,1,"arbitrary-legacy-id",false] call ACME_fnc_ventManualClaim),"legacy arbitrary ID accepted"] call _check;
      [!([_patient,_medic,"device",1,1,0,"ventManual:operator:1:device:1:0",false] call ACME_fnc_ventManualClaim),"zero sequence accepted"] call _check;
      [!([_patient,_medic,"device",1,2,1,"ventManual:operator:1:device:2:1",false] call ACME_fnc_ventManualClaim),"old episode accepted"] call _check;
      [!([_patient,_medic,"device",0,1,1,"ventManual:operator:0:device:1:1",false] call ACME_fnc_ventManualClaim),"stale clinical epoch accepted"] call _check;
      [[_patient,_medic,"device",1,1,1,"ventManual:operator:1:device:1:1",false] call ACME_fnc_ventManualClaim,"valid command blocked after invalid legacy IDs"] call _check;
    ''')
