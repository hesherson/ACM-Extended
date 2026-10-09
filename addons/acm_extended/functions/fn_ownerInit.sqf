// NA2 owner lifecycle. One shared recovery scan supplements event-driven registration.
if (missionNamespace getVariable ["ACME_NA2_ownerInstalled", false]) exitWith {};
ACME_NA2_ownerInstalled = true;
["ACME_ownerCommand", { isNil { _this call ACME_fnc_ownerDispatch; }; }] call CBA_fnc_addEventHandler;
["ACME_netNotice", { _this call ACME_fnc_netNotice; }] call CBA_fnc_addEventHandler;
["ACME_aiProtectionRefresh", {
    params [["_unit", objNull, [objNull]]];
    if (isNull _unit || {!local _unit}) exitWith {};
    [_unit] call ACME_fnc_aiProtectionSync;
    // Re-read owner state after the corresponding replicated flag/animation notification. Never queue a wanted boolean.
    [{_this call ACME_fnc_aiProtectionSync;}, [_unit]] call CBA_fnc_execNextFrame;
}] call CBA_fnc_addEventHandler;
["ACME_manualSuctionSound", {_this call ACME_fnc_manualSuctionSound;}] call CBA_fnc_addEventHandler;
["ACME_worldSfx", { if (hasInterface) then {_this call ACME_fnc_remoteSay3D;}; }] call CBA_fnc_addEventHandler;
["ACME_seizureGestureSync", { _this call ACME_fnc_seizureGestureSync; }] call CBA_fnc_addEventHandler;
["ACME_transfusionRemoveResult", {_this call ACME_fnc_transfusionRemoveBagResult;}] call CBA_fnc_addEventHandler;
["ACME_transfusionPullResult", {_this call ACME_fnc_transfusionPullResult;}] call CBA_fnc_addEventHandler;
["ACME_rehangUsedBagResult", {_this call ACME_fnc_rehangUsedBagResult;}] call CBA_fnc_addEventHandler;
["ACME_yRefillResult", {_this call ACME_fnc_yRefillResult;}] call CBA_fnc_addEventHandler;
["ACME_discardYTubingResult", {_this call ACME_fnc_discardYTubingResult;}] call CBA_fnc_addEventHandler;
["ACME_vialLeaseResult", {_this call ACME_fnc_vialLeaseResult;}] call CBA_fnc_addEventHandler;
["ACME_supplySettle", {_this call ACME_fnc_treatmentSupplyRefund;}] call CBA_fnc_addEventHandler;
["ACME_hpmkReturnItem", {
    params [["_receiver", objNull, [objNull]]];
    if (!isNull _receiver && {local _receiver}) then {
        [_receiver, "ACM_HPMK"] call ace_common_fnc_addToInventory;
    };
}] call CBA_fnc_addEventHandler;
["ACME_ettReturnTube", {
    params [["_receiver", objNull, [objNull]]];
    if (!isNull _receiver && {local _receiver}) then {
        [_receiver, "ACME_ETTube"] call ace_common_fnc_addToInventory;
    };
}] call CBA_fnc_addEventHandler;
["ACME_aajtReturnItem", {
    params [["_receiver", objNull, [objNull]]];
    if (!isNull _receiver && {local _receiver}) then {
        [_receiver, "ACME_AAJT_S"] call ace_common_fnc_addToInventory;
    };
}] call CBA_fnc_addEventHandler;
["ACME_ventBatteryExchangeResult", {
    params [
        ["_patient", objNull, [objNull]],
        ["_requestId", "", [""]],
        ["_accepted", false, [false]],
        ["_returnedPct", 100, [0]],
        ["_installedPct", 100, [0]]
    ];
    if (!hasInterface || {isNull ACE_player}) exitWith {};
    private _pending = uiNamespace getVariable ["ACME_vent_batterySwapRequest", ""];
    if (_pending != _requestId) exitWith {};
    uiNamespace setVariable ["ACME_vent_batterySwapRequest", ""];
    private _supply = uiNamespace getVariable ["ACME_vent_batterySwapSupply", []];
    uiNamespace setVariable ["ACME_vent_batterySwapSupply", []];
    if (count _supply == 4) then {
        private _source = if (isNull (_supply select 2)) then {_supply select 0} else {_supply select 2};
        if (_accepted && {!isNull _source}) then {_source setVariable ["ACME_vent_spareBattery", _returnedPct, true];};
        [_supply] call ACME_fnc_treatmentSupplyRefund;
    };
    private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
    if (_accepted) then {
        // Compatibility with an already-issued pre-B156 exchange without an item reservation.
        if (_supply isEqualTo []) then {ACE_player setVariable ["ACME_vent_spareBattery", _returnedPct, true];};
        if (!isNull _dlg && {(uiNamespace getVariable ["ACME_vent_target", objNull]) isEqualTo _patient}) then {
            private _ban = _dlg displayCtrl 88001;
            _ban ctrlSetText format ["BATTERY %1%2 OFF", round _installedPct, "%"];
            _ban ctrlShow true;
            uiNamespace setVariable ["ACME_vent_swapMsgUntil", diag_tickTime + 2.5];
        };
    } else {
        if (!isNull _dlg) then {
            private _ban = _dlg displayCtrl 88001;
            _ban ctrlSetText "SWAP CONFLICT";
            _ban ctrlShow true;
            uiNamespace setVariable ["ACME_vent_swapMsgUntil", diag_tickTime + 2.5];
        };
        ["Battery swap cancelled: another provider changed this ventilator.", 2, ACE_player] call ace_common_fnc_displayTextStructured;
    };
}] call CBA_fnc_addEventHandler;
["ACME_nrbDraw", { isNil { _this call ACME_fnc_nrbOxygenDraw; }; }] call CBA_fnc_addEventHandler;
["ACME_nrbSound", { _this call ACME_fnc_nrbSoundServer; }] call CBA_fnc_addEventHandler;
["ACME_thoraOutput", { if (isServer) then { isNil { _this call ACME_fnc_thoraOutput; }; }; }] call CBA_fnc_addEventHandler;
["CAManBase", "Local", {
    params ["_unit", "_isLocal"];
    [_unit, "retire"] call ACME_fnc_aiProtectionSync;
    private _ownedNow = missionNamespace getVariable ["ACME_clinical_ownedUnits", []];
    if (_isLocal && {alive _unit}) then {_ownedNow pushBackUnique _unit;} else {_ownedNow = _ownedNow - [_unit];};
    missionNamespace setVariable ["ACME_clinical_ownedUnits", _ownedNow];
    // IO syncope timers are machine-local. A departed owner's job must neither
    // resume after an away/back transfer nor strand the returning owner's token.
    _unit setVariable ["ACME_ioSyncopeToken", -1, false];
    // Also invalidates an old callback on an away-and-back locality change.
    _unit setVariable ["ACME_wakeRepairTicket", (_unit getVariable ["ACME_wakeRepairTicket", 0]) + 1, false];
    // Provider input workers must also retire after away/back transfers between their scheduled ticks.
    _unit setVariable ["ACME_providerLocalityEpoch", (_unit getVariable ["ACME_providerLocalityEpoch", 0]) + 1, false];
    // B268: carrier preparation callbacks belong to this exact local ownership
    // period. Clear machine-local wait markers on both edges, including rapid
    // away/back transfers. Replicated custody/clinical leases remain intact.
    {
        _unit setVariable [_x, "", false];
    } forEach ["ACME_chestAccess_frontBusy", "ACME_CS_frontBusy",
        "ACME_chestAccess_vestBusy", "ACME_CS_vestBusy", "ACME_chestAccess_requestToken"];
    if (_isLocal) then {
        // A migrated carrier lift has no completion on the incoming machine.
        // Release only its exact finite animation lease; a stronger/newer
        // patient controller keeps its token, animation, speed and collision.
        private _carrierLock = _unit getVariable ["ACME_patientAnimLock", []];
        private _carrierToken = _carrierLock param [0, ""];
        if (_carrierToken != "" && {(_carrierLock param [1, ""]) in
            ["chest-access-vest", "chest-access-vest-restore"]}) then {
            [_unit, _carrierToken] call ACME_fnc_patientAnimRelease;
        };
    };
    // Pending prone-to-Semi-Fowler normalization has no active pose yet. Retire it on BOTH local transitions,
    // so returning to this machine cannot revive a callback from its previous ownership period.
    _unit setVariable ["ACME_headElev_startEpoch", (_unit getVariable ["ACME_headElev_startEpoch", 0]) + 1, false];
    [_unit] call ACME_fnc_aajtDownedStop;
    private _headPFH = _unit getVariable ["ACME_headElev_pfh", -1];
    if (_headPFH >= 0) then {[_headPFH] call CBA_fnc_removePerFrameHandler;};
    _unit setVariable ["ACME_headElev_pfh", -1];
    // B249: respiration audio PFH IDs are local machine handles. Retire them on
    // BOTH locality edges so a quick away/back handoff cannot strand a stale
    // "already running" marker or leave two sound emitters behind.
    private _breathPFH = _unit getVariable ["ACME_bs_pfh", -1];
    if (_breathPFH >= 0) then {[_breathPFH] call CBA_fnc_removePerFrameHandler;};
    _unit setVariable ["ACME_bs_pfh", -1, false];
    private _headEH = _unit getVariable ["ACME_headElev_killEH", -1];
    if (_headEH >= 0) then {_unit removeEventHandler ["Killed", _headEH];};
    _unit setVariable ["ACME_headElev_killEH", -1];
    _unit setVariable ["ACME_net_scalarCache", createHashMap, false];
    _unit setVariable ["ACME_net_cacheOwner", [], false];
    _unit setVariable ["ACME_net_approxCache", createHashMap, false];
    _unit setVariable ["ACME_net_approxOwner", [], false];
    // Every ownership transition starts a new publication epoch, including away/back to the same machine.
    // These are local suppression caches only; replicated physiology remains intact for the new owner.
    {
        _unit setVariable [_x, [], false];
    } forEach ["ACME_circ_stateNetOwner", "ACME_tbi_stateNetOwner", "ACME_infusion_netOwner", "ACM_circulation_ForkStatePublishOwner", "ACM_breathing_ForkStatePublishOwner"];
    {
        _unit setVariable [_x, createHashMap, false];
    } forEach ["ACM_circulation_ForkStatePublished", "ACM_breathing_ForkStatePublished"];
    _unit setVariable ["ACME_ivBagsPublishedSig", nil, false];
    _unit setVariable ["ACME_medicationDriveFlushToken", [], false];
    _unit setVariable ["ACME_medicationDriveNetAt", -1, false];
    _unit setVariable ["ACME_clinicalLastOwner", -1];
    _unit setVariable ["ACME_nativeWorkerOwner", nil, false];
    _unit setVariable ["ACME_alt_ptxSample", nil, false];
    _unit setVariable ["ACME_nativeVomitWorker", [], false];
    {
        private _h = _unit getVariable [_x, -1];
        if (_h >= 0) then {[_h] call CBA_fnc_removePerFrameHandler;};
        _unit setVariable [_x, -1, false];
    } forEach ["ACM_circulation_CardiacArrest_PFH", "ACM_circulation_ReversibleCardiacArrest_PFH", "ACM_airway_AirwayObstructionVomit_PFH", "ACM_breathing_Pneumothorax_PFH", "ACM_airway_AirwayCollapse_PFH", "ACM_airway_AirwayObstructionBlood_PFH", "ACM_circulation_HemolyticReaction_PFH"];
    {if ((_x find "acme_clock_") == 0) then {_unit setVariable [_x, nil, false];};} forEach allVariables _unit;
    private _juncHandle = _unit getVariable ["ACME_juncPFH", -1];
    if (_juncHandle >= 0) then {[_juncHandle] call CBA_fnc_removePerFrameHandler;};
    _unit setVariable ["ACME_juncPFH", -1]; _unit setVariable ["ACME_juncWorker", []];
    // Remove stale machine-local work immediately, including a quick away/back transfer.
    {
        private _list = missionNamespace getVariable [_x, []];
        missionNamespace setVariable [_x, _list - [_unit]];
    } forEach ["ACME_nrb_activePatients", "ACME_hpmk_activePatients", "ACME_tbi_activePatients", "ACME_cs_activePatients", "ACME_autoBP_patients", "ACME_clinical_activePatients", "ACME_infusion_activePatients", "ACME_circ_activePatients", "ACME_coag_activePatients", "ACME_preox_activePatients", "ACME_aspiration_activePatients", "ACME_shock_activePatients", "ACME_rhythmThreshold_activePatients", "ACME_rhythm_activePatients"];
    private _drain = _unit getVariable ["ACME_thora_drainPFH", -1];
    if (_drain >= 0) then { [_drain] call CBA_fnc_removePerFrameHandler; };
    _unit setVariable ["ACME_thora_drainPFH", -1, false];
    _unit setVariable ["ACME_nrb_lastTickLocal", nil, false];
    _unit setVariable ["ACME_hpmk_lastTickLocal", nil, false];
    _unit setVariable ["ACME_nrb_lastDrawSend", -1, false];
    _unit setVariable ["ACME_nrb_sfxWanted", nil, false];
    // B255 Direct Pressure locality teardown.
    // The outgoing PFH may never tick again after a rapid away/back transfer;
    // retire its exact patient claim.
    private _dpPatient = _unit getVariable ["ACME_DP_Patient", objNull];
    private _dpPart = _unit getVariable ["ACME_DP_Part", ""];
    private _dpToken = _unit getVariable ["ACME_DP_ClaimToken", ""];
    private _dpEpoch = _unit getVariable ["ACME_DP_ClaimEpoch", -1];
    if (!isNull _dpPatient && {_dpPart != ""} && {_dpToken != ""}) then {
        [_dpPatient, "directPressureClaim", ["release", [_unit, _dpPart, _dpToken, _dpEpoch]]] call ACME_fnc_ownerDispatch;
        // Only the incoming owner may clear the inherited public provider state.
        if (_isLocal) then {
            [_unit, _dpPatient, _dpPart, _dpToken, _dpEpoch] call ACME_fnc_directPressureRetire;
        };
    };
    // Claims without an ACK are not yet represented by active patient fields.
    private _dpPending = _unit getVariable ["ACME_DP_ClaimPending", []];
    if (_dpPending isEqualType [] && {count _dpPending >= 4}) then {
        _dpPending params ["_pendingPatient", "_pendingPart", "_pendingToken", "_pendingEpoch"];
        if (!isNull _pendingPatient && {_pendingPart != ""} && {_pendingToken != ""}) then {
            [_pendingPatient, "directPressureClaim", ["release", [_unit, _pendingPart, _pendingToken, _pendingEpoch]]] call ACME_fnc_ownerDispatch;
        };
    };
    _unit setVariable ["ACME_DP_ClaimPending", [], false];
    _unit setVariable ["ACME_DP_ClaimRequestedAt", -1, false];
    if (!_isLocal) then {
        // Handler IDs belong to the departing machine alone.
        private _dpPFH = _unit getVariable ["ACME_DP_PFH", -1];
        if (_dpPFH >= 0) then {[_dpPFH] call CBA_fnc_removePerFrameHandler;};
        _unit setVariable ["ACME_DP_PFH", -1, false];
        {[_x, "keydown"] call CBA_fnc_removeKeyHandler;} forEach (_unit getVariable ["ACME_DP_KeyIDs", []]);
        _unit setVariable ["ACME_DP_KeyIDs", [], false];
        private _dpDraw = _unit getVariable ["ACME_DP_Draw3D", -1];
        if (_dpDraw >= 0) then {removeMissionEventHandler ["Draw3D", _dpDraw];};
        _unit setVariable ["ACME_DP_Draw3D", -1, false];
        // These are local stance hints, never persistent clinical state.
        // The former owner no longer has a PFH to retire them on its next tick.
        _unit setVariable ["ACME_DP_InPose", false, false];
        _unit setVariable ["ACME_DP_TreatmentBusy", false, false];
        _unit setVariable ["ACME_DP_Paused", false, false];
        _unit setVariable ["ACME_DP_Mode", "", false];
    };
    // End B255 DP locality cleanup.
    // B258: machine-local CPR animation cleanup belongs to the native
    // circulation module; this event handler only requests that boundary.
    [_unit] call ACM_circulation_fnc_cprRetireAnimLocal;
    if (_isLocal) then {
        // B156 transferred fall cleanup: finite presentation jobs belong to the departed machine.
        // Retire their exact replicated ownership before registering replacement patient work.
        private _fallPoseLock = _unit getVariable ["ACME_patientAnimLock", []];
        private _providerOwnsPose = (count _fallPoseLock >= 5 && {(_fallPoseLock select 4) > serverTime}) || {[_unit] call ACME_fnc_providerStanceOwned};
        if !((_unit getVariable ["ACME_blast_stanceToken", []]) isEqualTo []) then {
            _unit setVariable ["ACME_blast_stanceToken", [], true];
            if (alive _unit && {!_providerOwnsPose} && {!([_unit] call ACME_fnc_animBlocked)}) then {_unit setUnitPos "AUTO";};
        };
        if !((_unit getVariable ["ACME_obtunded_sprintRagdollToken", []]) isEqualTo []) then {
            _unit setVariable ["ACME_obtunded_sprintRagdollToken", [], true];
            if (_unit getVariable ["ACME_obtunded_sprintRagdollActive", false]) then {
                _unit setVariable ["ACME_obtunded_sprintRagdollActive", false, true];
                if (alive _unit && {!(_unit getVariable ["ACE_isUnconscious", false])}) then {_unit setUnconscious false;};
            };
        };
        // End B156 transferred fall cleanup.
        // B156 transferred native treatment rate cleanup: the old owner's finite action has stopped.
        if ((_unit getVariable ["ACME_nativeTreatmentRate", []]) isNotEqualTo []) then {
            _unit setVariable ["ACME_nativeTreatmentRate", [], true];
            _unit setAnimSpeedCoef 1;
            ["ace_common_setAnimSpeedCoef", [_unit, 1]] call CBA_fnc_globalEvent;
        };
        // End B156 transferred native treatment rate cleanup.
        // The animation lease carries its speed across ownership changes. The old owner's expiry callback
        // cannot clean up here, so adopt only this exact live lease and schedule its bounded release.
        private _animLock = _unit getVariable ["ACME_patientAnimLock", []];
        private _speedToken = _unit getVariable ["ACME_patientAnimSpeedToken", ""];
        if (count _animLock >= 6 && {(_animLock select 5) > 1}) then {
            private _token = _animLock select 0;
            private _expires = _animLock select 4;
            _unit setVariable ["ACME_patientAnimSpeedToken", _token, true];
            if (_expires <= serverTime) then {
                [_unit, _token, false] call ACME_fnc_patientAnimRelease;
            } else {
                private _rate = _animLock select 5;
                _unit setAnimSpeedCoef _rate;
                ["ace_common_setAnimSpeedCoef", [_unit, _rate]] call CBA_fnc_globalEvent;
                [{
                    params ["_unit", "_token"];
                    if (isNull _unit || {!local _unit}) exitWith {};
                    private _lock = _unit getVariable ["ACME_patientAnimLock", []];
                    if ((_lock param [0, ""]) == _token && {(_lock param [4, -1]) <= serverTime}) then {
                        [_unit, _token, false] call ACME_fnc_patientAnimRelease;
                    };
                }, [_unit, _token], (_expires - serverTime) max 0.05] call CBA_fnc_waitAndExecute;
            };
        } else {
            if (_speedToken != "" && {_animLock isEqualTo []}) then {[_unit, _speedToken, false] call ACME_fnc_patientAnimRelease;};
        };
        [_unit] call ACME_fnc_ownerRegister;
        [{ _this call ACME_fnc_ownerRegister; }, [_unit]] call CBA_fnc_execNextFrame;
        [{ _this call ACME_fnc_ownerRegister; }, [_unit], 0.5] call CBA_fnc_waitAndExecute;
    };
}] call CBA_fnc_addClassEventHandler;
["CAManBase", "init", {
    [{ _this call ACME_fnc_ownerRegister; }, [_this select 0]] call CBA_fnc_execNextFrame;
}, true, [], true] call CBA_fnc_addClassEventHandler;
[{
    [] call ACME_fnc_aiProtectionTick;
    // Provider stale-state repair and registry pruning stay responsive at 1 Hz. Local/init events maintain the
    // owner registry directly. The 30 s world sweep is now only a missed-event audit: it calls ownerRegister solely
    // for units absent from the registry/owner generation, so hundreds of healthy AI never get rebuilt in one spike.
    private _nextRecovery = missionNamespace getVariable ["ACME_ownerRecoveryNextAt", -1];
    if (_nextRecovery < 0 || {CBA_missionTime >= _nextRecovery}) then {
        missionNamespace setVariable ["ACME_ownerRecoveryNextAt", CBA_missionTime + 30];
        private _actualOwned = allUnits select {local _x && {alive _x}};
        private _knownOwned = missionNamespace getVariable ["ACME_clinical_ownedUnits", []];
        private _missingOwned = _actualOwned select {
            !(_x in _knownOwned) || {(_x getVariable ["ACME_ownerRegisterSeen", -999]) != owner _x}
        };
        missionNamespace setVariable ["ACME_clinical_ownedUnits", _actualOwned];
        {[_x] call ACME_fnc_ownerRegister;} forEach _missingOwned;
    };
    if ((hasInterface && {!isNil "ACE_player"} && {!isNull ACE_player})
        || {!((missionNamespace getVariable ["ACM_core_ContinuousAction_Controller", []]) isEqualTo [])}) then {
        [] call ACME_fnc_providerStateReconcile;
    };
    {
        missionNamespace setVariable [_x, (missionNamespace getVariable [_x, []]) select {!isNull _x && {local _x} && {alive _x}}];
    } forEach ["ACME_nrb_activePatients", "ACME_hpmk_activePatients", "ACME_tbi_activePatients", "ACME_cs_activePatients", "ACME_autoBP_patients", "ACME_clinical_activePatients", "ACME_infusion_activePatients", "ACME_circ_activePatients", "ACME_coag_activePatients", "ACME_preox_activePatients", "ACME_aspiration_activePatients", "ACME_shock_activePatients", "ACME_rhythmThreshold_activePatients", "ACME_rhythm_activePatients"];
}, 1, []] call CBA_fnc_addPerFrameHandler;
if (isServer) then {
    ACME_nrb_soundRegistry = createHashMap;
    [{
        {
            private _entry = ACME_nrb_soundRegistry get _x;
            _entry params ["_patient", "_source", "_at"];
            if (isNull _patient || {!alive _patient} || {
                CBA_missionTime > _at + 2 && {
                    !(_patient getVariable ["ACME_nrb_on", false]) || {!(_patient getVariable ["ACME_nrb_hasO2", false])}
                }
            }) then {
                if (!isNull _source) then { deleteVehicle _source; };
                ACME_nrb_soundRegistry deleteAt _x;
            };
        } forEach (keys ACME_nrb_soundRegistry);
    }, 0.5, []] call CBA_fnc_addPerFrameHandler;
};
