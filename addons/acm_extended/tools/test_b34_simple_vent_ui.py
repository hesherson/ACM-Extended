"""Simple ventilator UI mutation boundaries and setup/sensor contracts.

These are source integration checks, not an Arma UI/runtime simulation. They
protect against a stale editor or direct callback changing saved advanced
settings after the server switches Simple mode on.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / "functions" / ("fn_" + name + ".sqf")).read_text()


class SimpleVentUIContracts(unittest.TestCase):
    def test_all_patient_setting_writers_recheck_procedure_tier(self):
        # The init path only seeds absent advanced values and does not edit them.
        for name in ("ventPanelOpen", "ventPanelKnob", "ventPanelLiveEdit",
                     "ventPanelNavClick", "ventPanelListClick"):
            with self.subTest(entry=name):
                text = source(name)
                gate = text.index('[ACE_player, "ventilator", true] call ACME_fnc_procedureAllowed')
                writes = list(re.finditer(r'_[A-Za-z0-9]+ setVariable \[', text))
                self.assertTrue(writes)
                self.assertLess(gate, writes[0].start())
                self.assertIn('exitWith {}', text[gate:gate + 100])

    def test_stale_wheel_edit_flags_clear_before_their_write_branches(self):
        text = source("ventPanelKnob")
        guard = text[text.index('if (_simple) then {'):text.index('// an open alarm window')]
        for flag, reset in (("editingParam", "-1"), ("editingPeep", "false"),
                            ("editingIE", "false"), ("editingFio2", "false")):
            self.assertIn(f'setVariable ["ACME_vent_{flag}", {reset}]', guard)
        self.assertIn('_screen == "alerts"', guard)
        self.assertIn('"ACME_vent_editingAlert", -1]) == 2', guard)
        self.assertIn('setVariable ["ACME_vent_editingAlert", -1]', guard)
        self.assertLess(text.index('if (_simple) then {'), text.index('_tP setVariable'))
        # The pressure alert and RR alarms keep their independent edit paths.
        for field in ("alertPAlert", "alertRRLow", "alertRRHigh"):
            self.assertIn(f'_tA setVariable ["ACME_vent_{field}"', text)

    def test_direct_live_edit_keeps_rr_and_blocks_vt_and_pinsp(self):
        text = source("ventPanelLiveEdit")
        guard = text.index('getVariable ["ACME_vent_simpleMode", false]')
        self.assertIn('ACME_vent_nivMask', text[guard:text.index('switch (_selIdx)')])
        self.assertIn('&& {_selIdx != 0}', text[guard:text.index('switch (_selIdx)')])
        self.assertLess(guard, text.index('switch (_selIdx)'))
        self.assertIn('case 0:', text)
        self.assertIn('_vTgt setVariable ["ACME_vent_bpm", _v, true]', text)
        self.assertIn('"ACME_vent_pinsp"', text)
        self.assertIn('"ACME_vent_vt"', text)
        self.assertIn('_field != "bpm"', source("ventPanelFieldClick"))

    def test_setup_and_subscreen_routes_do_not_commit_advanced_choices(self):
        router = source("ventPanelShowScreen")
        early = router[:router.index('uiNamespace setVariable ["ACME_vent_screen"')]
        self.assertIn('_screen in ["weight", "mode", "interface"]', early)
        self.assertIn('then {"params"} else {"connect"}', early)
        self.assertIn('_screen in ["o2", "ie", "peep"]', early)
        self.assertNotRegex(early, r'_target setVariable')
        nav = source("ventPanelNavClick")
        guard = nav.index('getVariable ["ACME_vent_simpleMode", false]')
        self.assertLess(guard, nav.index('private _commit'))
        self.assertIn('then {"menu"} else {"interface"}', nav)

    def test_connect_and_restart_honor_enable_gate_and_physical_reach(self):
        nav = source("ventPanelNavClick")
        connect = nav[nav.index('case "connect":'):nav.index('case "menu":')]
        restart = nav[nav.index('// START VENT.'):nav.index('case 1: {  // NEW PATIENT.')]
        for text in (connect, restart):
            self.assertIn('[ACE_player, "ventilator"] call ACME_fnc_procedureAllowed', text)
            self.assertIn('(objectParent ACE_player) isNotEqualTo (objectParent _vTgt)', text)
            self.assertIn('(ACE_player distance _vTgt) > _leash', text)
            self.assertLess(text.index('ACME_fnc_procedureAllowed'),
                            text.index('setVariable ["ACME_vent_connected", true'))
        self.assertIn('setVariable ["ACME_vent_connected", false', nav)

    def test_live_toggle_rebuilds_without_writing_advanced_device_settings(self):
        tick = source("ventPanelTick")
        block = tick[tick.index('// Refresh a visible panel'):tick.index('// slow measured BPM')]
        for key in ("editing", "editingParam", "editingAlert", "editingPeep", "editingIE", "editingFio2"):
            self.assertIn(f'setVariable ["ACME_vent_{key}"', block)
        self.assertIn('call ACME_fnc_ventPanelShowScreen', block)
        self.assertNotRegex(block, r'_[A-Za-z0-9]+ setVariable')
        self.assertIn('ACME_fnc_procedureAllowed', tick)
        self.assertIn('[87700] call ACME_fnc_minigameClose', tick)

    def test_automatic_controls_remain_read_only_and_sensors_report_delivery(self):
        refresh = source("ventPanelRefresh")
        self.assertIn('call ACME_fnc_ventEffectiveSettings', refresh)
        self.assertIn('"ACME_vent_vti"} else {"ACME_vent_vte"}', refresh)
        self.assertIn('else {"AUTO"}', refresh)
        self.assertIn('call ACME_fnc_ventMinuteVolume', refresh)
        self.assertIn('_selIdx == 1 && {!_simple}', source("ventPanelLiveRefresh"))
        self.assertIn('_target ctrlEnable (!_automatic)', source("ventPanelListRefresh"))
        self.assertIn('exitWith { "SIMPLE" }', source("ventModeTitle"))
        tick = source("ventPanelTick")
        self.assertIn('_peepC = _effectiveFrame select 5', tick)
        self.assertIn('_ieR = _effectiveFrame select 9', tick)
        self.assertIn('[] call ACME_fnc_ventManualBreath', source("ventPanelStripClick"))


if __name__ == "__main__":
    unittest.main()
