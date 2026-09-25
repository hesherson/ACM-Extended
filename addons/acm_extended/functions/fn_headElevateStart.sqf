// "Elevate Head 30". it raises the head of the bed by about 30 degrees. it sets ACME_headElevated on the patient,
// which fn_tbihandle reads to ease ICP and CPP down slowly and to make herniation impossible while elevated.
// Semi-Fowler has a hard supine invariant: if the casualty is already on their back, keep them there; if they are
// posterior-up, physically roll them to the anterior/front view FIRST, then run the grab/elevate choreography.
// the ACE treatment callback args are [_medic, _patient, _bodyPart, _classname, ...], so slot 3 carries the
// treatment classname, a string, and the auto flag cannot be a typed positional param there. the
// transport-restore path passes a literal true in slot 3, and anything else, ACE's classname included, reads as
// not-auto.
params ["_medic", "_patient", ["_bodyPart", ""]];
private _auto = (_this param [3, false]) isEqualTo true;
private _afterProneRoll = (_this param [4, false]) isEqualTo true;
if (isNull _patient || {!alive _patient} || {isNull _medic && {!_auto}}) exitWith {};
if (!local _patient) exitWith {
    [_patient, "headElevStart", [_medic, _patient, _bodyPart, _auto, _afterProneRoll]] call ACME_fnc_ownerDispatch;
};
if (canSuspend) exitWith {isNil {[_medic, _patient, _bodyPart, _auto, _afterProneRoll] call ACME_fnc_headElevateStart;};};
if (_patient getVariable ["ACME_headElevated", false]) exitWith {
    if (!isNull _medic) then { ["Head is already elevated.", 2, _medic] call ace_common_fnc_displayTextStructured; };
};

// Revalidate on the patient owner after the treatment timer/network hop, before moving gear or posing.
// This also protects automatic transport restoration if the patient got up in the meantime.
if !([_patient, _medic] call ACME_fnc_headElevateCanStart) exitWith {};

// Normalize front/supine before ANY Semi-Fowler animation. The retry flag prevents a second roll request after
// the authored patient roll finishes. Already-supine casualties take no detour.
private _actualBeforeElevate = [_patient, _patient getVariable ["ACME_CS_facing","front"]]
    call ACME_fnc_chestSealActualSide;
private _needFrontFirst = !_afterProneRoll && {_actualBeforeElevate != "front"};

if (_needFrontFirst) exitWith {
    // This pre-roll belongs to the still-unstarted placement generation. Use the roll's real ownership token rather
    // than sleeping for a nominal animation duration: the next Semi-Fowler frame begins as soon as the casualty roll
    // actually retires, with no dead-air delay and no race against a late roll callback.
    private _startPoseToken = _patient getVariable ["ACME_headElev_poseToken", ""];

    if ([_patient] call ACME_fnc_chestSealCanPhysicalRoll) then {
        if (!isNull _medic && {!(_medic isEqualTo _patient)} && {alive _medic}) then {
            [_medic,"chestAccessFrontRoll",[_medic,_patient]] call ACME_fnc_ownerDispatch;
        };
        [_patient,"front",false,_medic,true] call ACME_fnc_chestSealRoll;

        private _rollToken = _patient getVariable ["ACME_CS_rollToken", ""];
        if (_rollToken != "") then {
            [{
                params ["_p","_rollToken","_startPoseToken"];
                if (isNull _p || {!local _p} || {!alive _p}
                    || {(_p getVariable ["ACME_headElev_poseToken", ""]) != _startPoseToken}) exitWith {true};
                (_p getVariable ["ACME_CS_rollToken", ""]) != _rollToken
            }, {
                params ["_p","_rollToken","_startPoseToken","_m","_body","_auto"];
                if (isNull _p || {!local _p} || {!alive _p}
                    || {(_p getVariable ["ACME_headElev_poseToken", ""]) != _startPoseToken}) exitWith {};
                // A different non-empty token means another/newer roll superseded this normalization. Do not let the
                // old Semi-Fowler continuation steal that patient's animation generation.
                if ((_p getVariable ["ACME_CS_rollToken", ""]) != "") exitWith {};
                _p setVariable ["ACME_CS_facing","front",true];
                [_m,_p,_body,_auto,true] call ACME_fnc_headElevateStart;
            }, [_patient,_rollToken,_startPoseToken,_medic,_bodyPart,_auto], 4.5, {
                params ["_p","_rollToken","_startPoseToken","_m","_body","_auto"];
                if (isNull _p || {!local _p} || {!alive _p}
                    || {(_p getVariable ["ACME_headElev_poseToken", ""]) != _startPoseToken}) exitWith {};
                private _currentRoll = _p getVariable ["ACME_CS_rollToken", ""];
                if (_currentRoll != "" && {_currentRoll != _rollToken}) exitWith {};
                // Fail closed to the stable supine side. Only the exact wedged roll this start created may be
                // cancelled; a newer roll generation is never touched.
                [_p,"front"] call ACME_fnc_patientRollCancel;
                _p setVariable ["ACME_CS_facing","front",true];
                [{_this call ACME_fnc_headElevateStart;}, [_m,_p,_body,_auto,true], 0.05] call CBA_fnc_waitAndExecute;
            }] call CBA_fnc_waitUntilAndExecute;
        } else {
            // Roll request was denied by an older patient-animation lease. Stabilize to face-up and retry on the
            // next scheduling slice instead of waiting several seconds for a transition that never started.
            private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp","ACM_LyingState"];
            _patient setVariable ["ACME_CS_facing","front",true];
            ["ace_common_switchMove",[_patient,_faceUp]] call CBA_fnc_globalEvent;
            [{_this call ACME_fnc_headElevateStart;}, [_medic,_patient,_bodyPart,_auto,true], 0.05] call CBA_fnc_waitAndExecute;
        };
    } else {
        private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp","ACM_LyingState"];
        _patient setVariable ["ACME_CS_facing","front",true];
        ["ace_common_switchMove",[_patient,_faceUp]] call CBA_fnc_globalEvent;
        [{_this call ACME_fnc_headElevateStart;}, [_medic,_patient,_bodyPart,_auto,true], 0.05] call CBA_fnc_waitAndExecute;
    };
};

// At this point the patient is definitively anterior-up. All Semi-Fowler patient/provider animations start from it.
_patient setVariable ["ACME_CS_facing","front",true];

if (_patient getVariable ["ACME_headElev_vestRemoved", false]) then {
    [_patient] call ACME_fnc_headElevVestRestore;
};
[_patient] call ACME_fnc_chestAccessVestRestore;
if (_patient getVariable ["ACME_headElev_vestRemoved", false]) exitWith {};
// something has to physically prop the casualty up. a worn backpack does it directly, and if there is no backpack
// but the casualty is wearing a plate carrier, we strip the carrier, lift them, and wedge it behind the
// back.
private _hasBag = ((backpack _patient) isNotEqualTo "");
private _vestClass = vest _patient;

// Only an actual armored carrier is accepted as passive Semi-Fowler support. An unarmored chest rig/vest does not
// physically prop the casualty and therefore uses the same active provider-held mode as no vest at all.
private _hasCarrier = false;
if (_vestClass != "") then {
    private _vestInfo = configFile >> "CfgWeapons" >> _vestClass >> "ItemInfo";
    private _legacyArmor = getNumber (_vestInfo >> "armor");
    private _hp = _vestInfo >> "HitpointsProtectionInfo";
    private _chestArmor = getNumber (_hp >> "Chest" >> "armor");
    private _diaArmor = getNumber (_hp >> "Diaphragm" >> "armor");
    private _abdArmor = getNumber (_hp >> "Abdomen" >> "armor");
    private _carrierArmor = (((_legacyArmor max _chestArmor) max _diaArmor) max _abdArmor);
    _hasCarrier = _carrierArmor > 0;
};
private _manual = !_hasBag && {!_hasCarrier};
if (_manual && {_auto || {isNull _medic} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious", false]}
    || {([_medic, _patient] call ACME_fnc_patientInteractionDistance) > (missionNamespace getVariable ["ace_medical_gui_maxDistance", 3])
        && {vehicle _medic != vehicle _patient}}}) exitWith {};

// Each placement has a token. Deferred pose work must not affect a later placement.
private _serial = (missionNamespace getVariable ["ACME_headElev_serial", 0]) + 1;
missionNamespace setVariable ["ACME_headElev_serial", _serial];
private _poseToken = format ["%1:%2:%3", clientOwner, CBA_missionTime, _serial];
_patient setVariable ["ACME_headElev_poseToken", _poseToken, true];
_patient setVariable ["ACME_headElev_treatments", createHashMap, true];
_patient setVariable ["ACME_headElevated", true, true];
_patient setVariable ["ACME_headElev_visualActive", false, true];
// Unsupported/manual Semi-Fowler is an active maneuver, not a passive posture. Keep this origin flag even if a
// competing intervention clears the provider hold first; that episode may never auto-resume without a new action.
_patient setVariable ["ACME_headElev_manualUnsupported", _manual, true];
_patient setVariable ["ACME_headElev_hold", [[], [_medic, _poseToken, CBA_missionTime]] select _manual, true];

// A backpack or vehicle seat needs no removed vest and no refund record.
if (!_manual && {!_hasBag} && {!([_patient] call ACME_fnc_animBlocked)}) then {
    private _vestEntry = (getUnitLoadout _patient) param [4, [], [[]]];
    if (count _vestEntry == 2) then {
        _patient setVariable ["ACME_headElev_vestLoadout", _vestEntry, true];
        _patient setVariable ["ACME_headElev_vestRemoved", true, true];
        _patient setVariable ["ACME_headElev_propVest", _vestClass, true];
        _patient setVariable ["ACME_headElev_propVestItems", vestItems _patient, true];
        removeVest _patient;
        if (vest _patient != "") then {
            _patient setVariable ["ACME_headElev_vestRemoved", false, true];
            _patient setVariable ["ACME_headElev_vestLoadout", [], true];
            _patient setVariable ["ACME_headElev_propVest", "", true];
            _patient setVariable ["ACME_headElev_propVestItems", [], true];
        };
    };

};

if (!_manual && {!_hasBag} && {!([_patient] call ACME_fnc_animBlocked)}
    && {!(_patient getVariable ["ACME_headElev_vestRemoved", false])}) exitWith {
    _patient setVariable ["ACME_headElevated", false, true];
    _patient setVariable ["ACME_headElev_poseToken", "", true];
};
[_patient] call ACME_fnc_headElevWatch;

// Patient and provider begin the authored Semi-Fowler choreography together. Earlier builds inserted a
// provider-ready network handshake here; that produced visible dead time and could leave the logical posture set
// while the patient never moved if the provider episode was interrupted. Patient motion is patient-owned and starts
// immediately. Provider theatre is presentation-only and can be cancelled/preempted independently.
_patient setVariable ["ACME_headElev_basePosASL", getPosASL _patient, true];
_patient setVariable ["ACME_headElev_baseDir", getDir _patient, true];
_patient setVariable ["ACME_headElev_baseAnim", animationState _patient, true];
_patient setVariable ["ACME_headElev_pendingLift", [], true];
_patient setVariable ["ACME_headElev_liftRequestAt", -1, false];
missionNamespace setVariable ["ACME_headElev_TunePatient", _patient];

private _tiltAccepted = [_patient] call ACME_fnc_headElevApplyTilt;
if !(_tiltAccepted isEqualTo true) exitWith {
    // The treatment timer completed but another patient animation acquired the casualty in the handoff frame.
    // Roll the logical placement back immediately rather than leaving Semi-Fowler "on" with no visible posture.
    [objNull, _patient, true] call ACME_fnc_headElevateStop;
};

if (_manual) then {
    [_medic, "headElevHoldStart", [_medic, _patient, _bodyPart, _poseToken]] call ACME_fnc_ownerDispatch;
} else {
    if (!isNull _medic) then {[_medic, _patient] call ACME_fnc_headElevMedicStart;};
};
