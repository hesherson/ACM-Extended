private _acmeCanvas = call ACME_fnc_uiCanvas;
_acmeCanvas params ["_uiX", "_uiY", "_uiW", "_uiH"];
private _display = findDisplay 84000;
if (isNull _display) exitWith {};

// note that the unload handler of the dialog, meaning the close sfx, the med-list restore and clearing the infusion
// context, lives in fn_skinject now, so it covers both the narc box and the infusion-prep modes and survives size
// switches. this function only repurposes the buttons of the dialog for infusion prep, and is re-applied on every
// reopen by fn_skopendraw.

private _context = missionNamespace getVariable ["ACME_infusion_pendingContext", []];
private _mode = if (_context isEqualTo []) then {"active"} else {_context select 0};

// Prep Infusion is one medication at a time, so use ACM's native syringe mover directly.
// The previous implementation borrowed the Narc Box compound layer, but that layer assumes every
// pull is finalized with Draw and advances a component floor. Prep Infusion never performs that
// component-lock step, which made release/re-grab and return-to-vial behavior diverge.
// Native Syringe_Draw already has ACME's exact physical-vial clamp in its live drag loop.
if ((uiNamespace getVariable ["ACME_SK_WasteStage", ""]) != "") then {
    [] call ACME_fnc_skWasteEnd;
};
uiNamespace setVariable ["ACME_SK_WasteStage", ""];
uiNamespace setVariable ["ACME_SK_WasteMoving", false];
missionNamespace setVariable ["ACM_circulation_SyringeDraw_Moving", false];

private _nativePlunger = _display displayCtrl 84009;
if (!isNull _nativePlunger) then {
    _nativePlunger ctrlSetEventHandler ["MouseButtonUp", "call ACM_circulation_fnc_Syringe_Draw_Move"];
    _nativePlunger ctrlSetTooltip "Click to grab the plunger, move to draw or return medication, click again to release";
};
private _topText = ["Select medication, pull syringe, then inject into active saline bag", "Select medication, pull syringe, then prep the saline bag"] select (_mode == "prepared");
private _bottomText = ["Active bag infusion mode", "Prepared bag mode - use Give Prep after inserting the IV/IO"] select (_mode == "prepared");

private _ctrlTop = _display displayCtrl 84001;
_ctrlTop ctrlSetText _topText;

private _ctrlBottom = _display displayCtrl 84002;
_ctrlBottom ctrlShow true;
_ctrlBottom ctrlSetText _bottomText;

private _buttonY = safeZoneY + (safeZoneH / 1.19);
private _buttonW = _uiW / 7.5;
private _buttonH = safeZoneH / 24;
private _leftX = _uiX + (_uiW / 2) - _buttonW - (_uiW / 70);
private _rightX = _uiX + (_uiW / 2) + (_uiW / 70);

private _ctrlDraw = _display displayCtrl 84003;
_ctrlDraw ctrlSetText "Inject Into Bag";
_ctrlDraw ctrlSetTooltip "Inject the drawn medication into the selected saline bag";
_ctrlDraw ctrlSetEventHandler ["ButtonClick", "call ACME_fnc_injectIntoBag"];
_ctrlDraw ctrlSetPosition [_leftX, _buttonY, _buttonW, _buttonH];
_ctrlDraw ctrlSetFontHeight (safeZoneH / 42);
_ctrlDraw ctrlCommit 0;

private _ctrlPush = _display displayCtrl 84004;
_ctrlPush ctrlShow false;
_ctrlPush ctrlEnable false;

// Prep Infusion has no destructive Cancel state. Every accepted injection is already physically in the bag, so the
// lower-right action is the single Done/confirm control. It finalizes the accepted mixture and returns to Transfuse.
private _ctrlCancel = _display displayCtrl 84005;
_ctrlCancel ctrlShow true;
_ctrlCancel ctrlEnable true;
_ctrlCancel ctrlSetText "Done";
_ctrlCancel ctrlSetTooltip "Confirm the medications in this bag and return to Transfuse";
_ctrlCancel ctrlSetEventHandler ["ButtonClick", "call ACME_fnc_infusionDone"];
_ctrlCancel ctrlSetPosition [_rightX, _buttonY, _buttonW, _buttonH];
_ctrlCancel ctrlSetFontHeight (safeZoneH / 42);
_ctrlCancel ctrlCommit 0;

private _ctrlSwitch = _display displayCtrl 84007;
_ctrlSwitch ctrlShow true;
_ctrlSwitch ctrlEnable true;

private _ctrlInventoryText = _display displayCtrl 84008;
_ctrlInventoryText ctrlSetText "Inventory: Self";

// The normal Body Map / page-navigation control has no meaning in infusion mode. Keep exactly one completion
// control: the bottom-right Done button above. A second Done in the navigation strip was ambiguous and made the
// old Cancel button look as though it would undo already-injected medication.
private _doneBtn = _display displayCtrl 84150;
if (!isNull _doneBtn) then {
    _doneBtn ctrlShow false;
    _doneBtn ctrlEnable false;
};
// hide the route toggle, which is body-view only, in infusion mode.
private _routeBtn = _display displayCtrl 84151;
if (!isNull _routeBtn) then { _routeBtn ctrlShow false; };

// Flushes cannot be used while preparing a bag; B59 no longer creates a Drawn list.
// Reuse that free left-column area and measure it from the actual size list.
{
    private _c = _display displayCtrl _x;
    if (!isNull _c) then {_c ctrlShow false; _c ctrlEnable false;};
} forEach [84131, 84132, 84301];
private _sizeRect = ctrlPosition (_display displayCtrl 84130);
_sizeRect params ["_listX", "_sizeY", "_listW", "_sizeH"];
private _gap = safeZoneH / 40;
private _hdrY = _sizeY + _sizeH + _gap;
private _hdrH = safeZoneH / 28;
private _bodyY = _hdrY + _hdrH;
private _bodyH = (_buttonY - _gap - _bodyY) max (safeZoneH / 20);
private _tallyHdr = _display displayCtrl 84360;
if (isNull _tallyHdr) then {_tallyHdr = _display ctrlCreate ["ACME_SK_StyledLabel", 84360];};
_tallyHdr ctrlSetPosition [_listX, _hdrY, _listW, _hdrH];
_tallyHdr ctrlSetText "Pushed into bag";
_tallyHdr ctrlSetFontHeight (safeZoneH / 44);
_tallyHdr ctrlCommit 0;
private _tallyGroup = _display displayCtrl 84362;
if (isNull _tallyGroup) then {_tallyGroup = _display ctrlCreate ["RscControlsGroup", 84362];};
_tallyGroup ctrlSetPosition [_listX, _bodyY, _listW, _bodyH];
_tallyGroup ctrlCommit 0;
private _tallyBody = _display displayCtrl 84361;
if (isNull _tallyBody) then {_tallyBody = _display ctrlCreate ["RscStructuredText", 84361, _tallyGroup];};
_tallyBody ctrlSetPosition [0, 0, _listW - _uiW / 180, _bodyH];
_tallyBody ctrlCommit 0;
[] call ACME_fnc_infusionRefreshTally;

ACM_circulation_SyringeDraw_InventorySelection = 0;
[] call ACM_circulation_fnc_Syringe_UpdateMedicationList;

// ACM's native Syringe_Draw continuous action owns the live plunger. This PFH only refreshes
// the infusion stock/tally and button state; it never writes plunger position or draw volume.
private _stockPFH = _display getVariable ["ACME_infusionStockPFH", -1];
if (_stockPFH < 0) then {
    _stockPFH = [{
        params ["_args", "_handle"];
        _args params ["_display"];
        if (isNull _display) exitWith {[_handle] call CBA_fnc_removePerFrameHandler;};
        [] call ACME_fnc_infusionDrawStock;
    }, 0.1, [_display]] call CBA_fnc_addPerFrameHandler;
    _display setVariable ["ACME_infusionStockPFH", _stockPFH];
    _display displayAddEventHandler ["Unload", {
        params ["_d"];
        private _h = _d getVariable ["ACME_infusionStockPFH", -1];
        if (_h >= 0) then {[_h] call CBA_fnc_removePerFrameHandler;};
    }];
};
[] call ACME_fnc_infusionDrawStock;
