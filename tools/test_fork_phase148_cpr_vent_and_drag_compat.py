#!/usr/bin/env python3
"""Phase 148: vent provider churn must not impersonate CPR transitions, and carry-drop must avoid ACE PREP races."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

cpr = (ROOT / "addons/circulation/functions/fnc_beginCPR.sqf").read_text(encoding="utf-8", errors="ignore")
vent = (ROOT / "addons/acm_extended/functions/fn_ventDriveTick.sqf").read_text(encoding="utf-8", errors="ignore")
compat = (ROOT / "addons/acm_extended/functions/fn_compatCheck.sqf").read_text(encoding="utf-8", errors="ignore")
startup = (ROOT / "addons/acm_extended/functions/fn_initForkStartupRuntime.sqf").read_text(encoding="utf-8", errors="ignore")
core_cfg = (ROOT / "addons/core/CfgFunctions.hpp").read_text(encoding="utf-8", errors="ignore")
core_prestart = (ROOT / "addons/core/XEH_preStart.sqf").read_text(encoding="utf-8", errors="ignore")
bindings = (ROOT / "addons/acm_extended/functions/fn_clinicalBindings.sqf").read_text(encoding="utf-8", errors="ignore")

# The ventilator may legitimately move ACM_breathing_BVM_provider in and out while CPR continues.
assert '[["bvmProvider", _patient]' in vent
assert '[["bvmProvider", objNull]' in vent

# CPR notifications/animation restarts are keyed to a CPR transition, not to BVM-provider churn.
assert "private _cprChanged = _cprNow isNotEqualTo _cprWasActive;" in cpr
assert "private _bvmChanged = _bvmNow isNotEqualTo _bvmWasActive;" in cpr
assert 'if (_cprChanged) then {\n                    [LLSTRING(CPR_Continued)' in cpr
assert 'if (_cprChanged && {_notInVehicle}) then {[_medic, _epoch] call _fnc_doCPRAnimation;};' in cpr

# ACE is allowed to own/recompile dropObject_carry. ACME reconciles the dropped patient on ACE's supported event.
assert '"ace_dragging_stoppedCarry"' in startup
assert '"ACM_LyingState"' in startup
assert '"ACM_core_getUpPrompt"' in startup
assert "class dropObject_carry" not in core_cfg
assert '"ace_dragging_fnc_dropObject_carry"' not in compat
assert "ace_dragging_fnc_dropObject_carry =" not in core_prestart
assert '"ace_dragging_fnc_dropObject_carry"' not in bindings

print("PASS phase148: CPR/vent isolation and event-based carry-drop reconciliation")
