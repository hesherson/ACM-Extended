from backlog_clinical_probes import tract_and_peel_probe
"""B35 treatment contracts and actual SQF probes with mocked engine boundaries."""
from historical_source import read_source
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOCAL = (
    "applyChestSealLocal", "performNCDLocal", "Thoracostomy_startLocal",
    "Thoracostomy_insertChestTubeLocal", "Thoracostomy_resealChestTubeLocal",
    "Thoracostomy_closeLocal",
)


def override(name):
    return read_source(ROOT / "overrides" / f"fn_{name}.sqf", encoding="utf-8")


class TreatmentProgressionContracts(unittest.TestCase):
    def test_treatment_callbacks_forward_to_patient_owner_before_mutation(self):
        for name in LOCAL:
            text = override(name)
            with self.subTest(callback=name):
                self.assertIn('if (isNull _patient) exitWith {};', text)
                owner = text.index('if (!local _patient) exitWith')
                self.assertIn(f'["ACM_breathing_{name}", _this, _patient] call CBA_fnc_targetEvent;', text)
                self.assertLess(owner, text.index('call ACME_fnc_ptxEnsure'))
                self.assertLess(text.index('call ACME_fnc_ptxEnsure'), text.index('_patient setVariable'))

    def test_only_shared_controller_can_write_pressure_or_residual_grade(self):
        for name in LOCAL:
            with self.subTest(callback=name):
                text = override(name)
                self.assertNotRegex(text, r'setVariable\s*\[\s*"ACM_breathing_(?:Pneumothorax_State|TensionPneumothorax_State|TensionPneumothorax_Time)"')
                self.assertIn('call ACME_fnc_ptxTreat;', text)
                self.assertIn('call ACM_breathing_fnc_updateLungState;', text)
                self.assertNotIn('call ACM_breathing_fnc_handlePneumothorax', text)

    def test_no_autonomous_native_deterioration_or_posture_failure(self):
        for name in LOCAL + ("handlePneumothorax",):
            with self.subTest(callback=name):
                text = override(name)
                self.assertNotIn('call CBA_fnc_addPerFrameHandler', text)
                self.assertNotIn('call CBA_fnc_waitAndExecute', text)
                self.assertNotIn('call CBA_fnc_waitUntilAndExecute', text)
                self.assertNotIn('Lying_State', text)
                self.assertNotIn('ace_isUnconscious', text)

    def test_native_ncd_injury_is_once_only_and_can_receive_actual_drainage(self):
        text = override("performNCDLocal")
        self.assertEqual(text.count('call ACME_fnc_ptxInjury'), 1)
        self.assertLess(text.index('if (!_indicated)'), text.index('call ACME_fnc_ptxInjury'))
        self.assertLess(text.index('call ACME_fnc_ptxInjury'), text.index('call ACME_fnc_ptxTreat'))
        self.assertIn('[_patient, 0.5] call ace_medical_fnc_adjustPainLevel', text)
        effect = read_source(ROOT / 'functions/fn_chestSealEffectLocal.sqf')
        self.assertEqual(effect.count('call ACME_fnc_ptxInjury'), 1)  # Explicit missed insertion only.
        self.assertNotIn('case "ncdTension"', effect)
        self.assertNotIn('call CBA_fnc_waitAndExecute', effect)
        self.assertNotRegex(effect, r'setVariable\s*\[\s*"ACM_breathing_TensionPneumothorax_State"')

    def test_seal_removal_cannot_become_a_new_injury(self):
        effect=read_source(ROOT/'functions/fn_chestSealEffectLocal.sqf')
        peel=effect.split('case "peel":',1)[1].split('case "miss":',1)[0]
        self.assertIn('[_patient, "peel"] call ACME_fnc_ptxTreat',peel)
        self.assertNotIn('call ACME_fnc_ptxInjury',peel)
        self.assertNotIn('call ACM_breathing_fnc_handlePneumothorax',effect)
        # Cross-machine clock comparison was retired; stable epochs/revisions reject old effects.
        self.assertNotIn('ACME_NA2_resetTime',effect)
        self.assertIn('ACME_CS_blockedEffectEpoch',effect)
        self.assertIn('ACME_CS_lastSealEffectRev',effect)
        tract_and_peel_probe()

    def test_native_thoracostomy_keeps_observations_anesthesia_and_kit_semantics(self):
        text = override("Thoracostomy_startLocal")
        self.assertIn('"ACM_breathing_Hemothorax_Fluid"', text)
        self.assertIn('"ACM_breathing_Hemothorax_State"', text)
        self.assertNotRegex(text, r'setVariable\s*\[\s*"ACM_breathing_Hemothorax')
        self.assertIn('"Lidocaine", false, 1', text)
        self.assertIn('call ace_medical_fnc_adjustPainLevel', text)
        self.assertIn('"ace_medical_CriticalVitals"', text)
        self.assertIn('"ACM_breathing_Thoracostomy_UsedKit", _usedKit, true', text)
        self.assertIn('"quick_view"', text)
        for op, flag in (("startLocal", 1), ("insertChestTubeLocal", 2), ("resealChestTubeLocal", 2), ("closeLocal", 0)):
            self.assertIn(f'"ACM_breathing_Thoracostomy_State", {flag}, true', override('Thoracostomy_' + op))
        self.assertIn('"ACM_breathing_Thoracostomy_UsedKit", false, true', override('Thoracostomy_closeLocal'))

    def test_sealed_surgical_tract_cannot_cover_external_chest_wounds(self):
        click=read_source(ROOT/'functions/fn_thoraMouseDown.sqf')
        seal=click.split('if (_held == "seal") exitWith {',1)[1].split('private _tubeMedic',1)[0]
        self.assertNotIn('call ACM_breathing_fnc_applyChestSeal',seal)
        self.assertIn('"chestEffect", [_patient, _medS, "thoraSeal"',seal)
        self.assertIn('call ACME_fnc_clinicalEpoch',seal)
        effect=read_source(ROOT/'functions/fn_chestSealEffectLocal.sqf')
        branch=effect.split('case "thoraSeal":',1)[1].split('case "peel":',1)[0]
        self.assertIn('_clinicalEpoch != ([_patient] call ACME_fnc_clinicalEpoch)',branch)
        self.assertIn('ACME_thora_tube_%1',branch)
        self.assertIn('[_patient, _side, "sealed", true] call ACME_fnc_thoraSideStateCommit',branch)
        self.assertIn('[_patient, _side, "open", "sealed"] call ACME_fnc_thoraSideStateCommit',branch)
        self.assertIn('[_patient, "thoraSeal"] call ACME_fnc_ptxTreat',branch)
        self.assertNotIn('ACME_ptx_nativeSealCount',branch)
        self.assertNotIn('call ACM_breathing_fnc_applyChestSeal',branch)
        tract_and_peel_probe()

    def test_closing_tract_removes_its_outlet_but_never_an_installed_tube(self):
        text = override("Thoracostomy_closeLocal")
        self.assertLess(text.index('ACME_thora_tube_left'), text.index('call ACME_fnc_ptxEnsure'))
        self.assertLess(text.index('ACME_thora_tube_right'), text.index('call ACME_fnc_ptxEnsure'))
        for field in ("open", "tube", "sealed", "incision", "site"):
            self.assertIn(f'"ACME_thora_{field}_%1"', text)
        self.assertIn('"ACME_thora_ver"', text)
        self.assertLess(text.index('"ACME_thora_ver"'), text.index('call ACME_fnc_ptxTreat'))
        self.assertNotIn('ACME_CS_holeData', text)
        self.assertNotIn('ACME_CS_penetratingWounds', text)
        edit = read_source(ROOT / 'functions/fn_chestSealEdit.sqf')
        self.assertNotIn('5th intercostal space', edit)
        self.assertIn('_message = "NAR SPEAR placed.";', edit)

    def test_callbacks_are_registered_and_old_ncd_wrapper_cannot_override_them(self):
        prep=read_source(ROOT.parent/'breathing/XEH_PREP.hpp')
        post=read_source(ROOT/'functions/fn_postInit.sqf')
        events=read_source(ROOT.parent/'breathing/XEH_postInit.sqf')
        for name in LOCAL + ('handlePneumothorax',):
            self.assertIn(f'PREP({name});',prep)
            self.assertTrue((ROOT.parent/'breathing/functions'/f'fnc_{name}.sqf').is_file())
        for name in LOCAL:
            self.assertIn(f'QGVAR({name})',events)
            self.assertIn(f'LINKFUNC({name})',events)
        self.assertNotIn('ACM_breathing_fnc_performNCDLocal =',post)
        self.assertNotIn('ACME_ncdReTensionState =',post)


if __name__ == '__main__':
    unittest.main()
