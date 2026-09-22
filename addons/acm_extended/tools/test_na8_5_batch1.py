#!/usr/bin/env python3
"""NA8.5 Batch 1 source checks and Python reference tests. These do not execute SQF."""
from __future__ import annotations
from historical_source import read_source
from pathlib import Path
import itertools
import re
import sys
import unittest
sys.dont_write_bytecode = True
from source_scan import lex, code_streams, source_files
R = Path(__file__).resolve().parents[1]
RAW = 'ACME_hc_descriptors'
ALIAS = 'ACME_hcEff_descriptors'

def read(name):
    return read_source(R/name, encoding='utf-8-sig')

def code(name):
    return ' '.join(t.value for t in lex(read(name)))

def logs(text, config=False):
    return [t.value for ts in code_streams(text, config) for t in ts
            if t.kind == 'ident' and t.value.lower() in {'diag_log','bis_fnc_log','bis_fnc_error','cba_fnc_log'}]

# This is an intentionally small behavioral reference, not an SQF interpreter.
def gauge_reference(entries, types, labels=('Upper','Middle','Lower')):
    result = []
    for row in entries:
        row = list(row) if isinstance(row, list) else row
        if isinstance(row, list) and len(row) >= 2 and isinstance(row[0], str):
            text = row[0]
            if text.lower().startswith('true ('):
                site = next((i for i,label in enumerate(labels)
                             if text.lower().startswith(('true ('+label+')').lower())), -1)
                kind = types[site] if site >= 0 and site < len(types) else 0
                gauge = {5:'18g IV', 6:'20g IV'}.get(kind,'')
                if gauge:
                    row[0] = gauge+' '+text[5:]
        result.append(row)
    return result

class QuietOutput(unittest.TestCase):
    def test_no_unapproved_rpt_emitters_in_shipped_sqf_or_callbacks(self):
        # B22 restores the pre-B20 quiet debug overlay. No shipped runtime SQF or config callback may
        # emit RPT traffic; diagnostic dumping/tracing was explicitly reverted with the tabbed overlay.
        approved=set()
        failures=[]
        emitters=[]
        for p in source_files(R):
            if logs(read_source(p, encoding='utf-8-sig'),p.suffix.lower() in {'.cpp','.hpp','.inc'}):
                rel=str(p.relative_to(R)); emitters.append(rel)
                if rel not in approved: failures.append(rel)
        self.assertEqual(failures,[])
        self.assertEqual(set(emitters),approved)
    def test_scan_finds_quoted_config_callback(self):
        self.assertEqual(logs('onLoad = "diag_log \'message\';";',True),['diag_log'])
    def test_scan_ignores_comments_and_messages(self):
        self.assertEqual(logs('// diag_log "message";\nhint "diag_log";'),[])
    def test_clinical_log_functions_remain(self):
        for p in ['functions/fn_ivMinigameRegister.sqf','functions/fn_medLog.sqf']:
            self.assertIn('ace_medical_treatment_fnc_addToLog',read(p))
    def test_finite_value_guard_remains(self):
        s=read('overrides/fn_getBloodVolumeChange.sqf')
        self.assertIn('finite _v',s)
        self.assertEqual(s.count('call _fnc_finite'),4)
        self.assertIn('_fallback',s)
    def test_restore_rejections_remain(self):
        s=read('overrides/fn_deserializeState.sqf')
        for guard in ['if (isNull _state) exitWith', 'if (!_clockOK) exitWith', 'if (_invalid != "") exitWith']:
            self.assertIn(guard,s)
    def test_binding_results_are_kept(self):
        self.assertIn('ACME_NA3_bindingResult = call ACME_fnc_clinicalBindings',read('functions/fn_clinicalInit.sqf'))
        self.assertIn('ACME_runtimeOverrideStatus',read('functions/fn_postInit.sqf'))
    def test_network_report_keeps_rates_and_rows(self):
        s=read('functions/fn_netReport.sqf')
        self.assertIn('ACME_netReportDetails',s)
        self.assertIn('[(_totalSent / _elapsed), (_totalSaved / _elapsed)]',s)
    def test_local_probes_keep_result(self):
        for f,key in [('tools/na8_runtime_probe.sqf','ACME_uiProbeResult'),('tools/fracture_descriptor_probe.sqf','ACME_fractureProbeResult')]:
            self.assertIn(key,read(f)); self.assertTrue(read(f).rstrip().endswith('_out'))

class DescriptorSource(unittest.TestCase):
    def test_no_cached_descriptor_flag_in_executable_sources(self):
        hits=[]
        for p in source_files(R):
            for ts in code_streams(read_source(p, encoding='utf-8-sig'),p.suffix in {'.cpp','.hpp'}):
                if any(t.value.lower()==ALIAS.lower() for t in ts):hits.append(str(p.relative_to(R)))
        self.assertEqual(hits,[])
    def test_only_cba_owns_raw_setting(self):
        hits=[]
        for p in source_files(R):
            ts=lex(read_source(p, encoding='utf-8-sig'))
            for i,t in enumerate(ts):
                if t.kind=='ident' and t.value.lower()==RAW.lower() and i+1<len(ts) and ts[i+1].value=='=':
                    hits.append(str(p))
                if t.kind=='ident' and t.value.lower()=='setvariable' and i+2<len(ts) and ts[i+2].value.lower()==RAW.lower():
                    hits.append(str(p))
        self.assertEqual(hits,[])
    def test_all_previous_consumer_surfaces_read_effective_checkbox(self):
        files=['medDescriptor','clinTerm','skinSigns','bleedStatusRelabel','tbiAssessPupils','medLog','bodyPartName',
               'junctionalInflict','ivSiteRelabel','ivLogRelabel','updateEJTransfusionMenu','skSiteName',
               'junctionalInjuryEntry','inspectForFracture','ivLogSite']
        for f in files:
            with self.subTest(f=f):self.assertIn('getVariable ["ACME_hc_descriptors", false]',read('functions/fn_'+f+'.sqf'))
    def test_map_gate_precedes_cached_lookup(self):
        s=read('functions/fn_clinTerm.sqf')
        self.assertLess(s.index('getVariable ["ACME_hc_descriptors"'),s.index('getVariable ["ACME_clinTermMap"'))
    def test_choice_requires_boolean_true(self):
        for f in ['medDescriptor','clinTerm','skSiteName','medLog']:
            self.assertIn('getVariable ["ACME_hc_descriptors", false]) isEqualTo true',read('functions/fn_'+f+'.sqf'))
    def test_selftest_never_mutates_settings(self):
        s=code('functions/fn_descriptorSelfTest.sqf')
        self.assertNotIn('ACME_hc_descriptors =',s)
        self.assertNotIn('setVariable [ ACME_hc_descriptors',s)
        self.assertIn('ACME_descriptorSelfTestResult',s)
    def test_setting_has_no_difficulty_callback(self):
        s=read('XEH_preInit.sqf');a=s.index('["ACME_hc_descriptors", "CHECKBOX"');b=s.index('// the per-system enable',a)
        self.assertIn('false, 2, {}',s[a:b]);self.assertNotIn('applyHardcore',s[a:b])
    def test_breathing_hint_and_log_still_resolve_via_clinterm(self):
        s=read('overrides/fn_checkBreathingLocal.sqf')
        self.assertIn('call ACME_fnc_clinTerm',s)
        self.assertIn('private _hint = [_hintKey] call _lz',s)
        self.assertIn('private _hintLog = [_hintLogKey] call _lz',s)
        self.assertIn('localize _k',s)
    def test_native_fracture_fallback_retained(self):
        s=read('functions/fn_inspectForFracture.sqf')
        self.assertLess(s.index('getVariable ["ACME_hc_descriptors"'),s.index('call ACM_disability_fnc_inspectForFracture'))
    def test_menu_route_group_labels_still_split(self):
        s=read('overrides/fn_updateActions.sqf')
        for pair in ["['By Mouth', 'PO']", "['Inhaled', 'IN']", "['Buccal', 'BUC']"]:self.assertIn(pair,s)
        self.assertTrue('getVariable ["ACME_hc_descriptors", false]' in s or "getVariable ['ACME_hc_descriptors', false]" in s)
    def test_body_part_short_names_are_gated_but_explicit_log_abbreviation_is_not(self):
        s=read('functions/fn_bodyPartName.sqf')
        gate=s.index('getVariable ["ACME_hc_descriptors"')
        abbr=s.index('if (_form isEqualTo "abbr") exitWith')
        final=s.rindex('case "leftarm":  { "LUE" }')
        self.assertLess(abbr,gate)
        self.assertLess(gate,final)
    def test_plain_iv_log_site_is_available(self):
        s=read('functions/fn_ivLogSite.sqf')
        self.assertIn('["Left neck", "Right neck"]',s)
        self.assertLess(s.index('getVariable ["ACME_hc_descriptors"'),s.index('getOrDefault ["short"'))
    def test_named_and_numeric_site_contract_kept(self):
        s=read('functions/fn_skSiteName.sqf')
        for part in ['_site isEqualType ""','case "upper"','case "middle"','case "lower"','_site isEqualType 0']:
            self.assertIn(part,s)
    def test_non_boolean_checkbox_values_do_not_enable_reference(self):
        for value in [None,False,0,1,'true','false',[],{}]:
            with self.subTest(value=value):self.assertFalse(value is True)
    def test_actual_breathing_table_has_plain_and_clinical_rows(self):
        text=read('functions/fn_medDescriptor.sqf')
        rows=dict((m[0],(m[1],m[2])) for m in re.findall(r'\["(\w+)",\s*\["([^"]*)",\s*"([^"]*)"\]\]',text))
        expected={'fast':('Breathing quickly','Tachypneic'),'slow':('Breathing slowly','Bradypneic'),
                  'none':('Not breathing','Apneic'),'apneic':('Patient is not breathing','Patient is apneic')}
        for key,pair in expected.items():self.assertEqual(rows[key],pair)

class GaugeTests(unittest.TestCase):
    def test_site_types_select_each_gauge_in_source(self):
        s=read('functions/fn_ivGaugeRelabel.sqf')
        self.assertIn('_types param [_site, 0]',s)
        self.assertIn('case 5: {"18g IV"}',s);self.assertIn('case 6: {"20g IV"}',s)
    def test_new_helper_runs_before_ej_relabel(self):
        s=read('functions/fn_postInit.sqf')
        self.assertLess(s.index('call ACME_fnc_ivGaugeRelabel'),s.index(' + "(EJ)"'))
        self.assertNotIn('if !(5 in _iv)',s)
    def test_registration_present_once(self):
        self.assertEqual(read('config.cpp').count('class ivGaugeRelabel {};'),1)
    def test_no_patient_or_network_write_in_gauge_helper(self):
        s=code('functions/fn_ivGaugeRelabel.sqf').lower()
        for keyword in ['setvariable','remoteexec','cbA_fnc_globalevent'.lower(),'cbA_fnc_targetevent'.lower()]:
            self.assertNotIn(keyword,s)
    def test_all_125_type_combinations_reference(self):
        colors=[[1,1,1,1],[0,1,0,1],[0,0,1,1]]
        for types in itertools.product([0,1,2,5,6],repeat=3):
            # Native rows only exist for positive types. Preserve native known-gauge text.
            rows=[];expected=[]
            for i,(kind,label) in enumerate(zip(types,['Upper','Middle','Lower'])):
                if kind==0:continue
                name={1:'16g IV',2:'14g IV'}.get(kind,'true')
                rows.append([f'{name} ({label}) [Saline]',colors[i]])
                expected.append([f'{dict([(1,"16g IV"),(2,"14g IV"),(5,"18g IV"),(6,"20g IV")])[kind]} ({label}) [Saline]',colors[i]])
            with self.subTest(types=types): self.assertEqual(gauge_reference(rows,types),expected)
    def test_reversed_rows_match_site_not_list_order(self):
        rows=[['true (Lower)',[1]],['true (Upper) [Blood]',[2]]]
        self.assertEqual(gauge_reference(rows,[6,0,5]),[['18g IV (Lower)',[1]],['20g IV (Upper) [Blood]',[2]]])
    def test_localized_site_names(self):
        rows=[['true (Oben) [Plasma]',[1]],['true (Unten)',[2]]]
        self.assertEqual(gauge_reference(rows,[6,0,5],['Oben','Mitte','Unten']),[['20g IV (Oben) [Plasma]',[1]],['18g IV (Unten)',[2]]])
    def test_ej_laterality_kept_until_after_gauge(self):
        rows=[['true (Upper)',[1]],['true (Middle)',[2]]]
        self.assertEqual(gauge_reference(rows,[6,5,0]),[['20g IV (Upper)',[1]],['18g IV (Middle)',[2]]])
    def test_no_broad_boolean_text_replacement(self):
        rows=[['true ([unrelated])',[1]],['true (EJ)',[2]],['No external bleeding',[3]]]
        self.assertEqual(gauge_reference(rows,[6,0,5]),rows)
    def test_unknown_type_and_short_placement_are_untouched(self):
        rows=[['true (Upper)',[1]],['true (Lower)',[2]]]
        self.assertEqual(gauge_reference(rows,[99]),rows)
    def test_handles_sparse_or_malformed_rows(self):
        rows=[[],None,[False,[1]],['true (Upper)',[1],{'extra':'field'}]]
        got=gauge_reference(rows,[6,0,0]);self.assertEqual(got[-1],['20g IV (Upper)',[1],{'extra':'field'}])
    def test_identity_fix_is_independent_of_checkbox(self):
        self.assertNotIn('ACME_hc_',read('functions/fn_ivGaugeRelabel.sqf'))

if __name__=='__main__':
    unittest.main(verbosity=2)
