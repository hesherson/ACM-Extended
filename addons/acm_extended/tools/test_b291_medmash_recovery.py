"""Execute late-state owner recovery and the source-separated thermal writer.

Native objects, publication transport and unrelated patient workers are explicit
boundaries. The existing1Hz owner callback, disease reconciliation, temperature
commit and publication suppression execute production SQF.
"""
import pytest

from test_b291_medmash_phys import wrapped, component_reconcile
from test_b291_ocular_integration import function as ocular_function
from test_b282_owner_recovery_execution import setup as recovery_setup
from test_b156_coagulation_runtime import setup as coag_setup, function as coag_function
from test_b205_network_snapshot_execution import setup as network_setup
from test_b281_flight_scheduler import adapt as engine, function as flight_function
from test_menu_death_lifecycle import execute, read


def thermal_setup():
    text = read('hypothermiaTick')
    start = text.index('    // Infection supplies a fever setpoint')
    stop = text.index('    // severe hypothermia', start)
    return coag_setup() + network_setup() + coag_function('hypothermiaTemperatureCommit') + r'''
        ace_medical_status_fnc_getBloodPressure={[80,120]};
        private _thermalStep={private _u=_patient;
            private _feverOffset=_u getVariable ["ACM_infection_Fever_Offset",0];
            private _feverActive=_u getVariable ["ACME_infectionFeverActive",false];
    ''' + engine(text[start:stop]) + r'''};
    '''


def test_fever_recovery_evidence_is_published_once_and_new_owner_can_continue_resolving_it():
    execute(thermal_setup() + r'''
        _patient setVariable ["ACME_hypo_temp",37];
        _patient setVariable ["ACM_infection_Fever_Offset",2.6];
        call _thermalStep;call _thermalStep;
        [(_wire get "acme_infectionfeveractive")=="true","fever recovery evidence stayed on old owner"] call _check;
        [count (_packets select {(_x select 0)=="acme_infectionfeveractive"})==1,"steady fever marker generated duplicate publications"] call _check;
        // New-owner object state contains only the value observed on the wire.
        _ownerNum=8;
        _patient setVariable ["ACME_infectionFeverActive",(_wire get "acme_infectionfeveractive")=="true"];
        _patient setVariable ["ACM_infection_Fever_Offset",0];
        _patient setVariable ["ACME_hypo_temp",39.4];
        call _thermalStep;
        [(_patient getVariable "ACME_hypo_temp")<39.4,"treated fever became stranded after ownership transfer"] call _check;
    ''')


@pytest.mark.parametrize('temperature', [36.9, 37, 37.005])
def test_cleared_fever_retires_recovery_evidence_at_or_below_normal_temperature(temperature):
    execute(thermal_setup() + f'''
        _patient setVariable ["ACME_hypo_temp",{temperature}];
        _patient setVariable ["ACM_infection_Fever_Offset",0];
        _patient setVariable ["ACME_infectionFeverActive",true];
        call _thermalStep;call _thermalStep;
        [!(_patient getVariable "ACME_infectionFeverActive"),"resolved fever pinned thermal maintenance"] call _check;
        [(_wire get "acme_infectionfeveractive")=="false","fever endpoint was not published"] call _check;
        [count (_packets select {{(_x select 0)=="acme_infectionfeveractive"}})==1,"resolved marker produced repeated heartbeats"] call _check;
    ''')


def test_lower_positive_infection_setpoint_gradually_reduces_an_already_high_fever():
    execute(thermal_setup() + r'''
        _patient setVariable ["ACME_hypo_temp",39.6];
        _patient setVariable ["ACM_infection_Fever_Offset",0.6];
        call _thermalStep;
        private _temperature=_patient getVariable "ACME_hypo_temp";
        [_temperature<39.6 && {_temperature>37.6},"antibiotic stage reduction neither cooled gradually nor respected its remaining fever setpoint"] call _check;
        [_patient getVariable ["ACME_infectionFeverActive",false],"partial infection recovery erased ongoing fever evidence"] call _check;
    ''')


def test_existing_native_shock_precedence_is_unchanged_without_any_medmash_disease_drive():
    execute(coag_setup() + coag_function('setVarNet') + flight_function('shockPhenotypeTick') + r'''
        ACME_shock_activePatients=[_patient];
        _patient setVariable ["ACME_circ_State",createHashMapFromArray [["shockActive",true],["shockSeverity",0.5]]];
        _patient setVariable ["ACM_circulation_Blood_Volume",4.5];
        call ACME_fnc_shockPhenotypeTick;
        [(_patient getVariable "ACME_shock_phenotype")=="distributive","new features changed native shock precedence when absent"] call _check;
        [(_patient getVariable "ACME_shock_resistDelta")==-24 && {(_patient getVariable "ACME_shock_hrAdj")==19},"native shock HR/SVR drive changed without disease"] call _check;
    ''')


def late_setup():
    return recovery_setup() + wrapped('medmashReconcile') + ocular_function('shieldSource') + ocular_function('shieldRecover') + ''.join(
        component_reconcile(n) for n in ('burns','infection','ophthalmology')) + r'''
        private _finite={private _v=if (_this isEqualType []) then {_this select 0} else {_this};_v isEqualType 0};
        private _medicLocal=true;private _serverClock=12;private _componentTicks=[];
        ACM_burns_burnsEnabled=true;
        ACM_burns_fnc_tickPatient={if (((_this select 0) getVariable ["ACM_burns_SystemicBurden",0])>0) then {_componentTicks pushBack "burn";};};
        ACM_infection_fnc_handleInfectionPFH={_componentTicks pushBack "infection";};
        ACM_ophthalmology_fnc_structuralTick={_componentTicks pushBack "eye";};
    '''


@pytest.mark.parametrize('component,field,value', [
    ('burns','ACM_burns_SystemicBurden','0.3'),
    ('infection','ACM_infection_Infection_EligibleTime','-100'),
    ('ophthalmology','ACM_ophthalmology_eyeInjuries','[0.4,1]'),
])
def test_late_disease_fields_recover_their_native_registry_in_existing_one_hz_callback(component, field, value):
    execute(late_setup() + f'''
        ACME_clinical_activePatients=[_patient];
        _patient setVariable ["{field}",{value}];
        [([_patient] call ACME_fnc_ownerRegisterNeedsRecovery),"late disease state did not request bounded owner recovery"] call _check;
        call _sharedTick;
        [_patient in (missionNamespace getVariable ["ACM_{component}_activePatients",[]]),"late disease waited for slow world discovery"] call _check;
        [count _registerCalls==1,"late disease caused missing or duplicate owner registration"] call _check;
        call _sharedTick;
        [count _registerCalls==1,"already enrolled disease repeatedly rebuilt the owner"] call _check;
    ''')


def test_settled_anatomical_burn_does_not_request_periodic_owner_recovery():
    execute(late_setup() + r'''
        _patient setVariable ["ACM_burns_BurnBurden",0.4];
        _patient setVariable ["ACM_burns_SystemicBurden",0];
        [!([_patient] call ACME_fnc_ownerRegisterNeedsRecovery),"settled anatomy reactivated systemic burn maintenance"] call _check;
    ''')
