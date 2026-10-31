"""Run production optional-animation/Semi-Fowler workers in SQF-VM.

Only native engine observations/mutations and external CBA/ACE services are adapted. Clinical branching,
episode identity, carrier custody calls and delayed-worker cancellation execute from current production SQF.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
FUN = ROOT / "addons/acm_extended/functions"


def local_variable_writes(text):
    """Adapt broadcast flags and typed param defaults omitted by this older VM."""
    for match in reversed(list(re.finditer(r"\b(?:setVariable|param)\s*\[", text))):
        start = match.end() - 1
        depth = 0
        quote = False
        commas = []
        for end in range(start, len(text)):
            char = text[end]
            if char == '"':
                quote = not quote
            if quote:
                continue
            if char in "[({":
                depth += 1
            elif char in "])}":
                depth -= 1
            elif char == "," and depth == 1:
                commas.append(end)
            if depth == 0:
                break
        if len(commas) == 2:
            if match.group(0).startswith("setVariable"):
                assert text[commas[-1] + 1:end].strip() in ("true", "false")
            text = text[:commas[-1]] + text[end:]
    return text


def source(name):
    text = (FUN / f"fn_{name}.sqf").read_text()
    for command, field, default in (
        ("local", "testLocal", "true"), ("objectParent", "testParent", "objNull"),
        ("isPlayer", "testPlayer", "true"), ("backpack", "testBackpack", '""'),
        ("vest", "testVest", '""'), ("vestItems", "testVestItems", "[]"),
        ("getUnitLoadout", "testLoadout", "[]"), ("getMass", "testMass", "80"),
        ("getPosASL", "testPos", "[0,0,0]"), ("getDir", "testDir", "0"),
        ("animationState", "testAnim", '"ACM_LyingState"'),
        ("getAnimSpeedCoef", "testAnimRate", "1.5"),
        ("currentWeapon", "testWeapon", '""'), ("handgunWeapon", "testHandgun", '"pistol"'),
    ):
        text = re.sub(rf"\b{command}\s+(_\w+)\b", rf'(\1 getVariable ["{field}", {default}])', text)
    text = re.sub(r"\bremoveVest\s+(_\w+)", r"[\1] call ACME_test_removeVest", text)
    text = text.replace("hasInterface", "ACME_test_hasInterface").replace("clientOwner", "ACME_test_clientOwner")
    text = text.replace("serverTime", "ACME_test_serverTime").replace("toLowerANSI", "toLower")
    text = re.sub(r"\binputAction\s+_x\b", "ACME_test_input", text)
    return f"ACME_fnc_{name} = {{{local_variable_writes(text)}}};\n"


PRELUDE = r'''
ACME_test_hasInterface=true; ACME_test_clientOwner=2; ACME_test_serverTime=10;
CBA_missionTime=10; ACME_test_input=0; ACME_test_calls=[]; ACME_test_workers=[]; ACME_test_removed=[];
ACME_test_note={ACME_test_calls pushBack _this;};
ACME_test_assert={params ["_condition","_name"];if (!_condition) then {throw _name;};};
CBA_fnc_addPerFrameHandler={ACME_test_workers pushBack _this; count ACME_test_workers;};
CBA_fnc_removePerFrameHandler={ACME_test_removed pushBack (_this select 0);};
CBA_fnc_waitAndExecute={ACME_test_workers pushBack _this;};
CBA_fnc_execNextFrame={ACME_test_workers pushBack _this;};
CBA_fnc_globalEvent={_this call ACME_test_note;};
CBA_fnc_globalEventJIP={_this call ACME_test_note;};
CBA_fnc_serverEvent={_this call ACME_test_note;};
CBA_fnc_removeGlobalEventJIP={};
CBA_fnc_addKeyHandler={"key-id"}; CBA_fnc_removeKeyHandler={};
ACME_fnc_ownerDispatch={_this call ACME_test_note;};
ACME_fnc_headElevateCanStart={true}; ace_common_fnc_isAwake={true};
ACME_test_controlled=objNull; ACME_fnc_controlledProvider={ACME_test_controlled};
acre_sys_core_fnc_handleMultiPttKeyPressUp={["ptt-released"] call ACME_test_note;};
missionNamespace setVariable ["acre_sys_core_pttKeyDown",true];
ACME_fnc_patientInteractionDistance={0}; ACME_fnc_chestSealActualSide={"front"};
ACME_fnc_animBlocked={false}; ACME_fnc_choreographyRate={1.5};
ACME_fnc_releasePatient={}; ACME_fnc_headElevWatch={};
ACME_fnc_chestAccessManeuverActive={false};
ACME_fnc_headElevHoldClear={(_this select 0) setVariable ["ACME_headElev_hold",[]];};
ACME_fnc_headElevVestRestore={
    private _p=_this select 0;
    if (_p getVariable ["ACME_headElev_vestRemoved",false]) then {
        _p setVariable ["testVest", "PlateCarrier"];
        _p setVariable ["ACME_headElev_vestRemoved",false];
        ["vest-restored"] call ACME_test_note;
    };
};
ACME_fnc_chestAccessVestRestore={}; ACME_fnc_headElevMedicStart={};
ACME_fnc_headElevMedicSeq={}; ACME_fnc_medLog={};
ACME_fnc_manualPlateCarrierHeadElevSupport={false};
ACME_fnc_carrierInventoryCreate={"Box" createVehicle [0,0,0]};
ACME_test_removeVest={(_this select 0) setVariable ["testVest",""];["vest-removed"] call ACME_test_note;};
ACME_fnc_patientAnimRequest={ ["patient-animation",_this] call ACME_test_note; "patient-lease"; };
ACME_fnc_patientAnimRelease={}; ACME_fnc_doAnim={ ["animation",_this] call ACME_test_note; };
ACM_core_fnc_cprActive={false}; ACM_core_fnc_bvmActive={false};
ACME_fnc_chestAccessVestPark={};
ACME_fnc_headElevRestAnim={"ACM_LyingState"};
ACME_test_newPatient={
    private _p="Man" createVehicle [0,0,0];
    _p setVariable ["testBackpack","Pack"];
    _p setVariable ["testLoadout",[[],[],[],[],["PlateCarrier",[]]]];
    _p
};
'''


@pytest.fixture(scope="module")
def vm():
    binary = os.environ.get("ACME_SQF_VM") or os.environ.get("SQFVM") or shutil.which("sqfvm")
    if not binary:
        pytest.skip("SQF-VM required for production posture workers")
    return binary


def run(vm, names, body):
    code = PRELUDE + "\n".join(source(n) for n in names) + body + '\ndiag_log "POSTURE_RUNTIME_PASS";'
    with tempfile.TemporaryDirectory(prefix="acme-posture-") as temp:
        script = Path(temp) / "test.sqf"
        script.write_text(code)
        result = subprocess.run(
            [vm, "-a", "--suppress-welcome", "--no-execute-print", "--no-work-print",
             "--config", 'class CfgWeapons {class PlateCarrier {class ItemInfo {armor=10;class HitpointsProtectionInfo {class Chest {armor=10;};class Diaphragm {armor=10;};class Abdomen {armor=10;};};};};};',
             "--input-sqf", str(script)], capture_output=True, text=True, timeout=15,
        )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and "[ERR]" not in output and "[FAT]" not in output, output
    assert "POSTURE_RUNTIME_PASS" in output, output


@pytest.mark.parametrize("enabled", [None, True, False])
@pytest.mark.parametrize("carrier", [False, True])
def test_semi_fowler_keeps_support_cost_and_clinical_state_in_both_modes(vm, enabled, carrier):
    setting = "" if enabled is None else 'missionNamespace setVariable ["ACME_interventionAnimations",' + str(enabled).lower() + '];'
    if enabled is False:
        setting += 'ACME_fnc_chestSealActualSide={"back"};'  # Off mode must not request a physical pre-roll.
    run(vm, ["headElevCollision", "headElevPinPose", "headElevApplyTilt", "headElevAnimGuard", "headElevateStart", "headElevateStop"], setting + r'''
private _p=call ACME_test_newPatient; private _m="Man" createVehicle [0,0,0]; ACME_test_controlled=_p;
''' + ('_p setVariable ["testBackpack",""];_p setVariable ["testVest","PlateCarrier"];' if carrier else '') + r'''
[_m,_p] call ACME_fnc_headElevateStart;
[_p getVariable ["ACME_headElevated",false],"clinical elevation accepted"] call ACME_test_assert;
[(_p getVariable ["ACME_headElev_poseToken",""]) != "","placement has identity"] call ACME_test_assert;
''' + ('[(_p getVariable ["testVest","unexpected"]) == "","carrier physically removed"] call ACME_test_assert;[ACME_test_calls select [0,2] isEqualTo [["ptt-released"],["vest-removed"]],"PTT released before carrier removal"] call ACME_test_assert;' if carrier else '') + r'''
if !(missionNamespace getVariable ["ACME_interventionAnimations",true]) then {
    [!(_p getVariable ["ACME_headElev_visualActive",true]),"no visual elevation"] call ACME_test_assert;
    [(count ACME_test_workers)==0,"no animation or pin workers"] call ACME_test_assert;
    [{(_x select 0) in ["patient-animation","animation","ace_common_setMass"]} count ACME_test_calls == 0,"no motion or collision relaxation"] call ACME_test_assert;
    [_p] call ACME_fnc_headElevAnimGuard;
    [_p getVariable ["ACME_headElevated",false],"ordinary lying animation preserves logical benefit"] call ACME_test_assert;
    [!(_p getVariable ["ACME_headElev_Suspended",false]),"ordinary lying does not suspend benefit"] call ACME_test_assert;
} else {
    [_p getVariable ["ACME_headElev_visualActive",false],"default/on visual elevation"] call ACME_test_assert;
    [{(_x select 0)=="patient-animation"} count ACME_test_calls == 1,"normal lift requested"] call ACME_test_assert;
};
missionNamespace setVariable ["ACME_interventionAnimations",false];
[_m,_p] call ACME_fnc_headElevateStop;
[!(_p getVariable ["ACME_headElevated",true]),"logical lower completes off"] call ACME_test_assert;
[(_p getVariable ["ACME_headElev_poseToken","unexpected"]) == "","placement identity retired"] call ACME_test_assert;
''' + ('[(_p getVariable ["testVest",""]) == "PlateCarrier","original support carrier returned off"] call ACME_test_assert;' if carrier else ''))


def test_disabled_workers_cannot_reassert_queued_held_or_pinned_motion(vm):
    run(vm, ["doAnimHeld", "animQueue", "headElevPinPose"], r'''
private _u=call ACME_test_newPatient;
[_u,"TestMove",2] call ACME_fnc_doAnimHeld;
[_u,[["LaterMove",1]]] call ACME_fnc_animQueue;
[_u,2] call ACME_fnc_headElevPinPose;
[(count ACME_test_workers)==3,"enabled workers start"] call ACME_test_assert;
missionNamespace setVariable ["ACME_interventionAnimations",false];
{
    _x params ["_callback","_interval","_args"];
    [_args,_forEachIndex+1] call _callback;
} forEach +ACME_test_workers;
[(count ACME_test_removed)==3,"all previous workers retire"] call ACME_test_assert;
[(count ACME_test_calls)==0,"late workers cause no animation"] call ACME_test_assert;
[(_u getVariable ["ACME_animQ",[1]]) isEqualTo [],"queued motion discarded"] call ACME_test_assert;
[!(_u getVariable ["ACME_animQActive",true]),"queue controller released"] call ACME_test_assert;
ACME_test_workers=[];
[_u,"TestMove",2] call ACME_fnc_doAnimHeld;
[_u,[["LaterMove",1]]] call ACME_fnc_animQueue;
[_u,2] call ACME_fnc_headElevPinPose;
[(count ACME_test_workers)==0,"disabled requests create no workers"] call ACME_test_assert;
''')


def test_disabled_collision_request_preserves_pending_restore_generation(vm):
    run(vm, ["headElevCollision"], r'''
private _p=call ACME_test_newPatient;
[_p,false] call ACME_fnc_headElevCollision;
[(_p getVariable ["ACME_headElev_mass",-1]) == 80,"original mass retained"] call ACME_test_assert;
[_p,true] call ACME_fnc_headElevCollision;
private _epoch=_p getVariable ["ACME_headElev_collisionEpoch",-1];
missionNamespace setVariable ["ACME_interventionAnimations",false];
[_p,false] call ACME_fnc_headElevCollision;
[(_p getVariable ["ACME_headElev_collisionEpoch",-2]) == _epoch,"off disable cannot invalidate queued restore"] call ACME_test_assert;
private _restore=ACME_test_workers select 0; (_restore select 1) call (_restore select 0);
[isNil {_p getVariable "ACME_headElev_mass"},"original mass custody released"] call ACME_test_assert;
[(ACME_test_calls select ((count ACME_test_calls)-1)) isEqualTo ["ace_common_setMass",[_p,80]],"normal mass restored after disabling"] call ACME_test_assert;
''')


def test_empty_held_cancel_off_invalidates_old_worker_before_rapid_reenable(vm):
    run(vm, ["doAnimHeld"], r'''
private _u=call ACME_test_newPatient;
[_u,"OldTreatmentMove",2] call ACME_fnc_doAnimHeld;
private _oldGeneration=_u getVariable ["ACME_dah_gen",-1];
missionNamespace setVariable ["ACME_interventionAnimations",false];
[_u,""] call ACME_fnc_doAnimHeld;
[(_u getVariable ["ACME_dah_gen",-1]) > _oldGeneration,"disabled empty cancellation retained old generation"] call ACME_test_assert;
missionNamespace setVariable ["ACME_interventionAnimations",true];
private _old=ACME_test_workers select 0; [_old select 2,1] call (_old select 0);
[(count ACME_test_removed)==1 && {ACME_test_calls isEqualTo []},"old hold resurrected after rapid reenable"] call ACME_test_assert;
''')


def test_disabled_suspend_resume_preserves_support_custody_and_clinical_timing(vm):
    run(vm, ["headElevCollision", "headElevPropApply", "headElevApplyTilt", "headElevSuspend", "headElevResume"], r'''
missionNamespace setVariable ["ACME_interventionAnimations",false];
private _p=call ACME_test_newPatient;
_p setVariable ["ACME_headElevated",true]; _p setVariable ["ACME_headElev_poseToken","pose"];
_p setVariable ["ACME_headElev_noAnimation",true];
_p setVariable ["ACME_headElev_vestRemoved",true];
_p setVariable ["ACME_headElev_vestLoadout",["PlateCarrier",[]]];
[_p] call ACME_fnc_headElevSuspend;
[_p getVariable ["ACME_headElevated",false],"suspension keeps accepted placement"] call ACME_test_assert;
[_p getVariable ["ACME_headElev_Suspended",false],"clinical benefit suspended"] call ACME_test_assert;
[(_p getVariable ["ACME_headElev_suspendReadyAt",-1]) > CBA_missionTime,"clinical suspension deadline retained"] call ACME_test_assert;
[(count ACME_test_workers)==1,"only completion deadline queued"] call ACME_test_assert;
private _completion=ACME_test_workers select 0;
(_completion select 1) call (_completion select 0);
[(_p getVariable ["ACME_headElev_suspendPending","unexpected"]) == "","suspension completion acknowledged"] call ACME_test_assert;
[_p] call ACME_fnc_headElevResume;
[!(_p getVariable ["ACME_headElev_Suspended",true]),"clinical posture resumed"] call ACME_test_assert;
[_p getVariable ["ACME_headElev_vestRemoved",false],"support carrier custody retained through temporary flat maneuver"] call ACME_test_assert;
[(count ACME_test_calls)==0,"suspend/resume creates no move or collision change"] call ACME_test_assert;
''')


def test_manual_support_off_retains_real_hold_and_movement_cancellation(vm):
    run(vm, ["headElevHoldStart"], r'''
missionNamespace setVariable ["ACME_interventionAnimations",false];
private _p=call ACME_test_newPatient; private _m="Man" createVehicle [0,0,0]; ACE_player=_m;
_p setVariable ["ACME_headElevated",true]; _p setVariable ["ACME_headElev_poseToken","pose"];
_p setVariable ["ACME_headElev_hold",[_m,"pose",10]];
ACM_core_fnc_beginContinuousAction={
    params ["_args","_start","_cancel","_tick"];
    ACM_core_ContinuousAction_Active=true;
    ACME_test_continuousArgs=_args; ACME_test_cancel=_cancel; ACME_test_tick=_tick;
    _args call _start; true
};
private _started=[_m,_p,"head","pose",true] call ACME_fnc_headElevHoldStart;
[_started isEqualTo true,"logical support started"] call ACME_test_assert;
[(_m getVariable ["ACME_headElev_holding",[]]) isEqualTo [_p,"pose"],"provider and patient bound"] call ACME_test_assert;
[(count ACME_test_workers)==0,"no presentation hold worker"] call ACME_test_assert;
ACME_test_continuousArgs call ACME_test_tick;
[ACM_core_ContinuousAction_Active,"stationary support remains active"] call ACME_test_assert;
ACME_test_input=1; ACME_test_continuousArgs call ACME_test_tick;
[!ACM_core_ContinuousAction_Active,"movement cancels physical support even off"] call ACME_test_assert;
ACME_test_continuousArgs call ACME_test_cancel;
[(_m getVariable ["ACME_headElev_holding",[1]]) isEqualTo [],"provider hold cleared"] call ACME_test_assert;
[{(_x select 1)=="headElevHoldRelease"} count ACME_test_calls == 1,"patient receives exact support release"] call ACME_test_assert;
''')


@pytest.mark.parametrize("enabled", [None, True, False])
def test_animation_preflight_off_is_ready_without_holstering_or_reserving(vm, enabled):
    setting = "" if enabled is None else 'missionNamespace setVariable ["ACME_interventionAnimations",' + str(enabled).lower() + '];'
    run(vm, ["medicAnimationPrep"], setting + r'''
private _m="Man" createVehicle [0,0,0];
_m setVariable ["testWeapon","rifle"]; _m setVariable ["testAnim","amovpknlmstpsraswrfldnon"];
ace_weaponselect_fnc_putWeaponAway={["holster"] call ACME_test_note;};
private _delay=[_m] call ACME_fnc_medicAnimationPrep;
if (missionNamespace getVariable ["ACME_interventionAnimations",true]) then {
    [_delay > 0,"normal holster settle deadline retained"] call ACME_test_assert;
    [ACME_test_calls isEqualTo [["holster"]],"enabled/default preflight holsters once"] call ACME_test_assert;
    [(_m getVariable ["ACME_medicAnimationPrep",[]]) isEqualTo ["empty_hands_once",10,"rifle"],"normal one-shot reservation recorded"] call ACME_test_assert;
} else {
    [_delay == 0,"disabled preflight immediately ready"] call ACME_test_assert;
    [ACME_test_calls isEqualTo [],"disabled preflight does not holster"] call ACME_test_assert;
    [isNil {_m getVariable "ACME_medicAnimationPrep"},"disabled preflight creates no reservation"] call ACME_test_assert;
    _m setVariable ["ACME_medicAnimationPrep",["empty_hands_once",9,"rifle"]];
    [_m] call ACME_fnc_medicAnimationPrep;
    [(_m getVariable ["ACME_medicAnimationPrep",[]]) isEqualTo ["empty_hands_once",9,"rifle"],"old one-shot reservation left intact"] call ACME_test_assert;
};
''')
