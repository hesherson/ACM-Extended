"""B247: only changed Cheyne-Stokes RR should request replication; stale owner audio is silent."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "functions"

def test_cheyne_stokes_unchanged_rounded_rate_does_not_reenter_network_helper():
    code = (ROOT / "fn_cheyneStokesTick.sqf").read_text(encoding="utf-8-sig")
    gate = 'if ((_p getVariable ["ACME_cs_rrDrive", -1]) != _rr) then {'
    writer = '[_p, "ACME_cs_rrDrive", _rr] call ACME_fnc_setVarNet;'
    assert gate in code and code.index(gate) < code.index(writer)
    assert '_rr = round (_rr max 0 min 50);' in code
    assert '[_p, "cheyne"] call ACME_fnc_breathSoundsStart;' in code

def test_delayed_biot_gasp_cannot_emit_from_departed_owner():
    code = (ROOT / "fn_breathSoundsStart.sqf").read_text(encoding="utf-8-sig")
    assert 'if (isNull _u || {!alive _u} || {!local _u} || {(_u getVariable ["ACME_bs_mode", ""]) != "biot"}) exitWith {};' in code
    assert '["ACME_breathSay3D", [_u, "ACME_RoscGasp", _dist], _tg] call CBA_fnc_targetEvent;' in code
