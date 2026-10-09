// B229: native ground-inventory discovery; no custom carrier menu action.
// B218 server-only carrier capacity initialization; bounded for cross-client variable propagation.
if (isServer && {isNil "ACME_carrierInventoryCapacityEH"}) then {
    ACME_carrierInventoryCapacityEH = ["ACME_carrierInventoryCapacity", {
        params ["_patient", "_cargo"];
        [{
            params ["_p", "_c"];
            isNull _p || {isNull _c} || {
                ((_p getVariable ["ACME_carrierCargo", objNull]) isEqualTo _c)
                && {count (_p getVariable [_c getVariable ["ACME_carrierSavedVar", ""], []]) == 2}
            }
        }, ACME_fnc_carrierInventoryCapacity, _this, 2, {}] call CBA_fnc_waitUntilAndExecute;
    }] call CBA_fnc_addEventHandler;
};
// B258: a parked carrier is a separate simple object, not automatically
// deleted with its patient. Keep this on the engine's Deleted event, not the
// Killed event: unconscious/dead casualties must retain their gear until they
// are actually despawned. Each machine only cleans its locally known props.
if (isNil "ACME_manualPlateCarrierDeletedEH") then {
    ACME_manualPlateCarrierDeletedEH = ["CAManBase", "Deleted", {
        params ["_patient"];
        if (isNull _patient) exitWith {};
        {
            private _prop = _patient getVariable [_x, objNull];
            if (!isNull _prop) then {
                detach _prop;
                deleteVehicle _prop;
            };
        } forEach ["ACME_chestAccess_vestProp", "ACME_CS_vestProp", "ACME_carrierCargo"];
        ACME_manualPlateCarrierPatients = (missionNamespace getVariable ["ACME_manualPlateCarrierPatients", []]) - [_patient];
    }] call CBA_fnc_addClassEventHandler;
};

/* Stable B183: UI acknowledgement plus owner-local manual-carrier return watchdog. */
// Track only casualties with an active manual lease. State commits enroll synchronously; lifecycle events
// handle ownership/new units and a slow audit recovers missed/late replicated events.
if (isNil "ACME_manualPlateCarrierTrackEH") then {
    ACME_manualPlateCarrierPatients = [];
    ACME_manualPlateCarrierRecoveryAt = -1;
    ACME_manualPlateCarrierTrackEH = ["ACME_manualPlateCarrierTrack", {
        params ["_patient"];
        private _patients = missionNamespace getVariable ["ACME_manualPlateCarrierPatients", []];
        if (!isNull _patient && {local _patient} && {alive _patient}
            && {(_patient getVariable ["ACME_manualPlateCarrierState", ""]) != ""}) then {
            _patients pushBackUnique _patient;
        } else {
            _patients = _patients - [_patient];
        };
        missionNamespace setVariable ["ACME_manualPlateCarrierPatients", _patients];
    }] call CBA_fnc_addEventHandler;
    ["CAManBase", "Local", {
        params ["_patient"];
        ["ACME_manualPlateCarrierTrack", [_patient]] call CBA_fnc_localEvent;
        // State replication can arrive just after the ownership event. A departed owner cannot re-enroll here.
        [{["ACME_manualPlateCarrierTrack", _this] call CBA_fnc_localEvent;}, [_patient], 0.5] call CBA_fnc_waitAndExecute;
    }] call CBA_fnc_addClassEventHandler;
    ["CAManBase", "init", {
        [{["ACME_manualPlateCarrierTrack", _this] call CBA_fnc_localEvent;}, [_this select 0]] call CBA_fnc_execNextFrame;
    }, true, [], true] call CBA_fnc_addClassEventHandler;
    ["CAManBase", "Killed", {
        // Death neither restores nor deletes parked gear. Keep a currently
        // removing corpse tracked for owner-local completion/timeout; the
        // real Deleted event disposes of temporary objects.
        params ["_patient"];
        ["ACME_manualPlateCarrierTrack", [_patient]] call CBA_fnc_localEvent;
    }] call CBA_fnc_addClassEventHandler;
};
if (isNil "ACME_manualPlateCarrierWatchPFH") then {
    ACME_manualPlateCarrierWatchPFH = [{
        private _now = CBA_missionTime;
        if (_now >= (missionNamespace getVariable ["ACME_manualPlateCarrierRecoveryAt", -1])) then {
            ACME_manualPlateCarrierRecoveryAt = _now + 30;
            // Local/init/state events maintain enrollment. The audit only needs to recover
            // a missed active lease; do not dispatch a tracking event for every healthy AI.
            {
                ["ACME_manualPlateCarrierTrack", [_x]] call CBA_fnc_localEvent;
            } forEach (allUnits select {
                local _x && {alive _x} && {(_x getVariable ["ACME_manualPlateCarrierState", ""]) != ""}
            });
        };
        private _kept = [];
        {
            private _p = _x;
            if (isNull _p || {!local _p}) then {continue};

            private _state = _p getVariable ["ACME_manualPlateCarrierState", ""];
            if (_state == "") then {continue};

            private _awake = alive _p
                && {!(_p getVariable ["ACE_isUnconscious", false])}
                && {!(_p getVariable ["ace_medical_unconscious", false])};
            private _transported = !isNull objectParent _p
                || {!isNull attachedTo _p}
                || {_p call ace_common_fnc_isBeingDragged}
                || {_p call ace_common_fnc_isBeingCarried};

            private _origin = _p getVariable ["ACME_manualPlateCarrierOriginASL", []];
            private _moved = _origin isEqualType [] && {count _origin == 3}
                && {_p distance2D _origin > 0.35};

            private _externalVest = _state in ["off", "restoring"] && {(vest _p) != ""};

            if (_awake || {_transported} || {_moved} || {_externalVest}) then {
                private _reason = if (_awake) then {"awake"} else {
                    if (_transported) then {"transport"} else {
                        if (_externalVest) then {"external-restore"} else {"moved"}
                    }
                };
                [_p, _reason] call ACME_fnc_manualPlateCarrierAutoReturn;
            };
            if ((_p getVariable ["ACME_manualPlateCarrierState", ""]) != "") then {_kept pushBack _p;};
        } forEach (+(missionNamespace getVariable ["ACME_manualPlateCarrierPatients", []]));
        ACME_manualPlateCarrierPatients = _kept;
    }, 0.20, []] call CBA_fnc_addPerFrameHandler;
};

// Drag/carry setup gets an immediate return instead of waiting for the 0.20 s watchdog pass.
if (isNil "ACME_manualPlateCarrierTransportEH") then {
    ACME_manualPlateCarrierTransportEH = [];
    {
        private _eh = [_x, {
            params ["_unit", "_target"];
            if (!isNull _target && {(_target getVariable ["ACME_manualPlateCarrierState", ""]) != ""}) then {
                [_target, "transport"] call ACME_fnc_manualPlateCarrierAutoReturn;
            };
        }] call CBA_fnc_addEventHandler;
        ACME_manualPlateCarrierTransportEH pushBack _eh;
    } forEach ["ace_dragging_setupDrag", "ace_dragging_setupCarry"];
};

if (hasInterface && {isNil "ACME_manualPlateCarrierAckEH"}) then {
    ACME_manualPlateCarrierAckEH = ["ACME_manualPlateCarrierAck", {
        params [
            ["_patient", objNull, [objNull]],
            ["_restore", false, [false]],
            ["_success", false, [false]]
        ];

        if (!_success) exitWith {
            if (!isNull ACE_player) then {
                ["Plate carrier action could not be completed.", 1.8, ACE_player, 13]
                    call ace_common_fnc_displayTextStructured;
            };
        };

        if (!isNull ACE_player) then {
            [
                ["Plate carrier removed and parked above the casualty.",
                 "Plate carrier returned to the casualty."] select _restore,
                1.8,
                ACE_player,
                13
            ] call ace_common_fnc_displayTextStructured;
        };

        [{
            params ["_patient"];
            private _display = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
            if (!isNull _display
                && {(missionNamespace getVariable ["ace_medical_gui_target", objNull]) isEqualTo _patient}
                && {!isNil "ace_medical_gui_fnc_updateActions"}) then {
                [_display] call ace_medical_gui_fnc_updateActions;
            };
        }, [_patient]] call CBA_fnc_execNextFrame;
    }] call CBA_fnc_addEventHandler;
};
