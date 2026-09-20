#!/usr/bin/env python3
"""Phase 129: Hang Bag uses local visuals/custom IV rope and no transform/animation watchdog fighting."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
F=R/'addons/acm_extended/functions'
start=(F/'fn_hangBagStart.sqf').read_text()
tick=(F/'fn_hangBagTick.sqf').read_text()
stop=(F/'fn_hangBagStop.sqf').read_text()
line=(F/'fn_ivLineCreate.sqf').read_text()
init=(F/'fn_initHangBagRuntime.sqf').read_text()
assert 'createSimpleObject [_bagModel' in start
assert 'createVehicleLocal [0, 0, 0]' in start
assert 'hideObject true' in start
assert 'ACME_IVLine_Rope_Blood' in start
assert 'ACME_IVLine_Rope_Plasma' in start
assert 'ACME_hang_ropeClass' in start
assert '_ropeClass\n    ] call ACME_fnc_ivLineCreate' in start
assert '0.05, [_medic, _patient]' in start
assert 'private _desiredFlowMult' in tick
assert 'getVariable ["ACME_hang_flowMult", 1]) isNotEqualTo _desiredFlowMult' in tick
assert tick.count('call ACME_fnc_setVarNet') == 1
for bad in ['_medic setPosASL', '_medic setDir _lockDir', '_medic setVelocity [0,0,0]', '_medic setVelocityModelSpace']:
    assert bad not in tick
assert 'call ACME_fnc_doAnim;' not in tick
assert '[true, _medic] call ACME_fnc_hangBagStop' in tick
assert '[_medic, ""] call ACME_fnc_doAnimHeld' in stop
assert stop.index('[_medic, ""] call ACME_fnc_doAnimHeld') < stop.index('[_medic, _outAnim, 1] call ACME_fnc_doAnim')
assert 'ACME_hang_ropeClass = "ACME_IVLine_Rope";' in init
assert '["_ropeClass", "", [""]]' in line
print('PASS phase129: Hang Bag visual, custom IV rope and cancel lifecycle no longer fight provider transforms/animation')
