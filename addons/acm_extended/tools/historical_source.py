"""Read current source for pre-fork historical contracts. No source or global patches.

Aliases are exact reviewed moves, not a fuzzy filename search. Only the old startup
and debug dispatchers expand statically named initialization/debug module calls.
This is a structural source bundle, not proof of runtime branch reachability.
Use plain Path.read_text for a single-file snapshot or any execution test.
"""
from pathlib import Path
from source_scan import lex
ROOT = Path(__file__).resolve().parents[3]
ALIASES = {'addons/acm_extended/overrides/fn_Syringe_Inject.sqf': 'addons/circulation/functions/fnc_Syringe_Inject.sqf',
 'addons/acm_extended/overrides/fn_Thoracostomy_closeLocal.sqf': 'addons/breathing/functions/fnc_Thoracostomy_closeLocal.sqf',
 'addons/acm_extended/overrides/fn_Thoracostomy_insertChestTubeLocal.sqf': 'addons/breathing/functions/fnc_Thoracostomy_insertChestTubeLocal.sqf',
 'addons/acm_extended/overrides/fn_Thoracostomy_resealChestTubeLocal.sqf': 'addons/breathing/functions/fnc_Thoracostomy_resealChestTubeLocal.sqf',
 'addons/acm_extended/overrides/fn_Thoracostomy_startLocal.sqf': 'addons/breathing/functions/fnc_Thoracostomy_startLocal.sqf',
 'addons/acm_extended/overrides/fn_aedAnalyzeRhythm.sqf': 'addons/circulation/functions/fnc_AED_AnalyzeRhythm.sqf',
 'addons/acm_extended/overrides/fn_applyChestSealLocal.sqf': 'addons/breathing/functions/fnc_applyChestSealLocal.sqf',
 'addons/acm_extended/overrides/fn_attemptROSC.sqf': 'addons/circulation/functions/fnc_attemptROSC.sqf',
 'addons/acm_extended/overrides/fn_beginCPR.sqf': 'addons/circulation/functions/fnc_beginCPR.sqf',
 'addons/acm_extended/overrides/fn_canOpenMenu.sqf': 'addons/gui/overrides/fnc_canOpenMenu.sqf',
 'addons/acm_extended/overrides/fn_canTreatCached.sqf': 'addons/core/overrides/fnc_canTreatCached.sqf',
 'addons/acm_extended/overrides/fn_canUseBVM.sqf': 'addons/breathing/functions/fnc_canUseBVM.sqf',
 'addons/acm_extended/overrides/fn_checkBreathingLocal.sqf': 'addons/breathing/functions/fnc_checkBreathingLocal.sqf',
 'addons/acm_extended/overrides/fn_collectActions.sqf': 'addons/gui/overrides/fnc_collectActions.sqf',
 'addons/acm_extended/overrides/fn_deserializeState.sqf': 'addons/core/overrides/fnc_deserializeState.sqf',
 'addons/acm_extended/overrides/fn_feelPulse.sqf': 'addons/circulation/functions/fnc_feelPulse.sqf',
 'addons/acm_extended/overrides/fn_genEKG.sqf': 'addons/circulation/functions/fnc_displayAEDMonitor_generateEKG.sqf',
 'addons/acm_extended/overrides/fn_getBloodVolumeChange.sqf': 'addons/core/overrides/fnc_getBloodVolumeChange.sqf',
 'addons/acm_extended/overrides/fn_getCardiacOutput.sqf': 'addons/core/overrides/fnc_getCardiacOutput.sqf',
 'addons/acm_extended/overrides/fn_getDogtagData.sqf': 'addons/core/overrides/fnc_getDogtagData.sqf',
 'addons/acm_extended/overrides/fn_getUp.sqf': 'addons/core/functions/fnc_getUp.sqf',
 'addons/acm_extended/overrides/fn_handleAirwayObstruction_Vomit.sqf': 'addons/airway/functions/fnc_handleAirwayObstruction_Vomit.sqf',
 'addons/acm_extended/overrides/fn_handleEffects.sqf': 'addons/core/overrides/fnc_handleEffects.sqf',
 'addons/acm_extended/overrides/fn_handleMed_NaloxoneLocal.sqf': 'addons/circulation/functions/fnc_handleMed_NaloxoneLocal.sqf',
 'addons/acm_extended/overrides/fn_handlePneumothorax.sqf': 'addons/breathing/functions/fnc_handlePneumothorax.sqf',
 'addons/acm_extended/overrides/fn_handleReversibleCardiacArrest.sqf': 'addons/circulation/functions/fnc_handleReversibleCardiacArrest.sqf',
 'addons/acm_extended/overrides/fn_handleUnitVitals.sqf': 'addons/core/overrides/fnc_handleUnitVitals.sqf',
 'addons/acm_extended/overrides/fn_inspectChestLocal.sqf': 'addons/breathing/functions/fnc_inspectChestLocal.sqf',
 'addons/acm_extended/overrides/fn_medicationLocal.sqf': 'addons/core/overrides/fnc_medicationLocal.sqf',
 'addons/acm_extended/overrides/fn_performNCDLocal.sqf': 'addons/breathing/functions/fnc_performNCDLocal.sqf',
 'addons/acm_extended/overrides/fn_resetVariables.sqf': 'addons/core/functions/fnc_resetVariables.sqf',
 'addons/acm_extended/overrides/fn_syringeDrawButton.sqf': 'addons/circulation/functions/fnc_Syringe_Draw_Button.sqf',
 'addons/acm_extended/overrides/fn_syringeGetMedicationList.sqf': 'addons/circulation/functions/fnc_Syringe_GetMedicationList.sqf',
 'addons/acm_extended/overrides/fn_syringePrepareFinish.sqf': 'addons/circulation/functions/fnc_Syringe_PrepareFinish.sqf',
 'addons/acm_extended/overrides/fn_syringeUpdateMedicationList.sqf': 'addons/circulation/functions/fnc_Syringe_UpdateMedicationList.sqf',
 'addons/acm_extended/overrides/fn_tourniquetRemove.sqf': 'addons/core/overrides/fnc_tourniquetRemove.sqf',
 'addons/acm_extended/overrides/fn_treatment.sqf': 'addons/core/overrides/fnc_treatment.sqf',
 'addons/acm_extended/overrides/fn_updateActions.sqf': 'addons/gui/overrides/fnc_updateActions.sqf',
 'addons/acm_extended/overrides/fn_updateCirculationState.sqf': 'addons/circulation/functions/fnc_updateCirculationState.sqf',
 'addons/acm_extended/overrides/fn_updateHeartRate.sqf': 'addons/core/overrides/fnc_updateHeartRate.sqf',
 'addons/acm_extended/overrides/fn_useBVM.sqf': 'addons/breathing/functions/fnc_useBVM.sqf',
 'addons/acm_extended/overrides/fn_useStethoscope.sqf': 'addons/breathing/functions/fnc_useStethoscope.sqf'}

ALIASES['addons/acm_extended/overrides/fn_onMedicationUsage.sqf'] = 'addons/core/overrides/fnc_onMedicationUsage.sqf'

ALIASES['addons/acm_extended/overrides/fn_setIVLocal.sqf'] = 'addons/circulation/functions/fnc_setIVLocal.sqf'

ALIASES['addons/acm_extended/overrides/fn_getCardiacMedicationEffects.sqf'] = 'addons/circulation/functions/fnc_getCardiacMedicationEffects.sqf'

ALIASES['addons/acm_extended/overrides/fn_getNauseaMedicationEffects.sqf'] = 'addons/circulation/functions/fnc_getNauseaMedicationEffects.sqf'

ALIASES['addons/acm_extended/overrides/fn_updateOxygen.sqf'] = 'addons/core/overrides/fnc_updateOxygen.sqf'

ALIASES['addons/acm_extended/overrides/fn_handleMed_AtropineLocal.sqf'] = 'addons/circulation/functions/fnc_handleMed_AtropineLocal.sqf'

ALIASES['addons/acm_extended/overrides/fn_handleMed_DimercaprolLocal.sqf'] = 'addons/circulation/functions/fnc_handleMed_DimercaprolLocal.sqf'

def read_source(path, encoding="utf-8-sig", errors="strict"):
    path = Path(path).resolve()
    relative = path.relative_to(ROOT).as_posix()
    path = ROOT / ALIASES.get(relative, relative)
    def expand(current, visited):
        if current in visited:
            return ""
        visited.add(current)
        text = current.read_text(encoding=encoding, errors=errors)
        parts = [text]
        tokens = lex(text)
        values = [t.value for t in tokens]
        names = []
        for i, token in enumerate(values[:-1]):
            name = values[i+1]
            if tokens[i].kind != "ident" or tokens[i+1].kind != "ident" or token != "call" or not name.startswith("ACME_fnc_"):
                continue
            name = name[len("ACME_fnc_"):]
            if name.startswith(("init", "register")) or (current.stem == "fn_debugMenu" and name.startswith("debugMenu")):
                names.append(name)
        for name in names:
            child = current.parent / ("fn_" + name + ".sqf")
            if not child.is_file():
                raise FileNotFoundError(f"Historical contract called module missing: {child}")
            parts.extend(["\n// Historical contract: called module " + name + "\n", expand(child, visited)])
        return "".join(parts)
    if path.name in {"fn_postInit.sqf", "fn_debugMenu.sqf"}:
        return expand(path, set())
    return path.read_text(encoding=encoding, errors=errors)


def assignment_expression(text, name):
    """Extract one actual private assignment, including multiline/nested expressions.

    Comments and quoted examples cannot become candidates. Missing, duplicated or
    unterminated assignments fail closed instead of silently selecting old text.
    """
    from source_scan import matching
    tokens = lex(text)
    pairs = matching(tokens)
    candidates = []
    for i in range(len(tokens) - 3):
        if not (tokens[i].kind == 'ident' and tokens[i].value == 'private'
                and tokens[i+1].kind == 'ident' and tokens[i+1].value == name
                and tokens[i+2].value == '='):
            continue
        j = i + 3
        while j < len(tokens):
            t = tokens[j]
            if t.kind == 'symbol' and t.value in ('[', '(', '{'):
                if j not in pairs:
                    raise AssertionError(f'Unbalanced assignment: {name}')
                j = pairs[j] + 1
                continue
            if t.kind == 'symbol' and t.value == ';':
                candidates.append(text[tokens[i+3].offset:t.offset].strip())
                break
            j += 1
        else:
            raise AssertionError(f'Unterminated assignment: {name}')
    if len(candidates) != 1:
        raise AssertionError(f'Expected one private assignment for {name}; found {len(candidates)}')
    return candidates[0]


def array_command_arguments(text, command):
    """Return the arguments of one literal-array command, never a quoted example."""
    from source_scan import matching
    tokens = lex(text)
    pairs = matching(tokens)
    candidates = []
    for i, token in enumerate(tokens[:-1]):
        if token.kind != 'ident' or token.value != command or tokens[i+1].value != '[':
            continue
        begin = i + 1
        if begin not in pairs:
            raise AssertionError(f'Unbalanced array for {command}')
        end = pairs[begin]
        mark = tokens[begin].offset + 1
        args = []
        j = begin + 1
        while j < end:
            t = tokens[j]
            if t.kind == 'symbol' and t.value in ('[', '(', '{'):
                if j not in pairs:
                    raise AssertionError(f'Unbalanced argument for {command}')
                j = pairs[j] + 1
                continue
            if t.kind == 'symbol' and t.value == ',':
                args.append(text[mark:t.offset].strip())
                mark = t.offset + 1
            j += 1
        args.append(text[mark:tokens[end].offset].strip())
        candidates.append(args)
    if len(candidates) != 1:
        raise AssertionError(f'Expected one {command} command; found {len(candidates)}')
    return candidates[0]


def class_body(text, name):
    """One defined config class (forward declarations do not count)."""
    from source_scan import matching
    tokens = lex(text)
    pairs = matching(tokens)
    bodies = []
    for i in range(len(tokens)-2):
        if tokens[i].kind != 'ident' or tokens[i].value != 'class' or tokens[i+1].value != name:
            continue
        j=i+2
        while j<len(tokens) and tokens[j].value not in ('{',';'):
            j+=1
        if j<len(tokens) and tokens[j].value=='{':
            if j not in pairs:
                raise AssertionError(f'Unclosed config class {name}')
            bodies.append(text[tokens[j].offset+1:tokens[pairs[j]].offset])
    if len(bodies)!=1:
        raise AssertionError(f'Expected one defined class {name}; found {len(bodies)}')
    return bodies[0]


def assert_release_consistent(root=ROOT):
    """Check header, public version, runtime source and fallback agree, not an old batch ID."""
    import re
    root = Path(root)
    header=(root/'addons/main/script_version.hpp').read_text(encoding='utf-8-sig')
    values=[]
    for key in ('MAJOR','MINOR','PATCH','BUILD'):
        matches=re.findall(r'^\s*#define\s+'+key+r'\s+(\d+)\s*$',header,re.M)
        assert len(matches)==1, f'Expected one numeric {key} definition'
        values.append(matches[0])
    expected='.'.join(values)
    cfg=(root/'addons/acm_extended/config.cpp').read_text(encoding='utf-8-sig')
    patches=class_body(cfg,'CfgPatches')
    own=class_body(patches,'ACM_Extended')
    public=re.findall(r'\bversion\s*=\s*"([^"]+)"\s*;',own)
    assert public==[expected], (public,expected)
    startup=(root/'addons/acm_extended/functions/fn_initForkStartupRuntime.sqf').read_text(encoding='utf-8-sig')
    assert re.search(r'ACME_infusion_version\s*=\s*getText\s*\(configFile\s*>>\s*"CfgPatches"\s*>>\s*"ACM_Extended"\s*>>\s*"version"\)',startup)
    fallback=re.findall(r'ACME_infusion_version\s*=\s*"([^"]+)"',startup)
    assert fallback==[expected], (fallback,expected)
    dispatcher=(root/'addons/acm_extended/functions/fn_postInit.sqf').read_text(encoding='utf-8-sig')
    tokens=lex(dispatcher)
    assert any(a.kind==b.kind=='ident' and a.value=='call' and b.value=='ACME_fnc_initForkStartupRuntime' for a,b in zip(tokens,tokens[1:])), 'Runtime version initializer is not called'
    return expected
