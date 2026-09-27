#!/usr/bin/env python3
"""RC17 guard: wake interventions repair ACE medical/state-machine desynchronization."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

post = read("addons/core/XEH_postInit.sqf")
blast = read("addons/acm_extended/functions/fn_blastApply.sqf")
roc = read("addons/acm_extended/functions/fn_rocuroniumTick.sqf")
obt = read("addons/acm_extended/functions/fn_obtundedApply.sqf")
startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")

# Every ace_medical_WakeUp event gets a next-frame coherence check after native ACE has first chance.
# CBA publishes the casualty object directly, so the observer must normalize that object before scheduling repair.
assert '[QACEGVAR(medical,WakeUp), {' in post
wake = post.split('[QACEGVAR(medical,WakeUp), {', 1)[1].split('[QGVAR(playWakeUpSound), {', 1)[0]
assert 'private _unit = if (_this isEqualType objNull)' in wake
assert 'CBA_fnc_execNextFrame' in wake
assert 'FUNC(canWake)' in wake
assert 'FUNC(reconcileWake)' in wake
assert 'ACME_obtunded_wakeStimGraceUntil' in wake

gate = read("addons/core/functions/fnc_canWake.sqf")
machine = read("addons/core/ACM_Statemachine.hpp")
repair = read("addons/core/functions/fnc_reconcileWake.sqf")
assert 'if (_this isEqualType objNull) then {' in gate
assert 'condition = QUOTE([_this] call FUNC(canWake));' in machine
assert 'CBA_statemachine_fnc_getCurrentState' in repair
assert 'CBA_statemachine_fnc_manualTransition' in repair
assert '"Unconscious", "Injured"' in repair
assert 'ACEFUNC(medical_status,setUnconsciousState)' in repair

# Normal gameplay systems must use ACE's public state-machine setter for new KO/wake requests.
assert 'call ace_medical_fnc_setUnconscious;' in blast
assert 'ace_medical_status_fnc_setUnconsciousState' not in blast
assert 'call ace_medical_fnc_setUnconscious;' in roc
assert 'call ace_medical_status_fnc_setUnconsciousState;' not in roc

# Intentional KO -> obtunded conversion must use the same canonical wake authority as every other
# consciousness transition. The actual state-machine repair now lives centrally in reconcileWake.
assert 'ACM_core_fnc_requestWake' in obt
assert '"obtunded"' in obt
assert 'CBA_statemachine_fnc_manualTransition' not in obt
assert obt.index('call ACM_core_fnc_requestWake') < obt.index('call ACME_fnc_obtundedStateCommit')

assert 'ACME_buildBatch = "B153";' in startup
assert 'ACME_debugRevision = "";' in startup

print("PASS 1.2.3 stable: wake repair preserves CBA state synchronization and ACM lying-state recovery")
