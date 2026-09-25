// NA2 owner lifecycle. One shared recovery scan supplements event-driven registration.
if (missionNamespace getVariable ["ACME_NA2_ownerInstalled", false]) exitWith {};
ACME_NA2_ownerInstalled = true;
["ACME_ownerCommand", { isNil { _this call ACME_fnc_ownerDispatch; }; }] call CBA_fnc_addEventHandler;
["ACME_netNotice", { _this call ACME_fnc_netNotice; }] call CBA_fnc_addEventHandler;
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
    // IO syncope timers are machine-local. A departed owner's job must neither
    // resume after an away/back transfer nor strand the returning owner's token.
    _unit setVariable ["ACME_ioSyncopeToken", -1, false];
    // Also invalidates an old callback on an away-and-back locality change.
    _unit setVariable ["ACME_wakeRepairTicket", (_unit getVariable ["ACME_wakeRepairTicket", 0]) + 1, false];
    [_unit] call ACME_fnc_aajtDownedStop;
    private _headPFH = _unit getVariable ["ACME_headElev_pfh", -1];
    if (_headPFH >= 0) then {[_headPFH] call CBA_fnc_removePerFrameHandler;};
    _unit setVariable ["ACME_headElev_pfh", -1];
    private _headEH = _unit getVariable ["ACME_headElev_killEH", -1];
    if (_headEH >= 0) then {_unit removeEventHandler ["Killed", _headEH];};
    _unit setVariable ["ACME_headElev_killEH", -1];
    _unit setVariable ["ACME_net_scalarCache", createHashMap, false];
    _unit setVariable ["ACME_net_cacheOwner", [], false];
    _unit setVariable ["ACME_net_approxCache", createHashMap, false];
    _unit setVariable ["ACME_net_approxOwner", [], false];
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
    } forEach ["ACME_nrb_activePatients", "ACME_hpmk_activePatients", "ACME_tbi_activePatients", "ACME_cs_activePatients", "ACME_autoBP_patients", "ACME_clinical_activePatients", "ACME_infusion_activePatients", "ACME_circ_activePatients", "ACME_coag_activePatients"];
    private _drain = _unit getVariable ["ACME_thora_drainPFH", -1];
    if (_drain >= 0) then { [_drain] call CBA_fnc_removePerFrameHandler; };
    _unit setVariable ["ACME_thora_drainPFH", -1, false];
    _unit setVariable ["ACME_nrb_lastTickLocal", nil, false];
    _unit setVariable ["ACME_hpmk_lastTickLocal", nil, false];
    _unit setVariable ["ACME_nrb_lastDrawSend", -1, false];
    _unit setVariable ["ACME_nrb_sfxWanted", nil, false];
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
    ACME_clinical_ownedUnits = allUnits select {local _x && {alive _x}};
    {[_x] call ACME_fnc_ownerRegister;} forEach ACME_clinical_ownedUnits;
    if (hasInterface && {!isNil "ACE_player"} && {!isNull ACE_player}) then {
        [] call ACME_fnc_providerStateReconcile;
    };
    {
        missionNamespace setVariable [_x, (missionNamespace getVariable [_x, []]) select {!isNull _x && {local _x} && {alive _x}}];
    } forEach ["ACME_nrb_activePatients", "ACME_hpmk_activePatients", "ACME_tbi_activePatients", "ACME_cs_activePatients", "ACME_autoBP_patients", "ACME_clinical_activePatients", "ACME_infusion_activePatients", "ACME_circ_activePatients", "ACME_coag_activePatients"];
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
