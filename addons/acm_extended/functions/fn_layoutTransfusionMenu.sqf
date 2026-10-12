/* B276: rounded native surfaces and card presentation of existing native transfusion controls, without replacing their actions. */
disableSerialization;
params [["_display", findDisplay 86000]];
if (isNull _display || {!isNull (findDisplay 86200)} || {!isNull (findDisplay 84000)}) exitWith {};

private _uiW = safeZoneW min (safeZoneH * 1.7777778);
private _uiX = safeZoneX + ((safeZoneW - _uiW) / 2);
private _fontH = safeZoneH * 0.018;
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
private _piggyback = [86194,"ACME_TransfusionActionButton","Piggyback Fluid"] call _ensure;
private _warmer = [86195,"ACME_TransfusionActionButton","Add Fluid Warmer"] call _ensure;
private _warmerNotice = [86196,"ACME_TransfusionCaption","This is your only fluid warmer. Add it?"] call _ensure;
private _warmerYes = [86197,"ACME_TransfusionActionButton","Yes"] call _ensure;
private _warmerNo = [86198,"ACME_TransfusionActionButton","No"] call _ensure;
private _bloodType = [86199,"ACME_TransfusionCenteredCaption","Blood Type: ???"] call _ensure;
private _accessKind = [86210,"ACME_TransfusionAccessCaption",""] call _ensure;
private _accessIcon = [86211,"RscPictureKeepAspect",""] call _ensure;
private _spikeDropdown = [86212,"ACME_TransfusionActionButton","v"] call _ensure;
private _warming = [86213,"ACME_TransfusionCaption",""] call _ensure;

if !(_display getVariable ["ACME_txLayoutHooks", false]) then {
    _display setVariable ["ACME_txLayoutHooks", true];
    _display setVariable ["ACME_txActionMenu", ""];
    _display setVariable ["ACME_txSpikeDropdown", false];
    {
        _x params ["_ctrl", "_menu", "_pane"];
        _ctrl setVariable ["ACME_txActionMenuName", _menu];
        _ctrl setVariable ["ACME_txPane", _pane];
        _ctrl ctrlAddEventHandler ["ButtonClick", {
            params ["_ctrl"];
            private _parent = ctrlParent _ctrl;
            uiNamespace setVariable ["ACME_lineWarmerConfirm",[]];
            private _menu = _ctrl getVariable ["ACME_txActionMenuName", ""];
            _parent setVariable ["ACME_txActivePane", _ctrl getVariable ["ACME_txPane", "transfusion"]];
            _parent setVariable ["ACME_txActionMenu", if ((_parent getVariable ["ACME_txActionMenu", ""]) == _menu) then {""} else {_menu}];
            [_parent] call ACME_fnc_layoutTransfusionMenu;
        }];
    } forEach [[_bagActions,"bag","transfusion"],[_infActions,"infusion","infusion"]];
    _piggyback ctrlAddEventHandler ["ButtonClick", { ["start"] call ACME_fnc_piggybackWorkflow; }];
    {
        _x params ["_button","_operation"];
        _button setVariable ["ACME_warmerOperation",_operation];
        _button ctrlAddEventHandler ["ButtonClick", {
            params ["_ctrl"];
            private _ctx = [_ctrl getVariable ["ACME_txPane","transfusion"]] call ACME_fnc_getSelectedActiveBagContext;
            if (_ctx isEqualTo []) exitWith {};
            private _physical = ((_ctx select 0) getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_ctx select 1,[]];
            private _uid = (_physical param [_ctx select 2,[]]) param [8,""];
            [_ctrl getVariable ["ACME_warmerOperation","add"],_uid] call ACME_fnc_lineWarmerRequest;
            [ctrlParent _ctrl] call ACME_fnc_layoutTransfusionMenu;
        }];
    } forEach [[_warmer,"add"],[_warmerYes,"yes"],[_warmerNo,"no"]];
    _spikeDropdown ctrlAddEventHandler ["ButtonClick", {
        params ["_ctrl"];
        private _display = ctrlParent _ctrl;
        _display setVariable ["ACME_txSpikeDropdown",!(_display getVariable ["ACME_txSpikeDropdown",false])];
        [_display] call ACME_fnc_layoutTransfusionMenu;
    }];
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
    _display displayAddEventHandler ["Unload",{uiNamespace setVariable ["ACME_lineWarmerConfirm",[]];}];
    _display displayAddEventHandler ["KeyDown",{
        params ["_display","_key"];
        if (_key == 1) then {
            uiNamespace setVariable ["ACME_lineWarmerConfirm",[]];
            ["cancel"] call ACME_fnc_piggybackWorkflow;
        };
        false
    }];
    // An unrelated treatment cancels intent only; the staged bag stays in provider custody.
    {
        private _ctrl = _display displayCtrl _x;
        if (!isNull _ctrl) then {_ctrl ctrlAddEventHandler ["ButtonClick",{
            uiNamespace setVariable ["ACME_lineWarmerConfirm",[]];
            ["cancel"] call ACME_fnc_piggybackWorkflow;
        }];};
    } forEach [86006,86007,86146,86120,86147,86134,86148,86132,86133,86149,86131,86142,86950,86951];
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
    // Grey corner surfaces are background-only. Native buttons keep every existing action,
    // tooltip, disabled state and keyboard focus; these hooks update decoration only.
    {
        private _ctrl = _display displayCtrl _x;
        if (!isNull _ctrl) then {
            _ctrl ctrlSetBackgroundColor [0,0,0,0];
            _ctrl ctrlAddEventHandler ["MouseEnter",{params ["_ctrl"];_ctrl setVariable ["ACME_txSkinHover",true];[ctrlParent _ctrl] call ACME_fnc_layoutTransfusionMenu;}];
            _ctrl ctrlAddEventHandler ["MouseExit",{params ["_ctrl"];_ctrl setVariable ["ACME_txSkinHover",false];[ctrlParent _ctrl] call ACME_fnc_layoutTransfusionMenu;}];
            _ctrl ctrlAddEventHandler ["SetFocus",{params ["_ctrl"];_ctrl setVariable ["ACME_txSkinFocus",true];[ctrlParent _ctrl] call ACME_fnc_layoutTransfusionMenu;}];
            _ctrl ctrlAddEventHandler ["KillFocus",{params ["_ctrl"];_ctrl setVariable ["ACME_txSkinFocus",false];[ctrlParent _ctrl] call ACME_fnc_layoutTransfusionMenu;}];
        };
    } forEach [86006,86007,86146,86147,86134,86148,86120,86121,86122,86131,86132,
        86133,86149,86141,86142,86143,86144,86170,86172,86194,86195,86197,86198,86212];
    {
        private _ctrl = _display displayCtrl _x;
        if (!isNull _ctrl) then {
            _ctrl ctrlSetFont "RobotoCondensed";
            _ctrl ctrlSetFontHeight _fontH;
            _ctrl ctrlSetTextColor [1,1,1,1];
            _ctrl ctrlSetBackgroundColor [0,0,0,0];
        };
    } forEach [86006,86007,86146,86120,86147,86121,86122,86131,86132,86133,86134,86141,86142,86148,86149];
    {
        private _ctrl = _display displayCtrl _x;
        if (!isNull _ctrl) then {
            _ctrl ctrlSetFont "RobotoCondensed";
            _ctrl ctrlSetFontHeight (safeZoneH * 0.019);
            _ctrl ctrlSetBackgroundColor [0,0,0,0];
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
    [86002,0.350,0.744,0.300,0.030],
    [86199,0.350,0.126,0.300,0.024],
    [86210,0.382,0.777,0.236,0.024],
    [86211,0.363,0.777,0.019,0.024],
    [86213,0.141,0.441,0.184,0.027],
    [86161,0.673,0.164,0.202,0.027],
    [86003,0.673,0.193,0.160,0.030],
    [86037,0.838,0.193,0.033,0.030],
    [86006,0.125,0.188,0.212,0.029],
    [86004,0.137,0.228,0.200,0.210],
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
    [86171,0.355,0.812,0.290,0.078],
    [86176,0.133,0.581,0.196,0.029],
    [86177,0.681,0.643,0.186,0.029],
    [86178,0.145,0.235,0.184,0.029],
    [86126,0.355,0.892,0.290,0.024]
];
private _yButton = _display displayCtrl 86142;
private _showY = !isNull _yButton && {ctrlShown _yButton};
private _preparedMode = uiNamespace getVariable ["ACME_preparedListMode", false];
if (_preparedMode) then {
    [86141,0.673,0.526,0.097,0.034] call _place;
    [86121,0.778,0.526,0.097,0.034] call _place;
    [_spikeDropdown,"show",false] call ACME_fnc_transfusionUiSet;
} else {
    if (_showY) then {
        // Blood defaults to the native Y-set action; the native Spike Bag path stays in its dropdown.
        [86142,0.673,0.526,0.169,0.034] call _place;
        [86212,0.847,0.526,0.028,0.034] call _place;
        [86141,0.673,0.564,0.202,0.031] call _place;
        [_spikeDropdown,"show",true] call ACME_fnc_transfusionUiSet;
        [(_display displayCtrl 86141),"show",_display getVariable ["ACME_txSpikeDropdown",false]] call ACME_fnc_transfusionUiSet;
    } else {
        [86141,0.673,0.526,0.202,0.034] call _place;
        [_spikeDropdown,"show",false] call ACME_fnc_transfusionUiSet;
    };
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
// The selected location belongs under the familiar body map; no repeated line-status header/footer.
{[(_display displayCtrl _x),"show",false] call ACME_fnc_transfusionUiSet;} forEach [86162,86163,86175];
private _knownType = [ACE_player,_patient] call ACME_fnc_knownBloodType;
[_bloodType,"text",format ["Blood Type: %1",_knownType]] call ACME_fnc_transfusionUiSet;
private _partIdx = ["head","body","leftarm","rightarm","leftleg","rightleg"] find toLowerANSI _part;
private _accessText = "";
private _iconClass = "";
if (_valid && {_partIdx >= 0}) then {
    private _location = if (_part == "head") then {["Left EJ","Right EJ"] param [_site,"EJ"]} else {
        [_part] call ACM_core_fnc_getBodyPartString
    };
    [(_display displayCtrl 86002),"text",_location] call ACME_fnc_transfusionUiSet;
    if (_iv) then {
        private _type = ((_patient getVariable ["ACM_circulation_IV_Placement",[]]) param [_partIdx,[]]) param [_site,0];
        private _gauge = switch (_type) do {case 2:{14};case 5:{18};case 6:{20};default {16};};
        private _marks = _patient getVariable ["ACME_IV_Marks",[]];
        private _mi = _marks findIf {
            (_x param [4,""]) == "hub"
                && {(if ((_x param [0,""]) == "ej") then {"head"} else {_x param [0,""]}) == _part}
                && {([_x param [10,""]] call ACME_fnc_ivSiteIndex) == _site}
        };
        private _accessory = if (_mi >= 0) then {(_marks select _mi) param [15,[]]} else {[]};
        private _fieldGauge = _accessory param [5,0];
        _accessText = if (_fieldGauge > 0) then {format ["%1G field IV",_fieldGauge]} else {format ["%1G IV",_gauge]};
        if (_accessory param [0,false]) then {_accessText = _accessText + " + extension";};
        _iconClass = format ["ACM_IV_%1g",if (_fieldGauge > 0) then {_fieldGauge} else {_gauge}];
    } else {
        private _type = (_patient getVariable ["ACM_circulation_IO_Placement",[]]) param [_partIdx,0];
        _accessText = ["EZ-IO","FAST1 IO"] select (_type == 4);
        _iconClass = ["ACM_IO_EZ","ACM_IO_FAST"] select (_type == 4);
    };
};
[_accessKind,"text",_accessText] call ACME_fnc_transfusionUiSet;
[_accessKind,"show",_valid] call ACME_fnc_transfusionUiSet;
[_accessIcon,"text",getText (configFile >> "CfgWeapons" >> _iconClass >> "picture")] call ACME_fnc_transfusionUiSet;
[_accessIcon,"show",_valid] call ACME_fnc_transfusionUiSet;
if (_valid) then {
    // Center the combined native icon + short descriptor so the icon stays beside the actual text.
    private _textW = ((ctrlTextWidth _accessKind) max (_uiW * 0.032)) min (_uiW * 0.225);
    private _iconW = safeZoneH * 0.022 * (pixelW / pixelH);
    private _gap = 4 * pixelW;
    private _startX = _uiX + _uiW * 0.5 - ((_textW + _iconW + _gap) / 2);
    [_accessIcon,"position",[_startX,safeZoneY + safeZoneH * 0.777,_iconW,safeZoneH * 0.024]] call ACME_fnc_transfusionUiSet;
    [_accessKind,"position",[_startX + _iconW + _gap,safeZoneY + safeZoneH * 0.777,_textW,safeZoneH * 0.024]] call ACME_fnc_transfusionUiSet;
};
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
        _ctrl ctrlSetFontHeight (safeZoneH * 0.020);
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
[(_display displayCtrl 86163),"show",false] call ACME_fnc_transfusionUiSet;
[_bagActions,"text",if (_menu == "bag") then {"< Bag Actions"} else {"Bag Actions >"}] call ACME_fnc_transfusionUiSet;
[_infActions,"text",if (_menu == "infusion") then {"< Infusion Actions"} else {"Infusion Actions >"}] call ACME_fnc_transfusionUiSet;

[86173,0.128,0.228,0.206,0.249] call _place;
[86174,0.128,0.593,0.206,0.181] call _place;
[_bagBackdrop,"show",_menu == "bag"] call ACME_fnc_transfusionUiSet;
[_infBackdrop,"show",_menu == "infusion"] call ACME_fnc_transfusionUiSet;
{
    private _ctrl = _display displayCtrl _x;
    if (!isNull _ctrl) then {
        [_x,0.141,0.233 + _forEachIndex * 0.028,0.180,0.024] call _place;
        [_ctrl,"show",_menu == "bag"] call ACME_fnc_transfusionUiSet;
    };
} forEach [86007,86146,86147,86134,86148,86120,86194];
private _bagCtx = ["transfusion"] call ACME_fnc_getSelectedActiveBagContext;
private _canPiggyback = _valid && {!(_bagCtx isEqualTo [])}
    && {[_patient,_part,_iv,_site,_bagCtx param [3,""],false] call ACME_fnc_piggybackEligible};
[_piggyback,"enable",_canPiggyback] call ACME_fnc_transfusionUiSet;
private _warmerPane = if (_menu == "infusion") then {"infusion"} else {"transfusion"};
private _warmerCtx = [_warmerPane] call ACME_fnc_getSelectedActiveBagContext;
private _warmerUID = "";
if (_warmerCtx isNotEqualTo []) then {
    private _physical = (_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]];
    _warmerUID = (_physical param [_warmerCtx select 2,[]]) param [8,""];
};
{_x setVariable ["ACME_txPane",_warmerPane];} forEach [_warmer,_warmerYes,_warmerNo];
([_patient,_part,_iv,_site,_warmerUID,ACE_player] call ACME_fnc_lineWarmerActionState)
    params ["_warmerShow","_warmerInstalled","_warmerAvailable","_lastWarmer","_confirmWarmer"];
_warmer setVariable ["ACME_warmerOperation",["add","remove"] select _warmerInstalled];
[_warmer,"text",["Add Fluid Warmer","Remove Fluid Warmer"] select _warmerInstalled] call ACME_fnc_transfusionUiSet;
[_warmer,"enable",_warmerInstalled || {_warmerAvailable > 0}] call ACME_fnc_transfusionUiSet;
if (_menu == "infusion") then {
    [86195,0.141,0.725,0.180,0.033] call _place;
    [86196,0.141,0.719,0.180,0.026] call _place;
    [86197,0.141,0.747,0.087,0.025] call _place;
    [86198,0.234,0.747,0.087,0.025] call _place;
} else {
    [86195,0.141,0.430,0.180,0.029] call _place;
    [86196,0.141,0.425,0.180,0.026] call _place;
    [86197,0.141,0.452,0.087,0.025] call _place;
    [86198,0.234,0.452,0.087,0.025] call _place;
};
[_warmer,"show",_menu in ["bag","infusion"] && {_warmerShow} && {!_confirmWarmer}] call ACME_fnc_transfusionUiSet;
{[_x,"show",_menu in ["bag","infusion"] && {_confirmWarmer}] call ACME_fnc_transfusionUiSet;} forEach [_warmerNotice,_warmerYes,_warmerNo];
// Warming appears on its fluid card and inline details; suppress the former duplicate caption.
[_warming,"show",false] call ACME_fnc_transfusionUiSet;
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
// B276: bounded predeclared decorations. Paint uses the existing 0.25 s worker;
// it never creates controls, edits list records, moves a bag or sends owner events.
private _surfaceRoot = "\x\ACM\addons\circulation\ui\transfusionmenu\surfaces\";
{
    _x params ["_buttonIDC","_skinIDC"];
    private _button = _display displayCtrl _buttonIDC;
    private _skin = _display displayCtrl _skinIDC;
    private _show = !isNull _button && {ctrlShown _button};
    [_skin,"show",_show] call ACME_fnc_transfusionUiSet;
    if (_show) then {
        private _variant = if (!ctrlEnabled _button) then {"button_disabled"} else {
            if ((_button getVariable ["ACME_txSkinHover",false]) || {_button getVariable ["ACME_txSkinFocus",false]}) then {"button_hover"} else {"button"}
        };
        private _skinRect = ctrlPosition _button;
        // Full-width buttons use a flatter texture than split actions. Choose using physical
        // pixels so interface size and ultrawide safe zones do not select the wrong shape.
        private _aspect = ((_skinRect select 2) / pixelW) / (((_skinRect select 3) / pixelH) max 1);
        if (_aspect >= 10) then {_variant = _variant + "_wide";};
        [_skin,"color",_button getVariable ["ACME_txSkinTint",[1,1,1,1]]] call ACME_fnc_transfusionUiSet;
        [_skin,"position",ctrlPosition _button] call ACME_fnc_transfusionUiSet;
        [_skin,"text",_surfaceRoot + _variant + "_ca.paa"] call ACME_fnc_transfusionUiSet;
    };
} forEach [[86006,86300],[86007,86301],[86146,86302],[86147,86303],[86134,86304],
    [86148,86305],[86120,86306],[86121,86307],[86122,86308],[86131,86309],[86132,86310],
    [86133,86311],[86149,86312],[86141,86313],[86142,86314],[86143,86315],[86144,86316],
    [86170,86317],[86172,86318],[86194,86319],[86195,86320],[86197,86321],[86198,86322],[86212,86323]];
{
    _x params ["_caption","_skinIDC","_listIDC"];
    private _skin = _display displayCtrl _skinIDC;
    private _list = _display displayCtrl _listIDC;
    private _show = ctrlShown _caption;
    [_skin,"show",_show] call ACME_fnc_transfusionUiSet;
    if (_show) then {
        private _rect = ctrlPosition _list;
        _rect set [3,safeZoneH * 0.072];
        [_skin,"position",_rect] call ACME_fnc_transfusionUiSet;
    };
} forEach [[_fluidEmpty,86370,86004],[_infEmpty,86371,86129],[_preparedEmpty,86372,86127]];
private _cardSelection = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selection_IVBags",[]];
private _detailsSurface = _display displayCtrl 86373;
[_detailsSurface,"show",_valid] call ACME_fnc_transfusionUiSet;
[_detailsSurface,"position",ctrlPosition _lineDetails] call ACME_fnc_transfusionUiSet;
{
    _x params ["_listIDC","_baseIDC"];
    private _list = _display displayCtrl _listIDC;
    if (!isNull _list) then {
        (ctrlPosition _list) params ["_lx","_ly","_lw","_lh"];
        private _rowH = safeZoneH * 0.072;
        private _rows = lbSize _list;
        // Native scrollbar values are read-only. Cards show only complete visible rows;
        // partially clipped rows retain the native selection highlight and hit rectangle.
        private _scroll = ((ctrlScrollValues _list) param [0,0]) max 0 min 1;
        private _offset = _scroll * ((_rows * _rowH - _lh) max 0);
        private _first = floor (_offset / _rowH);
        for "_slot" from 0 to 3 do {
            private _row = _first + _slot;
            private _cy = _ly + _row * _rowH - _offset;
            private _card = _display displayCtrl (_baseIDC + _slot * 4);
            private _caption = _display displayCtrl (_baseIDC + _slot * 4 + 1);
            private _track = _display displayCtrl (_baseIDC + _slot * 4 + 2);
            private _fill = _display displayCtrl (_baseIDC + _slot * 4 + 3);
            private _show = ctrlShown _list && {_row < _rows} && {_cy >= _ly - pixelH}
                && {_cy + _rowH <= _ly + _lh + pixelH};
            [_card,"show",_show] call ACME_fnc_transfusionUiSet;
            private _meta = "";
            private _fraction = -1;
            private _color = [0.65,0.65,0.65,1];
            if (_show) then {
                private _selected = (lbCurSel _list) == _row;
                [_card,"position",[_lx,_cy + safeZoneH * 0.003,_lw,_rowH - safeZoneH * 0.006]] call ACME_fnc_transfusionUiSet;
                [_card,"text",_surfaceRoot + (["row","row_selected"] select _selected) + "_ca.paa"] call ACME_fnc_transfusionUiSet;
                private _cache = _list getVariable [format ["ACME_txCard_%1",_row],[]];
                private _sourceRow = _cardSelection param [_list lbValue _row,[]];
                if (_listIDC in [86004,86129] && {_cache isNotEqualTo []}
                    && {(_cache param [8,[]]) isEqualTo [_patient,_part,_iv,_site]}
                    && {(_cache param [6,""]) == (_sourceRow param [9,"__missing"])}
                    && {(_cache param [7,""]) == (_list lbText _row)}) then {
                    _cache params ["_remaining","_original","_thermal","_role","_flowing","_type"];
                    _fraction = (_remaining / (_original max 1)) max 0 min 1;
                    _meta = if (_thermal != "") then {_thermal} else {
                        if (_type in ["ACME_SalineY","ACME_EmptySaline"]) then {"Reserve Flush Saline"} else {
                            if (_role != "") then {"Piggyback " + _role} else {["Paused","Flowing"] select _flowing}
                        }
                    };
                    _color = if (_thermal find "Warming" >= 0) then {[1,0.55,0.13,1]} else {
                        if (_role != "") then {[0.79,0.73,0.89,1]} else {[0.65,0.65,0.65,1]}
                    };
                };
                if (_listIDC == 86145 && {(_list lbData _row) != ""}) then {_meta = "Ready to hang";};
                if (_listIDC == 86127 && {(_list lbValue _row) >= 0}) then {_meta = "Prepared infusion";};
                [_caption,"position",[_lx + safeZoneH * 0.054,_cy + safeZoneH * 0.048,_lw - safeZoneH * 0.060,safeZoneH * 0.017]] call ACME_fnc_transfusionUiSet;
                [_caption,"text",_meta] call ACME_fnc_transfusionUiSet;
                [_caption,"color",_color] call ACME_fnc_transfusionUiSet;
                private _trackRect = [_lx + _uiW * 0.006,_cy + _rowH - safeZoneH * 0.007,_lw - _uiW * 0.012,(2 * pixelH) max (safeZoneH * 0.0015)];
                [_track,"position",_trackRect] call ACME_fnc_transfusionUiSet;
                _trackRect set [2,(_trackRect select 2) * (_fraction max 0)];
                [_fill,"position",_trackRect] call ACME_fnc_transfusionUiSet;
            };
            [_caption,"show",_show && {_meta != ""}] call ACME_fnc_transfusionUiSet;
            [_track,"show",_show && {_fraction >= 0}] call ACME_fnc_transfusionUiSet;
            [_fill,"show",_show && {_fraction > 0}] call ACME_fnc_transfusionUiSet;
        };
    };
} forEach [[86004,86400],[86129,86420],[86005,86440],[86145,86460],[86127,86480]];
[_display] call ACME_fnc_updateTransfusionLineDetails;
_display setVariable ["ACME_txLayoutWriting", false];
