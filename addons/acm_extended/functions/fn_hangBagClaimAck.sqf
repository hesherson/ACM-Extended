// Patient-owner reply. Delayed acceptance cannot animate a cancelled/newer provider episode.
params ["_patient", "_medic", "_episode", "_accepted", "_epoch", "_providerOwner", "_leaseUntil", ["_sequence", -1, [0]]];
if (isNull _medic || {!local _medic}) exitWith {};
private _same = (_medic getVariable ["ACME_hang_Start", -2]) == _episode
    && {(_medic getVariable ["ACME_hang_Patient", objNull]) isEqualTo _patient};
if (!_same || {!(_medic getVariable ["ACME_hang_Active", false])}) exitWith {
    if (_accepted) then {[_patient, "hangBagRelease", [_medic, _episode, 1, _epoch, _providerOwner]] call ACME_fnc_ownerDispatch;};
};
// Replies from older renewal requests must not cancel or shorten a newer accepted lease.
if (!finite _sequence || {_sequence < 0} || {_sequence <= (_medic getVariable ["ACME_hang_ClaimAckSequence", -1])}) exitWith {};
_medic setVariable ["ACME_hang_ClaimAckSequence", _sequence, false];
if (!_accepted || {_leaseUntil <= serverTime} || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
    || {_providerOwner != clientOwner}
    || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {_epoch != (_medic getVariable ["ACME_hang_ClaimEpoch", -1])}
    || {_patient getVariable ["ACME_clinicalRestoring", false]}
    || {!isNull objectParent _medic}
    || {_medic distance _patient > (missionNamespace getVariable ["ACME_hang_leash", 3])}
    || {(_medic getVariable ["ACME_hang_PlayerBound", false]) && {!(_medic isEqualTo ACE_player)}}
    || {!(missionNamespace getVariable ["ACME_sys_hang", true])}) exitWith {
    [true, _medic] call ACME_fnc_hangBagStop;
};
_medic setVariable ["ACME_hang_ClaimAckAt", (_leaseUntil - 6) max (_medic getVariable ["ACME_hang_ClaimAckAt", 0]), false];
// Renewals/duplicate ACKs never repeat props, input handlers or the raised-bag animation.
if (_medic getVariable ["ACME_hang_Claimed", false]) exitWith {};
_medic setVariable ["ACME_hang_Claimed", true, false];
[_medic, _patient, _medic getVariable ["ACME_hang_Part", ""],
    _medic getVariable ["ACME_hang_FluidType", "saline"]] call ACME_fnc_hangBagActivate;
