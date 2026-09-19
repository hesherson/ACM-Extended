private _acmeNVArgs = _this;
_acmeNVArgs call {
/* B22 local Narc Box UI loop.
   Preserve the pre-B20 dialog layout. This loop only refreshes row stock text/highlights and applies plunger limits.
   No network publication and no helper-message surface. */
disableSerialization;
private _acmeCanvas = call ACME_fnc_uiCanvas;
_acmeCanvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
params ["_args", "_handle"];
_args params ["_d"];
if (isNull _d) exitWith {[_handle] call CBA_fnc_removePerFrameHandler;};
private _now = diag_tickTime;
private _view = uiNamespace getVariable ["ACME_SK_View", "syringe"];
private _body = _view == "body";
private _carousel = false; // B60 retired standalone carousel view.
private _infusion = !((_d getVariable ["ACME_SK_Return", []]) isEqualTo []);
private _stage = uiNamespace getVariable ["ACME_SK_WasteStage", ""];
// B62 explicit held-key repeat. A/D owns promotion while browsing. The expanded carousel cannot collapse while
// the pointer is anywhere inside the full-width lower retention zone, over the active syringe, or inside tag UI.
// Dedicated Edit Tag mode disables collapse completely until Done is pressed.
if (_body) then {
    private _tagEditMode = uiNamespace getVariable ["ACME_SK_TagEditMode", false];
    private _pendingInjection = uiNamespace getVariable ["ACME_SK_PendingInjection",[]];
    private _hasPendingInjection = _pendingInjection isEqualType [] && {count _pendingInjection >= 3};
    private _heldDir = uiNamespace getVariable ["ACME_SK_CarouselHeldDir", 0];
    private _repeatAt = uiNamespace getVariable ["ACME_SK_CarouselRepeatAt", 0];
    if (!_tagEditMode && {_heldDir != 0} && {_now >= _repeatAt} && {!(uiNamespace getVariable ["ACME_SK_CarouselBusy", false])}) then {
        uiNamespace setVariable ["ACME_SK_CarouselRepeatAt", _now + 0.09];
        [_heldDir] call ACME_fnc_skCarouselMove;
    };

    if (_tagEditMode) then {
        uiNamespace setVariable ["ACME_SK_CarouselExpanded", true];
        uiNamespace setVariable ["ACME_SK_CarouselCollapseAt", 0];
        // B68: once any real tag text exists, pulse Done green as a soft acknowledgement. Empty tags remain valid.
        private _done = _d displayCtrl 84472;
        if (!isNull _done) then {
            private _typed = false;
            {
                // Pulse only for actual entered content, not an accidental blank/space in a transparent editor.
                private _chars = toArray (ctrlText (_d displayCtrl _x));
                if ((_chars findIf {_x > 32}) >= 0) exitWith {_typed = true;};
            } forEach [84460,84461,84462];
            if (_typed) then {
                private _a = 0.42 + 0.36 * (0.5 + 0.5 * sin (_now * 260));
                _done ctrlSetBackgroundColor (["success", _a] call ACME_fnc_a11yColor);
            } else {
                _done ctrlSetBackgroundColor [0.05,0.05,0.05,0.65];
            };
        };
    } else {
        if (_hasPendingInjection) then {
            uiNamespace setVariable ["ACME_SK_CarouselExpanded",true];
            uiNamespace setVariable ["ACME_SK_CarouselCollapseAt",0];
        };
        if (!_hasPendingInjection && {uiNamespace getVariable ["ACME_SK_CarouselExpanded", false]}) then {
            private _focus = focusedCtrl _d;
            private _editingTag = !isNull _focus && {(ctrlIDC _focus) in [84460,84461,84462]};
            private _colorOpen = ctrlShown (_d displayCtrl 84471);
            private _hover = uiNamespace getVariable ["ACME_SK_CarouselHover", false];
            private _zoneHover = uiNamespace getVariable ["ACME_SK_CarouselZoneHover", false];
            if (_hover || {_zoneHover} || {_editingTag} || {_colorOpen} || {_heldDir != 0}) then {
                uiNamespace setVariable ["ACME_SK_CarouselCollapseAt", _now + 0.90];
            } else {
                private _collapseAt = uiNamespace getVariable ["ACME_SK_CarouselCollapseAt", 0];
                if (_collapseAt > 0 && {_now >= _collapseAt} && {!(uiNamespace getVariable ["ACME_SK_CarouselBusy", false])}) then {
                    uiNamespace setVariable ["ACME_SK_CarouselExpanded", false];
                    uiNamespace setVariable ["ACME_SK_CarouselCollapseAt", 0];
                    [0.12] call ACME_fnc_skDynamicLayout;
                    [0.12] call ACME_fnc_skCarouselRender;
                };
            };
        };
    };
} else {
    uiNamespace setVariable ["ACME_SK_CarouselHeldDir", 0];
    uiNamespace setVariable ["ACME_SK_CarouselRepeatAt", 0];
    // B66: keep the MAIN draw-page Select Syringe Tag control alive through ACM's first-frame native layout and
    // later syringe-size/flush refreshes. This also guarantees live tag text is repainted while preparing.
    if (_now >= (_d getVariable ["ACME_SK_NextPendingTag",0])) then {
        _d setVariable ["ACME_SK_NextPendingTag", _now + 0.10];
        call ACME_fnc_skPendingTagRender;
    };
};
if (_body) then {
    // Keep Push validation live while typing. The renderer only changes edit geometry/enable state when needed.
    call ACME_fnc_skBodyActionRender;
};
private _navPulse = ["info", 0.30 + 0.45 * (0.5 + 0.5 * sin (_now * 220))] call ACME_fnc_a11yColor;
(_d displayCtrl 84153) ctrlSetBackgroundColor _navPulse;
(_d displayCtrl 84157) ctrlSetBackgroundColor _navPulse;
// Native access changes can show Push again; retain the Narc Box's Save action and view.
(_d displayCtrl 84005) ctrlShow _infusion;
(_d displayCtrl 84005) ctrlEnable _infusion;
(_d displayCtrl 84004) ctrlShow (!_infusion && {!_body} && {!_carousel} && {_stage in ["compound","draw"]});
(_d displayCtrl 84006) ctrlShow false;

// Plain/native draw paths (not the compound PFH) stop at actual usable solution.
if (_stage == "") then {
    private _nativeList = _d displayCtrl 84006;
    private _sel = lbCurSel _nativeList;
    // Infusion prep can select the medication through ACME's visible row before ACM's hidden native listbox has
    // published its matching lbCurSel. The old guard therefore skipped the first physical-plunger clamp and let a
    // 10 mL syringe travel to 10 mL even when the bound vial only contained 4 mL. The authoritative medication
    // identity is ACM's draw-session variable; use the hidden list only as a fallback.
    private _med = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medication", ""];
    if (_med == "" && {_sel >= 0}) then {_med = _nativeList lbData _sel;};
    if (_med != "") then {
        private _holder = [ACE_player] call ACME_fnc_vialHolder;
        if (!isNull _holder) then {
            private _sizeMl = (ACM_circulation_SyringeDraw_Size max 0.1);
            private _hardMax = (["limit", _med, missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount",0], _d] call ACME_fnc_vialSession) min _sizeMl;
            _hardMax = _hardMax max 0;
            ACM_circulation_SyringeDraw_MaxDose = _hardMax;

            // Do not rely only on ACM reading MaxDose on its next frame. Clamp the actual plunger and mouse to the
            // remaining source volume here as well, so an exhausted vial is a physical hard stop even if native
            // selection logic briefly rewrites MaxDose. This covers infusion-prep draws and any plain native draw.
            private _drawnNow = (missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0]) max 0;
            if (_drawnNow > _hardMax + 0.0001 || {missionNamespace getVariable ["ACM_circulation_SyringeDraw_Moving", false]}) then {
                private _top = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitTop", -1];
                private _bottom = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_LimitBottom", -1];
                if (_top >= 0 && {_bottom >= 0}) then {
                    private _maxY = linearConversion [0, _sizeMl, _hardMax, _top, _bottom, true];
                    private _plunger = _d displayCtrl 84009;
                    private _visIdc = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_PlungerVisual", -1];
                    private _vis = _d displayCtrl _visIdc;
                    private _adjust = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Ctrl_PlungerAdjustment", 0];
                    if (_drawnNow > _hardMax + 0.0001) then {
                        ACM_circulation_SyringeDraw_DrawnAmount = _hardMax;
                        if (!isNull _plunger) then {
                            (ctrlPosition _plunger) params ["_px", "", "_pw", "_ph"];
                            _plunger ctrlSetPosition [_px, _maxY, _pw, _ph];
                            _plunger ctrlCommit 0;
                        };
                        if (!isNull _vis) then {
                            (ctrlPosition _vis) params ["_vx", "", "_vw", "_vh"];
                            _vis ctrlSetPosition [_vx, _maxY - _adjust, _vw, _vh];
                            _vis ctrlCommit 0;
                        };
                    };
                    if (missionNamespace getVariable ["ACM_circulation_SyringeDraw_Moving", false]) then {
                        private _res5 = (getResolution select 5) max 0.1;
                        getMousePosition params ["", "_my"];
                        private _maxMouse = _maxY + (0.026 * (0.55 / _res5));
                        if (_my > _maxMouse) then {setMousePosition [_uiX + _uiW / 2, _maxMouse];};
                        // B73 current-vial depletion endpoint. If native mouse rounding leaves <=0.01 mL in the vial
                        // while the hand is physically against its lower stop, finish the draw at the exact hard max.
                        if ((_hardMax - _drawnNow) <= 0.015 && {_my >= _maxMouse - (2 * pixelH)} && {!isNull _plunger}) then {
                            ACM_circulation_SyringeDraw_DrawnAmount = _hardMax;
                            (ctrlPosition _plunger) params ["_pxB73", "", "_pwB73", "_phB73"];
                            _plunger ctrlSetPosition [_pxB73, _maxY, _pwB73, _phB73];
                            _plunger ctrlCommit 0;
                            if (!isNull _vis) then {
                                (ctrlPosition _vis) params ["_vxB73", "", "_vwB73", "_vhB73"];
                                _vis ctrlSetPosition [_vxB73, _maxY - _adjust, _vwB73, _vhB73];
                                _vis ctrlCommit 0;
                            };
                        };
                        // B70 exact empty syringe endpoint. Native mouse/control geometry can leave 0.01 mL when the plunger is
                        // visually at the top. Snap only at the physical top, never in the middle of travel.
                        if (_drawnNow <= 0.015 && {!isNull _plunger}) then {
                            (ctrlPosition _plunger) params ["_px0", "", "_pw0", "_ph0"];
                            private _topMouse = _top + (_ph0 / 2);
                            if (_my <= _topMouse + (2 * pixelH)) then {
                                ACM_circulation_SyringeDraw_DrawnAmount = 0;
                                _plunger ctrlSetPosition [_px0, _top, _pw0, _ph0];
                                _plunger ctrlCommit 0;
                                if (!isNull _vis) then {
                                    (ctrlPosition _vis) params ["_vx0", "", "_vw0", "_vh0"];
                                    _vis ctrlSetPosition [_vx0, _top - _adjust, _vw0, _vh0];
                                    _vis ctrlCommit 0;
                                };
                            };
                        };
                    };
                };
            };
        };
    };
};

// Inventory can change while the box stays open. B41 delegates stock membership/order/identity to the same
// authoritative row builder used by the visible overlay. Do not independently compare config-order medication
// keys against the alphabetically sorted hidden list: that would make an unchanged list appear stale every 0.5 s
// and repeatedly repaint/reset native selection state.
if (!_infusion && {_now >= (_d getVariable ["ACME_SK_NextStockRefresh", 0])}) then {
    _d setVariable ["ACME_SK_NextStockRefresh", _now + 0.5];
    if !(uiNamespace getVariable ["ACME_SK_WasteMoving", false]) then {
        [_d] call ACME_fnc_skMedicationSync;
    };
};

// B25: no custom return resistance. ACM owns normal plunger feel in the plain/native path.

if (_now >= (_d getVariable ["ACME_SK_NextRefresh", 0])) then {
    _d setVariable ["ACME_SK_NextRefresh", _now + 0.2];
    call ACME_fnc_skListRefresh;
};
// B48: stock text lives inside the native medication row. Refresh it often enough to follow the plunger
// without rebuilding the list or disturbing selection.
if (_now >= (_d getVariable ["ACME_SK_NextMedStock", 0])) then {
    _d setVariable ["ACME_SK_NextMedStock", _now + 0.10];
    [_d] call ACME_fnc_skMedicationStockRefresh;
};
if (_body && {_now >= (_d getVariable ["ACME_SK_NextBody", 0])}) then {
    call ACME_fnc_skBuildHotspots;
};

private _alpha = 0.22 + 0.26 * (0.5 + 0.5 * sin (_now * 240));
{
    _x params ["_kind", "_nativeID", "_data", "_value", "_back", "_visible", ["_text1", controlNull], ["_text2", controlNull], ["_stock", controlNull], ["_countText", controlNull]];
    if (!_visible) then {continue};
    private _selected = false;
    switch (_kind) do {
        case "size": {_selected = _value == (uiNamespace getVariable ["ACME_SK_CurSize", 10]) && {!(_stage in ["waste", "draw"])};};
        case "medication": {
            private _list = _d displayCtrl _nativeID;
            _selected = (lbCurSel _list) >= 0 && {(_list lbData (lbCurSel _list)) == _data};
        };
        case "flush": {_selected = (uiNamespace getVariable ["ACME_SK_WasteFlushClass", ""]) == _data && {_stage in ["waste", "draw"]};};
    };
    _selected = _selected && {_back getVariable ["ACME_SK_Available", false]};

    // The selected medication's current-vial number updates at the same 25 Hz UI rate as the plunger. Other rows
    // refresh at 5 Hz through skListRefresh.
    if (_kind == "medication" && {_selected} && {!isNull _stock}) then {
        private _reserved = 0;
        if (_stage in ["compound","draw"]) then {
            {if ((_x param [0, ""]) == _data) then {_reserved = _reserved + (_x param [1, 0]);};} forEach (uiNamespace getVariable ["ACME_SK_CompoundComponents", []]);
            _reserved = _reserved + (((uiNamespace getVariable ["ACME_SK_WasteFill", 0]) - (uiNamespace getVariable ["ACME_SK_WasteFloorMl", 0])) max 0);
        } else {
            if (_stage == "") then {_reserved = missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0];};
        };
        private _holder = [ACE_player] call ACME_fnc_vialHolder;
        if (!isNull _holder) then {
            private _pv = ["preview", _data, _reserved, _d] call ACME_fnc_vialSession;
            _pv params ["_curMl", "_vials", "_total", ""];
            private _cnt = str (_vials max 0);
            while {count _cnt < 2} do {_cnt = "0" + _cnt;};
            _stock ctrlSetText format ["%1 mL", _curMl toFixed 2];
            if (!isNull _countText) then {_countText ctrlSetText ("x" + _cnt);};
            private _font = safeZoneH / 44 * 0.68;
            {
                if (!isNull _x) then {
                    _x ctrlSetFontHeight _font;
                    private _w = (ctrlPosition _x) select 2;
                    private _measured = ctrlTextWidth _x;
                    if (_measured > _w) then {_x ctrlSetFontHeight (_font * (_w / _measured));};
                    _x ctrlSetTextColor (if (_total > 0.000001 || {_reserved > 0.000001}) then {[0.86,0.90,0.93,1]} else {[0.50,0.50,0.50,1]});
                };
            } forEach [_stock, _countText];
        };
    };

    private _flash = _back getVariable ["ACME_SK_FlashAt", -1];
    private _elapsed = _now - _flash;
    private _red = _flash >= 0 && {_elapsed < 0.09 || {_elapsed >= 0.18 && {_elapsed < 0.27}}};
    // B54: darker resting rows so the section reads as one dark panel.
    _back ctrlSetBackgroundColor (if (_red) then {[1,0.05,0.05,0.85]} else {if (_selected) then {[0.12,0.75,0.25,_alpha]} else {[0,0,0,0.30]}});

    // Small selected-row indent only; it does not resize or move the list/group itself.
    private _wasVisual = _back getVariable ["ACME_SK_SelectedVisual", false];
    if (_selected isNotEqualTo _wasVisual) then {
        _back setVariable ["ACME_SK_SelectedVisual", _selected];
        {
            if (!isNull _x) then {
                private _bp = +(_x getVariable ["ACME_SK_BasePos", ctrlPosition _x]);
                private _ind = _x getVariable ["ACME_SK_SelectedIndent", 0];
                if (_selected) then {
                    _bp set [0, (_bp select 0) + _ind];
                    _bp set [2, ((_bp select 2) - _ind) max (pixelW * 20)];
                };
                _x ctrlSetPosition _bp;
                _x ctrlCommit 0;
            };
        } forEach [_text1, _text2];
    };
    if (_flash >= 0 && {_elapsed >= 0.36}) then {_back setVariable ["ACME_SK_FlashAt", -1];};
} forEach (_d getVariable ["ACME_SK_PulseRows", []]);

};
private _acmeNVD = (_acmeNVArgs select 0) param [0,displayNull];
[_acmeNVD, [], "ACME_SK_Shade"] call ACME_fnc_darknessShade;
[_acmeNVD] call ACME_fnc_minigameVisionTick;
