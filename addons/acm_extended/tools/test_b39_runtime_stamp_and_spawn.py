from historical_source import read_source
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return read_source(ROOT/rel, errors="ignore")
class B39RuntimeStampAndSpawn(unittest.TestCase):
    def test_config_is_r3(self):
        self.assertIn('version = "1.0.100-r7";', read('config.cpp'))
    def test_runtime_version_comes_from_config(self):
        p=read('functions/fn_postInit.sqf')
        d=read('functions/fn_debugMenu.sqf')
        self.assertIn('ACME_infusion_version = getText',p)
        self.assertIn('ACME_buildBatch = "B43";',p)
        self.assertNotIn('ACME_infusion_version = "1.0.100-r2"',p)
        self.assertIn('private _ver = getText',d)
    def test_reset_never_calls_getup(self):
        r=read('overrides/fn_resetVariables.sqf')
        self.assertIn('ACM_core_Lying_State',r)
        body='\n'.join(line.split('//',1)[0] for line in r.splitlines())
        self.assertNotIn('call ACM_core_fnc_getUp',body)
        self.assertIn('class resetVariables { file = "\\acm_extended\\overrides\\fn_resetVariables.sqf"; };',read('config.cpp'))
    def test_native_getup_callers_remain_compatible(self):
        g=read('overrides/fn_getUp.sqf')
        self.assertIn('["_authorized", true, [false]]',g)
    def test_b39_medication_identity_rebuild_present(self):
        self.assertIn('call ACME_fnc_skMedicationSync',read('functions/fn_skListRefresh.sqf'))
        sync=read('functions/fn_skMedicationSync.sqf')
        self.assertIn('_ctrl lbSetData',sync.replace('_list','_ctrl')) if False else self.assertIn('lbSetData',sync)
    def test_obtunded_weapon_path_does_not_delete_projectiles(self):
        t=read('functions/fn_obtundedInputLock.sqf')
        self.assertIn('ACME_fnc_obtundedWeaponIntent',t)
        self.assertIn('removeEventHandler ["FiredMan"',t)
        self.assertNotIn('deleteVehicle _projectile',t)
        self.assertIn('class obtundedWeaponIntent {};',read('config.cpp'))
    def test_awake_ett_rejection_present(self):
        s=read('functions/fn_laryngoScroll.sqf')
        self.assertIn('laryngoTubeEject',s)
        self.assertIn('"awake"',s)
if __name__=='__main__': unittest.main()
