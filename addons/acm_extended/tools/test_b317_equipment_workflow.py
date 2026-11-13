"""Regression coverage for confirmed placement and the powered Tempus waveform entry point."""

import re

import pytest

from test_b308_patient_equipment import setup
from test_b312_mounts_cables import setup as field_setup
from test_b316_field_equipment import monitor_source
from test_menu_death_lifecycle import ROOT, adapt, execute


@pytest.mark.parametrize(("kind", "sensor", "expected"), [
    ("pro", 1, '[false,true,false,false,false]'),
    ("pro", -1, '[false,false,false,false,false]'),
    ("ls", 0, '[false,true]'),
    ("ls", 5, '[true,false]'),
])
def test_first_sensor_commits_only_after_the_owner_proves_inventory(kind, sensor, expected):
    execute(setup() + f'''
        [_medic,_patient,"{kind}","setup",false,[],objNull,"",{sensor}] call ACME_fnc_equipmentRequest;
        [count _inventoryMessages == 1 && {{_spawnCount == 0}},"device appeared before debit"] call _check;
        _caller=2;
        (_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
        _caller=7;
        (_acks select 0) call ACME_fnc_equipmentAck;
        (_acks select 0) call ACME_fnc_equipmentAck;
        private _device=_patient getVariable ["ACME_eq_{kind}",objNull];
        [_device isEqualTo _deviceFixture && {{_spawnCount == 1}} && {{_stock == 0}} && {{_feeds == 1}},
            "placement did not commit exactly once"] call _check;
        private _flags=if ("{kind}" == "pro") then {{_device getVariable "acme_tempus_sensors"}} else {{
            [_device getVariable "acme_tempusls_pads",_device getVariable "acme_tempusls_ecg"]
        }};
        [_flags isEqualTo {expected},"changed more than the requested sensor"] call _check;
    ''')


def test_menu_claims_the_manually_placed_monitor_and_never_steals_an_assigned_one():
    execute(setup() + '''
        private _device=missionNamespace;
        private _calls=[];
        private _nearby=[_device];
        private _sender=7;
        ACME_fnc_tempusUse={};ACME_fnc_tempusLsUse={};
        private _action={''' + monitor_source() + '''};
        _device setVariable ["acme_tempus_pat",_medic];
        [!([_medic,_patient,"pro",[3,true],true,_device] call _action),"assigned monitor was stolen"] call _check;
        _device setVariable ["acme_tempus_pat",objNull];
        [[_medic,_patient,"pro",[3,true],true] call _action,"manual monitor not claimable"] call _check;
        [_stock == 1 && {_spawnCount == 0},"manual monitor incorrectly replaced"] call _check;
        [(_device getVariable "acme_tempus_sensors") isEqualTo [false,false,false,true,false],"wrong manual sensor"] call _check;
        [(_patient getVariable "ACME_eq_pro") isEqualTo _device,"manual monitor was not bound"] call _check;
    ''')


def test_patient_stock_accuvac_debits_the_donor_on_the_confirmed_server_request():
    execute(setup() + '''
        ACME_fnc_treatmentSupplyOrder={[_patient,_medic]};
        [_patient,_patient,"accu","setup",false,[],objNull,"",-1,_medic] call ACME_fnc_equipmentRequest;
        [count _inventoryMessages == 1 && {(_inventoryMessages select 0 select 0) isEqualTo _patient},
            "provider could not deploy patient stock"] call _check;
        _caller=2;
        (_inventoryMessages select 0) call ACME_fnc_equipmentInventory;
        _caller=7;
        (_acks select 0) call ACME_fnc_equipmentAck;
        [(_patient getVariable "ACME_eq_accu") isEqualTo _deviceFixture && {_stock == 0},
            "shared pump did not deploy"] call _check;
    ''')


def test_feed_start_retries_until_the_expected_patient_owner_reports_receipt():
    execute(field_setup() + '''
        [_device] call ACME_fnc_equipmentMonitorTick;
        [_device] call ACME_fnc_equipmentMonitorTick;
        [_feedRetries == 1,"feed retry unbounded"] call _check;
        _monitorTime = 22;
        [_device] call ACME_fnc_equipmentMonitorTick;
        [_feedRetries == 2,"missing feed not restarted"] call _check;
        _device setVariable ["ACME_eq_feedOwner",[_patient,7]];
        _monitorTime = 26;
        [_device] call ACME_fnc_equipmentMonitorTick;
        [_feedRetries == 2,"acknowledged feed restarted"] call _check;
        _device setVariable ["ACME_eq_feedOwner",[_patient,9]];
        [_device] call ACME_fnc_equipmentMonitorTick;
        [_feedRetries == 3,"owner handoff did not restart feed"] call _check;
    ''')


def fixture_source(path):
    source = (ROOT / path).read_text()
    source = source.replace('_device distance _patient', '_distance')
    source = re.sub(r'!finite (_\w+)', r'!(\1 isEqualType 0)', source)
    source = source.replace('alive (_patient getVariable ["ace_medical_CPR_provider",objNull])', 'false')
    source = re.sub(r'(\w+) resize \[([^,]+),([^\]]+)\];',
                    r'\1 = []; for "_fill" from 1 to (\2) do {\1 pushBack (\3);};', source)
    source = re.sub(r'_control ctrlWebBrowserAction \["ExecJS",', '_browser pushBack (["ExecJS",', source)
    source = source.replace('_api+".resetWaveforms()"];','_api+".resetWaveforms()"]);')
    source = source.replace('_first,_part,count _packets,_markers]];', '_first,_part,count _packets,_markers]]);')
    source = re.sub(r'linearConversion (\[[^\]]+\])', r'(\1 call _linear)', source)
    return adapt(source)


@pytest.mark.parametrize("ls", [False, True])
def test_powered_first_wave_packet_advances_with_and_without_an_owner_vitals_cache(ls):
    tempus = "addons/acme_tempus/functions"
    prefix = "acme_tempusls" if ls else "acme_tempus"
    execute(f'''
        private _control = missionNamespace;
        private _device = parsingNamespace;
        private _browser = [];
        private _nowTime = 25;
        private _rate = 93;
        private _rhythm = 0;
        CBA_missionTime = 50;
        private _linear = {{
            params ["_lo","_hi","_x","_y0","_y1","_bounded"];
            private _portion = (_x-_lo)/(_hi-_lo);
            if (_bounded) then {{_portion = _portion max 0 min 1;}};
            _y0 + _portion*(_y1-_y0)
        }};
        ACME_fnc_clinicalEpoch = {{1}};
        ACME_fnc_rhythmGet = {{_rhythm}};
        ACME_fnc_ecgArtifactStrength = {{0}};
        ACME_fnc_ecgArtifactApply = {{[_this select 1,_this select 2]}};
        ACM_circulation_fnc_recentAEDShock = {{false}};
        ACM_circulation_fnc_getEKGHeartRate = {{_rate}};
        ACM_circulation_fnc_hasPulse = {{_rate > 0}};
        ACME_fnc_tempusVitals = {{[93,93,0,118,79,98,18,37,37]}};
        _device setVariable ["{prefix}_pat",_patient];
        _device setVariable ["{prefix}_pw",[true,25,true]];
        _device setVariable ["{prefix}_v",[]];
        _device setVariable ["acme_tempus_sensors",[true,true,false,true,false]];
        ACME_fnc_tempusBeatPlan = {{{fixture_source(tempus+'/fn_tempusBeatPlan.sqf')}}};
        ACME_fnc_tempusProjectLead = {{{fixture_source(tempus+'/fn_tempusProjectLead.sqf')}}};
        ACM_circulation_fnc_displayAEDMonitor_generateEKG = {{{fixture_source("addons/circulation/functions/fnc_displayAEDMonitor_generateEKG.sqf")}}};
        private _stream = {{{fixture_source(tempus+'/fn_tempusWaveforms.sqf')}}};
        private _ls = {str(ls).lower()};
        [_control,_device,_ls,true] call _stream;
        [count _browser == (if (_ls) then {{2}} else {{6}}),"first powered frame did not reach the bridge"] call _check;
        [(_browser findIf {{((_x select 1) find "waveformPart") >= 0 && {{((_x select 1) find "-") >= 0}}}}) >= 0,
            "ECG stayed flat before the owner feed"] call _check;
        _device setVariable ["{prefix}_v",[93,93,0,118,79,98,18,37,37]];
        _nowTime = 26.16;
        _browser = [];
        [_control,_device,_ls] call _stream;
        [count _browser == (if (_ls) then {{1}} else {{5}}),"cached vitals interrupted the sweep"] call _check;
        [(_control getVariable "ACME_wave_cursor") == 80,"sample cursor skipped or repeated a block"] call _check;
    ''')
