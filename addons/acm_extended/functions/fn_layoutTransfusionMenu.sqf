/* B274: final presentation of existing native transfusion controls, without replacing their actions. */
disableSerialization;
params [["_display", findDisplay 86000]];
if (isNull _display || {!isNull (findDisplay 86200)} || {!isNull (findDisplay 84000)}) exitWith {};

private _uiW = safeZoneW min (safeZoneH * 1.7777778);
private _uiX = safeZoneX + ((safeZoneW - _uiW) / 2);
private _fontH = safeZoneH * 0.020;
private _moveBusy = (missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Move_Active", false])
    || {missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Move_Active_Moving", false]};

// Captured native anchors stay immutable. The managed flag prevents the legacy controller's intermediate
// rectangles from being written every tick; only this final presentation is allowed to move managed controls.
_display setVariable ["ACME_txLayoutManaged", true];
_display setVariable ["ACME_txLayoutWriting", true];

private _ensure = {
    params ["_idc", "_class", "_text"];
    private _ctrl = _display displayCtrl _idc;
    if (isNull _ctrl) then {
        _ctrl = _display ctrlCreate [_class, _idc];
        if (_class != "ACME_TransfusionInlineDetails") then {_ctrl ctrlSetText _text;};
    };
    if (_class == "ACME_TransfusionCaption") then {_ctrl ctrlEnable false;};
    _ctrl
};
private _bagActions = [86170,"ACME_TransfusionActionButton","Bag Actions >"] call _ensure;
private _lineDetails = [86171,"ACME_TransfusionInlineDetails",""] call _ensure;
private _infActions = [86172,"ACME_TransfusionActionButton","Infusion Actions >"] call _ensure;
private _bagBackdrop = [86173,"ACME_TransfusionCaption",""] call _ensure;
private _infBackdrop = [86174,"ACME_TransfusionCaption",""] call _ensure;
private _infEmpty = [86176,"ACME_TransfusionCaption","No infusions at this access"] call _ensure;
private _preparedEmpty = [86177,"ACME_TransfusionCaption","No prepared infusions"] call _ensure;
private _fluidEmpty = [86178,"ACME_TransfusionCaption","No fluids at this access"] call _ensure;

if !(_display getVariable ["ACME_txLayoutHooks", false]) then {
    _display setVariable ["ACME_txLayoutHooks", true];
    _display setVariable ["ACME_txActionMenu", ""];
    {
        _x params ["_ctrl", "_menu", "_pane"];
        _ctrl setVariable ["ACME_txActionMenuName", _menu];
        _ctrl setVariable ["ACME_txPane", _pane];
        _ctrl ctrlAddEventHandler ["ButtonClick", {
            params ["_ctrl"];
            private _parent = ctrlParent _ctrl;
            private _menu = _ctrl getVariable ["ACME_txActionMenuName", ""];
            _parent setVariable ["ACME_txActivePane", _ctrl getVariable ["ACME_txPane", "transfusion"]];
            _parent setVariable ["ACME_txActionMenu", if ((_parent getVariable ["ACME_txActionMenu", ""]) == _menu) then {""} else {_menu}];
            [_parent] call ACME_fnc_layoutTransfusionMenu;
        }];
    } forEach [[_bagActions,"bag","transfusion"],[_infActions,"infusion","infusion"]];
    // Closing a local popover never replays the control action. Its config handler remains the single
    // treatment/move/remove entry point, including the native Move -> Place operation.
    {
        private _ctrl = _display displayCtrl _x;
        if (!isNull _ctrl) then {
            _ctrl ctrlAddEventHandler ["ButtonClick", {
                params ["_ctrl"];
                // Config action / ButtonClick ordering varies between native controls. Retain the hidden-list
                // selection context until both have run, then dismiss only the local presentation next frame.
                [{
                    params ["_parent"];
                    if (!isNull _parent) then {
                        _parent setVariable ["ACME_txActionMenu", ""];
                        [_parent] call ACME_fnc_layoutTransfusionMenu;
                    };
                },[ctrlParent _ctrl]] call CBA_fnc_execNextFrame;
            }];
        };
    } forEach [86007,86146,86120,86147,86134,86148,86132,86133,86149];
    // Returning from Inventory or the body map to a popover action restores its owning pane before
    // the native handler resolves selection. No treatment action is bound to these focus hooks.
    {
        _x params ["_ids", "_pane"];
        {
            private _ctrl = _display displayCtrl _x;
            if (!isNull _ctrl) then {
                _ctrl setVariable ["ACME_txPane", _pane];
                {
                    _ctrl ctrlAddEventHandler [_x, {
                        params ["_ctrl"];
                        (ctrlParent _ctrl) setVariable ["ACME_txActivePane", _ctrl getVariable ["ACME_txPane", "transfusion"]];
                    }];
                } forEach ["MouseEnter","MouseButtonDown","SetFocus"];
            };
        } forEach _ids;
    } forEach [[[86007,86146,86120,86147,86134,86148],"transfusion"],[[86132,86133,86149,86131],"infusion"]];
};

if !(_display getVariable ["ACME_txStylesReady", false]) then {
    _display setVariable ["ACME_txStylesReady", true];
    {
        private _ctrl = _display displayCtrl _x;
        if (!isNull _ctrl) then {
            _ctrl ctrlSetFont "RobotoCondensed";
            _ctrl ctrlSetFontHeight _fontH;
            _ctrl ctrlSetTextColor [1,1,1,1];
            _ctrl ctrlSetBackgroundColor [0,0,0,1];
        };
    } forEach [86006,86007,86146,86120,86147,86121,86122,86131,86132,86133,86134,86141,86142,86148,86149];
    {
        private _ctrl = _display displayCtrl _x;
        if (!isNull _ctrl) then {
            _ctrl ctrlSetFont "RobotoCondensed";
            _ctrl ctrlSetFontHeight (safeZoneH * 0.019);
            _ctrl ctrlSetBackgroundColor [0,0,0,0.75];
        };
    } forEach [86004,86005,86127,86129,86145];
};

private _place = {
    params ["_idc", "_x", "_y", "_w", "_h"];
    private _ctrl = _display displayCtrl _idc;
    if (!isNull _ctrl) then {
        [_ctrl,"position",[_uiX + _uiW * _x,safeZoneY + safeZoneH * _y,_uiW * _w,safeZoneH * _h]] call ACME_fnc_transfusionUiSet;
    };
};
// The entire BodyBackground rect, overlays, and exact-site hotspots are deliberately untouched. They share
// their existing KeepAspect square and letterboxing transform across every medical menu.
{
    _x call _place;
} forEach [
    [86002,0.350,0.177,0.300,0.031],
    [86003,0.673,0.193,0.160,0.030],
    [86037,0.838,0.193,0.033,0.030],
    [86006,0.125,0.188,0.212,0.029],
    [86004,0.137,0.228,0.200,0.230],
    [86128,0.125,0.538,0.212,0.029],
    [86129,0.125,0.575,0.212,0.187],
    [86131,0.125,0.778,0.212,0.033],
    [86172,0.125,0.819,0.212,0.033],
    [86144,0.673,0.232,0.202,0.034],
    [86005,0.673,0.279,0.202,0.235],
    [86145,0.673,0.279,0.202,0.235],
    [86130,0.673,0.595,0.202,0.029],
    [86127,0.673,0.636,0.202,0.149],
    [86121,0.778,0.526,0.097,0.034],
    [86122,0.673,0.810,0.202,0.034],
    [86171,0.355,0.795,0.290,0.090],
    [86176,0.133,0.581,0.196,0.029],
    [86177,0.681,0.643,0.186,0.029],
    [86178,0.145,0.235,0.184,0.029],
    [86126,0.125,0.895,0.750,0.024]
];
private _yButton = _display displayCtrl 86142;
private _showY = !isNull _yButton && {ctrlShown _yButton};
private _preparedMode = uiNamespace getVariable ["ACME_preparedListMode", false];
if (_preparedMode || {_showY}) then {
    [86141,0.673,0.526,0.097,0.034] call _place;
    [86142,0.778,0.526,0.097,0.034] call _place;
} else {
    [86141,0.673,0.526,0.202,0.034] call _place;
};
[(_display displayCtrl 86121),"show",_preparedMode] call ACME_fnc_transfusionUiSet;

private _menu = _display getVariable ["ACME_txActionMenu", ""];
if (_moveBusy) then {_menu = "bag"; _display setVariable ["ACME_txActionMenu",_menu];};
private _ctrlFluids = _display displayCtrl 86004;
private _ctrlInfusions = _display displayCtrl 86129;
private _ctrlPrepared = _display displayCtrl 86127;
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _iv = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _site = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
private _valid = !isNull _patient && {[_patient,_part,_iv,_site] call ACME_fnc_transfusionAccessValid};
private _isY = _valid && {[_patient,_part,_iv,_site] call ACME_fnc_isYLineAccess};
private _flowing = false;
if (_valid) then {
    private _partIdx = ["head","body","leftarm","rightarm","leftleg","rightleg"] find toLowerANSI _part;
    if (_partIdx >= 0) then {
        if (_iv) then {
            private _flow = (_patient getVariable ["ACM_circulation_FluidBagsFlow_IV", []]) param [_partIdx, []];
            _flowing = _site >= 0 && {(_flow param [_site, 0]) > 0};
        } else {
            _flowing = ((_patient getVariable ["ACM_circulation_FluidBagsFlow_IO", []]) param [_partIdx, 0]) > 0;
        };
    };
};
private _status = if (_valid) then {
    format ["%1 | %2", if (_isY) then {"Y line"} else {"Established access"}, if (_flowing) then {"Open"} else {"Paused"}]
} else {"Select an established IV or IO"};
[(_display displayCtrl 86175),"text",_status] call ACME_fnc_transfusionUiSet;
[_lineDetails,"show",_valid] call ACME_fnc_transfusionUiSet;
[_bagActions,"enable",_moveBusy || {!isNull _ctrlFluids && {lbCurSel _ctrlFluids >= 0}}] call ACME_fnc_transfusionUiSet;
[_infActions,"enable",!isNull _ctrlInfusions && {lbCurSel _ctrlInfusions >= 0}] call ACME_fnc_transfusionUiSet;
// Empty sections keep their heading and a quiet nonselectable caption, rather than changing the menu layout.
{
    private _ctrl = _display displayCtrl _x;
    if (!isNull _ctrl) then {[_ctrl,"show",true] call ACME_fnc_transfusionUiSet;};
} forEach [86128,86129,86131,86130,86127];
[_infEmpty,"show",_menu != "infusion" && {isNull _ctrlInfusions || {lbSize _ctrlInfusions == 0}}] call ACME_fnc_transfusionUiSet;
[_preparedEmpty,"show",isNull _ctrlPrepared || {lbSize _ctrlPrepared == 0}] call ACME_fnc_transfusionUiSet;
[_fluidEmpty,"show",_menu != "bag" && {isNull _ctrlFluids || {lbSize _ctrlFluids == 0}}] call ACME_fnc_transfusionUiSet;
{
    private _ctrl = _display displayCtrl _x;
    if (!isNull _ctrl) then {
        _ctrl ctrlSetFontHeight (safeZoneH * 0.021);
        _ctrl ctrlSetTextColor [1,1,1,1];
        _ctrl ctrlSetBackgroundColor [0,0,0,0];
    };
} forEach [86128,86130];

// Stop remains above Fluids. Prime/Flush belongs beside Bag Actions for the selected access.
private _service = _display displayCtrl 86143;
private _hasService = !isNull _service && {ctrlShown _service};
if (_hasService) then {
    [86170,0.125,0.478,0.100,0.033] call _place;
    [86143,0.237,0.478,0.100,0.033] call _place;
} else {
    [86170,0.125,0.478,0.212,0.033] call _place;
};

[_ctrlFluids,"show",_menu != "bag"] call ACME_fnc_transfusionUiSet;
[_ctrlInfusions,"show",_menu != "infusion"] call ACME_fnc_transfusionUiSet;
private _rate = _display displayCtrl 86126;
if (!isNull _rate) then {_rate ctrlSetFontHeight (safeZoneH * 0.017);};
[(_display displayCtrl 86163),"show",isNull _rate || {!ctrlShown _rate}] call ACME_fnc_transfusionUiSet;
[_bagActions,"text",if (_menu == "bag") then {"< Bag Actions"} else {"Bag Actions >"}] call ACME_fnc_transfusionUiSet;
[_infActions,"text",if (_menu == "infusion") then {"< Infusion Actions"} else {"Infusion Actions >"}] call ACME_fnc_transfusionUiSet;
_bagBackdrop ctrlSetBackgroundColor [0.09,0.09,0.09,1];
_infBackdrop ctrlSetBackgroundColor [0.09,0.09,0.09,1];
[86173,0.128,0.228,0.206,0.234] call _place;
[86174,0.128,0.593,0.206,0.142] call _place;
[_bagBackdrop,"show",_menu == "bag"] call ACME_fnc_transfusionUiSet;
[_infBackdrop,"show",_menu == "infusion"] call ACME_fnc_transfusionUiSet;
{
    private _ctrl = _display displayCtrl _x;
    if (!isNull _ctrl) then {
        [_x,0.141,0.234 + _forEachIndex * 0.037,0.180,0.031] call _place;
        [_ctrl,"show",_menu == "bag"] call ACME_fnc_transfusionUiSet;
    };
} forEach [86007,86146,86147,86134,86148,86120];
{
    private _ctrl = _display displayCtrl _x;
    if (!isNull _ctrl) then {
        [_x,0.141,0.603 + _forEachIndex * 0.039,0.180,0.033] call _place;
        [_ctrl,"show",_menu == "infusion"] call ACME_fnc_transfusionUiSet;
    };
} forEach [86132,86133,86149];
// Cuff meters are created by the existing pressure painter. Keep them attached to the final button rectangle
// and hidden together with their collapsed popover, without introducing another state refresh worker.
{
    _x params ["_buttonIDC","_barIDC"];
    private _button = _display displayCtrl _buttonIDC;
    private _bar = _display displayCtrl _barIDC;
    if (!isNull _button && {!isNull _bar}) then {
        private _pos = ctrlPosition _button;
        private _height = (4 * pixelH) max ((_pos select 3) * 0.12);
        [_bar,"position",[_pos select 0,(_pos select 1)+(_pos select 3)-_height,_pos select 2,_height]] call ACME_fnc_transfusionUiSet;
        [_bar,"show",ctrlShown _button] call ACME_fnc_transfusionUiSet;
    };
} forEach [[86148,86151],[86149,86152]];
[_display] call ACME_fnc_updateTransfusionLineDetails;
_display setVariable ["ACME_txLayoutWriting", false];
