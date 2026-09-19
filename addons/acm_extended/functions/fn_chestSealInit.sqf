disableSerialization;
params ["_display"];
private _oldPFH = uiNamespace getVariable ["ACME_CS_PFH", -1];
if (_oldPFH >= 0) then {[_oldPFH] call CBA_fnc_removePerFrameHandler;};
uiNamespace setVariable ["ACME_CS_PFH", -1];
uiNamespace setVariable ["ACME_CS_DLG", _display];
uiNamespace setVariable ["ACME_minigame_open", true];

// an escape hatch. a display does not close on esc, because that goes to the pause menu and leaves this panel
// sitting behind it. without this, a player can be trapped inside a procedure with no way out.
_display displayAddEventHandler ["KeyDown", {
    if (_this call ACME_fnc_minigameInput) exitWith {true};
    params ["", "_key"];
    if (_key == 1) exitWith { [86400] call ACME_fnc_minigameClose; true };  // 1 is dik_escape.
    false
}];  // it gates the ACE flashlights self-action.
[_display] call ACME_fnc_installLightKey;  // ctrl+win opens the flashlight picker.

call ACM_GUI_fnc_pauseMedicalMenuPFH;

private _medic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
private _patient = uiNamespace getVariable ["ACME_CS_Patient", objNull];
if (!isNull _patient) then {[_patient, "ui:chest:" + str clientOwner, true] call ACME_fnc_ecgJostleRequest;};
// Publish interest only on open/close, not for every cursor update.
private _viewer = ACE_player;
uiNamespace setVariable ["ACME_CS_presenceViewer", _viewer];
if (!isNull _viewer) then { _viewer setVariable ["ACME_CS_viewing", _patient, true]; };
ACME_CS_presence = createHashMap;
uiNamespace setVariable ["ACME_CS_SealsLeft", if (isNull _medic) then {0} else {[_medic, "ACM_ChestSeal"] call ace_common_fnc_getCountOfItem}];
uiNamespace setVariable ["ACME_CS_SpearsLeft", if (isNull _medic) then {0} else {[_medic, "ACME_NARSPEAR"] call ace_common_fnc_getCountOfItem}];
uiNamespace setVariable ["ACME_CS_Side", "front"];
uiNamespace setVariable ["ACME_CS_Dragging", false];
uiNamespace setVariable ["ACME_CS_ArchBlend", 0];
uiNamespace setVariable ["ACME_CS_FingerGlow", []];
uiNamespace setVariable ["ACME_CS_FlipLockedUntil", 0];
uiNamespace setVariable ["ACME_CS_VirtualFlip", false];
uiNamespace setVariable ["ACME_CS_Held", false];
uiNamespace setVariable ["ACME_CS_SpearHeld", false];

// The chest procedure always opens on the anterior/front diagram. Physical preparation is handled once by
// fn_chestSealPatientBegin; after that, only the explicit Flip button is allowed to change the diagram side.
uiNamespace setVariable ["ACME_CS_Side", "front"];

uiNamespace setVariable ["ACME_CS_Holes", []];
uiNamespace setVariable ["ACME_CS_netSnapshot", []];
uiNamespace setVariable ["ACME_CS_presenceTargets", []];
uiNamespace setVariable ["ACME_CS_presencePacket", []];
uiNamespace setVariable ["ACME_CS_presenceLastT", -1];
uiNamespace setVariable ["ACME_CS_presenceLastState", []];
uiNamespace setVariable ["ACME_CS_sessionNextPing", diag_tickTime + 5];
// Join after the controls and body geometry exist (also important on a listen server).

private _isFiniteNumber = {
    params ["_value"];
    ((typeName _value) isEqualTo "SCALAR") && {finite _value}
};

private _pw = pixelW;
private _ph = pixelH;
private _af = 0.5625;
if (([_pw] call _isFiniteNumber) && {[_ph] call _isFiniteNumber} && {_pw > 0} && {_ph > 0}) then {
    private _candidateAF = _pw / _ph;
    if (([_candidateAF] call _isFiniteNumber) && {_candidateAF > 0.05} && {_candidateAF < 4}) then {
        _af = _candidateAF;
    };
};
if !(([_af] call _isFiniteNumber) && {_af > 0.05} && {_af < 4}) then {
    private _resolution = getResolution;
    private _resW = _resolution param [0, 1920];
    private _resH = _resolution param [1, 1080];
    if (([_resW] call _isFiniteNumber) && {[_resH] call _isFiniteNumber} && {_resW > 0} && {_resH > 0}) then {
        private _candidateAF = _resH / _resW;
        if (([_candidateAF] call _isFiniteNumber) && {_candidateAF > 0.05} && {_candidateAF < 4}) then {
            _af = _candidateAF;
        };
    };
};
if !(([_af] call _isFiniteNumber) && {_af > 0.05} && {_af < 4}) then {_af = 0.5625;};
uiNamespace setVariable ["ACME_CS_AspectFix", _af];

private _szX = safeZoneX;
private _szY = safeZoneY;
private _szW = safeZoneW;
private _szH = safeZoneH;
if !(([_szX] call _isFiniteNumber) && {[_szY] call _isFiniteNumber} && {[_szW] call _isFiniteNumber} && {[_szH] call _isFiniteNumber} && {_szW > 0} && {_szH > 0}) then {
    _szX = 0;
    _szY = 0;
    _szW = 1;
    _szH = 1;
};
private _cx = _szX + (_szW / 2);

// B34: enlarge the complete body without cropping it. Fit the body and its
// right-hand tool column together; on narrow displays the horizontal fit wins.
// All procedural dimensions below use the same scale, including rake fingers.
private _bodyH = (_szH * 0.92) min ((_szW * 0.46) / (_af * 0.755));
private _layoutH = _bodyH / 0.78;
private _bodyW = _bodyH * _af;
private _slotH = _bodyH * 0.205;
private _slotW = _slotH * _af;
private _colW = _slotW;
private _gap = (_bodyH * 0.05) * _af;
private _totalW = _bodyW + _gap + _colW;
// center the dummy on screen, so the rake area is symmetric about the screen center, and the seal and spear slot
// column sits to its right. _totalW and _groupX are kept for reference and the body is centerd now.
private _groupX = _cx - (_totalW / 2);
private _bodyX = _cx - (_bodyW / 2);
private _bodyY = _szY + ((_szH - _bodyH) / 2);
private _colX = _bodyX + _bodyW + _gap;
uiNamespace setVariable ["ACME_CS_BodyRect", [_bodyX, _bodyY, _bodyW, _bodyH]];
// the unshaken rect. in a moving vehicle the tick offsets the body from this, and the hit-testing follows the
// body, so the casualty moves under your hands and your hand stays where you put it.
uiNamespace setVariable ["ACME_CS_BodyRectBase", [_bodyX, _bodyY, _bodyW, _bodyH]];

(_display displayCtrl 86401) ctrlSetPosition [_bodyX, _bodyY, _bodyW, _bodyH];
(_display displayCtrl 86401) ctrlCommit 0;

(missionNamespace getVariable ["ACME_CS_thoraxZoneFrac", [0.42, 0.225, 0.16, 0.135]]) params ["_fzx", "_fzy", "_fzw", "_fzh"];
private _zone = _display displayCtrl 86404;
// the shaped guide overlay shares the rect of the body, because the blue is baked at the chest location in the
// paa, so it aligns to the body image. the texture is swapped front to back in fn_chestsealrender.
private _zoneInsetX = (missionNamespace getVariable ["ACME_CS_zoneHorizontalInsetFrac", 0.04]) max 0 min 0.20;
_zone ctrlSetPosition [_bodyX + (_bodyW * _zoneInsetX), _bodyY, _bodyW * (1 - (2 * _zoneInsetX)), _bodyH];
_zone ctrlSetText "\acm_extended\ui\cs_zone_front_ca.paa";
_zone ctrlCommit 0;
_zone ctrlShow true;

// the interaction surface, which is the engine ui-coord source, plus the getMousePosition into ui
// auto-calibration.
// CS_Surface is a controls-group, so it receives mouse events, sized to the body. its MouseMoving and MouseHolding
// report the cursor in dialog ui coords exactly as the engine computes them, which is correct under any display
// mode, ultrawide non-stretch included. each event also feeds a min and max calibration of the getMousePosition
// into ui transform, so getMousePosition can be mapped correctly on frames where the event does not fire.
uiNamespace setVariable ["ACME_CS_EvtUI", []];
uiNamespace setVariable ["ACME_CS_EvtUITime", -1];
uiNamespace setVariable ["ACME_CS_FingerMode", 0];  // 0 means no hand on the chest until a button is held.
uiNamespace setVariable ["ACME_CS_CalXminG",  1e9];
uiNamespace setVariable ["ACME_CS_CalXmaxG", -1e9];
uiNamespace setVariable ["ACME_CS_CalYminG",  1e9];
uiNamespace setVariable ["ACME_CS_CalYmaxG", -1e9];
uiNamespace setVariable ["ACME_CS_CalXminU", 0];
uiNamespace setVariable ["ACME_CS_CalXmaxU", 0];
uiNamespace setVariable ["ACME_CS_CalYminU", 0];
uiNamespace setVariable ["ACME_CS_CalYmaxU", 0];
uiNamespace setVariable ["ACME_CS_CoordSrc", "init"];

private _surface = _display displayCtrl 86410;
_surface ctrlSetPosition [_bodyX, _bodyY, _bodyW, _bodyH];
_surface ctrlCommit 0;
_surface ctrlEnable true;
_surface ctrlShow true;

private _fnTrack = {
    params ["_ctrl", "_ex", "_ey"];
    if !((_ex isEqualType 0) && {_ey isEqualType 0} && {finite _ex} && {finite _ey}) exitWith {};
    uiNamespace setVariable ["ACME_CS_EvtUI", [_ex, _ey]];
    uiNamespace setVariable ["ACME_CS_EvtUITime", diag_tickTime];
    private _gmp = getMousePosition;
    _gmp params ["_gx", "_gy"];
    if !((_gx isEqualType 0) && {_gy isEqualType 0} && {finite _gx} && {finite _gy}) exitWith {};
    if (_gx < (uiNamespace getVariable ["ACME_CS_CalXminG",  1e9]))  then { uiNamespace setVariable ["ACME_CS_CalXminG", _gx]; uiNamespace setVariable ["ACME_CS_CalXminU", _ex]; };
    if (_gx > (uiNamespace getVariable ["ACME_CS_CalXmaxG", -1e9])) then { uiNamespace setVariable ["ACME_CS_CalXmaxG", _gx]; uiNamespace setVariable ["ACME_CS_CalXmaxU", _ex]; };
    if (_gy < (uiNamespace getVariable ["ACME_CS_CalYminG",  1e9]))  then { uiNamespace setVariable ["ACME_CS_CalYminG", _gy]; uiNamespace setVariable ["ACME_CS_CalYminU", _ey]; };
    if (_gy > (uiNamespace getVariable ["ACME_CS_CalYmaxG", -1e9])) then { uiNamespace setVariable ["ACME_CS_CalYmaxG", _gy]; uiNamespace setVariable ["ACME_CS_CalYmaxU", _ey]; };
};
_surface ctrlAddEventHandler ["MouseMoving", _fnTrack];
_surface ctrlAddEventHandler ["MouseHolding", _fnTrack];

private _toolYOffset = missionNamespace getVariable ["ACME_CS_toolColumnYOffset", 0.065];
if !(([_toolYOffset] call _isFiniteNumber) && {_toolYOffset >= 0} && {_toolYOffset < 0.25}) then {_toolYOffset = 0.065;};
private _colY = _bodyY + (_bodyH * 0.025) + (_layoutH * _toolYOffset);
private _countH = _layoutH * 0.032;
private _slotGap = _layoutH * 0.018;
private _inset = _slotH * 0.075;
private _logoH = _slotH - 2 * _inset;
private _logoW = _logoH * _af;

(_display displayCtrl 86420) ctrlSetPosition [_colX, _colY, _slotW, _slotH];
(_display displayCtrl 86420) ctrlCommit 0;
(_display displayCtrl 86424) ctrlSetPosition [_colX, _colY, _slotW, _slotH];
(_display displayCtrl 86424) ctrlCommit 0;
(_display displayCtrl 86422) ctrlSetPosition [_colX + (_slotW - _logoW) / 2, _colY + _inset, _logoW, _logoH];
(_display displayCtrl 86422) ctrlCommit 0;
(_display displayCtrl 86423) ctrlSetPosition [_colX, _colY + _slotH, _slotW, _countH];
(_display displayCtrl 86423) ctrlCommit 0;
uiNamespace setVariable ["ACME_CS_SlotRect", [_colX, _colY, _slotW, _slotH]];

private _spearY = _colY + _slotH + _countH + _slotGap;
(_display displayCtrl 86430) ctrlSetPosition [_colX, _spearY, _slotW, _slotH];
(_display displayCtrl 86430) ctrlCommit 0;
(_display displayCtrl 86434) ctrlSetPosition [_colX, _spearY, _slotW, _slotH];
(_display displayCtrl 86434) ctrlCommit 0;
(_display displayCtrl 86432) ctrlSetPosition [_colX + (_slotW - _logoW) / 2, _spearY + _inset, _logoW, _logoH];
(_display displayCtrl 86432) ctrlCommit 0;
(_display displayCtrl 86433) ctrlSetPosition [_colX, _spearY + _slotH, _slotW, _countH];
(_display displayCtrl 86433) ctrlCommit 0;
uiNamespace setVariable ["ACME_CS_SpearSlotRect", [_colX, _spearY, _slotW, _slotH]];

private _btnH = _layoutH * 0.050;
private _pad  = _layoutH * 0.014;
// the right-column button stack under the spear slot: the rake toggle on top, the flip beneath it and done
// beneath that, with equal padding between all three. the toggle previously floated left of the body.
private _rakeY = _spearY + _slotH + _countH + (_layoutH * 0.028);
private _rakeH = _btnH * 1.3;
(_display displayCtrl 86427) ctrlSetPosition [_colX, _rakeY, _slotW, _rakeH];
(_display displayCtrl 86427) ctrlCommit 0;
// the rake and feel toggle button is gone, because the hands live on the mouse buttons now: hold lmb to rake and
// hold RMB to feel for the 5th ics. that is one less control to hunt for mid-procedure. the existing cancel
// button is still the way out, so this slot is simply hidden rather than replaced with a redundant second
// exit.
(_display displayCtrl 86427) ctrlShow false;
(_display displayCtrl 86427) ctrlEnable false;
private _flipY = _rakeY + _rakeH + _pad;
(_display displayCtrl 86426) ctrlSetPosition [_colX, _flipY, _slotW, _btnH];
(_display displayCtrl 86426) ctrlCommit 0;
if ((uiNamespace getVariable ["ACME_CS_FlipLockedUntil", 0]) > diag_tickTime) then {
    (_display displayCtrl 86426) ctrlEnable false;
    (_display displayCtrl 86426) ctrlSetText "Flipping...";
    private _unlockDelay = ((uiNamespace getVariable ["ACME_CS_FlipLockedUntil", 0]) - diag_tickTime) max 0;
    [{
        disableSerialization;
        private _display = uiNamespace getVariable ["ACME_CS_DLG", displayNull];
        if (!isNull _display) then {
            private _btn = _display displayCtrl 86426;
            if (!isNull _btn) then {
                _btn ctrlEnable true;
                _btn ctrlSetText "Flip";
            };
        };
        uiNamespace setVariable ["ACME_CS_FlipLockedUntil", 0];
    }, [], _unlockDelay] call CBA_fnc_waitAndExecute;
};
(_display displayCtrl 86425) ctrlSetPosition [_colX, _flipY + _btnH + _pad, _slotW, _btnH];
(_display displayCtrl 86425) ctrlCommit 0;

private _fingerFactor = missionNamespace getVariable ["ACME_CS_fingerSizeFactor", 0.0125];  // smaller, tighter rake dots.
if !(([_fingerFactor] call _isFiniteNumber) && {_fingerFactor > 0}) then {_fingerFactor = 0.0125;};
private _dotH = _layoutH * _fingerFactor;
uiNamespace setVariable ["ACME_CS_DotH", _dotH];
uiNamespace setVariable ["ACME_CS_DotW", _dotH * _af];
uiNamespace setVariable ["ACME_CS_FingerSpacingH", _dotH * 0.88];
uiNamespace setVariable ["ACME_CS_FingerColorDecay", missionNamespace getVariable ["ACME_CS_fingerColorDecay", 0.28]];
uiNamespace setVariable ["ACME_CS_HoleH", _bodyH * 0.023];
uiNamespace setVariable ["ACME_CS_HoleW", (_bodyH * 0.023) * _af];
uiNamespace setVariable ["ACME_CS_ClickR", _bodyH * 0.05];
// the hole find radius. it is measured against the actual hole icon footprint, then clamped again in the tick
// loop, so a finger has to pass directly over the wound instead of sweeping nearby chest space.
private _findRadiusCfg = missionNamespace getVariable ["ACME_CS_findRadius", if (missionNamespace getVariable ["ACME_hcEff_cs", false]) then {0.006} else {0.0075}];
if !(([_findRadiusCfg] call _isFiniteNumber) && {_findRadiusCfg > 0}) then {_findRadiusCfg = 0.0075;};
uiNamespace setVariable ["ACME_CS_FindRadius", _bodyH * _findRadiusCfg];
// the rake drag weight: deliberately slow and less distance-scaled.
uiNamespace setVariable ["ACME_CS_DragBaseRate", missionNamespace getVariable ["ACME_CS_dragBaseRate", 0.55]];
uiNamespace setVariable ["ACME_CS_DragGainRate", missionNamespace getVariable ["ACME_CS_dragGainRate", 1.05]];
uiNamespace setVariable ["ACME_CS_DragMaxRate",  missionNamespace getVariable ["ACME_CS_dragMaxRate", 1.30]];
uiNamespace setVariable ["ACME_CS_DragLagDenom", missionNamespace getVariable ["ACME_CS_dragLagDenom", 0.36]];

private _applyRadiusCfg = missionNamespace getVariable ["ACME_CS_applyRadius", 0.062];
if !(([_applyRadiusCfg] call _isFiniteNumber) && {_applyRadiusCfg > 0}) then {_applyRadiusCfg = 0.062;};
uiNamespace setVariable ["ACME_CS_ApplyR", _bodyH * _applyRadiusCfg];
private _dragSpeedCfg = missionNamespace getVariable ["ACME_CS_dragMaxSpeed", 0.55];
if !(([_dragSpeedCfg] call _isFiniteNumber) && {_dragSpeedCfg >= 0}) then {_dragSpeedCfg = 0.55;};
uiNamespace setVariable ["ACME_CS_DragMaxSpeed", _bodyH * _dragSpeedCfg];
uiNamespace setVariable ["ACME_CS_DragPt", []];
uiNamespace setVariable ["ACME_CS_DragLast", -1];
uiNamespace setVariable ["ACME_CS_WastedCtrls", []];
uiNamespace setVariable ["ACME_CS_SealH", _bodyH * 0.05];
uiNamespace setVariable ["ACME_CS_SealW", (_bodyH * 0.05) * _af];

// the coordinates are taken from the supplied full-body placed overlays. screen-right is the patient's left.
uiNamespace setVariable ["ACME_CS_NCDTargetLeft", [0.57421875, 0.29296875]];
uiNamespace setVariable ["ACME_CS_NCDTargetRight", [0.4140625, 0.29296875]];
uiNamespace setVariable ["ACME_CS_NCDPlaceR", _bodyH * 0.018];
uiNamespace setVariable ["ACME_CS_NCDFadeR", _bodyH * 0.19];
// the acceptable 5th-ics placement zone per side, as an ellipse in body-fraction space, [centeru, centerv,
// radiusu, radiusv]. it is anchored on the authored midaxillary targets above, at a v of about 0.293, widened
// along the space through a large radiusu, and reaching about 0.05 toward the sternum, while kept thin in height
// through a small radiusv, so it only accepts a hit that is truly on the 5th intercostal line. the needle still
// renders at the authored target point. screen-right is the patient's left. it is tunable.
uiNamespace setVariable ["ACME_CS_NCDEllipseLeft",  [0.555, 0.293, 0.052, 0.015]];
uiNamespace setVariable ["ACME_CS_NCDEllipseRight", [0.445, 0.293, 0.052, 0.015]];

private _dots = [];
for "_i" from 0 to 3 do {
    private _d = _display ctrlCreate ["ACME_CS_Dot", -1];
    _d ctrlEnable false;
    _d ctrlShow false;
    _dots pushBack _d;
};
uiNamespace setVariable ["ACME_CS_Dots", _dots];

private _curSeal = _display ctrlCreate ["ACME_CS_PlacedSeal", -1];
_curSeal ctrlEnable false;
_curSeal ctrlShow false;
uiNamespace setVariable ["ACME_CS_CursorSeal", _curSeal];

private _curSpear = _display ctrlCreate ["ACME_CS_NCDSprite", -1];
_curSpear ctrlEnable false;
_curSpear ctrlShow false;
uiNamespace setVariable ["ACME_CS_CursorSpear", _curSpear];

private _placedLeft = _display ctrlCreate ["ACME_CS_NCDSprite", -1];
private _placedRight = _display ctrlCreate ["ACME_CS_NCDSprite", -1];
_placedLeft ctrlEnable false;
_placedRight ctrlEnable false;
_placedLeft ctrlSetText "\acm_extended\ui\items\nar_spear_left_placed_ca.paa";
_placedRight ctrlSetText "\acm_extended\ui\items\nar_spear_right_placed_ca.paa";
_placedLeft ctrlShow false;
_placedRight ctrlShow false;
uiNamespace setVariable ["ACME_CS_NCDPlacedCtrls", [_placedLeft, _placedRight]];

[] call ACME_fnc_chestSealRefreshSlot;
[] call ACME_fnc_chestSealRefreshSpearSlot;
[] call ACME_fnc_chestSealRender;

private _startTool = uiNamespace getVariable ["ACME_CS_StartTool", "seal"];
if (_startTool == "spear" && {(uiNamespace getVariable ["ACME_CS_SpearsLeft", 0]) > 0}) then {
    [] call ACME_fnc_chestSealToggleSpear;
};
uiNamespace setVariable ["ACME_CS_StartTool", ""];

private _pfh = [ACME_fnc_chestSealTick, 0, [_display]] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_CS_PFH", _pfh];
// THE WHEEL BURPS AN APPLIED SEAL, AND THE HANDLER CANNOT LIVE ON THE DISPLAY ALONE.
// a display level MouseZChanged does not fire while the cursor sits over a control, and on this panel the body
// picture and the interaction surface cover almost all of it, so a display handler on its own never fires at
// all. that is why the first version of this did nothing.
// fn_ivMinigameInit already carries the same note and the same cure, so this is that pattern rather than a new
// one: put the handler on every control as well as on the display.
// the two signatures differ, a control passing itself and a display passing itself, and fn_chestSealScroll reads
// neither. it takes its cursor and its geometry from uiNamespace exactly as fn_chestSealMouseDown does, so one
// handler serves both.
// the seal and hole controls are created later, by fn_chestSealRender, and they are ctrlEnable false so their
// mouse events fall through to the surface underneath. scrolling over a placed seal therefore lands on the
// surface, which is covered here.
private _fnCsScroll = {
    if ([_this,"wheel"] call ACME_fnc_minigameInputMouse) exitWith {true};
    params ["_src", ["_scroll", 0]];
    if (_scroll == 0) exitWith { false };
    [_src, _scroll] call ACME_fnc_chestSealScroll
};
_display displayAddEventHandler ["MouseZChanged", _fnCsScroll];
{
    if (!isNull _x) then { _x ctrlAddEventHandler ["MouseZChanged", _fnCsScroll]; };
} forEach (allControls _display);
// a fresh panel never inherits a burp that was running when the last one closed.
uiNamespace setVariable ["ACME_CS_BurpIdx", -1];
uiNamespace setVariable ["ACME_CS_BurpFired", false];
uiNamespace setVariable ["ACME_CS_BurpFrame", 0];
uiNamespace setVariable ["ACME_CS_BurpDir", 0];
uiNamespace setVariable ["ACME_CS_BurpSide", "right"];
_display displayAddEventHandler ["MouseButtonDown", {_this call ACME_fnc_chestSealMouseDown}];
// the hands are held on the mouse buttons now, where lmb is the four-finger rake and RMB is the single-finger
// feeler, so we need the up edge as well: releasing lifts that hand off the chest.
_display displayAddEventHandler ["MouseButtonUp", {_this call ACME_fnc_chestSealMouseUp}];
uiNamespace setVariable ["ACME_CS_LMB", false];
uiNamespace setVariable ["ACME_CS_RMB", false];

// On a listen/local server we are already the chest-state authority. Generate/refresh before the first UI read so
// the very first pass cannot render an empty chest while waiting for the serverEvent round trip. Remote clients still
// join through the authoritative session/snapshot path below.
if (isServer) then {[_patient] call ACME_fnc_chestSealGenHoles;};
private _cached = _patient getVariable ["ACME_CS_netSnapshot", []];
if (count _cached >= 5) then { [_patient, _cached, true] call ACME_fnc_chestSealSyncUI; };
["ACME_CS_session", [_patient, _viewer, "join"]] call CBA_fnc_serverEvent;
