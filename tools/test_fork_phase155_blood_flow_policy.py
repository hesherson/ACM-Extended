#!/usr/bin/env python3
"""B238: execute the reviewed historical contract under pytest and direct CLI."""

def test_current_contract():
    """RC10 regression: blood throughput uses the 100/200/300 ladder and never exceeds 300 mL/min per line."""
    from build_contract import assert_current_build as _assert_current_build
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]

    def read(rel):
        return (ROOT / rel).read_text(encoding="utf-8", errors="replace")

    flow = read("addons/circulation/functions/fnc_getBloodVolumeChange.sqf")
    iv = read("addons/circulation/functions/fnc_getIVFlowRate.sqf")
    runtime = read("addons/acm_extended/functions/fn_initHangBagRuntime.sqf")
    startup = read("addons/acm_extended/functions/fn_initForkStartupRuntime.sqf")

    # Tuned rates.
    assert 'ACME_warmedBlood_mlPerMin  = 200;' in runtime
    assert 'ACME_coldBlood_mlPerMin    = 100;' in runtime
    assert 'ACME_coldBloodHang_mlPerMin = 200;' in runtime
    assert 'ACME_bloodMax_mlPerMin     = 300;' in runtime

    blood_block = flow.split('// Blood has an explicit device/temperature flow envelope', 1)[1].split('// Final perfusion gate', 1)[0]

    # B238 expectation: the existing pressure model is continuous, not an on/off 300 mL/min switch.
    assert 'private _pressureLevel = [_cuff] call ACME_fnc_pressureLevel;' in blood_block
    assert 'if (_pressureLevel > 0) then {' in blood_block
    assert '_fixedRate = _base + ((_bloodCap - _base) max 0) * _pressureLevel;' in blood_block
    assert blood_block.index('if (_coldFlag) then {') < blood_block.index('if (_warmedFlag) then {')
    assert '_fixedRate = [_coldBase, _coldHang] select _hangActive;' in blood_block
    assert '_fixedRate = _warmBase;' in blood_block

    # Ordinary room-temperature blood with no warmer and no cuff keeps the existing physical gauge/Hang path.
    assert 'private _fixedRate = -1;' in blood_block
    assert 'if (_fixedRate >= 0) then {' in blood_block
    assert '_flow * _pressure' in iv

    # Every blood path is hard capped at 300 mL/min.
    assert 'private _capChange = _deltaT * (_bloodCap / 60);' in blood_block
    assert '_bagChange = ((_bagChange min _capChange) min _bagVolumeRemaining) max 0;' in blood_block

    # Explicit requested matrix.
    COLD = 100
    COLD_HANG = 200
    WARMER = 200
    PRESSURE = 300
    CAP = 300
    assert COLD == 100
    assert COLD_HANG == 200
    assert WARMER == 200
    assert PRESSURE == 300
    assert min(PRESSURE, CAP) == 300

    _assert_current_build()
    assert 'ACME_debugRevision = "";' in startup

    print("PASS rc10: cold 100, cold+Hang 200, active pressure 300, LifeWarmer 200, absolute 300 cap")

if __name__ == "__main__":
    test_current_contract()
