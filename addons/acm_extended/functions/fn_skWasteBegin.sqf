// enter the saline-flush waste stage on the open draw dialog. it copies ACM's own plunger geometry and drag math,
// from fnc_syringe_draw, so the plunger behaves exactly like a real syringe: the flush opens full of saline with
// the plunger seated at the bottom limit, the drug menu grays, and the draw button becomes "Waste". a per-frame
// handler modeled on ACM's syringe_draw loop lets you click the plunger and drag it up to waste saline, and
// committing locks the floor and flips to the draw stage, in fn_skwastecommit.
// call it as [_flushClass] call ACME_fnc_skWasteBegin.
params [["_flushClass", "ACM_SalineFlush_10"]];
disableSerialization;
private _acmeCanvas = call ACME_fnc_uiCanvas;
_acmeCanvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
private _dlg = findDisplay 84000;
if (isNull _dlg) exitWith {};
// Do not apply a 10 mL fill to geometry captured for another syringe size.
if ((missionNamespace getVariable ["ACM_circulation_SyringeDraw_Size", 0]) != 10) exitWith {};
if (([ACE_player, _flushClass] call ACME_fnc_itemCount) < 1) exitWith {};

private _cap = 10;  // the wired flush is 10 ml.
uiNamespace setVariable ["ACME_SK_WasteCap", _cap];
uiNamespace setVariable ["ACME_SK_CurSize", 10];
uiNamespace setVariable ["ACME_SK_WasteFill", _cap];
uiNamespace setVariable ["ACME_SK_WasteNS", _cap];
// A flush starts with saline only; discard the previous vial selection and label.
ACM_circulation_SyringeDraw_Medication = "";
ACM_circulation_SyringeDraw_MedicationSelected = false;
ACM_circulation_SyringeDraw_MedicationSelected_Index = -1;
(_dlg displayCtrl 84006) lbSetCurSel -1;
(_dlg displayCtrl 84001) ctrlSetText "Saline flush (10 mL)";
uiNamespace setVariable ["ACME_SK_WasteFlushClass", _flushClass];
uiNamespace setVariable ["ACME_SK_WasteStage", "waste"];
uiNamespace setVariable ["ACME_SK_WasteFloorMl", 0];  // ml of saline that must remain, which is 0 in the waste stage.
uiNamespace setVariable ["ACME_SK_WasteMoving", false];
// compounding auto-starts on open now, so a flush pick has to drop any drug components accumulated so far. a flush
// syringe and a compound are different things and must not carry each other's state.
uiNamespace setVariable ["ACME_SK_CompoundComponents", []];
uiNamespace setVariable ["ACME_SK_CompoundVials", []];

// the geometry comes straight from ACM, set by ACM_circulation_fnc_Syringe_Draw on open. maxdose must be the full
// capacity so the plunger can travel the whole barrel, because ACM caps the bottom limit by maxdose.
private _size = ACM_circulation_SyringeDraw_Size;
ACM_circulation_SyringeDraw_MaxDose = _size;  // the full-barrel travel for the flush.
private _limitTop    = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitTop", -1];
private _limitBottom = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitBottom", -1];
private _plungerVisIdc = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_PlungerVisual", -1];
private _adjust = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_PlungerAdjustment", 0];
if (_limitTop < 0 || {_limitBottom < 0}) exitWith {
    ["Draw dialog not ready. Reopen and try again.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// seat the plunger and the visual at the bottom, full of saline, exactly the way ACM positions them. drawnamount is
// the fill, which is the capacity.
private _plunger = _dlg displayCtrl 84009;
private _plungerVis = _dlg displayCtrl _plungerVisIdc;
(ctrlPosition _plunger) params ["_px", "", "_pw", "_ph"];
_plunger ctrlSetPosition [_px, _limitBottom, _pw, _ph];
_plunger ctrlCommit 0;
if (!isNull _plungerVis) then {
    (ctrlPosition _plungerVis) params ["_vx", "", "_vw", "_vh"];
    _plungerVis ctrlSetPosition [_vx, (_limitBottom - _adjust), _vw, _vh];
    _plungerVis ctrlCommit 0;
};
ACM_circulation_SyringeDraw_DrawnAmount = _cap;
ACM_circulation_SyringeDraw_Moving = false;

// gray the drug menu until saline has been wasted, because no drug goes into a full syringe.
private _medList = _dlg displayCtrl 84006;
if (!isNull _medList) then { _medList ctrlEnable false; };
private _medListBtn = _dlg displayCtrl 84007;
if (!isNull _medListBtn) then { _medListBtn ctrlEnable false; };

// button 84003 becomes waste, and push and inject are hidden during the flush flow.
private _btn = _dlg displayCtrl 84003;
if (!isNull _btn) then {
    _btn ctrlSetText "Waste";
    _btn ctrlSetTooltip "Click the plunger, drag up to waste saline, then press Waste to lock it in";
    _btn ctrlEnable true;
    _btn ctrlSetEventHandler ["ButtonClick", "call ACME_fnc_skWasteCommit"];
    _btn ctrlCommit 0;
};
{ private _c = _dlg displayCtrl _x; if (!isNull _c) then { _c ctrlShow false; _c ctrlEnable false; }; } forEach [84004, 84005];

// make the plunger draggable: clicking it toggles wastemoving. it mirrors ACM's syringe_draw_move and is gated on
// our stage instead of medicationselected. ACM's plunger uses onmousebuttonup.
_plunger ctrlSetEventHandler ["MouseButtonUp", "call ACME_fnc_skWasteToggleMove"];
_plunger ctrlSetTooltip "Click to grab the plunger, move to waste, click again to release";


// the per-frame plunger loop, modeled on ACM's syringe_draw per-frame block. it drives the plunger from the mouse
// when wastemoving, clamped between the stage floor and the full and empty limits, and derives the saline fill.
// there is one pfh per dialog, so drop any prior one.
private _old = uiNamespace getVariable ["ACME_SK_WastePFH", -1];
if (_old >= 0) then { [_old] call CBA_fnc_removePerFrameHandler; };
private _h = [{
    params ["_a", "_hid"];
    private _d = findDisplay 84000;
    private _stage = uiNamespace getVariable ["ACME_SK_WasteStage", ""];
    if (isNull _d || {_stage == ""}) exitWith {
        [_hid] call CBA_fnc_removePerFrameHandler;
        uiNamespace setVariable ["ACME_SK_WastePFH", -1];
    };
    // Once saline has been wasted, the flush behaves like the normal multi-component syringe: the medication
    // list remains selectable between pulls and the current source vial is tracked explicitly.
    if (_stage == "draw" && {!(uiNamespace getVariable ["ACME_SK_WasteMoving", false])}) then {
        private _ml=_d displayCtrl 84006; private _mlb=_d displayCtrl 84007;
        if (!isNull _ml && {!(ctrlEnabled _ml)}) then {_ml ctrlEnable true;};
        if (!isNull _mlb && {!(ctrlEnabled _mlb)}) then {_mlb ctrlEnable true;};
        if (!isNull _ml) then {
            private _sel=lbCurSel _ml;
            if (_sel>=0) then {
                private _selMed=_ml lbData _sel;
                if (_selMed!="" && {_selMed!=ACM_circulation_SyringeDraw_Medication}) then {
                    ACM_circulation_SyringeDraw_Medication=_selMed;
                    ACM_circulation_SyringeDraw_MedicationSelected=true;
                    ACM_circulation_SyringeDraw_MaxDose=ACM_circulation_SyringeDraw_Size;
                };
            };
        };
    };
    if !(uiNamespace getVariable ["ACME_SK_WasteMoving", false]) exitWith {};

    private _cap = uiNamespace getVariable ["ACME_SK_WasteCap", 10];
    private _size = ACM_circulation_SyringeDraw_Size;
    private _floorMl = uiNamespace getVariable ["ACME_SK_WasteFloorMl", 0];  // ml that must remain.
    private _limitTop    = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitTop", -1];
    private _limitBottom = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitBottom", -1];
    private _limitTopMouse = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitTopMouse", _limitTop];
    private _adjust = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_PlungerAdjustment", 0];
    private _visIdc = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_PlungerVisual", -1];
    private _plunger = _d displayCtrl 84009;
    private _plungerVis = _d displayCtrl _visIdc;
    if (isNull _plunger) exitWith {};

    // the plunger travels between the locked floor, the top of the allowed range, and full, at the bottom. map both to
    // y.
    private _floorY = linearConversion [0, _size, _floorMl, _limitTop, _limitBottom, true];
    (ctrlPosition _plunger) params ["_plungerX", "", "_plungerW", "_plungerH"];
    private _mouseOffset=_plungerH/2;
    getMousePosition params ["_mouseX","_mouseY"];

    private _maxFill=_size;
    if (_stage == "draw") then {
        private _medNow=ACM_circulation_SyringeDraw_Medication;
        private _lockedSame=0;
        if (!isNil "_medNow" && {_medNow!=""}) then {{if ((_x param [0,""])==_medNow) then {_lockedSame=_lockedSame+(_x param [1,0]);};} forEach (uiNamespace getVariable ["ACME_SK_CompoundComponents",[]]);};
        private _unlocked=if (isNil "_medNow" || {_medNow==""}) then {0} else {["limit",_medNow,_lockedSame+(((uiNamespace getVariable ["ACME_SK_WasteFill",_floorMl])-_floorMl) max 0),_d] call ACME_fnc_vialSession};
        private _newAvailable=(_unlocked-_lockedSame) max 0;
        _maxFill=(_floorMl+((_size-_floorMl) min _newAvailable)) max _floorMl min _size;
    };
    private _maxY=linearConversion [0,_size,_maxFill,_limitTop,_limitBottom,true];
    ACM_circulation_SyringeDraw_MaxDose=_maxFill;
    private _floorMouse=_floorY+_mouseOffset;
    private _maxMouse=_maxY+_mouseOffset;
    // Keep the native sticky cursor feel, but use the actual moving grab-control center instead of a canvas-derived
    // anchor. This keeps the mouse physically attached to the plunger and prevents the post-page-layout jump.
    private _mouseYClamped=(_maxMouse min _mouseY max _floorMouse);
    setMousePosition [_plungerX + (_plungerW / 2), _mouseYClamped];
    private _rawY=(_mouseYClamped-_mouseOffset) min _maxY max _floorY;
    private _fill=linearConversion [_limitTop,_limitBottom,_rawY,0,_size,true] max _floorMl min _maxFill;
    private _newY=linearConversion [0,_size,_fill,_limitTop,_limitBottom,true];
    // Exact endpoints: allow a pull to return fully to its floor and allow the selected vial to bottom out at 0.00.
    if ((_rawY-_floorY) <= (2*pixelH) && {(_fill-_floorMl)<=0.015}) then {_fill=_floorMl; _newY=_floorY;};
    if ((_maxY-_rawY) <= (2*pixelH) && {(_maxFill-_fill)<=0.015}) then {_fill=_maxFill; _newY=_maxY;};
    _plunger ctrlSetPosition [_plungerX,_newY,_plungerW,_plungerH]; _plunger ctrlCommit 0;
    if (!isNull _plungerVis) then {(ctrlPosition _plungerVis) params ["_vx","","_vw","_vh"]; _plungerVis ctrlSetPosition [_vx,_newY-_adjust,_vw,_vh]; _plungerVis ctrlCommit 0;};
    ACM_circulation_SyringeDraw_DrawnAmount=_fill;
    uiNamespace setVariable ["ACME_SK_WasteFill",_fill];
}, 0, []] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_SK_WastePFH", _h];
