"""Examination source-data/presentation reference tests; no Arma config/SQF runtime."""
from historical_source import read_source
from pathlib import Path
import random
import unittest

from na8_menu_reference import EXAMINE_GROUPS, policy
from source_scan import lex, matching

ROOT = Path(__file__).resolve().parents[1]


def action_fields(name):
    tokens = lex(read_source(ROOT / 'config.cpp'))
    pairs = matching(tokens)
    for i, token in enumerate(tokens[:-2]):
        if token.value == 'class' and tokens[i + 1].value == name and tokens[i + 2].value == ':':
            start = next(j for j in range(i + 3, len(tokens)) if tokens[j].value == '{')
            end = pairs[start]
            return {tokens[j].value: tokens[j + 2].value for j in range(start + 1, end - 2)
                    if tokens[j + 1].value == '=' and tokens[j + 2].kind == 'string'}
    raise AssertionError(name)


def order(rows):
    known = [row for _, _, names, _ in EXAMINE_GROUPS for name in names for row in rows if row['class'] == name]
    return known + [row for row in rows if not policy(row['class'], 'examine', [row['class']])[1]]


def render(rows, grouped, opened=()):
    rows = order(rows)
    if not grouped:
        return [row['class'] for row in rows if row['available']]
    out = [row['class'] for row in rows if row['available'] and not policy(row['class'], 'examine', [row['class']])[1]]
    for key, label, names, _ in EXAMINE_GROUPS:
        live = [row['class'] for row in rows if row['available'] and row['class'] in names]
        if live:
            out.append(label)
            if key in opened:
                out.extend(live)
    return out


class ExaminePresentation(unittest.TestCase):
    def test_table_cannot_duplicate_or_swallow_known_actions(self):
        names = [name for _, _, group, _ in EXAMINE_GROUPS for name in group]
        self.assertEqual(len(names), len(set(names)))
        for key, _, group, _ in EXAMINE_GROUPS:
            for name in group:
                self.assertEqual(policy(name, 'examine', [name]), ('examine', key, False))

    def test_known_order_survives_native_config_declaration_order(self):
        names = ['usestethoscope', 'acme_checktemperature', 'checkresponse', 'acme_assesspupils', 'acme_inspectchest', 'checkpulse']
        expected = ['checkresponse', 'acme_assesspupils', 'checkpulse', 'acme_inspectchest', 'usestethoscope', 'acme_checktemperature']
        rng = random.Random(33)
        for _ in range(20):
            rng.shuffle(names)
            rows = [dict(**{'class': name}, available=True) for name in names]
            self.assertEqual(render(rows, False), expected)

    def test_callbacks_and_foreign_examinations_are_retained(self):
        callback = object()
        rows = [dict(**{'class': n}, available=True, callback=callback) for n in ['anotheraddon_exam', 'acme_inspectchest', 'anotheraddon_second']]
        result = order(rows)
        self.assertEqual([r['class'] for r in result], ['acme_inspectchest', 'anotheraddon_exam', 'anotheraddon_second'])
        self.assertTrue(all(r['callback'] is callback for r in result))

    def test_grouped_and_flat_keep_body_site_eligibility(self):
        rows = [dict(**{'class': n}, available=a) for n, a in [('checkresponse', False), ('acme_inspectchest', True), ('usestethoscope', False)]]
        self.assertEqual(render(rows, False), ['acme_inspectchest'])
        self.assertEqual(render(rows, True), ['Chest Inspection'])
        self.assertEqual(render(rows, True, ['examine_chest']), ['Chest Inspection', 'acme_inspectchest'])
        rows[1]['available'] = False
        self.assertEqual(render(rows, True, ['examine_chest']), [])

    def test_chest_move_does_not_capture_bvm_descendants(self):
        self.assertEqual(policy('UseBVM', 'airway', ['usebvm', 'usestethoscope', 'checkbreathing', 'checkpulse']), ('airway', '', False))
        self.assertEqual(policy('SlapAwake', 'advanced', ['slapawake', 'shakeawake', 'checkresponse']), ('examine', 'examine_response', False))

    def test_runtime_shares_one_membership_and_order_table(self):
        collector = read_source(ROOT / 'overrides/fn_collectActions.sqf')
        mapper = read_source(ROOT / 'functions/fn_menuActionInfo.sqf')
        postinit = read_source(ROOT / 'functions/fn_postInit.sqf')
        self.assertIn('ACME_fnc_menuExamineGroups', collector)
        self.assertIn('ACME_fnc_menuExamineGroups', mapper)
        self.assertIn('ACME_fnc_menuExamineGroups', postinit)
        self.assertNotIn('call _condition', collector)
        self.assertNotIn('displayName', mapper)


class CorpseChestAssessment(unittest.TestCase):
    def test_configuration_allows_living_and_dead_human_patients(self):
        fields = action_fields('ACME_InspectChest')
        self.assertEqual(fields['condition'], "!isNull _patient && {_patient isKindOf 'CAManBase'}")
        self.assertIn('ACM_breathing_fnc_inspectChest', fields['callbackSuccess'])

    def test_requested_pose_lifecycle_is_preserved(self):
        fields = action_fields('ACME_InspectChest')
        self.assertIn('ACME_fnc_inspectChestPoseStart', fields['callbackStart'])
        self.assertIn('ACME_fnc_inspectChestPoseStop', fields['callbackSuccess'])
        self.assertIn('ACME_fnc_inspectChestPoseStop', fields['callbackFailure'])
        self.assertEqual(fields['animationMedic'], '')

    def test_dead_findings_survive_without_a_live_obtunded_roll(self):
        source = read_source(ROOT / 'overrides/fn_inspectChestLocal.sqf')
        self.assertIn('if (isNull _patient) exitWith {};', source)
        self.assertIn('if (alive _patient\n', source)
        self.assertIn('!(alive _patient)', source)
        self.assertIn('STR_ACM_Breathing_InspectChest_None', source)
        self.assertNotIn('if (!alive _patient) exitWith', source)


if __name__ == '__main__':
    unittest.main()
