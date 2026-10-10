params ["_patient", "_payload", ["_epoch", -1]];
if (!local _patient) exitWith {[_patient, "restore", _this] call ACME_fnc_ownerDispatch;};
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {};
if (_payload isEqualTo []) exitWith {[_patient] call ACME_fnc_ownerRegister;};
private _validation = [_payload] call ACME_fnc_clinicalValidate;
if !(_validation select 0) exitWith {};
private _allowed = ((call ACME_fnc_clinicalFields) select {_x param [3, true]}) apply {_x select 0};
// Restoring a pre-B271 episode onto an existing casualty must not borrow the
// current casualty's marker and turn an old quiet timer into closure readiness.
private _restoredPtx = ((_payload select 1) findIf {(_x select 0) == "ACME_ptx_state"}) >= 0;
private _restoredObservation = ((_payload select 1) findIf {(_x select 0) == "ACME_ptx_observationRevision"}) >= 0;
if (_restoredPtx && {!_restoredObservation}) then {
    _patient setVariable ["ACME_ptx_observationRevision", nil, true];
};
private _chest = [];
private _ettRestore = createHashMap;
private _rocRestoreSet = false;
private _rocRestore = false;
private _calciumRestoreSet = false;
private _calciumRestore = 0;
private _nrbRestore = createHashMap;
private _hpmkRestore = createHashMap;
private _obtundedRestore = createHashMap;
private _blastRestore = createHashMap;
private _blastEpisodeRestore = createHashMap;
private _rhythmHoldRestore = createHashMap;
private _rhythmTimingRestore = createHashMap;
private _bloodThermalRestore = createHashMap;
private _hypoTempRestoreSet = false;
private _hypoTempRestore = 37;
private _evacRestoreSet = false;
private _evacRestore = false;
private _ventShuntRestoreSet = false;
private _ventShuntRestore = 0;
private _rocStressRestore = createHashMap;
private _rocAwarenessRestore = createHashMap;
private _rocAwakeRestoreSet = false;
private _rocAwakeRestore = false;
private _rocApneaRestoreSet = false;
private _rocApneaRestore = false;
private _toxicityFiredRestoreSet = false;
private _toxicityFiredRestore = createHashMap;
{
    _x params ["_name", "_encoded"];
    if !(_name in _allowed) then {continue;};
    private _value = [_encoded, false] call ACME_fnc_clinicalCodec;
    if (isNil "_value") then {continue;};
    if (_name in ["ACME_nrb_on", "ACME_nrb_hasO2", "ACME_nrb_delivering"]) then {
        _nrbRestore set [_name, _value];
        continue;
    };
    if (_name in ["ACME_hpmk_state", "ACME_hpmk_on"]) then {
        _hpmkRestore set [_name, _value];
        continue;
    };
    if (_name in ["ACME_obtunded", "ACME_obtunded_manual", "ACME_obtunded_posture"]) then {
        _obtundedRestore set [_name, _value];
        continue;
    };
    if (_name in ["ACME_blastLung_State", "ACME_blastLung_ARDS"]) then {
        _blastRestore set [_name, _value];
        continue;
    };
    if (_name in ["ACME_blastLung_exposures", "ACME_blastLung_Onset", "ACME_blastLung_Time"]) then {
        _blastEpisodeRestore set [_name, _value];
        continue;
    };
    if (_name in ["ACME_rhythmNativeHoldKind", "ACME_rhythmNativeHoldRhythm"]) then {
        _rhythmHoldRestore set [_name, _value];
        continue;
    };
    if (_name in ["ACME_rhythmNativeHighHRFloorUntil", "ACME_rhythmNativeShockGraceUntil"]) then {
        _rhythmTimingRestore set [_name, _value];
        continue;
    };
    if (_name in ["ACME_coldBloodHungAt", "ACME_tempFlagHoldUntil"]) then {
        _bloodThermalRestore set [_name, _value];
        continue;
    };
    if (_name isEqualTo "ACME_hypo_temp") then {
        _hypoTempRestoreSet = true;
        _hypoTempRestore = _value;
        continue;
    };
    if (_name isEqualTo "ACME_requiresEvac") then {
        _evacRestoreSet = true;
        _evacRestore = _value;
        continue;
    };
    if (_name isEqualTo "ACME_vent_shunt") then {
        _ventShuntRestoreSet = true;
        _ventShuntRestore = _value;
        continue;
    };
    if (_name in ["ACME_roc_postROSCGraceUntil", "ACME_roc_awakeDwell", "ACME_roc_awakeResistAdd", "ACME_hrDrive_roc"]) then {
        _rocStressRestore set [_name, _value];
        continue;
    };
    if (_name in ["ACME_roc_awarenessEvent", "ACME_roc_awarenessAt", "ACME_roc_awarenessSeconds"]) then {
        _rocAwarenessRestore set [_name, _value];
        continue;
    };
    if (_name isEqualTo "ACME_roc_awakeParalysis") then {
        _rocAwakeRestoreSet = true;
        _rocAwakeRestore = _value;
        continue;
    };
    if (_name isEqualTo "ACME_roc_apnea") then {
        _rocApneaRestoreSet = true;
        _rocApneaRestore = _value;
        continue;
    };
    if (_name in ["ACME_ETT_Inserted", "ACME_ETT_CuffInflated", "ACME_ETT_Secured", "ACME_ETT_Unsecured"]) then {
        _ettRestore set [_name, _value];
        continue;
    };
    if (_name isEqualTo "ACME_roc_paralyzed") then {
        _rocRestoreSet = true;
        _rocRestore = _value;
        continue;
    };
    if (_name isEqualTo "ACME_ca_caCl2Given") then {
        _calciumRestoreSet = true;
        _calciumRestore = _value;
        continue;
    };
    if (_name isEqualTo "ACME_medicationToxicityFired") then {
        _toxicityFiredRestoreSet = true;
        _toxicityFiredRestore = _value;
        continue;
    };
    if (_name in ["ACME_CS_holeData", "ACME_CS_wastedSeals", "ACME_ncd_placed", "ACME_ncd_tensionBase", "ACME_penetratingTorso", "ACME_penetratingTorsoCount", "ACME_thora_outputMl", "ACME_thora_outputPerHour", "ACME_thora_outputStart"]) then {_chest pushBack [_name, _value];} else {_patient setVariable [_name, _value, true];};
} forEach (_payload param [1, []]);

// B106: XStat surgical/impaired flags are derived from the junctional device state.
// Rebuild them after ownership/state restoration so forceWalk and evacuation eligibility cannot drift.
private _xStatActive = (["leftarm", "rightarm", "leftleg", "rightleg"] findIf {
    toLowerANSI (_patient getVariable [format ["ACME_Junc_%1", _x], ""]) isEqualTo "xstat"
}) >= 0;
private _xStatLegActive = (["leftleg", "rightleg"] findIf {
    toLowerANSI (_patient getVariable [format ["ACME_Junc_%1", _x], ""]) isEqualTo "xstat"
}) >= 0;
private _xStatWasImpaired = _patient getVariable ["ACME_XStat_impaired", false];
_patient setVariable ["ACME_XStat_needsSurgery", _xStatActive, true];
_patient setVariable ["ACME_XStat_impaired", _xStatLegActive, true];
if (_xStatLegActive || {_xStatWasImpaired}) then {
    if (local _patient) then {
        _patient forceWalk _xStatLegActive;
    } else {
        [_patient, _xStatLegActive] remoteExec ["ACME_fnc_forceWalkLocal", _patient];
    };
};

// Phase 67: persistent owner-gated state must rehydrate through the same mutation boundaries used at runtime.
if (count _hpmkRestore > 0) then {
    private _state = _hpmkRestore getOrDefault ["ACME_hpmk_state", ""];
    if (!(_state isEqualType "")) then {_state = "";};
    if (_state isEqualTo "" && {_hpmkRestore getOrDefault ["ACME_hpmk_on", false]}) then {_state = "wrapped";};
    [_patient, _state, true, false] call ACME_fnc_hpmkStateCommit;
};
if (count _obtundedRestore > 0) then {
    private _on = _obtundedRestore getOrDefault ["ACME_obtunded", false];
    private _manual = _obtundedRestore getOrDefault ["ACME_obtunded_manual", false];
    private _posture = _obtundedRestore getOrDefault ["ACME_obtunded_posture", "free"];
    [_patient, _on, _manual, _posture, -1, true] call ACME_fnc_obtundedStateCommit;
};
if ("ACME_blastLung_State" in _blastRestore) then {
    [_patient, _blastRestore get "ACME_blastLung_State", true, false, false] call ACME_fnc_blastLungStateCommit;
};
if ("ACME_blastLung_ARDS" in _blastRestore) then {
    [_patient, _blastRestore get "ACME_blastLung_ARDS", objNull, true, false, false] call ACME_fnc_blastLungArdsCommit;
};
if (count _blastEpisodeRestore > 0) then {
    [_patient,
        _blastEpisodeRestore getOrDefault ["ACME_blastLung_exposures", "KEEP"],
        _blastEpisodeRestore getOrDefault ["ACME_blastLung_Onset", "KEEP"],
        _blastEpisodeRestore getOrDefault ["ACME_blastLung_Time", "KEEP"],
        true
    ] call ACME_fnc_blastLungEpisodeCommit;
};
if (count _rhythmHoldRestore > 0) then {
    private _kind = _rhythmHoldRestore getOrDefault ["ACME_rhythmNativeHoldKind", _patient getVariable ["ACME_rhythmNativeHoldKind", ""]];
    private _rhythm = _rhythmHoldRestore getOrDefault ["ACME_rhythmNativeHoldRhythm", _patient getVariable ["ACME_rhythmNativeHoldRhythm", -1]];
    [_patient, _kind, _rhythm, true, false] call ACME_fnc_rhythmNativeHoldCommit;
};
if ("ACME_rhythmNativeHighHRFloorUntil" in _rhythmTimingRestore) then {
    [_patient, _rhythmTimingRestore get "ACME_rhythmNativeHighHRFloorUntil", true, false, false] call ACME_fnc_rhythmNativeHighHRFloorCommit;
};
if ("ACME_rhythmNativeShockGraceUntil" in _rhythmTimingRestore) then {
    [_patient, _rhythmTimingRestore get "ACME_rhythmNativeShockGraceUntil", true, false] call ACME_fnc_rhythmNativeShockGraceCommit;
};
if (_hypoTempRestoreSet) then {
    [_patient, _hypoTempRestore, true, false, false] call ACME_fnc_hypothermiaTemperatureCommit;
};
if (_evacRestoreSet) then {
    [_patient, _evacRestore, true, false, false] call ACME_fnc_evacuationRequirementCommit;
};
if (_ventShuntRestoreSet) then {
    [_patient, _ventShuntRestore, true, false] call ACME_fnc_ventShuntCommit;
};
if (count _rocStressRestore > 0) then {
    [_patient,
        _rocStressRestore getOrDefault ["ACME_roc_postROSCGraceUntil", "KEEP"],
        _rocStressRestore getOrDefault ["ACME_roc_awakeDwell", "KEEP"],
        _rocStressRestore getOrDefault ["ACME_roc_awakeResistAdd", "KEEP"],
        _rocStressRestore getOrDefault ["ACME_hrDrive_roc", "KEEP"],
        true, false
    ] call ACME_fnc_rocStressStateCommit;
};
if (count _rocAwarenessRestore > 0) then {
    [_patient,
        _rocAwarenessRestore getOrDefault ["ACME_roc_awarenessEvent", "KEEP"],
        _rocAwarenessRestore getOrDefault ["ACME_roc_awarenessAt", "KEEP"],
        _rocAwarenessRestore getOrDefault ["ACME_roc_awarenessSeconds", "KEEP"],
        true, false
    ] call ACME_fnc_rocAwarenessStateCommit;
};
if (_rocAwakeRestoreSet) then {[_patient, _rocAwakeRestore, true, false, false] call ACME_fnc_rocAwakeParalysisCommit;};
if (_rocApneaRestoreSet) then {[_patient, _rocApneaRestore, true, false, false] call ACME_fnc_rocApneaCommit;};
if (count _bloodThermalRestore > 0) then {
    [_patient, objNull, objNull,
        _bloodThermalRestore getOrDefault ["ACME_coldBloodHungAt", objNull],
        _bloodThermalRestore getOrDefault ["ACME_tempFlagHoldUntil", objNull],
        true, false
    ] call ACME_fnc_bloodThermalStateCommit;
};
if (count _nrbRestore > 0) then {
    [_patient,
        _nrbRestore getOrDefault ["ACME_nrb_on", -1],
        _nrbRestore getOrDefault ["ACME_nrb_hasO2", -1],
        _nrbRestore getOrDefault ["ACME_nrb_delivering", -1],
        true, false
    ] call ACME_fnc_nrbStateCommit;
};
if (count _ettRestore > 0) then {
    [_patient,
        _ettRestore getOrDefault ["ACME_ETT_Inserted", -1],
        _ettRestore getOrDefault ["ACME_ETT_CuffInflated", -1],
        _ettRestore getOrDefault ["ACME_ETT_Secured", -1],
        _ettRestore getOrDefault ["ACME_ETT_Unsecured", -1],
        true, false
    ] call ACME_fnc_ettAirwayStateCommit;
};
if (_rocRestoreSet) then {
    [_patient, _rocRestore, true, false] call ACME_fnc_rocParalysisCommit;
};
if (_calciumRestoreSet) then {
    [_patient, _calciumRestore, "set", true, false] call ACME_fnc_calciumCreditCommit;
};
if (_toxicityFiredRestoreSet && {_toxicityFiredRestore isEqualType createHashMap}) then {
    [_patient, "set", "", -1, _toxicityFiredRestore, true] call ACME_fnc_medicationToxicityFiredCommit;
};
// Work resumes with fresh ownership, epochs and clocks; no old network request is replayed.
private _jobs = _patient getVariable ["ACME_yFlushJobs", createHashMap];
{private _j = _jobs get _x; _j set [6, if (count _j >= 13) then {serverTime} else {CBA_missionTime}]; _j set [8, _epoch];} forEach keys _jobs;
_patient setVariable ["ACME_yFlushJobs", _jobs, true];
private _moves = _patient getVariable ["ACME_bagMoves", createHashMap];
{private _m = _moves get _x; _m set [3, CBA_missionTime - 121]; _m set [4, _epoch];} forEach keys _moves;
_patient setVariable ["ACME_bagMoves", _moves, true];
{
    private _m = _patient getVariable [_x, createHashMap];
    if (count _m > 0) then {
        _m set ["lastTick", CBA_missionTime];
        if (_x isEqualTo "ACME_tbi_State") then {
            [_patient, _m] call ACME_fnc_tbiStateCommit;
        } else {
            [_patient, _m] call ACME_fnc_circStateCommit;
        };
    };
} forEach ["ACME_circ_State", "ACME_tbi_State"];
if (_patient getVariable ["ACME_nrb_on", false]) then {
    private _medic = _patient getVariable ["ACME_nrb_medic", objNull];
    private _oxygen = _patient getVariable ["ACME_nrb_hasO2", false];
    [_patient, false, -1, -1, true, false] call ACME_fnc_nrbStateCommit;
    [_patient, _medic, true, _oxygen && {!isNull _medic} && {alive _medic}, true] call ACME_fnc_nrbStateLocal;
};
[_patient, -1, -1, false, true, false] call ACME_fnc_nrbStateCommit;
_patient setVariable ["ACME_nrb_lastDrawSend", -1, false];
_patient setVariable ["ACME_nrb_sfxWanted", nil, false];
_patient setVariable ["ACME_vent_driving", false, true];
_patient setVariable ["ACME_vent_effectiveRR", 0, true];
_patient setVariable ["ACME_clinicalLastOwner", -1, false];
// Ordered after the reset event, from the same sender. Server owns the chest edit epoch and snapshot.
["ACME_clinicalChestRestore", [_patient, _chest, _epoch]] call CBA_fnc_serverEvent;
[_patient] call ACME_fnc_ownerRegister;
[_patient] call ace_medical_status_fnc_updateWoundBloodLoss;
