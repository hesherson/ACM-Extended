"""September 22 preservation audit. Snapshot checks protect the fixes lost by the merge.

These are source/structural regression checks, not an Arma multiplayer simulation.
The dated snapshot checks intentionally require review when protected behavior changes.
"""
from pathlib import Path
import hashlib
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")

PROTECTED = {'addons/acm_extended/functions/fn_beginStethoscopeAction.sqf': '47419e5817f88d8ce338a1a4ef158513ba40f4da26d76d0e4c27bd5be0b2a757', 'addons/acm_extended/functions/fn_blastApply.sqf': '68749e75d73f191076f01da6ad20414d8a6129420a8016a60e68f3b7671fbbf2', 'addons/acm_extended/functions/fn_chestAccessVestAcquire.sqf': '1e038a885e12ffe009ff1ee98e3106753c57aeda6460b8bc61311fc70c29d780', 'addons/acm_extended/functions/fn_chestAccessVestEvent.sqf': '0609ad694ef14bf4d27d54d27ea5b9002e8bffb409c3cddbf62ee7ec424ddaa6', 'addons/acm_extended/functions/fn_chestAccessVestPark.sqf': '533809a58ba02625b98947465c89d6d0eba4ecca7971fc09f474ab99e38cf10b', 'addons/acm_extended/functions/fn_chestAccessVestProvider.sqf': '2e7c054dcf5dc3efe27aee9c66bf681377832373403d89bce1197adf1a5792bd', 'addons/acm_extended/functions/fn_chestAccessVestRestore.sqf': 'ff46adc33d8ff12cbe73c988acdad67eb7f4be5548bed73e6c454676f1b52f28', 'addons/acm_extended/functions/fn_chestSealApply.sqf': 'bf5ac1fc51b675db8c07cd902f97d437e1cfc2dfbf0d23d7190d8b57d3757dc5', 'addons/acm_extended/functions/fn_chestSealBurp.sqf': '6fcd96fa824f7fbe4deaa218e78d27d80e59f60a5c6189cc9c94998d2087bc70', 'addons/acm_extended/functions/fn_chestSealClose.sqf': '18ead4f88f0c5a4caa7a2f57ac05262127de0d3e7ebaa8291172024fd6e0f719', 'addons/acm_extended/functions/fn_chestSealFlip.sqf': '317b429a37a41869111449b3fe6bd3f6b65be5ebdca76f39e53ac1b8b564bfd1', 'addons/acm_extended/functions/fn_chestSealFlipTick.sqf': '74c8af15c76ff0fadf367627a6a746633cb82d1633b0ea99419cd47cef5ec702', 'addons/acm_extended/functions/fn_chestSealOpen.sqf': '8fe4339c35f63e482d2e1822e8d0ed2c3d95f5c52a8a566b24b01c662225edc9', 'addons/acm_extended/functions/fn_chestSealParkCarrier.sqf': 'e9f6439258a72331d8ec45d349f872ffc74a7f9cb6e9fe4e08287fbc6e03b046', 'addons/acm_extended/functions/fn_chestSealPatientBegin.sqf': '9a759b9164594da6e4fc7bddc9f5027bf046b97cbfff6852ce52b3b86677386b', 'addons/acm_extended/functions/fn_chestSealPatientEnd.sqf': '50676b1cd73e6f3e8b3b6d725aae765d396d71d545a3e164ea5ce5d3ae548152', 'addons/acm_extended/functions/fn_chestSealProviderHoldStart.sqf': '6f0f9010b3baf04c80713f6358173faf1cb8663c0802c46083e3020f3a01c23c', 'addons/acm_extended/functions/fn_headElevRestAnim.sqf': '3f816acb5c6e6c3f2c7d194f65555ba5aa76012ad1fb979f77ec23c864b69031', 'addons/acm_extended/functions/fn_headElevResume.sqf': '9cb6d33b55a583e655ae981744b33936f816aa6c5f643f5f5c5be4190e8b65c4', 'addons/acm_extended/functions/fn_headElevSuspend.sqf': '3e80f58bc561c74d1df272b7d478a2010a7e8b7d1787f124a38f588ac6cc2886', 'addons/acm_extended/functions/fn_headElevTryResume.sqf': 'aec630fcf32cd65211ad3acfc07438147f6a90f68c387938e8fee35f0054b00a', 'addons/acm_extended/functions/fn_headElevateStart.sqf': '3fc226020d4ec3a900802438aeb583c7e99a505fd8aec6919a48e051b23a2309', 'addons/acm_extended/functions/fn_headElevateStop.sqf': 'bbec41dfd8a1a2aa18dca1c94cec760d3cbd48463881619e77051e263e38c09b', 'addons/acm_extended/functions/fn_initBloodStorageRuntime.sqf': 'e46a74bf8da0b696769d7cf77086a984ed5a5efab1c43db9f65e82c4a1b16c79', 'addons/acm_extended/functions/fn_initChestSealProcedureRuntime.sqf': 'b5692741af8f912e8ba5254a65676d5593c8f5f32dd16268850f97a683e7812a', 'addons/acm_extended/functions/fn_initForkStartupRuntime.sqf': 'c599b2fa0258dbf51eab3d8ff37c2565f3a8033496af496cd18089a39263c381', 'addons/acm_extended/functions/fn_initHangBagRuntime.sqf': '98088b1c60ece165bf161183a2af3fefaaec33c6b39bb7c9f47cb4ebf82d9321', 'addons/acm_extended/functions/fn_ivMinigameInit.sqf': '028e8cffc0ad5506890602835c5fe05bd3db1c68db4185085eb3090554094b42', 'addons/acm_extended/functions/fn_ivTrayHover.sqf': '5d9801c1c25ecbe98855b2d53088cbf9e5df79539b9877f82f3d3c9f479b044e', 'addons/acm_extended/functions/fn_medicAnimationPrep.sqf': '8ec6effab7e90d973a16331ad9cd441de0f7e1f7faf6d26a894f9e9945268175', 'addons/acm_extended/functions/fn_ownerDispatch.sqf': 'e66c12ca9653fdf223a422fcde404561b7ff132aa15e49cf01062a325d24ed96', 'addons/acm_extended/functions/fn_registerChestAccessVestRuntime.sqf': 'df6587164beca9783ead235adaddea8a19e8c4d5bccf6ced7bdf1a277fdd37e0', 'addons/acm_extended/functions/fn_registerTransfusionUiRuntime.sqf': 'e52c1ea98eebe48a1c2ba2c0b44c035ab455f771af8462c488705d584c25d6d0', 'addons/acm_extended/functions/fn_rollProviderStart.sqf': '63bb9cf397da2d4b28f548733fe855036c1c02fc6e4d4ce8eba07a47b618ffb2', 'addons/acm_extended/functions/fn_stethoscopeClose.sqf': 'e6686c43b3aec1a3292274c77dd43065e9860d6ca05568dae8ffa2e6e40c2bf7', 'addons/acm_extended/functions/fn_stethoscopeEntryFlip.sqf': '0be32893eba272cca260994538c32c427f637f8eea2244ec386f0b78e115c61b', 'addons/acm_extended/functions/fn_stethoscopeEntryFlipTick.sqf': '3a0b0229f2d52e0bc6e7feb67a2769c7f57c3abce439a6cda91e875b6b612e2c', 'addons/acm_extended/functions/fn_stethoscopeFlipTick.sqf': '8bd2601e1eef825eff4212e89a0a18ca659964fa299a83eb70b3e4b93385bde7', 'addons/acm_extended/functions/fn_thoraOpen.sqf': '2c101784f0f5fcb875696de4f679dc9fdc07501433f1da7152caf35e386ddd02', 'addons/acm_extended/functions/fn_transientStateReconcile.sqf': '41b320be637cdbebc3202c92a2c2088e1517e07c9aa6a4f1a3b9d5596345e658', 'addons/acm_extended/functions/fn_treatmentPoseStart.sqf': 'a0051b370d90ec845d18f7792e3d9c720ed4a031e59bbe87cead4b772ebc51f5', 'addons/acm_extended/functions/fn_treatmentPoseStop.sqf': '65db40b04b8742297119271cfcc787e15439d159853a4c03c612689745e40bae', 'addons/acm_extended/functions/fn_updateJunctionalImage.sqf': 'c4b1efc3b72e6621dfcaa23fa1aae6bf17e40836e0dc20b131453315146f5731', 'addons/acm_extended/functions/fn_updateTransfusionControls.sqf': '832bbfa59e386b0b5fd11dfbf471077c1568cb1817eedb00a7c2b1bd904b7480', 'addons/acm_extended/tools/test_iv_ui_followup_patch.py': '7079c31de55c6d36c6923c6a3e0553194654a2541e7311259195925a549b3b18', 'addons/acm_extended/tools/test_seizure_gesture_unification.py': 'efb5fbd303e7be4a08f3889d52c5ff378f288f5cc41d8c8383da1cab08a440b1', 'addons/airway/functions/fnc_beginHeadTiltChinLift.sqf': 'cfa24285f82688bdb97076e96af4bf879842b45339c6b88d65f137acfb91915e', 'addons/airway/functions/fnc_establishSurgicalAirway.sqf': '390a5693ef91cff1a06394ad39652ee9780147fcf321b4377a462cf4e2f0fd6a', 'addons/breathing/functions/fnc_useStethoscope.sqf': 'f8474c55110d2b9089059f8fd5aff890441363467e9c4f5e1e3ef0218924f67e', 'addons/circulation/functions/fnc_getBloodVolumeChange.sqf': '775efc92f8b29232ecb811a5d8645949603378641d40c048d2083dea8145dab8', 'addons/circulation/functions/fnc_openTransfusionMenu.sqf': 'e917c654ec6443704abb0abb84b883f955fe079d5015077c7d86934253c9e453', 'addons/core/functions/fnc_beginContinuousAction.sqf': '7c8a9b9aee9c0fa15150009293663c5ec748b8b709db64277b4fff7598e6b9e7', 'addons/core/overrides/fnc_treatment.sqf': '90a3ce87d43dde2c1d5b60063120e49e88fd16ca1ab6e9da20d07e535fd7e1dd', 'addons/gui/overrides/fnc_updateActions.sqf': '5c9bca1fcb0d5ed1b28a4e74692c75e4c58c2705e12bdb06a2aa7a8dcfb55aa3', 'addons/gui/overrides/fnc_updateInjuryList.sqf': 'db4bf5db97db8f66dc109a5c0e08663de246c50031de3d73b880769bcda0bb4f', 'tools/test_fork_phase150_flip_cancel.py': 'c2d67e025b43709396f6ff1aa53d5cec5fc60c5084a3406cf5649f81cb6f1e36', 'tools/test_fork_phase151_junctional_chest_workspace.py': 'edbf926f88c32a1cea1b3d4597e0bfbd32b2e058e987aacacbfb2778b46bba77', 'tools/test_fork_phase155_blood_flow_policy.py': '271d14672ef59cddba3bfbf60d5672046faef10f7fc6b6d622897c530452f944', 'tools/test_fork_phase160_chest_animation_rollback.py': 'dc0a2e914b3cb30bdc0bdd9326c0837791fb663abb2979fc92984722315b4b35', 'tools/test_fork_phase161_medical_ui_performance.py': 'c205de49a443f3e146fa960e13abd7191ff899d25a45c865916addbd02fb046a', 'tools/test_fork_phase162_wake_state_reconciliation.py': '01700265acdf6e177a65238d97c368a4359df19a547ce73c6f2e62765479b80c', 'tools/test_fork_phase163_acm_continuous_dialog_lifecycle.py': '6b65e3e3db434c83568b1195ce2480c8c51557e363bb508f6684e40a441ea528', 'tools/test_fork_phase164_chest_access_animation_flow.py': '675ce38dc82e0e64b6f1aaf0a57d5bbcfb3bb6a27c3365120758a0d36da73334', 'tools/test_fork_phase164_chest_animation_contract.py': '28e147d76e8d484ff294f44bef871503113497758637b2eea1ef20462baec044', 'tools/test_fork_phase165_airway_seizure_regressions.py': '9b65b8bae219e7adb85959a39b2ce34b19bb527aaa335b2c98a5d674a79562e2', 'tools/test_fork_phase166_chest_wait_payload_regressions.py': '95e564761e52d1d07b57442ae28a82d313a3e7308220221542a284f03dd1f214', 'tools/test_fork_phase167_chest_minigame_animation_contract.py': '362ecc88876882542f53cef844e6ec1fac616b46da3ba6c49dcdeb5930ab7dc7', 'tools/test_fork_phase168_supine_patient_invariant.py': 'a9fc8858502f6d7722d83c705e0a58fa0962df508648625957e906dfa5cd7bf7'}

# Reviewed updates to the six affected snapshots only. The original hashes above
# remain as audit provenance; executable regression cases cover each F01-F04 change.
REVIEWED_LIFECYCLE_UPDATES = {
    'addons/acm_extended/functions/fn_initHangBagRuntime.sqf': '177a105a3ff96c73e5999d77ba760eacaad9b36e59a66abffabc3b3a8bd9f61f',  # F04 ACK registration and token-scoped disconnect release
    'addons/acm_extended/functions/fn_ownerDispatch.sqf': '4c25ddb79f17419375bf8891c25d617976cffdc812e705a61ad8ecf0bb7720be',  # F04 reuse explicit owner operations for atomic lease arbitration
    'addons/acm_extended/functions/fn_stethoscopeClose.sqf': '66c50d484cdc6391191b90a6cb710a8fea846c26b780dc1f6cf1c7402d3705ae',  # F03 capture flip state before reset
    'addons/acm_extended/functions/fn_transientStateReconcile.sqf': '33162edbc565e192dbc431e5d992c1f1183920fcfeec21ed388ab316c9fc6df0',  # F04 protect unexpired claim before Active replicates
    'addons/airway/functions/fnc_establishSurgicalAirway.sqf': '20ac5b962ac042cb11d3da59ce86456af02e15f2677ae21750ba3efbdcb3e2da',  # F01 acquire surgical reservation only after accepted startup
    'addons/core/functions/fnc_beginContinuousAction.sqf': '9a93184b753ba68755847774e3a06ffaa553556d919bb42f887639b3749ac2f8',  # F02 player-bound cancellation; AI policy and dialog grace preserved
}
PROTECTED.update(REVIEWED_LIFECYCLE_UPDATES)

# AW reviewed update: provider acquisition failure may no longer bypass the authored
# medic4 gate and roll the casualty directly from the Flip button handler.
REVIEWED_AW_UPDATES = {
    'addons/acm_extended/functions/fn_chestSealFlip.sqf': '854017266106f8763a77a15350c7a70d70a2960fc9d31dba7f57a5e37ee484ae',
    'tools/test_fork_phase167_chest_minigame_animation_contract.py': '7185c7d14f33d92322d08ce9d7271f7593541e23b274207b136cd66e5f3a00f9',
}
PROTECTED.update(REVIEWED_AW_UPDATES)

@pytest.mark.parametrize("path,expected", sorted(PROTECTED.items()))
def test_prior_fix_restored_without_rewrite(path, expected):
    data = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(data).hexdigest() == expected, path

def test_wake_request_does_not_start_a_second_repair_timer():
    s = read("addons/core/functions/fnc_requestWake.sqf")
    assert "CBA_fnc_localEvent" in s
    assert "FUNC(reconcileWake)" in s
    assert "call ACEFUNC(medical_status,setUnconsciousState)" not in s
    assert "CBA_fnc_waitAndExecute" not in s
    assert '0.15' not in s

def test_repair_refuses_unknown_and_fatal_machine_states():
    s = read("addons/core/functions/fnc_reconcileWake.sqf")
    gate = s.index('if !(_state in ["Default", "Injured", "Unconscious"]) exitWith {false};')
    assert s.index("FUNC(canWake)") < gate
    assert gate < s.index("call CBA_statemachine_fnc_manualTransition")
    assert gate < s.index("call ACEFUNC(medical_status,setUnconsciousState)")
    assert '"Unconscious", "Injured"' in s
    assert "isNull _machine" in s
    assert '"ACME_clinicalRestoring"' in s

def test_delayed_wake_is_invalidated_by_a_new_episode_or_owner():
    s = read("addons/core/XEH_postInit.sqf")
    block = s.split('[QACEGVAR(medical,WakeUp), {',1)[1].split('[QGVAR(playWakeUpSound)',1)[0]
    for guard in ('"ACME_wakeRepairTicket"', '"ACME_clinicalEpoch"', 'owner _unit != _owner', '"ACME_clinicalRestoring"'):
        assert guard in block
    assert 'FUNC(canWake)' in block and 'FUNC(reconcileWake)' in block
    assert 'call ACEFUNC(medical_status,setUnconsciousState)' not in block
    assert 'ACME_wakeRepairTicket' in read('addons/core/functions/fnc_onUnconscious.sqf')
    assert 'ACME_wakeRepairTicket' in read('addons/acm_extended/functions/fn_ownerInit.sqf')

def test_obtunded_denial_precedes_state_and_physical_writes():
    s=read('addons/acm_extended/functions/fn_obtundedApply.sqf')
    guard=s.index('&& {!([_patient, false, "obtunded"] call ACM_core_fnc_requestWake)}) exitWith')
    assert guard<s.index('[_patient, _on, _manual, _posture, _token, false]')
    assert guard<s.index('detach _patient')
    assert guard<s.index('setUnitPos')
    assert '"ACME_obtunded_transitionToken"' in s[:guard]

def test_paralytic_disable_releases_only_its_own_effects():
    s=read('addons/acm_extended/functions/fn_rocuroniumTick.sqf')
    block=s.split('if !(missionNamespace getVariable ["ACME_sys_paralytic", true]) exitWith {',1)[1].split('private _dose',1)[0]
    for name in ('rocParalysisCommit','rocApneaCommit','rocAwakeParalysisCommit','rocStressStateCommit','requestWake'):
        assert name in block
    for name in ('setUnconsciousState','ace_medical_spo2','ace_medical_bloodVolume'):
        assert name not in block

def test_seizure_sync_and_vehicle_suppression_survive():
    cfg=read('addons/acm_extended/config.cpp')
    owner=read('addons/acm_extended/functions/fn_ownerInit.sqf')
    motion=read('addons/acm_extended/functions/fn_seizureMotion.sqf')
    advance=read('addons/acm_extended/functions/fn_seizureGestureAdvance.sqf')
    sync=read('addons/acm_extended/functions/fn_seizureGestureSync.sqf')
    assert 'class seizureGestureSync {};' in cfg
    assert 'ACME_fnc_seizureGestureSync' in owner
    assert 'ACME_seizure_vehicleVisualSuppressed' in motion
    assert 'ACME_seizureGestureSync' in advance
    for term in ('ACME_roc_paralyzed','ACME_fnc_clinicalEpoch','owner _patient','!alive _patient'):
        assert term in sync

def test_paralysis_stops_gesture_once_without_network_stop_spam():
    roc=read('addons/acm_extended/functions/fn_rocuroniumTick.sqf')
    motion=read('addons/acm_extended/functions/fn_seizureMotion.sqf')
    assert '[_patient, false] call ACME_fnc_seizureMotion;' in roc
    assert 'if !(_endingSession isEqualTo []) then {' in motion
    assert motion.index('if !(_endingSession isEqualTo []) then {') < motion.index('["ACME_seizureGestureSync", [_patient, _endingSession')

def test_masked_seizure_is_not_revealed_by_the_ordinary_injury_list():
    s=read('addons/acm_extended/functions/fn_seizureInjuryEntry.sqf')
    assert s.index('if (_target getVariable ["ACME_roc_paralyzed", false]) exitWith {};') < s.index('switch (_state)')
    assert 'setVariable' not in s
    assert '"MASKED"' in read('addons/acm_extended/functions/fn_debugMenuClinical.sqf')

def test_all_three_new_functions_and_seizure_functions_are_registered_once():
    prep=read('addons/core/XEH_PREP.hpp')
    cfg=read('addons/acm_extended/config.cpp')
    for name in ('canWake','requestWake','reconcileWake'):
        assert prep.count(f'PREP({name});') == 1
    for name in ('sedationActive','seizureControl','seizureGestureSync'):
        assert cfg.count(f'class {name} {{}};') == 1
