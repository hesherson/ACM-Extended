/* B213: retire only the held worker started by this pressure episode.
 * ACME_dah_gen is shared by every provider action. Incrementing it on every paused DP frame killed the
 * auscultation/chest-access worker which had just taken over. Matching our captured generation is essential.
 */
params ["_medic"];
if (isNull _medic || {!local _medic}) exitWith {};
private _ownGeneration = _medic getVariable ["ACME_DP_HeldGeneration", -1];
if (_ownGeneration >= 0 && {(_medic getVariable ["ACME_dah_gen", 0]) == _ownGeneration}) then {
    _medic setVariable ["ACME_dah_gen", _ownGeneration + 1, false];
};
_medic setVariable ["ACME_DP_HeldGeneration", -1, false];
_medic setVariable ["ACME_DP_InPose", false, false];
_medic setVariable ["ACME_DP_PosePrep", [], false];
_medic setVariable ["ACME_DP_IdleStart", CBA_missionTime, false];
