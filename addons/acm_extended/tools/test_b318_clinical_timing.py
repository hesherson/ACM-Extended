"""Execute clinical timing policy, half-life math, fridge aging, and infusion batching."""

import pytest

from test_b288_world_persistence import setup as fridge_setup
from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import ROOT, adapt, execute, read


def definitions():
    profile = adapt(read('medicationHalfLife')).replace(
        'missionNamespace getVariable "ACME_medicationKinetics"',
        'missionNamespace getVariable ["ACME_medicationKinetics",createHashMap]')
    profile = profile.replace('if (isNil "_table")', 'if (count _table == 0)')
    effect = adapt((ROOT / 'addons/circulation/functions/fnc_getMedicationEffect.sqf').read_text())
    kinetic_effect = read('medicationKineticEffect').replace(
        'linearConversion [_onset+_plateau,_nativeDuration,_age,1,0,true]',
        '[_onset+_plateau,_nativeDuration,_age,1,0,true] call _linear')
    for route, value in [('IM',0),('IV',1),('PO',2),('INHALE',3)]:
        effect = effect.replace('ACM_ROUTE_'+route,str(value))
    primitive = 'private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];if (_key in _map) then {_map get _key} else {_default}};'
    return primitive + ''.join(f'{name}={{{map_defaults(source)}}};' for name,source in [
        ('ACME_fnc_medicationKinetics',read('medicationKinetics')),
        ('ACME_fnc_medicationHalfLife',profile),
        ('ACME_fnc_medicationResidual',read('medicationResidual')),
        ('ACME_fnc_medicationKineticEffect',kinetic_effect),
        ('ACM_circulation_fnc_getMedicationEffect',effect),
        ('ACME_fnc_compactMedicationRecords',read('compactMedicationRecords'))
    ])


@pytest.mark.parametrize('name,half', [('Adenosine_IV',5),('Epinephrine_IV',180),('Norepinephrine_IV',144),
                                       ('Esmolol_IV',540),('Morphine_IV',7200),('TXA_IV',7200),('Ceftriaxone_IV',25200)])
def test_effect_halves_and_survives_native_record_deadline(name, half):
    execute(definitions() + f'''
        private _row = ["{name}",0,2,7,0,0,0,1,1,0,0,0,1,"Default",0];
        private _elapsed = {half} + 3;
        [abs (([_row,_elapsed] call ACME_fnc_medicationKineticEffect) - 0.5) < 0.0001,"incorrect clinical half-life"] call _check;
        [abs (([_row,{half},"physical"] call ACME_fnc_medicationKineticEffect) - 0.5) < 0.0001,"incorrect IV clearance"] call _check;
        [[_row,_elapsed,"active"] call ACME_fnc_medicationKineticEffect,"native timeout truncated PK record"] call _check;
        [!([_row,100 + 11*{half},"active"] call ACME_fnc_medicationKineticEffect),"negligible tail did not retire"] call _check;
    ''')


def test_redistribution_does_not_extend_propofol_hypnosis_or_rocuronium_paralysis():
    execute(definitions() + '''
        {
            private _row = [_x,0,90,480,0,0,0,1,0,0,0,0,1,"Default",0];
            [([_row,481] call ACME_fnc_medicationKineticEffect) == 0,"terminal half-life extended acute effect"] call _check;
            [([_row,481,"physical"] call ACME_fnc_medicationKineticEffect) > 0,"redistribution deleted circulating drug"] call _check;
        } forEach ["Propofol_IV","Rocuronium_IV"];
        private _row = ["Midazolam",0,600,3000,0,0,0,0,120,0,0,0,1,"Default",0];
        [([_row,300,"physical"] call ACME_fnc_medicationKineticEffect)==1,"IM onset was bypassed"] call _check;
        missionNamespace setVariable ["ACME_clinicalTiming",[0.5]];
        [abs (([_row,1620] call ACME_fnc_medicationKineticEffect) - 0.5) < 0.0001,"server scale not applied"] call _check;
    ''')


def test_infusion_batching_preserves_dose_and_keeps_bolus_and_routes_distinct():
    execute(definitions() + '''
        private _a = ["Morphine_IV",1,3,60,-3,0.2,0,1,1,0,0,0,0.2,"Opioid",0,"","ACME_infusionPulse"];
        private _b = +_a; _b set [1,21]; _b set [12,0.6];
        private _c = +_b; _c set [14,1];
        private _bolus = _a select [0,15];
        private _batched = [[_a,_b,_c,_bolus],120] call ACME_fnc_compactMedicationRecords;
        [count _batched == 3,"bolus or separate route was merged"] call _check;
        private _combo = _batched select 0;
        [abs ((_combo select 12)-0.8) < 0.0001 && {abs ((_combo select 1)-16) < 0.0001}
            && {(_combo select 4) == -6},"batching altered dose, time or effect coefficient"] call _check;
        [count ([[_a,_b],25] call ACME_fnc_compactMedicationRecords)==2,"ongoing onset was merged"] call _check;
    ''')


def test_only_server_setting_source_is_published_and_clients_cannot_inject_a_policy():
    source = read('clinicalTimingSync')
    source = source.replace('isRemoteExecuted','_remote').replace('remoteExecutedOwner','_sender')
    source = source.replace('isServer','_server').replace(
        '_policy remoteExecCall ["ACME_fnc_clinicalTimingSync",-2,"ACME_clinicalTiming"]',
        '_published pushBack +_policy')
    execute('private _sync={'+adapt(source)+'''};
        private _server=true;private _remote=false;private _sender=2;
        private _published=[];private _scopes=[];
        ACME_fnc_clinicalClockTick={};
        CBA_settings_fnc_get={_scopes pushBack (_this select 1);switch (_this select 0) do {
            case "ACME_medicationTimeScale": {0.8}; case "ACME_clinicalTimeBasis": {0}; default {true};
        }};
        call _sync; call _sync;
        [count _published==1 && {count _scopes==24} && {(_scopes findIf {_x!="server"})<0},"settings were not read from server only"] call _check;
        _server=false;_remote=true;_sender=5;[99,true,true,true,24,24,48,4,24,4,21,1] call _sync;
        [((missionNamespace getVariable "ACME_clinicalTiming") select 0)==0.8,"peer overwrote policy"] call _check;
        _sender=2;[1.1,true,true,true,24,24,48,4,24,4,21,1] call _sync;
        [((missionNamespace getVariable "ACME_clinicalTiming") select 0)==1.1,"authenticated JIP policy failed"] call _check;
    ''')


def test_defaults_and_collection_expiry_before_the_spiked_deadline():
    execute('''
        [["warm"] call ACME_fnc_bloodTiming == 14400 && {["fresh"] call ACME_fnc_bloodTiming == 86400}
            && {["spiked"] call ACME_fnc_bloodTiming == 14400}
            && {["fridge"] call ACME_fnc_bloodTiming == 1814400},"reference defaults wrong"] call _check;
        CBA_missionTime = 86399;
        private _bag = [["FreshBlood",200,1,0,true,0,500,7,"uid",500,["freshV1",true,0,0],"bagOnly"]] call ACME_fnc_bloodUseRow;
        [!([_bag,"native","expired"] call ACME_fnc_bloodUseRow),"fresh bag expired early"] call _check;
        CBA_missionTime = 86400;
        [[_bag,"native","expired"] call ACME_fnc_bloodUseRow,"spiking extended the donor collection limit"] call _check;
    ''')


def test_fridge_lot_age_survives_restore_and_blocks_expired_stock():
    execute(fridge_setup()+'''
        private _saved = +_savedFridge;
        _saved set [6,1814300];
        _patient setVariable ["ACME_bloodFridge",true];
        [([_patient,_saved,0,100] call ACME_fnc_bloodFridgeRestore),"fridge restore refused valid save"] call _check;
        [(_patient getVariable ["ACME_bf_stock",["missing"]]) isEqualTo [],"expired stock revived on restart"] call _check;
        [([_patient] call ACME_fnc_bloodFridgeSnapshot) select 6 == 1814400,"lot clock rebased incorrectly"] call _check;
        private _legacy = _saved select [0,6]; _legacy set [0,1];
        [[_legacy] call ACME_fnc_bloodFridgeSnapshotValid,"legacy fridge save rejected"] call _check;
    ''')
