"""Fracture presentation source checks and Python reference examples; does not execute SQF."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CALLBACK = (ROOT / 'functions/fn_inspectForFracture.sqf').read_text()
RESOLVER = (ROOT / 'functions/fn_clinTerm.sqf').read_text()
CONFIG = (ROOT / 'config.cpp').read_text()
TERMS = dict(re.findall(r'\["(str_[^"]+)",\s*"([^"]*)"\]', RESOLVER))
BASE = 'str_acm_disability_inspectforfracture_'
CUSTOM = 'str_acme_disability_inspectforfracture_'
PARTS = ['head', 'body', 'leftarm', 'rightarm', 'leftleg', 'rightleg']
DISPLAY = ['head', 'torso', 'left arm', 'right arm', 'left leg', 'right leg']


def reference(state=0, damage=0, splint=0, ace=0, prepared=False, part='leftarm', hardcore=True):
    """Independent reference for the explicit presentation policy, not a medical/SQF engine."""
    try:
        index = PARTS.index(part.lower())
    except (ValueError, AttributeError):
        return None
    if index not in (2, 3, 4, 5):
        return None
    if not hardcore:
        return 'delegate-to-ACM'
    if splint > 0:
        key = BASE + 'splintapplied'
    elif ace == -1:
        key = CUSTOM + 'stabilized'
    elif state == 3:
        key = BASE + 'significantswelling'
    elif state == 2:
        key = BASE + 'swelling'
    elif state == 1:
        key = BASE + 'severebruising'
    elif ace > 0:
        key = CUSTOM + 'confirmed'
    elif state not in (0, 1, 2, 3):
        key = CUSTOM + 'indeterminate'
    elif damage > 1:
        key = BASE + 'bruised'
    else:
        key = BASE + 'noinjury'
    hint = TERMS[key].replace('%1', DISPLAY[index])
    log = TERMS[key + '_short']
    if prepared:
        hint += '<br />' + TERMS[BASE + 'realignmentperformed']
        log += ', ' + TERMS[BASE + 'realignmentperformed_short']
    return hint, log


class FracturePresentationExamples(unittest.TestCase):
    def test_off_uses_native_for_every_state(self):
        for state in range(4):
            self.assertEqual(reference(state, 10, hardcore=False), 'delegate-to-ACM')

    def test_plain_bruise(self):
        hint, log = reference(damage=1.1)
        self.assertEqual(hint, "Patient's left arm is visibly contused; no crepitus found.")
        self.assertEqual(log, 'Visible contusion; no crepitus found')

    def test_native_bruise_threshold_not_inclusive(self):
        self.assertIn('no visible contusion', reference(damage=1)[0])

    def test_just_over_bruise_threshold(self):
        self.assertIn('visibly contused', reference(damage=1.00001)[0])

    def test_mild_fracture(self):
        hint, log = reference(state=1, ace=1)
        self.assertIn('severely contused; crepitus present', hint)
        self.assertIn('crepitus present', log)

    def test_severe_fracture(self):
        hint, log = reference(state=2, ace=1)
        self.assertIn('severely contused and swollen; crepitus present', hint)
        self.assertIn('crepitus present', log)

    def test_complex_fracture(self):
        hint, _ = reference(state=3, ace=1)
        self.assertIn('marked swelling and deformity; crepitus present', hint)

    def test_low_body_damage_does_not_hide_fracture(self):
        self.assertIn('crepitus present', reference(state=2, damage=0)[0])

    def test_damage_does_not_invent_complex_fracture(self):
        hint, _ = reference(damage=100)
        self.assertIn('visibly contused', hint)
        self.assertNotIn('deformity', hint)
        self.assertNotIn('crepitus present', hint)

    def test_splint_masks_hidden_severity(self):
        for state in range(4):
            hint, log = reference(state=state, splint=1)
            self.assertIn('crepitus was not assessed through the splint', hint)
            self.assertNotIn('crepitus present', log)
            self.assertNotIn('contusion', log)

    def test_wrapped_splint_also_masks(self):
        self.assertIn('is splinted', reference(state=3, splint=2)[0])

    def test_ace_minus_one_is_stabilized(self):
        hint, log = reference(state=3, ace=-1)
        self.assertIn('has been stabilized', hint)
        self.assertNotIn('crepitus present', log)
        self.assertNotIn('healed', hint)

    def test_splint_takes_precedence_over_minus_one(self):
        self.assertIn('is splinted', reference(state=3, ace=-1, splint=1)[0])

    def test_realignment_retained(self):
        hint, log = reference(state=2, prepared=True)
        self.assertIn('realignment previously performed', hint)
        self.assertIn('realignment previously performed', log)
        self.assertNotIn('healed', hint)

    def test_splinted_realignment_retained(self):
        hint, _ = reference(state=2, splint=1, prepared=True)
        self.assertIn('is splinted', hint)
        self.assertIn('realignment previously performed', hint)

    def test_unprepared_does_not_report_realignment(self):
        self.assertNotIn('realignment', reference(state=2)[0])

    def test_each_limb_uses_selected_label(self):
        for part, label in zip(PARTS[2:], DISPLAY[2:]):
            self.assertIn(label, reference(state=2, part=part)[0])

    def test_mixed_case_native_body_parts(self):
        self.assertIn('right leg', reference(state=2, part='RightLeg')[0])

    def test_head_and_torso_not_limb_inspections(self):
        for part in ('head', 'body'):
            self.assertIsNone(reference(part=part))

    def test_invalid_selection_rejected(self):
        for part in ('', 'foot', None):
            self.assertIsNone(reference(part=part))

    def test_unknown_severity_no_fake_negative(self):
        hint, _ = reference(state=4, damage=0)
        self.assertIn('indeterminate', hint)
        self.assertNotIn('no crepitus found', hint)

    def test_native_fracture_without_acm_grade(self):
        self.assertIn('has crepitus on assessment', reference(state=0, ace=1)[0])

    def test_repeat_same_state_same_findings(self):
        self.assertEqual(reference(state=2), reference(state=2))

    def test_no_crepitus_never_claims_no_fracture(self):
        for state in (0, 1):
            hint, log = reference(state=state, damage=2)
            for text in (hint, log):
                self.assertNotIn('no fracture', text.lower())
                self.assertNotIn('fracture excluded', text.lower())


class FractureSourceContracts(unittest.TestCase):
    def test_registered_once_under_acme(self):
        from tagcheck import parse_config
        matches = [r for r in parse_config(ROOT/'config.cpp') if r['resolved'].lower() == 'acme_fnc_inspectforfracture']
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['file'], r'\acm_extended\functions\fn_inspectForFracture.sqf')

    def test_action_changes_only_callback_and_retains_parent(self):
        match = re.search(r'class InspectForFracture:\s*CheckPulse\s*\{([^}]+)\};', CONFIG)
        self.assertIsNotNone(match)
        self.assertEqual(match[1].strip(), 'callbackSuccess = "ACME_fnc_inspectForFracture";')

    def test_explicit_disability_dependency(self):
        dependencies = re.search(r'requiredAddons\[\]\s*=\s*\{([^}]+)', CONFIG)[1]
        self.assertIn('"ACM_disability"', dependencies)

    def test_native_function_not_reassigned(self):
        self.assertNotRegex(CALLBACK, r'ACM_disability_fnc_inspectForFracture\s*=')
        self.assertIn('_this call ACM_disability_fnc_inspectForFracture', CALLBACK)
        self.assertLess(CALLBACK.index('call ACM_disability_fnc_inspectForFracture'), CALLBACK.index('private _read'))

    def test_gate_independent_of_dropdowns(self):
        self.assertIn('missionNamespace getVariable ["ACME_hc_descriptors", false]', CALLBACK)
        self.assertIn('isEqualTo true', CALLBACK)
        self.assertNotIn('ACME_hcEff_descriptors', CALLBACK)
        self.assertNotIn('ACME_ui_menu', CALLBACK)
        self.assertNotIn('ACME_ui_nest', CALLBACK)
        self.assertNotIn('ACME_medicalMenu', CALLBACK)

    def test_no_global_patient_or_limb_lookup(self):
        self.assertNotIn('ace_medical_gui_target', CALLBACK)
        self.assertNotIn('ace_medical_gui_selectedBodyPart', CALLBACK)
        self.assertIn('_patient getVariable', CALLBACK)

    def test_uses_all_native_assessment_inputs(self):
        for name in ('ACM_disability_Fracture_State','ace_medical_bodyPartDamage','ACM_disability_SplintStatus','ace_medical_fractures','ACM_disability_Fracture_Prepared'):
            self.assertIn('"' + name + '"', CALLBACK)

    def test_no_clinical_writes_or_repeat_worker(self):
        for token in ('setVariable', 'addPerFrameHandler', 'waitAndExecute', 'random ', 'remoteExec', 'globalEvent', 'adjustPainLevel'):
            self.assertNotIn(token, CALLBACK)

    def test_one_hint_and_log(self):
        self.assertEqual(CALLBACK.count('call ace_common_fnc_displayTextStructured'), 1)
        self.assertEqual(CALLBACK.count('call ace_medical_treatment_fnc_addToLog'), 1)
        self.assertIn('"quick_view"', CALLBACK)
        self.assertIn('STR_ACM_Disability_InspectForFracture_ActionLog', CALLBACK)

    def test_all_result_keys_have_hint_and_log_entries(self):
        keys = re.findall(r'\{"(STR_[^"]+)"\}', CALLBACK)
        self.assertEqual(len(keys), 9)
        for key in keys:
            self.assertIn(key.lower(), TERMS)
            self.assertIn(key.lower() + '_short', TERMS)

    def test_exact_native_threshold_preserved(self):
        self.assertIn('case (_bodyPartDamage > 1)', CALLBACK)
        self.assertNotIn('case (_bodyPartDamage >= 1)', CALLBACK)

    def test_unknown_and_treated_precedence_in_source(self):
        self.assertLess(CALLBACK.index('case (_splint > 0)'), CALLBACK.index('case (_aceFracture == -1)'))
        self.assertLess(CALLBACK.index('case (_aceFracture == -1)'), CALLBACK.index('case (_fractureState == 3)'))
        self.assertLess(CALLBACK.index('case (!(_fractureState in'), CALLBACK.index('case (_bodyPartDamage > 1)'))

    def test_typed_reads_and_index_guard(self):
        self.assertIn('if !(_partIndex in [2, 3, 4, 5]) exitWith {};', CALLBACK)
        self.assertIn('_values param [_partIndex, _default, [_default]]', CALLBACK)
        self.assertIn('if !(_values isEqualType []) exitWith {_default}', CALLBACK)

    def test_hint_and_log_realignment_same_flag(self):
        after = CALLBACK[CALLBACK.index('if (_prepared) then'):]
        self.assertIn('_hint = format', after)
        self.assertIn('_hintLog = format', after)
        self.assertIn('_hintHeight = 3.5', after)

    def test_central_resolver_remains_gated(self):
        self.assertLess(RESOLVER.index('ACME_hc_descriptors'), RESOLVER.index('createHashMapFromArray'))
        self.assertEqual(RESOLVER.count('str_acm_disability_inspectforfracture_swelling"'), 1)


if __name__ == '__main__':
    unittest.main()
