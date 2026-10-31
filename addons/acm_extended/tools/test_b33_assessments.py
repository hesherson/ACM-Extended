"""B33 assessment source regressions; these do not execute SQF or Arma UI.

Protect exact-temperature disclosure at completion and keep the new observation
additive to every existing injury finding, using live drug/descriptor state.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / "functions" / ("fn_" + name + ".sqf")).read_text(encoding="utf-8")


class AssessmentContracts(unittest.TestCase):
    def test_exact_temperature_callbacks_recheck_provider_tool_before_disclosure(self):
        for name in ("checkTemperature", "readCoreTemp"):
            with self.subTest(callback=name):
                text = source(name)
                gate = text.index('([_medic, _patient, "ACM_Thermometer"] call ACME_fnc_treatmentSupplyCount) <= 0')
                self.assertLess(gate, text.index('getVariable ["ACME_hypo_temp"'))
                self.assertLess(gate, text.index("call ace_common_fnc_displayTextStructured"))
                self.assertLess(gate, text.index("call ACME_fnc_medLog"))
                self.assertIn("exitWith {};", text[gate:text.index("private _t", gate)])
                self.assertNotIn("removeItem", text)
        self.assertLess(source("checkTemperature").index('"ACM_Thermometer"'),
                        source("checkTemperature").index('setVariable ["ACME_tempReading"'))

    def test_eye_movement_is_appended_after_all_existing_injury_findings(self):
        text = source("tbiAssessPupils")
        append = text.index("_exam = _exam +")
        original = text[:append]
        for finding in (
            "Anisocoria.", "blown (fixed, dilated)", "bilateral fixed + dilated",
            "equal/round, sluggish bilaterally", "PERRL.",
            "bigger and slower", "wide open and does not react", "neither reacts to light",
            "equal but react slowly", "equal and react normally to light",
        ):
            self.assertIn(finding, original)
        self.assertIn('[_exam, 3, _medic]', text[append:])
        self.assertIn('[_patient, "activity", "%1 assessed pupils: %2", _args]', text[append:])
        self.assertIn('[_patient, "quick_view", "%1 assessed pupils: %2", _args]', text[append:])

    def test_append_uses_current_descriptor_choice_without_exposing_drug_cause(self):
        text = source("tbiAssessPupils")
        self.assertIn('getVariable ["ACME_hc_descriptors", false]) isEqualTo true', text)
        append = text[text.index("_exam = _exam +"):]
        self.assertIn('if (_hcP) then {" Nystagmus."}', append)
        self.assertIn('" Their eyes are rapidly and involuntarily moving."', append)
        self.assertNotIn("ketamine", append.lower())

    def test_current_ketamine_effect_cannot_be_replaced_by_total_load_or_old_flag(self):
        text = source("tbiAssessPupils")
        branch = text[text.index("// B33:"):text.index("[_exam, 3, _medic]")]
        self.assertIn("call ACME_fnc_sedationComponents", branch)
        self.assertIn("_ket >= 1", branch)
        self.assertIn("_ket > ((_prop max 0) + (_mid max 0))", branch)
        for field in ("ACE_isUnconscious", "ace_medical_inCardiacArrest", "ACME_roc_paralyzed"):
            self.assertIn(field, branch)
        self.assertIn("alive _patient", branch)
        for mutation in ("setVariable", "remoteExec", "ACME_fnc_setVarNet"):
            self.assertNotIn(mutation, branch)

    def test_prior_trauma_unconsciousness_does_not_block_current_deep_ketamine(self):
        text = source("tbiAssessPupils")
        branch = text[text.index("// B33:"):text.index("[_exam, 3, _medic]")]
        self.assertNotIn("ACME_ket_sedated", branch)
        self.assertIn('getVariable ["ACE_isUnconscious", false]', branch)
        # Both independent requirements remain even when prior unconsciousness
        # belongs to trauma: a stale flag/trace or other-hypnotic majority fails.
        self.assertIn("_ket >= 1 && {_ket > ((_prop max 0) + (_mid max 0))}", branch)


if __name__ == "__main__":
    unittest.main()
