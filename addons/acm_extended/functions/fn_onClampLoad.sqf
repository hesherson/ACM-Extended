private _display = findDisplay 86200;
if (isNull _display) exitWith {};

// idempotent: it runs once per dialog instance. it is called from the config onload and from the watchdog pfhs, so
// the initialization happens even if the engine never fires the config onload in this environment.
if ((uiNamespace getVariable ["ACME_RollerClamp_InitDisplay", displayNull]) isEqualTo _display) exitWith {};
uiNamespace setVariable ["ACME_RollerClamp_InitDisplay", _display];

uiNamespace setVariable ["ACME_RollerClamp_DLG", _display];
uiNamespace setVariable ["ACME_RollerClamp_Dragging", false];
uiNamespace setVariable ["ACME_RollerClamp_ReleaseOnUp", false];
uiNamespace setVariable ["ACME_RollerClamp_NextCommit", 0];
uiNamespace setVariable ["ACME_RollerClamp_Edit", []];
uiNamespace setVariable ["ACME_RollerClamp_Session", [_display,ACE_player,0,0]];
uiNamespace setVariable ["ACME_RollerClamp_Track", []];

// Vision is owned by the clamp runtime, not by one-shot dialog redraws.
// Arma can transiently report normal vision during the first frames of a dialog even when NV is already active.
// Re-check every frame briefly, then fall back to a low-rate local refresh while the clamp remains open.
uiNamespace setVariable ["ACME_RollerClamp_VisionSettleUntil", diag_tickTime + 0.25];
uiNamespace setVariable ["ACME_RollerClamp_NextVisionTick", 0];

// the panel layout. every control is anchored to the backdrop panel, so the title, the rate strip and the button
// row always line up with the HUD overlay.
private _uiW = safeZoneW min (safeZoneH * 1.7777778);
private _uiX = safeZoneX + ((safeZoneW - _uiW) / 2);
private _centerX = _uiX + (_uiW / 2);

private _panelW = _uiW * 0.58;
private _panelH = safeZoneH * 0.84;
private _panelX = _centerX - (_panelW / 2);
private _panelY = safeZoneY + (safeZoneH * 0.07);
private _pad = safeZoneH * 0.012;

private _titleH = safeZoneH / 24;
private _btnH = safeZoneH / 24;
private _stripH = safeZoneH / 22;

private _btnY = _panelY + _panelH - _btnH - _pad;  // the button row, inside the panel bottom.
private _stripY = _btnY - _stripH - _pad;  // the rate strip, directly above the buttons.
private _titleY = _panelY + _pad;

private _ctrlBackdrop = _display displayCtrl 86210;
if (!isNull _ctrlBackdrop) then {
    _ctrlBackdrop ctrlSetPosition [_panelX, _panelY, _panelW, _panelH];
    _ctrlBackdrop ctrlCommit 0;
};

private _ctrlTitle = _display displayCtrl 86205;
if (!isNull _ctrlTitle) then {
    _ctrlTitle ctrlSetPosition [_panelX, _titleY, _panelW, _titleH];
    _ctrlTitle ctrlCommit 0;
};

// the rate strip is exactly as wide as the backdrop, so it is flush with the overlay.
private _ctrlRate = _display displayCtrl 86206;
if (!isNull _ctrlRate) then {
    _ctrlRate ctrlSetPosition [_panelX, _stripY, _panelW, _stripH];
    _ctrlRate ctrlCommit 0;
};

// the button row: three equal buttons, symmetric, inside the panel.
private _btnW = _panelW * 0.31;
private _btnGap = _panelW * 0.025;
private _btnX0 = _panelX + ((_panelW - ((_btnW * 3) + (_btnGap * 2))) / 2);

private _ctrlDrop = _display displayCtrl 86207;
private _ctrlToggle = _display displayCtrl 86208;
private _ctrlClose = _display displayCtrl 86209;

if (!isNull _ctrlDrop) then {
    _ctrlDrop ctrlSetPosition [_btnX0, _btnY, _btnW, _btnH];
    _ctrlDrop ctrlCommit 0;
};
if (!isNull _ctrlToggle) then {
    _ctrlToggle ctrlSetPosition [_btnX0 + _btnW + _btnGap, _btnY, _btnW, _btnH];
    _ctrlToggle ctrlCommit 0;
};
if (!isNull _ctrlClose) then {
    _ctrlClose ctrlSetPosition [_btnX0 + ((_btnW + _btnGap) * 2), _btnY, _btnW, _btnH];
    _ctrlClose ctrlCommit 0;
};

// the clamp artwork. the shipped paa is a 2048 by 2048 canvas with the 604 by 2048 art padded in, centerd and
// unscaled. the control is sized so the art comes out aspect-true at the desired height, and the track for the
// wheel is the art rect rather than the control rect.
// pixelw and pixelh are engine-supplied per-pixel ui unit sizes. they are exact for any resolution, aspect ratio
// from 16:9 through 32:9, stretch mode or ui scale. safezone-based math breaks on ultra-wide auto-stretch
// configs, where the engine reports safezones for the center region only.
private _unitFix = pixelW / pixelH;

private _bgContent = missionNamespace getVariable ["ACME_infusion_clampBGContent", [0.3525, 0.0, 0.2949, 1.0]];
_bgContent params ["_bcX", "_bcY", "_bcW", "_bcH"];

private _artTop = _titleY + _titleH + _pad;
private _artBottom = _stripY - _pad;
private _artH = (_artBottom - _artTop) max 0.1;
private _artW = _artH * (604 / 2048) * _unitFix;
private _artX = _centerX - (_artW / 2);

private _bgCtrlW = _artW / (_bcW max 0.01);
private _bgCtrlH = _artH / (_bcH max 0.01);
private _bgCtrlX = _centerX - (_bgCtrlW * (_bcX + (_bcW / 2)));
private _bgCtrlY = _artTop - (_bgCtrlH * _bcY);

private _ctrlBG = _display displayCtrl 86201;
if (!isNull _ctrlBG) then {
    // the paa, directly. this used to fall back to a .png if the .paa was missing, which was only ever useful while
    // the art was being converted. once the pngs are stripped from the addon the fallback cannot fire, and a fallback
    // that points at a file that is not shipped is worse than no fallback at all.
    _ctrlBG ctrlSetText "\acm_extended\ui\roller_clamp_bg.paa";
    _ctrlBG ctrlSetPosition [_bgCtrlX, _bgCtrlY, _bgCtrlW, _bgCtrlH];
    _ctrlBG ctrlSetFade 0;
    _ctrlBG ctrlShow true;
    _ctrlBG ctrlCommit 0;
};
uiNamespace setVariable ["ACME_RollerClamp_Track", [_artX, _artTop, _artW, _artH]];

private _ctrlWheel = _display displayCtrl 86202;
if (!isNull _ctrlWheel) then {
    _ctrlWheel ctrlSetText "\acm_extended\ui\roller_clamp_whl.paa";
    _ctrlWheel ctrlSetFade 0;
    _ctrlWheel ctrlShow true;
    _ctrlWheel ctrlCommit 0;
};

// grab handling, plunger-style.
// a quick click grabs the wheel, stickily, and clicking again releases it.
// a press and hold drags, and releasing the button drops the wheel.
// the final value is committed on release, and throttled commits run while moving.
private _ctrlDrag = _display displayCtrl 86203;
if (!isNull _ctrlDrag) then {
    // the hitbox: the clamp artwork plus some side margin, for easier grabbing.
    private _hitW = _artW * 1.6;
    _ctrlDrag ctrlSetPosition [_centerX - (_hitW / 2), _artTop, _hitW, _artH];
    _ctrlDrag ctrlSetFade 0;
    _ctrlDrag ctrlShow true;
    _ctrlDrag ctrlCommit 0;

    _ctrlDrag ctrlAddEventHandler ["MouseButtonDown", {
        params ["_ctrl", "_button"];
        if (_button != 0) exitWith {false};
        uiNamespace setVariable ["ACME_RollerClamp_DownTime", diag_tickTime];
        if (uiNamespace getVariable ["ACME_RollerClamp_Dragging", false]) then {
            uiNamespace setVariable ["ACME_RollerClamp_ReleaseOnUp", true];
        } else {
            uiNamespace setVariable ["ACME_RollerClamp_Dragging", true];
            uiNamespace setVariable ["ACME_RollerClamp_ReleaseOnUp", false];
        };
        true
    }];
    _ctrlDrag ctrlAddEventHandler ["MouseButtonUp", {
        params ["_ctrl", "_button"];
        if (_button != 0) exitWith {false};
        if !(uiNamespace getVariable ["ACME_RollerClamp_Dragging", false]) exitWith {false};
        private _down = uiNamespace getVariable ["ACME_RollerClamp_DownTime", -1];
        private _quickClick = (_down >= 0) && {(diag_tickTime - _down) < 0.25};
        if ((uiNamespace getVariable ["ACME_RollerClamp_ReleaseOnUp", false]) || {!_quickClick}) then {
            uiNamespace setVariable ["ACME_RollerClamp_Dragging", false];
            uiNamespace setVariable ["ACME_RollerClamp_ReleaseOnUp", false];
            [uiNamespace getVariable ["ACME_RollerClamp_Position", 1], false] call ACME_fnc_setClampPosition;
        };
        true
    }];
};

// the scroll wiring. a display-level MouseZChanged does not fire while the cursor is over a control, and the
// backdrop and overlay cover the whole panel, so the handler must sit on every control. fn_scrollclamp dedups per
// frame, so overlapping handlers can never double-step.
private _fnc_scrollEH = {
    _this call ACME_fnc_scrollClamp;
    true
};
{
    private _c = _display displayCtrl _x;
    if (!isNull _c) then {
        _c ctrlAddEventHandler ["MouseZChanged", _fnc_scrollEH];
    };
} forEach [86210, 86201, 86202, 86203, 86206, 86207, 86208, 86209];
_display displayAddEventHandler ["MouseZChanged", _fnc_scrollEH];



uiNamespace setVariable ["ACME_RollerClamp_SfxPct", -1];
uiNamespace setVariable ["ACME_RollerClamp_LoggedWheel", false];
uiNamespace setVariable ["ACME_RollerClamp_LoggedUpdate", false];

call ACME_fnc_updateClampDialog;
