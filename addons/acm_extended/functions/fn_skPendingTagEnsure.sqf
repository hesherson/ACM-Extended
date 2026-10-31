/* B71 ensure the MAIN Draw Syringe tag selector exists on the live ACM draw display.
 * Build order is artwork -> selector -> dropdown.  That keeps the selector above the syringe/tag art and the
 * dropdown above everything else, matching the working stored-syringe tag editor and keeping every row clickable.
 */
disableSerialization;
private _acmeCanvas = call ACME_fnc_uiCanvas;
_acmeCanvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
private _d = findDisplay 84000;
if (isNull _d || {!(_d getVariable ["ACME_SK_PendingTagReady", false])}) exitWith {false};

private _drawView = (uiNamespace getVariable ["ACME_SK_View", "syringe"]) == "syringe";

// Create the syringe tag artwork/editors first so the selector can never be hidden or intercept-blocked by them.
private _pic = _d displayCtrl 84600;
if (isNull _pic) then {
    _pic = _d ctrlCreate ["RscPicture", 84600];
    if (!isNull _pic) then {_pic ctrlShow false;};
};
for "_line" from 0 to 2 do {
    private _e = _d displayCtrl (84601 + _line);
    if (isNull _e) then {
        _e = _d ctrlCreate ["ACME_SK_TagEdit", 84601 + _line];
        if (!isNull _e) then {
            _e ctrlShow false;
            _e ctrlSetBackgroundColor [0,0,0,0];
            _e ctrlAddEventHandler ["KillFocus", {call ACME_fnc_skPendingTagCommit;}];
            _e ctrlAddEventHandler ["KeyUp", {call ACME_fnc_skPendingTagCommit;}];
        };
    };
};

// Selector is created after the artwork. B72 gives its first frame the same compact left-of-barrel geometry used
// by fn_skPendingTagRender, so there is no initial jump or overlap before the first repaint.
private _button = _d displayCtrl 84610;
if (isNull _button) then {
    _button = _d ctrlCreate ["ACME_SK_StyledButton", 84610];
    if (!isNull _button) then {
        private _size0 = uiNamespace getVariable ["ACME_SK_CurSize", 10];
        private _idx0 = ([10,5,3,1] find _size0) max 0;
        private _barrel0 = _d displayCtrl (84010 + 3 * _idx0 + 2);
        private _r0 = if (!isNull _barrel0) then {
            +(ctrlPosition _barrel0)
        } else {
            +(_d getVariable ["ACME_SK_CarouselNativeRect", [_uiX + _uiW/2 - _uiW*0.045, safeZoneY + safeZoneH*0.14, _uiW*0.09, safeZoneH*0.46]])
        };
        private _bh0 = safeZoneH / 32;
        private _gap0 = (4 * pixelW) max ((_r0 select 2) * 0.010);
        _button ctrlSetText "Select Syringe Tag";
        // B78: same compact width as Draw Syringe, same tag-face placement as the Body Map selector.
        private _textW0 = ctrlTextWidth _button;
        private _bw0 = ((_textW0 + 12*pixelW) max (safeZoneH*0.090)) min (safeZoneH*0.145);
        private _tagCenterX0 = (_r0 select 0) + (_r0 select 2)*0.36;
        private _bx0 = _tagCenterX0 - _bw0/2;
        _bx0 = (_bx0 max (_uiX + 2*pixelW)) min (_uiX + _uiW - _bw0 - 2*pixelW);
        private _by0 = (_r0 select 1) + (_r0 select 3)*0.575;
        _button ctrlSetPosition [_bx0,_by0,_bw0,_bh0];
        _button ctrlSetTextColor [1,1,1,1];
        _button ctrlSetBackgroundColor [0.05,0.05,0.05,0.82];
        _button ctrlSetTooltip "Select or change the optional tag for the syringe being prepared";
        _button ctrlShow _drawView;
        _button ctrlEnable _drawView;

        // B74: click is the ONLY toggle for the main Draw Syringe tag list. Hover must never open or close it.
        _button ctrlAddEventHandler ["ButtonClick", {
            private _d = findDisplay 84000;
            if (isNull _d || {(uiNamespace getVariable ["ACME_SK_View","syringe"]) != "syringe"}) exitWith {};
            call ACME_fnc_skPendingTagEnsure;
            private _l = _d displayCtrl 84611;
            if (isNull _l) exitWith {};
            if (ctrlShown _l) then {
                _l lbSetCurSel -1;
                _l ctrlShow false;
            } else {
                _l lbSetCurSel -1;
                _l ctrlShow true;
                ctrlSetFocus _l;
            };
        }];
        _button ctrlCommit 0;
    };
};

// Dropdown LAST: identical selection mechanics to the working stored-syringe selector, with a dedicated dark list
// class and both LBSelChanged + MouseButtonUp commit paths so one click always applies a tag.
private _list = _d displayCtrl 84611;
if (isNull _list) then {
    _list = _d ctrlCreate ["ACME_SK_TagList", 84611];
    if (!isNull _list) then {
        _list ctrlSetPosition [0,0,0,0];
        _list ctrlSetBackgroundColor [0.04,0.04,0.04,0.96];
        _list ctrlShow false;
        {
            _x params ["_id","_label"];
            private _i = _list lbAdd _label;
            _list lbSetData [_i,_id];
        } forEach [
            ["none","None - No syringe tag"],
            ["yellow_induction","Yellow - Induction agents"],
            ["orange_benzodiazepine","Orange - Benzodiazepines / sedatives"],
            ["blue_opioid","Light blue - Opioids / narcotics"],
            ["blue_stripe_reversal","Blue/white stripe - Opioid antagonists"],
            ["red_paralytic","Red - Paralytics / muscle relaxants"],
            ["red_stripe_reversal","Red/white stripe - Paralytic reversal"],
            ["violet_vasopressor","Violet - Vasopressors"],
            ["violet_stripe_hypotensive","Violet/white stripe - Hypotensive agents"],
            ["green_anticholinergic","Green - Anticholinergics"],
            ["gray_local_anesthetic","Gray - Local anesthetics"],
            ["salmon_antiemetic","Salmon / pink - Antiemetics"],
            ["white_saline_flush","White - Saline / diluent / maintenance"]
        ];
        _list ctrlAddEventHandler ["LBSelChanged", {_this call ACME_fnc_skPendingTagColor;}];
        _list ctrlAddEventHandler ["MouseButtonUp", {
            params ["_ctrl"];
            private _row = lbCurSel _ctrl;
            if (_row >= 0) then {[_ctrl,_row] call ACME_fnc_skPendingTagColor;};
        }];
    };
};

!isNull (_d displayCtrl 84610)
