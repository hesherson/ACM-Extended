/* B212 assessment-only adapter of ACE common/fnc_progressBar.sqf (ACE3, GPL-2.0).
 * Existing controls, input cancellation, eligibility and callback arguments are unchanged.
 * Both assessments include entry and the complete normal-speed final RTM; missing work fails boundedly.
 * The bar follows observed completion, including graph-transition delay, with bounded failure.
 */
/*
 * Author: commy2, Glowbal, PabstMirror
 * Draw progress bar and execute given function if successful.
 * Finish/Failure/Conditional are all passed [_args, _elapsedTime, _totalTime, _errorCode]
 *
 * Arguments:
 * 0: Total Time (in game "time" seconds) <NUMBER>
 * 1: Arguments, passed to condition, fail and finish <ARRAY>
 * 2: On Finish: Code called or STRING raised as event. <CODE or STRING>
 * 3: On Failure: Code called or STRING raised as event. <CODE or STRING>
 * 4: Localized Title <STRING> (default: "")
 * 5: Code to check each frame <CODE> (default: {true})
 * 6: Exceptions for checking ace_common_fnc_canInteractWith (works like a permission system, if there is an exception, it will return true; e.g. "isNotSwimming" in the exceptions, the progress bar will work while swimming) <ARRAY> (default: [])
 * 7: Create progress bar as dialog, this blocks user input <BOOL> (default: true)
 *
 * Return Value:
 * None
 *
 * Example:
 * [5, [], {Hint "Finished!"}, {hint "Failure!"}, "My Title"] call ace_common_fnc_progressBar
 *
 * Public: Yes
 */

params ["_totalTime", "_args", "_onFinish", "_onFail", ["_localizedTitle", ""], ["_condition", {true}], ["_exceptions", []], ["_dialog", true]];

private _player = ACE_player;

//Open Dialog and set the title
closeDialog 0;
if (_dialog) then {
    createDialog "ace_common_ProgressBar_Dialog";
} else {
    "ace_common_progressBarDisplay" cutRsc ["ace_common_ProgressBar_Display", "PLAIN"];
};

private _display = uiNamespace getVariable "ace_common_dlgProgress";

// Ensure CBA keybindings are hooked into the display
_display call (uiNamespace getVariable "CBA_events_fnc_initDisplayCurator");

// Hide cursor by using custom transparent cursor
if (_dialog) then {
    private _map = _display displayCtrl 101;
    _map ctrlMapCursor ["", "ace_common_blank"];
} else { // Add key handler for ESC to cancel
    [0x01, [false, false, false], {
        "ace_common_progressBarDisplay" cutText ["", "PLAIN"];
        ["ace_common_progressBarKeyHandler", "keydown"] call CBA_fnc_removeKeyHandler;
        true
    }, "keydown", "ace_common_progressBarKeyHandler"] call CBA_fnc_addKeyHandler;
};

(uiNamespace getVariable "ace_common_ctrlProgressBarTitle") ctrlSetText _localizedTitle;

//Adjust position based on user setting:
private _ctrlPos = ctrlPosition (uiNamespace getVariable "ace_common_ctrlProgressBarTitle");
_ctrlPos set [1, ((0 + 29 * ace_common_settingProgressBarLocation) * ((((safeZoneW / safeZoneH) min 1.2) / 1.2) / 25) + (safeZoneY + (safeZoneH - (((safeZoneW / safeZoneH) min 1.2) / 1.2))/2))];

(uiNamespace getVariable "ace_common_ctrlProgressBG") ctrlSetPosition _ctrlPos;
(uiNamespace getVariable "ace_common_ctrlProgressBG") ctrlCommit 0;
(uiNamespace getVariable "ace_common_ctrlProgressBar") ctrlSetPosition _ctrlPos;
(uiNamespace getVariable "ace_common_ctrlProgressBar") ctrlCommit 0;
(uiNamespace getVariable "ace_common_ctrlProgressBarTitle") ctrlSetPosition _ctrlPos;
(uiNamespace getVariable "ace_common_ctrlProgressBarTitle") ctrlCommit 0;

[{
    (_this select 0) params ["_args", "_onFinish", "_onFail", "_condition", "_player", "_startTime", "_totalTime", "_exceptions", "_title", "_dialog", "_initialTime"];

    private _elapsedTime = CBA_missionTime - _startTime;
    private _errorCode = -1;
    private _assessment = _player getVariable ["ACME_assessment", []];
    if ((_assessment param [0, -2]) == (_args param [7, -1]) && {(_assessment param [0, -2]) >= 0}) then {
        private _observedTotal = _assessment param [12, -1];
        if (_observedTotal > 0) then {_totalTime = _observedTotal;};
        if ((_assessment param [2, -1]) == 3) then {_totalTime = _elapsedTime;};
        (_this select 0) set [6, _totalTime];
    };

    // this does not check: target fell unconscious, target died, target moved inside vehicle / left vehicle, target moved outside of players range, target moves at all.
    if (isNull (uiNamespace getVariable ["ace_common_ctrlProgressBar", controlNull])) then {
        _errorCode = 1;
    } else {
        if (ACE_player != _player || !alive _player) then {
            _errorCode = 2;
        } else {
            if !([_args, _elapsedTime, _totalTime, _errorCode] call _condition) then {
                _errorCode = 3;
            } else {
                if !([_player, objNull, _exceptions] call ace_common_fnc_canInteractWith) then {
                    _errorCode = 4;
                } else {
                    if (!_dialog && {dialog}) then {
                        _errorCode = 5;
                    } else {
                        if (_elapsedTime >= _totalTime || {_elapsedTime >= _initialTime + 5}) then {
                            private _decision = [_args, _elapsedTime, _totalTime, _initialTime] call ACME_fnc_assessmentCompletion;
                            if (_decision < 0) then {
                                _errorCode = 3;
                            } else {
                                if (_decision > _totalTime) then {
                                    // The RTM is still moving. Keep this same progress display/input episode and
                                    // use the observed remaining duration on the following owner frame.
                                    _totalTime = _decision;
                                    (_this select 0) set [6, _totalTime];
                                } else {
                                    _errorCode = 0;
                                };
                            };
                        };
                    };
                };
            };
        };
    };

    if (_errorCode != -1) then {
        //Error or Success, close dialog and remove PFEH

        //Only close dialog if it's the progressBar:
        if (!isNull (uiNamespace getVariable ["ace_common_ctrlProgressBar", controlNull])) then {
            if (_dialog) then {
                closeDialog 0;
            } else {
                "ace_common_progressBarDisplay" cutText ["", "PLAIN"];
                // Remove key handler for non-dialog bar
                ["ace_common_progressBarKeyHandler", "keydown"] call CBA_fnc_removeKeyHandler;
            };
        };

        [_this select 1] call CBA_fnc_removePerFrameHandler;

        if (_errorCode == 0) then {
            if (_onFinish isEqualType "") then {
                [_onFinish, [_args, _elapsedTime, _totalTime, _errorCode]] call CBA_fnc_localEvent;
            } else {
                [_args, _elapsedTime, _totalTime, _errorCode] call _onFinish;
            };
        } else {
            if (_onFail isEqualType "") then {
                [_onFail, [_args, _elapsedTime, _totalTime, _errorCode]] call CBA_fnc_localEvent;
            } else {
                [_args, _elapsedTime, _totalTime, _errorCode] call _onFail;
            };
        };
    } else {
        //Update Progress Bar (ratio of elepased:total)
        private _readout = [_elapsedTime, _totalTime, (_this select 0) param [11, [-1,0]]] call ACME_fnc_assessmentReadout;
        (_this select 0) set [11, _readout];
        private _ratio = _readout select 1;
        (uiNamespace getVariable "ace_common_ctrlProgressBar") progressSetPosition _ratio;
        switch (ace_common_progressBarInfo) do {
            case 0: {};
            case 1: {
                (uiNamespace getVariable "ace_common_ctrlProgressBarTitle") ctrlSetText (_title + format [" (%1", floor (_ratio * 100)] + "%)");
            };
            case 2: {
                (uiNamespace getVariable "ace_common_ctrlProgressBarTitle") ctrlSetText (_title + " " + format [localize "STR_ACE_Common_TimeLeft", _readout select 0]);
            };
        };
    };
}, 0, [_args, _onFinish, _onFail, _condition, _player, CBA_missionTime, _totalTime, _exceptions, _localizedTitle, _dialog, _totalTime]] call CBA_fnc_addPerFrameHandler;
