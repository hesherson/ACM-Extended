private _acmeCanvas = call ACME_fnc_uiCanvas;
_acmeCanvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
// the onload for the syringe kit dialog, idd 86300. it mirrors the approach of the roller-clamp dialog: a minimal
// set of config controls, all positioned here from safezone math, lists populated and wired at runtime, and a
// per-frame mover started for the plunger drag. it is idempotent.
private _display = findDisplay 86300;
if (isNull _display) exitWith {};
if ((uiNamespace getVariable ["ACME_SK_InitDisplay", displayNull]) isEqualTo _display) exitWith {};
uiNamespace setVariable ["ACME_SK_InitDisplay", _display];
uiNamespace setVariable ["ACME_SK_DLG", _display];

// the shared ambient-light and flashlight system, the same one every other procedure screen uses. the syringe
// kit is a hands-on procedure and it was the only one of them left lit in the dark.
// see fn_darknessshade for how the beam works, and fn_installlightkey for the ctrl+win handoff to ACE.
[_display] call ACME_fnc_installLightKey;

// the panel.
private _panelW = _uiW * 0.46;
private _panelH = safeZoneH * 0.80;
private _panelX = _uiX + ((_uiW - _panelW) / 2);
private _panelY = safeZoneY + ((safeZoneH - _panelH) / 2);
private _pad = _panelH * 0.03;

(_display displayCtrl 86310) ctrlSetPosition [_panelX, _panelY, _panelW, _panelH];
(_display displayCtrl 86310) ctrlCommit 0;

// the title.
(_display displayCtrl 86311) ctrlSetPosition [_panelX, _panelY + _pad, _panelW, _panelH * 0.07];
(_display displayCtrl 86311) ctrlCommit 0;

// the left column: two stacked lists, sizes on top and sources below.
private _colX = _panelX + _pad;
private _colW = _panelW * 0.34;
private _lblH = _panelH * 0.05;
private _listTop = _panelY + _panelH * 0.16;
private _sizesH = _panelH * 0.30;
private _srcTop = _listTop + _sizesH + _panelH * 0.10;
private _srcH  = _panelH * 0.20;

(_display displayCtrl 86319) ctrlSetPosition [_colX, _listTop - _lblH, _colW, _lblH];  // the sizes label.
(_display displayCtrl 86319) ctrlCommit 0;
(_display displayCtrl 86317) ctrlSetPosition [_colX, _listTop, _colW, _sizesH];  // the sizes list.
(_display displayCtrl 86317) ctrlCommit 0;
(_display displayCtrl 86320) ctrlSetPosition [_colX, _srcTop - _lblH, _colW, _lblH];  // the sources label.
(_display displayCtrl 86320) ctrlCommit 0;
(_display displayCtrl 86318) ctrlSetPosition [_colX, _srcTop, _colW, _srcH];  // the sources list.
(_display displayCtrl 86318) ctrlCommit 0;

// the syringe, using the real in-game flush texture, plus the barrel geometry.
// the flush icon is a vertical syringe: the needle at the bottom, the plunger and thumb-rest at the top, and
// graduations 1 to 10 down the barrel. we show it at native, square, aspect and derive the fillable barrel rect
// from its measured internals, so the blue fluid column and the moving plunger line sit inside the glass. measured
// on the 256 by 256 icon, the barrel glass is x 0.449 to 0.539 and the fillable band is y 0.17 to 0.60.
private _synH = _panelH * 0.50;
private _synW = _synH;  // a w equal to h in coord units renders pixel-square on any aspect, because _uiW over safeZoneH is about the screen aspect.
private _synX = _panelX + (_panelW * 0.66) - (_synW / 2);
private _synY = _panelY + _panelH * 0.15;

private _syn = _display displayCtrl 86326;
_syn ctrlSetPosition [_synX, _synY, _synW, _synH];
_syn ctrlCommit 0;

// the fillable inner-barrel rect. the top is a full plunger, about 1 ml, and the bottom is about 10 ml, just above
// the flanges.
private _barrelX    = _synX + (_synW * 0.452);
private _barrelW    = _synW * 0.085;
private _barrelTopY = _synY + (_synH * 0.17);
private _barrelH    = _synH * (0.60 - 0.17);
uiNamespace setVariable ["ACME_SK_Geo", [_barrelX, _barrelTopY, _barrelW, _barrelH]];

// retire the old procedural barrel backdrop and plunger rod, because the real texture supplies both.
(_display displayCtrl 86312) ctrlShow false;  // the old glass-barrel backdrop.
(_display displayCtrl 86315) ctrlShow false;  // the old plunger rod.

// the fluid and the plunger are positioned every frame by the renderer, and the overlay is the fixed grab band.
private _overlay = _display displayCtrl 86316;
_overlay ctrlSetPosition [_barrelX - (_barrelW * 0.6), _barrelTopY, _barrelW * 2.2, _barrelH];
_overlay ctrlCommit 0;

// the volume readout, above the syringe.
(_display displayCtrl 86321) ctrlSetPosition [_synX + (_synW * 0.20), _synY - (_panelH * 0.02), _synW * 0.6, _panelH * 0.07];
(_display displayCtrl 86321) ctrlCommit 0;

// the status line and the buttons, at the bottom.
private _btnH = _panelH * 0.08;
private _btnY = _panelY + _panelH - _btnH - _pad;
private _infoY = _btnY - (_panelH * 0.07) - (_panelH * 0.01);
(_display displayCtrl 86322) ctrlSetPosition [_panelX + _pad, _infoY, _panelW - (2 * _pad), _panelH * 0.07];
(_display displayCtrl 86322) ctrlCommit 0;

private _btnW = (_panelW - (2 * _pad) - (2 * (_panelW * 0.02))) / 3;
private _bx0 = _panelX + _pad;
private _gap = _panelW * 0.02;
(_display displayCtrl 86323) ctrlSetPosition [_bx0, _btnY, _btnW, _btnH];  // waste.
(_display displayCtrl 86323) ctrlCommit 0;
(_display displayCtrl 86324) ctrlSetPosition [_bx0 + _btnW + _gap, _btnY, _btnW, _btnH];  // draw.
(_display displayCtrl 86324) ctrlCommit 0;
(_display displayCtrl 86325) ctrlSetPosition [_bx0 + (2 * (_btnW + _gap)), _btnY, _btnW, _btnH];  // close.
(_display displayCtrl 86325) ctrlCommit 0;

// populate the lists.
private _sizes = _display displayCtrl 86317;
lbClear _sizes;
{
    private _i = _sizes lbAdd format ["%1 mL", _x];
    _sizes lbSetValue [_i, _x];
} forEach [1, 3, 5, 10];

private _sources = _display displayCtrl 86318;
lbClear _sources;
{
    _x params ["_label", "_key"];
    private _i = _sources lbAdd _label;
    _sources lbSetData [_i, _key];
} forEach [["Saline Flush", "Saline"], ["Epinephrine 1:10,000 (0.1 mg/mL)", "EpinephrineCardiac"]];

// wire the events.
_sizes ctrlAddEventHandler ["LBSelChanged", {_this call ACME_fnc_syringeKitSize}];
_sources ctrlAddEventHandler ["LBSelChanged", {_this call ACME_fnc_syringeKitSource}];
_overlay ctrlAddEventHandler ["ButtonClick", {call ACME_fnc_syringeKitGrab}];
(_display displayCtrl 86323) ctrlAddEventHandler ["ButtonClick", {call ACME_fnc_syringeKitWaste}];
(_display displayCtrl 86324) ctrlAddEventHandler ["ButtonClick", {call ACME_fnc_syringeKitDraw}];
(_display displayCtrl 86325) ctrlAddEventHandler ["ButtonClick", {closeDialog 0}];

// the initial state: default to a 10 ml barrel, empty.
uiNamespace setVariable ["ACME_SK_Size", 10];
uiNamespace setVariable ["ACME_SK_Vol", 0];
uiNamespace setVariable ["ACME_SK_SalineBase", -1];
uiNamespace setVariable ["ACME_SK_EpiMl", 0];
uiNamespace setVariable ["ACME_SK_Med", ""];
uiNamespace setVariable ["ACME_SK_Source", ""];
uiNamespace setVariable ["ACME_SK_Grab", false];

// the programmatic list selections below will fire LBSelChanged. suppress the size and source handlers for the
// setup window, so their resets cannot fight what we set here, including deferred events that land a frame or two
// later. we set all the state explicitly, so the handlers are not needed during setup.
uiNamespace setVariable ["ACME_SK_Suppress", true];
_sizes lbSetCurSel 3;  // "10 mL".

// when it is opened from the "Saline Flush" self-action, auto-load a full 10 ml flush, so the medic lands straight
// on a full plunger, ready to waste. the menu statement sets the flag before the open.
private _autoLoaded = false;
if (uiNamespace getVariable ["ACME_SK_AutoSaline", false]) then {
    uiNamespace setVariable ["ACME_SK_AutoSaline", false];
    if (([ACE_player, "ACM_SalineFlush_10"] call ACME_fnc_itemCount) >= 1) then {
        // the full saline-flush state, set explicitly. it mirrors the saline case of fn_syringekitsource.
        uiNamespace setVariable ["ACME_SK_Size", 10];
        uiNamespace setVariable ["ACME_SK_Source", "Saline"];
        uiNamespace setVariable ["ACME_SK_Vol", 10];  // full, so the plunger is all the way up.
        uiNamespace setVariable ["ACME_SK_SalineBase", -1];  // not yet wasted or locked.
        uiNamespace setVariable ["ACME_SK_EpiMl", 0];
        uiNamespace setVariable ["ACME_SK_Med", ""];
        uiNamespace setVariable ["ACME_SK_Grab", false];
        _sources lbSetCurSel 0;  // reflect "Saline Flush" in the list. the handler is suppressed.
        _autoLoaded = true;
        ["10 mL flush loaded. Push plunger DOWN to your volume, then Waste."] call ACME_fnc_syringeKitInfo;
    } else {
        _sources lbSetCurSel -1;
        ["No prefilled saline flush (ACM_SalineFlush_10) in your kit. Pick a source on the left."] call ACME_fnc_syringeKitInfo;
    };
};
if (!_autoLoaded) then {
    _sources lbSetCurSel -1;
    ["Pick size -> Saline Flush -> drag plunger -> Waste to volume -> add Epi."] call ACME_fnc_syringeKitInfo;
};

call ACME_fnc_syringeKitRender;

// release the handler suppression once any deferred LBSelChanged from the setcursel calls above has drained, which
// takes a couple of frames. after this, real user clicks on the lists behave normally.
[{ uiNamespace setVariable ["ACME_SK_Suppress", false]; }, [], 0.15] call CBA_fnc_waitAndExecute;

// the per-frame plunger mover.
private _h = [ACME_fnc_syringeKitTick, 0, []] call CBA_fnc_addPerFrameHandler;
uiNamespace setVariable ["ACME_SK_PFH", _h];
