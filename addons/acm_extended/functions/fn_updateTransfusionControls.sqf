private _display = findDisplay 86000;
if (isNull _display) exitWith {};

// while the roller clamp dialog, 86200, is open on top of the transfusion menu, do not rebuild the lists of the
// menu. churning the infusions sub-list, with lbclear, lbadd and lbSetCurSel, every frame behind the dialog was
// disrupting the live selection of the clamp, so "Adjust Infusion" could not change anything. the clamp dialog
// runs off its own stored context, ACME_RollerClamp_Context, and the menu refreshes the instant the dialog
// closes.
if (!isNull (findDisplay 86200)) exitWith {};
// the same applies to the narc box and syringe-draw dialog, 84000. when prep infusion opens it on top of the
// menu, churning the layout of the menu behind it, and racing ACM's control teardown and rebuild, is what left
// the menu scrambled after spike, prep and give. the menu refreshes cleanly the instant the draw dialog
// closes.
if (!isNull (findDisplay 84000)) exitWith {};

// keep ACME_YLines honest, under the discard-only teardown model. a y line persists until the medic explicitly
// discards it, because ACME_fnc_discardYTubing removes the key, whatever happens to the bags on it. pulling
// bags leaves empty markers. if any path nonetheless strips a keyed site bare, from a race, an ACM-side cleanup
// or a legacy flow, this self-heals it by recreating the empty blood bag and empty saline bag pair, so the line
// stays visible in the transfusion list and structurally intact until it is discarded. keys are never
// auto-dropped now. that auto-drop was the pre-discard rule, and it was how a fully pulled y could vanish from
// the menu.
private _yTarget = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
if (!isNull _yTarget) then {
    private _yl = _yTarget getVariable ["ACME_YLines", []];
    if (count _yl > 0) then {
        private _ivBags = _yTarget getVariable ["ACM_circulation_IV_Bags", createHashMap];
        private _healed = false;
        {
            (_x splitString "#") params [["_bp", ""], ["_ivStr", "true"], ["_siteStr", "-1"]];
            private _site = parseNumber _siteStr;
            private _ivB = _ivStr == "true";
            private _arr = _ivBags getOrDefault [_bp, []];
            private _held = (_arr findIf {
                (
                    ((_x param [0, ""]) in ["ACME_SalineY", "ACME_EmptySaline", "ACME_Empty", "Saline"])
                    || {((_x param [0, ""]) in ["Blood", "FreshBlood"]) && {(_x param [1, 0]) > 0.01}}
                )
                && {(_x param [3, -1]) isEqualTo _site}
                && {(str (_x param [4, true])) == _ivStr}
            }) > -1;
            if (!_held) then {
                _arr pushBack ["ACME_Empty", 0, 0, _site, _ivB, -1, 1000, -1];
                _arr pushBack ["ACME_EmptySaline", 0, 0, _site, _ivB, -1, 1000, -1];
                _ivBags set [_bp, _arr];
                _healed = true;
            };
        } forEach _yl;
        if (_healed) then {
            [_yTarget, _ivBags] call ACME_fnc_ivBagsCommit;
            if (!isNil "ACM_circulation_fnc_TransfusionMenu_UpdateBagList") then { [false] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList; };
        };
    };
};

// compatible-saline cue, shown only during the mid-y-line "Select Flush Saline" step, where a blood unit is
// pending its pairing. every valid ACM saline can be the clamped limb, so each saline row in the available-bags
// list is tinted a soft green whose opacity pulses, as an at-a-glance indicator of which bag to pick to flush
// or pair. outside that step, with nothing pending, the rows keep their default color. it is re-applied every
// pass, so it holds through rebuilds.
private _rl = _display displayCtrl 86005;
if (!isNull _rl && {(missionNamespace getVariable ["ACME_yPending", ""]) != ""}) then {
    private _p = 0.5 + (0.5 * sin (360 * ((diag_tickTime * 1.1) % 1)));  // about 1.1 hz, matching the flush line pulse.
    private _sCol = [0.45, 0.95, 0.55, 0.4 + (0.45 * _p)];
    for "_r" from 0 to ((lbSize _rl) - 1) do {
        ((_rl lbData _r) splitString "|") params [["_rClass", ""], ["_rAction", ""]];
        if (_rClass != "" && {[_rClass, _rAction] call ACME_fnc_isSalineItem}) then {
            _rl lbSetColor [_r, _sCol];
        };
    };
};

private _ctrlInject = _display displayCtrl 86120;
private _ctrlInfuse = _display displayCtrl 86147;
private _ctrlPrep = _display displayCtrl 86121;
private _ctrlGivePrep = _display displayCtrl 86122;
private _ctrlPreparedList = _display displayCtrl 86127;
private _ctrlActiveInfTitle = _display displayCtrl 86128;
private _ctrlActiveInfList = _display displayCtrl 86129;
private _ctrlPreparedTitle = _display displayCtrl 86130;
private _ctrlDrop = _display displayCtrl 86123;
private _ctrlRateDown = _display displayCtrl 86124;
private _ctrlRateUp = _display displayCtrl 86125;
private _ctrlRateText = _display displayCtrl 86126;
private _ctrlNativeStop = _display displayCtrl 86006;
private _ctrlAdjust = _display displayCtrl 86131;
private _ctrlInfMove = _display displayCtrl 86132;
private _ctrlInfRemove = _display displayCtrl 86133;
private _ctrlInfPressure = _display displayCtrl 86149;
private _ctrlLeftList = _display displayCtrl 86004;
private _ctrlRightList = _display displayCtrl 86005;
private _ctrlMove = _display displayCtrl 86007;
private _ctrlRemove = _display displayCtrl 86008;
private _ctrlPullBag = _display displayCtrl 86146;

call ACME_fnc_updateTransfusionAccessHotspots;

// the master gate for every bag and transfusion action button. an action that operates on a hung bag, which
// covers pull bag, hang bag, infuse, spike and add, y tubing, flush, prep, give, inject, the native move and
// remove, and iv sets, is only ever live when an actual bag row is selected in the transfusion list, 86004.
// with no bag row selected, every one of those buttons grays out, so nothing can fire against an empty or
// ambiguous selection. the infusion-specific controls, adjust infusion and the move and remove of the
// infusions list, are deliberately not gated on this, because they belong to the infusions sub-list and have
// their own selection.
private _ctrlTransfusionList = _display displayCtrl 86004;
private _bagRowSelected = (!isNull _ctrlTransfusionList) && {(lbCurSel _ctrlTransfusionList) >= 0};

private _activeContext = [] call ACME_fnc_getSelectedActiveBagContext;
private _canActive = false;
private _hasInfusion = false;
private _rateText = "Select medicated saline bag";

if ((uiNamespace getVariable ["ACME_infusion_LayoutDisplay", displayNull]) != _display) then {
    // a new menu instance. the entire custom layout, the spike, prep, give, prepared, infuse, flush and hang
    // positions, is computed from ACM's native move, remove, stop and list positions, captured here once.
    // the bug was that on a programmatic reopen, after spike, prep and give, the 0.05 s pfh could catch the dialog
    // mid-build, before ACM had created and positioned those native controls. we then cached empty base positions,
    // as [], so downstream the _moveBase isNotEqualTo [] test failed and the whole layout collapsed into scattered
    // fallback spots. that is the report that the menu gets completely messed up until you reopen it, and a manual
    // reopen caught a settled menu, so it worked.
    // the fix is not to lock in the bases until the native controls actually exist and are positioned. until then
    // layoutdisplay keeps pointing at the old display and we bail out below and retry next tick. it converges
    // within a frame or two once ACM finishes building the dialog.
    private _movePos = if (isNull _ctrlMove) then {[]} else {ctrlPosition _ctrlMove};
    private _ctrlsReady = !isNull _ctrlMove && {!isNull _ctrlRemove} && {!isNull _ctrlRightList}
        && {!isNull _ctrlNativeStop} && {!isNull _ctrlLeftList}
        && {(_movePos isNotEqualTo []) && {(_movePos select 2) > 0}};  // a real width means it is actually laid out.

    if (_ctrlsReady) then {
        uiNamespace setVariable ["ACME_infusion_LayoutDisplay", _display];
        uiNamespace setVariable ["ACME_infusion_BaseLeftListPos", ctrlPosition _ctrlLeftList];
        uiNamespace setVariable ["ACME_infusion_BaseRightListPos", ctrlPosition _ctrlRightList];
        uiNamespace setVariable ["ACME_infusion_BaseMovePos", ctrlPosition _ctrlMove];
        uiNamespace setVariable ["ACME_infusion_BaseRemovePos", ctrlPosition _ctrlRemove];
        uiNamespace setVariable ["ACME_infusion_BaseStopPos", ctrlPosition _ctrlNativeStop];
        uiNamespace setVariable ["ACME_infusion_PreparedListSignature", ""];
        uiNamespace setVariable ["ACME_infusion_ActiveInfusionListSignature", ""];

        // swap ACM's native remove button for our pull bag button. the native one rounds the returned volume and cannot
        // be safely reconfigured in config without collapsing the layout. the native position was just captured into
        // baseremovepos, and the layout anchors off that captured value, so hiding the live control here is safe.
        if (!isNull _ctrlRemove) then {
            private _rp = ctrlPosition _ctrlRemove;
            _ctrlRemove ctrlShow false;
            _ctrlRemove ctrlEnable false;
            if (!isNull _ctrlPullBag) then {
                _ctrlPullBag ctrlSetPosition _rp;
                _ctrlPullBag ctrlCommit 0;
                _ctrlPullBag ctrlShow true;
                _ctrlPullBag ctrlEnable true;
            };
        };

        if (!isNull _ctrlLeftList) then {
            _ctrlLeftList ctrlAddEventHandler ["LBSelChanged", {
                params ["_ctrl", "_index"];
                if (_index >= 0 && {!((ctrlParent _ctrl) getVariable ["ACME_txRebuilding", false])}) then {
                    missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionSelectionIndex", -1];
                    missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex", -1];
                    private _inf = ctrlParent _ctrl displayCtrl 86129;
                    if (!isNull _inf) then {_inf lbSetCurSel -1;};
                    // remember the stable true index of the selected bag for pull bag. the infusions list clears the live selection
                    // of this list when it rebuilds, so lbCurSel is unreliable at click time and this is not. the -1 clears do not
                    // reach here, because they fail the _index >= 0 guard above.
                    private _sel = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags", []];
                    private _value = _ctrl lbValue _index;
                    missionNamespace setVariable ["ACME_pull_selTrueIndex", if (_value >= 0 && {_value < count _sel}) then {(_sel select _value) param [8, -1]} else {-1}];
                };
            }];
        };

        // the selection handler for the infusions list, 86129. without this the infusion selection was never recorded,
        // so it was silently dropped on every list rebuild, because the re-select pass below runs off these vars. that
        // grayed move and remove and made a dirty epi impossible to act on after any refresh or sub-menu round trip. it
        // records the stable true index of the selected bag, which survives ACM reordering the selection array, plus
        // its selection index, and points pull bag at the same bag, so move, remove and pull all target it.
        if (!isNull _ctrlActiveInfList) then {
            _ctrlActiveInfList ctrlAddEventHandler ["LBSelChanged", {
                params ["_ctrl", "_index"];
                if (_index >= 0 && {!((ctrlParent _ctrl) getVariable ["ACME_txRebuilding", false])}) then {
                    private _val = _ctrl lbValue _index;
                    private _sel = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags", []];
                    private _ti = if (_val >= 0 && {_val < count _sel}) then {(_sel select _val) param [8, -1]} else {-1};
                    missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionSelectionIndex", _val];
                    missionNamespace setVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex", _ti];
                    missionNamespace setVariable ["ACME_pull_selTrueIndex", _ti];
                };
            }];
        };
    };
};

// Remember the list the medic is using. Moving to its action buttons keeps that pane.
if !(_display getVariable ["ACME_txPaneHooks", false]) then {
    _display setVariable ["ACME_txPaneHooks", true];
    _display setVariable ["ACME_txActivePane", "transfusion"];
    {
        _x params ["_idc", "_pane"];
        private _c = _display displayCtrl _idc;
        if (!isNull _c) then {
            _c setVariable ["ACME_txPane", _pane];
            {
                _c ctrlAddEventHandler [_x, {
                    params ["_c"];
                    (ctrlParent _c) setVariable ["ACME_txActivePane", _c getVariable ["ACME_txPane", "inventory"]];
                }];
            } forEach ["MouseEnter", "MouseButtonDown", "SetFocus"];
        };
    } forEach [[86004,"transfusion"],[86129,"infusion"],[86005,"inventory"],[86145,"prepared"],[86127,"prepared"]];
};

// if this is still a not-yet-captured new display, because the native controls were not ready above, skip the
// whole layout this frame at function scope. laying out against the now-invalid bases of the previous display
// is exactly what scrambled the menu. retry next tick, once ACM has finished building the reopened dialog.
if ((uiNamespace getVariable ["ACME_infusion_LayoutDisplay", displayNull]) != _display) exitWith {};

// a defensive pre-hide of the volatile adjust infusion controls: the drop set, the rate, the adjust button, the
// infusions sub-list and its move and remove. the active-infusion block below re-shows and repositions
// whichever apply in the same frame, so there is no flicker in the normal case. but if that block ever aborts
// on a bad or edge-case bag entry, these would otherwise be left visible at their raw config positions, which
// is the report that the menu scrambles after give infusion, titrate and done. pre-hiding degrades the worst
// case to a missing infusion sub-list, which a reopen still recovers, instead of a scrambled, unusable menu.
{
    if (!isNull _x) then { _x ctrlShow false; };
} forEach [_ctrlDrop, _ctrlRateDown, _ctrlRateUp, _ctrlRateText, _ctrlActiveInfTitle, _ctrlAdjust];

private _leftBase = +(uiNamespace getVariable ["ACME_infusion_BaseLeftListPos", []]);
private _rightBase = +(uiNamespace getVariable ["ACME_infusion_BaseRightListPos", []]);
private _moveBase = +(uiNamespace getVariable ["ACME_infusion_BaseMovePos", []]);
private _removeBase = +(uiNamespace getVariable ["ACME_infusion_BaseRemovePos", []]);
private _stopBase = +(uiNamespace getVariable ["ACME_infusion_BaseStopPos", []]);

// B116: the native Stop IV Transfusion row sat too close to the enlarged list beneath it. Move the stop row and
// the entire left-list stack down together, preserving the gap instead of letting the button cover the first line.
private _stopNudge = safeZoneH * 0.008;
if (_stopBase isNotEqualTo []) then {
    _stopBase set [1, (_stopBase select 1) + _stopNudge];
    if (!isNull _ctrlNativeStop) then {
        _ctrlNativeStop ctrlSetPosition _stopBase;
        _ctrlNativeStop ctrlCommit 0;
    };
};
if (_leftBase isNotEqualTo []) then {
    _leftBase set [1, (_leftBase select 1) + _stopNudge];
    _leftBase set [3, ((_leftBase select 3) - _stopNudge) max (safeZoneH * 0.20)];
};

private _uiW = safeZoneW min (safeZoneH * 1.7777778);
private _uiX = safeZoneX + ((safeZoneW - _uiW) / 2);

private _rightX = _uiX + (_uiW / 2) + (_uiW / 7.75);
private _rightY = safeZoneY + (safeZoneH / 2) - (safeZoneH / 6);
private _rightW = _uiW / 5.9;
private _rightH = safeZoneH * 0.62;

if (_rightBase isNotEqualTo []) then {
    _rightBase params ["_rx", "_ry", "_rw", "_rh"];
    _rightX = _rx;
    _rightY = _ry;
    _rightW = _rw;
    _rightH = _rh;
};

private _buttonW = _uiW / 12;
private _buttonH = safeZoneH / 40;
if (_stopBase isNotEqualTo []) then {
    _buttonW = _stopBase select 2;
    _buttonH = _stopBase select 3;
};
// match the size of ACM's native move and remove buttons, and the exact gap ACM uses between them, so the whole
// column reads as stock ACM.
private _btnGap = _buttonH * 0.28;
if (_moveBase isNotEqualTo []) then {
    _buttonW = _moveBase select 2;
    _buttonH = _moveBase select 3;
    if (_removeBase isNotEqualTo []) then {
        private _g = (_removeBase select 1) - ((_moveBase select 1) + (_moveBase select 3));
        if (_g > 0) then {_btnGap = _g};
    };
};
private _fontH = _buttonH * 0.62;

private _rowStep = _buttonH * 2;
private _buttonX = _rightX + ((_rightW - _buttonW) / 2);
// mirror the left column: the native fluids list on top, then the prepared-infusion block, the prep and give
// buttons, then the title and list, below it. this column was previously the reverse, with the infusion block
// on top and the fluids beneath, which did not match the left side where infusions sit at the bottom.
private _preparedTitleH = _buttonH * 0.85;
private _preparedH = _rowStep * 2;
private _gap = _buttonH * 0.25;
// the right column, top to bottom: the "Prepared IV sets" toggle button, then the available-bag list, then the
// spike and add button, which acts on the selected bag so it sits right under the list, then the
// prepared-infusion block of prep, give, title and list. a row is reserved for the spike button, so it is
// always visible.
private _spikeRowH = _buttonH;
private _infBlockH = (2 * _buttonH) + (2 * _btnGap) + _preparedTitleH + _preparedH + _spikeRowH + _gap;
// the prepared iv sets toggle sits in its own compact row at the very top of the column, and the fluids list
// starts below it. shifting the list down by _setsBtnH plus _gap, and shrinking it by the same, keeps _spikeY
// and the whole lower block exactly where they were, so only the list gives up a sliver of height for the
// button.
private _setsBtnH = _buttonH;
private _setsBtnY = _rightY;  // the toggle at the very top.
private _nativeListY = _rightY + _setsBtnH + _gap;  // fluids below the sets toggle.
private _nativeListH = (_rightH - _infBlockH - _gap - _setsBtnH - _gap) max _rowStep;
private _spikeY = _nativeListY + _nativeListH + _gap;  // the spike and add button under the list.
private _infBlockY = _spikeY + _spikeRowH + _gap;  // the prepared block below the spike button.
private _prepY = _infBlockY;
private _giveY = _prepY + _buttonH + _btnGap;
private _preparedTitleY = _giveY + _buttonH + _btnGap;
private _preparedY = _preparedTitleY + _preparedTitleH;

if (!isNull _ctrlRightList) then {
    _ctrlRightList ctrlSetPosition [_rightX, _nativeListY, _rightW, _nativeListH max _rowStep];
    _ctrlRightList ctrlCommit 0;
};

// the "Prepared IV sets" toggle button, 86144, in its own row at the top of the column, and the prepared-sets
// overlay list, 86145. with the mode off, the overlay is hidden and the native fluids list, 86005, shows. with
// the mode on, the native list is hidden and the overlay is shown over the same rectangle, so ACM's own
// updatebaglist, which clears and rebuilds 86005 on a body-part, iv or inventory change, never touches our set
// rows. it is re-asserted every pass, so it holds through ACM's event-driven rebuilds.
private _preparedMode = uiNamespace getVariable ["ACME_preparedListMode", false];
private _preparedSetCountB50 = count (ACE_player getVariable ["ACME_preparedIVSets", []]);
private _ctrlSetsBtn = _display displayCtrl 86144;
if (!isNull _ctrlSetsBtn) then {
    _ctrlSetsBtn ctrlSetPosition [_rightX, _setsBtnY, _rightW, _setsBtnH];
    _ctrlSetsBtn ctrlSetFontHeight _fontH;
    // B50: the toggle advertises exactly how many complete IV sets the medic is carrying.  If any exist, pulse
    // the button with the same circulation green family used elsewhere in the medical body map.
    _ctrlSetsBtn ctrlSetText (if (_preparedMode) then {
        format ["<<  Loose Bags | Prepared IV sets (%1)", _preparedSetCountB50]
    } else {
        format ["Prepared IV sets (%1)  >>", _preparedSetCountB50]
    });
    private _setPulse = 0.5 + 0.5 * sin (360 * (diag_tickTime % 1));
    if (_preparedSetCountB50 > 0) then {
        _ctrlSetsBtn ctrlSetBackgroundColor [0.20, 0.65, 0.20, 0.30 + 0.45 * _setPulse];
        _ctrlSetsBtn ctrlSetTextColor [0.82, 1.00, 0.82, 1];
    } else {
        _ctrlSetsBtn ctrlSetBackgroundColor [0, 0, 0, 0.55];
        _ctrlSetsBtn ctrlSetTextColor [1, 1, 1, 1];
    };
    _ctrlSetsBtn ctrlCommit 0;
    _ctrlSetsBtn ctrlShow true;
};
private _ctrlSetsList = _display displayCtrl 86145;
if (!isNull _ctrlSetsList) then {
    _ctrlSetsList ctrlSetPosition [_rightX, _nativeListY, _rightW, _nativeListH max _rowStep];
    _ctrlSetsList ctrlCommit 0;
    _ctrlSetsList ctrlShow _preparedMode;
};
if (!isNull _ctrlRightList) then { _ctrlRightList ctrlShow (!_preparedMode); };

// the spike and add button, 86141, and y tubing, 86142. for a blood bag, or while a y pairing is pending, the
// two share the row as spike and y tubing. otherwise spike takes the full width and y tubing is hidden. in
// prepared iv sets mode neither builds, because the inventory list is hidden, so the y button is always hidden
// and spike becomes the full-width "Hang Set". the labels and the enable state are set in the relabel section
// below.
private _selRow0 = if (!isNull _ctrlRightList) then { lbCurSel _ctrlRightList } else { -1 };
private _selCls0 = if (_selRow0 >= 0) then { ((_ctrlRightList lbData _selRow0) splitString "|") param [0, ""] } else { "" };
// the classname of the FBTK contains "blood", from fieldbloodtransfusionkit, and it is not a blood product for
// y-set building. it is a single collection bag handled natively. exclude it, so the "Spike Y tubing" button
// never shows for it.
private _selIsBlood0 = ((_selCls0 find "FieldBloodTransfusionKit") < 0) && {((toLowerANSI _selCls0) find "blood") >= 0};
private _showY0 = (!_preparedMode) && {_selIsBlood0 || {(missionNamespace getVariable ["ACME_yPending", ""]) != ""}};
private _ctrlSpikeBtn = _display displayCtrl 86141;
private _ctrlYBtn = _display displayCtrl 86142;
if (!isNull _ctrlSpikeBtn) then {
    if (_showY0 && {!isNull _ctrlYBtn}) then {
        private _halfW = (_rightW - _gap) / 2;
        _ctrlSpikeBtn ctrlSetPosition [_rightX, _spikeY, _halfW, _spikeRowH];
        _ctrlYBtn ctrlSetPosition [_rightX + _halfW + _gap, _spikeY, _halfW, _spikeRowH];
        _ctrlYBtn ctrlSetFontHeight _fontH; _ctrlYBtn ctrlCommit 0; _ctrlYBtn ctrlShow true;
    } else {
        _ctrlSpikeBtn ctrlSetPosition [_rightX, _spikeY, _rightW, _spikeRowH];
        if (!isNull _ctrlYBtn) then { _ctrlYBtn ctrlShow false; };
    };
    _ctrlSpikeBtn ctrlSetFontHeight _fontH;
    _ctrlSpikeBtn ctrlCommit 0;
    _ctrlSpikeBtn ctrlShow true;
};
private _ctrlSpikeNative = _display displayCtrl 86140;
if (!isNull _ctrlSpikeNative) then { _ctrlSpikeNative ctrlShow false; };

{
    if (!isNull _x) then {_x ctrlSetFontHeight _fontH;};
} forEach [_ctrlInject, _ctrlPrep, _ctrlGivePrep, _ctrlNativeStop, _ctrlMove, _ctrlRemove, _ctrlPullBag];

// These two controls previously kept their larger config size while the rest of
// this column received the runtime font height above. Use that same height at
// every UI scale; both already inherit the native RobotoCondensed font.
{
    private _ctrl = _display displayCtrl _x;
    if (!isNull _ctrl) then {_ctrl ctrlSetFontHeight _fontH;};
} forEach [86134, 86148];

if (!isNull _ctrlPrep) then {
    _ctrlPrep ctrlSetPosition [_rightX, _prepY, _rightW, _buttonH];
    _ctrlPrep ctrlCommit 0;
};

if (!isNull _ctrlGivePrep) then {
    _ctrlGivePrep ctrlSetPosition [_rightX, _giveY, _rightW, _buttonH];
    _ctrlGivePrep ctrlCommit 0;
};

if (!isNull _ctrlPreparedTitle) then {
    _ctrlPreparedTitle ctrlSetPosition [_rightX, _preparedTitleY, _rightW, _preparedTitleH];
    _ctrlPreparedTitle ctrlSetFontHeight (_preparedTitleH * 0.62);
    _ctrlPreparedTitle ctrlCommit 0;
    _ctrlPreparedTitle ctrlShow true;
};

if (!isNull _ctrlPreparedList) then {
    _ctrlPreparedList ctrlSetPosition [_rightX, _preparedY, _rightW, _preparedH];
    _ctrlPreparedList ctrlCommit 0;
};

// the left-column stack. move and remove are ACM's. below remove we reserve a row for flush line whenever the
// selected access line carries y tubing, and push infuse and hang bag down one row so nothing overlaps, which
// fixes the remove and flush line overlap. with no y line, infuse sits directly below remove as before and
// flush line is hidden.
private _ctrlFlush = _display displayCtrl 86143;
private _ctrlHang  = _display displayCtrl 86134;
private _flTarget = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _flLineKey = format ["%1#%2#%3",
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1]];
private _flLineYd = if (isNull _flTarget) then {false} else {_flLineKey in (_flTarget getVariable ["ACME_YLines", []])};

if (!isNull _ctrlInject) then {
    if (_moveBase isNotEqualTo [] && {_removeBase isNotEqualTo []}) then {
        private _mx = _moveBase select 0;
        private _my = _moveBase select 1;
        private _mw = _moveBase select 2;
        private _mh = _moveBase select 3;
        private _ry = _removeBase select 1;
        private _gap1 = _ry - _my;  // the move to remove row pitch.
        private _row1 = _ry + _gap1;  // the row directly below remove.
        // discard y tubing sits below pull bag, or one row lower when the flush line row is in play. the restored infuse
        // follows one row below it, then hang bag.
        private _infY = if (_flLineYd) then { _row1 + _gap1 } else { _row1 };
        _ctrlInject ctrlSetPosition [_mx, _infY, _mw, _mh];
        if (_flLineYd && {!isNull _ctrlFlush}) then {
            _ctrlFlush ctrlSetPosition [_mx, _row1, _mw, _mh];  // below pull bag and above discard.
            _ctrlFlush ctrlSetFontHeight _fontH;
            _ctrlFlush ctrlCommit 0;
        };
        if (!isNull _ctrlInfuse) then {
            _ctrlInfuse ctrlSetPosition [_mx, _infY + _gap1, _mw, _mh];
            _ctrlInfuse ctrlSetFontHeight _fontH;
            _ctrlInfuse ctrlCommit 0;
            _ctrlInfuse ctrlShow true;
        };
        // hang bag follows one row below infuse, and preserves its own width and height.
        if (!isNull _ctrlHang) then {
            private _hp = ctrlPosition _ctrlHang;
            _ctrlHang ctrlSetPosition [_mx, _infY + (_gap1 * 2), _mw, (_hp select 3)];
            _ctrlHang ctrlCommit 0;

            // pressure infuse sits one row below hang bag, on the same pitch as the whole column. it is driven from the
            // resolved geometry of hang bag rather than from a config y, because every button in this stack is positioned
            // at runtime and a config y would be overwritten the moment this pass ran.
            private _ctrlPI = _display displayCtrl 86148;
            if (!isNull _ctrlPI) then {
                _ctrlPI ctrlSetPosition [_mx, _infY + (_gap1 * 3), _mw, (_hp select 3)];
                _ctrlPI ctrlCommit 0;
                _ctrlPI ctrlShow true;
            };
        };
    } else {
        _ctrlInject ctrlSetPosition [_uiX + (_uiW / 2) - (_uiW / 8), safeZoneY + (safeZoneH / 2) - (safeZoneH / 10), _uiW / 22, safeZoneH / 40];
    };
    _ctrlInject ctrlCommit 0;
};

if !(_activeContext isEqualTo []) then {
    _activeContext params ["_patient", "_bodyPart", "_bagIndex", "_type", "_accessType", "_bagAccessSite", "_bagIV", "_bloodType", "_volume", "_freshBloodID", "_remainingVolume"];
    _canActive = [_activeContext] call ACME_fnc_canMedicateBagContext;
    private _entries = _patient getVariable ["ACME_infusion_BagMedications", []];
    // the same matcher the infusions sub-list uses, so the adjust readout and the list can never disagree about
    // whether this bag is infusing. the active bag context carries the selected access site and true index, so hand
    // the matcher a bag row in the shape it expects.
    private _acRow = [_type, _remainingVolume, _accessType, _bagAccessSite, _bagIV, _bloodType, _volume, _freshBloodID, _bagIndex];
    private _hit = [_patient, _bodyPart, _acRow, _entries] call ACME_fnc_bagInfusionEntry;
    if !(_hit isEqualTo []) then {
        (_hit select 0) params ["", "", "", "", "", "", "", "", "", "", "", "_medication", "_classIV", "_doseTotal", "_doseRemaining", "_pendingDose", "_lastPulse", "_rateMgPerSecond", "_lastTick", "_durationSeconds", ["_dropSet", ACME_infusion_defaultDropSet], ["_dropsPerMinute", 60], ["_clampPosition", -1]];
        _hasInfusion = true;
        if (_clampPosition < 0) then {_clampPosition = [_dropsPerMinute] call ACME_fnc_dropsToClampPosition};
        private _medName = localize (format ["STR_ACM_Circulation_Medication_%1", _medication]);
        if (_medName == "") then {_medName = _medication};
        _rateText = format ["%1 | %2", _medName, [_doseRemaining, _remainingVolume, _dropSet, _dropsPerMinute, _clampPosition] call ACME_fnc_formatRate];
    };
};

private _selection = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags", []];
private _targetPatient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _selectedAccessValid = false;
if (!isNull _targetPatient) then {
    private _txBodyPart = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
    private _txIV = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
    private _txSite = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
    _selectedAccessValid = [_targetPatient,_txBodyPart,_txIV,_txSite] call ACME_fnc_transfusionAccessValid;
};
private _targetBodyPart = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _entriesForTarget = if (isNull _targetPatient) then {[]} else {_targetPatient getVariable ["ACME_infusion_BagMedications", []]};
private _infusionSelectionIndexes = [];
private _infusionLabels = [];

// bag to drug-entry binding, through the one shared matcher, ACME_fnc_bagInfusionEntry. it must be one to one:
// an entry backs exactly one bag row and a row holds exactly one entry, so two identical carriers, one with a
// drug and one plain, never both claim the same entry. exact bindings, on identity, bagindex and access site,
// are taken first, so they get first refusal on their entry before any looser identity-only match can steal it,
// and each claimed entry is then consumed so nothing double-binds. using the same matcher the adjust readout
// uses is what guarantees the list and the adjust button can never disagree about whether a bag is
// infusing.
private _claimed = [];  // indices into _entriesForTarget that are already bound to a row.
private _rowEntry = [];  // per bag row: its bound entry, or [] if it is a plain carrier.
{ _rowEntry pushBack []; } forEach _selection;

// pass 1: exact matches first. the matcher returns an exact one when the bagindex and the site line up.
{
    private _selIndex = _forEachIndex;
    private _hit = [_targetPatient, _targetBodyPart, _x, _entriesForTarget, _claimed] call ACME_fnc_bagInfusionEntry;
    if !(_hit isEqualTo []) then {
        _hit params ["_entry", "_entryIdx"];
        _entry params ["", "", "_hEBagIndex", "", "_hEAccessSite"];
        _x params ["", "", "", ["_sAccessSite", -1], "", "", "", "", ["_sTrueIndex", -1]];
        // bind here only if this is the exact one, and leave identity-only rows for pass 2, so an exact owner elsewhere
        // gets first refusal on its entry.
        if ((_hEBagIndex == _sTrueIndex) && {_hEAccessSite == _sAccessSite}) then {
            _rowEntry set [_selIndex, _entry];
            _claimed pushBack _entryIdx;
        };
    };
} forEach _selection;

// pass 2: rows still unbound take any remaining identity match from what is left.
{
    private _selIndex = _forEachIndex;
    if ((_rowEntry select _selIndex) isEqualTo []) then {
        private _hit = [_targetPatient, _targetBodyPart, _x, _entriesForTarget, _claimed] call ACME_fnc_bagInfusionEntry;
        if !(_hit isEqualTo []) then {
            _hit params ["_entry", "_entryIdx"];
            _rowEntry set [_selIndex, _entry];
            _claimed pushBack _entryIdx;
        };
    };
} forEach _selection;

// build the sub-list rows from the now unambiguous bindings.
{
    private _selIndex = _forEachIndex;
    _x params ["_sType", "_sRemaining", "_sAccessType", "_sAccessSite", "_sIV", ["_sBloodType", -1], ["_sVolume", 0], ["_sFreshBloodID", -1], ["_sTrueIndex", -1]];
    private _bestEntry = _rowEntry select _selIndex;
    if !(_bestEntry isEqualTo []) then {
        _infusionSelectionIndexes pushBackUnique _selIndex;
        _infusionLabels pushBack [_selIndex, [_bestEntry, _targetPatient getVariable ["ACME_infusion_BagMedications", []]] call ACME_fnc_formatInfusionLabel, _sRemaining, _sType, _sBloodType, _sVolume, (_bestEntry param [11, ""]), _sTrueIndex];
    };
} forEach _selection;

private _hasActiveInfusions = !(_infusionSelectionIndexes isEqualTo []);
// active drug infusions get their own sub-list directly below the transfusion list, so each one can be selected
// and have its drip rate adjusted. the matching bag rows are moved out of the main list into that sub-list
// below, and non-infusion bags stay in the main list. this was briefly forced off in favor of an inline
// "(Infusing...)" tag on the bag row, and the separate adjustable section is the intended ux.

if (!isNull _ctrlLeftList) then {
    if (_leftBase isNotEqualTo []) then {
        _leftBase params ["_lx", "_ly", "_lw", "_lh"];
        if (_hasActiveInfusions) then {
            private _normalH = _lh * 0.55;
            private _titleH = _buttonH * 0.85;
            private _gap = _buttonH * 0.25;
            private _infTitleY = _ly + _normalH + _gap;
            private _infListY = _infTitleY + _titleH;
            private _infListH = (_ly + _lh) - _infListY;
            _ctrlLeftList ctrlSetPosition [_lx, _ly, _lw, _normalH];
            _ctrlLeftList ctrlCommit 0;
            if (!isNull _ctrlActiveInfTitle) then {
                _ctrlActiveInfTitle ctrlSetPosition [_lx, _infTitleY, _lw, _titleH];
                _ctrlActiveInfTitle ctrlSetFontHeight (_titleH * 0.62);
                _ctrlActiveInfTitle ctrlCommit 0;
                _ctrlActiveInfTitle ctrlShow true;
            };
            if (!isNull _ctrlActiveInfList) then {
                _ctrlActiveInfList ctrlSetPosition [_lx, _infListY, _lw, _infListH max _rowStep];
                _ctrlActiveInfList ctrlCommit 0;
                _ctrlActiveInfList ctrlShow true;
            };
        } else {
            _ctrlLeftList ctrlSetPosition _leftBase;
            _ctrlLeftList ctrlCommit 0;
            if (!isNull _ctrlActiveInfTitle) then {_ctrlActiveInfTitle ctrlShow false;};
            if (!isNull _ctrlActiveInfList) then {_ctrlActiveInfList ctrlShow false; _display setVariable ["ACME_txRebuilding", true];
            lbClear _ctrlActiveInfList;};
        };
    };

    if (_hasActiveInfusions) then {
        _display setVariable ["ACME_txRebuilding", true];
        for "_r" from ((lbSize _ctrlLeftList) - 1) to 0 step -1 do {
            if ((_ctrlLeftList lbValue _r) in _infusionSelectionIndexes) then {
                _ctrlLeftList lbDelete _r;
            };
        };
    };

    // infusion marker. an actively flowing saline bag is an infusion in progress, so relabel ACM's "[S:" saline
    // marker to "[I:" and tint the row yellow, so the running bag reads as an infusion rather than just hung
    // saline. listbox rows cannot color a single glyph, so the whole row carries the color. the native rows for
    // bags ACME has pulled into its own infusions list are already gone above.
    if (!isNull _targetPatient && {_targetBodyPart != ""}) then {
        private _partIdx = ACME_infusion_bodyParts find toLowerANSI _targetBodyPart;
        private _flowIV = _targetPatient getVariable ["ACM_circulation_FluidBagsFlow_IV", []];
        private _flowIO = _targetPatient getVariable ["ACM_circulation_FluidBagsFlow_IO", []];
        for "_r" from 0 to ((lbSize _ctrlLeftList) - 1) do {
            private _selIdx = _ctrlLeftList lbValue _r;
            if (_selIdx >= 0 && {_selIdx < count _selection}) then {
                (_selection select _selIdx) params [["_sType", ""], "", "", ["_sAccessSite", -1], ["_sIV", false]];
                // saline rows ship without artwork, because the saline fluid config carries no picture, so give them the ACE
                // saline-bag icon. that matches how blood units already show their bag art.
                if (_sType in ["Saline", "ACME_SalineY"]) then { _ctrlLeftList lbSetPicture [_r, "\z\ace\addons\medical_treatment\ui\salineIV_ca.paa"]; };
                private _flowing = false;
                if (_partIdx >= 0) then {
                    if (_sIV) then {
                        if (_partIdx < count _flowIV) then {
                            private _pf = _flowIV select _partIdx;
                            if (_sAccessSite >= 0 && {_sAccessSite < count _pf}) then {_flowing = (_pf select _sAccessSite) > 0};
                        };
                    } else {
                        if (_partIdx < count _flowIO) then {_flowing = (_flowIO select _partIdx) > 0};
                    };
                };
                if (_flowing) then {
                    private _txt = _ctrlLeftList lbText _r;
                    private _at = _txt find "[S";
                    if (_at >= 0) then {
                        _ctrlLeftList lbSetText [_r, (_txt select [0, _at]) + "[I" + (_txt select [_at + 2])];
                    };
                    _ctrlLeftList lbSetColor [_r, [1, 0.85, 0.16, 1]];  // pillar amber.
                };
                // blood warmer. a warmed blood unit reads orange with a [warmed] tag, which wins over amber.
                if ((_sType in ["Blood", "FreshBlood"]) && {_targetPatient getVariable ["ACME_warmedBlood", false]}) then {
                    private _wtxt = _ctrlLeftList lbText _r;
                    if ((_wtxt find " [Warmed]") < 0) then {
                        _ctrlLeftList lbSetText [_r, _wtxt + " [Warmed]"];
                    };
                    _ctrlLeftList lbSetColor [_r, [1, 0.55, 0.13, 1]];  // warm orange.
                };
                // cooled blood. if the medic is carrying a blood cooler that still holds blood, the blood units read light blue
                // with a [cooled] tag. it is a reminder that they are cold and will pull body temperature down during
                // transfusion unless they run through the inline warmer. [warmed] takes precedence, because a unit on the
                // warmer is no longer cold, so this only paints unwarmed blood.
                if ((_sType in ["Blood", "FreshBlood"]) && {!(_targetPatient getVariable ["ACME_warmedBlood", false])}) then {
                    private _coolStore = ACE_player getVariable ["ACME_coolerStore", createHashMap];
                    private _heldClr = ((uniformItems ACE_player) + (vestItems ACE_player) + (backpackItems ACE_player)) select { (_x find "ACME_BloodCooler_") == 0 };
                    if (((keys _coolStore) findIf {(_x in _heldClr) && {(count (_coolStore getOrDefault [_x, []])) > 0}}) >= 0) then {
                        private _ctxt = _ctrlLeftList lbText _r;
                        if ((_ctxt find " [Cooled]") < 0) then {
                            _ctrlLeftList lbSetText [_r, _ctxt + " [Cooled]"];
                        };
                        _ctrlLeftList lbSetColor [_r, [0.45, 0.72, 1, 1]];  // light blue.
                    };
                };
                // y line linkage. blood on a y-tubing'd line gets a [y] tag, so the unit and its paired saline read as one
                // line.
                if (_sType in ["Blood", "FreshBlood"]) then {
                    private _rowLineKey = format ["%1#%2#%3", _targetBodyPart, _sIV, _sAccessSite];
                    if (_rowLineKey in (_targetPatient getVariable ["ACME_YLines", []])) then {
                        private _ytxt = _ctrlLeftList lbText _r;
                        if ((_ytxt find " [Y]") < 0) then { _ctrlLeftList lbSetText [_r, _ytxt + " [Y]"]; };
                    };
                };

                // medications infusing through this bag. instead of listing them as separate infusion-tab rows, tag the bag with
                // "(Infusing...)" and put the drug names and doses in the hover tooltip of the row.
                (_selection select _selIdx) params [["_rType",""], "", "", ["_rAccessSite",-1], ["_rIV",false], ["_rBloodType", -1], ["_rVolume", 0], ["_rFreshBloodID", -1], ["_rTrueIndex", -1]];
                private _medsHere = [];
                {
                    _x params ["", "_eBodyPart", "_eBagIndex", "_eType", "_eAccessSite", "_eIV", "_eBloodType", "_eVolume", "_eFreshBloodID", "", "", "_eMedication", "", "_eDoseTotal", "_eDoseRemaining"];
                    if ((toLowerANSI _eBodyPart == toLowerANSI _targetBodyPart) && {_eType == _rType} && {_eIV == _rIV} && {_eBloodType == _rBloodType} && {_eVolume == _rVolume} && {_eFreshBloodID == _rFreshBloodID}) then {
                        private _mn = localize (format ["STR_ACM_Circulation_Medication_%1", _eMedication]);
                        if (_mn == "") then {_mn = _eMedication};
                        _medsHere pushBack ([_eMedication, _eDoseRemaining] call ACME_fnc_formatDose);
                    };
                } forEach _entriesForTarget;
                if !(_medsHere isEqualTo []) then {
                    private _itxt = _ctrlLeftList lbText _r;
                    if ((_itxt find " (Infusing...)") < 0) then { _ctrlLeftList lbSetText [_r, _itxt + " (Infusing...)"]; };
                    _ctrlLeftList lbSetTooltip [_r, format ["Infusing: %1", _medsHere joinString ", "]];
                };
            };
        };
    };
};

if (!isNull _ctrlActiveInfList) then {
    if (_hasActiveInfusions) then {
        // the signature drives the lbclear and rebuild. it is built from structural fields only, the selidx, label,
        // type, blood, nominal volume and medication, and deliberately excludes the live remaining volume, _sRemaining
        // at index 2. that drains continuously, so including it rebuilt the listbox every tick at 20 hz, which is the
        // visible flash after a bag starts flowing. the label uses the mix volume rather than the remaining volume, so
        // dropping it costs nothing on screen.
        private _signature = str (_infusionLabels apply {[_x select 0, _x select 1, _x select 3, _x select 4, _x select 5, _x select 6]});
        if ((uiNamespace getVariable ["ACME_infusion_ActiveInfusionListSignature", ""]) != _signature) then {
            private _oldSelected = missionNamespace getVariable ["ACME_infusion_SelectedActiveInfusionSelectionIndex", -1];
            private _oldTrueIndex = missionNamespace getVariable ["ACME_infusion_SelectedActiveInfusionTrueIndex", -1];
            _display setVariable ["ACME_txRebuilding", true];
            lbClear _ctrlActiveInfList;
            {
                _x params ["_selIdx", "_label", "_remaining", "_pType", "_pBloodType", "_pVolume", "_pMedication", ["_pTrueIndex", -1]];
                private _i = _ctrlActiveInfList lbAdd _label;
                _ctrlActiveInfList lbSetValue [_i, _selIdx];
                _ctrlActiveInfList lbSetTooltip [_i, format ["%1 | %2ml remaining", _label, round _remaining]];
                // the same bag artwork ACM uses in its own list, with the vial icon at the right.
                private _bagClass = [_pType, _pVolume, _pBloodType] call ACM_circulation_fnc_formatFluidBagName;
                private _bagPic = getText (configFile >> "CfgWeapons" >> _bagClass >> "picture");
                if (_bagPic != "") then {_ctrlActiveInfList lbSetPicture [_i, _bagPic];};
                if (_pMedication isEqualType "" && {_pMedication != ""}) then {
                    private _vialPic = getText (configFile >> "CfgWeapons" >> ([_pMedication] call ACME_fnc_vialClass) >> "picture");
                    if (_vialPic != "") then {_ctrlActiveInfList lbSetPictureRight [_i, _vialPic];};
                };
                // re-select across a rebuild by the stable trueindex of the bag first, which survives ACM reordering the
                // selection array when a unit empties or is pulled, and fall back to the positional selidx. this is what kept
                // the infusion selected, so a medic can keep adjusting it after the first set.
                if ((_pTrueIndex >= 0 && {_pTrueIndex == _oldTrueIndex}) || {_selIdx == _oldSelected}) then {_ctrlActiveInfList lbSetCurSel _i;};
            } forEach _infusionLabels;
            uiNamespace setVariable ["ACME_infusion_ActiveInfusionListSignature", _signature];
        };
    } else {
        _display setVariable ["ACME_txRebuilding", true];
            lbClear _ctrlActiveInfList;
    };
};

private _canPrep = false;
if (_preparedMode) then {
    // B50: Prep Infusion is ONLY a Prepared IV sets action.  It is enabled only when the currently selected set is
    // a staged saline record and its physical bag/action pair also passes the saline classifier.  A blood, FWB,
    // PlasmaLyte, HTS, magnesium, mannitol, other premix or malformed set can never light this button.
    private _selSet = if (!isNull _ctrlSetsList) then {lbCurSel _ctrlSetsList} else {-1};
    private _selSetId = if (_selSet >= 0 && {!isNull _ctrlSetsList}) then {_ctrlSetsList lbData _selSet} else {""};
    if (_selSetId != "") then {
        private _pSets = ACE_player getVariable ["ACME_preparedIVSets", []];
        private _pIdx = _pSets findIf {(_x param [0, ""]) isEqualTo _selSetId};
        if (_pIdx >= 0) then {
            private _prepRec = _pSets select _pIdx;
            private _prepClass = _prepRec param [1, ""];
            private _prepAction = _prepRec param [2, ""];
            _canPrep = ((_prepRec param [8, "yset"]) isEqualTo "saline")
                && {[_prepClass, _prepAction] call ACME_fnc_isSalineItem};
        };
    };
};
// In loose-bag view _canPrep deliberately remains false, even if a saline set exists elsewhere in inventory.
// The medic must open Prepared IV sets and deliberately select the carrier that will receive the medication.

private _preparedEntries = ACE_player getVariable ["ACME_infusion_PreparedBags", []];
private _preparedCount = count _preparedEntries;
private _selectedPrepared = -1;

_display setVariable ["ACME_txRebuilding", false];

if (!isNull _ctrlPreparedList) then {
    private _signature = str (_preparedEntries apply {[_x param [0, ""], _x param [3, ""], _x param [4, 0], _x param [10, -1]]});
    if ((uiNamespace getVariable ["ACME_infusion_PreparedListSignature", ""]) != _signature) then {
        private _oldSelected = missionNamespace getVariable ["ACME_infusion_SelectedPreparedIndex", -1];
        lbClear _ctrlPreparedList;
        if (_preparedEntries isEqualTo []) then {
            private _i = _ctrlPreparedList lbAdd "No prepped infusions";
            _ctrlPreparedList lbSetValue [_i, -1];
        } else {
            {
                private _label = [_x] call ACME_fnc_formatPreparedLabel;
                private _i = _ctrlPreparedList lbAdd _label;
                _ctrlPreparedList lbSetValue [_i, _forEachIndex];
                _ctrlPreparedList lbSetTooltip [_i, _label];
            } forEach _preparedEntries;
            if (_oldSelected < 0 || {_oldSelected >= count _preparedEntries}) then {_oldSelected = 0};
            _ctrlPreparedList lbSetCurSel _oldSelected;
            missionNamespace setVariable ["ACME_infusion_SelectedPreparedIndex", _oldSelected];
        };
        uiNamespace setVariable ["ACME_infusion_PreparedListSignature", _signature];
    };

    private _row = lbCurSel _ctrlPreparedList;
    if (_row >= 0) then {
        _selectedPrepared = _ctrlPreparedList lbValue _row;
        if (_selectedPrepared >= 0) then {missionNamespace setVariable ["ACME_infusion_SelectedPreparedIndex", _selectedPrepared];};
    };
    _ctrlPreparedList ctrlShow true;
};

if (!isNull _ctrlPrep) then {_ctrlPrep ctrlEnable _canPrep;};
// pull bag operates on the selected hung bag. it must never resolve to an infusion, and it must gray out
// entirely when no bag row is selected in the transfusion list.
if (!isNull _ctrlPullBag) then {_ctrlPullBag ctrlEnable _bagRowSelected;};
private _preparedLineIsY = [
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true],
    missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1]
] call ACME_fnc_isYLineAccess;
// 86120 is the repurposed "Discard Y Tubing" button. it is live only when the selected access actually carries
// a y and a bag row is selected in the transfusion list.
if (!isNull _ctrlInject) then {_ctrlInject ctrlEnable (_bagRowSelected && {_preparedLineIsY});};
// 86147 is the restored infuse. it is live only when the selected hung bag can carry a medication, which the
// central gate, canMedicateBagContext, now restricts to a plain normal saline bag with fluid left at any
// volume, and only when a bag row is actually selected in the transfusion list.
if (!isNull _ctrlInfuse) then {_ctrlInfuse ctrlEnable (_bagRowSelected && {_canActive});};
if (!isNull _ctrlGivePrep) then {
    private _canGive = _selectedAccessValid && {(_selectedPrepared >= 0 && {_selectedPrepared < _preparedCount})} && {!_preparedLineIsY};
    _ctrlGivePrep ctrlEnable _canGive;
    _ctrlGivePrep ctrlSetText "Give Infusion";
    // yellow when an infusion is selected, because this action is transfusion-bound.
    _ctrlGivePrep ctrlSetTextColor ([[1, 1, 1, 1], (["warning", 1] call ACME_fnc_a11yColor)] select _canGive);
};

if (!isNull _ctrlDrop) then {_ctrlDrop ctrlShow false;};
if (!isNull _ctrlRateDown) then {_ctrlRateDown ctrlShow false;};
if (!isNull _ctrlRateUp) then {_ctrlRateUp ctrlShow false;};
if (!isNull _ctrlRateText) then {
    // attached flush to the bottom edge of ACM's transfusion window. on menubackground, x is szx plus szw/4, w is
    // szw/2, and the bottom is szy plus 0.75 times szh.
    private _winX = _uiX + (_uiW / 2) - (_uiW * 0.35);
    private _winW = _uiW * 0.70;
    private _winBottom = safeZoneY + (safeZoneH * 0.865);
    _ctrlRateText ctrlSetPosition [_winX, _winBottom, _winW, _buttonH * 1.25];
    _ctrlRateText ctrlCommit 0;
    _ctrlRateText ctrlShow _hasInfusion;
    _ctrlRateText ctrlSetText _rateText;
};

// ACM's native move must never relocate a medicated bag, because its move flow breaks the entry linkage. it is
// disabled whenever the native list selection is one of our infusions, unless ACM's move flow is
// mid-transaction, because the same button completes and continues sanctioned moves started from our own
// button.
if (!isNull _ctrlMove) then {
    private _nativeSelMedicated = _hasInfusion && {!isNull _ctrlLeftList} && {(lbCurSel _ctrlLeftList) >= 0};
    private _acmMoveBusy = (missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Move_Active", false]) || {missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Move_Active_Moving", false]};
    _ctrlMove ctrlEnable !(_nativeSelMedicated && {!_acmMoveBusy});
};

// infusions-specific move and remove. it is a vertical stack to the right of the infusions list, mirroring ACM's
// native move and remove column. the side offset and the gap are taken from ACM's own geometry, so it reads as
// stock.
private _infSelected = false;
if (!isNull _ctrlActiveInfList && {ctrlShown _ctrlActiveInfList}) then {
    _infSelected = (lbCurSel _ctrlActiveInfList) >= 0;
};
private _sideGap = _btnGap;
if (_moveBase isNotEqualTo [] && {_leftBase isNotEqualTo []}) then {
    private _g = (_moveBase select 0) - ((_leftBase select 0) + (_leftBase select 2));
    if (_g > 0) then {_sideGap = _g};
};
{
    _x params ["_ctrl", "_slot"];
    if (!isNull _ctrl) then {
        if (!isNull _ctrlActiveInfList) then {
            (ctrlPosition _ctrlActiveInfList) params ["_listX", "_listY", "_listW", "_listH"];
            _ctrl ctrlSetPosition [_listX + _listW + _sideGap, _listY + (_slot * (_buttonH + _btnGap)), _buttonW, _buttonH];
            _ctrl ctrlSetFontHeight _fontH;
            _ctrl ctrlCommit 0;
            _ctrl ctrlShow (ctrlShown _ctrlActiveInfList);
        } else {
            _ctrl ctrlShow false;
        };
        _ctrl ctrlEnable _infSelected;
    };
} forEach [[_ctrlInfMove, 0], [_ctrlInfRemove, 1], [_ctrlInfPressure, 2]];
private _pane = _display getVariable ["ACME_txActivePane", "transfusion"];
private _txCtx = ["transfusion"] call ACME_fnc_getSelectedActiveBagContext;
private _inCtx = ["infusion"] call ACME_fnc_getSelectedActiveBagContext;
private _txSelected = _pane == "transfusion" && {!(_txCtx isEqualTo [])};
if (_txSelected) then {
    private _physical = ((_targetPatient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_txCtx select 1, []]) param [(_txCtx select 2) max 0, []];
    private _id = _physical param [8, ""];
    if (_id != "" && {((_targetPatient getVariable ["ACME_infusion_BagMedications", []]) findIf {(_x param [23, ""]) == _id}) >= 0}) then {_txSelected = false;};
};
if (!isNull _ctrlHang) then {
    _ctrlHang ctrlEnable (_selectedAccessValid && {_txSelected} && {(_txCtx param [10, 0]) > 0.5} && {(_txCtx param [3, ""]) in ["Blood","FreshBlood","Saline","Plasma","PlasmaLyte"]} && {!(ACE_player getVariable ["ACME_hang_Active", false])} && {isNull objectParent ACE_player});
};
(_display displayCtrl 86148) ctrlEnable (_txSelected && {[_txCtx, false] call ACME_fnc_pressureInfuserCan});
if (!isNull _ctrlInfPressure) then {
    _ctrlInfPressure ctrlEnable (_pane == "infusion" && {[_inCtx, true] call ACME_fnc_pressureInfuserCan});
};

// a dedicated entry point. "Adjust Infusion" sits directly above the infusions section, anchored to the live
// position of the section title so it tracks any resolution or aspect ratio. it is visible with the section and
// enabled on selection.
if (!isNull _ctrlAdjust) then {
    if (!isNull _ctrlActiveInfTitle) then {
        (ctrlPosition _ctrlActiveInfTitle) params ["_titleX", "_titleY", "_titleW", "_titleH"];
        _ctrlAdjust ctrlSetPosition [_titleX, _titleY - _buttonH - (safeZoneH * 0.003), _titleW, _buttonH];
        _ctrlAdjust ctrlCommit 0;
        _ctrlAdjust ctrlShow (ctrlShown _ctrlActiveInfTitle);
    } else {
        _ctrlAdjust ctrlShow false;
    };
    _ctrlAdjust ctrlEnable _hasInfusion;
};
// do not add a "ButtonClick" event handler to the native stop control, 86006. it already carries ACM's config
// action, call func(transfusionmenu_toggleivflow), and that function is a pure toggle: a flow above 0 goes to
// 0, and otherwise it goes to 1. a second identical handler made it fire twice per click, toggling off then
// back on, so stop appeared to do nothing. the config action alone is correct.

// spike bag. relabel the renamed add bag button by the spike state of the selected bag, and ungray prep infusion
// only once a bag is spiked. each physical bag must be spiked, which consumes one iv line, before a medic can
// hang it. the spike persists on the medic until the bag is used, meaning hung, or removed, meaning dropped,
// which the availability clamp below detects automatically.
private _ctrlSpike = _display displayCtrl 86141;
private _spiked = ACE_player getVariable ["ACME_spikedBags", createHashMap];
private _selClass = "";
if (!isNull _ctrlRightList) then {
    private _si = lbCurSel _ctrlRightList;
    if (_si >= 0) then { _selClass = ((_ctrlRightList lbData _si) splitString "|") param [0, ""]; };
};
// clamp the spiked count of the selected class to what is actually on hand, across the medic and the patient. a
// hung or dropped bag drops the count, so its spike clears. that is the until-used-or-removed rule, for
// free.
if (_selClass != "") then {
    private _avail = [ACE_player, _targetPatient, _selClass] call ACME_fnc_treatmentSupplyCount;
    if ((_spiked getOrDefault [_selClass, 0]) > _avail) then {
        _spiked set [_selClass, _avail];
        ACE_player setVariable ["ACME_spikedBags", _spiked, true];
    };
};
private _spikingActive = missionNamespace getVariable ["ACME_spikingActive", []];
private _isSpikingSel = (count _spikingActive > 0) && {(_spikingActive param [0, ""]) == _selClass};

// the blood and y-line state for the selected bag and the selected access line. the FBTK is excluded, see the
// show-gate note above, because it is a native single-bag collection kit and never a y-set blood product.
private _selIsFBTK = (_selClass find "FieldBloodTransfusionKit") >= 0;
private _selIsBlood = !_selIsFBTK && {((toLowerANSI _selClass) find "blood") >= 0};
private _yPending = missionNamespace getVariable ["ACME_yPending", ""];
// Built sets have their own prepared-set rows; native bag rows use the selected live line.
private _bpSel = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _ivSel = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _siteSel = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
private _lineKey = format ["%1#%2#%3", _bpSel, _ivSel, _siteSel];
private _yLines = if (isNull _targetPatient) then {[]} else {_targetPatient getVariable ["ACME_YLines", []]};
private _lineYd = _lineKey in _yLines;
private _lineDirty = if (isNull _targetPatient) then {false} else {(_targetPatient getVariable ["ACME_YLineDirty", createHashMap]) getOrDefault [toLower (format ["%1#%2#%3", _bpSel, _ivSel, _siteSel]), false]};
private _yReady = _lineYd;

// the state for the selected bag and access line.
private _normalSpiked = (_spiked getOrDefault [_selClass, 0]) >= 1;
private _yPrepped = _selIsBlood && {_lineYd};
private _yPendingThis = (_yPending != "") && {_yPending == _selClass};
// the action class of the selected available row. it is used to validate the saline on pick saline, for the
// graying.
private _selAction = "";
if (!isNull _ctrlRightList) then {
    private _si2 = lbCurSel _ctrlRightList;
    if (_si2 >= 0) then { _selAction = ((_ctrlRightList lbData _si2) splitString "|") param [1, ""]; };
};
private _selValidSaline = (_selClass != "") && {[_selClass, _selAction] call ACME_fnc_isSalineItem};

// is a unit actively running on the selected y line? this stops add bag looking clickable mid-transfusion.
private _yActiveBlood = false;
private _yLiveReserve = false;
if (!isNull _targetPatient && _lineYd) then {
    private _lineBags = (_targetPatient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_bpSel, []];
    _yActiveBlood = (_lineBags findIf {
        ((_x param [3, -1]) isEqualTo _siteSel) && {(_x param [4, true]) isEqualTo _ivSel} &&
        {((_x param [0, ""]) in ["Blood", "FreshBlood"]) && {(_x param [1, 0]) > 0.01}}
    }) >= 0;
    // a live clamped saline reserve on this line. there is nothing to refill until flush line bleeds it.
    _yLiveReserve = (_lineBags findIf {
        ((_x param [3, -1]) isEqualTo _siteSel) && {(_x param [4, true]) isEqualTo _ivSel} &&
        {((_x param [0, ""]) in ["ACME_SalineY", "Saline"]) && {(_x param [1, 0]) > 0.5}}
    }) >= 0;
};

// spike bag, 86141. it reads "Spike Bag" and becomes "Add Bag" once spiked, whether normally or y-prepped. for
// blood this is the non-y path and is mutually exclusive with spike y tubing. on a y line it is grayed while a
// unit runs and grayed while the line needs flushing, and it goes live again once the line is empty and
// flushed, which refills the empty bag slot.
if (!isNull _ctrlSpike) then {
    if (_preparedMode) then {
        // prepared iv sets mode. the spike button hangs the selected stored set. it is enabled only when a real set row,
        // with non-empty lbdata, is selected in the overlay list.
        private _setSel = if (!isNull _ctrlSetsList) then { lbCurSel _ctrlSetsList } else { -1 };
        private _setOk = _selectedAccessValid && {(_setSel >= 0)} && {!isNull _ctrlSetsList} && {(_ctrlSetsList lbData _setSel) != ""};
        _ctrlSpike ctrlSetText "Hang Set";
        _ctrlSpike ctrlEnable _setOk;
    } else {
        // loose-bag mode. by default the spike button spikes the selected bag and stages it into the prepared iv sets.
        // there are exceptions. a blood unit selected while this access site already carries a y line reads "Add to Y
        // tubing", which is a direct refill onto the existing y line, and a saline on a y'd site reads "Add Bag", which
        // is a direct reserve refill. blood shows "Unit running" while one is up and needs a flush when the line is
        // dirty, and saline shows "Reserve set" while a live reserve is still hanging. it is grayed during a spike
        // beat.
        private _txt = "Spike Bag";
        private _en = (_selClass != "");
        if (_isSpikingSel) then {
            _txt = "Spiking Bag...";
            _en = false;
        } else {
            if (_selIsBlood && _lineYd) then {
                if (_yActiveBlood) then {
                    _txt = "Unit running";
                    _en = false;
                } else {
                    _txt = "Add to Y tubing";
                    _en = !_lineDirty;
                };
            } else {
                if (_selValidSaline && _lineYd) then {
                    // a saline on a y'd site refills the clamped saline reserve in place, as "Add Bag". it is grayed while a live
                    // reserve is still hanging, because flush line bleeds it first.
                    if (_yLiveReserve) then {
                        _txt = "Reserve set";
                        _en = false;
                    } else {
                        _txt = "Add Bag";
                        _en = true;
                    };
                } else {
                    _en = (_selClass != "") && {!(_selIsBlood && _yPendingThis)};
                };
            };
        };
        if (_selIsFBTK && {!_ivSel}) then {
            _txt = "IV required";
            _en = false;
        };
        _ctrlSpike ctrlSetText _txt;
        _ctrlSpike ctrlEnable _en;
    };
};

// spike y tubing, 86142. it has three states while building a prepared set. with nothing pending it reads "Spike
// Y tubing", grayed unless a fresh, un-spiked blood unit is selected. with blood pending and saline not, it
// reads "Select Flush Saline", grayed unless a proper ACM saline is selected. with both pending it reads "Build
// Y Tubing", which assembles and stores the set.
private _ctrlY = _display displayCtrl 86142;
private _yPendingSaline = missionNamespace getVariable ["ACME_yPendingSaline", ""];
if (!isNull _ctrlY) then {
    if (diag_tickTime < (missionNamespace getVariable ["ACME_yBuildingActive", -1])) then {
        _ctrlY ctrlSetText "Building...";
        _ctrlY ctrlEnable false;
    } else {
    if (_yPending != "" && {_yPendingSaline != ""}) then {
        _ctrlY ctrlSetText "Build Y Tubing";
        _ctrlY ctrlEnable true;
    } else {
        if (_yPending != "") then {
            _ctrlY ctrlSetText "Select Flush Saline";
            _ctrlY ctrlEnable _selValidSaline;
        } else {
            _ctrlY ctrlSetText "Spike Y tubing";
            _ctrlY ctrlEnable (_selIsBlood && {!_normalSpiked} && {!_yPrepped});
        };
    };
    };
};

// flush line, 86143. it is visible on a y'd line, and enabled and pulsing once a unit has run, so a dirty line
// means a flush is needed.
private _ctrlFlush2 = _display displayCtrl 86143;
if (!isNull _ctrlFlush2) then {
    _ctrlFlush2 ctrlShow _lineYd;
    _ctrlFlush2 ctrlEnable _lineDirty;
    if (_lineYd) then {
        if (_lineDirty) then {
            private _p = 0.5 + (0.5 * sin (360 * ((diag_tickTime * 1.1) % 1)));  // a pulse at about 1.1 hz.
            _ctrlFlush2 ctrlSetBackgroundColor (["danger", 0.55 + (0.4 * _p)] call ACME_fnc_a11yColor);
            _ctrlFlush2 ctrlSetTextColor (["danger2", 1] call ACME_fnc_a11yColor);
        } else {
            _ctrlFlush2 ctrlSetBackgroundColor [0, 0, 0, 1];
            _ctrlFlush2 ctrlSetTextColor [1, 1, 1, 1];
        };
    };
};

// relabel the active list, 86004, so y-tubing rows read clearly.
// persisted markers render blank from ACM, so they become "[Empty Bag]".
// the clamped y saline, ACME_SalineY, renders blank, so it becomes "Saline (<vol>ml) [Y]", and the volume drops
// 50 per flush.
// blood and fresh blood on a y'd line get a " [Y]" suffix, so it is clearly part of the y set.
private _ctrlActive = _display displayCtrl 86004;
if (!isNull _ctrlActive) then {
    private _selBags = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags", []];
    // an attention pulse for empty-bag rows. it is the same red pulse at about 1.1 hz that the flush line button
    // uses, so an empty bag visually flags itself the same way the flush prompt does.
    private _emptyPulse = 0.5 + (0.5 * sin (360 * ((diag_tickTime * 1.1) % 1)));
    private _emptyCol = [1, 0.20 + (0.20 * _emptyPulse), 0.20 + (0.20 * _emptyPulse), 0.65 + (0.35 * _emptyPulse)];
    for "_r" from 0 to ((lbSize _ctrlActive) - 1) do {
        private _vi = _ctrlActive lbValue _r;
        if (_vi >= 0 && {_vi < count _selBags}) then {
            (_selBags select _vi) params [["_bType", ""], ["_bVol", 0]];
            private _cur = _ctrlActive lbText _r;
            // default this row to normal white text. the empty-bag branches below override it to pulsing red. this reset is
            // what stops a refilled slot, which was empty and now holds a live unit, from keeping the red color.
            _ctrlActive lbSetColor [_r, [1, 1, 1, 1]];
            if (_bType isEqualTo "ACME_Empty") then {
                if (_cur isNotEqualTo "[Empty Blood Bag] [Y]") then { _ctrlActive lbSetText [_r, "[Empty Blood Bag] [Y]"]; };
                _ctrlActive lbSetColor [_r, _emptyCol];  // pulsing red, meaning this needs attention.
            } else {
                if (_bType isEqualTo "ACME_EmptySaline") then {
                    if (_cur isNotEqualTo "[Empty Saline Bag] [Y]") then { _ctrlActive lbSetText [_r, "[Empty Saline Bag] [Y]"]; };
                    _ctrlActive lbSetColor [_r, _emptyCol];  // pulsing red, meaning this needs attention.
                } else {
                if (_bType isEqualTo "ACME_SalineY" || {_lineYd && {_bType isEqualTo "Saline"}}) then {
                    private _want = format ["Saline (%1ml) [Y]", round _bVol];
                    if (_cur isNotEqualTo _want) then { _ctrlActive lbSetText [_r, _want]; };
                    // the y saline reserve ships no artwork, so give it the ACE saline-bag icon, like blood.
                    _ctrlActive lbSetPicture [_r, "\z\ace\addons\medical_treatment\ui\salineIV_ca.paa"];
                } else {
                    if (_bType in ["Blood", "FreshBlood"]) then {
                        // the live remaining ml, like the saline row. it rewrites the "(<num>ml)" in ACM's label, because ACM shows the
                        // static original volume on this list and never ticks it down.
                        private _open = _cur find "(";
                        private _mlAt = _cur find "ml)";
                        if (_open >= 0 && {_mlAt > _open}) then {
                            private _newLabel = (_cur select [0, _open + 1]) + (str (round _bVol)) + (_cur select [_mlAt]);
                            if (_newLabel isNotEqualTo _cur) then { _ctrlActive lbSetText [_r, _newLabel]; _cur = _newLabel; };
                        };
                        if (_lineYd && {(_cur find "[Y]") < 0}) then {
                            _ctrlActive lbSetText [_r, _cur + " [Y]"];
                            _cur = _cur + " [Y]";
                        };
                        // warmed blood reads orange with a [warmed] tag, and normal, cold blood stays white. the row was reset to white
                        // above, so the orange is re-asserted here every refresh. otherwise the reset strips the color the earlier
                        // pass set and warmed units look identical to cold.
                        if (_targetPatient getVariable ["ACME_warmedBlood", false]) then {
                            if ((_cur find " [Warmed]") < 0) then {
                                _ctrlActive lbSetText [_r, _cur + " [Warmed]"];
                            };
                            _ctrlActive lbSetColor [_r, [1, 0.55, 0.13, 1]];  // warm orange.
                        };
                    };
                };
                };
            };
        };
    };
};
// cooler blood surfaced in the available-bags list on the right.
// units sitting in the blood cooler of the medic appear as selectable [cooled] rows, so they can be spiked and
// hung without a manual unload first, and spiking one pulls it from the cooler, in
// fn_transfusionspikeoradd. ACM rebuilds this list only on inventory and target events, so we keep our rows in
// sync and touch the list only when they differ. that means no per-frame churn, and ACM's own rows and their
// selection are never altered.
// lbdata is ACM's own "class|fluidData" plus a trailing "|COOLER" marker. ACM's params read the first two fields
// only, so addbag still works, and our code keys on the marker. fresh-blood units carry per-unit ids that ACM
// lists dynamically and are not surfaced here, so those still need a manual unload.
private _coolerScanDue = diag_tickTime >= (_display getVariable ["ACME_txCoolerNextScan", 0]);
if (!isNull _ctrlRightList
    && {_coolerScanDue}
    && {missionNamespace getVariable ["ACME_coolerAutoUse", true]}
    && {!isNil "ACM_circulation_Fluids_Array"}) then {
    // Carried/nearby cooler contents are not a frame-time signal. nearestObjects plus inventory scans were being
    // repeated by the UI refresher; cache that discovery cadence independently from button/list repaint cadence.
    _display setVariable ["ACME_txCoolerNextScan", diag_tickTime + 0.75];
    private _store = ACE_player getVariable ["ACME_coolerStore", createHashMap];
    // only blood inside a cooler the medic is carrying is usable here. a cooler that has been dropped or handed off
    // keeps its blood in the store, preserved, and must not appear as spikeable until it is carried again.
    private _heldNow = ((uniformItems ACE_player) + (vestItems ACE_player) + (backpackItems ACE_player)) select { (_x find "ACME_BloodCooler_") == 0 };
    private _want = createHashMap;
    {
        if (_x in _heldNow) then {
            private _contents = _store get _x;
            if (_contents isEqualType []) then {
                {
                    private _bc = _x param [0, ""];
                    if (_bc find "ACM_BloodBag_" == 0) then { _want set [_bc, (_want getOrDefault [_bc, 0]) + 1]; };
                } forEach _contents;
            };
        };
    } forEach (keys _store);

    // also count blood inside any cooler box within reach, about 6 m. a box you are dragging rides just in front of
    // you, one set down by a casualty is a step away, and one in your vehicle is a couple of meters off. so a
    // nearby open box feeds the transfusion menu exactly like carrying a cooler does, and spiking pulls from it in
    // fn_transfusionspikeoradd.
    {
        private _bx = _x;
        {
            if ((_x find "ACM_BloodBag_") == 0) then { _want set [_x, (_want getOrDefault [_x, 0]) + 1]; };
        } forEach (itemCargo _bx);
    } forEach (nearestObjects [ACE_player, ["ACME_BloodCoolerBox_CSWB1U", "ACME_BloodCoolerBox_CSWB2U", "ACME_BloodCoolerBox_CSWB4U"], 6]);

    // a signature of class and count, so we rebuild on a cooler-content change. the row-count check catches an ACM
    // list rebuild that wiped our rows. fn_transfusionspikeoradd sets the sig to "__force__" after a pull to force
    // this.
    private _wantKeys = keys _want; _wantKeys sort true;
    private _wantSig = "";
    { _wantSig = _wantSig + format ["%1:%2;", _x, _want get _x]; } forEach _wantKeys;
    private _ourRows = [];
    for "_r" from 0 to ((lbSize _ctrlRightList) - 1) do {
        if ((((_ctrlRightList lbData _r) splitString "|") param [2, ""]) == "COOLER") then { _ourRows pushBack _r; };
    };
    private _lastSig = uiNamespace getVariable ["ACME_coolerRowSig", ""];

    if (_wantSig != _lastSig || {(count _ourRows) != (count _wantKeys)}) then {
        for "_i" from ((count _ourRows) - 1) to 0 step -1 do { _ctrlRightList lbDelete (_ourRows select _i); };
        {
            private _bc = _x;
            private _fi = ACM_circulation_Fluids_Array find _bc;
            if (_fi >= 0) then {
                private _data = ACM_circulation_Fluids_Array_Data select _fi;
                private _cfg = configFile >> "CfgWeapons" >> _bc;
                private _nm = [getText (_cfg >> "displayName"), getText (_cfg >> "shortName")] select (isText (_cfg >> "shortName"));
                private _row = _ctrlRightList lbAdd (_nm + " [Cooled]");
                _ctrlRightList lbSetData [_row, format ["%1|%2|COOLER", _bc, _data]];
                _ctrlRightList lbSetPicture [_row, getText (_cfg >> "picture")];
                _ctrlRightList lbSetColor [_row, [0.45, 0.72, 1, 1]];  // light blue, matching the [cooled] active rows.
                _ctrlRightList lbSetTooltip [_row, format ["In cooler: %1", _want get _bc]];
            };
        } forEach _wantKeys;
        uiNamespace setVariable ["ACME_coolerRowSig", _wantSig];
    };
};

// used bags surfaced in the available list, 86005.
// a bag pulled off a y leg, in fn_transfusionpullbag, is parked in ACME_usedBags on the medic with its exact
// remaining volume. each one is surfaced here as a distinct orange "[Used]" row showing the remaining ml, so a
// partially spent bag can be re-hung later, because fn_transfusionspikeoradd reads the |USED marker and the id.
// it is signature-driven, so it rebuilds only when the used set changes, and the row-count check re-adds our
// rows after an ACM list rebuild wipes them.
if (!isNull _ctrlRightList) then {
    private _usedBags = ACE_player getVariable ["ACME_usedBags", []];
    private _usedSig = "";
    { _usedSig = _usedSig + format ["%1:%2;", (_x param [0, ""]), round (_x param [2, 0])]; } forEach _usedBags;
    private _ourUsedRows = [];
    for "_r" from 0 to ((lbSize _ctrlRightList) - 1) do {
        if ((((_ctrlRightList lbData _r) splitString "|") param [2, ""]) == "USED") then { _ourUsedRows pushBack _r; };
    };
    private _lastUsedSig = uiNamespace getVariable ["ACME_usedRowSig", ""];
    if (_usedSig != _lastUsedSig || {(count _ourUsedRows) != (count _usedBags)}) then {
        for "_i" from ((count _ourUsedRows) - 1) to 0 step -1 do { _ctrlRightList lbDelete (_ourUsedRows select _i); };
        {
            _x params [["_id", ""], ["_type", ""], ["_remVol", 0], ["_accessType", 0], ["_bloodType", -1], ["_origVol", 1000], ["_name", ""]];
            private _row = _ctrlRightList lbAdd (format ["%1 %2 mL [Used]", _name, round _remVol]);
            _ctrlRightList lbSetData [_row, format ["%1|usedbag|USED|%2", _type, _id]];
            _ctrlRightList lbSetColor [_row, [1, 0.55, 0.1, 1]];  // strong orange, distinct from the cooler blue and the y amber.
            _ctrlRightList lbSetTooltip [_row, format ["Used bag: %1 mL remaining of %2 mL. Hang to re-use.", round _remVol, round _origVol]];
        } forEach _usedBags;
        uiNamespace setVariable ["ACME_usedRowSig", _usedSig];
    };
};

// prepared iv sets surfaced in the overlay list, 86145.
// the rows show the label of each stored set, and lbdata carries the set id, read by hang set in
// fn_transfusionspikeoradd into fn_hangpreparedset. sets tied to a different casualty are hidden, because a set
// pulled off one patient can only go back on that patient, and untied sets, which is every freshly built set,
// show for everyone. it is signature-driven, so it rebuilds only when the shown set list changes, and
// fn_togglepreparedsets, build and hang set the sig to "__force__" to force it.
if (!isNull _ctrlSetsList) then {
    private _sets = ACE_player getVariable ["ACME_preparedIVSets", []];
    private _tgtNet = if (isNull _targetPatient) then { "" } else { netId _targetPatient };
    private _shown = [];
    {
        private _tied = _x param [5, ""];
        if (_tied == "" || {_tied == _tgtNet}) then { _shown pushBack [_x param [0, ""], _x param [6, ""]]; };
    } forEach _sets;
    private _wantSig = str _shown;
    // rebuild on a signature change, or when the displayed row count does not match what should show. the row-count
    // fallback, the same guard the cooler and used-bag rows use, catches the intermittent case where sets do not
    // appear until you leave and re-enter the prepared list. if a rebuild was ever missed, the next pass reconciles
    // it instead of waiting for a mode toggle to force the signature.
    private _wantRows = (count _shown) max 1;  // an empty set list still shows the one "No prepared IV sets" row.
    if (_wantSig != (uiNamespace getVariable ["ACME_preparedRowSig", ""]) || {(lbSize _ctrlSetsList) != _wantRows}) then {
        private _oldSel = lbCurSel _ctrlSetsList;
        lbClear _ctrlSetsList;
        if (_shown isEqualTo []) then {
            private _i = _ctrlSetsList lbAdd "No prepared IV sets";
            _ctrlSetsList lbSetData [_i, ""];
            _ctrlSetsList lbSetColor [_i, [0.8, 0.8, 0.8, 0.6]];
        } else {
            {
                _x params ["_sid", "_slabel"];
                private _i = _ctrlSetsList lbAdd _slabel;
                _ctrlSetsList lbSetData [_i, _sid];
                _ctrlSetsList lbSetTooltip [_i, _slabel];
                if ((_slabel find "[Cooled]") >= 0) then { _ctrlSetsList lbSetColor [_i, [0.45, 0.72, 1, 1]]; };
            } forEach _shown;
            if (_oldSel < 0 || {_oldSel >= (count _shown)}) then { _oldSel = 0; };
            _ctrlSetsList lbSetCurSel _oldSel;
        };
        uiNamespace setVariable ["ACME_preparedRowSig", _wantSig];
    };
};

// temporary diagnostic. it reached the end without aborting.
