"""Execute corpse device controls and suction against production SQF.

Engine objects, UI, network transport and inventory primitives are fixtures.
Eligibility, protocol receipts, pressure/volume arithmetic and airway debits run
from the checked-out source. Arma scheduling/rendering are not certified here.
"""
import pytest

from test_b156_procedure_supplies import primitives, supply_setup
from test_historical_airway_execution import suction_setup as fluid_setup
from test_historical_cardiac_execution import code, setup as cardiac_setup
from source_scan import lex, matching, split_args
from test_menu_death_lifecycle import ROOT, execute, read


def source(name):
    text = read(name).replace('serverTime', '_serverTime')
    text = text.replace('getPlayerUID _medic', '"provider"').replace('netId _medic', '"provider"')
    text = text.replace('(_x select 1) == _medic', '(_x select 1) isEqualTo _medic')
    text = text.replace('(_proof param [0, objNull]) == _patient', '(_proof param [0, objNull]) isEqualTo _patient')
    # Adapt the inner HashMap engine call first; the shared primitive adapter
    # intentionally handles one expression at a time, not overlapping edits.
    text = text.replace('_localReceipts getOrDefault [_localKey, []]', '([_localReceipts,[_localKey,[]]] call _mapDefault)')
    return primitives(code(text))


def function(name):
    return 'ACME_fnc_'+name+'={'+source(name)+'};\n'


def setup():
    return cardiac_setup()+supply_setup()+'''
        private _serverTime=100;
        private _clinical=[];
        private _near=true;
        private _allowed=true;
        private _registrations=0;
        ACME_fnc_procedureAllowed={_allowed};
        ACME_fnc_itemCount=ace_common_fnc_getCountOfItem;
        ACME_fnc_ventRecoveryNear={_near};
        ACME_fnc_setVarNet={params ["_p","_key","_value"];_p setVariable [_key,_value];};
        ACM_breathing_fnc_setRuntimeState={_clinical pushBack _this;};
        ACME_fnc_ownerRegister={_registrations=_registrations+1;};
        ACME_fnc_ventDeviceFields={["ACME_vent_vt","ACME_vent_fio2"]};
        CBA_fnc_serverEvent={_events pushBack _this;};
        ACME_fnc_ventEffectiveSettings={[true,"SIMPLE",12,500,95,5,0,0,0,0,0,35]};
        _patientAlive=false;
    '''


@pytest.mark.parametrize('alive', [False, True])
def test_device_inventory_take_works_once_for_live_and_dead_patient(alive):
    execute(setup()+function('ventInventoryLocal')+f'_patientAlive={str(alive).lower()};'+'''
        _medic setVariable ["fixtureStock",["ACME_Ventilator"]];
        _medic setVariable ["ACME_vent_vt",450];
        ["take","device-1",_medic,_patient] call ACME_fnc_ventInventoryLocal;
        ["take","device-1",_medic,_patient] call ACME_fnc_ventInventoryLocal;
        [count _debits==1,"inventory take repeated or rejected valid patient"] call _check;
        [count _events==2,"duplicate did not acknowledge existing receipt"] call _check;
        private _ack=(_events select 1) select 1;
        [_ack select 3,"valid device take reported failure"] call _check;
        [["ACME_vent_vt",450] in (_ack select 4),"returned device settings lost"] call _check;
    ''')


@pytest.mark.parametrize('blocker', [
    '_alive=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_near=false;', '_allowed=false;', '_patient=objNull;',
])
def test_dead_patient_inventory_take_preserves_provider_and_supply_guards(blocker):
    execute(setup()+function('ventInventoryLocal')+'''
        _medic setVariable ["fixtureStock",["ACME_Ventilator"]];
    '''+blocker+'''
        ["take","device-1",_medic,_patient] call ACME_fnc_ventInventoryLocal;
        [count _debits==0,"invalid provider took a device"] call _check;
        [!(((_events select 0) select 1) select 3),"invalid take acknowledged success"] call _check;
    ''')


def breath_setup(simple):
    return setup()+function('ventSimpleManualBreath' if simple else 'ventManualBreathCommit')+'''
        missionNamespace setVariable ["ACME_vent_simpleMode",true];
        _patient setVariable ["ACME_vent_simpleEpisode",[true,2]];
        _patient setVariable ["ACME_vent_custodyId","device-1"];
        _patient setVariable ["ACME_vent_circuit",true];
        _patient setVariable ["ACME_vent_powerOn",true];
        _patient setVariable ["ACME_vent_configured",true];
        _patient setVariable ["ACME_vent_connected",true];
        _patient setVariable ["ACME_vent_iface","INVASIVE"];
        _patient setVariable ["ACME_ETT_Inserted",true];
        _patient setVariable ["ACME_vent_fio2",95];
        _patient setVariable ["ACME_vent_compliance",0.2];
        _patient setVariable ["ACME_vent_baroDose",0.4];
    '''


def breath_call(simple, ident='breath-1', custody='device-1', epoch=1, episode=2):
    if simple:
        return f'[_patient,_medic,"{custody}",{epoch},0,"{ident}",{episode}] call ACME_fnc_ventSimpleManualBreath;'
    return f'[_patient,_medic,"{custody}",{epoch},"{ident}"] call ACME_fnc_ventManualBreathCommit;'


@pytest.mark.parametrize('simple', [False, True], ids=['advanced','simple'])
@pytest.mark.parametrize('alive', [False, True], ids=['dead','living'])
def test_manual_breath_has_mechanical_feedback_but_only_living_gas_exchange(simple,alive):
    execute(breath_setup(simple)+f'_patientAlive={str(alive).lower()};'+breath_call(simple)+'''
        [count _events==1,"valid manual breath did not acknowledge"] call _check;
        [(_patient getVariable ["ACME_vent_vti",0])>0 && {(_patient getVariable ["ACME_vent_vte",0])>0},"manual breath produced no measured volumes"] call _check;
        [(_patient getVariable ["ACME_vent_manualRR",0])==1,"manual device count missing"] call _check;
        [count _clinical==(if (_patientAlive) then {1} else {0}),"corpse breath restored gas exchange or living breath lost it"] call _check;
        if (!_patientAlive) then {
            [isNil {_patient getVariable "ACME_bvm_lastBreathServer"},"corpse breath wrote native gas exchange timestamp"] call _check;
            [(_patient getVariable ["ACME_vent_baroDose",0])==0.4,"corpse breath accumulated barotrauma"] call _check;
        };
    '''+breath_call(simple)+'''
        [count _events==1 && {(_patient getVariable ["ACME_vent_manualRR",0])==1},"duplicate breath repeated device delivery"] call _check;
    ''')


@pytest.mark.parametrize('simple', [False, True], ids=['advanced','simple'])
@pytest.mark.parametrize('blocker', [
    '_alive=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_near=false;', '_allowed=false;',
    '_patient setVariable ["ACME_vent_custodyId","different-device"];',
    '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_patient setVariable ["ACME_vent_recovering",true];',
    '_patient setVariable ["ACME_vent_configured",false];',
    '_patient setVariable ["ACME_vent_connected",false];',
    '_patient setVariable ["ACME_ETT_Inserted",false];',
    'missionNamespace setVariable ["ACME_sys_vent",false];',
])
def test_corpse_breath_keeps_owner_device_provider_and_airway_guards(simple,blocker):
    execute(breath_setup(simple)+blocker+breath_call(simple)+'''
        [count _events==0 && {count _clinical==0},"invalid corpse breath was delivered"] call _check;
        [isNil {_patient getVariable "ACME_vent_vti"},"invalid breath wrote device output"] call _check;
    ''')


@pytest.mark.parametrize('simple', [False, True], ids=['advanced','simple'])
def test_dead_patient_manual_breath_keeps_refractory_timing(simple):
    execute(breath_setup(simple)+breath_call(simple)+breath_call(simple,'too-soon')+'''
        [count _events==1,"corpse bypassed breath interval"] call _check;
        CBA_missionTime=12;
    '''+breath_call(simple,'next-breath')+'''
        [count _events==2 && {(_patient getVariable ["ACME_vent_manualRR",0])==2},"eligible subsequent breath rejected"] call _check;
    ''')


def test_corpse_device_enrollment_initializes_simple_episode_without_physiology_worker():
    registration=source('ventCustodyInit').split('if (!true) exitWith {};',1)[0]
    assert 'missionNamespace setVariable ["ACME_vent_custody",' not in registration
    execute(setup()+'''
        private _byName=createHashMap;
        CBA_fnc_addEventHandler={_byName set [_this select 0,_this select 1];};
        ACM_circ_activePatients=[];
        ACME_circ_activePatients=[];
        missionNamespace setVariable ["ACME_vent_simpleMode",true];
    '''+registration+'''
        [_patient] call (_byName get "ACME_ventPatientEnroll");
        [(_patient getVariable ["ACME_vent_simpleEpisode",[]]) isEqualTo [true,1],"corpse device lacks simple protocol episode"] call _check;
        [ACME_circ_activePatients isEqualTo [],"corpse device started physiology scheduler"] call _check;
        [_patient] call (_byName get "ACME_ventPatientEnroll");
        [(_patient getVariable ["ACME_vent_simpleEpisode",[]]) isEqualTo [true,1],"duplicate enrollment invalidated episode"] call _check;
        missionNamespace setVariable ["ACME_vent_simpleMode",false];
        [_patient] call (_byName get "ACME_ventPatientEnroll");
        [(_patient getVariable ["ACME_vent_simpleEpisode",[]]) isEqualTo [false,2],"new device mode failed to invalidate prior episode"] call _check;
        _patientAlive=true;
        [_patient] call (_byName get "ACME_ventPatientEnroll");
        [ACME_circ_activePatients isEqualTo [_patient],"living device failed to enroll physiology"] call _check;
    ''')


def suction_setup():
    return setup()+fluid_setup()+function('suctionStateLocal')+function('suctionPublish')+'''
        ACME_fnc_suctionSfxStop={};
        _patientAlive=false;
        _medic setVariable ["fixtureStock",["ACM_ACCUVAC"]];
        uiNamespace setVariable ["ACME_laryngo_dlg",missionNamespace];
        uiNamespace setVariable ["ACME_laryngo_patient",_patient];
        uiNamespace setVariable ["ACME_laryngo_medic",_medic];
        uiNamespace setVariable ["ACME_suctionToken","session"];
        uiNamespace setVariable ["ACME_suctionEpoch",1];
        uiNamespace setVariable ["ACME_suction_type",1];
        uiNamespace setVariable ["ACME_laryngo_held","suction"];
        uiNamespace setVariable ["ACME_laryngo_sucInMouth",true];
        uiNamespace setVariable ["ACME_laryngo_sucOn",true];
        _patient setVariable ["ACME_suctionSessions",[]];
        ACME_fnc_ownerDispatch={
            _events pushBack _this;
            if ((_this select 1)=="suctionState") then {(_this select 2) call ACME_fnc_suctionStateLocal;};
        };
    '''


@pytest.mark.parametrize('mode,controls', [
    ('hand',''),
    ('salad','uiNamespace setVariable ["ACME_laryngo_sucPinned",true]; uiNamespace setVariable ["ACME_laryngo_sucPinRel",[0.2,0.4]];'),
    ('manual','uiNamespace setVariable ["ACME_suction_type",0]; uiNamespace setVariable ["ACME_suction_sqT0",0]; _medic setVariable ["ACME_suctionManualSession",[_patient,"session",0]];'),
])
def test_corpse_suction_publish_session_and_bounded_fluid_debit_then_close(mode,controls):
    execute(suction_setup()+controls+'''
        [true] call ACME_fnc_suctionPublish;
        private _sessions=_patient getVariable ["ACME_suctionSessions",[]];
    '''+f'[count _sessions==1 && {{((_sessions select 0) select 3)=="{mode}"}},"corpse suction did not publish active operator lease"] call _check;'+'''
        [_patient,_medic,1,"drain-1",_stamp,2,"session"] call ACME_fnc_laryngoFluidDrainLocal;
        [(([_patient] call ACME_fnc_laryngoFluidState) select 2)==2,"corpse retained fluid did not drain"] call _check;
        [_patient,_medic,1,"drain-1",_stamp,2,"session"] call ACME_fnc_laryngoFluidDrainLocal;
        [(([_patient] call ACME_fnc_laryngoFluidState) select 2)==2,"duplicate corpse drain applied twice"] call _check;
        [true,true] call ACME_fnc_suctionPublish;
        [(_patient getVariable ["ACME_suctionSessions",[]]) isEqualTo [],"closing corpse suction kept active session"] call _check;
        [_patient,_medic,1,"drain-2",_stamp,2,"session"] call ACME_fnc_laryngoFluidDrainLocal;
        [(([_patient] call ACME_fnc_laryngoFluidState) select 2)==2,"closed corpse session still drained"] call _check;
        [true] call ACME_fnc_suctionPublish;
        [(_patient getVariable ["ACME_suctionSessions",[]]) isEqualTo [],"closed token reopened corpse suction"] call _check;
        [count _clinical==0,"corpse suction started gas exchange"] call _check;
    ''')


@pytest.mark.parametrize('blocker', [
    '_alive=false;', '_medic setVariable ["ACE_isUnconscious",true];',
    '_distance=6;', '_patient setVariable ["ACME_clinicalEpoch",2];',
    '_medic setVariable ["fixtureStock",[]];',
])
def test_corpse_suction_preserves_provider_epoch_range_and_supply_guards(blocker):
    execute(suction_setup()+blocker+'''
        [true] call ACME_fnc_suctionPublish;
        [(_patient getVariable ["ACME_suctionSessions",[]]) isEqualTo [],"invalid corpse operator obtained suction session"] call _check;
        [_patient,_medic,1,"invalid",_stamp,2,"session"] call ACME_fnc_laryngoFluidDrainLocal;
        [(([_patient] call ACME_fnc_laryngoFluidState) select 2)==4,"invalid corpse operator drained fluid"] call _check;
    ''')


def test_corpse_drive_tick_tracks_mode_episode_and_exits_before_physiology():
    execute(setup()+function('ventDriveTick')+'''
        ACME_fnc_clinicalTickDelta={0.25};
        missionNamespace setVariable ["ACME_vent_simpleMode",true];
        [_patient] call ACME_fnc_ventDriveTick;
        [(_patient getVariable ["ACME_vent_simpleEpisode",[]]) isEqualTo [true,1],"drive failed to initialize Boolean mode episode"] call _check;
        [_patient] call ACME_fnc_ventDriveTick;
        [(_patient getVariable ["ACME_vent_simpleEpisode",[]]) isEqualTo [true,1],"same mode advanced episode"] call _check;
        missionNamespace setVariable ["ACME_vent_simpleMode",false];
        [_patient] call ACME_fnc_ventDriveTick;
        [(_patient getVariable ["ACME_vent_simpleEpisode",[]]) isEqualTo [false,2],"drive failed to invalidate changed mode"] call _check;
        [count _clinical==0 && {isNil {_patient getVariable "ACME_vent_driving"}},"corpse mode tracking restarted physiology"] call _check;
    ''')


def simple_setting_callback():
    """Load the actual registered CBA callback, retaining its direct _this value."""
    text=(ROOT/'addons/acm_extended/XEH_preInit.sqf').read_text()
    ts=lex(text); pairs=matching(ts)
    start=next(i-1 for i,t in enumerate(ts) if t.kind=='string' and t.value=='ACME_vent_simpleMode')
    args=split_args(ts,start+1,pairs[start],pairs)
    assert len(args)==7 and args[6][0].value=='{' and args[6][-1].value=='}'
    callback=text[args[6][0].offset+1:args[6][-1].offset]
    # Engine membership and object locality/liveness are explicit boundaries.
    # The production callback, generation comparison and writer stay intact.
    callback=callback.replace('allDeadMen','_deadUnits')
    callback=callback.replace('local _patient','(_patient getVariable ["TEST_local",true])')
    callback=callback.replace('alive _patient','(_patient getVariable ["TEST_alive",false])')
    return 'private _onSimpleModeChanged={'+code(callback)+'};'


def test_actual_simple_setting_callback_refreshes_corpse_and_fences_previous_mode_packets():
    execute(breath_setup(True)+simple_setting_callback()+'''
        private _deadUnits=[_patient];
        ACME_circ_activePatients=[];
        _patient setVariable ["ACME_vent_onPatient",true];
        _patient setVariable ["ACME_vent_simpleEpisode",[false,2]];
        true call _onSimpleModeChanged;
        [(_patient getVariable ["ACME_vent_simpleEpisode",[]]) isEqualTo [true,3],"actual setting callback did not refresh attached corpse"] call _check;
        true call _onSimpleModeChanged;
        [(_patient getVariable ["ACME_vent_simpleEpisode",[]]) isEqualTo [true,3],"duplicate setting callback invalidated current request"] call _check;
    '''+breath_call(True,episode=3)+'''
        [count _events==1,"first current-mode corpse breath failed after setting callback"] call _check;
        missionNamespace setVariable ["ACME_vent_simpleMode",false];
        false call _onSimpleModeChanged;
        [(_patient getVariable ["ACME_vent_simpleEpisode",[]]) isEqualTo [false,4],"disabling mode did not advance corpse generation"] call _check;
        missionNamespace setVariable ["ACME_vent_simpleMode",true];
        true call _onSimpleModeChanged;
        [(_patient getVariable ["ACME_vent_simpleEpisode",[]]) isEqualTo [true,5],"reenabling mode reused old corpse generation"] call _check;
        CBA_missionTime=12;
    '''+breath_call(True,'delayed-before-toggle',episode=3)+'''
        [count _events==1,"delayed pre-toggle breath crossed mode generation"] call _check;
    '''+breath_call(True,'current-after-toggle',episode=5)+'''
        [count _events==2,"current post-toggle corpse breath failed"] call _check;
        [count _clinical==0 && {_handlers isEqualTo []} && {ACME_circ_activePatients isEqualTo []},"setting callback enrolled corpse physiology or scheduler"] call _check;
    ''')


@pytest.mark.parametrize('blocker', [
    '_patient setVariable ["TEST_local",false];',
    '_patient setVariable ["TEST_alive",true];',
    '_patient setVariable ["ACME_vent_onPatient",false];',
    '_deadUnits=[objNull];',
])
def test_simple_setting_callback_only_changes_local_attached_corpse_devices(blocker):
    execute(setup()+simple_setting_callback()+'''
        private _deadUnits=[_patient];
        _patient setVariable ["ACME_vent_onPatient",true];
        _patient setVariable ["ACME_vent_simpleEpisode",[false,2]];
    '''+blocker+'''
        true call _onSimpleModeChanged;
        [(_patient getVariable ["ACME_vent_simpleEpisode",[]]) isEqualTo [false,2],"setting callback modified ineligible or remote device"] call _check;
        [count _clinical==0 && {_handlers isEqualTo []},"setting callback created physiology work"] call _check;
    ''')
