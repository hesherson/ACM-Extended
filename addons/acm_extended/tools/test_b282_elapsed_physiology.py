"""Execute clinical effects and their real elapsed clock across FPS/stall edges.

Only native object locality/liveness, frame duration and publication cross
fixtures. The production clock and each effect integration execute directly;
there is no Python copy of the physiology under test.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from test_menu_death_lifecycle import PREAMBLE, adapt, read


EFFECTS = {
    "ettMainstemTick": ("ACME_o2Drain_mainstem", .55,
                        '_patient setVariable ["ACME_ETT_Mainstem",true];'
                        '_patient setVariable ["ACME_ETT_Inserted",true];',
                        '_patient setVariable ["ACME_ETT_Mainstem",false];'),
    "hcVentTick": ("ACME_vent_vili", .5 / 60,
                   'missionNamespace setVariable ["ACME_hcEff_vent",true];'
                   '_patient setVariable ["ACME_vent_driving",true];'
                   '_patient setVariable ["ACME_vent_vti",1280];'
                   '_patient setVariable ["ACME_vent_weight",80];',
                   '_patient setVariable ["ACME_vent_driving",false];'),
    "hcCircTick": ("ACME_hc_pressorDebt", .45,
                   'missionNamespace setVariable ["ACME_hcEff_circ",true];'
                   '_patient setVariable ["ACME_pressorResistAdd",20];'
                   '_patient setVariable ["ace_medical_bloodVolume",3];',
                   'missionNamespace setVariable ["ACME_hcEff_circ",false];'),
}


def function(name):
    source = read(name).replace("local _patient", "_patientLocal")
    source = source.replace("clientOwner", "_fixtureOwner")
    source = source.replace("diag_deltaTime", "_frameDelta")
    return "ACME_fnc_" + name + "={\n" + adapt(source) + "\n};\n"


def setup(name):
    return r'''
      private _patientLocal=true;private _fixtureOwner=7;private _frameDelta=1/60;
      ACME_fnc_setVarNet={params ["_p","_key","_value"];_p setVariable [_key,_value];};
      ACME_fnc_setVarNetApprox=ACME_fnc_setVarNet;
      ACME_fnc_ventEffectiveSettings={[false]};
      CBA_missionTime=100;
    ''' + function("clinicalTickDelta") + function(name) + EFFECTS[name][2]


def execute(code):
    vm = os.environ.get("SQFVM") or shutil.which("sqfvm")
    if not vm:
        pytest.skip("SQF-VM required")
    with tempfile.TemporaryDirectory(prefix="acme-b282-elapsed-") as directory:
        path = Path(directory) / "case.sqf"
        path.write_text(PREAMBLE + code + '\ndiag_log (if (_ok) then {"B282_ELAPSED_OK"} else {"B282_ELAPSED_FAIL"});')
        result = subprocess.run([vm, "--automated", "--suppress-welcome", "--no-execute-print",
                                 "--no-work-print", "--input-sqf", str(path)], capture_output=True,
                                text=True, timeout=20)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert not any(tag in output for tag in ("[ERR]", "[FAT]", "[WRN]", "MENU_FIX_FAIL", "B282_ELAPSED_FAIL")), output
    assert "B282_ELAPSED_OK" in output, output


@pytest.mark.parametrize("name", EFFECTS)
@pytest.mark.parametrize("cadence", [.25, .5, 1])
@pytest.mark.parametrize("fps", [5, 60])
def test_identical_elapsed_exposure_has_identical_effect_at_high_and_low_fps(name, cadence, fps):
    key, rate, _, _ = EFFECTS[name]
    execute(setup(name) + f'''
      _frameDelta=1/{fps};[_patient] call ACME_fnc_{name};
      for "_i" from 1 to {int(20 / cadence)} do {{
        CBA_missionTime=100+_i*{cadence};[_patient] call ACME_fnc_{name};
      }};
      [abs ((_patient getVariable ["{key}",0])-{20 * rate})<.0001,"frame rate changed the clinical effect rate"] call _check;
    ''')


@pytest.mark.parametrize("name", EFFECTS)
def test_repeated_callbacks_at_same_clock_instant_do_not_advance_effect(name):
    key, rate, _, _ = EFFECTS[name]
    execute(setup(name) + f'''
      [_patient] call ACME_fnc_{name};CBA_missionTime=101;
      [_patient] call ACME_fnc_{name};[_patient] call ACME_fnc_{name};
      [abs ((_patient getVariable ["{key}",0])-{rate})<.00001,"duplicate callback advanced physiology"] call _check;
    ''')


@pytest.mark.parametrize("name", EFFECTS)
def test_long_stall_is_bounded_and_does_not_leave_replay_backlog(name):
    key, rate, _, _ = EFFECTS[name]
    execute(setup(name) + f'''
      [_patient] call ACME_fnc_{name};CBA_missionTime=400;
      [_patient] call ACME_fnc_{name};
      [abs ((_patient getVariable ["{key}",0])-{5 * rate})<.00001,"stall caused unbounded physiology catch-up"] call _check;
      CBA_missionTime=400.25;[_patient] call ACME_fnc_{name};
      [abs ((_patient getVariable ["{key}",0])-{5.25 * rate})<.00001,"discarded stall replayed on next callback"] call _check;
    ''')


@pytest.mark.parametrize("name", EFFECTS)
def test_owner_transfer_rebaselines_clock_and_preserves_durable_effect(name):
    key, rate, _, _ = EFFECTS[name]
    execute(setup(name) + f'''
      [_patient] call ACME_fnc_{name};CBA_missionTime=101;[_patient] call ACME_fnc_{name};
      _fixtureOwner=8;CBA_missionTime=1000;[_patient] call ACME_fnc_{name};
      [abs ((_patient getVariable ["{key}",0])-{rate})<.00001,"incoming owner replayed another owner's elapsed time"] call _check;
      CBA_missionTime=1000.25;[_patient] call ACME_fnc_{name};
      [abs ((_patient getVariable ["{key}",0])-{1.25 * rate})<.00001,"new owner failed to resume current clinical time"] call _check;
    ''')


@pytest.mark.parametrize("name", EFFECTS)
def test_inactive_passes_do_not_charge_time_after_reactivation(name):
    key, rate, active, inactive = EFFECTS[name]
    execute(setup(name) + inactive + f'''
      [_patient] call ACME_fnc_{name};CBA_missionTime=400;[_patient] call ACME_fnc_{name};
    ''' + active + f'''
      [_patient] call ACME_fnc_{name};
      [(_patient getVariable ["{key}",0])==0,"reactivation charged inactive exposure"] call _check;
      CBA_missionTime=400.25;[_patient] call ACME_fnc_{name};
      [abs ((_patient getVariable ["{key}",0])-{.25 * rate})<.00001,"reactivation did not resume current effect"] call _check;
    ''')


@pytest.mark.parametrize("name", EFFECTS)
@pytest.mark.parametrize("edge", ["_patientLocal=false;", "_patientAlive=false;"])
def test_non_owner_and_dead_patient_do_not_mutate_effect(name, edge):
    key, _, _, _ = EFFECTS[name]
    execute(setup(name) + edge + f'''
      _patient setVariable ["{key}",.125];[_patient] call ACME_fnc_{name};
      [(_patient getVariable ["{key}",0])==.125,"non-owner or dead patient changed clinical effect"] call _check;
    ''')


def ncd_setup():
    return setup("ettMainstemTick") + function("ncdAirLeakTick") + r'''
      missionNamespace setVariable ["ACME_sys_ncdLeak",true];
      _patient setVariable ["ACME_ncd_total",3];
      _patient setVariable ["ACME_ncd_leak",0];
      ACME_fnc_breathSoundsStart={};
    '''


@pytest.mark.parametrize("cadence", [.25, .5, 1, 5])
def test_needle_leak_keeps_five_second_cadence_using_active_elapsed_time(cadence):
    execute(ncd_setup() + f'''
      [_patient] call ACME_fnc_ncdAirLeakTick;
      for "_i" from 1 to {int(20 / cadence)} do {{
        CBA_missionTime=100+_i*{cadence};[_patient] call ACME_fnc_ncdAirLeakTick;
      }};
      [abs ((_patient getVariable ["ACME_ncd_leak",0])-.007)<.00001,"needle leak rate depends on callback cadence"] call _check;
    ''')


@pytest.mark.parametrize("inactive,active", [
    ('_patient setVariable ["ACM_breathing_Thoracostomy_State",2];',
     '_patient setVariable ["ACM_breathing_Thoracostomy_State",0];'),
    ('missionNamespace setVariable ["ACME_sys_ncdLeak",false];',
     'missionNamespace setVariable ["ACME_sys_ncdLeak",true];'),
    ('_patient setVariable ["ACME_ncd_total",2];',
     '_patient setVariable ["ACME_ncd_total",3];'),
])
def test_needle_leak_does_not_replay_time_with_drain_disabled_or_no_extra_needles(inactive, active):
    execute(ncd_setup() + r'''
      [_patient] call ACME_fnc_ncdAirLeakTick;
      CBA_missionTime=104;[_patient] call ACME_fnc_ncdAirLeakTick;
    ''' + inactive + r'''
      CBA_missionTime=105;[_patient] call ACME_fnc_ncdAirLeakTick;
      CBA_missionTime=3700;[_patient] call ACME_fnc_ncdAirLeakTick;
    ''' + active + r'''
      [_patient] call ACME_fnc_ncdAirLeakTick;
      [(_patient getVariable ["ACME_ncd_leak",0])==0,"needle leak charged an hour of inactive exposure"] call _check;
      CBA_missionTime=3705;[_patient] call ACME_fnc_ncdAirLeakTick;
      [abs ((_patient getVariable ["ACME_ncd_leak",0])-.00175)<.000001,"needle leak did not resume from current active time"] call _check;
    ''')


def test_needle_leak_stall_is_bounded_even_with_partial_cadence_accumulated():
    execute(ncd_setup() + r'''
      [_patient] call ACME_fnc_ncdAirLeakTick;
      CBA_missionTime=104;[_patient] call ACME_fnc_ncdAirLeakTick;
      CBA_missionTime=3700;[_patient] call ACME_fnc_ncdAirLeakTick;
      [abs ((_patient getVariable ["ACME_ncd_leak",0])-.00175)<.000001,"needle leak stall caused unbounded catch-up"] call _check;
      [_patient] call ACME_fnc_ncdAirLeakTick;
      [abs ((_patient getVariable ["ACME_ncd_leak",0])-.00175)<.000001,"needle leak replayed discarded backlog"] call _check;
    ''')


def test_needle_leak_owner_transfer_discards_pending_elapsed_without_erasing_leak():
    execute(ncd_setup() + r'''
      _patient setVariable ["ACME_ncd_leak",.1];[_patient] call ACME_fnc_ncdAirLeakTick;
      CBA_missionTime=104;[_patient] call ACME_fnc_ncdAirLeakTick;
      _fixtureOwner=8;CBA_missionTime=3700;[_patient] call ACME_fnc_ncdAirLeakTick;
      [(_patient getVariable ["ACME_ncd_leak",0])==.1,"needle leak inherited another owner's partial clock"] call _check;
      CBA_missionTime=3705;[_patient] call ACME_fnc_ncdAirLeakTick;
      [abs ((_patient getVariable ["ACME_ncd_leak",0])-.10175)<.000001,"needle leak failed after owner transfer"] call _check;
    ''')
