from historical_source import class_body
from backlog_clinical_probes import bvm_with_cpr_probe, reserved_roles_probe
from historical_source import assert_release_consistent
from historical_source import read_source
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return read_source(ROOT/rel, encoding='utf-8-sig')

class B27JunctionalCPRBVM(unittest.TestCase):
    def test_version_pair(self):
        assert_release_consistent()
    def test_junctional_state_writers_still_broadcast(self):
        self.assertRegex(read('functions/fn_junctionalInflict.sqf'),r'setVariable\s*\[format\s*\["ACME_Junc_%1".*?true\]')
        owner=read('functions/fn_ownerDispatch.sqf')
        for operation,next_operation,state in [('junctionalPackDone','junctionalWrapDone','packed'),('junctionalWrapDone','junctionalInflict','wrapped')]:
            entry=read('functions/fn_'+operation+'.sqf')
            self.assertIn(f'[_patient, "{operation}", [_medic, _p]] call ACME_fnc_ownerDispatch;',entry)
            block=owner.split(f'case "{operation}":',1)[1].split(f'case "{next_operation}":',1)[0]
            self.assertIn(f'_patient setVariable [format ["ACME_Junc_%1", _part], "{state}", true];',block)
            self.assertNotIn('_patient setVariable',entry)
    def test_junctional_gui_sync_is_local_only(self):
        s=read('functions/fn_junctionalGuiSyncTick.sqf')
        self.assertIn('ace_medical_gui_menuDisplay',s)
        self.assertIn('ace_medical_gui_fnc_updateBodyImage',s)
        self.assertIn('ace_medical_gui_fnc_updateInjuryList',s)
        for bad in ('targetEvent','globalEvent','serverEvent','remoteExec','publicVariable','_target setVariable','_patient setVariable'):
            self.assertNotIn(bad,s)
    def test_junctional_gui_sync_is_bounded(self):
        p=read('functions/fn_postInit.sqf')
        self.assertIn('[{call ACME_fnc_junctionalGuiSyncTick}, 0.2, []] call CBA_fnc_addPerFrameHandler;',p)
    def test_cpr_action_no_longer_blocked_by_bvm(self):
        c=read('../circulation/ACE_Medical_Treatment_Actions.hpp')
        block=class_body(c,'CPR')
        self.assertIn('condition = QUOTE([ARR_2(_medic,_patient)] call ACEFUNC(medical_treatment,canCPR));',block)
        self.assertIn('callbackSuccess = QUOTE([ARR_2(_medic,_patient)] call FUNC(beginCPR));',block)
        self.assertNotIn('bvmActive',block)
    def test_begin_cpr_override_registered(self):
        prep=read('../circulation/XEH_PREP.hpp')
        self.assertEqual(prep.count('PREP(beginCPR);'),1)
        s=read('overrides/fn_beginCPR.sqf')
        preflight=s[:s.index('private _oldSession')]
        self.assertIn('call FUNC(cprSessionValid)',preflight)
        self.assertNotIn('bvmActive',preflight)
        self.assertNotIn('BVM_provider',preflight)
    def test_bvm_can_run_during_cpr(self):
        bvm_with_cpr_probe()
    def test_one_provider_per_role_remains(self):
        reserved_roles_probe()
    def test_cross_provider_role_vars_still_networked(self):
        b=read('overrides/fn_useBVM.sqf');c=read('overrides/fn_beginCPR.sqf')
        self.assertIn('_patient setVariable [QGVAR(BVM_Medic), _medic, true];',b)
        self.assertIn("_t setVariable ['ACM_breathing_BVM_provider', ACE_player, true]",b)
        self.assertIn('_patient setVariable [QACEGVAR(medical,CPR_provider), _medic, true];',c)
        self.assertIn('_patient setVariable [QGVAR(CPR_Medic), _medic, true];',c)

if __name__=='__main__': unittest.main()
