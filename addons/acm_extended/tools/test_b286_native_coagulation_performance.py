"""Execute native coagulation PFHs and count work between real attempt deadlines.

The checked-out callback, time guards, interval formulas and wound traversal run
in SQF-VM. Object liveness, CBA registration and ACE drug/wound operations are
explicit boundaries; their counters expose unnecessary work and missed attempts.
"""
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from test_historical_vial_execution import map_defaults
from test_menu_death_lifecycle import ROOT, adapt


CASES = [
    pytest.param("handleCoagulationPFH", "Coagulation", 9, 3, id="external"),
    pytest.param("handleIBCoagulationPFH", "IBCoagulation", 6, 1.5, id="internal"),
]


def source(name):
    text = (ROOT / "addons/damage/functions" / f"fnc_{name}.sqf").read_text()
    # These macros cross native object/ACE boundaries. The callback itself is
    # captured from the complete production registration, without reimplementing it.
    for old, new in {
        "IS_BLEEDING(_patient)": "true",
        "IS_I_BLEEDING(_patient)": "true",
        "GET_HEART_RATE(_patient)": "80",
        "GET_EFF_BLOOD_VOLUME(_patient)": "6",
        "GET_OPEN_WOUNDS(_patient)": "(_patient call _wounds)",
        "GET_INTERNAL_WOUNDS(_patient)": "(_patient call _wounds)",
        "VAR_INTERNAL_WOUNDS": '"ACM_damage_InternalWounds"',
    }.items():
        text = text.replace(old, new)
    macros = (ROOT / "addons/main/script_macros.hpp").read_text()
    priority = re.findall(r"^#define ALL_BODY_PARTS_PRIORITY (\[[^\n]+\])$", macros, re.M)
    assert len(priority) == 1
    text = text.replace("ALL_BODY_PARTS_PRIORITY", priority[0])
    return map_defaults(adapt(text, component="damage"))


def setup(name, prefix):
    return r'''
        private _ok=true;
        private _patient=profileNamespace;
        private _patientAlive=true;
        private _medCalls=0;
        private _woundQueries=0;
        private _clots=0;
        private _medResult=0;
        private _handlers=[];
        private _removed=[];
        private _check={if !(_this select 0) then {
            _ok=false; diag_log ("B286_COAG_FAIL "+(_this select 1));
        }};
        private _mapDefault={params ["_map","_args"];_args params ["_key","_default"];
            if (_key in _map) then {_map get _key} else {_default}};
        private _wounds={_woundQueries=_woundQueries+1;
            _patient getVariable "ACM_damage_InternalWounds"};
        CBA_fnc_addPerFrameHandler={_handlers pushBack _this;count _handlers-1};
        CBA_fnc_removePerFrameHandler={_removed pushBack (_this select 0)};
        ace_medical_status_fnc_getMedicationCount={
            [_this isEqualTo [_patient,"TXA_IV",false],"drug query arguments changed"] call _check;
            _medCalls=_medCalls+1;_medResult
        };
        ace_medical_treatment_fnc_hasTourniquetAppliedTo={false};
        ACM_damage_fnc_clotWoundsOnBodyPart={_clots=_clots+1};
        ace_medical_status_fnc_updateWoundBloodLoss={_clots=_clots+1};
        _patient setVariable ["ACM_damage_InternalWounds",createHashMapFromArray [["body",[[1,5,1]]]]];
        CBA_missionTime=10;
        private _start={
    ''' + source(name) + r'''
        };
        [_patient] call _start;
        [count _handlers==1 && {((_handlers select 0) select 1)==1},"registration cadence changed"] call _check;
        private _h=_handlers select 0;
        private _tick={[_h select 2,0] call (_h select 0)};
    ''' + f'''
        private _deadlineKey="ACM_damage_{prefix}_NextAttempt";
        private _handleKey="ACM_damage_{prefix}_PFH";
        private _activeKey="ACM_damage_{prefix}_Active";
        private _due=_patient getVariable _deadlineKey;
    '''


def execute(code):
    vm = os.environ.get("SQFVM") or shutil.which("sqfvm")
    if not vm:
        pytest.skip("SQF-VM required")
    with tempfile.TemporaryDirectory(prefix="acme-b286-native-coag-") as directory:
        path = Path(directory) / "case.sqf"
        path.write_text(code + '\ndiag_log (if (_ok) then {"B286_COAG_OK"} else {"B286_COAG_FAIL"});')
        result = subprocess.run(
            [vm, "--automated", "--suppress-welcome", "--no-execute-print",
             "--no-work-print", "--input-sqf", str(path)],
            capture_output=True, text=True, timeout=15,
        )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert not any(tag in output for tag in ("[ERR]", "[FAT]", "[WRN]", "B286_COAG_FAIL")), output
    assert "B286_COAG_OK" in output, output


@pytest.mark.parametrize("name,prefix,first_interval,txa_interval", CASES)
def test_callbacks_skip_queries_until_due_and_use_current_txa_on_each_attempt(
    name, prefix, first_interval, txa_interval,
):
    execute(setup(name, prefix) + r'''
        {CBA_missionTime=_x;call _tick;} forEach [10,11,_due-.001];
        [_medCalls==0 && {_woundQueries==0} && {_clots==0},"waiting callback queried drugs or wounds"] call _check;
        [(_patient getVariable _deadlineKey)==_due,"waiting callback moved deadline"] call _check;
        [count _removed==0,"waiting callback retired active handler"] call _check;
        CBA_missionTime=_due;call _tick;
        [_medCalls==1 && {_woundQueries==1} && {_clots==1},"exact deadline did not run one attempt"] call _check;
    ''' + f'''
        [abs ((_patient getVariable _deadlineKey)-_due-{first_interval})<.000001,"baseline attempt interval changed"] call _check;
    ''' + r'''
        private _next=_patient getVariable _deadlineKey;
        _medResult=99;
        call _tick;
        CBA_missionTime=_next-.001;call _tick;
        [_medCalls==1 && {_woundQueries==1} && {_clots==1},"between-attempt callbacks repeated work"] call _check;
        CBA_missionTime=_next;call _tick;
        [_medCalls==2 && {_woundQueries==2} && {_clots==2},"later attempt missed live TXA/wound queries"] call _check;
    ''' + f'''
        [abs ((_patient getVariable _deadlineKey)-_next-{txa_interval})<.000001,"later TXA effect or interval cap changed"] call _check;
    ''' + r'''
        [count _removed==0 && {(_patient getVariable _handleKey)==0},"successful attempt retired handler"] call _check;
    ''')


@pytest.mark.parametrize("name,prefix,first_interval,txa_interval", CASES)
def test_dead_patient_cleans_up_before_future_deadline_without_drug_or_wound_queries(
    name, prefix, first_interval, txa_interval,
):
    execute(setup(name, prefix) + r'''
        _patientAlive=false;CBA_missionTime=11;call _tick;
        [_medCalls==0 && {_woundQueries==0} && {_clots==0},"dead cleanup queried drugs or wounds"] call _check;
        [_removed isEqualTo [0] && {(_patient getVariable _handleKey)==-1},"dead handler was not removed"] call _check;
        [!(_patient getVariable _activeKey),"dead cleanup left active flag"] call _check;
        [(_patient getVariable _deadlineKey)==_due,"dead cleanup scheduled an attempt"] call _check;
    ''')


def test_external_inactivity_timeout_still_cleans_up_before_future_deadline():
    execute(setup("handleCoagulationPFH", "Coagulation") + r'''
        _patient setVariable [_deadlineKey,1000];
        CBA_missionTime=130;call _tick;
        [count _removed==0,"inactivity cleanup ran at exact 120-second boundary"] call _check;
        CBA_missionTime=130.001;call _tick;
        [_removed isEqualTo [0] && {(_patient getVariable _handleKey)==-1},"inactivity timeout was hidden by next-attempt guard"] call _check;
        [!(_patient getVariable _activeKey),"inactivity timeout left active flag"] call _check;
        [_medCalls==0 && {_woundQueries==0} && {_clots==0},"inactivity cleanup queried drugs or wounds"] call _check;
    ''')
