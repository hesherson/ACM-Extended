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
private _bagMedications = _patient getVariable ["ACME_infusion_BagMedications", []];

private _partLabel = {
    params ["_part"];
    if (!isNil "ACM_core_fnc_getBodyPartString") exitWith {[_part] call ACM_core_fnc_getBodyPartString};
    _part
};

private _placedLabels = [];
{
    private _siteIndex = _forEachIndex;
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

    private _outline = _display displayCtrl (87300 + _siteIndex);
    if (isNull _outline) then {
        _outline = _display ctrlCreate ["RscPictureKeepAspect",87300 + _siteIndex];
        _outline ctrlEnable false;
        [_outline,"text",format ["\acm_extended\ui\transfusion\access\%1_ca.paa",toLowerANSI _key]] call ACME_fnc_transfusionUiSet;
    };
    [_outline,"position",[_outerX,_outerY,_outerW,_outerH]] call ACME_fnc_transfusionUiSet;
    private _hotIDC = 86900 + _siteIndex;
    private _hot = _display displayCtrl _hotIDC;
    if (isNull _hot) then {
        _hot = _display ctrlCreate ["ACME_EJTransfusionHotspot", _hotIDC];
        _hot ctrlAddEventHandler ["MouseEnter", {
            params ["_ctrl"];
            _ctrl setVariable ["ACME_TX_Hover", true];
            _ctrl ctrlSetBackgroundColor [0,0,0,0];
        }];
        _hot ctrlAddEventHandler ["MouseExit", {
            params ["_ctrl"];
            _ctrl setVariable ["ACME_TX_Hover", false];
            _ctrl ctrlSetBackgroundColor [0,0,0,0];
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
    _hot ctrlSetBackgroundColor [0,0,0,0];
    [_outline,"color",if (_selected) then {[1,1,1,1]} else {[0.45,1,0.45,1]}] call ACME_fnc_transfusionUiSet;
    [_outline,"show",_has && {_selected || {_hover}}] call ACME_fnc_transfusionUiSet;
    if (_has && {!isNull _image}) then {
        // Same interaction language as Body Map: the real device artwork is the target. Selected/hovered = 100%;
        // other established sites stay slightly dim so selection is obvious without changing hue.
        private _col = if (_selected || {_hover}) then {[0.20,0.65,0.20,1]} else {[0.20,0.65,0.20,0.42]};
        [_image,"color",_col] call ACME_fnc_transfusionUiSet;
    };

    // Only bags/infusions on this exact access label it. Empty sites remain artwork only.
    private _text = if (_has) then {[_bagsMap getOrDefault [_part, []],_bagMedications,!_isIO,_site] call ACME_fnc_transfusionAccessLabel} else {""};
    private _labelIDC = 87000 + _siteIndex;
    private _label = _display displayCtrl _labelIDC;
    if (isNull _label) then {
        _label = _display ctrlCreate ["RscText", _labelIDC];
        _label ctrlSetBackgroundColor [0.055,0.055,0.055,0.94];
        _label ctrlSetFont "RobotoCondensed";
        [_label,"enable",false] call ACME_fnc_transfusionUiSet;
    };
    private _leader = _display displayCtrl (87030 + _siteIndex);
    private _tagHit = _display displayCtrl (87240 + _siteIndex);
    private _borders = [];
    for "_edge" from 0 to 3 do {_borders pushBack (_display displayCtrl (87130 + _siteIndex * 4 + _edge));};
    private _showLabel = _has && {_text != ""};
    if (_showLabel) then {
        // Reuse native line/text controls; no texture, draw loop or custom body artwork.
        if (isNull _leader) then {
            _leader = _display ctrlCreate ["RscLine", 87030 + _siteIndex];
            [_leader,"enable",false] call ACME_fnc_transfusionUiSet;
        };
        // Indexed loop keeps the site's control range intact across all four edges.
        for "_edge" from 0 to 3 do {
            if (isNull (_borders select _edge)) then {
                private _border = _display ctrlCreate ["RscText", 87130 + _siteIndex * 4 + _edge];
                [_border,"enable",false] call ACME_fnc_transfusionUiSet;
                _borders set [_edge,_border];
            };
        };
        if (isNull _tagHit) then {
            _tagHit = _display ctrlCreate ["ACME_EJTransfusionHotspot", 87240 + _siteIndex];
            _tagHit ctrlAddEventHandler ["ButtonClick", {
                params ["_ctrl"];
                (_ctrl getVariable ["ACME_TX_Access", ["",true,-1]]) call ACME_fnc_selectTransfusionAccess;
            }];
        };
        _tagHit setVariable ["ACME_TX_Access", [_part, !_isIO, _site]];
        _tagHit ctrlSetTooltip _siteText;
        private _isPiggyback = !isNil "ACME_fnc_piggybackLine"
            && {([_patient,_part,!_isIO,_site] call ACME_fnc_piggybackLine) isNotEqualTo []};
        private _tagColor = if (_isPiggyback) then {[0.79,0.73,0.89,1]} else {[0.82,0.82,0.82,1]};
        [_label,"color",_tagColor] call ACME_fnc_transfusionUiSet;
        [_leader,"color",_tagColor] call ACME_fnc_transfusionUiSet;
        {if ((_x getVariable ["ACME_TX_BorderColor",[]]) isNotEqualTo _tagColor) then {_x ctrlSetBackgroundColor _tagColor;_x setVariable ["ACME_TX_BorderColor",_tagColor];};} forEach _borders;
        private _labelH = (_drawH * 0.035) max (14 * pixelH);
        _label ctrlSetFontHeight (_labelH * 0.68);
        [_label,"text",_text] call ACME_fnc_transfusionUiSet;
        private _labelW = ((ctrlTextWidth _label) + 8 * pixelW) max (22 * pixelW);
        _labelW = _labelW min (_drawW * 0.18);
        private _left = (_hx + _hw / 2) < (_drawX + _drawW / 2);
        private _above = _isEJ || {_v < 0.35} || {!_left && {_v < 0.55}};
        private _anchor = [_hx,_hy,_hw,_hh];
        private _flagOverhang = (_drawW * 0.035) max (10 * pixelW);
        private _rect = [_anchor,[_labelW + _flagOverhang,_labelH],[_outerX,_outerY,_outerW,_outerH],_placedLabels,3 * pixelH,_left,_above] call ACME_fnc_transfusionTagRect;
        if (_rect isEqualTo []) then {_showLabel = false;} else {
            _placedLabels pushBack (+_rect); // Reserve the entire flag, including its overhang.
            if (_left) then {_rect set [0,(_rect select 0) + _flagOverhang];};
            _rect set [2,_labelW];
            [_label,"position",_rect] call ACME_fnc_transfusionUiSet;
            [_tagHit,"position",_rect] call ACME_fnc_transfusionUiSet;
            [_leader,"position",[_anchor,_rect,_left] call ACME_fnc_transfusionTagLeader] call ACME_fnc_transfusionUiSet;
            _rect params ["_tx","_ty","_tw","_th"];
            // Extend the top edge beyond the outer corner for a flag silhouette.
            {
                [(_borders select _forEachIndex),"position",_x] call ACME_fnc_transfusionUiSet;
            } forEach [[_tx - (if (_left) then {_flagOverhang} else {0}),_ty,_tw + _flagOverhang,pixelH],[_tx,_ty,pixelW,_th],[_tx,_ty + _th - pixelH,_tw,pixelH],[_tx + _tw - pixelW,_ty,pixelW,_th]];
        };
    };
    [_label,"show",_showLabel] call ACME_fnc_transfusionUiSet;
    [_leader,"show",_showLabel] call ACME_fnc_transfusionUiSet;
    [_tagHit,"show",_showLabel] call ACME_fnc_transfusionUiSet;
    [_tagHit,"enable",_showLabel] call ACME_fnc_transfusionUiSet;
    {[_x,"show",_showLabel] call ACME_fnc_transfusionUiSet;} forEach _borders;
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
