/* B277: fixed native card pools. Original lists remain the single selection/workflow model.
 * Twelve cards are allocated once per display; scrolling rebinds slots, never copies or removes a bag. */
disableSerialization;
params [["_display",findDisplay 86000]];
if (isNull _display || {!isNull (findDisplay 86200)} || {!isNull (findDisplay 84000)}) exitWith {};
private _menu = _display getVariable ["ACME_txActionMenu",""];
private _preparedMode = uiNamespace getVariable ["ACME_preparedListMode",false];
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
private _endpoints = createHashMap;
private _layout = createHashMap;
private _uiW = safeZoneW min (safeZoneH * 1.7777778);
private _panes = [[86004,2,_menu != "bag"],[86129,2,_menu != "infusion"],[86005,3,!_preparedMode],[86145,3,_preparedMode],[86127,2,true]];
{
    _x params ["_idc","_capacity","_shown"];
    private _paneIndex = _forEachIndex;
    private _reactPane = _paneIndex == 0 && {_display getVariable ["ACME_reactActive",false]};
    private _list = _display displayCtrl _idc;
    if (!isNull _list) then {
        private _rect = ctrlPosition _list;
        _rect params ["_px","_py","_listW","_h"];
        private _viewportX = _px;
        // Reserve a stable gutter inside the native list viewport. Cards and
        // their text/artwork cannot reach the scrollbar, even at a narrow UI scale.
        private _railW = 3 * pixelW;
        private _railGap = (safeZoneH * 0.006 * (pixelW / pixelH)) max (5 * pixelW);
        // All panes share one physical card/content width. Wider left viewports center the same card.
        private _cardViewportW = _listW min (_uiW * 0.202);
        private _w = (_cardViewportW - _railW - _railGap) max (10 * pixelW);
        _px = _px + ((_listW - _cardViewportW) / 2);
        private _gap = safeZoneH * 0.007;
        private _rowH = (_h - _gap * (_capacity - 1)) / _capacity;
        private _offsetKey = format ["ACME_txCardOffset_%1",_idc];
        private _offset = _display getVariable [_offsetKey,0];
        private _context = [missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1],_patient];
        private _contextKey = format ["ACME_txCardContext_%1",_idc];
        if ((_display getVariable [_contextKey,[]]) isNotEqualTo _context) then {
            _display setVariable [_contextKey,_context];
            _offset = 0;
        };
        private _window = [lbSize _list,_capacity,_offset] call ACME_fnc_transfusionCardWindow;
        _offset = _window select 0;
        _display setVariable [_offsetKey,_offset];
        _layout set [_idc,[_rect,_capacity,_rowH,_offset,_shown]];
        for "_slot" from 0 to (_capacity - 1) do {
            private _groupId = 86500 + _paneIndex * 10 + _slot;
            private _group = _display displayCtrl _groupId;
            if (isNull _group) then {
                _group = _display ctrlCreate ["ACME_TransfusionCard",_groupId];
                [_group,"enable",true] call ACME_fnc_transfusionUiSet;
                private _hit = _group controlsGroupCtrl 9;
                [_hit,"enable",true] call ACME_fnc_transfusionUiSet;
                _hit ctrlAddEventHandler ["ButtonClick",{[_this select 0] call ACME_fnc_transfusionCardSelect;}];
                _hit ctrlAddEventHandler ["MouseZChanged",{[_this select 0,"wheel",_this select 1] call ACME_fnc_transfusionCardSelect;}];
                _hit ctrlAddEventHandler ["KeyDown",{[_this select 0,"key",_this select 1] call ACME_fnc_transfusionCardSelect;}];
                _hit ctrlAddEventHandler ["MouseEnter",{(ctrlParentControlsGroup (_this select 0)) setVariable ["ACME_txHover",true];[ctrlParent (_this select 0)] call ACME_fnc_updateTransfusionCards;}];
                _hit ctrlAddEventHandler ["MouseExit",{(ctrlParentControlsGroup (_this select 0)) setVariable ["ACME_txHover",false];[ctrlParent (_this select 0)] call ACME_fnc_updateTransfusionCards;}];
                _hit ctrlAddEventHandler ["SetFocus",{(ctrlParentControlsGroup (_this select 0)) setVariable ["ACME_txFocus",true];[ctrlParent (_this select 0)] call ACME_fnc_updateTransfusionCards;}];
                _hit ctrlAddEventHandler ["KillFocus",{(ctrlParentControlsGroup (_this select 0)) setVariable ["ACME_txFocus",false];[ctrlParent (_this select 0)] call ACME_fnc_updateTransfusionCards;}];
                for "_child" from 10 to 39 do {(_group controlsGroupCtrl _child) ctrlEnable false;};
            };
            private _row = (_window select 1) select _slot;
            private _identity = if (_row >= 0) then {[_list,_row] call ACME_fnc_transfusionCardIdentity} else {[]};
            private _visible = _shown && {_identity isNotEqualTo []};
            [_group,"show",_visible && {!_reactPane}] call ACME_fnc_transfusionUiSet;
            if (_visible) then {
                private _data = [_list,_row] call ACME_fnc_transfusionCardData;
                _data params ["_name","_detail","_status","_thermal","_color","_icon","_vial","_fraction",["_total",0]];
                if (_name == "") exitWith {
                    [_group,"show",false] call ACME_fnc_transfusionUiSet;
                    (_group controlsGroupCtrl 9) setVariable ["ACME_txIdentity",[]];
                };
                private _selected = (lbCurSel _list) == _row;
                private _isPib = (_name find "[PiB]") >= 0;
                private _profile = if (_selected) then {["selected","piggyback_selected"] select _isPib} else {
                    if (_group getVariable ["ACME_txFocus",false]) then {"popup"} else {if (_isPib) then {"piggyback"} else {["panel","button"] select (_group getVariable ["ACME_txHover",false])}}
                };
                private _cardRect = [_px,_py + _slot * (_rowH + _gap),_w,_rowH];
                [_group,_cardRect,_profile,0.007,!_reactPane] call ACME_fnc_transfusionRoundedFrame;
                private _hit = _group controlsGroupCtrl 9;
                _hit setVariable ["ACME_txListIDC",_idc];
                _hit setVariable ["ACME_txCapacity",_capacity];
                _hit setVariable ["ACME_txIdentity",_identity];
                _hit setVariable ["ACME_txPatient",_patient];
                private _tooltip = ([_name,_detail,_status,_thermal,_list lbTooltip _row] select {_x != ""}) joinString (toString [10]);
                if ((_hit getVariable ["ACME_txTooltip",""]) != _tooltip) then {_hit ctrlSetTooltip _tooltip;_hit setVariable ["ACME_txTooltip",_tooltip];};
                [_hit,"position",[0,0,_w,_rowH]] call ACME_fnc_transfusionUiSet;
                private _pad = _w * 0.045;
                private _iconW = safeZoneH * 0.030 * (pixelW / pixelH);
                private _textX = _pad + _iconW + _w * 0.025;
                private _vialH = (safeZoneH * 0.026) min (_rowH * 0.30);
                private _vialW = _vialH * 0.55 * (pixelW / pixelH);
                private _textW = (_w - _textX - _pad - (if (_vial != "") then {_vialW} else {0})) max 0;
                // Center the occupied caption block vertically, with one shared left edge for title/detail/status.
                // Thermal text ends at the progress track's right edge, above its graduations.
                private _hasTrack = _fraction >= 0;
                private _trackW = _w - _textX - _pad;
                private _trackY = _rowH * 0.79;
                private _captionBottom = if (_hasTrack) then {_rowH * 0.75} else {_rowH * 0.91};
                private _nameH = (safeZoneH * 0.021) min (_rowH * 0.25);
                private _detailH = (safeZoneH * 0.017) min (_rowH * 0.22);
                private _statusH = (safeZoneH * 0.015) min (_rowH * 0.20);
                private _thermalH = (safeZoneH * 0.014) min (_rowH * 0.19);
                private _contentH = _nameH + (if (_detail != "") then {_detailH} else {0}) + (if (_status != "") then {_statusH} else {0}) + (if (_thermal != "") then {_thermalH} else {0});
                private _captionTop = ((_captionBottom - _contentH) / 2) max 0;
                private _detailY = _captionTop + _nameH;
                private _statusY = _detailY + (if (_detail != "") then {_detailH} else {0});
                private _thermalW = _trackW;
                private _thermalY = _statusY + (if (_status != "") then {_statusH} else {0});
                private _metaPositions = [
                    [10,[_textX,_captionTop,_textW,_nameH]],
                    [11,[_textX,_detailY,_textW,_detailH]],
                    [12,[_textX,_statusY,_trackW,_statusH]],
                    [13,[_textX + _trackW - _thermalW,_thermalY,_thermalW,_thermalH]]
                ];
                {
                    _x params ["_child","_position"];
                    [(_group controlsGroupCtrl _child),"position",_position] call ACME_fnc_transfusionUiSet;
                } forEach (_metaPositions + [
                    [14,[_pad,_captionTop,_iconW,_contentH]],
                    [15,[_w - _pad - _vialW,_captionTop,_vialW,_vialH]],
                    [16,[_textX,_trackY,_trackW,safeZoneH * 0.0025]],
                    [17,[_textX,_trackY,_trackW * (_fraction max 0 min 1),safeZoneH * 0.0025]]
                ]);
                private _marks = [_total] call ACME_fnc_transfusionGraduations;
                for "_mark" from 0 to 10 do {
                    private _tick = _group controlsGroupCtrl (18 + _mark);
                    private _label = _group controlsGroupCtrl (29 + _mark);
                    private _shownMark = _hasTrack && {_mark < count _marks};
                    {[_x,"show",_shownMark] call ACME_fnc_transfusionUiSet;} forEach [_tick,_label];
                    if (_shownMark) then {
                        (_marks select _mark) params ["_markFraction","_markMl"];
                        private _tickX = _textX + _trackW * _markFraction;
                        [_tick,"position",[_tickX - pixelW / 2,_trackY - safeZoneH * 0.002, pixelW max 0.0004,safeZoneH * 0.006]] call ACME_fnc_transfusionUiSet;
                        // Center endpoint numbers on their ticks too. Half a label fits into the card padding;
                        // clamping them into the track would halve the 0/next and last/previous spacing.
                        private _labelW = (_trackW / ((count _marks) max 2)) min (_w * 0.15) min (2 * _pad);
                        private _labelX = _tickX - _labelW / 2;
                        [_label,"position",[_labelX,_trackY + safeZoneH * 0.004,_labelW,_rowH * 0.15]] call ACME_fnc_transfusionUiSet;
                        [_label,"text",str _markMl] call ACME_fnc_transfusionUiSet;
                    };
                };
                {[_group controlsGroupCtrl (10 + _forEachIndex),"text",_x] call ACME_fnc_transfusionUiSet;} forEach [_name,_detail,_status,_thermal];
                [(_group controlsGroupCtrl 10),"color",_color] call ACME_fnc_transfusionUiSet;
                [(_group controlsGroupCtrl 12),"color",if (_isPib) then {[0.79,0.73,0.89,1]} else {[0.66,0.66,0.66,1]}] call ACME_fnc_transfusionUiSet;
                [(_group controlsGroupCtrl 13),"color",if ((_thermal find "Warming") >= 0) then {[1,0.55,0.13,1]} else {[0.66,0.66,0.66,1]}] call ACME_fnc_transfusionUiSet;
                [(_group controlsGroupCtrl 14),"text",_icon] call ACME_fnc_transfusionUiSet;
                [(_group controlsGroupCtrl 15),"text",_vial] call ACME_fnc_transfusionUiSet;
                {[_group controlsGroupCtrl _x,"show",_fraction >= 0] call ACME_fnc_transfusionUiSet;} forEach [16,17];
                if ((_identity select 0) == "active" && {(_identity select 4) != ""}) then {_endpoints set [_identity select 4,[_cardRect select 0,(_cardRect select 1) + _rowH / 2]];};
            };
        };
        private _emptyCaption = _display displayCtrl (86600 + _paneIndex);
        if (isNull _emptyCaption) then {_emptyCaption = _display ctrlCreate ["ACME_TransfusionCaption",86600 + _paneIndex];_emptyCaption ctrlEnable false;};
        private _hasCard = false;
        for "_candidate" from 0 to ((lbSize _list) - 1) do {if (([_list,_candidate] call ACME_fnc_transfusionCardIdentity) isNotEqualTo []) exitWith {_hasCard = true;};};
        [_emptyCaption,"text",["No fluids at this access","No infusions at this access","No available fluids","No prepared IV sets","No prepared infusions"] select _paneIndex] call ACME_fnc_transfusionUiSet;
        [_emptyCaption,"position",[_px + _w * 0.04,_py + safeZoneH * 0.008,_w * 0.92,safeZoneH * 0.028]] call ACME_fnc_transfusionUiSet;
        [_emptyCaption,"show",_shown && {!_hasCard} && {!_reactPane}] call ACME_fnc_transfusionUiSet;
        // A quiet thumb communicates overflow; the full card is the wheel hit target.
        for "_piece" from 0 to 1 do {
            private _rail = _display displayCtrl (86610 + _paneIndex * 2 + _piece);
            if (isNull _rail) then {_rail = _display ctrlCreate ["RscText",86610 + _paneIndex * 2 + _piece];_rail ctrlEnable false;_rail ctrlSetBackgroundColor ([[0.20,0.20,0.20,1],[0.54,0.54,0.54,1]] select _piece);};
            private _overflow = _shown && {lbSize _list > _capacity};
            [_rail,"show",_overflow] call ACME_fnc_transfusionUiSet;
            if (_overflow) then {
                private _thumbH = (_h * _capacity / lbSize _list) max (safeZoneH * 0.025);
                private _thumbY = _py + (_h - _thumbH) * _offset / (((lbSize _list) - _capacity) max 1);
                [_rail,"position",[_viewportX + _listW - _railW,if (_piece == 0) then {_py} else {_thumbY},_railW,if (_piece == 0) then {_h} else {_thumbH}]] call ACME_fnc_transfusionUiSet;
            };
        };
        // Preserve lbValue/lbData/handlers. Only the native flat drawing is replaced by the card pool.
        [_list,"show",false] call ACME_fnc_transfusionUiSet;
    };
} forEach _panes;
_display setVariable ["ACME_txCardsReady",true];
_display setVariable ["ACME_txCardEndpoints",_endpoints];
_display setVariable ["ACME_txCardLayout",_layout];
// B294: the optional React renderer occupies this existing pane only. Keep native data,
// endpoints, rails and handlers current so fallback never reconstructs a workflow.
if (missionNamespace getVariable ["ACME_reactTransfusion",false] || {_display getVariable ["ACME_reactActive",false]}) then {
    [_display] call ACME_fnc_reactMedicalOpen;
};
if (_display getVariable ["ACME_reactActive",false]) then {
    {[_display displayCtrl _x,"show",false] call ACME_fnc_transfusionUiSet;} forEach [86500,86501,86600,86178];
};
