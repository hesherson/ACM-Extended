"""Run B272 vented thoracostomy recovery in the actual production SQF.

The B271 adapter supplies explicit native object/locality, clock, inventory,
network, UI and finite-number boundaries. Production Context, Ensure, Treat,
Step, Publish, aftercare and transaction code still execute without replacing
their clinical arithmetic or gates. ``finite`` fixtures receive finite values;
seven-field tests execute the retained legacy branch. Every VM run rejects
warning, error and fatal diagnostics. No Python physiology copy is used.
The VM's unimplemented HashMap getOrDefault in approximate publication is
adapted to membership/get/default with the original map, key and default.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

from test_b271_ptx_stability import BASE, function as fixture_function, model_setup, closure_setup, transaction_setup


def function(name, native=False):
    source = fixture_function(name, native=native)
    if name == "setVarNetApprox":
        original = '_cache getOrDefault [_key, []]'
        assert source.count(original) == 1
        source = source.replace(original, '[_cache, _key, []] call _getDefault')
    return source


def execute(code):
    vm = os.environ.get("SQFVM") or shutil.which("sqfvm")
    if not vm:
        pytest.skip("SQF-VM required")
    with tempfile.TemporaryDirectory(prefix="acme-b272-vented-") as directory:
        source = Path(directory) / "case.sqf"
        source.write_text(BASE.replace("B271_PTX_FAIL", "B272_VENTED_FAIL") + code +
                          '\ndiag_log (if (_ok) then {"B272_VENTED_OK"} else {"B272_VENTED_FAIL"});', encoding="utf-8")
        result = subprocess.run(
            [vm, "--automated", "--suppress-welcome", "--no-execute-print", "--no-work-print", "--input-sqf", str(source)],
            capture_output=True, text=True, timeout=20,
        )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert not any(tag in output for tag in ("[ERR]", "[FAT]", "[WRN]", "B272_VENTED_FAIL")), output
    assert "B272_VENTED_OK" in output, output
    return output


def covered_tract(side="left", *, legacy=False):
    return f'''
        _patient setVariable ["ACME_thora_open_{side}","sealed"];
        _patient setVariable ["ACME_thora_sealed_{side}",true];
        _patient setVariable ["ACME_thora_closed_{side}",{str(legacy).lower()}];
        _patient setVariable ["ACME_thora_incision_{side}",[[0.4,0.5],1,1]];
    '''


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("occlusion,expected", [(0, 2), (0.5, 1), (1, 0)])
def test_covered_finger_is_a_vented_definitive_outlet_including_legacy_closed_artwork(side, legacy, occlusion, expected):
    execute(function("ptxContext") + covered_tract(side, legacy=legacy) + f'''
        _patient setVariable ["ACME_CS_sealOcclusion",{occlusion}];
        private _before=+(_patient getVariable "ACME_ptx_state");
        private _c=[_patient] call ACME_fnc_ptxContext;
        [count _c==8 && {{abs ((_c select 2)-{expected})<0.000001}},"covered-finger vent capacity wrong"] call _check;
        [(_c select 6) && {{(_c select 5) isEqualTo {str(expected > 0).lower()}}}
            && {{(_c select 7) isEqualTo {str(expected > 0).lower()}}},"vent presence/definitive qualification wrong"] call _check;
        [(_patient getVariable "ACME_ptx_state") isEqualTo _before,"context changed injury state"] call _check;
        [count _events==0 && {{count _logs==0}},"read-only context published or logged"] call _check;
    ''')


@pytest.mark.parametrize("occlusion", [0, 0.5, 1])
@pytest.mark.parametrize("outlet", ["open", "same_tube", "opposite_tube"])
def test_open_finger_and_tube_drainage_outrank_a_covered_seal(occlusion, outlet):
    setup = covered_tract()
    if outlet == "open":
        setup = '_patient setVariable ["ACME_thora_open_left","finger"];'
    elif outlet == "same_tube":
        setup += '_patient setVariable ["ACME_thora_tube_left",true];'
    else:
        setup += '_patient setVariable ["ACME_thora_open_right","finger"]; _patient setVariable ["ACME_thora_tube_right",true];'
    execute(function("ptxContext") + setup + f'''
        _patient setVariable ["ACME_CS_sealOcclusion",{occlusion}];
        private _c=[_patient] call ACME_fnc_ptxContext;
        [(_c select 2)==5 && {{(_c select 5)}} && {{(_c select 7)}},"patent finger/tube lost full drainage to seal occlusion"] call _check;
    ''')


@pytest.mark.parametrize("hole_kind", ["visible_exit", "hidden_exit", "pending_penetrating"])
def test_vented_finger_cover_does_not_cover_a_separate_traumatic_communication(hole_kind):
    holes = '[["front",[0.4,0.5],0,0,true],["back",[0.4,0.5],0,0,false]]'
    pending = ""
    if hole_kind == "hidden_exit":
        holes = '[["front",[0.4,0.5],0,0,true],["back",[0.4,0.5],0,0,false,false]]'
    if hole_kind == "pending_penetrating":
        holes = '[["front",[0.4,0.5],0,0,true]]'
        pending = '_patient setVariable ["ACME_CS_penetratingWounds",[[1],[2]]]; _patient setVariable ["ACME_CS_processedPenetratingCount",1];'
    execute(function("ptxContext") + function("ptxStep") + covered_tract() + f'''
        _patient setVariable ["ACME_CS_holeData",{holes}];
        {pending}
        private _c=[_patient] call ACME_fnc_ptxContext;
        [(_c select 0)==1 && {{(_c select 1)==2}},"surgical dressing falsely covered separate wound"] call _check;
        private _s=[1,0.5,0.8,59,0,0,1,0.5,0.5];
        _s=([_s,_c,1,false,600,600,60] call ACME_fnc_ptxStep) select 0;
        [(_s select 2)>0.79 && {{(_s select 3)==0}},"uncovered separate communication earned settlement"] call _check;
    ''')


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("leak,progress,pressure", [(0.8, 0, 0), (0.6, 31, 0), (0, 60, 0), (0.8, 0, 0.8)])
def test_owner_can_place_a_vented_cover_before_settlement_without_instant_clinical_change(side, leak, progress, pressure):
    execute(closure_setup(side, ready=False) + f'''
        [_patient,[1,0.75,{leak},{progress},{pressure},0,1,0.75,0.5],false] call ACME_fnc_ptxPublish;
        _patient setVariable ["ACME_CS_sealOcclusion",1];
        private _before=+(_patient getVariable "ACME_ptx_state");
        private _accepted=[_patient,_medic,"thoraSeal",["{side}",7]] call ACME_fnc_chestSealEffectLocal;
        [_accepted,"valid early covered tract rejected"] call _check;
        [(_patient getVariable "ACME_ptx_state") isEqualTo _before,"placing vented cover changed air, leak, pressure or observation"] call _check;
        [(_patient getVariable "ACME_CS_sealOcclusion")==0 && {{(_patient getVariable "ACME_CS_sealVenting")==1}},"fresh dressing inherited an old obstructed vent"] call _check;
        [(_patient getVariable "ACME_thora_open_{side}")=="sealed" && {{(_patient getVariable "ACME_thora_sealed_{side}")}}
            && {{!(_patient getVariable ["ACME_thora_closed_{side}",false])}},"covered tract became an occlusive surgical closure"] call _check;
        private _c=[_patient] call ACME_fnc_ptxContext;
        [(_c select 2)==2 && {{(_c select 6)}} && {{(_c select 7)}},"accepted dressing lost vented outlet"] call _check;
    ''')


@pytest.mark.parametrize("ppv", [1, 1.5, 3])
@pytest.mark.parametrize("blood", [0, 1])
def test_covered_finger_settles_only_after_controlled_observation_then_resolves_to_zero(ppv, blood):
    execute(model_setup() + covered_tract() + f'''
        [_patient,[1,0.5,0.6,0,0,0,1,0.5,0.5],false] call ACME_fnc_ptxPublish;
        private _c=[_patient] call ACME_fnc_ptxContext;
        _c set [3,{blood}]; _c set [4,{ppv}];
        private _s=_patient getVariable "ACME_ptx_state";
        for "_i" from 1 to 59 do {{_s=([_s,_c,1,false,600,600,60] call ACME_fnc_ptxStep) select 0;}};
        [(_s select 2)>0 && {{(_s select 3)==59}} && {{(_s select 8)==0.5}},"covered tract settled or cleared residual before full observation"] call _check;
        _s=([_s,_c,1,false,600,600,60] call ACME_fnc_ptxStep) select 0;
        [(_s select 2)==0 && {{(_s select 3)==60}} && {{(_s select 8)<0.5}},"controlled covered tract failed to settle and begin residual clearance"] call _check;
        for "_i" from 1 to 600 do {{_s=([_s,_c,1,false,600,600,60] call ACME_fnc_ptxStep) select 0;}};
        [(_s select 1)==0 && {{(_s select 8)==0}} && {{(_s select 2)==0}},"covered finger retained permanent PTX or regenerated leak"] call _check;
    ''')


@pytest.mark.parametrize("occlusion,ppv", [(0, 3), (0.5, 1.5), (1, 1)])
def test_insufficient_vent_capacity_causes_gradual_air_gain_only_from_existing_leak(occlusion, ppv):
    execute(model_setup() + covered_tract() + f'''
        _patient setVariable ["ACME_CS_sealOcclusion",{occlusion}];
        _patient setVariable ["ACME_ptx_state",[1,0.75,1,30,0,0,1,0.75,0.5]];
        private _c=[_patient] call ACME_fnc_ptxContext; _c set [4,{ppv}];
        private _s=[1,0.75,1,30,0,0,1,0.75,0.5];
        private _next=([_s,_c,1,false,600,600,60] call ACME_fnc_ptxStep) select 0;
        [(_next select 1)>0.75 && {{(_next select 1)<0.76}} && {{(_next select 2)<1}}
            && {{(_next select 3)==0}},"overwhelmed vent failed to produce gradual existing-leak accumulation"] call _check;
        _s set [2,0]; _s set [3,60];
        _next=([_s,_c,1,false,600,600,60] call ACME_fnc_ptxStep) select 0;
        [(_next select 1)<0.75 && {{(_next select 2)==0}},"PPV or occlusion recreated settled injury"] call _check;
    ''')


@pytest.mark.parametrize("operation", ["thoraSeal", "burp", "thoraAftercare"])
@pytest.mark.parametrize("leak,progress", [(0.6, 31), (0, 60)])
def test_seal_and_reassessment_preserve_recovery_progress_and_settled_leak(operation, leak, progress):
    execute(model_setup() + covered_tract() + f'''
        [_patient,[1,2,{leak},{progress},0.8,0,1,2,0.5],true] call ACME_fnc_ptxPublish;
        _patient setVariable ["ACME_CS_sealOcclusion",0.9];
        private _before=+(_patient getVariable "ACME_ptx_state");
        [_patient,"{operation}"] call ACME_fnc_ptxTreat;
        private _s=_patient getVariable "ACME_ptx_state";
        [(_s select 2)=={leak} && {{(_s select 3)=={progress}}},"routine seal/aftercare reset healing progress or leak"] call _check;
        {'[_s isEqualTo _before,"seal placement directly relieved or worsened PTX"] call _check;' if operation == 'thoraSeal' else '[(_s select 1)<=1 && {(_s select 4)==0} && {!(_patient getVariable "ACM_breathing_TensionPneumothorax_State")},"valid vent release did not relieve air/pressure"] call _check;'}
        [(_patient getVariable "ACME_CS_sealOcclusion")=={0 if operation in ('burp', 'thoraSeal') else 0.9},"fresh cover/burp did not clear obstruction or another operation changed seal patency"] call _check;
    ''')


@pytest.mark.parametrize("operation", ["peel", "burp"])
@pytest.mark.parametrize("legacy", [False, True])
def test_actual_surgical_aftercare_preserves_progress_and_opposite_tube(operation, legacy):
    execute(closure_setup() + function("chestSealBurpReady") + covered_tract(legacy=legacy) + f'''
        private _debits=0;
        ACME_fnc_thoraDrainBloodLocal={{_debits=_debits+1;0}}; // Separate blood-owner debit boundary.
        _patient setVariable ["ACME_thora_open_right","finger"];
        _patient setVariable ["ACME_thora_tube_right",true];
        [_patient,[1,0.5,0,60,0,0,1,0.5,0.5],false] call ACME_fnc_ptxPublish;
        _patient setVariable ["ACME_CS_sealOcclusion",0.5];
        private _accepted=[_patient,_medic,"left","{operation}",7,[7,1,10],false] call ACME_fnc_thoraAftercareLocal;
        [_accepted && {{_debits==1}},"valid surgical aftercare was rejected or double-debited"] call _check;
        private _s=_patient getVariable "ACME_ptx_state";
        [(_s select 2)==0 && {{(_s select 3)==60}},"actual aftercare undid settled healing"] call _check;
        [(_patient getVariable "ACME_thora_tube_right") && {{(_patient getVariable "ACME_thora_open_right")=="finger"}},"selected aftercare altered opposite tube"] call _check;
        [(_patient getVariable "ACME_CS_sealOcclusion")=={0 if operation == 'burp' else 0.5},"burp failed to clear obstruction or peeling altered unrelated seal patency"] call _check;
        [(_patient getVariable "ACME_thora_open_left")=="{'finger' if operation == 'peel' else 'sealed'}", "aftercare did not preserve correct covered/open tract"] call _check;
    ''')


@pytest.mark.parametrize("outlet,factor", [(0, 1), (2, 1), (5, 5)])
@pytest.mark.parametrize("resolve_seconds", [60, 600])
def test_residual_clearance_has_bounded_gameplay_rate_and_tube_acceleration(outlet, factor, resolve_seconds):
    execute(function("ptxStep") + f'''
        private _s=[1,0.5,0,60,0,0,1,0.5,0.5];
        private _next=([_s,[0,0,{outlet},0,1,{str(outlet > 0).lower()},false,{str(outlet > 0).lower()}],1,false,600,600,60,{resolve_seconds}] call ACME_fnc_ptxStep) select 0;
        private _expected=0.5-{factor}/{resolve_seconds};
        [abs ((_next select 8)-_expected)<0.000001 && {{abs ((_next select 1)-_expected)<0.000001}},"residual clearance rate or tube factor wrong"] call _check;
        [(_next select 2)==0 && {{(_next select 6)==1}} && {{(_next select 7)==0.5}},"clearance changed injury identity/leak or native projection cursor"] call _check;
    ''')


@pytest.mark.parametrize("context,leak,pressure,tension", [
    ("[1,1,0.1,0,1,false,false,false]", 0, 0, False),
    ("[0,0,2,0,1,true,true,true]", 0.6, 0, False),
    ("[0,0,0,0,1,false,false,false]", 0, 0.8, False),
    ("[0,0,0,0,1,false,false,false]", 0, 0.8, True),
    ("[0,0,5,0,1,true,false]", 0, 0, False),
])
def test_unsafe_or_legacy_context_cannot_silently_clear_residual(context, leak, pressure, tension):
    execute(function("ptxStep") + f'''
        private _s=[1,0.5,{leak},0,{pressure},0,1,0.5,0.5];
        _s=([_s,{context},1,{str(tension).lower()},600,600,60] call ACME_fnc_ptxStep) select 0;
        [(_s select 8)==0.5,"unsafe or seven-field legacy context acquired residual clearance"] call _check;
    ''')


def test_new_trauma_and_reopened_external_wound_have_distinct_recurrence_causes():
    execute(model_setup() + covered_tract() + r'''
        [_patient,[1,0,0,60,0,0,1,0,0],false] call ACME_fnc_ptxPublish;
        _patient setVariable ["ACME_CS_holeData",[["back",[0.4,0.5],0,0,false]]];
        // A completely obstructed cover cannot offset the reopened external entry.
        _patient setVariable ["ACME_CS_sealOcclusion",1];
        [_patient] call ACME_fnc_ptxTensionTick;
        private _external=_patient getVariable "ACME_ptx_state";
        [(_external select 1)>0 && {(_external select 2)==0} && {(_external select 6)==1},"reopened wound confused external entry with new internal injury"] call _check;
        [_patient,1] call ACME_fnc_ptxInjury;
        private _new=_patient getVariable "ACME_ptx_state";
        [(_new select 2)>0 && {(_new select 6)==2} && {(_new select 3)==0},"new trauma failed to start a separate leaking injury"] call _check;
    ''')


@pytest.mark.parametrize("side", ["left", "right"])
def test_early_minigame_seal_reserves_once_and_owner_acceptance_retains_vent(side):
    execute(transaction_setup(ready=False) + f'''
        _patient setVariable ["ACME_thora_open_{side}","finger"];
        _patient setVariable ["ACME_thora_incision_{side}",[[0.4,0.5],1,1]];
        uiNamespace setVariable ["ACME_Thora_Side","{side}"];
        private _before=+(_patient getVariable "ACME_ptx_state");
        [objNull,0] call ACME_fnc_thoraMouseDown; [objNull,0] call ACME_fnc_thoraMouseDown;
        [_takes==1 && {{count _packets==1}} && {{count _deferred==1}},"early minigame seal did not reserve/send exactly once"] call _check;
        [(_patient getVariable "ACME_thora_open_{side}")=="finger","provider projected cover before owner accepted"] call _check;
        private _packet=_packets select 0; [_packet select 0,_packet select 2] call _ownerSeal;
        private _reply=(_events select ((count _events)-1)) select 1;
        [(_reply select 5),"owner rejected an early vented cover"] call _check;
        _reply call ACME_fnc_thoraAftercareAck; _reply call ACME_fnc_thoraAftercareAck;
        [_inventoryAdds==0 && {{count (missionNamespace getVariable "ACME_supplyReceipts")==0}},"accepted early seal was refunded or retained reservation"] call _check;
        [(_patient getVariable "ACME_ptx_state") isEqualTo _before,"owner transaction changed air/leak/progress immediately"] call _check;
        private _c=[_patient] call ACME_fnc_ptxContext;
        [(_c select 2)>=2 && {{(_c select 7)}},"owner-accepted cover lost vent"] call _check;
    ''')


@pytest.mark.parametrize("changed_state", ["tube", "kelly", "epoch"])
def test_owner_still_rejects_invalid_early_seal_transaction_and_refunds_exactly_once(changed_state):
    change = {
        "tube": '_patient setVariable ["ACME_thora_tube_left",true];',
        "kelly": '_patient setVariable ["ACME_thora_open_left","kelly"];',
        "epoch": '_patient setVariable ["ACME_clinicalEpoch",8];',
    }[changed_state]
    execute(transaction_setup(ready=False) + f'''
        [objNull,0] call ACME_fnc_thoraMouseDown; private _packet=_packets select 0;
        {change}
        [_packet select 0,_packet select 2] call _ownerSeal;
        private _reply=(_events select ((count _events)-1)) select 1;
        [!(_reply select 5),"owner accepted invalid tract/epoch merely because early cover is allowed"] call _check;
        _reply call ACME_fnc_thoraAftercareAck; _reply call ACME_fnc_thoraAftercareAck;
        [_inventoryAdds==1 && {{count (missionNamespace getVariable "ACME_supplyReceipts")==0}},"invalid early cover did not refund exact receipt once"] call _check;
        [!(_patient getVariable ["ACME_thora_sealed_left",false]),"rejected early cover published artwork"] call _check;
    ''')


def test_zero_or_negative_delta_and_legacy_seven_field_callers_retain_exact_state_contract():
    execute(function("ptxStep") + r'''
        private _s=[1,0.5,0,60,0,0,1,0.5,0.5];
        {
            private _next=([_s,[0,0,2,0,1,true,true,true],_x,false,600,600,60] call ACME_fnc_ptxStep) select 0;
            [_next isEqualTo _s,"nonpositive delta altered covered recovery"] call _check;
        } forEach [0,-5];
        private _legacy=([_s,[0,0,5,0,1,true,false],1,false,600,600,60] call ACME_fnc_ptxStep) select 0;
        [_legacy isEqualTo _s,"seven-field residual/observation contract changed"] call _check;
    ''')


@pytest.mark.parametrize("blood", [0, 1])
@pytest.mark.parametrize("hardcore", [False, True])
def test_surgical_cover_alone_runs_production_occlusion_worker_and_dry_vents_have_no_clog_timer(blood, hardcore):
    rate = 0.006 if hardcore else 0.0022
    execute(model_setup() + function("setVarNetApprox") + function("chestSealOcclusionTick") + covered_tract() + f'''
        [_patient,[1,0.5,0.6,0,0,0,1,0.5,0.5],false] call ACME_fnc_ptxPublish;
        _patient setVariable ["ACME_CS_sealOcclusion",0.2];
        _patient setVariable ["ACME_CS_sealVenting",0.8];
        _patient setVariable ["ACME_net_approxCache",createHashMapFromArray [
            ["acme_cs_sealocclusion",[0.2,10]], ["acme_cs_sealventing",[0.8,10]]]];
        missionNamespace setVariable ["ACME_hcEff_cs",{str(hardcore).lower()}];
        missionNamespace setVariable ["ACM_breathing_ChestInjury_Chances",createHashMapFromArray [[10,1]]];
        _patient setVariable ["ace_medical_openWounds",createHashMapFromArray [["body",[[10,1,{0.2 if blood else 0}]]]]];
        for "_i" from 1 to 100 do {{[_patient] call ACME_fnc_chestSealOcclusionTick;}};
        private _expected=0.2+100*{blood}*{rate};
        [abs ((_patient getVariable "ACME_CS_sealOcclusion")-_expected)<0.000001,"surgical cover was omitted from occlusion worker or dry vent acquired a mandatory clog timer"] call _check;
        [abs ((_patient getVariable "ACME_CS_sealVenting")-(1-_expected))<0.000001,"vent patency did not track real occlusion"] call _check;
        private _c=[_patient] call ACME_fnc_ptxContext;
        // Compare the context with the actual owner value. SQF's accumulated
        // scalar has rounding after 100 increments; its theoretical rate is
        // independently checked above without multiplying that rounding error.
        private _actualOcclusion=_patient getVariable "ACME_CS_sealOcclusion";
        [abs ((_c select 2)-2*(1-_actualOcclusion))<0.000001 && {{(_c select 7)}},"production worker and surgical outlet disagree on capacity"] call _check;
    ''')


@pytest.mark.parametrize("resolve_seconds", [60, 600, 1200])
def test_patient_owner_scheduler_routes_configured_residual_resolution_time(resolve_seconds):
    execute(model_setup() + covered_tract() + f'''
        [_patient,[1,0.5,0,60,0,0,1,0.5,0.5],false] call ACME_fnc_ptxPublish;
        missionNamespace setVariable ["ACME_ptx_resolveSec",{resolve_seconds}];
        [_patient] call ACME_fnc_ptxTensionTick;
        private _s=_patient getVariable "ACME_ptx_state";
        private _expected=0.5-1/{resolve_seconds};
        [abs ((_s select 8)-_expected)<0.000001 && {{abs ((_s select 1)-_expected)<0.000001}},"owner scheduler dropped custom residual clearance setting"] call _check;
        [(_s select 2)==0 && {{(_s select 6)==1}},"scheduler clearance regenerated healed injury"] call _check;
    ''')


@pytest.mark.parametrize("occlusion", [0, 1])
@pytest.mark.parametrize("factor", [1, 2, 5])
def test_ambient_pressure_change_can_expand_trapped_gas_but_never_regenerates_a_settled_leak(occlusion, factor):
    execute(model_setup() + function("ptxAmbientChange") + covered_tract() + f'''
        [_patient,[1,0.5,0,60,0,0,1,0.5,0.5],false] call ACME_fnc_ptxPublish;
        _patient setVariable ["ACME_CS_sealOcclusion",{occlusion}];
        [_patient,{factor}] call ACME_fnc_ptxAmbientChange;
        private _s=_patient getVariable "ACME_ptx_state";
        private _expected=0.5*{factor if occlusion else 1};
        [(_s select 1)==_expected && {{(_s select 8)==_expected}},"vented equalization or trapped-gas expansion wrong"] call _check;
        [(_s select 2)==0 && {{(_s select 6)==1}},"ambient pressure recreated internal injury"] call _check;
    ''')
