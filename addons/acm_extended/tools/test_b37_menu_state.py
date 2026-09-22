"""B37 dropdown/presentation policy tests and SQF source contracts, not Arma execution."""
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
import unittest

from source_scan import lex, matching
from historical_source import read_source

ROOT = Path(__file__).resolve().parents[1]
RENDER = read_source(ROOT / 'overrides/fn_updateActions.sqf')
STATE = (ROOT / 'functions/fn_menuDropdownState.sqf').read_text()
WHITE = (1, 1, 1, 1)
PALE_RED = (1, .94, .94, 1)
CREAM = (1, .96, .84, 1)


class StatePolicy:
    """Independent reference of requested user decisions across display lifetimes."""
    def __init__(self):
        self.patients = OrderedDict()

    def read(self, patient, deleted=()):
        for key in deleted:
            self.patients.pop(key, None)
        opened = self.patients.pop(patient, [])
        self.patients[patient] = opened
        while len(self.patients) > 32:
            self.patients.popitem(last=False)
        return list(opened)

    def toggle(self, patient, group):
        opened = self.read(patient)
        if group in opened:
            opened.remove(group)
        else:
            opened.append(group)
        self.patients[patient] = opened[-256:]
        return list(self.patients[patient])


@dataclass
class Row:
    name: str
    group: str = ''
    category: str = 'examine'
    available: bool = True
    action_class: str = ''
    callback: object = None
    stock: int = 2
    color: tuple = ()


def render(rows, groups, opened=(), nested=True, distinct=False):
    """Outputs visible row kind/name/color/row, with no actions performed."""
    rows = [r for r in rows if r.category == 'examine' and r.available]
    tags = [r for r in rows if r.action_class.lower() == 'checkdogtags']
    rows = [r for r in rows if r not in tags]
    result = []
    if nested:
        result.extend(('action', r.name, (), r) for r in rows if r.group not in groups)
        for key, color in groups.items():
            children = [r for r in rows if r.group == key]
            if children:
                result.append(('header', key, color if distinct and color else CREAM, None))
                if key in opened:
                    result.extend(('action', r.name, r.color, r) for r in children)
    else:
        result.extend(('action', r.name, r.color, r) for r in rows)
    result.extend(('action', r.name, r.color, r) for r in tags)
    painted, action_index = [], 0
    for kind, name, color, row in result:
        painted.append((kind, name, color or (WHITE if action_index % 2 == 0 else PALE_RED), row))
        if kind == 'action':
            action_index += 1
    return painted


class DropdownLifecycle(unittest.TestCase):
    def setUp(self):
        self.state = StatePolicy()

    def test_treatment_close_and_fresh_display_restore_all_open_sections(self):
        for group in ['iv_access', 'narc_box', 'examine_chest', 'ventilation']:
            self.state.toggle('patient', group)
        before = self.state.read('patient')
        for _ in range(30):
            self.assertEqual(self.state.read('patient'), before)

    def test_explicit_close_is_also_restored(self):
        self.state.toggle('patient', 'chest')
        self.state.toggle('patient', 'iv_access')
        self.state.toggle('patient', 'chest')
        self.assertEqual(self.state.read('patient'), ['iv_access'])

    def test_another_patient_does_not_inherit_or_erase_previous_decisions(self):
        self.state.toggle('a', 'iv_access')
        self.assertEqual(self.state.read('b'), [])
        self.state.toggle('b', 'examine_response')
        self.assertEqual(self.state.read('a'), ['iv_access'])
        self.assertEqual(self.state.read('b'), ['examine_response'])

    def test_tab_body_triage_and_grouping_setting_are_not_state_keys(self):
        self.state.toggle('patient', 'chest')
        for nested in [True, False, True]:
            for body in ['head', 'chest', 'leftarm', 'rightarm', 'legs']:
                for category in ['examine', 'airway', 'medication', 'triage']:
                    with self.subTest(nested=nested, body=body, category=category):
                        self.assertEqual(self.state.read('patient'), ['chest'])

    def test_hidden_then_reeligible_group_reappears_open(self):
        self.state.toggle('patient', 'chest')
        rows = [Row('Inspect Chest', 'chest')]
        rows[0].available = False
        self.assertEqual(render(rows, {'chest': ()}, self.state.read('patient')), [])
        rows[0].available = True
        shown = render(rows, {'chest': ()}, self.state.read('patient'))
        self.assertEqual([r[1] for r in shown], ['chest', 'Inspect Chest'])

    def test_read_returns_copy_not_live_mutable_state(self):
        self.state.toggle('patient', 'chest')
        self.state.read('patient').clear()
        self.assertEqual(self.state.read('patient'), ['chest'])

    def test_repeated_views_keep_cache_bounded_and_refresh_recent_patient(self):
        for i in range(32):
            self.state.toggle(i, 'chest')
        self.state.read(0)
        self.state.toggle(32, 'iv')
        self.assertEqual(len(self.state.patients), 32)
        self.assertIn(0, self.state.patients)
        self.assertNotIn(1, self.state.patients)

    def test_deleted_patient_pruned_but_death_alone_keeps_ui_state(self):
        self.state.toggle('corpse', 'chest')
        self.state.toggle('deleted', 'chest')
        self.assertEqual(self.state.read('corpse', deleted=['deleted']), ['chest'])
        self.assertNotIn('deleted', self.state.patients)


class VisiblePresentation(unittest.TestCase):
    def test_headers_are_cream_open_and_closed_and_do_not_count_as_actions(self):
        rows = [Row('Response', 'response'), Row('Pulse', 'vitals'), Row('Pressure', 'vitals')]
        for opened in [[], ['response'], ['response', 'vitals']]:
            painted = render(rows, {'response': (), 'vitals': ()}, opened)
            self.assertTrue(all(r[2] == CREAM for r in painted if r[0] == 'header'))
            colors = [r[2] for r in painted if r[0] == 'action']
            self.assertEqual(colors, [WHITE if i % 2 == 0 else PALE_RED for i in range(len(colors))])

    def test_hidden_rows_do_not_advance_stripes(self):
        rows = [Row('Absent', available=False), Row('First'), Row('Hidden', available=False), Row('Second')]
        shown = render(rows, {}, nested=False)
        self.assertEqual([(r[1], r[2]) for r in shown], [('First', WHITE), ('Second', PALE_RED)])

    def test_stripes_continue_between_open_sections_and_flat_mode(self):
        rows = [Row('One', 'a'), Row('Two', 'a'), Row('Three', 'b'), Row('Four', 'b')]
        for nested in [False, True]:
            painted = render(rows, {'a': (), 'b': ()}, ['a', 'b'], nested=nested)
            self.assertEqual([r[2] for r in painted if r[0] == 'action'], [WHITE, PALE_RED, WHITE, PALE_RED])

    def test_existing_distinct_palette_preference_is_preserved_without_dimming(self):
        palette = (.6, 1, .7, 1)
        rows = [Row('Response', 'response')]
        for opened in [[], ['response']]:
            self.assertEqual(render(rows, {'response': palette}, opened, distinct=True)[0][2], palette)
            self.assertEqual(render(rows, {'response': palette}, opened)[0][2], CREAM)

    def test_dog_tags_never_captured_by_group_and_always_follow_foreign_actions(self):
        callback = object()
        tag = Row('Localized tag label', 'response', action_class='CheckDogTags', callback=callback, stock=3)
        rows = [tag, Row('Foreign'), Row('Response', 'response'), Row('Other addon')]
        for nested in [False, True]:
            for opened in [[], ['response']]:
                painted = render(rows, {'response': ()}, opened, nested)
                self.assertEqual(painted[-1][:2], ('action', 'Localized tag label'))
                self.assertIs(painted[-1][3].callback, callback)
                self.assertEqual(painted[-1][3].stock, 3)
                self.assertEqual(sum(r[1] == tag.name for r in painted), 1)

    def test_dog_tags_still_respect_body_and_inventory_eligibility(self):
        rows = [Row('Check Dog Tags', available=False, action_class='CheckDogTags'), Row('Pulse')]
        self.assertEqual([r[1] for r in render(rows, {})], ['Pulse'])

    def test_explicit_nonwhite_action_colors_remain_intact(self):
        semantic = (1, .6, .2, 1)
        rows = [Row('First'), Row('Special', color=semantic), Row('Third')]
        self.assertEqual([r[2] for r in render(rows, {}, nested=False)], [WHITE, semantic, WHITE])


class RuntimeSourceContracts(unittest.TestCase):
    def test_structural_balance(self):
        for source in [RENDER, STATE]:
            matching(lex(source))

    def test_display_recreation_restores_cache_and_no_automatic_clear_remains(self):
        self.assertIn("['read', _target] call ACME_fnc_menuDropdownState", RENDER)
        self.assertIn("['toggle', _patient, _key] call ACME_fnc_menuDropdownState", RENDER)
        self.assertNotIn("setVariable ['ACME_menuOpen', []]", RENDER)
        self.assertNotIn('_open = _open select', RENDER)

    def test_patient_cache_is_local_and_bounded_without_alive_gate(self):
        self.assertIn("uiNamespace setVariable ['ACME_menuDropdownCache'", STATE)
        self.assertIn('count _cache > 32', STATE)
        self.assertIn('count _open > 256', STATE)
        self.assertNotIn('alive ', STATE)
        self.assertNotIn('_patient setVariable', STATE)
        for forbidden in ['remoteExec', 'publicVariable', 'CBA_fnc_targetEvent', 'profileNamespace']:
            self.assertNotIn(forbidden, STATE)

    def test_old_patient_headers_cannot_toggle_new_patient(self):
        self.assertIn("['ACME_menuRowTarget', objNull]) isNotEqualTo _patient) exitWith", RENDER)
        self.assertIn("['ACME_menuTarget', objNull]) isNotEqualTo _patient) exitWith", RENDER)

    def test_tag_extraction_precedes_name_fallback_grouping_and_appends_last(self):
        self.assertLess(RENDER.index('private _dogTags ='), RENDER.index('private _nameKeys ='))
        self.assertIn('_pressure + _menuActions + _dogTags', RENDER)
        self.assertIn("_class == 'checkdogtags'", RENDER)

    def test_action_class_reaches_posture_relabeler(self):
        self.assertIn("private _actionClass = toLower (_x param [8, ''])", RENDER)
        self.assertIn("[_paintName, _bodyPart, true, _actionClass] call ACME_fnc_ivSiteRelabel", RENDER)

    def test_color_stripes_do_not_count_headers_and_still_use_accessibility(self):
        self.assertIn("if (_groupKey == '') then {_actionIndex = _actionIndex + 1;};", RENDER)
        self.assertIn("[_textColor, 'protect'] call ACME_fnc_cbColor", RENDER)
        self.assertNotIn('ACME_menuOpenDimFactor', RENDER)

    def test_callbacks_item_counts_and_pending_reopen_are_retained(self):
        self.assertIn('call ace_medical_gui_fnc_countTreatmentItems', RENDER)
        self.assertIn("ctrlAddEventHandler ['ButtonClick', _statement]", RENDER)
        self.assertIn("if (_groupKey isEqualTo '') then", RENDER)
        self.assertIn('ace_medical_gui_pendingReopen = true', RENDER)


if __name__ == '__main__':
    unittest.main()
