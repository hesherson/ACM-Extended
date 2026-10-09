"""B240: reviewed current contract, with individually reportable execution."""

def test_current_phase129_hang_bag_visual_animation():
    #!/usr/bin/env python3
    """Phase 129: Hang Bag uses local visuals/custom IV rope and no transform/animation watchdog fighting."""
    from pathlib import Path
    R=Path(__file__).resolve().parents[1]
    F=R/'addons/acm_extended/functions'
    start=(F/'fn_hangBagStart.sqf').read_text()
    activate=(F/'fn_hangBagActivate.sqf').read_text()
    ack=(F/'fn_hangBagClaimAck.sqf').read_text()
    claim=(F/'fn_hangBagClaimLocal.sqf').read_text()
    tick=(F/'fn_hangBagTick.sqf').read_text()
    stop=(F/'fn_hangBagStop.sqf').read_text()
    prep=(F/'fn_hangBagPrep.sqf').read_text()
    restore=(F/'fn_hangBagRestoreWeapons.sqf').read_text()
    canstart=(F/'fn_hangBagCanStart.sqf').read_text()
    line=(F/'fn_ivLineCreate.sqf').read_text()
    init=(F/'fn_initHangBagRuntime.sqf').read_text()
    assert 'createSimpleObject [_bagModel' in activate
    assert 'createVehicleLocal [0, 0, 0]' in activate
    assert 'hideObject true' in activate
    assert 'ACME_IVLine_Rope_Blood' in activate
    assert 'ACME_IVLine_Rope_Plasma' in activate
    assert 'ACME_hang_ropeClass' in activate
    assert '_ropeClass\n    ] call ACME_fnc_ivLineCreate' in activate
    assert '0.05, [_medic, _patient]' in start
    from current_source_contracts import _has, inline_case
    assert _has(start, '[_patient, "hangBagClaim",')
    assert _has(start, 'call ACME_fnc_ownerDispatch;')
    assert not _has(start, 'call ACME_fnc_hangBagActivate;')
    assert 'ACME_hang_Claimed' in activate and '!local _medic' in activate
    assert _has(ack, 'if (_medic getVariable ["ACME_hang_Claimed", false]) exitWith {};')
    assert _has(ack, 'call ACME_fnc_hangBagActivate;')
    assert ack.index('if (_medic getVariable ["ACME_hang_Claimed", false]) exitWith') < ack.index('call ACME_fnc_hangBagActivate;')
    assert _has(claim, 'if (isNull _patient || {!local _patient}) exitWith {false};')
    assert _has(claim, 'private _nextFlow = (_flow max 1) min 5;')
    assert _has(claim, 'if ((_patient getVariable ["ACME_hang_flowMult", 1]) != _nextFlow) then')
    assert _has(claim, '_patient setVariable ["ACME_hang_flowMult", _nextFlow, true];')
    assert _has(tick, '[_patient, "hangBagRenew",')
    assert 'call ACME_fnc_setVarNet' not in tick
    assert _has(inline_case((F/'fn_ownerDispatch.sqf').read_text(), 'hangBagRenew'), 'call ACME_fnc_hangBagClaimLocal;')
    for bad in ['_medic setPosASL', '_medic setDir _lockDir', '_medic setVelocity [0,0,0]', '_medic setVelocityModelSpace']:
        assert bad not in tick
    assert 'call ACME_fnc_doAnim;' not in tick
    assert '[true, _medic] call ACME_fnc_hangBagStop' in tick
    assert '[_medic, ""] call ACME_fnc_doAnimHeld' in stop
    assert 'private _slots = [_ld select 0, _ld select 1];' in prep
    assert '_medic setVariable ["ACME_hang_savedWeaponSlots", _slots, true];' in prep
    assert 'alive _medic' not in restore
    assert '!local _medic' in restore
    assert '_medic setUnitLoadout' not in restore and '_medic setUnitLoadout' not in prep
    assert 'removeWeapon (primaryWeapon _medic)' in prep
    assert 'removeWeapon (secondaryWeapon _medic)' in prep
    assert 'addWeaponItem [_weapon' in restore
    assert 'ACME_hang_savedWeaponSlots", nil, true' in restore
    assert 'ACME_hangRestoreWeapons' in stop
    assert 'ACME_hang_Medic' in canstart and 'ACME_hang_Active' in canstart
    assert '_holderValid' in claim and '!_holderValid || {_exact}' in claim
    assert 'ACME_hang_ClaimOwner' in tick and 'ACME_hang_ClaimEpoch' in tick
    assert 'ACME_hang_ClaimAckAt' in tick and '>= 6' in tick
    assert '>= 2' in tick and 'ACME_hang_ClaimSequence' in tick
    assert '[_medic, _episodeStart] call ACME_fnc_hangBagRestoreWeapons' in stop
    assert stop.index('[_medic, ""] call ACME_fnc_doAnimHeld') < stop.index('[_medic, _outAnim, 1] call ACME_fnc_doAnim')
    assert 'ACME_hang_ropeClass = "ACME_IVLine_Rope";' in init
    assert '["_ropeClass", "", [""]]' in line
    print('PASS phase129: Hang Bag visual, custom IV rope and cancel lifecycle no longer fight provider transforms/animation')


if __name__ == "__main__":
    test_current_phase129_hang_bag_visual_animation()
