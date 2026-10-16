"""B38 mixture models, source contracts, and acknowledged-refund SQF execution.

Uses the checked-out native and Extended configs, resolved by the existing source
inventory helper. Pair coverage checks freedom and mass, not clinical safety.
"""
from historical_source import read_source
from pathlib import Path
import itertools
import json
import math
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
# This source inventory is not engine preprocessing or clinical dosing validation.
from historical_source import medication_matrix
MATRIX = medication_matrix()

MEDS = {row['classname']: row for row in MATRIX['medication_classes']}
SOURCES = {row['source']: row for row in MATRIX['concentrations']}
INJECTABLE = {'ACM_ROUTE_IM', 'ACM_ROUTE_IV', 0, 1}
STOCK = {
    name: row for name, row in SOURCES.items()
    if row['concentration'] > 0 and row['volume'] > 0
    and any(MEDS.get(c, {}).get('administrationType') in INJECTABLE for c in (name, name + '_IV'))
}

def src(name):
    return read_source(ROOT / 'functions' / ('fn_' + name + '.sqf'))

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
        self.assertIn('epinephrineRecipe',src('skCompoundLabel'))
        self.assertNotIn('epinephrineRecipe',src('skCompoundCommit'))
        self.assertNotIn('_unique',src('skCompoundCommit'))
        # Draw now stages components; Save performs source-funded generic preparation or the exact recognized epi recipe.
        save=src('skFlushSave')
        self.assertIn('call ACME_fnc_epinephrineRecipe',save)
        self.assertIn('call ACME_fnc_medicationTakeSources',save)
        self.assertIn('"dilutionB13"',save)
        from test_historical_medication_preparation import test_flush_draw_only_stages_and_save_funds_all_components_and_saline_carrier
        test_flush_draw_only_stages_and_save_funds_all_components_and_saline_carrier()

    def test_preparation_validates_before_atomic_source_debit(self):
        commit = src('skCompoundCommit')
        self.assertLess(commit.index('_totalDrugMl > _cap'), commit.index('call ACME_fnc_medicationTakeSources'))
        self.assertLess(commit.index('call ACME_fnc_medicationTakeSources'), commit.index('_store pushBack'))
        debit = src('medicationTakeSources')
        self.assertLess(debit.index('isNil {'), debit.index('ACME_fnc_infusionVialVolume'))
        self.assertLess(debit.index('ACME_fnc_infusionVialVolume'), debit.index('ACME_fnc_vialTake'))
        self.assertIn('ACME_fnc_vialRefund', debit)
        self.assertIn('ACME_fnc_treatmentSupplyTake', debit)
        self.assertIn('ACME_fnc_treatmentSupplyRefund', debit)
        self.assertLess(debit.index('ACME_fnc_infusionVialVolume'), debit.index('ACME_fnc_treatmentSupplyTake'))
        self.assertLess(debit.index('ACME_fnc_vialRefund'), debit.index('ACME_fnc_treatmentSupplyRefund'))

    def test_virtual_marker_includes_single_component_preparations(self):
        inject = src('skInjectSite')
        self.assertIn('in ["compoundB13", "dilutionB13"]', inject)
        self.assertIn('_x pushBack _virtual', inject)
        self.assertNotIn('count _components > 1', inject)
        self.assertIn('abs (_componentMl - _amt) > 0.001', inject)
        self.assertLess(inject.index('forEach _sourceParts'), inject.index('_store deleteAt'))

    def test_actual_route_is_kept_through_owner_and_flush(self):
        for name in ('medicationRequest','medicationLineLocal'):
            self.assertIn('[_x select 0,_x select 2,true,_x param [5,false]]',src(name))
        owner=src('medicationLineLocal')
        self.assertIn('[_site,_identity,_seconds,"bolus",_preparedMixture,_rateMeta]',owner)
        self.assertLess(owner.index('setVariable ["ACME_pendingFlush"'),owner.index('call ace_medical_treatment_fnc_medicationLocal'))
        from test_historical_medication_preparation import test_actual_route_and_prepared_metadata_survive_owner_delivery_without_dose_duplication, test_flush_queue_preserves_actual_route_mixture_and_rate_metadata_and_drains_once
        for iv in [True,False]:
            test_actual_route_and_prepared_metadata_survive_owner_delivery_without_dose_duplication(iv,0.6)
        test_flush_queue_preserves_actual_route_mixture_and_rate_metadata_and_drains_once()

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
        # Execute the production refund, retry and ACK paths. A rejected aliquot
        # merges into its original identity and retains current canonical tags;
        # packet retries and duplicate ACKs never manufacture another syringe.
        from test_b279_syringe_inventory import setup as inventory_setup, function
        from test_menu_death_lifecycle import execute
        # The existing fixture uses namespaces for native object identity.
        execute(inventory_setup() + ''.join(function(name).replace(
            'isNull (_row select 0)', '((_row select 0) isEqualTo objNull)') for name in (
            'medicationEscrowCommit', 'medicationRetry', 'medicationAck')) + r'''
            private _complete=["Ketamine",10,3,"current-provider mixture",2,
                [["Ketamine",2],["Propofol",1]],"dilutionB13","blue_opioid",
                "current correct tag","current line two","current line three","mix-id","flush","inventoryB279"];
            private _other=+_row; _other set [11,"other-id"]; _other set [8,"other label"];
            private _remaining=+_complete; _remaining set [2,1.8]; _remaining set [4,1.2];
            _remaining set [5,[["Ketamine",1.2],["Propofol",0.6]]];
            private _returned=+_complete; _returned set [2,1.2]; _returned set [4,0.8];
            _returned set [5,[["Ketamine",0.8],["Propofol",0.4]]];
            _returned set [3,"old refund label"]; _returned set [8,"old refund tag"];
            // A whole rejected syringe absent from inventory keeps every payload field.
            _medic setVariable ["ACME_narcStore",[_other]];
            [_medic,[[],[_complete],[]],false] call ACME_fnc_medicationRefund;
            private _restored=_medic getVariable "ACME_narcStore";
            [_restored isEqualTo [_other,_complete],"whole refund dropped mixture, saline, tag or stable identity"] call _check;
            // Missing ACK: retry the exact immutable request, without a dose refund.
            _medic setVariable ["ACME_narcStore",[_other,_remaining]];
            private _args=[_patient,_medic,1,"mixed-request","administer","leftarm",
                [["Ketamine_IV",40,true,"mixture",20,true,["rate","K"]],
                 ["Propofol_IV",4,true,"mixture",20,true,["rate","P"]]],0,[0,3,100],
                ["syringeB279","custody-request","mix-id"]];
            private _refund=[[],[_returned],[]];
            private _meta=_args select 9;
            private _escrow=createHashMapFromArray [["mixed-request",[_patient,_args,_refund,0,0,_meta]]];
            _medic setVariable ["ACME_medicationEscrow",_escrow];
            missionNamespace setVariable ["ACME_clinical_ownedUnits",[_medic]];
            private _retryDt=1; private _retried=[];
            ACME_fnc_clinicalTickDelta={_retryDt};
            ACME_fnc_ownerDispatch={_retried pushBack _this;};
            call ACME_fnc_medicationRetry;
            [count _retried==0 && {(_medic getVariable "ACME_narcStore") isEqualTo [_other,_remaining]},"missing ACK refunded or dispatched before retry interval"] call _check;
            call ACME_fnc_medicationRetry;
            [_retried isEqualTo [[_patient,"medicationLine",_args]],"retry dropped mixture dose, route, catheter, duration or custody metadata"] call _check;
            [(_medic getVariable "ACME_narcStore") isEqualTo [_other,_remaining],"retry invented another syringe or volume"] call _check;
            // Rejection merges into the existing physical identity, preserving its current label.
            [_medic,"mixed-request",false,"rejected"] call ACME_fnc_medicationAck;
            private _settled=_medic getVariable "ACME_narcStore";
            [count _settled==2 && {(_settled select 0) isEqualTo _other},"refund duplicated stable identity or touched another syringe"] call _check;
            private _mixed=_settled select 1;
            [abs ((_mixed select 2)-3)<0.000001 && {abs ((_mixed select 4)-2)<0.000001},"rejected aliquot lost medication or saline volume"] call _check;
            private _parts=_mixed select 5;
            [count _parts==2 && {(_parts select 0 select 0)=="Ketamine"} && {abs ((_parts select 0 select 1)-2)<0.000001}
                && {(_parts select 1 select 0)=="Propofol"} && {abs ((_parts select 1 select 1)-1)<0.000001},"refund dropped or reassigned mixture components"] call _check;
            [(_mixed select [7,7]) isEqualTo (_complete select [7,7]) && {(_mixed select 3)==(_complete select 3)},"stale refund overwrote canonical tag, identity or barrel"] call _check;
            private _settleCount=count _settlements;
            [_medic,"mixed-request",false,"duplicate"] call ACME_fnc_medicationAck;
            call ACME_fnc_medicationRetry;
            [(_medic getVariable "ACME_narcStore") isEqualTo _settled && {count _settlements==_settleCount} && {count _retried==1},"duplicate ACK/retry repaid the same aliquot twice"] call _check;
            // An accepted slice never restores the reserved medication, even with a repeated ACK.
            _medic setVariable ["ACME_narcStore",[_other,_remaining]];
            _medic setVariable ["ACME_medicationEscrow",createHashMapFromArray [["accepted-request",[_patient,_args,_refund,0,0,_meta]]]];
            [_medic,"accepted-request",true,"accepted"] call ACME_fnc_medicationAck;
            [_medic,"accepted-request",true,"duplicate"] call ACME_fnc_medicationAck;
            [(_medic getVariable "ACME_narcStore") isEqualTo [_other,_remaining],"accepted delivery was refunded"] call _check;
        ''')
        self.assertIn('[_row select 0,"medicationLine",_row select 1]', src('medicationRetry'))
        self.assertIn('_receipts getOrDefault [_id', src('medicationLineLocal'))

if __name__ == '__main__':
    unittest.main()
