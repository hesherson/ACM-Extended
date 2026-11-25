"""Regression contract for B397 vascular transit and restored B135 hemostasis.

Executes the extracted production admission and transit blocks in the project's
SQF-VM harness; engine cardiac output, CPR, locality and exposure are mocked.
"""
from test_menu_death_lifecycle import ROOT, adapt, execute, read

CORE = ROOT / "addons/core/overrides/fnc_medicationLocal.sqf"
VOLUME = ROOT / "addons/circulation/functions/fnc_getBloodVolumeChange.sqf"
DAMAGE = ROOT / "addons/damage/functions"


def excerpts():
    med = CORE.read_text().split("private _holdVascular = false;", 1)[1]
    med = "private _holdVascular = false;" + med.split("// Exit with basic medication handling", 1)[0]
    med = adapt(med).replace("IN_CRDC_ARRST(_patient)", "_arrest")
    med = med.replace("finite _nativeCO", "(_nativeCO isEqualType 0)")
    transit = VOLUME.read_text().split("private _transit = ", 1)[1]
    transit = "private _transit = " + transit.split("private _TXAEffect = ", 1)[0]
    transit = adapt(transit).replace("alive _unit", "_patientAlive").replace("local _unit", "_patientLocal")
    return med, transit


def setup():
    med, transit = excerpts()
    return r'''
        private _arrest=true;
        private _cpr=false;
        private _co=0;
        private _epoch=1;
        private _patientLocal=true;
        private _unit=_patient;
        private _deltaT=1;
        private _inCardiacArrest=true;
        private _fluidPerfusionOpen=false;
        private _received=[];
        ACM_core_fnc_cprActive={_cpr};
        ace_medical_status_fnc_getCardiacOutput={_co};
        ACME_fnc_clinicalEpoch={_epoch};
        ACME_fnc_ownerRegister={};
        _patient setVariable ["ACME_vascularTransit",[]];
        ace_medical_treatment_fnc_medicationLocal={
            params ["_patient","_bodyPart","_classname","_dose","_iv","_alreadyAdmitted","_delivery"];
    ''' + med + r'''
            _received pushBack _dose;
        };
        private _transport={
    ''' + transit + r'''
        };
        private _step={
            CBA_missionTime=CBA_missionTime+1;
            _inCardiacArrest=_arrest;
            _fluidPerfusionOpen=_cpr || {!_arrest && {_co>0.0001}};
            call _transport;
        };
        private _push={[_patient,"leftarm","TXA_IV",1000,true,false,[]] call ace_medical_treatment_fnc_medicationLocal;};
    '''


def test_no_flow_no_exposure_and_cpr_releases_once():
    execute(setup() + '''
        call _push;
        for "_i" from 1 to 90 do {call _step;};
        [count _received==0,"pulseless IV push reached systemic compartment"] call _check;
        [count (_patient getVariable "ACME_vascularTransit")==1,"pending dose lost"] call _check;
        _cpr=true;
        for "_i" from 1 to 8 do {call _step;};
        [count _received==0,"CPR transit completed early"] call _check;
        _cpr=false;
        for "_i" from 1 to 90 do {call _step;};
        [count _received==0,"interrupted CPR credited absent flow"] call _check;
        _cpr=true;
        for "_i" from 1 to 16 do {call _step;};
        [_received isEqualTo [1000],"CPR failed to release dose exactly once"] call _check;
        for "_i" from 1 to 20 do {call _step;};
        [_received isEqualTo [1000],"duplicate systemic admission"] call _check;
    ''')


def test_rosc_releases_and_preserves_prior_exposure():
    execute(setup() + '''
        _arrest=false; _co=4;
        call _push;
        _arrest=true; _co=0;
        call _push;
        for "_i" from 1 to 10 do {call _step;};
        [_received isEqualTo [1000],"prior exposure or pending admission altered"] call _check;
        _arrest=false; _co=4;
        for "_i" from 1 to 7 do {call _step;};
        [_received isEqualTo [1000,1000],"ROSC did not release exact pending dose"] call _check;
    ''')


def test_epoch_reset_drops_old_dose():
    execute(setup() + '''
        call _push; _epoch=2;
        _arrest=false; _co=4;
        for "_i" from 1 to 10 do {call _step;};
        [_received isEqualTo [],"reset replayed old dose"] call _check;
        [(_patient getVariable "ACME_vascularTransit") isEqualTo [],"stale queue retained"] call _check;
    ''')


def test_state_and_hemostasis_source_contract():
    assert '["ACME_vascularTransit", "", true, true]' in read("clinicalFields")
    assert '["ACME_vascularTransit", []]' in read("deadPhysiologyFreeze")
    assert 'ACME_vascularTransit' in read("clinicalNeedsTick")
    for name, limit in (("fnc_handleCoagulationPFH.sqf", "3.8"), ("fnc_handleIBCoagulationPFH.sqf", "3.6")):
        source = (DAMAGE / name).read_text()
        assert '|| {_txaCount > 0.1}' in source
        assert f'GET_EFF_BLOOD_VOLUME(_patient) < {limit} && {{_txaCount < 0.1}}' in source
        assert '_clotStrength < 0.10' in source
    volume = VOLUME.read_text()
    assert 'if (_TXAEffect > 0.5) then {' in volume
    assert 'if (!_fluidPerfusionOpen) then {_bagChange = 0;};' in volume
    assert volume.index('setVariable ["ACME_vascularTransit", _keep, true]') < volume.index('([_unit] + _x) call ACEFUNC(medical_treatment,medicationLocal)')
