from backlog_clinical_probes import chest_reset_probe
"""PTX owner/reset/save contracts, including a mocked-engine SQF reset probe."""
from historical_source import read_source
from pathlib import Path
import re
import unittest

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
        self.assertLess(local.index('"ACM_breathing_Pneumothorax_PFH"'), local.index("if (_isLocal)"))
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
        # Execute the instructor command plus actual breathing writers; check equipment and timer state.
        chest_reset_probe()

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
