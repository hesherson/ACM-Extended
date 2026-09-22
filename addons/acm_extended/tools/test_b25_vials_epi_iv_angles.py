from historical_source import read_source
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return read_source(ROOT/rel, encoding='utf-8-sig')

class B25Source(unittest.TestCase):
    def test_version_pair(self):
        for rel in ('config.cpp','functions/fn_postInit.sqf'):
            self.assertRegex(read(rel), r'(?:0\.9\.999r-\d+-NA8\.5-B(?:25|26|27|28|29|30|31|32|33|34|35)|1\.0\.100-r(?:2|3|4|5|6|7))')

    def test_vial_session_registered_and_manual_advance_only(self):
        c=read('config.cpp'); s=read('functions/fn_vialSession.sqf')
        self.assertIn('class vialSession {};',c)
        self.assertIn('No automatic rollover occurs',s)
        self.assertIn('_reservedMl >= (_unlocked - 0.0005)',s)
        self.assertIn('_selectedSealed = _selectedSealed + 1',s)
        self.assertIn('["select", _data, _reserved, _d] call ACME_fnc_vialSession',read('functions/fn_skListSelect.sqf'))

    def test_compound_plunger_uses_manual_vial_quota(self):
        s=read('functions/fn_skCompoundBegin.sqf')
        self.assertIn('["limit", _medNow',s)
        self.assertNotIn('[_holderNow,_medNow] call ACME_fnc_infusionVialVolume',s)
        self.assertIn('There is no automatic rollover through inventory',s)

    def test_custom_return_resistance_removed(self):
        self.assertNotIn('ACME_vial_returnRateFracPerSec',read('functions/fn_postInit.sqf'))
        self.assertNotIn('deliberately slower',read('functions/fn_skUiTick.sqf'))
        self.assertNotIn('private _fracR',read('functions/fn_skCompoundBegin.sqf'))

    def test_normal_epi_no_longer_redirected_to_code_epi(self):
        self.assertNotIn('Use the dedicated 1:10,000 epinephrine source for IV/IO boluses',read('overrides/fn_Syringe_Inject.sqf'))
        self.assertNotIn('This is 1:1,000 epinephrine. Select IM',read('functions/fn_skInjectSite.sqf'))
        self.assertNotIn('Use 1:1,000 epinephrine by itself for IM',read('functions/fn_skCompoundDraw.sqf'))
        self.assertIn('class Epinephrine_IV',read('config.cpp'))

    def test_fixed_fifteen_degree_art_uses_smooth_rotation(self):
        s=read('functions/fn_ivMinigameTick.sqf')
        self.assertIn('ACME_iv_armEdgeStart',s)
        self.assertIn('private _artSide = if (_patientLeft) then {"left"} else {"right"};',s)
        self.assertIn('ACME_iv_armEdgeExtraTiltDeg',s)
        self.assertIn('ACME_iv_ejTiltDeg',s)

class B25Reference(unittest.TestCase):
    def test_ten_one_ml_epi_vials_require_ten_explicit_unlocks_for_ten_ml(self):
        cap=1.0; sealed=10; start_open=0.0; selected=1; unlocked=1.0; drawn=0.0
        # First selected vial hard-stops at 1 mL.
        drawn=min(10.0,unlocked)
        self.assertEqual(drawn,1.0)
        # A second vial is available only after a deliberate selection/advance.
        self.assertLess(selected,sealed)
        selected+=1; unlocked=start_open+selected*cap
        drawn=min(10.0,unlocked)
        self.assertEqual(drawn,2.0)

    def test_partial_fifty_ml_vial_reopens_at_remaining_volume(self):
        cap=50.0; opened=40.0; sealed=0
        unlocked=opened if opened>0 else (cap if sealed else 0)
        self.assertEqual(unlocked,40.0)
        draw=min(10.0,unlocked)
        self.assertEqual(opened-draw,30.0)

    def test_arm_reference_is_15_base_with_edge_ramp(self):
        # B26+ intent: arms are authored from a 15-degree base and only add the remaining angle near the edge.
        def extra(span, start=.68):
            return 0 if span <= start else min(1,(span-start)/(1-start))*15
        self.assertEqual(extra(0),0)
        self.assertEqual(extra(.5),0)
        self.assertGreater(extra(.9),0)
        self.assertAlmostEqual(extra(1),15)

if __name__=='__main__': unittest.main()
