// a compile-time replacement of ACM_circulation_fnc_Syringe_Draw_Button.
// instead of ACE's full-screen progress bar, this grays the button of the draw dialog itself, 84003 for draw and
// 84004 for push, and relabels it "Drawing..." or "Pushing..." for the duration of the action, then restores its
// text and re-enables it, so you can draw drug after drug without the dialog tearing down.
// a push, meaning draw and administer, shows "Drawing..." and then "Pushing...". the durations are tunable through
// ACME_sk_drawSec and ACME_sk_pushSec, defaulting to 2 s.
params [["_type", 0]];
ACME_lastSyringeBtnType = _type;

if ((missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0]) <= 0) exitWith {};
if (_type > 0 && {isNull (missionNamespace getVariable ["ACM_circulation_SyringeDraw_Target", objNull])}) exitWith {};

private _medication = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medication", ""];
if (_medication == "EpinephrineCardiac") exitWith {[_type] call ACME_fnc_epinephrineDrawCardiac;};
private _medicationName = localize (format ["STR_ACM_Circulation_Medication_%1", _medication]);

private _display = findDisplay 84000;
private _drawSec = missionNamespace getVariable ["ACME_sk_drawSec", 2];
private _pushSec = missionNamespace getVariable ["ACME_sk_pushSec", 2];
private _customName = "";

// disable both action buttons while busy, so a second click cannot fire mid-action.
{ private _c = _display displayCtrl _x; if (!isNull _c) then {_c ctrlEnable false}; } forEach [84003, 84004];

if (_type > 0) then {
    // push, meaning draw and administer: "Drawing..." for _drawSec, then finalize, then "Pushing..." for _pushSec, then
    // inject.
    private _iv = _type != 2;
    private _push = _display displayCtrl 84004;
    private _orig = ["Push", ctrlText _push] select (!isNull _push);
    if (!isNull _push) then { _push ctrlSetText "Drawing..."; };

    [{
        _this params ["_display", "_push", "_orig", "_iv", "_pushSec"];
        // finalize the drawn syringe, the same call the draw path of ACM makes, then show the push phase.
        private _prepared = [
            ACE_player,
            missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medication", ""],
            missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0],
            missionNamespace getVariable ["ACM_circulation_SyringeDraw_Size", 10]
        ] call ACM_circulation_fnc_Syringe_PrepareFinish;
        if (!_prepared) exitWith {
            if (!isNull _push) then {_push ctrlSetText _orig;};
            {private _c=_display displayCtrl _x; if (!isNull _c) then {_c ctrlEnable true};} forEach [84003,84004];
        };
        if (!isNull _push) then { _push ctrlSetText "Pushing..."; };

        [{
            _this params ["_display", "_push", "_orig", "_iv"];
            [
                ACE_player,
                missionNamespace getVariable ["ACM_circulation_SyringeDraw_Target", objNull],
                missionNamespace getVariable ["ACM_circulation_SyringeDraw_TargetPart", ""],
                missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medication", ""],
                missionNamespace getVariable ["ACM_circulation_SyringeDraw_Size", 10],
                _iv,
                missionNamespace getVariable ["ACM_circulation_reusableSyringe", false]
            ] call ACM_circulation_fnc_Syringe_Inject;
            if (!isNull _push) then { _push ctrlSetText _orig; };
            { private _c = _display displayCtrl _x; if (!isNull _c) then {_c ctrlEnable true}; } forEach [84003, 84004];
        }, [_display, _push, _orig, _iv], _pushSec] call CBA_fnc_waitAndExecute;
    }, [_display, _push, _orig, _iv, _pushSec], _drawSec] call CBA_fnc_waitAndExecute;
} else {
    // draw only: "Drawing..." for _drawSec, then finalize. the button re-enables so the next drug can be drawn.
    playSound "ACME_SyringeDraw";
    private _draw = _display displayCtrl 84003;
    private _orig = ["Draw", ctrlText _draw] select (!isNull _draw);
    if (!isNull _draw) then { _draw ctrlSetText "Drawing..."; };

    [{
        _this params ["_display", "_draw", "_orig", "_medicationName", "_customName"];
        // capture the draw before preparefinish, which may clear the syringedraw vars, then store it.
        call ACME_fnc_skPendingTagCommit;
        private _med  = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medication", ""];
        private _size = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Size", 10];
        // The prepared magazine and its persistent row must use the same hundredth-mL quantity.
        private _amt  = (round ((missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0]) * 100)) / 100;
        private _prepared = [ACE_player, _med, _amt, _size] call ACM_circulation_fnc_Syringe_PrepareFinish;

        // the drawn drugs land in the "Drawn" list only after exact source solution was successfully reserved.
        if (_prepared && {_med != ""}) then {
            private _store = ACE_player getVariable ["ACME_narcStore", []];
            private _entry = [[_med, _size, _amt, _customName]] call ACME_fnc_skApplyPendingTag;
            _store pushBack _entry;
            ACE_player setVariable ["ACME_narcStore", _store, true];
            call ACME_fnc_skRefreshDrawn;
            call ACME_fnc_skAfterSaveOpenBody;
        };

        [format [localize "STR_ACM_Circulation_Syringe_Drawn", _medicationName], 1.5, ACE_player] call ace_common_fnc_displayTextStructured;
        if (!isNull _draw) then { _draw ctrlSetText _orig; };
        { private _c = _display displayCtrl _x; if (!isNull _c) then {_c ctrlEnable true}; } forEach [84003, 84004];
    }, [_display, _draw, _orig, _medicationName, _customName], _drawSec] call CBA_fnc_waitAndExecute;
};
