"""B240: reviewed current contract, with individually reportable execution."""

def test_current_phase145_zone3_reboa_smart_bandage():
    #!/usr/bin/env python3
    """Phase 145 guards: Zone 3 AAJT-S, one-wedge occlusion, corpse persistence and native ACM bandaging."""
    from pathlib import Path
    import re

    ROOT = Path(__file__).resolve().parents[1]


    def txt(path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8", errors="replace")


    def need(cond: bool, msg: str) -> None:
        if not cond:
            raise AssertionError(msg)


    cfg = txt("addons/acm_extended/config.cpp")
    apply = txt("addons/acm_extended/functions/fn_aajtApply.sqf")
    occ = txt("addons/acm_extended/functions/fn_aajtOccludes.sqf")
    pain = txt("addons/acm_extended/functions/fn_aajtPainTick.sqf")
    posture = txt("addons/acm_extended/functions/fn_aajtDownedTick.sqf")
    collapse = txt("addons/acm_extended/functions/fn_aajtForceProne.sqf")
    getup = txt("addons/core/functions/fnc_getUp.sqf")

    need('displayName = "Apply AAJT-S (Zone 3 REBOA)";' in cfg, "AAJT: Zone 3 chest action missing")
    need('icon = "\\acm_extended\\ui\\items\\aajt-s_zone3_reboa_ca.paa";' in cfg, "AAJT: Zone 3 art not wired")
    need(cfg.count('treatmentTime = 20;') >= 3, "AAJT: all three application modes must take 20 seconds")
    need('ACME_AAJT_inguinalSide' in occ and '== "leftleg"' in occ and '== "rightleg"' in occ,
         "AAJT: inguinal placement is not single-side authoritative")
    need(occ.count('ACME_AAJT_zone3') >= 2, "AAJT: Zone 3 does not occlude both lower extremities")
    need('[_patient, "leftleg", true] call ACME_fnc_aajtSetLegTQ;' in apply
         and '[_patient, "rightleg", true] call ACME_fnc_aajtSetLegTQ;' in apply,
         "AAJT: Zone 3 whole-lower-extremity flow refresh missing")
    need('[_patient, _p, true] call ACME_fnc_aajtSetLegTQ;' in apply,
         "AAJT: unilateral inguinal whole-leg flow refresh missing")
    for path in (
        "addons/core/overrides/fnc_updateWoundBloodLoss.sqf",
        "addons/circulation/functions/fnc_getIVFlowRate.sqf",
        "addons/circulation/functions/fnc_getBloodVolumeChange.sqf",
        "addons/core/overrides/fnc_medicationLocal.sqf",
        "addons/core/overrides/fnc_checkPulseLocal.sqf",
    ):
        need("ACME_fnc_aajtOccludes" in txt(path), f"AAJT: central occlusion not consumed by {path}")
    from current_source_contracts import _has
    bridge=txt('addons/core/overrides/fnc_getBloodVolumeChange.sqf')
    need(_has(bridge, '[_unit, _deltaT, _syncValues] call ACM_circulation_fnc_getBloodVolumeChange'), 'ACE volume bridge must delegate to canonical circulation')
    need('}, 1.0,' in pain and '0.82' in pain and 'ace_medical_fnc_adjustPainLevel' in pain,
         "AAJT: severe but analgesia-compatible pain worker missing")
    need('}, 0.20,' in posture and 'in ["stand", "crouch"]' in posture and 'ACME_fnc_aajtForceProne' in posture,
         "AAJT: Zone 3 weight-bearing watcher missing")
    need('ace_medical_engine_fnc_setUnconsciousAnim' in collapse and '_patient setUnitPos "DOWN";' in collapse,
         "AAJT: failed Get Up does not collapse/ragdoll to prone")
    z = getup[getup.index('if (_patient getVariable ["ACME_AAJT_zone3"'):getup.index('// Head elevation owns')]
    need('exitWith' not in z and 'ACME_fnc_aajtDownedTick' in z,
         "AAJT: Get Up is swallowed instead of visibly failing after rise begins")

    life = txt("addons/acm_extended/functions/fn_registerClinicalLifecycleRuntime.sqf")
    resp = txt("addons/acm_extended/functions/fn_registerRhythmLifecycleRuntime.sqf")
    death = txt("addons/acm_extended/functions/fn_deathFreeze.sqf")
    need('EntityKilled' in life and 'ACME_fnc_deathFreeze' in life, "death: corpse freeze path missing")
    need('[_oldUnit] call ACME_fnc_deathFreeze' in resp and '[_newUnit] call ACME_fnc_clearAllAilments' in resp,
         "death: old corpse and new-life reset are not separated")
    need('[_patient, "begin", true] call ACME_fnc_clinicalReset' in death and 'ACME_fnc_clearAllAilments' not in death,
         "death: durable intervention evidence is still being hard-reset")
    for name in ("directPressureStart", "directPressureTick", "medicationRequest", "medicationLineLocal",
                 "skBeginInjection", "skConfirmInjection", "skInjectSite", "salineFlush"):
        treatment=txt(f"addons/acm_extended/functions/fn_{name}.sqf")
        if name == 'medicationLineLocal':
            # Corpse actions complete stock accounting but must not restart physiology.
            from source_scan import lex, matching
            tokens=lex(treatment);pairs=matching(tokens)
            at=treatment.index('if (!alive _patient) exitWith {')
            opening=next(i for i,t in enumerate(tokens) if t.offset==at+len('if (!alive _patient) exitWith '))
            corpse=treatment[tokens[opening].offset:tokens[pairs[opening]].offset+1]
            need(_has(corpse, '["ACME_medicationAck", [_medic,_id,true,"postmortem: no physiology"], _medic] call CBA_fnc_targetEvent;'), 'corpse medication must acknowledge successful treatment')
            need('ACM_' not in corpse and 'ace_medical_fnc' not in corpse, 'corpse receipt must not apply clinical physiology')
        else:
            need('!alive _patient' not in treatment,
                 f"death: treatment path {name} still rejects corpse solely for death")

    # B95 rollback: the experimental multi-bandage transaction was removed. ACM's normal one-action-per-bandage
    # behavior is authoritative again, including its native item consumption, timing and callbacks.
    actions = txt("addons/core/ACE_Medical_Treatment_Actions.hpp")
    need('class PressureBandage: BasicBandage {' in actions, "bandage: native PressureBandage action missing")
    need('items[] = {"ACM_PressureBandage"};' in actions and 'consumeItem = 1;' in actions,
         "bandage: native PressureBandage inventory semantics not restored")
    need('callbackSuccess = QACEFUNC(medical_treatment,bandage);' in actions,
         "bandage: native ACE/ACM bandage callback not restored")
    need('smartBandage' not in actions and 'Bandage Wounds' not in actions,
         "bandage: removed smart-bundle action is still wired")
    for name in (
        "fnc_canSmartBandage.sqf", "fnc_getSmartBandagePlan.sqf", "fnc_getSmartBandageTime.sqf",
        "fnc_smartBandageApplyLocal.sqf", "fnc_smartBandageCancel.sqf", "fnc_smartBandageProgress.sqf",
        "fnc_smartBandageRestore.sqf", "fnc_smartBandageStart.sqf", "fnc_smartBandageSuccess.sqf",
    ):
        need(not (ROOT / "addons/damage/functions" / name).exists(), f"bandage: retired smart-bundle file remains: {name}")

    need(not (ROOT / "addons/acm_extended/ui/nv_close").exists(), "assets: generated NV texture directory remains")
    need(not (ROOT / "addons/acm_extended/functions/fn_minigameVisionTextures.sqf").exists(), "assets: obsolete NV mapper remains")
    need((ROOT / "addons/acm_extended/ui/items/aajt-s_zone3_reboa_ca.paa").is_file(), "assets: Zone 3 AAJT artwork missing")
    allowed = {"base", "15_left", "15_right", "ej_15_left", "ej_15_right"}
    for gauge in ("14g", "16g", "18g", "20g"):
        got = {p.name for p in (ROOT / "addons/acm_extended/ui/iv" / gauge).iterdir() if p.is_dir()}
        need(got <= allowed, f"assets: obsolete IV angle family remains under {gauge}: {sorted(got-allowed)}")

    # Every ACME callback referenced by treatment/config surfaces must have both bytes and a CfgFunctions registration.
    refs = set(re.findall(r'\bACME_fnc_([A-Za-z0-9_]+)\b', cfg + actions))
    files = {p.stem[3:] for p in (ROOT / "addons/acm_extended/functions").glob("fn_*.sqf")}
    regs = set(re.findall(r'\bclass\s+([A-Za-z0-9_]+)\s*\{\s*\};', cfg))
    need(not (refs-files), f"paths: missing ACME function files: {sorted(refs-files)}")
    need(not (refs-regs), f"paths: unregistered ACME callbacks: {sorted(refs-regs)}")

    print("phase 145 Zone 3 REBOA/native bandage/corpse persistence regression: PASS")


if __name__ == "__main__":
    test_current_phase145_zone3_reboa_smart_bandage()
