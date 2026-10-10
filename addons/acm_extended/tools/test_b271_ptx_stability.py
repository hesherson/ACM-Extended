"""Execute B271 durable PTX stabilization and surgical closure in production SQF.

Actual Context/Ensure/Injury/Treat/Step/Publish and treatment callbacks execute.
Only object, native clock/network/UI/inventory commands cross explicit fixtures;
all inputs to the finite-number adapter are finite. The pinned VM must emit no
warning/error/fatal diagnostics. No Python copy of the physiology is exercised.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pytest

from test_menu_death_lifecycle import ROOT, adapt


def function(name, native=False):
    directory = "breathing" if native else "acm_extended"
    prefix = "fnc" if native else "fn"
    path = ROOT / f"addons/{directory}/functions/{prefix}_{name}.sqf"
    source = path.read_text()
    # Namespace fixtures supply precisely the engine locality and clock values.
    source = re.sub(r"\blocal _patient\b", "_patientLocal", source)
    source = adapt(source, "breathing" if native else "core")
    source = re.sub(r"objNull,\s*\[objNull\]", "objNull, [profileNamespace]", source)
    source = source.replace("_tension!=_wasTension", "!(_tension isEqualTo _wasTension)")
    # Native localization is an engine UI/log boundary. Retain the string-table
    # key so activity-log identity and ordering remain observable in the VM.
    source = re.sub(r'\blocalize ("(?:[^"]|"")*")', r'\1', source)
    # The pinned VM returns nil for an absent typed-param array index. Arma
    # supplies false here. Preserve its bounds/type/default semantics exactly.
    source = source.replace(
        '_context param [7, false, [false]]',
        '(if (count _context > 7 && {(_context select 7) isEqualType false}) then {_context select 7} else {false})',
    )
    source = re.sub(r"\bfinite (_\w+)", r"([\1] call _finite)", source)
    source = source.replace('_openWounds getOrDefault ["body", []]', '[_openWounds, "body", []] call _getDefault')
    source = source.replace('_pending getOrDefault [_id, []]', '[_pending, _id, []] call _getDefault')
    source = source.replace('_pending getOrDefault [_receipt param [3, ""], []]', '[_pending, _receipt param [3, ""], []] call _getDefault')
    source = source.replace('_required getOrDefault [_name, ""]', '[_required, _name, ""] call _getDefault')
    source = source.replace("owner _obj", "7").replace("local _obj", "_patientLocal").replace("owner _patient", "7")
    source = source.replace(", _public]", "]").replace("serverTime", "_clock")
    symbol = "ACM_breathing_fnc_" if native else "ACME_fnc_"
    return f"{symbol}{name}={{\n{source}\n}};\n"


def execute(code):
    vm = os.environ.get("SQFVM") or shutil.which("sqfvm")
    if not vm:
        pytest.skip("SQF-VM required")
    with tempfile.TemporaryDirectory(prefix="acme-b271-ptx-") as directory:
        source_path = Path(directory) / "case.sqf"
        source_path.write_text(BASE + code + '\ndiag_log (if (_ok) then {"B271_PTX_OK"} else {"B271_PTX_FAIL"});', encoding="utf-8")
        result = subprocess.run(
            [vm, "--automated", "--suppress-welcome", "--no-execute-print", "--no-work-print", "--input-sqf", str(source_path)],
            capture_output=True, text=True, timeout=20,
        )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert not any(tag in output for tag in ("[ERR]", "[FAT]", "[WRN]", "B271_PTX_FAIL")), output
    assert "B271_PTX_OK" in output, output
    return output


BASE = r'''
private _patient=profileNamespace;
private _medic=uiNamespace;
private _patientLocal=true;
private _alive=false; // Absent native BVM provider is not delivering breaths.
private _patientAlive=true;
private _clock=10;
private _nowTime=10;
private _distance=1;
CBA_missionTime=10;
private _ok=true;
private _events=[];
private _logs=[];
private _takes=0;
private _refunds=[];
private _finite={params ["_value"]; _value isEqualType 0};
private _getDefault={params ["_map","_key","_default"]; if (_key in _map) then {_map get _key} else {_default}};
private _check={params ["_condition","_message"]; if (!_condition) then {_ok=false;diag_log format ["B271_PTX_FAIL %1",_message]};};
CBA_fnc_removePerFrameHandler={};
CBA_fnc_targetEvent={_events pushBack _this;};
ACM_breathing_fnc_updateLungState={};
ACM_breathing_fnc_setChestInjuryState={params ["_patient","_value"]; _patient setVariable ["ACM_breathing_ChestInjury_State",_value];};
ACME_fnc_chestSealLogOnce={_logs pushBack _this;false};
ACME_fnc_ventEffectiveSettings={[]};
ACME_fnc_setVarNetApprox={};
ACME_fnc_procedureAllowed={true};
ACME_fnc_clinicalTickDelta={1};
ace_common_fnc_getName={"Provider"};
ace_common_fnc_displayTextStructured={};
ace_medical_treatment_fnc_addToTriageCard={};
ace_medical_treatment_fnc_addToLog={_logs pushBack _this;};
missionNamespace setVariable ["ACME_sys_chestSeal",true];
missionNamespace setVariable ["ACME_ptx_tensionBaseSec",600];
missionNamespace setVariable ["ACME_ptx_leakSettleSec",600];
missionNamespace setVariable ["ACME_ptx_stableSec",60];
_patient setVariable ["ACME_clinicalEpoch",7];
_patient setVariable ["ACME_CS_holeData",[]];
_patient setVariable ["ACME_CS_penetratingWounds",[]];
// The pinned VM lacks typed param's empty-array default. A healthy concrete
// state supplies the same ncdPatency=0 boundary for context-only scenarios.
_patient setVariable ["ACME_ptx_state",[1,0,0,0,0,0,0,0,0]];
_patient setVariable ["ACM_breathing_Pneumothorax_PFH",-1];
_patient setVariable ["ACM_breathing_Thoracostomy_State",0];
'''


def model_setup():
    # In Arma a missing native cache read may assign nil silently. The pinned VM
    # warns, so seed the cache with nonmatching real publication fingerprints.
    cache = r'''
        private _netCache=createHashMap;
        {
            _x params ["_key","_initial"];
            _patient setVariable [_key,_initial];
            _netCache set [toLower _key,["FIXTURE-UNPUBLISHED"]];
        } forEach [["ACME_ptx_state",[]],["ACME_ptx_tensionSeverity",0],["ACME_ptx_observationRevision",1],
          ["ACME_CS_sealOcclusion",0],["ACME_CS_sealVenting",0],
          ["ACME_ptx_nativeSealCount",-1],["ACME_ptx_nativeSealHoleCount",-1]];
        _patient setVariable ["ACME_net_scalarCache",_netCache];
        _patient setVariable ["ACME_net_cacheOwner",[7,true]];
        _patient setVariable ["ACME_net_approxCache",createHashMap];
        _patient setVariable ["ACME_net_approxOwner",[7,true]];
        private _nativeCache=createHashMap;
        {
            _x params ["_key","_initial"];
            _patient setVariable [_key,_initial];
            _nativeCache set [toLower _key,"FIXTURE-UNPUBLISHED"];
        } forEach [["ACM_breathing_Pneumothorax_PFH",-1],
          ["ACM_breathing_Pneumothorax_State",0],
          ["ACM_breathing_TensionPneumothorax_State",false],
          ["ACM_breathing_TensionPneumothorax_Time",0],
          ["ACM_breathing_Thoracostomy_State",0],
          ["ACM_breathing_Hardcore_Pneumothorax",false]];
        _patient setVariable ["ACM_breathing_ForkStatePublishOwner",[7,true]];
        _patient setVariable ["ACM_breathing_ForkStatePublished",_nativeCache];
    '''
    return cache + "".join(function(name) for name in (
        "setVarNet", "ptxEnsure", "ptxContext", "ptxInjury", "ptxTreat",
        "ptxPublish", "ptxStep", "ptxTensionTick", "clinicalEpoch",
        "thoraSideStateCommit", "thoraBumpVer", "ptxCanClose",
    )) + function("setRuntimeState", native=True)


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("tract,tube,sealed,closed,expected", [
    ("", False, False, False, False),
    ("split", False, False, False, False),
    ("kelly", False, False, False, False),
    ("finger", False, False, False, True),
    ("finger", False, True, False, False),
    ("finger", False, False, True, False),
    ("sealed", False, True, True, False),
    ("finger", True, True, False, True),
])
def test_context_distinguishes_definitive_outlet_from_incomplete_or_closed_tract(side, tract, tube, sealed, closed, expected):
    execute(function("ptxContext") + f'''
        _patient setVariable ["ACME_thora_open_{side}","{tract}"];
        _patient setVariable ["ACME_thora_tube_{side}",{str(tube).lower()}];
        _patient setVariable ["ACME_thora_sealed_{side}",{str(sealed).lower()}];
        _patient setVariable ["ACME_thora_closed_{side}",{str(closed).lower()}];
        private _context=[_patient] call ACME_fnc_ptxContext;
        [count _context==8,"context missing definitive-outlet qualification"] call _check;
        [(_context select 7) isEqualTo {str(expected).lower()},"wrong definitive-outlet eligibility"] call _check;
        [((_context select 2)>=5) isEqualTo {str(expected).lower()},"drainage capacity disagrees with eligibility"] call _check;
    ''')


@pytest.mark.parametrize("native", [0, 1, 2])
def test_context_adopts_legacy_native_thoracostomy_only_without_explicit_side_state(native):
    execute(function("ptxContext") + f'''
        _patient setVariable ["ACM_breathing_Thoracostomy_State",{native}];
        private _legacy=[_patient] call ACME_fnc_ptxContext;
        [(_legacy select 7) isEqualTo {str(native > 0).lower()},"legacy native outlet misclassified"] call _check;
        _patient setVariable ["ACME_thora_open_left","split"];
        private _explicit=[_patient] call ACME_fnc_ptxContext;
        [!(_explicit select 7),"latched native state overrode incomplete explicit tract"] call _check;
    ''')


def test_ncd_and_external_wound_seal_venting_are_not_definitive_outlets():
    execute(function("ptxContext") + r'''
        _patient setVariable ["ACME_ptx_state",[1,0.85,0.6,0,0,1,1,0.85,0.85]];
        _patient setVariable ["ACME_CS_holeData",[["front",[0.4,0.5],0,0,true]]];
        private _context=[_patient] call ACME_fnc_ptxContext;
        [(_context select 5) && {(_context select 6)},"fixture lost temporary and seal outlets"] call _check;
        [!(_context select 7),"temporary/seal outlet qualified for definitive settlement"] call _check;
    ''')


@pytest.mark.parametrize("outlet,residual", [("finger", 0.5), ("tube", 0.0)])
@pytest.mark.parametrize("blood,ppv", [(0, 1), (1, 1), (1, 3)])
def test_definitive_outlet_settles_after_full_observation_and_stays_stable_after_closure(outlet, residual, blood, ppv):
    operation = "thora" if outlet == "finger" else "tube"
    tract = f'_patient setVariable ["ACME_thora_open_left","finger"];'
    if outlet == "tube":
        tract += '_patient setVariable ["ACME_thora_tube_left",true];'
    # The bleed/PPV values are supplied to the actual pure step for consistent
    # control; the patient-owner workflow supplies ordinary default context.
    execute(model_setup() + tract + f'''
        [_patient,[1,3,0.8,0,0.6,0,1,3,1],true] call ACME_fnc_ptxPublish;
        [_patient,"{operation}"] call ACME_fnc_ptxTreat;
        private _s=_patient getVariable "ACME_ptx_state";
        [(_s select 3)==0 && {{!(_patient getVariable "ACM_breathing_TensionPneumothorax_State")}},"definitive treatment did not reset observation/relieve tension"] call _check;
        private _context=[_patient] call ACME_fnc_ptxContext;
        _context set [3,{blood}]; _context set [4,{ppv}];
        for "_i" from 1 to 59 do {{
            _s=([_s,_context,1,false,600,600,60] call ACME_fnc_ptxStep) select 0;
        }};
        [(_s select 2)>0 && {{(_s select 3)==59}},"leak settled before full interval"] call _check;
        [_patient,_s,false] call ACME_fnc_ptxPublish;
        [!([_patient] call ACME_fnc_ptxCanClose),"closure allowed while leak remains"] call _check;
        _s=([_s,_context,1,false,600,600,60] call ACME_fnc_ptxStep) select 0;
        [_patient,_s,false] call ACME_fnc_ptxPublish;
        [(_s select 2)==0 && {{(_s select 3)==60}},"qualified definitive outlet did not settle leak"] call _check;
        [(_s select 1)<={max(residual, 0.5)} && {{[_patient] call ACME_fnc_ptxCanClose}},"settled patient not ready for closure"] call _check;
        // Remove the tube first, using the real owner side-state operation.
        [_patient,"left","tube",false] call ACME_fnc_thoraSideStateCommit;
        [_patient,"left","open","sealed"] call ACME_fnc_thoraSideStateCommit;
        [_patient,"left","sealed",true] call ACME_fnc_thoraSideStateCommit;
        [_patient,"left","closed",true] call ACME_fnc_thoraSideStateCommit;
        [_patient,"thoraSeal"] call ACME_fnc_ptxTreat;
        private _atClosure=+(_patient getVariable "ACME_ptx_state");
        for "_i" from 1 to 600 do {{
            CBA_missionTime=70+_i;
            [_patient] call ACME_fnc_ptxTensionTick;
        }};
        private _late=_patient getVariable "ACME_ptx_state";
        [(_late select 2)==0 && {{abs ((_late select 1)-(_atClosure select 1))<0.000001}},"settled PTX recurred after closing outlet"] call _check;
        [!(_patient getVariable "ACM_breathing_TensionPneumothorax_State"),"closure silently recreated tension"] call _check;
    ''')


@pytest.mark.parametrize("operation", ["ncd", "seal"])
def test_temporary_outlets_do_not_accelerate_leak_healing(operation):
    execute(model_setup() + f'''
        [_patient,[1,1,0.8,0,0,0,1,1,0.5],false] call ACME_fnc_ptxPublish;
        {'_patient setVariable ["ACME_CS_holeData",[["front",[0.4,0.5],0,0,true]]];' if operation == 'seal' else ''}
        [_patient,"{operation}"] call ACME_fnc_ptxTreat;
        for "_i" from 1 to 60 do {{
            CBA_missionTime=10+_i; [_patient] call ACME_fnc_ptxTensionTick;
        }};
        private _s=_patient getVariable "ACME_ptx_state";
        [abs ((_s select 2)-0.7)<0.000001,"temporary outlet incorrectly healed persistent leak"] call _check;
        [!([_patient] call ACME_fnc_ptxCanClose),"temporary drainage made unresolved leak closure-ready"] call _check;
    ''')


@pytest.mark.parametrize("operation", ["thora", "tube"])
def test_definitive_treatment_restarts_observation_after_looser_ncd_stability(operation):
    tube = '_patient setVariable ["ACME_thora_tube_left",true];' if operation == "tube" else ""
    execute(model_setup() + f'''
        [_patient,[1,0.85,0.6,60,0,1,1,0.85,0.85],false] call ACME_fnc_ptxPublish;
        _patient setVariable ["ACME_thora_open_left","finger"];
        {tube}
        [_patient,"{operation}"] call ACME_fnc_ptxTreat;
        [_patient] call ACME_fnc_ptxTensionTick;
        private _s=_patient getVariable "ACME_ptx_state";
        [(_s select 2)>0 && {{(_s select 3)==1}},"prior temporary-outlet timer skipped definitive observation"] call _check;
    ''')


@pytest.mark.parametrize("context,air,pressure,tension", [
    ("[1,1,5,0,1,true,false,true]", 0.5, 0, False),
    ("[0,0,5,0,1,true,false,true]", 3, 0, False),
    ("[0,0,0,0,1,true,false,true]", 0.5, 0, False),
    ("[0,0,5,0,1,true,false,true]", 0.5, 0.8, False),
    ("[0,0,0,0,1,true,false,true]", 0.5, 0.8, True),
])
def test_interrupted_qualification_resets_timer_without_healing(context, air, pressure, tension):
    execute(function("ptxStep") + f'''
        private _result=[[1,{air},0.8,59,{pressure},0,1,{air},0.5],{context},1,{str(tension).lower()},600,600,60] call ACME_fnc_ptxStep;
        private _s=_result select 0;
        [(_s select 3)==0 && {{(_s select 2)>0.79}},"unqualified definitive observation healed leak or retained timer"] call _check;
        {'[(_result select 1),"quiet timer silently relieved established tension"] call _check;' if tension else ''}
    ''')


def test_open_external_wound_requires_a_new_full_observation_after_it_is_covered():
    execute(function("ptxStep") + r'''
        private _s=[1,0.5,0.8,0,0,0,1,0.5,0.5];
        for "_i" from 1 to 30 do {_s=([_s,[0,0,5,0,1,true,false,true],1,false,600,600,60] call ACME_fnc_ptxStep) select 0;};
        _s=([_s,[1,1,5,0,1,true,false,true],1,false,600,600,60] call ACME_fnc_ptxStep) select 0;
        [(_s select 3)==0 && {(_s select 2)>0},"missed chest communication retained prior observation"] call _check;
        for "_i" from 1 to 59 do {_s=([_s,[0,1,5,0,1,true,true,true],1,false,600,600,60] call ACME_fnc_ptxStep) select 0;};
        [(_s select 3)==59 && {(_s select 2)>0},"newly covered wound borrowed earlier observation"] call _check;
        _s=([_s,[0,1,5,0,1,true,true,true],1,false,600,600,60] call ACME_fnc_ptxStep) select 0;
        [(_s select 2)==0 && {(_s select 3)==60},"covered definitive drainage did not eventually settle"] call _check;
    ''')


@pytest.mark.parametrize("dt", [-10, 0])
def test_zero_or_negative_delta_cannot_advance_stability_or_settle_leak(dt):
    execute(function("ptxStep") + f'''
        private _s=[1,0.5,0.6,59,0,0,1,0.5,0.5];
        private _before=+_s;
        private _result=[_s,[0,0,5,0,1,true,false,true],{dt},false,600,600,60] call ACME_fnc_ptxStep;
        [(_result select 0) isEqualTo _before,"nonpositive delta changed canonical state"] call _check;
    ''')


def test_large_delta_is_bounded_and_cannot_skip_observation():
    execute(function("ptxStep") + r'''
        private _s=[1,0.5,0.6,0,0,0,1,0.5,0.5];
        _s=([_s,[0,0,5,0,1,true,false,true],600,false,600,600,60] call ACME_fnc_ptxStep) select 0;
        [(_s select 3)==5 && {(_s select 2)>0},"large time delta skipped observation clamp"] call _check;
    ''')


def test_legacy_seven_field_context_retains_natural_healing_coefficients():
    execute(function("ptxStep") + r'''
        private _s=[1,0.5,0.6,59,0,0,1,0.5,0.5];
        _s=([_s,[0,0,5,0,1,true,false],1,false,600,600,60] call ACME_fnc_ptxStep) select 0;
        [abs ((_s select 2)-(0.6-1/600))<0.000001,"legacy caller accidentally acquired accelerated settlement"] call _check;
        [(_s select 3)==60,"legacy stable timer changed"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '_s set [1,1.01];', '_s set [2,0.00001];', '_s set [3,59];', '_s set [4,0.11];',
    '_patient setVariable ["ACM_breathing_TensionPneumothorax_State",true];',
    '_patient setVariable ["ACME_CS_holeData",[["front",[0.4,0.5],0,0,false]]];',
    '_s set [0,"bad"];', '_s resize 8;',
])
def test_closure_readiness_rejects_unsettled_or_unobserved_or_invalid_state_without_writes(change):
    execute(model_setup() + f'''
        private _s=[1,0.5,0,60,0,0,1,0.5,0.5];
        {change}
        _patient setVariable ["ACME_ptx_state",_s];
        private _before=+(_patient getVariable "ACME_ptx_state");
        private _nativeBefore=_patient getVariable "ACM_breathing_Pneumothorax_State";
        [!([_patient] call ACME_fnc_ptxCanClose),"unsafe state qualified for surgical closure"] call _check;
        [(_patient getVariable "ACME_ptx_state") isEqualTo _before,"readiness query changed canonical state"] call _check;
        [(_patient getVariable "ACM_breathing_Pneumothorax_State")==_nativeBefore,"readiness query projected native state"] call _check;
        [count _events==0 && {{count _logs==0}},"readiness query disclosed or published hidden state"] call _check;
    ''')


def test_ready_closure_is_read_only_and_does_not_require_a_still_open_drain():
    execute(model_setup() + r'''
        private _s=[1,0.5,0,60,0,0,1,0.5,0.5];
        _patient setVariable ["ACME_ptx_state",_s];
        private _before=+_s;
        [([_patient] call ACME_fnc_ptxCanClose),"qualified settled state rejected after drain removal"] call _check;
        [(_patient getVariable "ACME_ptx_state") isEqualTo _before,"ready query changed state"] call _check;
        [count _events==0 && {count _logs==0},"ready query caused clinical/UI effects"] call _check;
    ''')


@pytest.mark.parametrize("dead", [False, True])
def test_healthy_or_dead_procedural_tract_does_not_get_stuck_behind_unadvanced_ptx_timer(dead):
    execute(model_setup() + f'''
        _patientAlive={str(not dead).lower()};
        _patient setVariable ["ACME_thora_open_left","finger"];
        _patient setVariable ["ACME_ptx_state",[1,0,0,0,0,0,0,0,0]];
        [([_patient] call ACME_fnc_ptxCanClose),"healthy/dead mechanical closure blocked forever"] call _check;
    ''')


def test_new_injury_restores_leak_and_resets_previously_settled_observation():
    execute(model_setup() + r'''
        [_patient,[1,0.5,0,60,0,0,1,0.5,0.5],false] call ACME_fnc_ptxPublish;
        [_patient,1] call ACME_fnc_ptxInjury;
        private _s=_patient getVariable "ACME_ptx_state";
        [(_s select 2)>0 && {(_s select 3)==0} && {(_s select 6)==2},"new injury inherited healed stability"] call _check;
        [!([_patient] call ACME_fnc_ptxCanClose),"new injury remained closure-ready"] call _check;
        [(_s select 1)>=1.5 && {(_patient getVariable "ACM_breathing_ChestInjury_State")},"new injury lost native injury consequences"] call _check;
    ''')


def test_equal_native_projection_does_not_reseed_a_settled_leak():
    execute(model_setup() + r'''
        [_patient,[1,0.5,0,60,0,0,1,0.5,0.5],false] call ACME_fnc_ptxPublish;
        private _before=+(_patient getVariable "ACME_ptx_state");
        private _adopted=[_patient] call ACME_fnc_ptxEnsure;
        [(_adopted select 2)==0 && {_adopted isEqualTo _before},"equal native projection reseeded settled leak"] call _check;
    ''')


def closure_setup(side="left", ready=True):
    leak, observed = (0, 60) if ready else (0.6, 0)
    return model_setup() + "".join(function(name) for name in (
        "chestSealEffectLocal", "thoraAftercareLocal", "thoraAftercareAck",
        "treatmentSupplyRefund", "thoraAftercareRetry", "thoraAftercareRequest", "thoraMouseDown",
    )) + "".join(function(name, native=True) for name in (
        "applyChestSealLocal", "Thoracostomy_closeLocal", "Thoracostomy_close",
    )) + f'''
        _alive=true;
        _patient setVariable ["ACM_breathing_Thoracostomy_State",1];
        _patient setVariable ["ACME_thora_open_{side}","finger"];
        _patient setVariable ["ACME_thora_incision_{side}",[[0.4,0.5],1,1]];
        [_patient,[1,0.5,{leak},{observed},0,0,1,0.5,0.5],false] call ACME_fnc_ptxPublish;
    '''


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("path", ["owner_seal", "native_close", "native_seal"])
def test_unsettled_surgical_closure_preserves_patent_drain_and_existing_ptx(side, path):
    operation = {
        "owner_seal": f'[_patient,_medic,"thoraSeal",["{side}",7]] call ACME_fnc_chestSealEffectLocal;',
        "native_close": '[_medic,_patient,true] call ACM_breathing_fnc_Thoracostomy_closeLocal;',
        "native_seal": '[_medic,_patient] call ACM_breathing_fnc_applyChestSealLocal;',
    }[path]
    execute(closure_setup(side, ready=False) + r'''
        private _before=+(_patient getVariable "ACME_ptx_state");
    ''' + operation + f'''
        private _after=_patient getVariable "ACME_ptx_state";
        [(_patient getVariable "ACME_thora_open_{side}")=="finger","unsettled closure removed surgical vent"] call _check;
        [!(_patient getVariable ["ACME_thora_sealed_{side}",false]) && {{!(_patient getVariable ["ACME_thora_closed_{side}",false])}},"unsettled closure published closed artwork"] call _check;
        [(_after select 1)==(_before select 1) && {{(_after select 2)==(_before select 2)}},"attempted closure changed clinical injury"] call _check;
        [count _logs==0,"blocked closure logged success"] call _check;
        {'[(_patient getVariable "ACM_breathing_ChestSeal_State"),"ordinary traumatic seal was blocked with surgical closure"] call _check;' if path == 'native_seal' else ''}
    ''')


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("path", ["owner_seal", "native_close", "native_seal"])
def test_ready_surgical_closure_preserves_settled_injury_and_no_long_term_recurrence(side, path):
    operation = {
        "owner_seal": f'[_patient,_medic,"thoraSeal",["{side}",7]] call ACME_fnc_chestSealEffectLocal;',
        "native_close": '[_medic,_patient,true] call ACM_breathing_fnc_Thoracostomy_closeLocal;',
        "native_seal": '[_medic,_patient] call ACM_breathing_fnc_applyChestSealLocal;',
    }[path]
    execute(closure_setup(side) + operation + f'''
        [(_patient getVariable "ACME_thora_open_{side}")!="finger","qualified closure left drain patent"] call _check;
        private _atClosure=+(_patient getVariable "ACME_ptx_state");
        [(_atClosure select 1)==0.5 && {{(_atClosure select 2)==0}},"closure erased residual collapse or recreated leak"] call _check;
        for "_i" from 1 to 120 do {{ CBA_missionTime=70+_i; [_patient] call ACME_fnc_ptxTensionTick; }};
        private _late=_patient getVariable "ACME_ptx_state";
        [(_late select 1)==0.5 && {{(_late select 2)==0}},"settled PTX recurred after approved closure"] call _check;
    ''')


def test_selected_surgical_seal_preserves_opposite_tube_and_external_wound_seal():
    execute(closure_setup() + r'''
        _patient setVariable ["ACME_thora_tube_right",true];
        _patient setVariable ["ACME_thora_open_right","finger"];
        _patient setVariable ["ACME_CS_holeData",[["front",[0.4,0.5],0,0,true]]];
        private _holes=+(_patient getVariable "ACME_CS_holeData");
        [_patient,_medic,"thoraSeal",["left",7]] call ACME_fnc_chestSealEffectLocal;
        [(_patient getVariable "ACME_thora_open_left")=="sealed","ready selected tract did not close"] call _check;
        [(_patient getVariable "ACME_thora_tube_right") && {(_patient getVariable "ACME_thora_open_right")=="finger"},"selected closure removed opposite outlet"] call _check;
        [(_patient getVariable "ACME_CS_holeData") isEqualTo _holes,"surgical seal changed traumatic wound coverage"] call _check;
        [!(_patient getVariable ["ACM_breathing_ChestSeal_State",false]),"selected surgical seal falsely declared whole chest sealed"] call _check;
    ''')


def transaction_setup(ready=True):
    from test_b205_thora_network_execution import block
    source = (ROOT / "addons/acm_extended/functions/fn_ownerDispatch.sqf").read_text()
    owner = adapt(block(source, 'case "thoraAftercare":'))
    owner = re.sub(r"\bfinite (_\w+)", r"([\1] call _finite)", owner)
    owner = owner.replace("serverTime", "_clock")
    return closure_setup(ready=ready) + r'''
        private _packets=[];
        private _deferred=[];
        private _inventoryAdds=0;
        private _testReceipt=[_medic,"ACM_ChestSeal",objNull,"seal-1"];
        missionNamespace setVariable ["ACME_supplyReceipts",createHashMapFromArray [["seal-1",_testReceipt]]];
        ACME_fnc_minigameInputMouse={false};
        ACME_fnc_thoraCanSweep={false};
        ACME_fnc_thoraRenderTube={};
        ACME_fnc_thoraSelectTool={};
        ACME_fnc_treatmentSupplyTake={_takes=_takes+1;_testReceipt};
        ace_common_fnc_addToInventory={_inventoryAdds=_inventoryAdds+1;};
        ACME_fnc_ownerDispatch={_packets pushBack _this;};
        CBA_fnc_waitAndExecute={_deferred pushBack _this;};
        uiNamespace setVariable ["ACME_Thora_Patient",_patient];
        uiNamespace setVariable ["ACME_Thora_Medic",_medic];
        uiNamespace setVariable ["ACME_Thora_Side","left"];
        uiNamespace setVariable ["ACME_Thora_Held","seal"];
        uiNamespace setVariable ["ACME_Thora_TubeSnap",true];
    ''' + 'private _ownerSeal={params ["_patient","_args"];' + owner + '};\n'


def test_unready_minigame_seal_does_not_consume_inventory_or_publish_tract():
    execute(transaction_setup(ready=False) + r'''
        [objNull,0] call ACME_fnc_thoraMouseDown;
        [_takes==0 && {count _packets==0},"unready UI seal consumed supply or crossed owner boundary"] call _check;
        [(_patient getVariable "ACME_thora_open_left")=="finger" && {!(_patient getVariable ["ACME_thora_closed_left",false])},"unready UI removed drainage"] call _check;
    ''')


def test_minigame_reserves_once_and_waits_for_owner_before_closing():
    execute(transaction_setup() + r'''
        [objNull,0] call ACME_fnc_thoraMouseDown;
        [objNull,0] call ACME_fnc_thoraMouseDown;
        [_takes==1 && {count _packets==1} && {count _deferred==1},"pending closure reserved or sent more than once"] call _check;
        [(_patient getVariable "ACME_thora_open_left")=="finger" && {!(_patient getVariable ["ACME_thora_closed_left",false])},"provider closed drain before owner acceptance"] call _check;
        private _packet=_packets select 0;
        [_packet select 0,_packet select 2] call _ownerSeal;
        [(_patient getVariable "ACME_thora_open_left")=="sealed","patient owner failed to accept ready seal"] call _check;
        private _reply=(_events select ((count _events)-1)) select 1;
        [(_reply select 5) && {(_reply select 6)=="seal"},"closure ACK has wrong outcome or operation"] call _check;
        _reply call ACME_fnc_thoraAftercareAck;
        _reply call ACME_fnc_thoraAftercareAck;
        [_inventoryAdds==0 && {count (missionNamespace getVariable "ACME_supplyReceipts")==0},"accepted seal was refunded or reservation retained"] call _check;
        [count (uiNamespace getVariable ["ACME_Thora_SealPending",[]])==0,"ACK did not clear matching seal pending state"] call _check;
    ''')


def test_owner_rechecks_new_injury_refunds_once_and_rejected_replay_cannot_later_close():
    execute(transaction_setup() + r'''
        [objNull,0] call ACME_fnc_thoraMouseDown;
        private _packet=_packets select 0;
        [_patient,1] call ACME_fnc_ptxInjury;
        [_packet select 0,_packet select 2] call _ownerSeal;
        private _reply=(_events select ((count _events)-1)) select 1;
        [!(_reply select 5),"owner trusted stale provider readiness after new injury"] call _check;
        _reply call ACME_fnc_thoraAftercareAck;
        _reply call ACME_fnc_thoraAftercareAck;
        [_inventoryAdds==1,"rejected seal was not refunded exactly once"] call _check;
        [(_patient getVariable "ACME_thora_open_left")=="finger","rejected owner request closed drainage"] call _check;
        [_patient,[1,0.5,0,60,0,0,2,0.5,0.5],false] call ACME_fnc_ptxPublish;
        [_packet select 0,_packet select 2] call _ownerSeal;
        private _replay=(_events select ((count _events)-1)) select 1;
        [!(_replay select 5) && {(_patient getVariable "ACME_thora_open_left")=="finger"},"rejected replay consumed already-refunded seal after recovery"] call _check;
        _replay call ACME_fnc_thoraAftercareAck;
        [_inventoryAdds==1,"rejected replay duplicated refund"] call _check;
    ''')


def test_accepted_replay_reports_original_success_without_closing_or_logging_twice():
    execute(transaction_setup() + r'''
        [objNull,0] call ACME_fnc_thoraMouseDown;
        private _packet=_packets select 0;
        [_packet select 0,_packet select 2] call _ownerSeal;
        private _version=_patient getVariable "ACME_thora_ver";
        private _logCount=count _logs;
        private _first=(_events select ((count _events)-1)) select 1;
        _first call ACME_fnc_thoraAftercareAck;
        [_packet select 0,_packet select 2] call _ownerSeal;
        private _repeat=(_events select ((count _events)-1)) select 1;
        [(_repeat select 5),"accepted replay incorrectly failed post-closure readiness"] call _check;
        [(_patient getVariable "ACME_thora_ver")==_version && {count _logs==_logCount},"accepted replay repeated closure or activity log"] call _check;
        _repeat call ACME_fnc_thoraAftercareAck;
        [_inventoryAdds==0,"accepted replay refunded committed seal"] call _check;
    ''')


@pytest.mark.parametrize("clock", [7, 26])
def test_owner_drops_unknown_future_or_expired_seal_packet_without_closing_or_settling_receipt(clock):
    execute(transaction_setup() + f'''
        [objNull,0] call ACME_fnc_thoraMouseDown;
        private _packet=_packets select 0;
        _clock={clock};
        [_packet select 0,_packet select 2] call _ownerSeal;
        [count _events==0 && {{(_patient getVariable "ACME_thora_open_left")=="finger"}},"unknown expired/future request closed drain or guessed terminal outcome"] call _check;
        [_inventoryAdds==0 && {{count (missionNamespace getVariable "ACME_supplyReceipts")==1}},"unknown expired/future request speculatively settled reservation"] call _check;
    ''')


def test_concurrent_providers_commit_one_seal_and_refund_the_losing_reservation():
    execute(transaction_setup() + r'''
        [objNull,0] call ACME_fnc_thoraMouseDown;
        private _packet=_packets select 0;
        private _otherArgs=+(_packet select 2);
        private _otherReceipt=[_medic,"ACM_ChestSeal",objNull,"seal-2"];
        private _pending=missionNamespace getVariable "ACME_supplyReceipts";
        _pending set ["seal-2",_otherReceipt];
        _otherArgs set [5,[8,1,10]];
        _otherArgs set [7,_otherReceipt];
        [_packet select 0,_packet select 2] call _ownerSeal;
        private _first=(_events select ((count _events)-1)) select 1;
        [(_first select 5),"first ready reservation failed"] call _check;
        _first call ACME_fnc_thoraAftercareAck;
        private _version=_patient getVariable "ACME_thora_ver";
        [_patient,_otherArgs] call _ownerSeal;
        private _other=(_events select ((count _events)-1)) select 1;
        [!(_other select 5),"concurrent reservation consumed second seal"] call _check;
        [((_events select ((count _events)-1)) select 2)==8,"concurrent ACK did not target original machine"] call _check;
        _other call ACME_fnc_thoraAftercareAck;
        _other call ACME_fnc_thoraAftercareAck;
        [_inventoryAdds==1 && {count (missionNamespace getVariable "ACME_supplyReceipts")==0},"concurrent supplies were not committed/refunded exactly once"] call _check;
        [(_patient getVariable "ACME_thora_ver")==_version,"concurrent loser republished closure"] call _check;
    ''')


@pytest.mark.parametrize("change", [
    '_patientLocal=false;', '_alive=false;', '_distance=6;',
    '_patient setVariable ["ACME_clinicalEpoch",8];',
    '_patient setVariable ["ACME_thora_tube_left",true];',
    '_patient setVariable ["ACME_thora_open_left","kelly"];',
])
def test_owner_aftercare_rejects_changed_owner_provider_epoch_or_tract(change):
    execute(closure_setup() + f'''
        {change}
        private _tractBefore=_patient getVariable "ACME_thora_open_left";
        private _accepted=[_patient,_medic,"left","seal",7,[7,1,10],false] call ACME_fnc_thoraAftercareLocal;
        [!_accepted,"invalid aftercare provider/owner/tract accepted"] call _check;
        [(_patient getVariable "ACME_thora_open_left")==_tractBefore,"invalid aftercare changed tract"] call _check;
        [count _logs==0,"invalid aftercare logged successful closure"] call _check;
    ''')


@pytest.mark.parametrize("injury_before_owner", [False, True])
def test_native_suture_logs_only_after_owner_accepts_closure(injury_before_owner):
    execute(closure_setup() + f'''
        [_medic,_patient] call ACM_breathing_fnc_Thoracostomy_close;
        [count _events==1 && {{count _logs==0}},"native public suture logged before owner acceptance"] call _check;
        private _nativeArgs=(_events select 0) select 1;
        {'[_patient,1] call ACME_fnc_ptxInjury;' if injury_before_owner else ''}
        _nativeArgs call ACM_breathing_fnc_Thoracostomy_closeLocal;
        [count _logs=={0 if injury_before_owner else 1},"native owner reported wrong accepted/rejected closure outcome"] call _check;
        [((_patient getVariable "ACME_thora_open_left")=="finger") isEqualTo {str(injury_before_owner).lower()},"native closure ignored current owner readiness"] call _check;
    ''')


@pytest.mark.parametrize("leak", [0, 0.6])
def test_pre_b271_state_adoption_discards_loose_observation_once_and_preserves_injury(leak):
    execute(model_setup() + f'''
        [_patient,[1,0.5,{leak},60,0,0,1,0.5,0.5],false] call ACME_fnc_ptxPublish;
        _patient setVariable ["ACME_ptx_observationRevision",0];
        [!([_patient] call ACME_fnc_ptxCanClose),"old episode qualified before observation migration"] call _check;
        private _adopted=[_patient] call ACME_fnc_ptxEnsure;
        [(_adopted select 3)==0 && {{(_adopted select 2)=={leak}}} && {{(_adopted select 1)==0.5}},"adoption preserved old timer or changed injury"] call _check;
        [(_patient getVariable "ACME_ptx_observationRevision")==1,"adoption did not publish observation revision"] call _check;
        _adopted set [3,12];
        [_patient,_adopted,false] call ACME_fnc_ptxPublish;
        private _again=[_patient] call ACME_fnc_ptxEnsure;
        [(_again select 3)==12 && {{(_again select 2)=={leak}}},"current revision repeatedly reset observation or reseeded healed leak"] call _check;
    ''')


def test_new_canonical_state_receives_current_observation_revision_without_claiming_stability():
    execute(model_setup() + r'''
        _patient setVariable ["ACME_ptx_state",[]];
        _patient setVariable ["ACME_ptx_observationRevision",0];
        _patient setVariable ["ACM_breathing_Pneumothorax_State",2];
        private _new=[_patient] call ACME_fnc_ptxEnsure;
        [(_patient getVariable "ACME_ptx_observationRevision")==1 && {(_new select 3)==0},"fresh episode lacked current revision or invented stability"] call _check;
        [(_new select 1)==2 && {(_new select 2)>0},"fresh native injury was not adopted"] call _check;
    ''')


def restore_setup():
    return model_setup() + "".join(function(name) for name in (
        "clinicalFields", "clinicalEncodedValid", "clinicalCodec", "clinicalValidate", "clinicalRestore",
    )) + r'''
        // These are unrelated engine/session rehydration boundaries. The full
        // production validator, codec, field whitelist and restore all execute.
        ACME_fnc_ownerRegister={};
        ACME_fnc_nrbStateCommit={};
        ace_medical_status_fnc_updateWoundBloodLoss={};
        CBA_fnc_serverEvent={_events pushBack _this;};
        [_patient,[1,0.5,0,60,0,0,1,0.5,0.5],false] call ACME_fnc_ptxPublish;
    '''


@pytest.mark.parametrize("include_revision", [False, True])
def test_snapshot_restore_cannot_borrow_new_observation_marker_for_old_episode(include_revision):
    execute(restore_setup() + f'''
        private _old=[1,0.5,0,60,0,0,1,0.5,0.5];
        private _rows=[["ACME_ptx_state",[_old,true] call ACME_fnc_clinicalCodec]];
        {'_rows pushBack ["ACME_ptx_observationRevision",["V",1]];' if include_revision else ''}
        [_patient,[3,_rows],7] call ACME_fnc_clinicalRestore;
        [(_patient getVariable "ACME_ptx_state") isEqualTo _old,"snapshot changed restored injury/timer before adoption"] call _check;
        {'[(_patient getVariable "ACME_ptx_observationRevision")==1,"new snapshot lost current observation revision"] call _check;' if include_revision else '[isNil {_patient getVariable "ACME_ptx_observationRevision"},"old snapshot borrowed existing new revision"] call _check;'}
        // This VM retains a namespace key cleared to nil. Arma treats that
        // object key as absent; reseed its default-zero engine boundary only
        // after asserting the real restore performed the required clear.
        {'_patient setVariable ["ACME_ptx_observationRevision",0];' if not include_revision else ''}
        private _adopted=[_patient] call ACME_fnc_ptxEnsure;
        [(_adopted select 3)=={60 if include_revision else 0} && {{(_adopted select 2)==0}},"restore incorrectly preserved old credit or reset current observation"] call _check;
        [([_patient] call ACME_fnc_ptxCanClose) isEqualTo {str(include_revision).lower()},"restored closure readiness disagrees with observation generation"] call _check;
    ''')


@pytest.mark.parametrize("revision", [0, 1, 2, '"bad"'])
def test_snapshot_validation_accepts_only_supported_observation_revision(revision):
    valid = revision in (0, 1)
    execute(restore_setup() + f'''
        private _result=[[3,[["ACME_ptx_observationRevision",["V",{revision}]]]]] call ACME_fnc_clinicalValidate;
        [(_result select 0) isEqualTo {str(valid).lower()},"snapshot accepted unsupported observation revision or rejected supported one"] call _check;
    ''')


@pytest.mark.parametrize("accepted", [False, True])
@pytest.mark.parametrize("later_clock", [26, 300])
def test_lost_ack_query_recovers_durable_original_outcome_without_reusing_supply(accepted, later_clock):
    reject = "" if accepted else "[_patient,1] call ACME_fnc_ptxInjury;"
    execute(transaction_setup() + f'''
        [objNull,0] call ACME_fnc_thoraMouseDown;
        private _firstPacket=_packets select 0;
        {reject}
        [_firstPacket select 0,_firstPacket select 2] call _ownerSeal;
        private _lost=(_events select ((count _events)-1)) select 1;
        [(_lost select 5) isEqualTo {str(accepted).lower()},"initial owner outcome incorrect"] call _check;
        // Drop the first ACK at the transport boundary. The real scheduled
        // query callback executes, using the still-reserved receipt and request.
        _events=[]; _packets=[];
        [_patient,[1,0.5,0,60,0,0,2,0.5,0.5],false] call ACME_fnc_ptxPublish;
        // Periodic lost-ACK queries keep the known decision alive; clinical
        // recovery cannot change its original rejected/accepted outcome.
        for "_at" from 26 to {later_clock - 1} step 16 do {{
            _clock=_at; _nowTime=_at;
            private _retryWork=_deferred deleteAt 0;
            (_retryWork select 1) call (_retryWork select 0);
            [count _packets==1 && {{(_packets select 0) isEqualTo _firstPacket}},"periodic retry replaced the original transaction"] call _check;
            private _lostPacket=_packets deleteAt 0;
            [_lostPacket select 0,_lostPacket select 2] call _ownerSeal;
            _events=[];
        }};
        _clock={later_clock}; _nowTime={later_clock};
        private _query=_deferred deleteAt 0;
        (_query select 1) call (_query select 0);
        [count _packets==1 && {{(_packets select 0) isEqualTo _firstPacket}},"lost-ACK recovery minted a new transaction or lost original request"] call _check;
        private _retry=_packets select 0;
        [_retry select 0,_retry select 2] call _ownerSeal;
        private _reply=(_events select ((count _events)-1)) select 1;
        [(_reply select 5) isEqualTo {str(accepted).lower()},"late known-result query changed original terminal outcome"] call _check;
        _reply call ACME_fnc_thoraAftercareAck;
        [_inventoryAdds=={0 if accepted else 1} && {{count (missionNamespace getVariable "ACME_supplyReceipts")==0}},"late ACK did not settle exact original reservation once"] call _check;
        [((_patient getVariable "ACME_thora_open_left")=="sealed") isEqualTo {str(accepted).lower()},"late result query repeated rejected closure after clinical state changed"] call _check;
        _packets=[];
        private _lastScheduled=_deferred deleteAt 0;
        (_lastScheduled select 1) call (_lastScheduled select 0);
        [count _packets==0 && {{count _deferred==0}} && {{_takes==1}},"settled receipt kept retrying or allocated another supply"] call _check;
    ''')


def test_widening_keeps_its_single_legacy_query_without_starting_seal_retry_loop():
    execute(transaction_setup() + r'''
        [_patient,_medic,"left","widen",true,_testReceipt] call ACME_fnc_thoraAftercareRequest;
        [count _packets==1 && {count _deferred==1},"widen entry did not issue one original packet/query"] call _check;
        _packets=[];
        private _query=_deferred deleteAt 0;
        (_query select 1) call (_query select 0);
        [count _packets==1 && {count _deferred==0},"legacy widen query started continuous seal reconciliation"] call _check;
    ''')


def test_seal_result_ledger_does_not_exhaust_a_patient_after_128_prior_transactions():
    execute(transaction_setup() + r'''
        private _old=[];
        for "_i" from 1 to 128 do {_old pushBack [7,[20,_i,9],"left",200,false];};
        _patient setVariable ["ACME_thoraSealResults",_old];
        [objNull,0] call ACME_fnc_thoraMouseDown;
        private _packet=_packets select 0;
        [_packet select 0,_packet select 2] call _ownerSeal;
        private _reply=(_events select ((count _events)-1)) select 1;
        [(_reply select 5) && {(_patient getVariable "ACME_thora_open_left")=="sealed"},"historical seal outcomes blocked fresh closure"] call _check;
        [count (_patient getVariable "ACME_thoraSealResults")==129,"fresh outcome was not retained beyond widening's separate cap"] call _check;
    ''')


def test_expired_inactive_result_is_not_guessed_or_replayed_and_fresh_transaction_prunes_it():
    execute(transaction_setup() + r'''
        [objNull,0] call ACME_fnc_thoraMouseDown;
        private _packet=_packets select 0;
        [_patient,1] call ACME_fnc_ptxInjury;
        [_packet select 0,_packet select 2] call _ownerSeal;
        _events=[];
        _clock=131;
        [_patient,[1,0.5,0,60,0,0,2,0.5,0.5],false] call ACME_fnc_ptxPublish;
        [_packet select 0,_packet select 2] call _ownerSeal;
        [count _events==0 && {(_patient getVariable "ACME_thora_open_left")=="finger"},"expired inactive query guessed outcome or re-executed closure"] call _check;
        private _new=+(_packet select 2);
        private _newReceipt=[_medic,"ACM_ChestSeal",objNull,"seal-2"];
        private _supplyPending=missionNamespace getVariable "ACME_supplyReceipts";
        _supplyPending set ["seal-2",_newReceipt];
        _new set [5,[7,2,131]];
        _new set [7,_newReceipt];
        [_patient,_new] call _ownerSeal;
        private _reply=(_events select ((count _events)-1)) select 1;
        [(_reply select 5),"fresh request after inactive expiry did not close ready tract"] call _check;
        [count (_patient getVariable "ACME_thoraSealResults")==1,"fresh result failed to prune inactive expired history"] call _check;
    ''')


@pytest.mark.parametrize("old_pending", ['[objNull,"left",7,10,[7,1,10]]', '[_patient,"right",6,10,[7,1,10]]'])
def test_old_pending_for_other_patient_or_epoch_does_not_block_current_ready_seal(old_pending):
    execute(transaction_setup() + f'''
        uiNamespace setVariable ["ACME_Thora_SealPending",{old_pending}];
        [objNull,0] call ACME_fnc_thoraMouseDown;
        [_takes==1 && {{count _packets==1}},"unrelated old pending token blocked current patient/epoch"] call _check;
    ''')
