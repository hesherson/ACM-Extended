/*
 * Exact transfusion access-site interaction layer.
 * Uses the same measured alpha bounds as the Narc Box, but maps them onto ACM's KeepAspect body image so the
 * click target is the catheter/IO artwork, including EJ. It also annotates each occupied line by fluid type.
 */
disableSerialization;
private _display = findDisplay 86000;
if (isNull _display) exitWith {};
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
if (isNull _patient) exitWith {};

// Any stock IV/IO overlay has the same BodyBackground rect. IDC 86010 is always constructed even when hidden.
private _ref = _display displayCtrl 86010;
if (isNull _ref) exitWith {};
(ctrlPosition _ref) params ["_outerX", "_outerY", "_outerW", "_outerH"];

// body_background.paa and every access overlay are square canvases. RscPictureKeepAspect letterboxes the square
// inside the authored box, so map the measured UVs onto the actual square pixels, not the outer control box.
private _drawW = _outerW;
private _drawH = _outerW * (pixelH / pixelW);
if (_drawH > _outerH) then {
    _drawH = _outerH;
    _drawW = _outerH * (pixelW / pixelH);
};
private _drawX = _outerX + ((_outerW - _drawW) / 2);
private _drawY = _outerY + ((_outerH - _drawH) / 2);

private _imageByNativeIDC = createHashMapFromArray [
    [70130,86020],[70131,86021],[70132,86022],
    [70133,86023],[70134,86024],[70135,86025],
    [70140,86026],[70141,86027],[70142,86028],
    [70143,86029],[70144,86030],[70145,86031],
    [70136,86011],[70137,86012],[70146,86013],[70147,86014],[70113,86010]
];
private _ejImageByNativeIDC = createHashMapFromArray [[7290020,7290120],[7290021,7290121]];
private _geometry = call ACME_fnc_skSiteGeometry;
private _selectedPart = toLowerANSI (missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""]);
private _selectedIV = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _selectedSite = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
private _bagsMap = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];

private _fluidAbbrev = {
    params ["_type"];
    switch (toLowerANSI _type) do {
        case "blood";
        case "freshblood": {"B"};
        case "plasma": {"P"};
        case "saline";
        case "acme_saliney": {"NS"};
        case "plasmalyte": {"PL"};
        case "mannitol": {"Mtol"};
        case "hts";
        case "hts3": {"HTS"};
        case "magnesium": {"MgSO₄"};
        case "esmolol": {"Esm"};
        case "fbtk": {"FBTK"};
        default {
            private _s = _type;
            if ((count _s) > 5) then {_s select [0,5]} else {_s}
        };
    };
};

private _partLabel = {
    params ["_part"];
    if (!isNil "ACM_core_fnc_getBodyPartString") exitWith {[_part] call ACM_core_fnc_getBodyPartString};
    _part
};

private _placedLabels = [];
{
    _x params ["_key", "_part", "_site", "_nativeImageIDC", "_unusedInputIDC", "_uv"];
    private _isIO = _site < 0;
    private _isEJ = _nativeImageIDC in [7290020,7290021];
    private _has = if (_isIO) then {
        [_patient, _part, 0] call ACM_circulation_fnc_hasIO
    } else {
        [_patient, _part, 0, _site] call ACM_circulation_fnc_hasIV
    };

    private _imageIDC = if (_isEJ) then {_ejImageByNativeIDC getOrDefault [_nativeImageIDC, -1]} else {_imageByNativeIDC getOrDefault [_nativeImageIDC, -1]};
    private _image = if (_imageIDC >= 0) then {_display displayCtrl _imageIDC} else {controlNull};
    if (_isEJ && {isNull _image}) then {
        _image = _display ctrlCreate ["RscPictureKeepAspect", _imageIDC];
    };
    if (_isEJ && {!isNull _image}) then {
        // Build the PBO path from the literal backslash character. This guarantees one separator per component
        // even if a source/preprocessor path has been escaped by an external build step.
        [_image,"text",[_site] call ACME_fnc_ejTexturePath] call ACME_fnc_transfusionUiSet;
        [_image,"position",[_outerX,_outerY,_outerW,_outerH]] call ACME_fnc_transfusionUiSet;

        [_image,"show",_has] call ACME_fnc_transfusionUiSet;
    };

    _uv params ["_u", "_v", "_uw", "_uh"];
    // The measured alpha bounds remain authoritative, with a small physical-pixel margin so the catheter is easy
    // to click without turning the entire limb into a hidden button. Every established site remains independently
    // selectable, including both EJs and each individual peripheral-IV position.
    private _padX = 6 * pixelW;
    private _padY = 6 * pixelH;
    private _hx = _drawX + (_u * _drawW) - _padX;
    private _hy = _drawY + (_v * _drawH) - _padY;
    private _hw = (_uw * _drawW) + (2 * _padX);
    private _hh = (_uh * _drawH) + (2 * _padY);

    private _hotIDC = 86900 + _forEachIndex;
    private _hot = _display displayCtrl _hotIDC;
    if (isNull _hot) then {
        _hot = _display ctrlCreate ["ACME_EJTransfusionHotspot", _hotIDC];
        _hot ctrlAddEventHandler ["MouseEnter", {
            params ["_ctrl"];
            _ctrl setVariable ["ACME_TX_Hover", true];
            _ctrl ctrlSetBackgroundColor [0.20,0.65,0.20,0.22];
        }];
        _hot ctrlAddEventHandler ["MouseExit", {
            params ["_ctrl"];
            _ctrl setVariable ["ACME_TX_Hover", false];
            _ctrl ctrlSetBackgroundColor (if (_ctrl getVariable ["ACME_TX_Selected",false]) then {[1,1,1,0.08]} else {[0,0,0,0]});
        }];
        _hot ctrlAddEventHandler ["ButtonClick", {
            params ["_ctrl"];
            (_ctrl getVariable ["ACME_TX_Access", ["",true,-1]]) call ACME_fnc_selectTransfusionAccess;
        }];
    };
    _hot setVariable ["ACME_TX_Access", [_part, !_isIO, _site]];
    private _hotRect = [_hx,_hy,_hw,_hh];
    if ((_hot getVariable ["ACME_TX_Rect",[]]) isNotEqualTo _hotRect) then {
        _hot setVariable ["ACME_TX_Rect",_hotRect];
        [_hot,"position",_hotRect] call ACME_fnc_transfusionUiSet;
    };
    private _siteText = if (_isEJ) then {(["Left EJ","Right EJ"] select (_site max 0 min 1))} else {
        private _n = [_part, _site max 0, _isIO] call ACME_fnc_skSiteName;
        format ["%1 - %2", [_part] call _partLabel, _n]
    };
    if ((_hot getVariable ["ACME_TX_Tooltip",""]) != _siteText) then {
        _hot ctrlSetTooltip _siteText; _hot setVariable ["ACME_TX_Tooltip",_siteText];
    };
    if ((_hot getVariable ["ACME_TX_Visible",-1]) isNotEqualTo _has) then {
        _hot setVariable ["ACME_TX_Visible",_has]; [_hot,"enable",_has] call ACME_fnc_transfusionUiSet; [_hot,"show",_has] call ACME_fnc_transfusionUiSet;
    };

    private _selected = _has && {(_selectedPart == _part)} && {(_selectedIV == (!_isIO))} && {if (_isIO) then {true} else {_selectedSite == _site}};
    _hot setVariable ["ACME_TX_Selected",_selected];
    private _hover = _hot getVariable ["ACME_TX_Hover", false];
    _hot ctrlSetBackgroundColor (if (_hover) then {[0.20,0.65,0.20,0.22]} else {if (_selected) then {[1,1,1,0.08]} else {[0,0,0,0]}});
    if (_has && {!isNull _image}) then {
        // Same interaction language as Body Map: the real device artwork is the target. Selected/hovered = 100%;
        // other established sites stay slightly dim so selection is obvious without changing hue.
        private _col = if (_selected || {_hover}) then {[0.20,0.65,0.20,1]} else {[0.20,0.65,0.20,0.42]};
        [_image,"color",_col] call ACME_fnc_transfusionUiSet;
    };

    // Fluid shorthand sits beside the true access site, not at a generic limb location.
    private _abbr = [];
    if (_has) then {
        private _arr = _bagsMap getOrDefault [_part, []];
        {
            private _bType = _x param [0, ""];
            private _remaining = _x param [1, 0];
            private _bSite = _x param [3, -1];
            private _bIV = _x param [4, true];
            private _match = (_remaining > 0.01) && {if (_isIO) then {!_bIV} else {_bIV && {_bSite == _site}}};
            if (_match && {!(_bType in ["ACME_Empty","ACME_EmptySaline"])}) then {
                private _a = [_bType] call _fluidAbbrev;
                private _uid = _x param [8, ""];
                private _drugs = (_patient getVariable ["ACME_infusion_BagMedications", []]) select {(_x param [23, ""]) == _uid && {_uid != ""}};
                if (_drugs isNotEqualTo []) then {_a = (_drugs apply {[_x select 11] call ACME_fnc_infusionName}) joinString "/";};
                if (_a != "") then {_abbr pushBackUnique _a;};
            };
        } forEach _arr;
    };
    private _labelIDC = 87000 + _forEachIndex;
    private _label = _display displayCtrl _labelIDC;
    if (isNull _label) then {
        _label = _display ctrlCreate ["RscText", _labelIDC];
        _label ctrlSetBackgroundColor [0.043,0.082,0.188,0.82];
        [_label,"color",[0.94,0.91,0.82,1]] call ACME_fnc_transfusionUiSet;
        [_label,"enable",false] call ACME_fnc_transfusionUiSet;
    };
    private _showLabel = _has && {!(_abbr isEqualTo [])};
    if (_showLabel) then {
        private _labelH = (_drawH * 0.035) max (14 * pixelH);
        private _text = _abbr joinString "+";
        _label ctrlSetFontHeight (_labelH * 0.68);
        [_label,"text",_text] call ACME_fnc_transfusionUiSet;
        private _labelW = ((ctrlTextWidth _label) + 8 * pixelW) max (22 * pixelW);
        _labelW = _labelW min (_drawW * 0.18);
        private _left = (_hx + _hw / 2) < (_drawX + _drawW / 2);
        private _rect = [[_hx,_hy,_hw,_hh],[_labelW,_labelH],[_outerX,_outerY,_outerW,_outerH],_placedLabels,3 * pixelH,_left] call ACME_fnc_transfusionTagRect;
        if (_rect isEqualTo []) then {_showLabel = false;} else {
            _placedLabels pushBack _rect;
            [_label,"position",_rect] call ACME_fnc_transfusionUiSet;

        };
    };
    [_label,"show",_showLabel] call ACME_fnc_transfusionUiSet;
} forEach _geometry;

// Keep ACM's header descriptive now that there is no route toggle and the artwork itself is the selector.
private _ctrlSelectionText = _display displayCtrl 86002;
if (!isNull _ctrlSelectionText && {_selectedIV}) then {
    if (_selectedPart == "head") then {
        _ctrlSelectionText ctrlSetText format ["Head - IV (%1)", ["Left EJ","Right EJ"] select ((_selectedSite max 0) min 1)];
    } else {
        if (_selectedPart in ["leftarm","rightarm","leftleg","rightleg"] && {missionNamespace getVariable ["ACME_hc_descriptors", false]}) then {
            private _name = [_selectedPart, ((_selectedSite max 0) min 2), false] call ACME_fnc_skSiteName;
            if (_name != "") then {_ctrlSelectionText ctrlSetText format ["%1 - IV (%2)", [_selectedPart] call _partLabel, _name];};
        };
    };
};
