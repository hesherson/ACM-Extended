// A targeted request lets a medic refresh premixed infusion state even when another client or the server owns
// the patient. The receiver writes only while the patient is local. The regular PFH catches an ownership change.
["ACME_syncPremixedBagsLocal", {
    params [["_patient", objNull, [objNull]]];
    if (!isNull _patient && {local _patient}) then {[_patient] call ACME_fnc_syncPremixedBags;};
}] call CBA_fnc_addEventHandler;

// Any ACE interaction menu replaces pulse palpation as the active interaction surface. Retire the pulse layer
// immediately so it can never remain underlaid behind another action/menu.
["ace_interactMenuOpened", {
    if (uiNamespace getVariable ["ACME_PulseCheckActive", false]) then {
        uiNamespace setVariable ["ACME_PulseCheckCancel", true];
        "ACM_FeelPulse" cutText ["","PLAIN",0,false];
    };
}] call CBA_fnc_addEventHandler;

// the medical menu opened.
["ace_medicalMenuOpened", {
    params ["_medic", "_target", "_display"];

    // B169 renderer ownership: do not rely on ACE's single global menuPFH lifetime. The stock onLoad/onUnload pair
    // is final in this runtime and rapid medical-menu replacement can let an older display's unload retire the PFH
    // which a newer display is using. That leaves a visible menu with stale/unbound action rows until some unrelated
    // control forces updateActions. Own one independent renderer driver per concrete display generation instead.
    if (!isNull _display && {hasInterface} && {!isNil "ACE_player"} && {_medic isEqualTo ACE_player}) then {
        private _rendererEpoch = (uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", 0]) + 1;
        uiNamespace setVariable ["ACME_medicalMenuRendererEpoch", _rendererEpoch];
        _display setVariable ["ACME_medicalMenuRendererEpoch", _rendererEpoch];

        private _oldRenderer = uiNamespace getVariable ["ACME_medicalMenuRendererPFH", -1];
        if (_oldRenderer isEqualType 0 && {_oldRenderer >= 0}) then {
            [_oldRenderer] call CBA_fnc_removePerFrameHandler;
        };

        // Bind action rows immediately. The persistent PFH below then keeps the complete ACE menu lifecycle current.
        if (!isNil "ace_medical_gui_fnc_updateActions") then {
            [_display] call ace_medical_gui_fnc_updateActions;
        };

        private _rendererPFH = [{
            params ["_args", "_idPFH"];
            _args params ["_display", "_epoch"];

            private _currentDisplay = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
            private _currentEpoch = uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", -1];
            if (isNull _display || {_display isNotEqualTo _currentDisplay} || {_epoch != _currentEpoch}) exitWith {
                [_idPFH] call CBA_fnc_removePerFrameHandler;
                if ((uiNamespace getVariable ["ACME_medicalMenuRendererPFH", -1]) == _idPFH) then {
                    uiNamespace setVariable ["ACME_medicalMenuRendererPFH", -1];
                };
            };

            if (!isNil "ace_medical_gui_fnc_menuPFH") then {
                call ace_medical_gui_fnc_menuPFH;
            } else {
                if (!isNil "ace_medical_gui_fnc_updateActions") then {
                    [_display] call ace_medical_gui_fnc_updateActions;
                };
            };
        }, 0, [_display, _rendererEpoch]] call CBA_fnc_addPerFrameHandler;

        _display setVariable ["ACME_medicalMenuRendererPFH", _rendererPFH];
        uiNamespace setVariable ["ACME_medicalMenuRendererPFH", _rendererPFH];

        // Once ACE's onLoad has finished, retire its unqualified global renderer PFH. From this point forward only
        // the display-generation driver above paints the menu, so a late stock onUnload can clear menuPFH without
        // affecting the live renderer.
        [{
            params ["_display", "_epoch", "_rendererPFH"];
            if (isNull _display
                || {_epoch != (uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", -1])}
                || {_rendererPFH != (uiNamespace getVariable ["ACME_medicalMenuRendererPFH", -1])}) exitWith {};

            private _acePFH = missionNamespace getVariable ["ace_medical_gui_menuPFH", -1];
            if (_acePFH isEqualType 0 && {_acePFH >= 0} && {_acePFH != _rendererPFH}) then {
                [_acePFH] call CBA_fnc_removePerFrameHandler;
            };
            missionNamespace setVariable ["ace_medical_gui_menuPFH", -1];

            if (call ACME_fnc_debugEnabled) then {
                diag_log format ["[ACME MENU RENDERER] owner epoch=%1 renderer=%2 retiredACE=%3 target=%4",
                    _epoch, _rendererPFH, _acePFH,
                    if (isNull (missionNamespace getVariable ["ace_medical_gui_target", objNull])) then {"null"} else {
                        netId (missionNamespace getVariable ["ace_medical_gui_target", objNull])
                    }];
            };
        }, [_display, _rendererEpoch, _rendererPFH]] call CBA_fnc_execNextFrame;

        _display displayAddEventHandler ["Unload", {
            params ["_display"];
            private _epoch = _display getVariable ["ACME_medicalMenuRendererEpoch", -1];
            if (_epoch != (uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", -2])) exitWith {};
            private _pfh = _display getVariable ["ACME_medicalMenuRendererPFH", -1];
            if (_pfh isEqualType 0 && {_pfh >= 0}
                && {_pfh == (uiNamespace getVariable ["ACME_medicalMenuRendererPFH", -1])}) then {
                [_pfh] call CBA_fnc_removePerFrameHandler;
                uiNamespace setVariable ["ACME_medicalMenuRendererPFH", -1];
            };
        }];
    };

    private _cancelledHandsOn = false;
    if (!isNull _medic && {local _medic} && {hasInterface} && {!isNil "ACE_player"} && {_medic isEqualTo ACE_player}) then {
        // A valid continuous action refreshes LastSeen every <=2 s. If that heartbeat disappeared, release only
        // the orphaned global gate before the menu evaluates treatment eligibility.
        if (missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]) then {
            private _session = _medic getVariable ["ACM_core_ContinuousAction_Session", []];
            private _lastSeen = _medic getVariable ["ACM_core_ContinuousAction_LastSeen", -1e6];
            if ((count _session) < 2 || {(CBA_missionTime - _lastSeen) > 4}) then {
                missionNamespace setVariable ["ACM_core_ContinuousAction_Active", false];
                _medic setVariable ["ACM_core_ContinuousAction_Session", [], true];
            };
        };

        // Provider-only Semi-Fowler theatre has its own every-frame heartbeat. A lost PFH must not leave menu
        // stance/animation ownership latched forever; valid live choreography is deliberately left untouched.
        if (_medic getVariable ["ACME_headElev_seqActive", false]) then {
            private _seqSeen = _medic getVariable ["ACME_headElev_seqLastSeen", -1e6];
            if ((CBA_missionTime - _seqSeen) > 1) then {
                call ACME_fnc_headElevateCancelSeq;
            };
        };

        // Opening the medical menu is an explicit request to leave these two non-dialog hands-on maneuvers.
        // Cancel the exact current generation synchronously so its global continuous-action gate cannot make the
        // freshly opened menu's buttons appear dead while waiting for the PFH cleanup on the next frame.
        if (missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]) then {
            private _session = _medic getVariable ["ACM_core_ContinuousAction_Session", []];
            private _epoch = _session param [1, -1];
            private _sessionPatient = _session param [0, objNull];
            private _headTiltSession = if (!isNull _target) then {
                _target getVariable ["ACM_airway_HeadTilt_State_Session", []]
            } else {
                []
            };
            private _manualHold = _medic getVariable ["ACME_headElev_holding", []];

            private _ownsHeadTilt = _sessionPatient isEqualTo _target
                && {_epoch >= 0}
                && {_headTiltSession isEqualTo [_medic, _epoch]};
            private _ownsManualSemiFowler = (_manualHold param [0, objNull]) isEqualTo _target
                && {(_manualHold param [1, ""]) != ""};

            if (_ownsHeadTilt || {_ownsManualSemiFowler}) then {
                missionNamespace setVariable ["ACM_core_ContinuousAction_Active", false];
                _cancelledHandsOn = true;
            };
        };
    };

    // Pulse palpation is a modal cutRsc. Opening the medical menu must retire it immediately; otherwise the pulse
    // layer can survive underneath the menu and keep its input/pose handlers alive until the player finds Escape.
    if (uiNamespace getVariable ["ACME_PulseCheckActive", false]) then {
        uiNamespace setVariable ["ACME_PulseCheckCancel", true];
        "ACM_FeelPulse" cutText ["","PLAIN",0,false];
    };

    // Register a premixed bag at once when the patient menu opens. Pass the target explicitly. A bare call here
    // inherits this event's _this array and previously treated the medic as the optional patient argument.
    [_target] call ACME_fnc_syncPremixedBags;

    // Bind Unload to its original provider and generation, never a later ACE_player/menu.
    if (_medic isEqualTo ACE_player) then {
        // Let the cancelled hands-on controller run its exact onCancel/provider-exit cleanup first. The menu itself
        // is already live and fully interactive; it does not need to seize a crouch animation on this same frame.
        if (!_cancelledHandsOn) then {
            [_medic, _target, _display] call ACME_fnc_menuPoseStart;
        };
        if (!isNull _display) then {
            _display displayAddEventHandler ["Unload", {
                params ["_display"];
                private _owner = _display getVariable ["ACME_menuPoseOwner", []];
                if (count _owner == 2) then {[_owner select 0, false, _owner select 1] call ACME_fnc_menuPoseStop;};
            }];
        };
    };

    // the hardcore site relabel used to start a 0-delay PFH here that repainted ACE's buttons and injury list
    // after ACE had drawn them. it is gone. the buttons are now relabelled at the single ctrlSetText in
    // overrides/fn_updateActions.sqf, and the injury list on the ace_medical_gui_updateInjuryListPart event
    // below, both of which run inside ACE's own build rather than chasing it.
    // this also fixes a real defect: the PFH only started when hardcore was ALREADY on at the moment the menu
    // opened, so toggling the setting with the menu up appeared to do nothing.
}] call CBA_fnc_addEventHandler;

// Eligibility is patient-specific and only follows a real started treatment. Menu
// inspection and failed availability checks do not turn first contact into empty hands.
["ace_treatmentStarted", {
    params ["_medic", "_patient", ["_bodyPart", ""], ["_classname", ""]];
    if (call ACME_fnc_debugEnabled) then {
        diag_log format ["[ACME TREATMENT] started class=%1 body=%2 patient=%3 medic=%4",
            _classname, _bodyPart, if (isNull _patient) then {"null"} else {netId _patient},
            if (isNull _medic) then {"null"} else {netId _medic}];
    };
    if (!isNull _medic && {local _medic} && {!isNull _patient} && {_medic isNotEqualTo _patient}) then {
        _medic setVariable ["ACME_menuPoseAfterTreatment", _patient];
        _medic setVariable ["ACME_menuPoseCare", [_patient, _classname]];
    };
}] call CBA_fnc_addEventHandler;

// Some treatments close their source menu before their next-frame pose starts.
// Re-arm only the matching, genuinely started care on completion/cancellation.
{
    [_x, {
        params ["_medic", "_patient", ["_bodyPart", ""], ["_classname", ""]];
        if (isNull _medic || {!local _medic}) exitWith {};
        if ((_medic getVariable ["ACME_menuPoseCare", []]) isEqualTo [_patient, _classname]) then {
            _medic setVariable ["ACME_menuPoseCare", []];
            _medic setVariable ["ACME_menuPoseAfterTreatment", _patient];
        };
    }] call CBA_fnc_addEventHandler;
} forEach ["ace_treatmentSucceded", "ace_treatmentFailed"];

// Debug-only lifecycle markers make timer-with-no-result reports decisive without changing treatment ownership.
// ACE emits success after the class callback has run; failure means the progress action terminated before it.
["ace_treatmentSucceded", {
    params ["_medic", "_patient", ["_bodyPart", ""], ["_classname", ""]];
    if (call ACME_fnc_debugEnabled) then {
        diag_log format ["[ACME TREATMENT] success class=%1 body=%2 patient=%3",
            _classname, _bodyPart, if (isNull _patient) then {"null"} else {netId _patient}];
    };
}] call CBA_fnc_addEventHandler;
["ace_treatmentFailed", {
    params ["_medic", "_patient", ["_bodyPart", ""], ["_classname", ""]];
    if (call ACME_fnc_debugEnabled) then {
        diag_log format ["[ACME TREATMENT] failed class=%1 body=%2 patient=%3",
            _classname, _bodyPart, if (isNull _patient) then {"null"} else {netId _patient}];
    };
}] call CBA_fnc_addEventHandler;
