"""B31 source/geometry contracts. These do not execute Arma's animation graph."""
from historical_source import read_source
from pathlib import Path
import math
import re
import unittest
from test_b29_narc_plunger import expression

ROOT = Path(__file__).resolve().parents[1]
START = read_source(ROOT / 'functions/fn_treatmentPoseStart.sqf')
STOP = read_source(ROOT / 'functions/fn_treatmentPoseStop.sqf')
SYNC = read_source(ROOT / 'functions/fn_treatmentPoseSync.sqf')
CONTINUOUS = read_source(ROOT / 'functions/fn_beginStethoscopeAction.sqf')
CONFIG = read_source(ROOT / 'config.cpp')
PHASE = expression(re.search(r'private _phase = ([^;]+);', START)[1])


def class_block(name):
    match = re.search(r'\bclass ' + re.escape(name) + r'(?:\s*:\s*\w+)?\s*\{', CONFIG)
    start = match.end()
    depth = 1
    for index in range(start, len(CONFIG)):
        depth += (CONFIG[index] == '{') - (CONFIG[index] == '}')
        if not depth:
            return CONFIG[start:index]
    raise AssertionError('Unclosed class: ' + name)


class TreatmentAnimationContracts(unittest.TestCase):
    def test_source_time_is_exact_after_frame_overshoot(self):
        # Evaluate the actual SQF phase expression across source durations and frame
        # rates. A delay-only freeze would stop at the overshot frame instead.
        from test_historical_pose_lifecycle import test_owner_freeze_uses_current_mode_timeline_despite_frame_overshoot
        # The current controller uses per-mode owner-clock timing and seeks before its final freeze.
        for mode,hold in [('roll',2.2),('inspect',2.2),('pulse',.421),('stethoscope',.421)]:
            for duration in (3,12):
                test_owner_freeze_uses_current_mode_timeline_despite_frame_overshoot(mode,hold,duration)

    def test_native_motions_have_work_loops_and_real_crouch_exits(self):
        from test_historical_pose_lifecycle import WRAPPERS, test_work_wrappers_keep_authored_entry_exit_and_weapon_restrictions
        # Finite inspection uses its held frame; junctional and stethoscope wrappers remain looped.
        for args in WRAPPERS:
            test_work_wrappers_keep_authored_entry_exit_and_weapon_restrictions(*args)

    def test_ace_has_no_competing_pose_for_owned_progress_actions(self):
        for action in ('ACME_InspectChest', 'ACME_PackJunctional', 'ACME_WrapJunctional'):
            block = class_block(action)
            for field in ('animationMedic', 'animationMedicProne', 'animationMedicSelf', 'animationMedicSelfProne'):
                self.assertIn(field + ' = "";', block)
        for action, stem in (('ACME_PackJunctional', 'Pack'), ('ACME_WrapJunctional', 'Wrap')):
            block = class_block(action)
            self.assertIn('ACME_fnc_junctional' + stem + 'SfxStart', block)
            self.assertIn('ACME_fnc_junctional' + stem + 'Done', block)
            self.assertEqual(block.count('ACME_fnc_treatmentPoseStop'), 2)

    def test_cancel_between_work_request_and_entry_cancels_pending_move(self):
        # Regress stage1: being in crouch does not mean no work is queued.
        from test_historical_pose_lifecycle import test_matching_stop_clears_its_pending_work_once_and_returns_to_crouch
        for stage in (-1,-2,0,1,2,3):
            test_matching_stop_clears_its_pending_work_once_and_returns_to_crouch(stage)
        self.assertNotIn('call ACME_fnc_animQueue', START + STOP)

    def test_jip_waits_for_atomic_episode_and_retires_unique_hold(self):
        self.assertIn('["ACME_treatmentPoseEpisode", [_epoch, true], true]', START)
        self.assertIn('CBA_fnc_waitUntilAndExecute', SYNC)
        self.assertLess(SYNC.index('CBA_fnc_waitUntilAndExecute'), SYNC.index('["ACME_treatmentPoseRemote", [_epoch, "release"'))
        self.assertIn('local _medic &&', STOP)
        self.assertIn('isEqualTo [_currentEpoch, true]', STOP)
        self.assertIn('[_jip, _medic] call CBA_fnc_removeGlobalEventJIP', START)
        self.assertIn('CBA_fnc_removeGlobalEventJIP', STOP)
        self.assertIn('(_record select 0) > _epoch', SYNC)
        self.assertIn('(_record select 1) == "release"', SYNC)

    def test_fatigue_and_deleted_provider_cleanup_are_episode_scoped(self):
        from test_historical_pose_lifecycle import test_deleted_provider_retires_only_its_handler_jip_and_fatigue_exclusion, test_old_owner_tick_cannot_stop_a_new_treatment_episode
        # Current callback carries entry helpers as well as the episode/exclusion; do not require the old tuple text.
        test_deleted_provider_retires_only_its_handler_jip_and_fatigue_exclusion()
        test_old_owner_tick_cannot_stop_a_new_treatment_episode()

    def test_stethoscope_lifecycle_has_one_pose_owner_and_native_cleanup(self):
        self.assertNotRegex(CONTINUOUS, r'"ACM_GenericContinuous"')
        self.assertNotIn('call ace_common_fnc_doAnimation', CONTINUOUS)
        self.assertIn('ACME_fnc_treatmentPoseStart', CONTINUOUS)
        self.assertIn('ACME_fnc_treatmentPoseStop', CONTINUOUS)
        # Pose retirement is presentation-only and must not cancel a healthy scope dialog.
        self.assertNotIn('_poseEnded', CONTINUOUS)
        self.assertIn('DO NOT include treatmentPoseEpisode here', CONTINUOUS)
        self.assertIn('_enteredVehicle', CONTINUOUS)
        self.assertIn('call _onCancel', CONTINUOUS)
        self.assertIn('CBA_fnc_removeKeyHandler', CONTINUOUS)
        self.assertIn('ACM_core_openMedicalMenu', CONTINUOUS)
        self.assertIn('ACM_core_ContinuousAction_Epoch', CONTINUOUS)
        self.assertIn('[_medic, "stethoscope", _poseEpoch, true] call ACME_fnc_treatmentPoseStop', CONTINUOUS)
        steth = read_source(ROOT / 'overrides/fn_useStethoscope.sqf')
        self.assertIn('call ACME_fnc_beginStethoscopeAction', steth)
        self.assertIn('ace_hearing_fnc_updateHearingProtection', steth)


if __name__ == '__main__':
    unittest.main()
