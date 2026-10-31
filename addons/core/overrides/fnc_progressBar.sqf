#include "..\script_component.hpp"
#include "\a3\ui_f\hpp\defineDIKCodes.inc"
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

private _acmeDPPlayer = call ACME_fnc_controlledProvider;
if (!isNull _acmeDPPlayer
    && {_acmeDPPlayer getVariable ["ACME_DP_Active", false]}
    && {(_acmeDPPlayer getVariable ["ACME_DP_Mode", ""]) in ["limb", "self"]}
    && {_totalTime isEqualType 0}) then {
    _totalTime = _totalTime * (missionNamespace getVariable ["ACME_DP_treatTimeMult", 1.6]);
};

private _player = call ACME_fnc_controlledProvider;

//Open Dialog and set the title
closeDialog 0;
if (_dialog) then {
    createDialog QACEGVAR(common,ProgressBar_Dialog);
} else {
    QACEGVAR(common,progressBarDisplay) cutRsc [QACEGVAR(common,ProgressBar_Display), "PLAIN"];
};

private _display = uiNamespace getVariable QACEGVAR(common,dlgProgress);

// Ensure CBA keybindings are hooked into the display
_display call (uiNamespace getVariable "CBA_events_fnc_initDisplayCurator");

// Hide cursor by using custom transparent cursor
if (_dialog) then {
    private _map = _display displayCtrl 101;
    _map ctrlMapCursor ["", QACEGVAR(common,blank)];
} else { // Add key handler for ESC to cancel
    [DIK_ESCAPE, [false, false, false], {
        QACEGVAR(common,progressBarDisplay) cutText ["", "PLAIN"];
        [QACEGVAR(common,progressBarKeyHandler), "keydown"] call CBA_fnc_removeKeyHandler;
        true
    }, "keydown", QACEGVAR(common,progressBarKeyHandler)] call CBA_fnc_addKeyHandler;
};

(uiNamespace getVariable QACEGVAR(common,ctrlProgressBarTitle)) ctrlSetText _localizedTitle;

//Adjust position based on user setting:
private _ctrlPos = ctrlPosition (uiNamespace getVariable QACEGVAR(common,ctrlProgressBarTitle));
_ctrlPos set [1, ((0 + 29 * ACEGVAR(common,settingProgressBarLocation)) * ((((safeZoneW / safeZoneH) min 1.2) / 1.2) / 25) + (safeZoneY + (safeZoneH - (((safeZoneW / safeZoneH) min 1.2) / 1.2))/2))];

(uiNamespace getVariable QACEGVAR(common,ctrlProgressBG)) ctrlSetPosition _ctrlPos;
(uiNamespace getVariable QACEGVAR(common,ctrlProgressBG)) ctrlCommit 0;
(uiNamespace getVariable QACEGVAR(common,ctrlProgressBar)) ctrlSetPosition _ctrlPos;
(uiNamespace getVariable QACEGVAR(common,ctrlProgressBar)) ctrlCommit 0;
(uiNamespace getVariable QACEGVAR(common,ctrlProgressBarTitle)) ctrlSetPosition _ctrlPos;
(uiNamespace getVariable QACEGVAR(common,ctrlProgressBarTitle)) ctrlCommit 0;

[{
    (_this select 0) params ["_args", "_onFinish", "_onFail", "_condition", "_player", "_startTime", "_totalTime", "_exceptions", "_title", "_dialog"];

    private _elapsedTime = CBA_missionTime - _startTime;
    private _errorCode = -1;

    // this does not check: target fell unconscious, target died, target moved inside vehicle / left vehicle, target moved outside of players range, target moves at all.
    if (isNull (uiNamespace getVariable [QACEGVAR(common,ctrlProgressBar), controlNull])) then {
        _errorCode = 1;
    } else {
        if ((call ACME_fnc_controlledProvider) != _player || !alive _player) then {
            _errorCode = 2;
        } else {
            if !([_args, _elapsedTime, _totalTime, _errorCode] call _condition) then {
                _errorCode = 3;
            } else {
                if !([_player, objNull, _exceptions] call ACEFUNC(common,canInteractWith)) then {
                    _errorCode = 4;
                } else {
                    if (!_dialog && {dialog}) then {
                        _errorCode = 5;
                    } else {
                        if (_elapsedTime >= _totalTime) then {
                            _errorCode = 0;
                        };
                    };
                };
            };
        };
    };

    if (_errorCode != -1) then {
        //Error or Success, close dialog and remove PFEH

        //Only close dialog if it's the progressBar:
        if (!isNull (uiNamespace getVariable [QACEGVAR(common,ctrlProgressBar), controlNull])) then {
            if (_dialog) then {
                closeDialog 0;
            } else {
                QACEGVAR(common,progressBarDisplay) cutText ["", "PLAIN"];
                // Remove key handler for non-dialog bar
                [QACEGVAR(common,progressBarKeyHandler), "keydown"] call CBA_fnc_removeKeyHandler;
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
        private _ratio = _elapsedTime / _totalTime;
        (uiNamespace getVariable QACEGVAR(common,ctrlProgressBar)) progressSetPosition _ratio;
        switch (ACEGVAR(common,progressBarInfo)) do {
            case 0: {};
            case 1: {
                (uiNamespace getVariable QACEGVAR(common,ctrlProgressBarTitle)) ctrlSetText (_title + format [" (%1", floor (_ratio * 100)] + "%)");
            };
            case 2: {
                (uiNamespace getVariable QACEGVAR(common,ctrlProgressBarTitle)) ctrlSetText (_title + " " + format [localize "STR_ACE_Common_TimeLeft", ceil (_totalTime - _elapsedTime)]);
            };
        };
    };
}, 0, [_args, _onFinish, _onFail, _condition, _player, CBA_missionTime, _totalTime, _exceptions, _localizedTitle, _dialog]] call CBA_fnc_addPerFrameHandler;
