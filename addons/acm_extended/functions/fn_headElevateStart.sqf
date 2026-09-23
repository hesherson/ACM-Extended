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
    // A delayed normalization belongs to the placement state that accepted this request.
    private _startPoseToken = _patient getVariable ["ACME_headElev_poseToken", ""];
    private _delay = 0.08;

    if ([_patient] call ACME_fnc_chestSealCanPhysicalRoll) then {
        if (!isNull _medic && {!(_medic isEqualTo _patient)} && {alive _medic}) then {
            [_medic,"chestAccessFrontRoll",[_medic,_patient]] call ACME_fnc_ownerDispatch;
        };

        [_patient,"front",false,_medic,true] call ACME_fnc_chestSealRoll;

        private _patientRoll = missionNamespace getVariable ["ACME_CS_rollTime",1.85];
        if !(_patientRoll isEqualType 0 && {finite _patientRoll}) then {_patientRoll = 1.85;};
        private _providerRoll = missionNamespace getVariable ["ACME_rollProviderDuration",2.2];
        if !(_providerRoll isEqualType 0 && {finite _providerRoll}) then {_providerRoll = 2.2;};
        _delay = (_patientRoll + 0.10) max (_providerRoll + 0.25);
    } else {
        // A stale/non-rollable downed state must still never feed the Semi-Fowler grab from the stomach.
        private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp","ACM_LyingState"];
        _patient setVariable ["ACME_CS_facing","front",true];
        ["ace_common_switchMove",[_patient,_faceUp]] call CBA_fnc_globalEvent;
    };

    [{
        params ["_m","_p","_body","_auto","_startPoseToken"];
        if (!isNull _p && {local _p} && {alive _p}) then {
            if ((_p getVariable ["ACME_headElev_poseToken", ""]) != _startPoseToken) exitWith {};
            // Startup revalidates eligibility before setting facing or touching gear. Do not write ahead of it.
            [_m,_p,_body,_auto,true] call ACME_fnc_headElevateStart;
        };
    }, [_medic,_patient,_bodyPart,_auto,_startPoseToken], _delay] call CBA_fnc_waitAndExecute;
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
private _manual = !_hasBag && {_vestClass isEqualTo ""};
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
    // place it after the lift step, so the sequence reads strip, lift, wedge. it is guarded against an early lower or
    // death.
    [{
        params ["_patient", "_vestClass", "_poseToken"];
        if (isNull _patient || {!local _patient} || {!alive _patient}
            || {!(_patient getVariable ["ACME_headElevated", false])}
            || {(_patient getVariable ["ACME_headElev_poseToken", ""]) != _poseToken}
            || {!(_patient getVariable ["ACME_headElev_vestRemoved", false])}
            || {!isNull objectParent _patient}) exitWith {};
        // render the carrier as a createSimpleObject of the world model of the vest: a static, non-simulated visual that
        // renders the instant it is created and is pinned by the attachment. that is unlike the old GroundWeaponHolder
        // plus cargo, whose draped-vest cargo frequently never spawned a visible model and froze invisible. it falls back
        // to a weapon holder only if the vest exposes no usable model.
        private _model = getText (configFile >> "CfgWeapons" >> _vestClass >> "model");
        private _prop = objNull;
        if (_model != "") then { _prop = createSimpleObject [_model, [0,0,0], false]; };
        if (isNull _prop) then {
            _prop = createVehicle ["GroundWeaponHolder", getPosATL _patient, [], 0, "CAN_COLLIDE"];
            _prop addItemCargoGlobal [_vestClass, 1];
        };
        _patient setVariable ["ACME_headElev_propObj", _prop, true];
        [_patient] call ACME_fnc_headElevPropApply;  // it seats and orients behind the upper back, with no sim toggling needed.
    }, [_patient, _vestClass, _poseToken], (missionNamespace getVariable ["ACME_headElev_standTime", 0.8]) + 0.4] call CBA_fnc_waitAndExecute;
};

if (!_manual && {!_hasBag} && {!([_patient] call ACME_fnc_animBlocked)}
    && {!(_patient getVariable ["ACME_headElev_vestRemoved", false])}) exitWith {
    _patient setVariable ["ACME_headElevated", false, true];
    _patient setVariable ["ACME_headElev_poseToken", "", true];
};
[_patient] call ACME_fnc_headElevWatch;

// B71 Semi-Fowler: preserve the support-surface reference only for prop bookkeeping.  Do not attach or setPos the
// casualty. The patient and provider start their requested animations in tandem on this frame.
_patient setVariable ["ACME_headElev_basePosASL", getPosASL _patient, true];
_patient setVariable ["ACME_headElev_baseDir", getDir _patient, true];
_patient setVariable ["ACME_headElev_baseAnim", animationState _patient, true];
missionNamespace setVariable ["ACME_headElev_TunePatient", _patient];
[_patient] call ACME_fnc_headElevApplyTilt;

if (_manual) then {
    [_medic, "headElevHoldStart", [_medic, _patient, _bodyPart, _poseToken]] call ACME_fnc_ownerDispatch;
} else {
    if (!isNull _medic) then {[_medic, _patient] call ACME_fnc_headElevMedicStart;};
};
