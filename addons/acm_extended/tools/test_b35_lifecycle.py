"""PTX owner/reset/save source contracts; these checks do not execute Arma or CBA."""
from historical_source import read_source
from pathlib import Path
import re
import unittest
from source_scan import lex, matching

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return read_source(ROOT / relative, encoding="utf-8-sig")


def source(name):
    return read(f"functions/fn_{name}.sqf")


class PtxLifecycle(unittest.TestCase):
    def test_isolated_stable_chest_stays_in_shared_registry(self):
        register = source("ownerRegister")
        chest = register[register.index("private _hasPtx"):register.index("private _needs")]
        for field in ("ACM_breathing_Pneumothorax_State",
                      "ACM_breathing_TensionPneumothorax_State",
                      "ACM_breathing_ChestInjury_State", "ACME_ptx_state"):
            self.assertIn(field, chest)
        needs = register[register.index("private _needs"):register.index("private _registry")]
        self.assertIn("|| {_hasPtx}", needs)
        self.assertIn("if (_needs) then {_registry pushBackUnique _patient;}", register)
        circ = source("circHandle")
        self.assertIn('missionNamespace getVariable ["ACME_clinical_activePatients", []]', circ)

    def test_recovery_adopts_but_never_reinflicts_injury(self):
        register = source("ownerRegister")
        self.assertIn("if (_hasPtx) then {[_patient] call ACME_fnc_ptxEnsure;};", register)
        self.assertNotIn("ACME_fnc_ptxInjury", register)
        self.assertNotIn("handlePneumothorax", register)
        self.assertLess(register.index("ACME_clinicalRestoring"), register.index("ACME_fnc_ptxEnsure"))
        self.assertLess(register.index("if (!alive _patient) exitWith"), register.index("ACME_fnc_ptxEnsure"))

    def test_native_worker_removed_on_both_locality_directions(self):
        init = source("ownerInit")
        local = init[init.index('["CAManBase", "Local"'):init.index('["CAManBase", "init"')]
        self.assertIn('"ACM_breathing_Pneumothorax_PFH"', local)
        self.assertIn("CBA_fnc_removePerFrameHandler", local)
        cleanup = local.index('"ACM_breathing_Pneumothorax_PFH"')
        # The native-handler foreach executes in the Local event's outer
        # scope on both edges. Compare with the actual incoming registration
        # that restarts PTX through ownerRegister, not an unrelated earlier
        # incoming-only carrier animation branch.
        tokens = lex(local)
        pairs = matching(tokens)
        scopes = [i for i, token in enumerate(tokens) if token.value == '{'
                  and token.offset < cleanup < tokens[pairs[i]].offset]
        self.assertEqual(len(scopes), 1, 'native PTX cleanup is conditional on a locality direction')
        values = [token.value for token in tokens]
        call = ['[', '_h', ']', 'call', 'CBA_fnc_removePerFrameHandler']
        calls = [i for i in range(len(tokens)) if values[i:i+len(call)] == call]
        self.assertEqual(len(calls), 1, 'native cleanup must remove each exact old handle once')
        removal = tokens[calls[0]].offset
        removal_scopes = [i for i, token in enumerate(tokens) if token.value == '{'
                          and token.offset < removal < tokens[pairs[i]].offset]
        self.assertEqual(len(removal_scopes), 3,
                         'native PTX removal must run on both Local edges inside its handle foreach')
        self.assertEqual(removal_scopes[0], scopes[0])
        self.assertEqual(values[removal_scopes[2]-7:removal_scopes[2]],
                         ['if', '(', '_h', '>=', '0', ')', 'then'])
        loop_end = pairs[removal_scopes[1]]
        self.assertEqual(values[loop_end+1:loop_end+3], ['forEach', '['])
        loop_array_end = pairs[loop_end+2]
        self.assertIn('ACM_breathing_Pneumothorax_PFH', values[loop_end+3:loop_array_end])
        registration = local.index('[_unit] call ACME_fnc_ownerRegister;')
        incoming_registration = local.rfind('if (_isLocal) then {', 0, registration)
        self.assertLess(cleanup, incoming_registration)
        self.assertLess(incoming_registration, registration)
        native_cleanup = local[local.index('private _h = _unit getVariable'):cleanup]
        self.assertIn('[_h] call CBA_fnc_removePerFrameHandler;', native_cleanup)
        self.assertIn('_unit setVariable [_x, -1, false];', native_cleanup)
        self.assertIn('["ACME_alt_ptxSample", nil, false]', local)
        self.assertNotIn('["ACME_ptx_state", nil', local)
        self.assertNotIn('["ACME_ptx_tensionSeverity", nil', local)

    def test_full_heal_retires_native_worker_and_old_episode_first(self):
        reset = source("clinicalReset")
        begin = reset[reset.index('if (_phase == "begin")'):reset.index("// Physical equipment")]
        self.assertIn("ACME_fnc_clinicalEpoch) + 1, true", begin)
        self.assertIn('"ACM_breathing_Pneumothorax_PFH"', begin)
        self.assertIn('["ACME_alt_ptxSample", nil, false]', begin)
        self.assertIn("CBA_fnc_removePerFrameHandler", begin)
        self.assertIn("call ACME_fnc_clinicalFields", reset)
        self.assertIn("_patient setVariable [_name, nil, true]", reset)

    def test_state_is_saved_but_old_progress_cannot_return_from_save(self):
        fields = source("clinicalFields")
        for field in ("ACME_ptx_state", "ACME_ptx_tensionSeverity", "ACME_ptx_nativeSealCount", "ACME_ptx_nativeSealHoleCount"):
            self.assertEqual(len(re.findall(rf'"{field}"', fields)), 1)
            self.assertIn(f'["{field}", "", true, true]', fields)
        self.assertIn('["ACME_ptx_tensionProgress", "", true, false]', fields)
        self.assertNotIn('"ACME_alt_ptxSample"', fields)
        self.assertNotIn('"ACM_breathing_Pneumothorax_PFH"', fields)
        self.assertIn("if (!_persist) then {continue;};", source("clinicalSnapshot"))
        self.assertIn("select {_x param [3, true]}", source("clinicalRestore"))

    def test_instant_seal_snapshot_only_accepts_absent_or_wound_count(self):
        validate = source("clinicalValidate")
        self.assertIn('["ACME_ptx_nativeSealCount","SCALAR"]', validate)
        self.assertIn('["ACME_ptx_nativeSealHoleCount","SCALAR"]', validate)
        seal = validate[validate.index('case "ACME_ptx_nativeSealCount"'):validate.index('case "ACME_do2_dilution"')]
        self.assertIn('case "ACME_ptx_nativeSealHoleCount"', seal)
        self.assertIn('!([_v] call _number)', seal)
        self.assertIn('_v < -1', seal)
        self.assertIn('floor _v != _v', seal)

    def test_model_uses_plain_encoded_duration_payload(self):
        snapshot = source("clinicalSnapshot")
        self.assertIn('[_v, true, _clock] call ACME_fnc_clinicalCodec', snapshot)
        # No PTX duration is recast as a machine-local wall clock during saving.
        self.assertNotIn('if (_name == "ACME_ptx_state")', snapshot)
        self.assertIn('["ACME_ptx_state", "", true, true]', source("clinicalFields"))

    def test_save_preflight_rejects_wrong_model_shape_and_ranges(self):
        validate = source("clinicalValidate")
        self.assertIn('["ACME_ptx_state","ARRAY"]', validate)
        ptx = validate[validate.index('case "ACME_ptx_state"'):validate.index('case "ACME_ptx_tensionSeverity"')]
        for guard in ('count _v != 9', '(_v select 0) != 1',
                      '[1,8] findIf', '(_v select _x) > 32',
                      '(_v select 7) > 4', '[2,4,5] findIf',
                      '(_v select 3) > 86400', 'floor (_v select 6)',
                      '(_v findIf {!([_x] call _number)})'):
            self.assertIn(guard, ptx)
        self.assertIn('finite _v', validate)
        restore = read("overrides/fn_deserializeState.sqf")
        self.assertLess(restore.index("ACME_fnc_clinicalValidate"), restore.index("ACME_fnc_clearAllAilments"))

    def test_saved_internal_gas_range_is_separate_from_native_stage(self):
        validate = source("clinicalValidate")
        ptx = validate[validate.index('case "ACME_ptx_state"'):validate.index('case "ACME_ptx_tensionSeverity"')]
        self.assertIn('([1,8] findIf {(_v select _x) < 0 || {(_v select _x) > 32}})', ptx)
        self.assertIn('(_v select 7) < 0 || {(_v select 7) > 4}', ptx)
        self.assertNotIn('[1,7,8]', ptx)

    def test_restore_reuses_saved_model_and_never_runs_native_injury_entry(self):
        restore = read("overrides/fn_deserializeState.sqf")
        self.assertNotIn("call EFUNC(breathing,handlePneumothorax)", restore)
        self.assertNotIn("ACME_fnc_ptxInjury", restore)
        self.assertIn("[_unit] call ACME_fnc_ptxEnsure;", restore)
        self.assertLess(restore.index("call ACME_fnc_clinicalRestore"), restore.index("call ACME_fnc_ptxEnsure"))
        self.assertLess(restore.index('["ACME_clinicalRestoring", false, false]'), restore.index("call ACME_fnc_ptxEnsure"))
        self.assertLess(restore.index("call ACME_fnc_ptxEnsure"), restore.rindex("call ACME_fnc_ownerRegister"))

    def test_legacy_save_is_adopted_from_physiology_not_saved_handler_id(self):
        restore = read("overrides/fn_deserializeState.sqf")
        breathing = restore[restore.index("// Breathing:"):restore.index("QEGVAR(breathing,Hemothorax_PFH)")]
        for field in ("Pneumothorax_State", "TensionPneumothorax_State", "ChestInjury_State", "ACME_ptx_state"):
            self.assertIn(field, breathing)
        self.assertNotIn("Pneumothorax_PFH", breathing)

    def test_instructor_clear_retires_model_without_touching_equipment(self):
        mega=source('megacodeChestInjury')
        clear=mega[mega.index('if (_t == "ncd")'):mega.index('switch (_t)')]
        for field in ('ACME_ptx_state','ACME_ptx_tensionSeverity','ACME_ptx_tensionProgress'):
            self.assertIn(field,clear)
        self.assertIn('CBA_fnc_removePerFrameHandler',clear)
        self.assertIn('["pneumothoraxPFH", -1]',clear)
        self.assertIn('["hardcorePneumothorax", false]',clear)
        for unrelated in ('ACME_CS_holeData','ACME_thora_tube_left','ACME_ncd_placed'):
            self.assertNotIn(unrelated,clear)
        from test_historical_airway_execution import test_instructor_chest_clear_removes_episode_and_worker_but_retains_equipment
        test_instructor_chest_clear_removes_episode_and_worker_but_retains_equipment()

    def test_training_injury_seeds_model_before_native_projection(self):
        mega = source("megacodeChestInjury")
        tension = mega[mega.index('case "tpneumo"'):mega.index('case "hemothorax"')]
        self.assertLess(tension.index('ACME_fnc_ptxInjury'), tension.index('ACME_fnc_ptxPublish'))
        for seed in ('_ptx set [1, 4]', '_ptx set [3, 0]', '_ptx set [4, 1]', '_ptx set [7, 4]'):
            self.assertIn(seed, tension)
        self.assertNotIn('setVariable ["ACM_breathing_Pneumothorax_State"', tension)
        self.assertIn('[_p, _ptx, true] call ACME_fnc_ptxPublish', tension)


if __name__ == "__main__":
    unittest.main()
