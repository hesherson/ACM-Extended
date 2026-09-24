/* NA2: explicit patient-owner commands; never accept arbitrary code/function names.
   Called by CBA in an unscheduled scope. A locality change in transit is rerouted. */
params ["_patient", "_operation", ["_args", []], ["_hops", 0]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {
    if (_hops < 4) then {
        ["ACME_ownerCommand", [_patient, _operation, _args, _hops + 1], _patient] call CBA_fnc_targetEvent;
    } else {  };
};
switch (_operation) do {
    case "vialLease": {
        _args params [["_medic",objNull,[objNull]],["_op","claim",[""]],["_token","",[""]]];
        [_patient,_medic,_op,_token] call ACME_fnc_vialLeaseCommit;
    };
    case "careGrace": {
        _args params [["_duration", 0, [0]]];
        if (finite _duration && {_duration >= 0}) then {
            _patient setVariable ["ACME_beingTreated_until", CBA_missionTime + _duration, false];
        };
    };
    case "bvmBreath": {
        _args params [["_oxygen", false, [false]]];
        private _now = CBA_missionTime;
        private _changes = [["bvmLastBreath", _now]];
        if (_oxygen) then {_changes pushBack ["bvmLastBreathOxygen", _now];};
        [_patient, _changes, true] call ACM_breathing_fnc_setRuntimeState;
        // Presentation/observer freshness uses a clock shared by every client.
        _patient setVariable ["ACME_bvm_lastBreathServer", serverTime, true];
    };
    case "bvmTelemetry": {
        _args params [["_rate", 0, [0]]];
        if (finite _rate && {_rate >= 0} && {_rate <= 80}) then {
            [_patient, "ACME_bvm_rate", _rate] call ACME_fnc_setVarNet;
            _patient setVariable ["ACME_bvm_lastBreathServer", serverTime, true];
        };
    };
    case "breathingState": {
        _args params [["_changes", [], [[]]], ["_public", true, [true]]];
        [_patient, _changes, _public] call ACM_breathing_fnc_setRuntimeState;
    };
    case "stethoscopeLungs": {
        _args params [["_epoch",-1]];
        if (alive _patient && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)}
            && {CBA_missionTime >= (_patient getVariable ["ACME_stethNextLungUpdate",-1])}) then {
            _patient setVariable ["ACME_stethNextLungUpdate",CBA_missionTime + 0.5];
            [_patient] call ACM_breathing_fnc_updateLungState;
        };
    };
    case "suctionState": {_args call ACME_fnc_suctionStateLocal;};
    case "ecgJostle": {_args call ACME_fnc_ecgJostleLocal;};
    case "medicationLine": {_args call ACME_fnc_medicationLineLocal;};
    // Small non-bag crystalloid boluses still contribute real circulating volume. Route the mutation through
    // the casualty owner so it cannot race the native circulation integrator on another machine.
    case "crystalloidCredit": {
        _args params [["_liters", 0, [0]]];
        if (finite _liters && {_liters > 0}) then {
            [_patient, [["salineVolume", (_patient getVariable ["ACM_circulation_Saline_Volume", 0]) + _liters]], true] call ACM_circulation_fnc_setRuntimeState;
        };
    };
    case "headElevHoldStart": {_args call ACME_fnc_headElevHoldStart;};
    case "headElevHoldRelease": {_args call ACME_fnc_headElevHoldRelease;};
    case "headElevHoldStop": {_args call ACME_fnc_headElevHoldStop;};
    case "headElevTreatment": {_args call ACME_fnc_headElevTreatmentEvent;};
    case "chestAccessVestEvent": {_args call ACME_fnc_chestAccessVestEvent;};
    case "chestAccessVestProvider": {_args call ACME_fnc_chestAccessVestProvider;};
    case "chestAccessFrontRoll": {
        _args params [["_medic",objNull,[objNull]],["_casualty",objNull,[objNull]]];
        if (!isNull _medic && {local _medic} && {alive _medic} && {!isNull _casualty}) then {
            [_medic,"chestAccessFront",_casualty] call ACME_fnc_rollProviderStart;
        };
    };
    case "headElevTilt": {_args call ACME_fnc_headElevApplyTilt;};
    case "headElevCollision": {_args call ACME_fnc_headElevCollision;};
    case "headElevSuspend": {_args call ACME_fnc_headElevSuspend;};
    case "headElevTryResume": {_args call ACME_fnc_headElevTryResume;};
    case "headElevResume": {_args call ACME_fnc_headElevResume;};
    case "headElevStart": {_args call ACME_fnc_headElevateStart;};
    case "headElevStop": {_args call ACME_fnc_headElevateStop;};
    case "headElevDeath": {[_patient] call ACME_fnc_headElevDeathRelease;};
    case "headElevMedicStart": {_args call ACME_fnc_headElevMedicStart;};
    case "headElevMedicSeq": {_args call ACME_fnc_headElevMedicSeq;};
    case "airwayGradeState": {
        _args params [["_candidate", [], [[]]], ["_bump", 0, [0]]];
        if (count _candidate == 2) then {
            private _cached = +(_patient getVariable ["ACME_airwayGrade", []]);
            private _worst = if (count _cached == 2) then {
                [((_cached select 0) max (_candidate select 0)) min 4,
                 ((_cached select 1) max (_candidate select 1)) min 4]
            } else {+_candidate};
            if !(_cached isEqualTo _worst) then {_patient setVariable ["ACME_airwayGrade", _worst, true];};
            private _oldBump = _patient getVariable ["ACME_airwayTraumaBump", -1];
            if (_bump > _oldBump) then {_patient setVariable ["ACME_airwayTraumaBump", _bump, true];};
        };
    };
    case "laryngoAnatomy": {
        _args params [["_fulc", -1, [0]], ["_ideal", -1, [0]]];
        if ((_patient getVariable ["ACME_laryngo_fulcNeed", -1]) < 1 && {_fulc >= 1 && {_fulc <= 5}}) then {
            _patient setVariable ["ACME_laryngo_fulcNeed", _fulc, true];
        };
        if ((_patient getVariable ["ACME_ETT_IdealFrame", -1]) < 1 && {_ideal >= 5 && {_ideal <= 8}}) then {
            _patient setVariable ["ACME_ETT_IdealFrame", _ideal, true];
        };
    };
    case "laryngoFluidDrain": {_args call ACME_fnc_laryngoFluidDrainLocal;};
    case "ettAirwayState": {
        _args params ["_inserted", "_cuff", "_secured", "_unsecured", ["_public", true], ["_dedupe", false]];
        [_patient, _inserted, _cuff, _secured, _unsecured, _public, _dedupe] call ACME_fnc_ettAirwayStateCommit;
    };
    case "ettMigrationState": {
        _args params [["_op", "", [""]], ["_data", [], [[]]]];
        [_patient, _op, _data] call ACME_fnc_ettMigrationStateCommit;
    };
    case "ettMigrate": {
        _args params [["_severity", 1, [0]]];
        [_patient, _severity] call ACME_fnc_ettMigrate;
    };
    case "ettCuffDone": {
        _args params [["_medic", objNull, [objNull]], ["_tubeCommitted", false, [false]], ["_rammed", false, [false]], ["_timeToTube", 0, [0]]];
        if (_tubeCommitted) then {
            [_patient, true, true, -1, -1, true, false] call ACME_fnc_ettAirwayStateCommit;
            _patient setVariable ["ACME_ETT_Medic", _medic, true];
            _patient setVariable ["ACME_ETT_Time", CBA_missionTime, true];
            _patient setVariable ["ACME_ETT_Trauma", _rammed, true];
            _patient setVariable ["ACME_ETT_Passes", (_patient getVariable ["ACME_laryngo_failCount", 0]) + 1, true];
            _patient setVariable ["ACME_ETT_TimeToTube", _timeToTube max 0, true];
        } else {
            [_patient, -1, true, -1, -1, true, false] call ACME_fnc_ettAirwayStateCommit;
        };
    };
    case "ettExtubate": {
        _args params [["_medic", objNull, [objNull]]];
        if (_patient getVariable ["ACME_ETT_Inserted", false]) then {
            [_patient, false, false, false, false, true, false] call ACME_fnc_ettAirwayStateCommit;
            [_patient, "placement", [0, 0, false]] call ACME_fnc_ettMigrationStateCommit;
            [_patient, "obstruction", [false, 0]] call ACME_fnc_ettMigrationStateCommit;
            [_patient, "tip", [[]]] call ACME_fnc_ettMigrationStateCommit;
            _patient setVariable ["ACME_o2Drain_mainstem", 0, true];
            _patient setVariable ["ACME_vent_complianceMult", 1, true];
            _patient setVariable ["ACME_ETT_Trauma", false, true];
            _patient setVariable ["ACME_ETT_Medic", objNull, true];
            _patient setVariable ["ACME_ETT_Time", 0, true];
            if (_patient getVariable ["ACME_vent_connected", false]) then {
                _patient setVariable ["ACME_vent_connected", false, true];
                _patient setVariable ["ACME_vent_driving", false, true];
            };
            if (!isNil "ace_medical_treatment_fnc_addToLog") then {
                [_patient, "airway", "Extubated: ET tube removed", []] call ace_medical_treatment_fnc_addToLog;
            };
            if (!isNull _medic) then {["ACME_ettReturnTube", [_medic], _medic] call CBA_fnc_targetEvent;};
        };
    };
    case "laryngoConsequence": {_args call ACME_fnc_laryngoConsequenceLocal;};
    case "laryngoStimulus": {_args call ACME_fnc_laryngoStimulusLocal;};
    case "infusionClamp": {_args call ACME_fnc_infusionClampLocal;};
    case "pressureCuff": {_args call ACME_fnc_pressureInfuserCommit;};
    case "ivState": {_args call ACME_fnc_ivStateLocal;};
    case "ivMarks": {
        _args params [["_op", "", [""]], ["_data", [], [[]]], ["_epoch", -1, [0]]];
        [_patient, _op, _data, _epoch] call ACME_fnc_ivMarkCommit;
    };
    case "ivCompromised": {
        _args params [["_bodyPart", "", [""]], ["_site", -1, [0]], ["_mode", "set", [""]]];
        private _bp = toLower _bodyPart;
        if (_bp == "ej") then {_bp = "head";};
        if (_bp != "" && {_site >= 0}) then {
            private _key = format ["ACME_ivCompromised_%1_%2", _bp, _site];
            if (toLower _mode == "clear") then {_patient setVariable [_key, nil, true];}
            else {_patient setVariable [_key, true, true];};
        };
    };
    case "ivSite": {_args call ACME_fnc_ivPlacementLocal;};
    case "preparedAttach": {_args call ACME_fnc_preparedAttachLocal;};
    case "preparedHang": {_args call ACME_fnc_preparedHangCommit;};
    case "arrest": {_args call ACME_fnc_arrestLocal;};
    case "rhythmSet": {_args call ACME_fnc_rhythmSet;};
    case "rhythmToggle": {_args call ACME_fnc_rhythmToggle;};
    case "shock": {_args call ACME_fnc_shockLocal;};
    case "syncArmed": {
        _args params [["_medic", objNull, [objNull]], ["_armed", false, [false]], ["_epoch", -1, [0]]];
        if (!isNull _medic && {alive _medic} && {[_medic] call ace_common_fnc_isAwake}
            && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)}
            && {(_medic distance _patient) <= ace_medical_gui_maxDistance}
            && {[_patient, "", 1] call ACM_circulation_fnc_hasAED}) then {
            _patient setVariable ["ACME_sync_armed", _armed, true];
        };
    };
    case "aajtApply": {_args call ACME_fnc_aajtApply;};
    case "aajtRemove": {_args call ACME_fnc_aajtRemove;};
    case "aajtState": {_args call ACME_fnc_aajtStateCommit;};
    case "aajtGrace": {
        _args params [["_duration", 0, [0]]];
        if (finite _duration && {_duration >= 0}) then {
            _patient setVariable ["ACME_AAJT_treatmentGraceUntil", CBA_missionTime + _duration, false];
        };
    };
    case "aajtApplying": {
        _args params [["_part", "", [""]], ["_active", false, [false]]];
        if (_active) then {
            _patient setVariable ["ACME_Junc_AAJTApplying", [serverTime, toLowerANSI _part], true];
        } else {
            _patient setVariable ["ACME_Junc_AAJTApplying", [], true];
        };
    };
    case "xstatApply": {
        _args params [["_medic", objNull, [objNull]], ["_part", "", [""]]];
        [_medic, _patient, _part] call ACME_fnc_xstatApply;
    };
    case "aajtFlow": {_args call ACME_fnc_aajtSetLegTQ;};
    case "directPressureMarker": {
        _args params [["_medic", objNull, [objNull]], ["_bodyPart", "", [""]], ["_active", false, [false]]];
        private _part = toLower _bodyPart;
        if (_part == "") exitWith {};
        private _key = format ["ACME_DP_press_%1", _part];
        if (_active) then {
            // Provider-local state identifies the exact hold. The patient owner alone publishes the clinical marker.
            if (!isNull _medic
                && {_medic getVariable ["ACME_DP_Active", false]}
                && {(_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient}
                && {(_medic getVariable ["ACME_DP_Part", ""]) == _part}
                && {alive _medic}
                && {!(_medic getVariable ["ACE_isUnconscious", false])}) then {
                _patient setVariable [_key, _medic, true];
                if (_part == "body") then {_patient setVariable ["ACME_DP_TorsoMedic", _medic, true];}
                else {_patient setVariable ["ACME_DP_LimbMedic", _medic, true];};
            };
        } else {
            // A stale stop/disconnect may never clear another provider's newer replacement hold.
            if ((_patient getVariable [_key, objNull]) isEqualTo _medic) then {
                _patient setVariable [_key, objNull, true];
            };
            if ((_patient getVariable ["ACME_DP_TorsoMedic", objNull]) isEqualTo _medic) then {
                _patient setVariable ["ACME_DP_TorsoMedic", objNull, true];
            };
            if ((_patient getVariable ["ACME_DP_LimbMedic", objNull]) isEqualTo _medic) then {
                _patient setVariable ["ACME_DP_LimbMedic", objNull, true];
            };
        };
        if (_part in ["leftarm", "rightarm", "leftleg", "rightleg"]) then {
            [_patient] call ace_medical_status_fnc_updateWoundBloodLoss;
        };
    };
    case "directPressureClot": {
        _args params [["_medic", objNull, [objNull]], ["_bodyPart", "", [""]]];
        private _part = toLower _bodyPart;
        if (!isNull _medic && {_part != ""}
            && {_medic getVariable ["ACME_DP_Active", false]}
            && {(_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient}
            && {(_medic getVariable ["ACME_DP_Part", ""]) == _part}
            && {(_patient getVariable [format ["ACME_DP_press_%1", _part], objNull]) isEqualTo _medic}) then {
            [_patient, _part, 2, 3, true, false] call ACM_damage_fnc_clotWoundsOnBodyPart;
        };
    };
    case "junctionalPackStart": {
        _args params [["_medic", objNull, [objNull]], ["_bodyPart", "", [""]], ["_duration", 10, [0]]];
        private _part = toLower _bodyPart;
        if (_part != "") then {
            _patient setVariable [format ["ACME_Junc_Packing_%1", _part], true, true];
            private _now = CBA_missionTime;
            private _lastStim = _patient getVariable ["ACME_DP_FracturePainLast", -1e6];
            private _stimPart = toLower (_patient getVariable ["ACME_DP_FracturePainPart", ""]);
            if ((_now - _lastStim) <= 15 && {_stimPart == _part} && {_patient call ace_common_fnc_isAwake}) then {
                private _stable = !isNil "ace_medical_status_fnc_hasStableVitals"
                    && {[_patient] call ace_medical_status_fnc_hasStableVitals};
                if (_stable) then {
                    private _until = (_patient getVariable ["ACME_obtunded_wakeStimGraceUntil", 0])
                        max (_now + (_duration max 0) + 4);
                    _patient setVariable ["ACME_obtunded_wakeStimGraceUntil", _until, false];
                };
            };
        };
    };
    case "junctionalPackDone": {
        _args params [["_medic", objNull, [objNull]], ["_bodyPart", "", [""]]];
        private _part = toLower _bodyPart;
        if (_part != "") then {
            _patient setVariable [format ["ACME_Junc_%1", _part], "packed", true];
            _patient setVariable [format ["ACME_Junc_Packing_%1", _part], false, true];
            if (_patient call ace_common_fnc_isAwake) then {
                [_patient, missionNamespace getVariable ["ACME_junctionalPackPain", 0.2]] call ace_medical_fnc_adjustPainLevel;
            };
        };
    };
    case "junctionalWrapDone": {
        _args params [["_medic", objNull, [objNull]], ["_bodyPart", "", [""]]];
        private _part = toLower _bodyPart;
        if (_part != "") then {
            _patient setVariable [format ["ACME_Junc_%1", _part], "wrapped", true];
            _patient setVariable [format ["ACME_Junc_PackedAt_%1", _part], -1, true];
            if (!isNil "ACM_damage_fnc_clotWoundsOnBodyPart") then {
                [_patient, _part, 5, 4, false] call ACM_damage_fnc_clotWoundsOnBodyPart;
            };
            if (_patient call ace_common_fnc_isAwake) then {
                [_patient, missionNamespace getVariable ["ACME_junctionalWrapPain", 0.2]] call ace_medical_fnc_adjustPainLevel;
            };
        };
    };
    case "junctionalInflict": {_args call ACME_fnc_junctionalInflict;};
    case "junctional": {_args call ACME_fnc_junctionalResume;};
    case "restore": {_args call ACME_fnc_clinicalRestore;};
    case "infusionRegister": {_args call ACME_fnc_infusionRegisterLocal;};
    case "infusionRemove": {_args call ACME_fnc_infusionRemoveLocal;};
    case "transfusionRemoveBag": {_args call ACME_fnc_transfusionRemoveBagCommit;};
    case "transfusionFlowToggle": {_args call ACME_fnc_transfusionFlowToggleCommit;};
    case "transfusionPull": {_args call ACME_fnc_transfusionPullCommit;};
    case "rehangUsedBag": {_args call ACME_fnc_rehangUsedBagCommit;};
    case "yRefill": {_args call ACME_fnc_yRefillCommit;};
    case "discardYTubing": {_args call ACME_fnc_discardYTubingCommit;};
    case "yFlush": {_args call ACME_fnc_yFlushStart;};
    case "bagMove": {_args call ACME_fnc_clinicalBagMove;};
    case "hangBagClaim": {isNil {[_patient, "claim", _args] call ACME_fnc_hangBagClaimLocal;};};
    case "hangBagRenew": {isNil {[_patient, "renew", _args] call ACME_fnc_hangBagClaimLocal;};};
    case "hangBagRelease": {isNil {[_patient, "release", _args] call ACME_fnc_hangBagClaimLocal;};};
    case "register": { [_patient] call ACME_fnc_ownerRegister; };
    case "hpmkState": { _args call ACME_fnc_hpmkStateCommit; };
    case "hpmkPrep": { _args call ACME_fnc_hpmkPrep; };
    case "hpmkWrap": { _args call ACME_fnc_hpmkWrap; };
    case "hpmkUnwrap": { _args call ACME_fnc_hpmkUnwrap; };
    case "hpmkRemove": { _args call ACME_fnc_hpmkRemove; };
    case "autoBP": { _args call ACME_fnc_toggleAutoBP; };
    case "cheyne": { _args call ACME_fnc_debugCheyneStokes; };
    case "debugSeizure": { _args call ACME_fnc_debugInduceSeizure; };
    case "tbiInit": { _args call ACME_fnc_tbiInit; };
    case "thoraDrain": { [_patient] call ACME_fnc_thoraPassiveDrain; };
    case "thoraAftercare": {_args call ACME_fnc_thoraAftercareLocal;};
    case "nrbState": { _args call ACME_fnc_nrbStateLocal; };
    case "nrbAck": { _args call ACME_fnc_nrbOxygenAck; };
    case "chestEffect": { _args call ACME_fnc_chestSealEffectLocal; };
    case "burp": { _args call ACME_fnc_chestSealBurp; };
    case "chestSealRoll": {_args call ACME_fnc_chestSealRoll;};
    case "patientRollCancel": {_args call ACME_fnc_patientRollCancel;};
    case "chestSealPatientBegin": {_args call ACME_fnc_chestSealPatientBegin;};
    case "chestSealPatientEnd": {_args call ACME_fnc_chestSealPatientEnd;};
    case "patientAnimRequest": {_args call ACME_fnc_patientAnimRequest;};
    case "patientAnimRelease": {_args call ACME_fnc_patientAnimRelease;};
    case "ventManualBreath": {_args call ACME_fnc_ventManualBreathCommit;};
    case "ventBattery": {
        _patient setVariable ["ACME_vent_battery", 100, true];
        _patient setVariable ["ACME_vent_battWarned", 0, true];
    };
    case "ventPowerState": {
        _args params [
            ["_medic", objNull, [objNull]],
            ["_on", false, [false]],
            ["_hasBooted", false, [false]],
            ["_custody", "", [""]]
        ];
        if (!isNull _medic && {alive _medic} && {[_medic] call ace_common_fnc_isAwake}
            && {(_medic distance _patient) <= ace_medical_gui_maxDistance}
            && {(_custody == "") || {(_patient getVariable ["ACME_vent_custodyId", ""]) == _custody}}) then {
            _patient setVariable ["ACME_vent_powerOn", _on, true];
            _patient setVariable ["ACME_vent_hasBooted", _hasBooted, true];
        };
    };
    case "ventHardStop": {_args call ACME_fnc_ventHardStopCommit;};
    case "ventBatteryExchange": {
        _args params [
            ["_medic", objNull, [objNull]],
            ["_requestId", "", [""]],
            ["_sparePct", 100, [0]],
            ["_sentAt", 0, [0]]
        ];
        if (isNull _medic || {_requestId == ""}) exitWith {};
        private _receipts = +(_patient getVariable ["ACME_vent_batterySwapReceipts", []]);
        if (_requestId in _receipts) exitWith {};
        _receipts pushBack _requestId;
        if (count _receipts > 24) then {_receipts deleteRange [0, count _receipts - 24];};
        _patient setVariable ["ACME_vent_batterySwapReceipts", _receipts, true];

        private _valid = alive _medic
            && {[_medic] call ace_common_fnc_isAwake}
            && {(_medic distance _patient) <= ace_medical_gui_maxDistance}
            && {abs (serverTime - _sentAt) <= 12};
        private _lockUntil = _patient getVariable ["ACME_vent_batterySwapLockUntil", -1];
        private _accepted = _valid && {serverTime >= _lockUntil};
        private _returned = _medic getVariable ["ACME_vent_spareBattery", 100];
        if (_accepted) then {
            _returned = _patient getVariable ["ACME_vent_battery", 100];
            _patient setVariable ["ACME_vent_battery", (_sparePct max 0) min 100, true];
            _patient setVariable ["ACME_vent_battWarned", 0, true];
            // Long enough to reject a second provider who completed the same 4.375 s physical hatch exchange.
            _patient setVariable ["ACME_vent_batterySwapLockUntil", serverTime + 1.0, true];
        };
        ["ACME_ventBatteryExchangeResult", [_patient, _requestId, _accepted, _returned, (_sparePct max 0) min 100], _medic] call CBA_fnc_targetEvent;
    };
    case "treatmentPatientSettle": {_args call ACME_fnc_treatmentPatientSettle;};
};
