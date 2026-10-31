// a compile-time replacement of ACM_circulation_fnc_Syringe_Draw_Button.
// instead of ACE's full-screen progress bar, this grays the button of the draw dialog itself, 84003 for draw and
// 84004 for push, and relabels it "Drawing..." or "Pushing..." for the duration of the action, then restores its
// text and re-enables it, so you can draw drug after drug without the dialog tearing down.
// a push, meaning draw and administer, shows "Drawing..." and then "Pushing...". the durations are tunable through
// ACME_sk_drawSec and ACME_sk_pushSec, defaulting to 2 s.
params [["_type", 0]];
ACME_lastSyringeBtnType = _type;
private _medic = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medic", objNull];
if (isNull _medic) then {_medic = call ACME_fnc_controlledProvider;};
if (isNull _medic || {!local _medic} || {_medic isNotEqualTo (call ACME_fnc_controlledProvider)}) exitWith {};

if ((missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0]) <= 0) exitWith {};
if (_type > 0 && {isNull (missionNamespace getVariable ["ACM_circulation_SyringeDraw_Target", objNull])}) exitWith {};

private _medication = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medication", ""];
if (_medication == "EpinephrineCardiac") exitWith {[_type] call ACME_fnc_epinephrineDrawCardiac;};
private _medicationName = localize (format ["STR_ACM_Circulation_Medication_%1", _medication]);

private _display = findDisplay 84000;
private _drawSec = missionNamespace getVariable ["ACME_sk_drawSec", 2];
private _pushSec = missionNamespace getVariable ["ACME_sk_pushSec", 2];
private _customName = "";
private _drawContext = [_medication, missionNamespace getVariable ["ACM_circulation_SyringeDraw_Size", 10],
    (round ((missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0]) * 100)) / 100,
    missionNamespace getVariable ["ACM_circulation_SyringeDraw_Target", objNull],
    missionNamespace getVariable ["ACM_circulation_SyringeDraw_TargetPart", ""]];

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
        _this params ["_display", "_push", "_orig", "_iv", "_pushSec", "_medic", "_drawContext"];
        if (isNull _display || {isNull _medic} || {!local _medic} || {_medic isNotEqualTo (call ACME_fnc_controlledProvider)}) exitWith {};
        // Capture the exact freshly drawn magazine through the legacy push
        // timer. The background inventory importer must not convert it while
        // this callback still owns its original direct-push workflow.
        _drawContext params ["_drawMed", "_drawSize", "_drawMl", "_drawPatient", "_drawPart"];
        private _drawAmmo = round (_drawMl * 100);
        private _drawMedic = _medic;
        // finalize the drawn syringe, the same call the draw path of ACM makes, then show the push phase.
        private _prepared = [
            _medic,
            _drawMed,
            _drawMl,
            _drawSize
        ] call ACM_circulation_fnc_Syringe_PrepareFinish;
        if (!_prepared) exitWith {
            if (!isNull _push) then {_push ctrlSetText _orig;};
            {private _c=_display displayCtrl _x; if (!isNull _c) then {_c ctrlEnable true};} forEach [84003,84004];
        };
        private _pendingId = format ["nativePush:%1:%2:%3",clientOwner,diag_tickTime,_drawAmmo];
        private _pending = _drawMedic getVariable ["ACME_nativeSyringePending",[]];
        private _drawClass = format ["ACM_Syringe_%1_%2",_drawSize,_drawMed];
        _pending pushBack [_drawClass,_drawAmmo,_pendingId,diag_tickTime + _pushSec + 30];
        _drawMedic setVariable ["ACME_nativeSyringePending",_pending,false];
        private _drawReceipt = [_drawClass,_drawAmmo,_pendingId];
        if (!isNull _push) then { _push ctrlSetText "Pushing..."; };

        [{
            _this params ["_display", "_push", "_orig", "_iv","_drawMedic","_drawPatient","_drawPart","_drawMed","_drawSize","_drawReceipt"];
            if (!isNull _drawMedic && {local _drawMedic} && {alive _drawMedic}
                && {_drawMedic isEqualTo (call ACME_fnc_controlledProvider)}) then {[
                _drawMedic,
                _drawPatient,
                _drawPart,
                _drawMed,
                _drawSize,
                _iv,
                missionNamespace getVariable ["ACM_circulation_reusableSyringe", false],
                _drawReceipt
            ] call ACM_circulation_fnc_Syringe_Inject;};
            private _pending = _drawMedic getVariable ["ACME_nativeSyringePending",[]];
            _pending = _pending select {(_x param [2,""]) != (_drawReceipt select 2)};
            _drawMedic setVariable ["ACME_nativeSyringePending",_pending,false];
            if (!isNull _push) then { _push ctrlSetText _orig; };
            { private _c = _display displayCtrl _x; if (!isNull _c) then {_c ctrlEnable true}; } forEach [84003, 84004];
        }, [_display, _push, _orig, _iv,_drawMedic,_drawPatient,_drawPart,_drawMed,_drawSize,_drawReceipt], _pushSec] call CBA_fnc_waitAndExecute;
    }, [_display, _push, _orig, _iv, _pushSec, _medic, _drawContext], _drawSec] call CBA_fnc_waitAndExecute;
} else {
    // draw only: "Drawing..." for _drawSec, then finalize. the button re-enables so the next drug can be drawn.
    playSound "ACME_SyringeDraw";
    private _draw = _display displayCtrl 84003;
    private _orig = ["Draw", ctrlText _draw] select (!isNull _draw);
    if (!isNull _draw) then { _draw ctrlSetText "Drawing..."; };

    [{
        _this params ["_display", "_draw", "_orig", "_medicationName", "_customName", "_medic", "_drawContext"];
        if (isNull _display || {isNull _medic} || {!local _medic} || {_medic isNotEqualTo (call ACME_fnc_controlledProvider)}) exitWith {};
        // capture the draw before preparefinish, which may clear the syringedraw vars, then store it.
        call ACME_fnc_skPendingTagCommit;
        _drawContext params ["_med", "_size", "_amt"];
        // The prepared magazine and its persistent row must use the same hundredth-mL quantity.
        private _prepared = [_medic, _med, _amt, _size] call ACM_circulation_fnc_Syringe_PrepareFinish;

        // the drawn drugs land in the "Drawn" list only after exact source solution was successfully reserved.
        if (_prepared && {_med != ""}) then {
            private _store = _medic getVariable ["ACME_narcStore", []];
            private _entry = [[_med, _size, _amt, _customName]] call ACME_fnc_skApplyPendingTag;
            _store pushBack _entry;
            [_medic,_store] call ACME_fnc_narcStoreCommit;
            call ACME_fnc_skRefreshDrawn;
            call ACME_fnc_skAfterSaveOpenBody;
        };

        [format [localize "STR_ACM_Circulation_Syringe_Drawn", _medicationName], 1.5, _medic] call ace_common_fnc_displayTextStructured;
        if (!isNull _draw) then { _draw ctrlSetText _orig; };
        { private _c = _display displayCtrl _x; if (!isNull _c) then {_c ctrlEnable true}; } forEach [84003, 84004];
    }, [_display, _draw, _orig, _medicationName, _customName, _medic, _drawContext], _drawSec] call CBA_fnc_waitAndExecute;
};
