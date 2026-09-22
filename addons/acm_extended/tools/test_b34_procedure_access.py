from backlog_clinical_probes import thora_access_probe
"""Offline integration contracts. These inspect shipped SQF/config, not Arma execution."""
from historical_source import read_source
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return read_source(ROOT / "functions" / f"fn_{name}.sqf", encoding="utf-8")


class ProcedureAccessContracts(unittest.TestCase):
    def test_action_config_does_not_reimpose_old_medic_tiers(self):
        config = read_source(ROOT / "config.cpp")
        required = {
            "ACME_PerformThoracostomy": "ACM_breathing_allowThoracostomy",
            "ACME_InsertChestTube": "ACME_skillChestTube",
            "ACME_IntubateStart": "ACME_skillIntubation",
            "ACME_Extubate": "ACME_skillIntubation",
            "ACME_OpenAirwayView": "ACME_skillIntubation",
            "ACME_ConnectETVent": "ACME_skillVentilator",
            "ACME_DisconnectETVent": "ACME_skillVentilator",
            "ACME_VentOpenPatient": "ACME_skillVentilator",
            "ACME_SyringeKit_DrawPatient": "ACME_skillMedicationPreparation",
            "ACME_PushDoseEpi": "ACME_skillMedicationBolus",
            "ACME_OsmoBolus_HTS": "ACME_skillMedicationBolus",
        }
        for action, setting in required.items():
            block = re.search(r'^    class ' + action + r'\s*:[^{]+\{(.*?)^    };', config, re.M | re.S)
            self.assertIsNotNone(block, action)
            self.assertIn(f'medicRequired = "{setting}";', block[1])
            self.assertIn(f"'{action}'] call ACME_fnc_procedureActionAllowed", block[1])
        adjust = re.search(r'^    class ACME_AdjustThoracostomy\s*:[^{]+\{(.*?)^    };', config, re.M | re.S)[1]
        self.assertIn('medicRequired = 0;', adjust)
        self.assertIn('call ACME_fnc_thoraCanOpen', adjust)

    def test_new_settings_register_once_globally_and_native_tiers_are_not_duplicated(self):
        settings = read_source(ROOT / "XEH_preInit.sqf") + read_source(ROOT / "XEH_settings.hpp")
        for key in ("ACME_skillChestTube", "ACME_skillThoracostomySeal", "ACME_skillIntubation",
                    "ACME_skillVentilator", "ACME_skillMedicationPreparation", "ACME_skillMedicationBolus"):
            blocks = re.findall(r'\["' + key + r'", "LIST"[^\n]+', settings)
            self.assertEqual(len(blocks), 1, key)
            self.assertIn('[[0, 1, 2], ["Everyone", "Medic", "Doctor"]', blocks[0])
            self.assertIn('], 1, {}]', blocks[0])
        for native in ("ACM_breathing_allowThoracostomy", "ACM_breathing_allowNCD"):
            self.assertNotRegex(settings, r'\[\s*"' + native + r'"\s*,\s*"LIST"')
        self.assertIn('"Allow Surgical Kit use for Thoracostomy"', settings)

    def test_native_tiers_reused_and_doctor_tube_default_preserved(self):
        text = source("procedureAllowed")
        self.assertIn('["ACME_allowThoracostomy", "ACM_breathing_allowThoracostomy", 1]', text)
        self.assertIn('["ACME_allowNCD", "ACM_breathing_allowNCD", 1]', text)
        self.assertIn('["ACME_allowChestTubes", "ACME_skillChestTube", 2]', text)
        self.assertIn('["", "ACME_skillThoracostomySeal", 1]', text)
        self.assertIn('[_medic, _skill] call ace_medical_treatment_fnc_isMedic', text)
        self.assertIn('if !(_skill in [0, 1, 2]) exitWith {false}', text)

    def test_disabling_new_starts_preserves_aftercare_without_disabling_tier_checks(self):
        text = source("procedureAllowed")
        self.assertIn('if (!_existing && {_enabledKey != ""}', text)
        self.assertGreater(text.index('call ace_medical_treatment_fnc_isMedic'), text.index('if (!_existing'))
        actions = source("procedureActionAllowed")
        for action in ("ACME_Extubate", "ACME_OpenAirwayView", "ACME_DisconnectETVent",
                       "ACME_ResealChestTube", "ACME_CloseIncision"):
            self.assertIn(f'case "{action}"', actions)
        self.assertIn('["intubation", true]', actions)
        self.assertIn('["ventilator", true]', actions)
        self.assertIn('["thoracostomy", true]', actions)

    def test_lower_tier_seal_provider_has_independent_existing_wound_admission(self):
        text = source("thoraCanOpen")
        self.assertIn('[_medic, "thoracostomySeal", true]', text)
        self.assertIn('ACME_thora_incision_left', text)
        self.assertIn('ACME_thora_incision_right', text)
        self.assertLess(text.index('if (_existing'), text.index('call ACME_fnc_thoraKitItem'))
        # A stricter new-incision or tube threshold cannot be inherited by Adjust.
        self.assertNotIn('case "ACME_AdjustThoracostomy"', source("procedureActionAllowed"))

    def test_shared_surgical_kit_is_optional_reusable_and_disposable_is_preferred(self):
        thora_access_probe()
        kit = source("thoraKitItem")
        self.assertLess(kit.index('exitWith {"ACM_ThoracostomyKit"}'), kit.index('ACME_thora_allowSurgicalKit'))
        self.assertIn('getVariable ["ACME_thora_allowSurgicalKit", false]', kit)
        self.assertEqual(kit.count('call ace_medical_treatment_fnc_hasItem'), 2)
        click = source("thoraMouseDown")
        begin = click.index('private _usedKit = _kit == "ACM_ThoracostomyKit"')
        end = click.index('[_patient, _side, "open", "finger"] call ACME_fnc_thoraSideStateCommit', begin)
        debit = click[begin:end]
        self.assertIn('if (_usedKit) then', debit)
        self.assertIn('call ace_medical_treatment_fnc_useItem', debit)
        self.assertIn('if (_kit == "") exitWith {false}', debit)
        self.assertNotIn('removeItem "ACE_surgicalKit"', click)

    def test_lost_kit_or_permission_blocks_inflight_surgical_commit(self):
        for name in ("thoraSelectTool", "thoraMouseDown", "thoraMouseUp"):
            text = source(name)
            self.assertIn('"thoracostomy"] call ACME_fnc_procedureAllowed', text)
            self.assertIn('call ACME_fnc_thoraKitItem', text)
        release = source("thoraMouseUp")
        self.assertLess(release.index('call ACME_fnc_procedureAllowed'),
                        release.index('[_patient, _side, "incision", [_start, _angle, _lenCm]] call ACME_fnc_thoraSideStateCommit'))

    def test_tube_gate_and_verified_consumption_precede_patient_projection(self):
        text = source("thoraMouseDown")
        start = text.index('private _tubeMedic')
        tube = text[start:]
        self.assertLess(tube.index('call ACME_fnc_thoraClosureMode'), tube.index('removeItem "ACM_ChestTubeKit"'))
        self.assertLess(tube.index('>= _tubeBefore) exitWith'), tube.index('[_patient, _side, "tube", true] call ACME_fnc_thoraSideStateCommit'))
        self.assertIn('Thoracostomy_State", 0]) != 2', tube)

    def test_ncd_rechecks_at_authoritative_acceptance_before_snapshot_changes(self):
        request = source("chestSealRequest")
        self.assertLess(request.index('call ACME_fnc_procedureAllowed'), request.index('_medic removeItem'))
        server = source("chestSealEdit")
        self.assertLess(server.index('call ACME_fnc_procedureAllowed'), server.index('switch (_op)'))
        self.assertIn('ACME_CS_editResults set', server)
        self.assertIn('"ACME_CS_ack"', server)

    def test_stale_menu_and_dead_bypass_both_recheck_access(self):
        for name in ("treatment", "canTreatCached"):
            text = read_source(ROOT / "overrides" / f"fn_{name}.sqf")
            self.assertIn('call ACME_fnc_procedureActionAllowed', text)
        cached = read_source(ROOT / "overrides/fn_canTreatCached.sqf")
        self.assertLess(cached.index('call ACME_fnc_procedureActionAllowed'), cached.index('!alive _target'))

    def test_intubation_enable_changes_do_not_strand_a_passed_tube(self):
        self.assertIn('[_medic, "intubation", _existingTube] call ACME_fnc_procedureAllowed', source("laryngoPassTube"))
        self.assertIn('!_existingTube', source("laryngoPassTube"))
        self.assertIn('getVariable ["ACME_ETT_Inserted", false]', source("laryngoCuffDone"))
        self.assertIn('|| {uiNamespace getVariable ["ACME_laryngo_tubePassed", false]}', source("laryngoCuffDone"))
        self.assertIn('[_medic, "intubation", true]', source("laryngoExtubate"))

    def test_flashlight_rebuild_restores_exact_committed_passage_before_ticking(self):
        producer = source("installLightKey")
        producer = producer[producer.index('uiNamespace setVariable ["ACME_laryngo_snap", ['):]
        fields = re.findall(r'uiNamespace getVariable \["(ACME_laryngo_[^"]+)"', producer)
        self.assertEqual(len(fields), 15)
        self.assertEqual(fields[14], 'ACME_laryngo_tubePassed')
        init = source("laryngoInit")
        restore = init.index('setVariable ["ACME_laryngo_tubePassed", _sPassed]')
        self.assertIn('["_sPassed", false, [false]]', init)
        self.assertGreater(restore, init.index('setVariable ["ACME_laryngo_tubePassed", false]'))
        self.assertLess(restore, init.index('private _pfh ='))
        # A legacy snapshot remains readable and conservatively defaults false;
        # the implementation never substitutes mere insertion depth for success.
        self.assertIn('if ((count _snap) >= 14)', init)
        self.assertNotRegex(init, r'_sPassed\s*=\s*.*_sDepth')

    def test_bolus_callbacks_recheck_before_drug_or_item_changes(self):
        for name, marker in (("administerPushDoseEpi", 'call ACME_fnc_epinephrinePushStored'),
                             ("tbiOsmoBolus", 'call ACME_fnc_tbiApplyOsmotherapy')):
            text = source(name)
            self.assertLess(text.index('call ACME_fnc_procedureAllowed'), text.index(marker))

    def test_consumable_aftercare_and_bolus_debit_once_after_final_access_check(self):
        config = read_source(ROOT / "config.cpp")
        for action in ("ACME_OsmoBolus_HTS", "ACME_DrainFluid_SuctionBag"):
            block = re.search(r'^    class ' + action + r'\s*:[^{]+\{(.*?)^    };', config, re.M | re.S)[1]
            self.assertIn('consumeItem = 0;', block)
        for name in ("tbiOsmoBolus", "thoraAftercare"):
            text = source(name)
            self.assertEqual(text.count('call ace_medical_treatment_fnc_useItem'), 1)
            self.assertNotIn('removeItem', text)
            self.assertLess(text.index('call ACME_fnc_procedureAllowed'), text.index('call ace_medical_treatment_fnc_useItem'))


if __name__ == "__main__":
    unittest.main()
