"""B240: reviewed current contract, with individually reportable execution."""

def test_current_phase140_hemtt_runtime_warnings_gate():
    #!/usr/bin/env python3
    """Phase 140: close HEMTT runtime-risk warnings before first binary build.

    This gate targets diagnostics that are warnings/help in HEMTT but represent real
    undefined runtime state, stale function registration, or invalid UI command forms.
    """
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]

    def text(rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    laryngo = text("addons/acm_extended/functions/fn_laryngoTick.sqf")
    assert 'private _lift = uiNamespace getVariable ["ACME_laryngo_lift", 0];' in laryngo
    assert 'if (_gripHeld || {_lift > 0.02}) then {' in laryngo

    waste = text("addons/acm_extended/functions/fn_skWasteBegin.sqf")
    from current_source_contracts import _has
    assert _has(waste, '(ctrlPosition _plunger) params ["_plungerX", "", "_plungerW", "_plungerH"];')
    assert _has(waste, 'setMousePosition [_plungerX + (_plungerW / 2), _mouseYClamped];')
    assert 'setMousePosition [_uiX+_uiW/2,' not in waste

    compound = text("addons/acm_extended/functions/fn_skCompoundBegin.sqf")
    assert _has(compound, '(ctrlPosition _plunger) params ["_plungerX", "", "_plungerW", "_plungerH"];')
    assert _has(compound, 'setMousePosition [_plungerX + (_plungerW / 2), _mouseYClamped];')
    assert 'setMousePosition [(_uiX + (_uiW / 2)),' not in compound

    tx = text("addons/acm_extended/functions/fn_updateTransfusionControls.sqf")
    assert '[_bestEntry, _targetPatient getVariable ["ACME_infusion_BagMedications", []]]' in tx
    assert '[_bestEntry, _patient getVariable ["ACME_infusion_BagMedications", []]]' not in tx

    circ = text("addons/acm_extended/functions/fn_circHandle.sqf")
    assert 'private _distalDrugEffectActive = false;' in circ
    assert '_distalDrugEffectActive = true;' in circ
    assert '_state set ["distalDrugEffectActive", _distalDrugEffectActive];' in circ

    vent = text("addons/acm_extended/functions/fn_ventPanelTick.sqf")
    assert 'private _tgtM = uiNamespace getVariable ["ACME_vent_target", ACE_player];' in vent
    assert vent.count('private _tgtM = uiNamespace getVariable ["ACME_vent_target", ACE_player];') == 1

    det = text("addons/cbrn/functions/fnc_spawnChemicalDetonationEffect.sqf")
    assert 'createVehicleLocal getPos _object' in det
    assert '_attachedObject' not in det

    haz = text("addons/cbrn/functions/fnc_initHazardZone.sqf")
    assert 'private _curator = getAssignedCuratorLogic _spawner;' in haz
    assert '[_curator, _originObject]' in haz
    assert '_thisCurator' not in haz

    discard = text("addons/circulation/functions/fnc_Syringe_Discard.sqf")
    assert 'uniformContainer _medic, vestContainer _medic, backpackContainer _medic' in discard
    assert 'uniformContainer _unit' not in discard

    bandage = text("addons/core/overrides/fnc_handleBandageOpening.sqf")
    # Physical dressings no longer reopen: retain only wound-transfer bookkeeping.
    assert _has(bandage, '_target setVariable [VAR_BANDAGED_WOUNDS, _bandagedWounds, true];')
    assert _has(bandage, '_woundsOnPart pushBack _bandagedInjury;')
    assert not _has(bandage, 'call CBA_fnc_waitAndExecute;')
    assert not _has(bandage, 'call CBA_fnc_addPerFrameHandler;')
    assert '_openWoundsOnPart pushBack' not in bandage
    assert '_targetDamage' not in bandage

    stitch = text("addons/damage/functions/fnc_stitchWound.sqf")
    assert '_useSuture' not in stitch
    assert '_stitchTimeMultiplier' not in stitch
    assert '_timeToStitch' not in stitch

    injury = text("addons/gui/overrides/fnc_updateInjuryList.sqf")
    assert '} forEach _IVBagsBodyPart;' in injury
    assert '_allBagsBodyPart' not in injury

    spawn = text("addons/mission/functions/fnc_spawnCustomPatient.sqf")
    assert 'private _internalWounds = GET_INTERNAL_WOUNDS(_patient);' in spawn
    assert 'if (_hasInternalBleeding) then {' in spawn
    assert 'private _targetWoundID = _woundClass;' in spawn
    assert '_internalWounds set [_bodyPart, _internalWoundsPart];' in spawn

    for rel in (
        "addons/zeus/functions/fnc_assignFullHealFacility.sqf",
        "addons/zeus/functions/fnc_forceWakeUp.sqf",
    ):
        body = text(rel)
        assert '_display closeDisplay 0;' not in body

    post = text("addons/circulation/XEH_postInit.sqf")
    prep = text("addons/circulation/XEH_PREP.hpp")
    assert 'LINKFUNC(handleMed_AmiodaroneLocal)' not in post
    assert '//PREP(handleMed_AmiodaroneLocal);' in prep

    onload = text("addons/acm_extended/functions/fn_syringeKitOnLoad.sqf")
    size = text("addons/acm_extended/functions/fn_syringeKitSize.sqf")
    draw = text("addons/acm_extended/functions/fn_syringeKitDraw.sqf")
    for bad in (
        'lbSetCurSel [_sizes,',
        'lbSetCurSel [_sources,',
        'lbSetCurSel [(_display displayCtrl 86318),',
    ):
        assert bad not in onload + size + draw
    assert '_sizes lbSetCurSel 3;' in onload
    assert '_sources lbSetCurSel 0;' in onload
    assert '(_display displayCtrl 86318) lbSetCurSel -1;' in size
    assert '(_display displayCtrl 86318) lbSetCurSel -1;' in draw

    print("PASS phase140: runtime-risk HEMTT warnings closed before first binary build")


if __name__ == "__main__":
    test_current_phase140_hemtt_runtime_warnings_gate()
