/* Fresh-body initialization is one owner transaction, never a delayed full heal.
 * Retries retain their issue time. A reset/restore already applied to this life,
 * or a late request, must not erase damage or treatment acquired after spawning.
 */
if (canSuspend) exitWith {
    private _result = false;
    isNil {_result = _this call ACME_fnc_respawnClinicalReset;};
    _result
};
params [["_newUnit", objNull, [objNull]], ["_issuedAt", -1, [0]]];
if (isNull _newUnit || {!alive _newUnit} || {!(_newUnit isKindOf "CAManBase")}) exitWith {false};
if (!finite _issuedAt || {_issuedAt < 0}) exitWith {false};
if (!local _newUnit) exitWith {
    [_newUnit, "respawnClinicalReset", [_newUnit, _issuedAt]] call ACME_fnc_ownerDispatch;
    false
};
if (_newUnit getVariable ["ACME_respawnResetComplete", false]) exitWith {true};
// The epoch is advanced before every hard reset/restore. Do not replay a new-life
// reset over a body which has already passed that boundary, even before its
// separate completion flag reaches the next owner.
if (([_newUnit] call ACME_fnc_clinicalEpoch) > 0) exitWith {
    _newUnit setVariable ["ACME_respawnResetComplete", true, true];
    true
};
private _age = serverTime - _issuedAt;
if (!finite _age || {_age < -2} || {_age > 3}) exitWith {false};
// Zeus, mission initializers and damage scripts may already have begun this
// new life before the first owner command arrives. Preserve that clinical
// work instead of applying a late baseline heal over it.
private _hasEntries = {
    if (_this isEqualTypeAny [[], createHashMap]) exitWith {count _this > 0};
    true
};
// An explicitly initialized Extended clinical field is also evidence that a
// scenario/restore already owns this life. Runtime clocks, leases and neutral
// registration bookkeeping are excluded by the real persistence registry.
private _extendedInitialized = ((call ACME_fnc_clinicalFields) findIf {
    _x params ["_name", "", "_clear", ["_persist", true]];
    _clear && {_persist} && {(_name find "ACME_") == 0}
        && {_name != "ACME_clinicalEpoch"} && {!isNil {_newUnit getVariable _name}}
}) >= 0;
private _alreadyActive = damage _newUnit > 0
    || {_extendedInitialized}
    || {_newUnit getVariable ["ace_medical_inCardiacArrest", false]}
    || {_newUnit getVariable ["ACE_isUnconscious", false]}
    || {_newUnit getVariable ["ACME_obtunded", false]}
    || {_newUnit getVariable ["ACME_hpmk_on", false]}
    || {_newUnit getVariable ["ACME_nrb_on", false]}
    || {_newUnit getVariable ["ACME_vent_onPatient", false]}
    || {(_newUnit getVariable ["ACM_circulation_Cardiac_RhythmState", 0]) != 0}
    || {(_newUnit getVariable ["ACM_breathing_Pneumothorax_State", 0]) > 0}
    || {_newUnit getVariable ["ACM_breathing_TensionPneumothorax_State", false]}
    || {_newUnit getVariable ["ACM_breathing_ChestInjury_State", false]}
    || {_newUnit getVariable ["ACM_airway_AirwayCollapse_State", false]}
    || {(_newUnit getVariable ["ACM_airway_AirwayObstructionVomit_State", 0]) > 0}
    || {(_newUnit getVariable ["ACM_airway_AirwayObstructionBlood_State", 0]) > 0}
    || {_newUnit getVariable ["ACM_circulation_isPerformingCPR", false]}
    || {(_newUnit getVariable ["ACME_resusPending", []]) call _hasEntries}
    || {(_newUnit getVariable ["ACME_resusToken_cpr", []]) call _hasEntries}
    || {(_newUnit getVariable ["ACME_resusToken_bvm", []]) call _hasEntries}
    || {(_newUnit getVariable ["ACM_circulation_IV_Bags", createHashMap]) call _hasEntries}
    || {(_newUnit getVariable ["ace_medical_medications", []]) call _hasEntries}
    || {(_newUnit getVariable ["ace_medical_openWounds", createHashMap]) call _hasEntries}
    || {(_newUnit getVariable ["ace_medical_bandagedWounds", createHashMap]) call _hasEntries};
if (_alreadyActive) exitWith {
    _newUnit setVariable ["ACME_respawnResetComplete", true, true];
    true
};
_newUnit setVariable ["ACME_respawnResetComplete", true, true];
[_newUnit] call ACME_fnc_clearAllAilments;
[_newUnit, false, false, "", -1, true] call ACME_fnc_obtundedStateCommit;
_newUnit setVariable ["ACME_obtunded_forcedBack", false, true];
[_newUnit, 0, true, false] call ACME_fnc_rhythmActiveCommit;
_newUnit setVariable ["ACME_rhythm_targetHR", 0, true];
_newUnit setVariable ["ACME_rhythm_bpOffset", 0, true];
_newUnit setVariable ["ACME_rhythm_savedTargetHR", nil, true];
_newUnit setVariable ["ACME_rhythm_obtundUntil", -1, true];
_newUnit setVariable ["ACME_rhythm_torsadesNonPerfusing", nil, true];
_newUnit setVariable ["ACME_rhythm_torsadesPerfusion", nil, true];
_newUnit setVariable ["ACME_rhythm_torsadesArrestRequestAt", nil, false];
[_newUnit, "", -1, true, false] call ACME_fnc_rhythmNativeHoldCommit;
[_newUnit, 0, false, false, false] call ACME_fnc_rhythmNativeHighHRFloorCommit;
[_newUnit, 0, false, false] call ACME_fnc_rhythmNativeShockGraceCommit;
[_newUnit, [["cardiacRhythmState", 0]], true] call ACM_circulation_fnc_setRuntimeState;
[_newUnit, false, false, false, true, false] call ACME_fnc_nrbStateCommit;
[_newUnit, "", true, false] call ACME_fnc_hpmkStateCommit;
_newUnit setVariable ["ACME_emma_bvmAttached", false, true];
_newUnit setVariable ["ACME_emma_lastPatient", objNull];
_newUnit setVariable ["ACME_emma_lastBag", -1e9];
[_newUnit, false] call ACME_fnc_obtundedApply;
true
