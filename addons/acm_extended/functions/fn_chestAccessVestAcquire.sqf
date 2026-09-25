// Prepare a casualty for unobstructed chest access.
//
// Visible choreography when a worn carrier must come off:
//   provider fully holsters > medic4 body-handling theatre
//   patient Grab/Hold > carrier removed and parked once beyond head > patient Release to supine
//
// ACME_chestAccess_readyServer acknowledges casualty-side gear/body work. Check Breathing separately requires
// its provider's frozen frame and acknowledges removal before lowering; other actions retain the final lower
// boundary. A failed provider presentation does not prevent the patient/gear transaction from completing.
params [
    ["_patient", objNull, [objNull]],
    ["_medic", objNull, [objNull]],
    ["_context", "access", [""]],
    ["_frontNormalized", false, [false]],
    ["_treatmentClass", "", [""]],
    ["_preparationToken", "", [""]]
];
if (isNull _patient || {!local _patient}) exitWith {false};
_context = toLowerANSI _context;
if !(_context in ["access","chestseal"]) then {_context = "access";};
_treatmentClass = toLowerANSI _treatmentClass;
private _preserveHeadElevation = _treatmentClass in ["usebvm","usebvm_oxygen","usebvm_vehicleoxygen","usebvm_portableoxygen"];

private _savedVar = ["ACME_chestAccess_vestLoadout","ACME_CS_vestLoadout"] select (_context == "chestseal");
private _propVar = ["ACME_chestAccess_vestProp","ACME_CS_vestProp"] select (_context == "chestseal");
private _readyVar = ["ACME_chestAccess_readyServer","ACME_CS_vestReadyServer"] select (_context == "chestseal");
private _busyVar = ["ACME_chestAccess_vestBusy","ACME_CS_vestBusy"] select (_context == "chestseal");
private _pfhVar = ["ACME_chestAccess_vestPFH","ACME_CS_vestPFH"] select (_context == "chestseal");
private _frontBusyVar = ["ACME_chestAccess_frontBusy","ACME_CS_frontBusy"] select (_context == "chestseal");
private _workspaceToken = if (_context == "chestseal") then {_patient getVariable ["ACME_CS_PreparationToken", ""]} else {_preparationToken};
if (_context == "chestseal" && {
    _workspaceToken == "" || {(_patient getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}
}) exitWith {false};

// Every chest procedure starts anterior-up. If the casualty is legitimately rollable and actually posterior-up,
// perform the authored front/supine roll BEFORE any carrier-removal or auscultation/chest-seal start animation.
// Do not use a nested exitWith here: nested SQF scopes would continue the outer function and start carrier theatre
// on the same frame as the roll.
private _frontRollPending = false;
if (!_frontNormalized) then {
    private _actualBefore = [_patient, _patient getVariable ["ACME_CS_facing","front"]] call ACME_fnc_chestSealActualSide;
    private _canFrontRoll = alive _patient
        && {isNull objectParent _patient}
        && {[_patient] call ACME_fnc_chestSealCanPhysicalRoll}
        && {_actualBefore == "back"
            || {_context == "chestseal" && {(_patient getVariable ["ACME_CS_rollToken", ""]) != ""}}};

    if (_canFrontRoll) then {
        _frontRollPending = true;

        if ((_patient getVariable [_frontBusyVar,""]) == "") then {
            private _frontToken = format ["front:%1:%2:%3:%4",_context,netId _patient,round(serverTime * 1000),_workspaceToken];
            _patient setVariable [_frontBusyVar,_frontToken,false];
            _patient setVariable [_readyVar,-1,true];

            // Provider uses the same literal medic4 roll theatre, but this episode completes fully back to crouch
            // before carrier access begins.
            if (!isNull _medic && {!(_medic isEqualTo _patient)} && {alive _medic}) then {
                [_medic,"chestAccessFrontRoll",[_medic,_patient]] call ACME_fnc_ownerDispatch;
            };

            private _preserveHead = (_patient getVariable ["ACME_headElevated",false])
                || {_patient getVariable ["ACME_headElev_Suspended",false]}
                || {_context == "chestseal"};
            if (_context != "chestseal" || {(_patient getVariable ["ACME_CS_rollToken", ""]) == ""}) then {
                [_patient,"front",false,_medic,_preserveHead] call ACME_fnc_chestSealRoll;
            };

            private _patientRoll = missionNamespace getVariable ["ACME_CS_rollTime", 1.85 / (call ACME_fnc_choreographyRate)];
            if !(_patientRoll isEqualType 0 && {finite _patientRoll}) then {_patientRoll = 1.85;};
            private _providerRoll = missionNamespace getVariable ["ACME_rollProviderDuration",2.2];
            if !(_providerRoll isEqualType 0 && {finite _providerRoll}) then {_providerRoll = 2.2;};
            private _wait = (_patientRoll + 0.15) max (_providerRoll + 0.40);

            private _afterFrontRoll = {
                params ["_p","_m","_ctx","_busyVar","_token","_treatmentClass","_preparationToken"];
                if (isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}) exitWith {};
                _p setVariable [_busyVar,"",false];
                if (_ctx != "chestseal") then {_p setVariable ["ACME_CS_facing","front",true];};
                // A denied roll leaves the body posterior-up. Recheck physical
                // eligibility/side instead of treating the nominal delay as a roll.
                [_p,_m,_ctx,_ctx != "chestseal",_treatmentClass,_preparationToken] call ACME_fnc_chestAccessVestAcquire;
            };
            private _frontArgs = [_patient,_medic,_context,_frontBusyVar,_frontToken,_treatmentClass,_preparationToken];
            if (_context == "chestseal") then {
                [{
                    params ["_args","","_earliest"];
                    _args params ["_p","","","_busyVar","_token"];
                    isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}
                        || {CBA_missionTime >= _earliest && {(_p getVariable ["ACME_CS_rollToken", ""]) == ""}}
                }, {
                    params ["_args","_after"];
                    _args call _after;
                }, [_frontArgs,_afterFrontRoll,CBA_missionTime + _wait]] call CBA_fnc_waitUntilAndExecute;
            } else {
                [_afterFrontRoll, _frontArgs, _wait] call CBA_fnc_waitAndExecute;
            };
        };
    };
};
if (_frontRollPending) exitWith {true};

// Removed gear alone is not completion: a delayed lowering/restoration callback
// may still own the body. Wait for that exact transaction before reusing custody.
if ((_patient getVariable [_busyVar, ""]) != "") exitWith {true};

// Existing custody belongs to an already-open chest episode. Never replay the lift or move the parked carrier.
private _saved = +(_patient getVariable [_savedVar, []]);
if ((count _saved) == 2) exitWith {
    if (_context == "chestseal") then {[_patient] call ACME_fnc_chestSealParkCarrier}
    else {[_patient] call ACME_fnc_chestAccessVestPark};
    _patient setVariable [_readyVar, serverTime, true];
    true
};

// Semi-Fowler is lowered before any separate worn carrier is lifted off.
// Start a fresh fixed park episode for the Semi-Fowler support prop.
private _preDelay = 0;
// BVM is compatible with a supported Semi-Fowler posture. If BVM still needs the worn carrier moved, remove/park
// the carrier without first laying the casualty flat. CPR and other flat-required work retain the normal suspension.
if ((_patient getVariable ["ACME_headElevated", false]) && {!_preserveHeadElevation}) then {
    private _headProp = _patient getVariable ["ACME_headElev_propObj", objNull];
    if (!isNull _headProp) then {_headProp setVariable ["ACME_chestFixedPark", nil, false];};

    if !(_patient getVariable ["ACME_headElev_Suspended", false]) then {
        _patient setVariable ["ACME_headElev_ResumePending", false, true];
        [_patient, true] call ACME_fnc_headElevSuspend;
    };

    private _suspendReady = _patient getVariable ["ACME_headElev_suspendReadyAt", -1];
    if (_suspendReady > CBA_missionTime) then {
        _preDelay = (_suspendReady - CBA_missionTime) + 0.05;
    };
};

// No worn carrier: the only preparation may be the Semi-Fowler lay-flat operation above.
// A timestamp is not enough here. The Release callback can still be handing into ACM_LyingState on the frame the
// nominal timer expires, which previously made auscultation classify the still-tilted body as posterior and enter
// a second roll path. Publish readiness only after the actual body is face-up, with a bounded fail-open.
private _vestClass = vest _patient;
private _vestEntry = (getUnitLoadout _patient) param [4, [], [[]]];
private _suspendPending = _context == "chestseal"
    && {_patient getVariable ["ACME_headElevated", false]}
    && {_patient getVariable ["ACME_headElev_Suspended", false]}
    && {(_patient getVariable ["ACME_headElev_suspendPending", ""]) != ""};
if (_vestClass == "" || {(count _vestEntry) != 2}) exitWith {
    if ((_preDelay max 0) <= 0 && {!_suspendPending}) then {
        if (_context != "chestseal") then {_patient setVariable ["ACME_CS_facing", "front", true];};
        _patient setVariable [_readyVar, serverTime, true];
    } else {
        _patient setVariable [_readyVar, -1, true];
        [{
            params ["_p","_readyVar","_ctx","_prep"];
            if (isNull _p || {!local _p}) exitWith {true};
            if (_ctx == "chestseal" && {
                (_p getVariable ["ACME_CS_PreparationToken", ""]) != _prep
                || {(_p getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}
            }) exitWith {true};
            private _readyAt = _p getVariable ["ACME_headElev_suspendReadyAt", -1];
            private _actual = [_p, _p getVariable ["ACME_CS_facing","front"]] call ACME_fnc_chestSealActualSide;
            (_readyAt <= CBA_missionTime) && {_ctx == "chestseal" || {_actual == "front"}}
                && {_ctx != "chestseal" || {(_p getVariable ["ACME_headElev_suspendPending", ""]) == ""}
                    || {!(_p getVariable ["ACME_headElevated", false])}
                    || {!(_p getVariable ["ACME_headElev_Suspended", false])}}
        }, {
            params ["_p","_readyVar","_ctx","_prep"];
            if (isNull _p || {!local _p}) exitWith {};
            if (_ctx == "chestseal" && {
                (_p getVariable ["ACME_CS_PreparationToken", ""]) != _prep
                || {(_p getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}
            }) exitWith {};
            if (_ctx != "chestseal") then {_p setVariable ["ACME_CS_facing", "front", true];};
            _p setVariable [_readyVar, serverTime, true];
        }, [_patient,_readyVar,_context,_workspaceToken], if (_context == "chestseal") then {-1} else {(_preDelay max 0) + 1.5}, {
            params ["_p","_readyVar","_ctx"];
            if (_ctx == "chestseal") exitWith {};
            if (isNull _p || {!local _p}) exitWith {};
            // Clinical reliability wins if a third-party animation masks the final classification.
            _p setVariable ["ACME_CS_facing", "front", true];
            _p setVariable [_readyVar, serverTime, true];
        }] call CBA_fnc_waitUntilAndExecute;
    };
    true
};

private _commitRemoval = {
    params ["_p","_ctx","_savedVar","_propVar","_pfhVar"];
    if (isNull _p || {!local _p}) exitWith {false};
    if ((count (_p getVariable [_savedVar, []])) == 2) exitWith {true};

    private _class = vest _p;
    private _entry = (getUnitLoadout _p) param [4, [], [[]]];
    if (_class == "" || {(count _entry) != 2}) exitWith {false};

    removeVest _p;
    if ((vest _p) != "") exitWith {false};

    private _model = getText (configFile >> "CfgWeapons" >> _class >> "model");
    private _prop = objNull;
    if (_model != "") then {
        _prop = createSimpleObject [_model, getPosATL _p, false];
    };
    if (isNull _prop) then {
        _prop = createVehicle ["GroundWeaponHolder", getPosATL _p, [], 0, "CAN_COLLIDE"];
        _prop addItemCargoGlobal [_class, 1];
    };

    _p setVariable [_savedVar, +_entry, true];
    _p setVariable [_propVar, _prop, true];
    _prop setVariable ["ACME_chestFixedPark", nil, false];

    if (_ctx == "chestseal") then {[_p] call ACME_fnc_chestSealParkCarrier}
    else {[_p] call ACME_fnc_chestAccessVestPark};

    // Custody watchdog. Parking is fixed-world, so repeated calls only repair external prop drift.
    private _oldPFH = _p getVariable [_pfhVar, -1];
    if (_oldPFH isEqualType 0 && {_oldPFH >= 0}) then {[_oldPFH] call CBA_fnc_removePerFrameHandler;};

    private _pfh = [{
        params ["_args","_handle"];
        _args params ["_patient","_ctx","_savedVar","_pfhVar"];
        if (isNull _patient || {!local _patient}
            || {(count (_patient getVariable [_savedVar, []])) != 2}) exitWith {
            [_handle] call CBA_fnc_removePerFrameHandler;
            if (!isNull _patient) then {_patient setVariable [_pfhVar, -1, false];};
        };

        if (_ctx == "chestseal") then {
            [_patient] call ACME_fnc_chestSealParkCarrier;
        } else {
            private _leases = _patient getVariable ["ACME_chestAccess_leases", createHashMap];
            private _dirty = false;
            {
                private _row = _leases get _x;
                private _provider = _row param [0,objNull,[objNull]];
                private _at = _row param [1,CBA_missionTime,[0]];
                if (isNull _provider || {!alive _provider} || {CBA_missionTime - _at > 900}) then {
                    _leases deleteAt _x;
                    _dirty = true;
                };
            } forEach +(keys _leases);

            if (_dirty) then {
                _patient setVariable ["ACME_chestAccess_leases", _leases, true];
                private _thora = false;
                {if (((_leases get _x) param [2,"",[""]]) == "thoracostomy") exitWith {_thora = true;};} forEach keys _leases;
                _patient setVariable ["ACME_Thora_ChestAccessActive", _thora, true];
            };

            [_patient] call ACME_fnc_chestAccessVestPark;

            if ((count _leases) == 0
                && {(_patient getVariable ["ACME_chestAccess_vestBusy", ""]) == ""}) then {
                [_patient, false, objNull, "access"] call ACME_fnc_chestAccessVestRestore;
            };
        };
    }, 0.20, [_p,_ctx,_savedVar,_pfhVar]] call CBA_fnc_addPerFrameHandler;
    _p setVariable [_pfhVar, _pfh, false];
    true
};

// Animation is allowed only for casualties whose body ACME may legitimately control.
// Otherwise gear correctness wins and the action proceeds after the Semi-Fowler lowering delay, if any.
private _canAnimate = !_preserveHeadElevation
    && {alive _patient}
    && {isNull objectParent _patient}
    && {!([_patient] call ACME_fnc_animBlocked)}
    && {[_patient] call ACME_fnc_chestSealCanPhysicalRoll
        || {_patient getVariable ["ACME_headElevated", false]}
        || {_patient getVariable ["ACME_headElev_Suspended", false]}};

if (!_canAnimate) exitWith {
    private _delay = _preDelay max 0;
    if (_delay <= 0 && {!_suspendPending}) then {
        [_patient,_context,_savedVar,_propVar,_pfhVar] call _commitRemoval;
        _patient setVariable [_readyVar, serverTime, true];
    } else {
        _patient setVariable [_readyVar, -1, true];
        private _removeWithoutAnimation = {
            params ["_p","_ctx","_saved","_prop","_pfhVar","_commit","_readyVar","_prep"];
            if (isNull _p || {!local _p}) exitWith {};
            if (_ctx == "chestseal" && {
                (_p getVariable ["ACME_CS_PreparationToken", ""]) != _prep
                || {(_p getVariable ["ACME_CS_ProcedureTokens", []]) isEqualTo []}
            }) exitWith {};
            [_p,_ctx,_saved,_prop,_pfhVar] call _commit;
            _p setVariable [_readyVar, serverTime, true];
        };
        private _args = [_patient,_context,_savedVar,_propVar,_pfhVar,_commitRemoval,_readyVar,_workspaceToken];
        if (_context == "chestseal") then {
            [{
                params ["_args","","_earliest"];
                private _p = _args select 0;
                isNull _p || {!local _p}
                    || {(_p getVariable ["ACME_CS_PreparationToken", ""]) != (_args select 7)}
                    || {CBA_missionTime >= _earliest && {
                        (_p getVariable ["ACME_headElev_suspendPending", ""]) == ""
                        || {!(_p getVariable ["ACME_headElevated", false])}
                        || {!(_p getVariable ["ACME_headElev_Suspended", false])}}}
            }, {
                params ["_args","_remove"];
                _args call _remove;
            }, [_args,_removeWithoutAnimation,CBA_missionTime + _delay]] call CBA_fnc_waitUntilAndExecute;
        } else {
            [_removeWithoutAnimation, _args, _delay] call CBA_fnc_waitAndExecute;
        };
    };
    true
};

private _liftTime = missionNamespace getVariable ["ACME_chestAccess_vestLiftTime", 1.2 / (call ACME_fnc_choreographyRate)];
if (!(_liftTime isEqualType 0) || {_liftTime <= 0}) then {_liftTime = 1.2 / (call ACME_fnc_choreographyRate);};
private _lowerTime = missionNamespace getVariable ["ACME_chestAccess_vestLowerTime", 1.4 / (call ACME_fnc_choreographyRate)];
if (!(_lowerTime isEqualType 0) || {_lowerTime <= 0}) then {_lowerTime = 1.4 / (call ACME_fnc_choreographyRate);};
private _holdTime = missionNamespace getVariable ["ACME_chestAccess_vestLiftHold", 0.04];
if (!(_holdTime isEqualType 0) || {_holdTime < 0}) then {_holdTime = 0.04;};
private _removeAnimSpeed = call ACME_fnc_choreographyRate;

// No synthetic settle gap after the casualty is back down. The queued intervention may launch on the first
// readiness frame instead of waiting while the provider is frozen with hands on the chest.
private _sequenceTime = _liftTime + _holdTime + _lowerTime;

private _serial = (_patient getVariable ["ACME_chestAccess_vestSerial", 0]) + 1;
_patient setVariable ["ACME_chestAccess_vestSerial", _serial, false];
private _token = format ["vest:%1:%2:%3:%4", _context, netId _patient, _serial, round (serverTime * 1000)];
_patient setVariable [_busyVar, _token, false];
_patient setVariable [_readyVar, -1, true];

private _beginPatient = {
    params [
        "_p","_medic","_ctx","_savedVar","_propVar","_pfhVar","_busyVar","_readyVar","_token",
        "_commit","_liftTime","_holdTime","_lowerTime","_removeAnimSpeed","_sequenceTime","_begin","_readyOnRemoval"
    ];
    if (isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}) exitWith {};

    // A future clock estimate is not completion: a loaded owner may deliver the
    // removal/lowering callbacks several frames after their nominal deadlines.
    _p setVariable [_readyVar, -1, true];

    if (_ctx == "chestseal" && {(!alive _p) || {!isNull objectParent _p}}) exitWith {
        [_p,_ctx,_savedVar,_propVar,_pfhVar] call _commit;
        _p setVariable [_busyVar, "", false];
        _p setVariable [_readyVar, serverTime, true];
    };

    private _claim = [_p, "ACME_HeadElevPatientGrab", 2, "chest-access-vest", _medic, _sequenceTime + 0.5, 4, _token]
        call ACME_fnc_patientAnimRequest;
    if (_claim == "") exitWith {
        // Retain a valid competing lease. Resume this exact preparation only
        // once it releases; cancellation clears the busy token and retires us.
        [{
            params ["_args"];
            _args params ["_p","","","","","","_busyVar","","_token"];
            if (isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}) exitWith {true};
            private _lock = _p getVariable ["ACME_patientAnimLock", []];
            (count _lock) < 5 || {(_lock param [4,-1]) <= serverTime}
        }, {
            params ["_args","_begin"];
            _args call _begin;
        }, [+_this,_begin]] call CBA_fnc_waitUntilAndExecute;
    };

    // Actual casualty RTM acceleration for carrier removal. The token prevents an old episode from resetting
    // a replacement patient's speed.
    _p setVariable ["ACME_chestAccess_removeSpeedToken", _token, false];
    ["ace_common_setAnimSpeedCoef", [_p, _removeAnimSpeed]] call CBA_fnc_globalEvent;

    [_p, false] call ACME_fnc_headElevCollision;
    [_p, _liftTime + _holdTime + 0.25] call ACME_fnc_headElevPinPose;

    // Patient-side completion is authoritative. The provider is handed off only after the casualty is back down.
    private _finish = {
        params ["_p","_medic","_ctx","_busyVar","_readyVar","_token","_finish"];
        if (isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}) exitWith {};

        private _lock = _p getVariable ["ACME_patientAnimLock", []];
        if (_ctx == "chestseal" && {(count _lock) >= 5}
            && {(_lock param [0,""]) != _token} && {(_lock param [4,-1]) > serverTime}) exitWith {
            [{
                params ["_args"];
                _args params ["_p","","","_busyVar","","_token"];
                if (isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}) exitWith {true};
                private _lock = _p getVariable ["ACME_patientAnimLock", []];
                (count _lock) < 5 || {(_lock param [0,""]) == _token} || {(_lock param [4,-1]) <= serverTime}
            }, {
                params ["_args","_finish"];
                _args call _finish;
            }, [+_this,_finish]] call CBA_fnc_waitUntilAndExecute;
        };

        [_p, true] call ACME_fnc_headElevCollision;
        if ((_lock param [0,""]) == _token && {(_lock param [1,""]) == "chest-access-vest"}) then {
            _p setVariable ["ACME_patientAnimLock", [], true];
        };

        if ((_lock param [0, ""]) in ["", _token]
            && {alive _p} && {isNull objectParent _p} && {[_p] call ACME_fnc_chestSealCanPhysicalRoll}) then {
            private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp", "ACM_LyingState"];
            if ((toLowerANSI animationState _p) != (toLowerANSI _faceUp)) then {
                ["ace_common_switchMove", [_p, _faceUp]] call CBA_fnc_globalEvent;
            };
            _p setVariable ["ACME_CS_facing", "front", true];
        };

        if ((_p getVariable ["ACME_chestAccess_removeSpeedToken",""]) == _token) then {
            _p setVariable ["ACME_chestAccess_removeSpeedToken", "", false];
            [_p, _token] call ACME_fnc_patientAnimRelease;
        };

        _p setVariable [_busyVar, "", false];
        _p setVariable [_readyVar, serverTime, true];

        // Do NOT remotely stop the provider pose from the casualty owner here. On dedicated servers the ready
        // timestamp can reach the medic before this separate owner-dispatch packet, allowing CPR/BVM to start and
        // then be overwritten by the late chestAccess pose-stop. The provider client now retires this exact pose
        // synchronously in fnc_treatment immediately before launching the queued intervention.
        // Chest Seal continues to own its separate chestseal context/hand-off path.
    };

    // Start the lower interval from the callback that actually removes the
    // carrier. A late lift callback must not share a frame with its completion.
    [{
        params ["_p","_medic","_ctx","_savedVar","_propVar","_pfhVar","_busyVar","_readyVar","_token","_commit","_lowerTime","_finish","_readyOnRemoval"];
        if (isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}) exitWith {};

        private _removed = [_p,_ctx,_savedVar,_propVar,_pfhVar] call _commit;
        // Check Breathing retains the provider's frozen hold and starts its native timer at real carrier removal.
        // Other chest actions keep their existing readiness-after-lowering boundary.
        if (_readyOnRemoval && {_removed}) then {_p setVariable [_readyVar, serverTime, true];};

        if (alive _p && {isNull objectParent _p}) then {
            private _releaseClaim = [_p, "ACME_HeadElevPatientRelease", 2, "chest-access-vest", _medic, _lowerTime + 0.4, 4, _token]
                call ACME_fnc_patientAnimRequest;
            if (_releaseClaim != "") then {
                [_p, _lowerTime + 0.2] call ACME_fnc_headElevPinPose;
            };
        };
        if (_ctx == "chestseal" || {_readyOnRemoval}) then {
            [_finish, [_p,_medic,_ctx,_busyVar,_readyVar,_token,_finish], _lowerTime] call CBA_fnc_waitAndExecute;
        };
    }, [_p,_medic,_ctx,_savedVar,_propVar,_pfhVar,_busyVar,_readyVar,_token,_commit,_lowerTime,_finish,_readyOnRemoval],
       _liftTime + _holdTime] call CBA_fnc_waitAndExecute;

    // Existing non-modal access transactions retain their established timing.
    if (_ctx != "chestseal" && {!_readyOnRemoval}) then {
        [_finish, [_p,_medic,_ctx,_busyVar,_readyVar,_token,_finish], _sequenceTime] call CBA_fnc_waitAndExecute;

        [{
        params ["_p","_tok"];
        if (isNull _p || {!local _p}) exitWith {};
        if ((_p getVariable ["ACME_chestAccess_removeSpeedToken",""]) == _tok) then {
            _p setVariable ["ACME_chestAccess_removeSpeedToken", "", false];
            [_p, _tok] call ACME_fnc_patientAnimRelease;
        };
        }, [_p,_token], _sequenceTime + 0.25] call CBA_fnc_waitAndExecute;
    };
};

// After any Semi-Fowler lay-flat finishes, let the provider fully holster/crouch and reach literal medic4.
// The patient lift starts only from that exact work state. A bounded timeout preserves clinical reliability.
private _startProvider = {
    params [
        "_p","_medic","_ctx","_savedVar","_propVar","_pfhVar","_busyVar","_readyVar","_token",
        "_commit","_liftTime","_holdTime","_lowerTime","_removeAnimSpeed","_sequenceTime","_beginPatient","_preparationToken","_readyOnRemoval"
    ];
    if (isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}) exitWith {};

    private _args = [
        _p,_medic,_ctx,_savedVar,_propVar,_pfhVar,_busyVar,_readyVar,_token,
        _commit,_liftTime,_holdTime,_lowerTime,_removeAnimSpeed,_sequenceTime,_beginPatient,_readyOnRemoval
    ];

    if (isNull _medic || {_medic isEqualTo _p} || {!alive _medic}) exitWith {
        _args call _beginPatient;
    };

    [_medic, "chestAccessVestProvider", [_medic, _p, "start", false, _token, _preparationToken]] call ACME_fnc_ownerDispatch;

    [{
        // _this is [_args,_beginPatient], not [_medic,_token].
        params ["_callArgs","_begin"];
        private _m = _callArgs param [1,objNull,[objNull]];
        private _token = _callArgs param [8,"",[""]];
        if (isNull _m || {!alive _m}) exitWith {true};
        private _ready = _m getVariable ["ACME_chestAccessProviderReady", []];
        (_ready param [0,""]) == _token && {(_ready param [1,-1]) != -1}
    }, {
        params ["_args","_begin"];
        _args call _begin;
    }, [_args,_beginPatient], 4.75, {
        params ["_args","_begin"];
        // Presentation failed to report ready. Continue the patient transaction rather than losing the clinical click.
        _args call _begin;
    }] call CBA_fnc_waitUntilAndExecute;
};
private _providerArgs = [
    _patient,_medic,_context,_savedVar,_propVar,_pfhVar,_busyVar,_readyVar,_token,
    _commitRemoval,_liftTime,_holdTime,_lowerTime,_removeAnimSpeed,_sequenceTime,_beginPatient,_workspaceToken,_treatmentClass == "checkbreathing"
];
if (_context == "chestseal") then {
    [{
        params ["_args","","_earliest"];
        _args params ["_p","","","","","","_busyVar","","_token"];
        isNull _p || {!local _p} || {(_p getVariable [_busyVar,""]) != _token}
            || {CBA_missionTime >= _earliest && {
                (_p getVariable ["ACME_headElev_suspendPending", ""]) == ""
                || {!(_p getVariable ["ACME_headElevated", false])}
                || {!(_p getVariable ["ACME_headElev_Suspended", false])}}}
    }, {
        params ["_args","_start"];
        _args call _start;
    }, [_providerArgs,_startProvider,CBA_missionTime + (_preDelay max 0)]] call CBA_fnc_waitUntilAndExecute;
} else {
    [_startProvider, _providerArgs, _preDelay max 0] call CBA_fnc_waitAndExecute;
};

true
