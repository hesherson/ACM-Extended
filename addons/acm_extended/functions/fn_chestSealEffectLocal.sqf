/* Owner-local clinical consequences of a server-accepted discrete edit.
   This uses the supplied ACM entry points; no medic cargo or UI lives here. */
params ["_patient", "_medic", "_op", ["_args", []], ["_epoch", ""], ["_issued", -1], ["_revision", -1]];
if (isNull _patient || {!local _patient}) exitWith {};
// B72: never compare a remote machine's CBA_missionTime stamp with this patient's owner-local reset time.
// Epoch/revision/clinical-epoch checks below are network-stable and already reject pre-reset or stale effects.
if (_epoch != "" && {_epoch == (_patient getVariable ["ACME_CS_blockedEffectEpoch", ""])}) exitWith {};
// A locality forward may arrive after a newer seal/peel projection. Never roll it back.
if (_op in ["seal", "peel"] && {_revision >= 0} && {_revision <= (_patient getVariable ["ACME_CS_lastSealEffectRev", -1])}) exitWith {};
if (_op in ["seal", "peel"] && {_revision >= 0}) then { _patient setVariable ["ACME_CS_lastSealEffectRev", _revision, true]; };
switch (_op) do {
    case "seal": {
        // Equipment remains real even when the residual PTX grade is zero. We are already on the patient owner,
        // so call ACM's LOCAL physiology function directly. The public wrapper also writes its own activity-log row;
        // calling it here and then logging again was the immediate duplicate-message source.
        [_medic, _patient] call ACM_breathing_fnc_applyChestSealLocal;
        _patient setVariable ["ACME_CS_sealApplied", true, true];
        private _logged = [_patient, "apply", "%1 applied a chest seal", [[_medic, false, true] call ace_common_fnc_getName], _medic] call ACME_fnc_chestSealLogOnce;
        if (_logged) then {[_patient, localize "STR_ACM_Breathing_ChestSeal"] call ace_medical_treatment_fnc_addToTriageCard;};
    };
    case "thoraSeal": {
        _args params [["_side", ""], ["_clinicalEpoch", -1]];
        if (!(_side in ["left", "right"]) || {_clinicalEpoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {false};
        // B271: only this owner commits the closure after accepting its supply transaction.
        if ((_patient getVariable [format ["ACME_thora_open_%1", _side], ""]) != "finger"
            || {_patient getVariable [format ["ACME_thora_tube_%1", _side], false]}
            || {_patient getVariable [format ["ACME_thora_sealed_%1", _side], false]}
            || {_patient getVariable [format ["ACME_thora_closed_%1", _side], false]}) exitWith {false};
        [_patient] call ACME_fnc_ptxEnsure;
        if !([_patient] call ACME_fnc_ptxCanClose) exitWith {false};
        // This is a per-tract closure, not ACM's global whole-chest ChestSeal_State. Setting the native
        // aggregate here would incorrectly imply that unrelated penetrating chest wounds are also sealed.

        // A seal over the finger-thoracostomy is a true occlusive closure of that surgical communication.
        // Preserve the incision/seal evidence, but retire the tract from the patent finger-drain state. It is
        // deliberately NOT a vent. Readiness proves this injury's leak has settled before closing it.
        [_patient, _side, "sealed", true] call ACME_fnc_thoraSideStateCommit;
        [_patient, _side, "closed", true] call ACME_fnc_thoraSideStateCommit;
        [_patient, _side, "open", "sealed"] call ACME_fnc_thoraSideStateCommit;
        [_patient] call ACME_fnc_thoraBumpVer;
        [_patient, "thoraSeal"] call ACME_fnc_ptxTreat;
        [_patient] call ACM_breathing_fnc_updateLungState;

        private _logged = [_patient, "apply", "%1 applied a chest seal over the thoracostomy incision", [[_medic, false, true] call ace_common_fnc_getName], _medic] call ACME_fnc_chestSealLogOnce;
        if (_logged) then {[_patient, localize "STR_ACM_Breathing_ChestSeal"] call ace_medical_treatment_fnc_addToTriageCard;};
        true
    };
    case "peel": {
        // Ordinary wound seals vent air only. Blood drainage requires the separate surgical tract aftercare.
        if !(_args param [0, false]) then {
            [_patient, [["chestSeal", false]], true] call ACM_breathing_fnc_setRuntimeState;
            _patient setVariable ["ACME_CS_sealApplied", false, true];
            [_patient, "remove", "Removed the chest seal", [], _medic] call ACME_fnc_chestSealLogOnce;
        };
        // Removing any individual seal changes communicating-wound coverage.
        [_patient, "peel"] call ACME_fnc_ptxTreat;
        if (alive _patient) then {[_patient] call ACM_breathing_fnc_updateLungState;};
    };
    // Obsolete ncdTension packets intentionally have no handler. A delayed packet
    // cannot recreate tension after successful treatment or a healed leak.
    case "miss": { [_patient, 1] call ACME_fnc_ptxInjury; };
    case "ncd": {
        private _patientSide = _args param [0, ""];
        if !(_patientSide in ["left", "right"]) exitWith {};
        // This was formerly written before _patient was declared in the UI function.
        _patient setVariable ["ACME_ncd_total", (_patient getVariable ["ACME_ncd_total", 0]) + 1, true];
        private _hadTension = _patient getVariable ["ACM_breathing_TensionPneumothorax_State", false];
        private _hadPtx = _patient getVariable ["ACM_breathing_Pneumothorax_State", 0];
        private _indicated = _hadTension || {_hadPtx > 0};
        [_medic, _patient] call ACM_breathing_fnc_performNCD;
        if (!_indicated) then {
            // The native owner callback creates the injury exactly once and applies
            // the actual catheter drainage. This edit records laterality only.
            _patient setVariable ["ACME_ncd_iatrogenicSide", _patientSide, true];
        };
        [_patient, "activity", "%1 performed a needle decompression (NAR SPEAR, %2 side)", "NCD %2, NAR SPEAR, %1",
            [[_medic, false, true] call ace_common_fnc_getName, _patientSide]] call ACME_fnc_medLog;
    };
};
