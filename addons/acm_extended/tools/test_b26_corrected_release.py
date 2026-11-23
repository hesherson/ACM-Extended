from historical_source import read_source, assert_release_identity
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return read_source(ROOT/rel, encoding='utf-8-sig')

class B26Corrected(unittest.TestCase):
    def test_version_pair(self):
        for rel in ('config.cpp','functions/fn_postInit.sqf'):
            assert_release_identity()
    def test_cardiac_vial_uses_acme_class_and_user_picture(self):
        c=read('config.cpp')
        # One item set since the ACME_ rename: the cardiac vial derives from ACME_Vial_Epinephrine and has no ACM_ alias.
        self.assertIn('class ACME_Vial_EpinephrineCardiac: ACME_Vial_Epinephrine', c)
        self.assertIn('vial_epinephrine_1_10000_ca.paa', c)
        self.assertIn('scopeArsenal = 2;', c)
        self.assertNotIn('class ACM_Vial_EpinephrineCardiac', c)
        self.assertTrue((ROOT/'ui/items/vial_epinephrine_1_10000_ca.paa').exists())
    def test_runtime_vial_list_uses_acme_item(self):
        p=read('functions/fn_postInit.sqf')
        self.assertIn('pushBackUnique "ACME_Vial_EpinephrineCardiac"', p)
        self.assertNotIn('ACM_Vial_EpinephrineCardiac', p)  # the alias the old list subtracted no longer exists
    def test_cardiac_vial_stock_is_counted_once(self):
        # The rename turned ACME_+ACM_ cardiac vial counts into ACME_+ACME_, which counts every sealed vial twice.
        once='[_holder, "ACME_Vial_EpinephrineCardiac"] call ACME_fnc_vialItemCount'
        doubled=sorted(p.name for p in (ROOT/'functions').glob('*.sqf') if p.read_text(encoding='utf-8-sig').count(once)>1)
        self.assertEqual(doubled, [], 'cardiac epinephrine vials are summed twice')
    def test_vial_resolver_handles_acme_prefix(self):
        c=read('config.cpp')
        self.assertIn('class vialClass {};', c)
        self.assertIn('class vialMedication {};', c)
        self.assertIn('ACME_Vial_EpinephrineCardiac', read('functions/fn_vialClass.sqf'))
        vm=read('functions/fn_vialMedication.sqf')
        self.assertIn('["_vial_", "_ampule_"]', vm)
        self.assertIn('_class select [_at + count _needle]', vm)
        self.assertNotIn('splitString "_"', vm)
        self.assertIn('ACME_fnc_skMedicationSync', read('overrides/fn_syringeUpdateMedicationList.sqf'))
        self.assertIn('ACME_fnc_vialMedication', read('functions/fn_medicationSourceRows.sqf'))
    def test_user_igel_remove_icon_is_wired(self):
        c=read('config.cpp')
        self.assertIn('ACM_menuIcon = "ACME_iGel_Remove"', c)
        self.assertIn('textureNoShortcut = "\\acm_extended\\ui\\items\\igel_remove_ca.paa"', c)
        self.assertTrue((ROOT/'ui/items/igel_remove_ca.paa').exists())
    def test_iv_changes_still_present(self):
        s=read('functions/fn_ivMinigameTick.sqf')
        self.assertIn('ACME_iv_armEdgeStart', s)
        self.assertIn('ACME_iv_legTiltDeg', s)
        self.assertIn('ACME_iv_ejTiltDeg', s)
        self.assertIn('ACME_iv_needleMotionTiltDeg', s)
    def test_dead_prepared_bag_gates_are_removed(self):
        self.assertNotIn('&& {alive _patient}', read('functions/fn_preparedAttachLocal.sqf').split('private _ok =',1)[1].split(';',1)[0])
        self.assertNotIn('{!alive _patient}', read('functions/fn_infusionRegisterCore.sqf').splitlines()[3])

if __name__=='__main__': unittest.main()
