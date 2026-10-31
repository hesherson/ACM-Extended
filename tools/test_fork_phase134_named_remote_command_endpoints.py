#!/usr/bin/env python3
"""Phase 134: raw remoteExec commands are replaced with named fork-owned endpoints."""
from pathlib import Path


def test_raw_remote_commands_use_named_fork_endpoints():
    R=Path(__file__).resolve().parents[1]
    A=R/'addons/acm_extended'
    Air=R/'addons/airway'
    all_sqf='\n'.join(p.read_text(errors='ignore') for p in (R/'addons').rglob('*.sqf'))
    for raw in ['remoteExec ["say3D"','remoteExecCall ["say3D"','remoteExec ["forceWalk"','remoteExecCall ["forceWalk"','remoteExec ["deleteVehicle"','remoteExecCall ["deleteVehicle"']:
        assert raw not in all_sqf, raw
    for f in ['fn_remoteSay3D.sqf','fn_remoteDeleteVehicle.sqf','fn_forceWalkLocal.sqf']:
        assert (A/'functions'/f).is_file(), f
    assert (Air/'functions/fnc_remoteSay3D.sqf').is_file()
    config=(A/'config.cpp').read_text()
    for cls in ['remoteSay3D','remoteDeleteVehicle','forceWalkLocal']:
        assert f'class {cls} {{}};' in config
    prep=(Air/'XEH_PREP.hpp').read_text()
    assert 'PREP(remoteSay3D);' in prep
    assert 'ACME_fnc_remoteSay3D' in all_sqf
    assert 'ACME_fnc_forceWalkLocal' in all_sqf
    assert 'ACME_fnc_remoteDeleteVehicle' in all_sqf
    assert 'ACM_airway_fnc_remoteSay3D' in all_sqf
    print('PASS phase134: raw say3D/forceWalk/deleteVehicle remoteExec commands use named fork endpoints')


if __name__ == "__main__":
    test_raw_remote_commands_use_named_fork_endpoints()
