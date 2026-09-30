// stage 2 of the HPMK: wrap the prepped kit, taking the state from prepped to wrapped. this is where passive
// rewarming begins, because ACME_hpmk_on going true drives fn_hpmktick. wrapped casualties do not receive a
// world blanket object; only a later dropped HPMK uses a collision-free visual anchor. the kit
// was already taken out at prep, so nothing is removed here.
// passive external rewarming retains the body heat of the patient to let a stable patient drift their core temp
// back up, and it does little for an unstable or non-perfusing patient, which is clinically correct, because that
// needs active rewarming.
// _this is the ACE callback [_medic, _patient, _bodyPart].
params ["_medic", "_patient"];
if (!local _patient) exitWith { ["ACME_ownerCommand", [_patient, "hpmkWrap", _this], _patient] call CBA_fnc_targetEvent; };
if (isNull _patient) exitWith {};

private _lyingState = _patient getVariable ["ACM_core_Lying_State", false];
private _isLying = if (_lyingState isEqualType true) then {_lyingState} else {_lyingState > 0};
// Engine death may clear ACE unconscious/lying flags; a corpse is still a valid physical recipient.
private _eligible = !alive _patient || {_patient getVariable ["ACE_isUnconscious", false]} || {_isLying};
if (!_eligible) exitWith {
    private _receiver = _patient getVariable ["ACME_hpmk_provider", _medic];
    [_receiver, _patient, true] call ACME_fnc_hpmkRemove;
};

// HPMK wrapping is state-only. Do not roll, attach, reposition or otherwise physically drive the casualty here.
// On multiplayer servers the old forced roll could hand the ragdoll/animation state between owners while an
// injured unit was intersecting terrain or another object, producing collision damage across the body and even
// bilateral leg fractures. Existing posture is deliberately preserved.
if ((_patient getVariable ["ACME_hpmk_state", ""]) == "wrapped") exitWith {
    ["This patient is already wrapped in an HPMK.", 2, _medic] call ACME_fnc_netNotice;
};

// Kill any legacy attached/networked blanket anchor before committing the wrapped state. Current HPMKs use no
// world object on the casualty, so stale state from an older build must never participate in collision physics.
["ACME_hpmkKillBlanket", [_patient]] call CBA_fnc_serverEvent;

[_patient, "wrapped", true, false] call ACME_fnc_hpmkStateCommit;
_patient setVariable ["ACME_hpmk_lastTickLocal", CBA_missionTime, false];
if (isNil "ACME_hpmk_activePatients") then { ACME_hpmk_activePatients = []; };
if (alive _patient) then {ACME_hpmk_activePatients pushBackUnique _patient;};

["Wrapped in HPMK.", 3, _medic] call ACME_fnc_netNotice;
if (!isNil "ace_medical_treatment_fnc_addToLog") then {
    [_patient, "activity", "Wrapped in NAR HPMK", []] call ace_medical_treatment_fnc_addToLog;
};
