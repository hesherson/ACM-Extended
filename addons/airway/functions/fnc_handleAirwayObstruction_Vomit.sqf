/* B32: de-macroed vanilla ACM worker (original author Blue), with a live
   arrest/paralysis pause. Existing airway contents are not erased; the native
   remaining-stomach ledger, nausea, recovery-position and cadence are retained.
   A replicated active flag identifies a previously requested native worker; local
   handles and episode tokens never move between owners. */
/*
 * Author: Blue
 * Handle airway obstruction due to vomit.
 *
 * Arguments:
 * 0: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player] call ACM_airway_fnc_handleAirwayObstruction_Vomit;
 *
 * Public: No
 */

params ["_patient", ["_epoch", -1]];
if (isNull _patient) exitWith {};
if (_epoch < 0) then {_epoch = [_patient] call ACME_fnc_clinicalEpoch;};
if (!local _patient) exitWith {
    ["ACM_airway_handleAirwayObstruction_Vomit", [_patient, _epoch], _patient] call CBA_fnc_targetEvent;
};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)
    || {_patient getVariable ["ACME_clinicalRestoring", false]}) exitWith {};
private _old = _patient getVariable ["ACM_airway_AirwayObstructionVomit_PFH", -1];
private _worker = [clientOwner, _epoch];
if (_old >= 0 && {(_patient getVariable ["ACME_nativeVomitWorker", []]) isEqualTo _worker}) exitWith {};
if (_old >= 0) then {[_old] call CBA_fnc_removePerFrameHandler;};
_patient setVariable ["ACM_airway_AirwayObstructionVomit_PFH", -1, false];
_patient setVariable ["ACME_nativeVomitWorker", [], false];
if (!alive _patient || {!(_patient getVariable ["ACE_isUnconscious", false])}
    || {(_patient getVariable ["ACM_airway_AirwayObstructionVomit_Count", 0]) < 1}) exitWith {
    _patient setVariable ["ACME_nativeVomitActive", false, true];
};
_patient setVariable ["ACME_nativeVomitWorker", _worker, false];
_patient setVariable ["ACME_nativeVomitActive", true, true];

private _PFH = [{
    params ["_args", "_idPFH"];
    _args params ["_patient", "_epoch"];
    // Retire the old machine/episode before any shared state or sound is touched.
    // Owner registration resumes only the replicated active flag, never mere contents.
    if (isNull _patient || {!local _patient}
        || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}
        || {_patient getVariable ["ACME_clinicalRestoring", false]}
        || {(_patient getVariable ["ACM_airway_AirwayObstructionVomit_PFH", -1]) != _idPFH}
        || {!((_patient getVariable ["ACME_nativeVomitWorker", []]) isEqualTo [clientOwner, _epoch])}) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
        if (!isNull _patient && {(_patient getVariable ["ACM_airway_AirwayObstructionVomit_PFH", -1]) == _idPFH}) then {
            _patient setVariable ["ACM_airway_AirwayObstructionVomit_PFH", -1, false];
            _patient setVariable ["ACME_nativeVomitWorker", [], false];
        };
    };

    private _inRecovery = _patient getVariable ["ACM_airway_RecoveryPosition_State", false];
    private _keepAirwayIntact = (_patient getVariable ["ACM_airway_AirwayItem_Oral", ""] == "SGA"); // TODO consciousness state
    private _gracePeriod = (_patient getVariable ["ACM_airway_AirwayObstructionVomit_GracePeriod", -1]) + 20 > CBA_missionTime;
    private _obstructionState = _patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0];
    private _vomitCount = _patient getVariable ["ACM_airway_AirwayObstructionVomit_Count", 0];

    if (!alive _patient || {!(_patient getVariable ["ACE_isUnconscious", false])} || {_vomitCount < 1}) exitWith {
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_PFH", -1, false];
        _patient setVariable ["ACME_nativeVomitWorker", [], false];
        _patient setVariable ["ACME_nativeVomitActive", false, true];
        [_idPFH] call CBA_fnc_removePerFrameHandler;
    };

    // Paused rather than discarded: after ROSC or reversal the native worker can
    // continue, but cannot emit active vomiting/audio or consume contents now.
    if (_patient getVariable ["ace_medical_inCardiacArrest", false]
        || {_patient getVariable ["ACME_roc_paralyzed", false]}) exitWith {};
    if (_keepAirwayIntact || _gracePeriod) exitWith {};

    private _medicationEffect = [_patient] call ACM_circulation_fnc_getNauseaMedicationEffects;

    if (random 1 < ((0.4 * ACM_airway_airwayObstructionVomitChance) + _medicationEffect)) then {
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_GracePeriod", CBA_missionTime, true];
        _patient setVariable ["ACM_airway_AirwayObstructionVomit_Count", ((_vomitCount - 1) max 0), true];

        if !(_inRecovery) then { // TODO check for pose
            [_patient, [["vomit", _obstructionState + 1]], true] call ACM_airway_fnc_setAirwayState;
        };

        // Every real emesis receives an episode receipt, including protected recovery-position emesis.
        // Tick applies the existing recovery-position protection; clearing/grace-only ticks emit nothing.
        private _emesis = [_patient,"make",format ["ACME-native-vomit:%1:%2",_epoch,CBA_missionTime],_obstructionState + 1,2] call ACME_fnc_aspirationEventKey;
        if !(_emesis isEqualTo []) then {_patient setVariable ["ACME_laryngo_emesis",_emesis,true];};

        playSound3D [format ["%1%2.wav", "\x\ACM\addons\airway\sound\vomit",(1 + round(random 5))], _patient, false, getPosASL _patient, 10, (0.9 + (random 0.2)), 10];
    };
}, (10 + (random 10)), [_patient, _epoch]] call CBA_fnc_addPerFrameHandler;

_patient setVariable ["ACM_airway_AirwayObstructionVomit_PFH", _PFH, false];
