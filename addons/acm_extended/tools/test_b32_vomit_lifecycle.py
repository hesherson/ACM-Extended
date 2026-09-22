"""Source-level lifecycle regressions; no claim of executing CBA/Arma here."""
from historical_source import read_source
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return read_source(ROOT / relative, encoding='utf-8-sig')


class NativeVomitLifecycle(unittest.TestCase):
    def test_stale_owner_or_episode_stops_before_any_shared_write(self):
        worker = read('overrides/fn_handleAirwayObstruction_Vomit.sqf')
        tick = worker[worker.index('private _PFH = [{'):]
        retire = tick[:tick.index('private _inRecovery')]
        for guard in ('!local _patient', '_epoch != ([_patient] call ACME_fnc_clinicalEpoch)',
                      'ACME_clinicalRestoring', '!= _idPFH', 'isEqualTo [clientOwner, _epoch]'):
            self.assertIn(guard, retire)
        self.assertIn('[_idPFH] call CBA_fnc_removePerFrameHandler', retire)
        self.assertNotIn('true]', retire)
        self.assertNotIn('ACME_nativeVomitActive', retire)
        self.assertNotIn('playSound3D', retire)
        # A stale handler cannot clear a newer handler's token or ID.
        self.assertIn('getVariable ["ACM_airway_AirwayObstructionVomit_PFH", -1]) == _idPFH', retire)
        self.assertIn('[_patient, _epoch], _patient] call CBA_fnc_targetEvent', worker)

    def test_reset_removes_the_worker_before_state_restore(self):
        reset = read('functions/fn_clinicalReset.sqf')
        begin = reset[reset.index('if (_phase == "begin")'):reset.index('// Physical equipment')]
        self.assertIn('ACME_fnc_clinicalEpoch) + 1, true', begin)
        self.assertIn('"ACM_airway_AirwayObstructionVomit_PFH"', begin)
        self.assertIn('CBA_fnc_removePerFrameHandler', begin)
        self.assertIn('["ACME_nativeVomitWorker", [], false]', begin)
        self.assertIn('["ACME_nativeVomitActive", false, true]', begin)
        restore = read('overrides/fn_deserializeState.sqf')
        self.assertLess(restore.index('call ACME_fnc_clearAllAilments'),
                        restore.index('call ACME_fnc_clinicalRestore'))

    def test_migration_keeps_eligibility_but_never_migrates_handles(self):
        init = read('functions/fn_ownerInit.sqf')
        local = init[init.index('["CAManBase", "Local"'):init.index('["CAManBase", "init"')]
        self.assertIn('"ACM_airway_AirwayObstructionVomit_PFH"', local)
        self.assertIn('["ACME_nativeVomitWorker", [], false]', local)
        self.assertNotIn('ACME_nativeVomitActive', local)
        resume = read('functions/fn_ownerRegister.sqf')
        self.assertIn('if (_patient getVariable ["ACME_nativeVomitActive", false]) then {\n'
                      '    [_patient] call ACM_airway_fnc_handleAirwayObstruction_Vomit;', resume)
        self.assertNotIn('AirwayObstructionVomit_State', resume)
        fields = read('functions/fn_clinicalFields.sqf')
        self.assertTrue('["ACME_nativeVomitActive", "", true]' in fields, 'native worker eligibility must persist/reset through clinicalFields')
        self.assertNotIn('ACME_nativeVomitWorker', fields)

    def test_arrest_pauses_native_cause_without_consuming_contents(self):
        worker = read('overrides/fn_handleAirwayObstruction_Vomit.sqf')
        pause = worker[worker.index('// Paused rather than discarded:'):worker.index('private _medicationEffect')]
        self.assertIn('"ace_medical_inCardiacArrest"', pause)
        self.assertIn('"ACME_roc_paralyzed"', pause)
        self.assertIn('exitWith {};', pause)
        self.assertNotIn('setVariable', pause)
        self.assertNotIn('playSound3D', pause)
        self.assertIn('if (_keepAirwayIntact || _gracePeriod) exitWith {};', pause)
        self.assertIn('((0.4 * ACM_airway_airwayObstructionVomitChance) + _medicationEffect)', worker)
        self.assertIn('((_vomitCount - 1) max 0)', worker)
        self.assertIn('}, (10 + (random 10)), [_patient, _epoch]]', worker)


if __name__ == '__main__':
    unittest.main()
