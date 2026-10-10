/* NA3 identified owner-local shock transaction. Unscheduled event/call only; no suspension before commit. */
params ["_medic", "_patient", "_id", "_epoch", "_expectedLast", "_expectedSync", "_sentAtServer"];
if (isNull _patient || {isNull _medic}) exitWith {};
if (!local _patient) exitWith {[_patient, "shock", _this] call ACME_fnc_ownerDispatch;};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)
    || {serverTime - _sentAtServer > 30}
    || {_sentAtServer - serverTime > 2}) exitWith {};
private _history = +(_patient getVariable ["ACME_shockCommitted", []]);
if (_id in _history) exitWith {};
private _last = _patient getVariable ["ACM_circulation_AED_LastShock", -60];
if (_last != _expectedLast) exitWith {
    [_medic, "Device state changed. Review the rhythm and charge before shocking again."] call ACME_fnc_clinicalNotice;
};
// Base ACM's AED_Provider is the casualty itself, not the operator. Validate the actual medic carried by the
// monitor/API request instead of comparing against that legacy sentinel.
if (!alive _medic || {!([_medic] call ace_common_fnc_isAwake)}
    || {(_medic distance _patient) > ace_medical_gui_maxDistance}) exitWith {};
if (!([_medic, _patient] call ACM_circulation_fnc_AED_CanAdministerShock)) exitWith {};
private _rhythm = [_patient] call ACME_fnc_rhythmGet;
private _organized = _rhythm in [4,100,101,103,104]; // B67: native perfusing VT is an organized SYNC rhythm, not a defibrillation rhythm.
private _defib = _rhythm in [2,3,102];
if (_expectedSync && {_defib}) exitWith {
    [_medic, "SYNC armed: no R wave to synchronize. Disarm SYNC to defibrillate."] call ACME_fnc_clinicalNotice;
};
// Commit the single charge before sounds, random outcomes or event callbacks.
_history pushBack _id;
if (count _history > 64) then {_history deleteRange [0, count _history - 64];};
_patient setVariable ["ACME_shockCommitted", _history, true];
private _runtime = [
    ["aedCharged", false],
    ["aedInUse", false],
    ["aedShockTotal", 1 + (_patient getVariable ["ACM_circulation_AED_ShockTotal", 0])]
];
// Native ACM's AED_LastShock drives defibrillation refractory behavior. A synchronized cardioversion must not
// poison that clock or make a later indicated defibrillation inside 60 seconds behave like a repeat shock.
if (!_expectedSync) then {_runtime pushBack ["aedLastShock", CBA_missionTime];};
[_patient, _runtime, true] call ACM_circulation_fnc_setRuntimeState;
[_medic, [["aedMedicInUse", false]], true] call ACM_circulation_fnc_setRuntimeState;
// Owner-local clinical clock for synchronized cardioversion persistence, plus one shared server clock for every
// physical shock so monitor/pulse clients never compare the casualty owner's CBA_missionTime to their own clock.
if (_expectedSync) then {_patient setVariable ["ACME_sync_lastShock", CBA_missionTime, true];};
_patient setVariable ["ACME_aed_lastShockServer", serverTime, true];
[_patient, CBA_missionTime + (missionNamespace getVariable ["ACME_rhythmNativeShockGraceSec", 10]), true, false] call ACME_fnc_rhythmNativeShockGraceCommit;
[_patient, "", -1, true, false] call ACME_fnc_rhythmNativeHoldCommit;
[_patient, 0, false, false, false] call ACME_fnc_rhythmNativeHighHRFloorCommit;
playSound3D [format ["x\ACM\addons\circulation\sound\shock_jolt%1.wav", 1 + round random 3], _patient, false, getPosASL _patient, 15, 1, 15];
// Preserve AED prompts and busy timing. Epoch guards stop stale delayed effects after a heal.
if (_patient getVariable ["ACM_circulation_AED_AnalyzeRhythm_State", false]) then {
    [_patient, [["aedAnalyzeBusy", true], ["aedAnalyzeRhythmState", false]], true] call ACM_circulation_fnc_setRuntimeState;
    [{
        params ["_p", "_epoch"];
        if (isNull _p || {_epoch != ([_p] call ACME_fnc_clinicalEpoch)}) exitWith {};
        [_p] call ACM_circulation_fnc_AED_TrackCPR;
        playSound3D ["x\ACM\addons\circulation\sound\aed_startcpr.wav", _p, false, getPosASL _p, 15, 1, 15];
    }, [_patient, _epoch], 2] call CBA_fnc_waitAndExecute;
    [{params ["_p", "_epoch"]; if (!isNull _p && {_epoch == ([_p] call ACME_fnc_clinicalEpoch)}) then {[_p, [["aedAnalyzeBusy", false]], true] call ACM_circulation_fnc_setRuntimeState;};}, [_patient, _epoch], 4] call CBA_fnc_waitAndExecute;
} else {
    [{params ["_p", "_epoch"]; if (!isNull _p && {_epoch == ([_p] call ACME_fnc_clinicalEpoch)}) then {playSound3D ["x\ACM\addons\circulation\sound\aed_3beep.wav", _p, false, getPosASL _p, 15, 1, 15];};}, [_patient, _epoch], 0.7] call CBA_fnc_waitAndExecute;
};
// Record the actor/action, not a clinical conclusion inferred from this transaction.
[_patient, "activity", ["%1 initiated defibrillation", "%1 initiated synchronized cardioversion"] select _expectedSync,
    [[_medic, false, true] call ace_common_fnc_getName]] call ace_medical_treatment_fnc_addToLog;
if (!alive _patient) exitWith {};
private _notice = "Shock delivered. No conversion.";
if (_organized && {!_expectedSync}) then {
    if (random 1 < (missionNamespace getVariable ["ACME_sync_ronTvfChance", 0.55])) then {
        [_patient] call ACME_fnc_rhythmRelease;
        [_patient, 2, _epoch] call ACME_fnc_arrestLocal;
        _notice = "Unsynchronized shock on an organized rhythm. R on T: VF.";
    };
} else {
    if (_organized && {_expectedSync}) then {
        private _map = missionNamespace getVariable ["ACME_sync_successByRhythm", createHashMap];
        private _chance = (_map getOrDefault [_rhythm, missionNamespace getVariable ["ACME_sync_successChance", 0.9]]) max 0 min 1;
        if (random 1 < _chance) then {
            [_patient, 0] call ACME_fnc_rhythmSet;
            _notice = "Synchronized cardioversion successful.";
        };
    } else {
        if (_defib) then {
            private _attempt = false;
            if (_rhythm == 102) then {
                private _map = missionNamespace getVariable ["ACME_sync_successByRhythm", createHashMap];
                _attempt = random 1 < ((_map getOrDefault [102, missionNamespace getVariable ["ACME_sync_successChance", 0.9]]) max 0 min 1);
            } else {
                // Preserve the native refractory-shock rule. Normalize CPR history to a bounded 0..0.10 bonus.
                if (CBA_missionTime - _last < 60) then {
                    [_patient, 1] call ACME_fnc_rhythmSet;
                } else {
                    private _effects = [_patient] call ACM_circulation_fnc_getCardiacMedicationEffects;
                    private _amio = _effects getOrDefault ["amiodarone", 0];
                    private _resistant = _patient getVariable ["ACM_circulation_CardiacArrest_ShockResistant", false];
                    if (!(_patient getVariable ["ACM_circulation_CardiacArrest_ResistChecked", false])) then {
                        _resistant = random 1 < 0.3;
                        [_patient, [["cardiacArrestResistChecked", true], ["cardiacArrestShockResistant", _resistant]], true] call ACM_circulation_fnc_setRuntimeState;
                    };
                    private _cpr = linearConversion [60,120,_patient getVariable ["ACM_circulation_CPR_StoppedTotal",0],0,0.10,true];
                    private _chance = (0.2 + 0.2 * _amio + _cpr) max 0 min 1;
                    if (!_resistant || {_amio > 1.9}) then {_attempt = random 1 < _chance;};
                    private _lido = [_patient] call ACME_fnc_lidoEffectiveness;
                    if (!_attempt && {_lido > 0}) then {
                        private _extra = (missionNamespace getVariable ["ACME_rhythm_lidoDefibBaseChance",0.2]) + _cpr + _lido * (missionNamespace getVariable ["ACME_rhythm_lidoDefibBoost",0.8]);
                        _attempt = random 1 < (_extra max 0 min 1);
                    };
                };
            };
            if (_attempt) then {
                if (_rhythm == 102 && {!(_patient getVariable ["ace_medical_inCardiacArrest",false])}) then {
                    [_patient,0,_epoch] call ACME_fnc_rhythmSet;
                    [_patient,"ACME_rhythm_torsadesRefractoryUntil",CBA_missionTime + (missionNamespace getVariable ["ACME_rhythm_defibTorsadesRefractorySec",8])] call ACME_fnc_setVarNet;
                    _notice = "Defibrillation converted polymorphic VT.";
                } else {
                    if ([_patient, _epoch] call ACME_fnc_shockROSC) then {_notice = "Defibrillation: return of spontaneous circulation.";};
                };
            };
        } else {
            // Native shock of sinus, VT, asystole or PEA. A waveform change never substitutes for arrest entry.
            [_patient] call ACME_fnc_rhythmRelease;
            [_patient, 1, _epoch] call ACME_fnc_arrestLocal;
        };
    };
};
[_patient, [["aedPadsLastSync", -1], ["aedEkgRhythm", -99]], true] call ACM_circulation_fnc_setRuntimeState;
[_medic, _notice] call ACME_fnc_clinicalNotice;
