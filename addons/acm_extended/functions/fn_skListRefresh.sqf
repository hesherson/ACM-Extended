/* B50: restore the Medication / Contents / Vials presentation in both Narc Box entry paths.

   The visible medication rows are now built DIRECTLY from ACME_fnc_medicationSourceRows.  IDC 84006 remains a
   hidden backing list only for ACM's draw/selection machinery.  This prevents ACM's own list refresh from making
   medication names briefly appear and then vanish, while preserving the important three-column stock UI.

   The header stays outside the scrolling group; row geometry and full-row click targets retain the established
   pre-B20 layout. B69 hides all preparation-source groups while Body Map is active, then restores them on Draw Syringe. */
disableSerialization;
private _acmeCanvas = call ACME_fnc_uiCanvas;
_acmeCanvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
private _d = findDisplay 84000;
if (isNull _d) exitWith {};
[_d] call ACME_fnc_skEpinephrineStock;
private _view = uiNamespace getVariable ["ACME_SK_View", "syringe"];
private _body = _view == "body";
private _carousel = _view == "carousel";
private _infusion = !((_d getVariable ["ACME_SK_Return", []]) isEqualTo []);
// B69: enforce preparation-page ownership on every list refresh as well as skSetView. Native ACM callbacks can
// touch their source captions while this dialog stays open; Body Map must remain visually clean until Draw Syringe.
(_d displayCtrl 84007) ctrlShow (!_infusion && {!_body});
(_d displayCtrl 84008) ctrlShow (!_body);
(_d displayCtrl 84129) ctrlShow (!_body);
(_d displayCtrl 84131) ctrlShow (!_infusion && {!_body});
private _allRows = [];
private _holder = [ACE_player] call ACME_fnc_vialHolder;

// Keep ACM's native list populated for its draw logic, but never use that transient control as the visible source.
[_d] call ACME_fnc_skMedicationSync;
private _nativeMedB50 = _d displayCtrl 84006;
if (!isNull _nativeMedB50) then {_nativeMedB50 ctrlShow false;};

private _fnReservedMl = {
    params ["_med", "_list"];
    private _reserved = 0;
    private _sel = lbCurSel _list;
    private _selected = _sel >= 0 && {(_list lbData _sel) == _med};
    private _stage = uiNamespace getVariable ["ACME_SK_WasteStage", ""];
    if (_stage in ["compound","draw"]) then {
        {
            if ((_x param [0, ""]) == _med) then {
                _reserved = _reserved + (_x param [1, 0]);
            };
        } forEach (uiNamespace getVariable ["ACME_SK_CompoundComponents", []]);
        // Locked components remain reserved when another drug is selected.
        // Only the current plunger tail belongs exclusively to the selected row.
        if (_selected) then {
            _reserved = _reserved + (((uiNamespace getVariable ["ACME_SK_WasteFill", 0]) - (uiNamespace getVariable ["ACME_SK_WasteFloorMl", 0])) max 0);
        };
    } else {
        if (_stage == "" && {_selected}) then {
            _reserved = missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0];
        };
    };
    _reserved max 0
};

private _fnStockInfo = {
    params ["_med", "_reserved", ["_physicalClass", ""]];
    if (isNull _holder) exitWith {["0.00 mL", 0, 0, 0, "x00"]};
    private _sessions = _d getVariable ["ACME_SK_VialSessions", createHashMap];
    private _bound = !((_sessions getOrDefault [_med, []]) isEqualTo []);
    private _curMl = 0; private _vials = 0; private _total = 0;
    if (_bound) then {
        (["preview", _med, _reserved, _d] call ACME_fnc_vialSession) params ["_curB","_vialsB","_totalB",""];
        _curMl = _curB; _vials = _vialsB; _total = _totalB;
    } else {
        private _pv = [_holder, _med, _reserved, _physicalClass] call ACME_fnc_vialPreview;
        _pv params ["_vialsP", "_curP", "", "_totalP"];
        _curMl = _curP; _vials = _vialsP; _total = _totalP;
    };
    // B51 display fail-safe: the physical item that created this row is indisputable stock evidence. If a stale
    // vial-session entry or a third-party concentration override ever returns an all-zero preview, recover the
    // current full-vial contents/count directly instead of painting a ghost 0.00 mL / x00 row.
    if (_physicalClass != "" && {_vials <= 0} && {_total <= 0.000001}) then {
        private _directCount = [_holder, _physicalClass] call ACME_fnc_vialItemCount;
        if (_med == "EpinephrineCardiac") then {
            _directCount = ([_holder, "ACME_Vial_EpinephrineCardiac"] call ACME_fnc_vialItemCount)
                + ([_holder, "ACM_Vial_EpinephrineCardiac"] call ACME_fnc_vialItemCount);
        };
        private _cap = [_med] call ACME_fnc_vialCapacity;
        if (_directCount > 0 && {_cap > 0}) then {
            _vials = _directCount;
            _curMl = _cap;
            _total = _directCount * _cap;
        };
    };
    private _count = str (_vials max 0);
    while {count _count < 2} do {_count = "0" + _count;};
    [format ["%1 mL", _curMl toFixed 2], _vials, _curMl, _total, "x" + _count]
};

{
    _x params ["_nativeID", "_groupID", "_kind"];
    private _list = _d displayCtrl _nativeID;
    if (isNull _list) then {continue};
    private _group = _d displayCtrl _groupID;
    if (isNull _group) then {
        // B54: a darker backdrop behind the whole section, created first so it draws under the group. It keeps
        // the original group geometry; only the background is darker.
        private _backdrop = _d ctrlCreate ["RscText", -1];
        _backdrop ctrlSetPosition (ctrlPosition _list);
        _backdrop ctrlSetBackgroundColor [0,0,0,0.55];
        _backdrop ctrlCommit 0;
        _group = _d ctrlCreate ["ACME_SK_RowGroup", _groupID];
        _group ctrlSetPosition (ctrlPosition _list);
        _group ctrlCommit 0;
        _group setVariable ["ACME_SK_Backdrop", _backdrop];
    };
    // IMPORTANT: do not recalculate or resize the group. This is the pre-B20 geometry the user requested.
    private _visible = !_carousel && {!_body};
    // B54: the native list is a hidden backing selector for every kind. Medication name, icon, contents and
    // vial count are painted together in this one group, so there is one scroll region and one scrollbar.
    _list ctrlShow false;
    if (_infusion && {_kind == "flush"}) then {_visible = false;};
    _group ctrlShow _visible;
    private _backdropB54 = _group getVariable ["ACME_SK_Backdrop", controlNull];
    if (!isNull _backdropB54) then {_backdropB54 ctrlShow _visible;};
    private _labelID = switch (_kind) do {case "flush": {84131}; default {-1};};
    if (_labelID >= 0) then {(_d displayCtrl _labelID) ctrlShow _visible;};

    private _specs = [];
    if (_kind == "medication") then {
        /* B51: bind the visible three-column row to ACM's real listbox row first.
           Live testing proved that IDC 84006 already has the correct medication labels/icons for a frame while
           B50's parallel ACME_SK_MedicationRows presentation could resolve to blank fields.  The native row is
           therefore the display-data authority; ACME's stored row metadata is only used to recover the exact
           physical vial classname and as a last-resort label/picture fallback. */
        private _metaRows = _d getVariable ["ACME_SK_MedicationRows", []];
        private _seenMedication = [];
        for "_i" from 0 to ((lbSize _list) - 1) do {
            private _data = _list lbData _i;
            if (_data == "" || {_data in _seenMedication}) then {continue};
            private _ri = _metaRows findIf {_x isEqualType [] && {(_x param [1, ""]) == _data}};
            private _meta = if (_ri >= 0) then {_metaRows select _ri} else {[]};
            private _label = _list lbText _i;
            if (_label == "" && {_meta isEqualType []}) then {_label = _meta param [0, ""];};
            if (_label == "") then {_label = _data;};
            private _picture = _list lbPicture _i;
            if (_picture == "" && {_meta isEqualType []}) then {_picture = _meta param [2, ""];};
            private _physicalClass = if (_meta isEqualType []) then {_meta param [3, ""]} else {""};
            if (_physicalClass == "") then {_physicalClass = [_data] call ACME_fnc_vialClass;};
            _seenMedication pushBack _data;
            _specs pushBack [_label, _data, 0, _picture, _physicalClass];
        };
        // If another addon empties/rebuilds the native list between ACM's update and this frame, never paint a
        // blank row. Append any authoritative carried-vial rows that were not present in the backing selector.
        {
            if !(_x isEqualType []) then {continue};
            private _data = _x param [1, ""];
            if (_data == "" || {_data in _seenMedication}) then {continue};
            private _label = _x param [0, ""];
            if (_label == "") then {_label = _data;};
            _specs pushBack [_label, _data, 0, _x param [2, ""], _x param [3, [_data] call ACME_fnc_vialClass]];
            _seenMedication pushBack _data;
        } forEach _metaRows;
    } else {
        for "_i" from 0 to ((lbSize _list) - 1) do {
            private _value = _list lbValue _i;
            private _data = _list lbData _i;
            private _item = switch (_kind) do {
                case "size": {format ["ACM_Syringe_%1", _value]};
                case "flush": {_data};
                default {""};
            };
            _specs pushBack [_list lbText _i, _data, _value, _list lbPicture _i, _item];
        };
    };

    private _rows = _group getVariable ["ACME_SK_Rows", []];
    if ((_rows findIf {
        private _ctrls = (_x select 1);
        private _at = ((_ctrls select 0) getVariable ["ACME_SK_FlashAt", -1]);
        _at >= 0 && {diag_tickTime - _at < 0.36}
    }) >= 0) then {
        _specs = _rows apply {+(_x select 0)};
    };

    private _keep = count _specs;
    if (count _rows > _keep) then {
        for "_i" from ((count _rows) - 1) to _keep step -1 do {
            {if (!isNull _x) then {ctrlDelete _x;};} forEach ((_rows select _i) select 1);
            _rows deleteAt _i;
        };
    };

    private _width = (ctrlPosition _group) select 2;
    private _rowH = safeZoneH / 20;                 // original pre-B20 row pitch
    private _innerW = _width - _uiW / 180;     // original pre-B20 width
    private _cursorY = 0;
    private _stockW = if (_kind == "medication") then {(_innerW * 0.235) max (_uiW / 45)} else {0};
    private _stockX = _innerW - _stockW;
    private _rightPad = _uiW / 420;
    private _countW = _stockW * 0.29;
    private _countX = _innerW - _rightPad - _countW;
    private _contentsW = (_countX - _stockX - (_uiW / 900)) max pixelW;

    if (_kind == "medication") then {
        // The header is outside the scrolling group, leaving every original row/hitbox in place.
        // Move only the inventory-source caption/button upward once to make room above the list.
        private _header = _group getVariable ["ACME_SK_ColumnHeader", []];
        private _headerH = safeZoneH / 32;
        if (_header isEqualTo []) then {
            private _headerBack = _d ctrlCreate ["RscText", -1];
            private _headerName = _d ctrlCreate ["RscText", -1];
            private _headerContents = _d ctrlCreate ["RscText", -1];
            private _headerCount = _d ctrlCreate ["ACME_SK_RightText", -1];
            _header = [_headerBack, _headerName, _headerContents, _headerCount];
            _group setVariable ["ACME_SK_ColumnHeader", _header];
            _headerBack ctrlSetBackgroundColor [0,0,0,0.62];
            {
                private _source = _d displayCtrl _x;
                if (!isNull _source) then {
                    private _pos = ctrlPosition _source;
                    _pos set [1, (_pos select 1) - _headerH];
                    _source ctrlSetPosition _pos;
                    _source ctrlCommit 0;
                };
            } forEach [84007,84008];
        };
        (ctrlPosition _group) params ["_groupX", "_groupY"];
        (_header select 0) ctrlSetPosition [_groupX, _groupY - _headerH, _innerW, _headerH];
        {
            _x params ["_index", "_caption", "_xPos", "_w"];
            private _ctrl = _header select _index;
            _ctrl ctrlSetFont "RobotoCondensedBold";
            _ctrl ctrlSetTextColor [1,0.96,0.84,1];
            _ctrl ctrlSetFontHeight (safeZoneH / 44 * 0.68);
            _ctrl ctrlSetText _caption;
            _ctrl ctrlSetPosition [_groupX + _xPos, _groupY - _headerH, _w, _headerH];
            _ctrl ctrlCommit 0;
            private _measured = ctrlTextWidth _ctrl;
            if (_measured > _w) then {_ctrl ctrlSetFontHeight (safeZoneH / 44 * 0.68 * (_w / _measured));};
        } forEach [[1,"Medication",_uiW / 420,_stockX - _uiW / 210],[2,"Contents",_stockX,_contentsW],[3,"Vials",_countX,_countW]];
        {_x ctrlShow _visible; _x ctrlCommit 0;} forEach _header;
    };

    {
        private _spec = _x;
        _spec params ["_label", "_data", "_value", "_picture", "_item"];
        // Last-mile B51 guard.  The row count already proves a physical source exists; never let a stale/malformed
        // presentation tuple turn that real item into an anonymous row. Recover identity and artwork directly from
        // the physical CfgWeapons class immediately before the controls are painted.
        if (_kind == "medication") then {
            if (_data == "" && {_item != ""}) then {_data = [_item] call ACME_fnc_vialMedication;};
            if (_item == "" && {_data != ""}) then {_item = [_data] call ACME_fnc_vialClass;};
            if (_item != "") then {
                private _itemCfg = configFile >> "CfgWeapons" >> _item;
                if (isClass _itemCfg) then {
                    if (_label == "") then {_label = getText (_itemCfg >> "displayName");};
                    if (_picture == "") then {_picture = getText (_itemCfg >> "picture");};
                };
            };
            if (_label == "") then {_label = if (_data != "") then {_data} else {_item};};
        };
        private _row = _rows param [_forEachIndex, []];
        if (_row isEqualTo []) then {
            private _back = _d ctrlCreate ["RscText", -1, _group];
            private _icon = _d ctrlCreate ["RscPictureKeepAspect", -1, _group];
            private _text1 = _d ctrlCreate ["RscText", -1, _group];
            private _text2 = _d ctrlCreate ["RscText", -1, _group];
            private _stock = _d ctrlCreate ["RscText", -1, _group];
            private _countText = _d ctrlCreate ["ACME_SK_RightText", -1, _group];
            {
                _x ctrlSetFont "RobotoCondensed";
                _x ctrlSetTextColor [1,1,1,1];
            } forEach [_text1, _text2];
            // B54: the numbers are the reading. Bold face for contents and vial count.
            {
                _x ctrlSetFont "RobotoCondensedBold";
                _x ctrlSetTextColor [1,1,1,1];
            } forEach [_stock, _countText];
            private _button = _d ctrlCreate ["ACME_SK_RowButton", -1, _group];
            _button ctrlAddEventHandler ["ButtonClick", {_this call ACME_fnc_skListSelect;}];
            _row = [[], [_back, _icon, _text1, _text2, _stock, _button, _countText]];
            _rows pushBack _row;
        };

        (_row select 1) params ["_back", "_icon", "_text1", "_text2", "_stock", "_button", "_countText"];
        _row set [0, +_spec];

        private _reserved = if (_kind == "medication") then {[_data, _list] call _fnReservedMl} else {0};
        private _stockInfo = if (_kind == "medication") then {[_data, _reserved, _item] call _fnStockInfo} else {["", -1, 0, 0, ""]};
        _stockInfo params ["_stockLabel", "_vialCount", "_curMl", "_totalMl", "_countLabel"];

        private _available = if (_item != "") then {([ACE_player, _item] call ACME_fnc_itemCount) > 0} else {true};
        if (_kind == "medication") then {
            // Keep the last vial row alive while its staged draw is still in the syringe, so the medic can push it back.
            _available = (_totalMl > 0.000001) || {_reserved > 0.000001};
        };

        private _iconW = if (_picture == "") then {0} else {_rowH * pixelW / pixelH};
        private _padX = if (_kind == "medication") then {_uiW / 420} else {0};
        private _textX = _iconW;
        private _textW = (_innerW - _iconW - _stockW - _padX) max (_uiW / 90);
        private _normalFont = safeZoneH / 44;
        private _font = _normalFont;
        private _minFont = _normalFont * 0.82;       // only a couple of apparent font points smaller

        _text1 ctrlSetFontHeight _font;
        _text1 ctrlSetText _label;
        _text1 ctrlSetPosition [_textX, _cursorY, _textW, _rowH];
        _text1 ctrlCommit 0;
        private _tw = ctrlTextWidth _text1;
        while {_tw > _textW && {_font > _minFont + 0.00001}} do {
            _font = (_font * 0.94) max _minFont;
            _text1 ctrlSetFontHeight _font;
            _text1 ctrlCommit 0;
            _tw = ctrlTextWidth _text1;
        };

        private _line1 = _label;
        private _line2 = "";
        private _rowThisH = _rowH;
        if (_tw > _textW) then {
            // Preserve line one's original y. Only the extra line grows downward, document-style.
            private _words = _label splitString " ";
            _line1 = "";
            private _rest = [];
            private _lineBreak = false;
            {
                if (_lineBreak) then {
                    _rest pushBack _x;
                } else {
                    private _trial = if (_line1 == "") then {_x} else {_line1 + " " + _x};
                    _text1 ctrlSetText _trial;
                    _text1 ctrlCommit 0;
                    if ((ctrlTextWidth _text1) <= _textW || {_line1 == ""}) then {
                        _line1 = _trial;
                    } else {
                        _lineBreak = true;
                        _rest pushBack _x;
                    };
                };
            } forEach _words;
            _line2 = _rest joinString " ";
            if (_line2 != "") then {_rowThisH = _rowH * 1.68;};
        };

        _back ctrlSetPosition [0, _cursorY, _innerW, _rowThisH];
        _icon ctrlSetPosition [0, _cursorY, _iconW, _rowH];
        _icon ctrlSetText _picture;
        _text1 ctrlSetFontHeight _font;
        _text1 ctrlSetText _line1;
        _text1 ctrlSetPosition [_textX, _cursorY, _textW, _rowH];
        _text1 ctrlShow true;
        if (_line2 == "") then {
            _text2 ctrlShow false;
        } else {
            _text2 ctrlSetFontHeight ((_font * 0.88) max (_minFont * 0.88));
            _text2 ctrlSetText _line2;
            _text2 ctrlSetPosition [_textX, _cursorY + (_rowH * 0.70), _textW, _rowH * 0.76];
            _text2 ctrlShow true;
        };

        if (_kind == "medication") then {
            _stock ctrlSetFontHeight (_normalFont * 0.68);
            _stock ctrlSetText _stockLabel;
            _stock ctrlSetPosition [_stockX, _cursorY, _contentsW, _rowH];
            _countText ctrlSetFontHeight (_normalFont * 0.68);
            _countText ctrlSetText _countLabel;
            _countText ctrlSetPosition [_countX, _cursorY, _countW, _rowH];
            {
                _x ctrlCommit 0;
                private _w = (ctrlPosition _x) select 2;
                private _measured = ctrlTextWidth _x;
                if (_measured > _w) then {_x ctrlSetFontHeight (_normalFont * 0.68 * (_w / _measured));};
                _x ctrlShow true;
            } forEach [_stock, _countText];
        } else {
            _stock ctrlSetText "";
            _stock ctrlShow false;
            _countText ctrlSetText "";
            _countText ctrlShow false;
        };

        _button ctrlSetPosition [0, _cursorY, _innerW, _rowThisH];
        _button ctrlSetText "";
        {_x ctrlCommit 0;} forEach [_back, _icon, _text1, _text2, _stock, _button, _countText];

        _button setVariable ["ACME_SK_Row", [_kind, _nativeID, _data, _value, _item, _back, _label]];
        _back setVariable ["ACME_SK_FlashAt", _back getVariable ["ACME_SK_FlashAt", -1]];
        _back setVariable ["ACME_SK_Available", _available];
        _back setVariable ["ACME_SK_SelectedVisual", false];
        _text1 ctrlSetTextColor (if (_available) then {[1,1,1,1]} else {[0.6,0.6,0.6,1]});
        _text2 ctrlSetTextColor (if (_available) then {[0.92,0.92,0.92,1]} else {[0.55,0.55,0.55,1]});
        {_x ctrlSetTextColor (if (_available) then {[0.96,0.98,1,1]} else {[0.50,0.50,0.50,1]});} forEach [_stock, _countText];
        _icon ctrlSetTextColor [1,1,1, if (_available) then {1} else {0.35}];
        // No new coaching. The tooltip is only the medication/item name already visible in the row.
        _button ctrlSetTooltip _label;

        private _enabled = _visible;
        if (_kind == "medication") then {
            private _compound = (uiNamespace getVariable ["ACME_SK_WasteStage", ""]) in ["compound","draw"];
            _enabled = _enabled && {if (_compound) then {!(uiNamespace getVariable ["ACME_SK_WasteMoving", false])} else {ctrlEnabled _list}};
        };
        _button ctrlEnable _enabled;

        // B54: a little more selected-row indent than the original _uiW / 360.
        private _indent = _uiW / 240;
        // Store the unindented geometry only. Refreshing a selected row must not promote the already-indented
        // position to the new baseline, which previously let controls creep horizontally over time.
        if !(_back getVariable ["ACME_SK_SelectedVisual", false]) then {
            _text1 setVariable ["ACME_SK_BasePos", ctrlPosition _text1];
            _text2 setVariable ["ACME_SK_BasePos", ctrlPosition _text2];
        };
        _text1 setVariable ["ACME_SK_SelectedIndent", _indent];
        _text2 setVariable ["ACME_SK_SelectedIndent", _indent];
        _allRows pushBack [_kind, _nativeID, _data, _value, _back, _visible, _text1, _text2, _stock, _countText];
        _cursorY = _cursorY + _rowThisH;
    } forEach _specs;

    _group setVariable ["ACME_SK_Rows", _rows];
} forEach [[84130,84300,"size"],[84132,84301,"flush"],[84006,84303,"medication"]];
_d setVariable ["ACME_SK_PulseRows", _allRows];
