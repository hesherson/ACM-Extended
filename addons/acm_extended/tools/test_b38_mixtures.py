"""B38 mixture regression models and source contracts, without an Arma/SQF runtime.

Uses the native and Extended configuration shipped in this repository.
The inventory is generated in memory; no audit fixture or source file is written. Pair coverage checks freedom and mass, not clinical safety.
"""
from pathlib import Path
from historical_source import read_source
import itertools
import json
import math
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
# This repository ships native ACM alongside Extended. Build the inventory in
# memory from those exact sources; do not depend on a generated audit artifact.
# The existing reader preserves unexpanded macros as strings, not clinical values.
from medication_inventory import inventory
NATIVE = ROOT.parent / 'core/ACM_Medication.hpp'
MATRIX = inventory(NATIVE, ROOT / 'config.cpp')
MEDS = {row['classname']: row for row in MATRIX['medication_classes']}
SOURCES = {row['source']: row for row in MATRIX['concentrations']}
INJECTABLE = {'ACM_ROUTE_IM', 'ACM_ROUTE_IV', 0, 1}
STOCK = {
    name: row for name, row in SOURCES.items()
    if row['concentration'] > 0 and row['volume'] > 0
    and any(MEDS.get(c, {}).get('administrationType') in INJECTABLE for c in (name, name + '_IV'))
}

def src(name):
    return (ROOT / 'functions' / ('fn_' + name + '.sqf')).read_text()

def prepared_class(source, iv):
    wanted = source + '_IV' if iv or source in ('Adenosine', 'Amiodarone', 'Rocuronium') else source
    if wanted not in MEDS:
        wanted = source if source in MEDS else source + '_IV'
    return wanted

def prepare(parts, capacity, stock):
    """Independent acceptance/volume oracle; chemical names impose no pair rules."""
    if capacity not in (1, 3, 5, 10) or not parts:
        return None
    needs = {}
    for name, amount in parts:
        if name not in STOCK or not isinstance(amount, (float, int)) or not math.isfinite(amount) or amount <= 0:
            return None
        needs[name] = needs.get(name, 0) + amount
    if sum(needs.values()) > capacity + .001 or any(stock.get(k, 0) + 1e-6 < v for k, v in needs.items()):
        return None
    return {k: stock.get(k, 0) - v for k, v in needs.items()}, [(k, v * STOCK[k]['concentration']) for k, v in parts]

class B38Mixtures(unittest.TestCase):
    def test_actual_injectable_catalog(self):
        self.assertEqual(len(STOCK), 24)
        self.assertNotIn('Naloxone', STOCK)
        self.assertNotIn('HTS3', STOCK)
        for name in ('Dimercaprol', 'Phentolamine', 'Hyaluronidase', 'Epinephrine', 'EpinephrineCardiac'):
            self.assertIn(name, STOCK)

    def test_all_276_source_pairs_in_both_orders_and_arbitrary_ratios(self):
        for a, b in itertools.combinations(STOCK, 2):
            for x, y in ((.07, .83), (.83, .07), (.17, .23), (.31, .59)):
                for parts in ([(a, x), (b, y)], [(b, y), (a, x)]):
                    with self.subTest(parts=parts):
                        result = prepare(parts, 1, {a: 1, b: 1})
                        self.assertIsNotNone(result)
                        left, doses = result
                        self.assertEqual(len(doses), 2)
                        self.assertAlmostEqual(sum(left.values()) + x + y, 2)
                        for (source, ml), (med, dose) in zip(parts, doses):
                            self.assertEqual(source, med)
                            self.assertAlmostEqual(dose, STOCK[source]['concentration'] * ml)

    def test_all_24_sources_in_one_syringe_without_component_loss(self):
        parts = [(n, .1) for n in STOCK]
        result = prepare(parts, 3, {n: .3 for n in STOCK})
        self.assertIsNotNone(result)
        self.assertEqual(len(result[1]), 24)
        self.assertAlmostEqual(sum(ml for _, ml in parts), 2.4)

    def test_same_drug_multiple_draws_reserve_combined_volume(self):
        parts = [('Ketamine', .7), ('Propofol', .2), ('Ketamine', .6)]
        self.assertIsNone(prepare(parts, 3, {'Ketamine': 1, 'Propofol': 1}))
        left, doses = prepare(parts, 3, {'Ketamine': 1.5, 'Propofol': 1})
        self.assertAlmostEqual(left['Ketamine'], .2)
        self.assertAlmostEqual(sum(d for n, d in doses if n == 'Ketamine'), 65)

    def test_epinephrine_strengths_never_reinterpret_each_other(self):
        _, doses = prepare([('Epinephrine', .1), ('EpinephrineCardiac', .1)], 1,
                           {'Epinephrine': 1, 'EpinephrineCardiac': 1})
        self.assertAlmostEqual(doses[0][1], .1)
        self.assertAlmostEqual(doses[1][1], .01)
        self.assertAlmostEqual(doses[0][1] / doses[1][1], 10)

    def test_capacity_and_invalid_volumes_still_rejected(self):
        for amount in (0, -1, float('inf'), float('nan'), 1.1):
            self.assertIsNone(prepare([('Ketamine', amount)], 1, {'Ketamine': 10}))
        self.assertIsNone(prepare([('Ketamine', 1)], 2, {'Ketamine': 10}))

    def test_last_component_shortage_preserves_all_sources(self):
        parts = [(n, .1) for n in STOCK]
        stock = {n: .2 for n in STOCK}
        stock[parts[-1][0]] = 0
        before = dict(stock)
        self.assertIsNone(prepare(parts, 3, stock))
        self.assertEqual(stock, before)

    def test_all_sources_have_real_definitions_for_both_prepared_routes(self):
        for source in STOCK:
            for iv in (False, True):
                with self.subTest(source=source, iv=iv):
                    cls = prepared_class(source, iv)
                    self.assertIn(cls, (source, source + '_IV'))
                    self.assertIn(MEDS[cls]['administrationType'], INJECTABLE)

    def test_unfinished_native_im_stubs_never_supply_reference_dose(self):
        for name in ('Adenosine', 'Amiodarone', 'Rocuronium'):
            self.assertEqual(prepared_class(name, False), name + '_IV')
            self.assertGreater(MEDS[name + '_IV']['maxEffectDose'], 1)
        self.assertIn('_source in ["Adenosine", "Amiodarone", "Rocuronium"]', src('skInjectSite'))

    def test_whitelist_and_epinephrine_draw_intercept_removed(self):
        for name in ('skCompoundCommit', 'skCompoundDraw', 'skWasteDraw', 'skInjectSite'):
            text = src(name)
            self.assertNotIn('verified compatibility list', text)
            self.assertNotIn('Keep cardiac epinephrine in its own syringe', text)
            self.assertNotIn('Required recipe:', text)
        self.assertNotIn('_compatible', src('skCompoundCommit'))
        self.assertNotIn('epinephrineDrawCardiac', src('skCompoundDraw'))
        self.assertNotIn('count _components > 1', src('skInjectSite'))

    def test_named_recipe_labels_do_not_gate_commit(self):
        self.assertIn('epinephrineRecipe', src('skCompoundLabel'))
        self.assertNotIn('epinephrineRecipe', src('skCompoundCommit'))
        self.assertNotIn('_unique', src('skCompoundCommit'))
        waste = src('skWasteDraw')
        self.assertIn('&& {[_med, _cap, _drugMl, _nsMl] call ACME_fnc_epinephrineRecipe}', waste)
        self.assertIn('"dilutionB13"', waste)

    def test_preparation_validates_before_atomic_source_debit(self):
        commit = src('skCompoundCommit')
        self.assertLess(commit.index('_totalDrugMl > _cap'), commit.index('call ACME_fnc_medicationTakeSources'))
        self.assertLess(commit.index('call ACME_fnc_medicationTakeSources'), commit.index('_store pushBack'))
        debit = src('medicationTakeSources')
        self.assertLess(debit.index('isNil {'), debit.index('ACME_fnc_infusionVialVolume'))
        self.assertLess(debit.index('ACME_fnc_infusionVialVolume'), debit.index('ACME_fnc_vialTake'))
        self.assertIn('ACME_fnc_vialRefund', debit)
        self.assertLess(debit.index('ACME_fnc_vialRefund'), debit.index('_medic removeItem _container'))

    def test_virtual_marker_includes_single_component_preparations(self):
        inject = src('skInjectSite')
        self.assertIn('in ["compoundB13", "dilutionB13"]', inject)
        self.assertIn('_x pushBack _virtual', inject)
        self.assertNotIn('count _components > 1', inject)
        self.assertIn('abs (_componentMl - _amt) > 0.001', inject)
        self.assertLess(inject.index('forEach _sourceParts'), inject.index('_store deleteAt'))

    def test_actual_route_is_kept_through_owner_and_flush(self):
        for name in ('medicationRequest', 'medicationLineLocal'):
            self.assertIn('[_x select 0,_x select 2,true,_x param [5,false]]', src(name))
        owner = src('medicationLineLocal')
        self.assertIn('_label,_site,_identity,_seconds,_preparedMixture', owner)
        self.assertIn('_x param [8,false]', owner)
        self.assertIn('[_site,_identity,_seconds,"bolus",_preparedMixture]', owner)
        self.assertLess(owner.index('setVariable ["ACME_pendingFlush"'), owner.index('call ace_medical_treatment_fnc_medicationLocal'))

    def test_native_gate_unchanged_but_prepared_uses_actual_route(self):
        route = src('medicationRouteAllowed')
        self.assertIn('["_preparedMixture", false]', route)
        self.assertLess(route.index('if (_preparedMixture isEqualTo true)'), route.index('"Phentolamine_IV"'))
        med = read_source(ROOT / 'overrides/fn_medicationLocal.sqf')
        self.assertIn('&& {!_iv} && {!_preparedMixture}) exitWith', med)
        self.assertIn('_administrationType = if (_iv) then {ACM_ROUTE_IV} else {ACM_ROUTE_IM}', med)
        self.assertIn('_occludedMedications pushBack [_partIndex, _classname, _dose, _iv, _delivery]', med)
        tq = read_source(ROOT / 'overrides/fn_tourniquetRemove.sqf')
        self.assertIn('_dose,_iv,false,_delivery', tq)

    def test_flush_state_roundtrip_accepts_old_and_new_rows(self):
        old = ['leftarm', 'Epinephrine_IV', .1, True, 'mixed', 0, [0, 3, 20], 5]
        new = old + [True]
        for row in (old, new):
            self.assertEqual(json.loads(json.dumps(row)), row)
        self.assertIn('["ACME_pendingFlush", "", true, true]', src('clinicalFields'))
        validate = src('clinicalValidate')
        self.assertIn('case "ACME_pendingFlush"', validate)
        self.assertIn('count _x in [8, 9]', validate)
        self.assertIn('_row param [8,false]', validate)
        self.assertIn('ACME_fnc_medicationRouteAllowed', validate)

    def test_refund_retry_preserve_complete_payload(self):
        self.assertIn('_doses,_site,_identity', src('medicationRequest'))
        self.assertIn('_refund', src('medicationRequest'))
        self.assertIn('_store pushBack (+_x)', src('medicationRefund'))
        self.assertIn('[_row select 0,"medicationLine",_row select 1]', src('medicationRetry'))
        self.assertIn('_receipts getOrDefault [_id', src('medicationLineLocal'))

if __name__ == '__main__':
    unittest.main()
