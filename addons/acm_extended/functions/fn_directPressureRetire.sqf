/* Current-provider-owner cleanup after the originating pressure worker loses locality.
 * Handler IDs, input hints and animation generations belong to the former machine; never touch them here.
 * A delayed retirement cannot clear a new request/episode from this or another provider owner.
 */
params ["_medic", "_patient", "_part", "_token", "_epoch"];
if (isNull _medic || {!local _medic} || {_token == ""}) exitWith {};
if ((_medic getVariable ["ACME_DP_ClaimToken", ""]) != _token
    || {(_medic getVariable ["ACME_DP_ClaimEpoch", -1]) != _epoch}
    || {!((_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient)}
    || {(_medic getVariable ["ACME_DP_Part", ""]) != _part}) exitWith {};
_medic setVariable ["ACME_DP_Active", false, true];
_medic setVariable ["ACME_DP_Patient", objNull, true];
_medic setVariable ["ACME_DP_Part", "", true];
_medic setVariable ["ACME_DP_ClaimToken", "", true];
_medic setVariable ["ACME_DP_ClaimEpoch", -1, true];
_medic setVariable ["ACME_DP_InPose", false, false];
_medic setVariable ["ACME_DP_TreatmentBusy", false, false];
_medic setVariable ["ACME_DP_Paused", false, false];
_medic setVariable ["ACME_DP_Mode", "", false];
