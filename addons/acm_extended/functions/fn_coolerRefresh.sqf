// populate the cooler manager. the left side is a slot-bay grid built at runtime to exactly match the unit capacity
// of the cooler, where 1u gives 1 bay, 2u gives 2 and 4u gives 4, so the carry count is unmistakable at a glance.
// each bay is either filled, with blood-bag art and a unit label in warm red, or an empty outline, a cold-blue
// "OPEN BAY". the right side is the loose blood bags in inventory, as a list, for loading. there is also the
// capacity badge and the coolant readout.
// the mirror list, idc 87410, is kept off-screen so the existing load and unload code, which reads lbCurSel and
// lbdata on 87410 to know which unit is selected, keeps working unchanged: clicking a bay selects the matching
// mirror row.
private _dlg = uiNamespace getVariable ["ACME_CLR_DLG", displayNull];
if (isNull _dlg) exitWith {};
private _rows=[ACE_player] call ACME_fnc_coolerRows;
private _sid=uiNamespace getVariable ["ACME_CLR_Id",""];
private _hit=_rows findIf {(_x select 0)==_sid};
private _ready=_hit>=0;
(_dlg displayCtrl 87412) ctrlEnable _ready;
(_dlg displayCtrl 87413) ctrlEnable _ready;
if (!_ready) exitWith {(_dlg displayCtrl 87403) ctrlSetText "Waiting for cooler inventory synchronization...";};
private _state=[(_rows select _hit) select 1] call ACME_fnc_coolerAdvance;
private _class=_state select 0;
uiNamespace setVariable ["ACME_CLR_Class",_class];
private _contents=_state select 2;
_dlg setVariable ["ACME_CLR_RenderState",[_sid,_state]];
private _capacity=getNumber(configFile >> "CfgWeapons" >> _class >> "ACME_coolerCapacityMl");
private _used=0;{_used=_used+([_x select 0] call ACME_fnc_coolerBagVolume);} forEach _contents;
private _cap=(ceil (_capacity/500)) max count _contents;
private _selector=_dlg displayCtrl 87422;
_selector setVariable ["ACME_filling",true];
lbClear _selector;
{
    private _i=_selector lbAdd format ["%1 (%2)",getText(configFile >> "CfgWeapons" >> ((_x select 1) select 0) >> "displayName"),_forEachIndex+1];
    _selector lbSetData [_i,_x select 0];
} forEach _rows;
_selector lbSetCurSel _hit;
_selector setVariable ["ACME_filling",false];
(_dlg displayCtrl 87402) ctrlSetText getText(configFile >> "CfgWeapons" >> _class >> "displayName");
(_dlg displayCtrl 87421) ctrlSetText format ["%1 mL",_capacity];
private _start=_state select 1;
private _chain=getNumber(configFile >> "CfgWeapons" >> _class >> "ACME_coolerColdChainTime");
private _remaining=if (_chain<=0) then {-1} else {(_chain-(serverTime-_start)) max 0};
private _coldStr=if (_remaining<0) then {"coolant: stable"} else {
    if (_remaining>0) then {format ["coolant: %1 min left",ceil(_remaining/60)]} else {"COOLANT EXPIRED - contents warming"}
};
(_dlg displayCtrl 87403) ctrlSetText format ["%1 / %2 mL   -   %3",_used,_capacity,_coldStr];

// the mirror list, off-screen, which drives the selection and the existing load and unload code.
private _lin = _dlg displayCtrl 87410;
private _prevSel = lbCurSel _lin;
lbClear _lin;
{
    _x params ["_bc", "_wt"];
    private _i = _lin lbAdd (getText (configFile >> "CfgWeapons" >> _bc >> "displayName"));
    _lin lbSetData [_i, str _forEachIndex];
} forEach _contents;
// keep a valid selection so unload always has a target, defaulting to the first filled bay.
if (count _contents > 0) then {
    private _sel = _prevSel;
    if (_sel < 0 || {_sel >= count _contents}) then { _sel = 0; };
    _lin lbSetCurSel _sel;
};

// the inventory blood bags, the right list. it is populated first so it always shows even if the grid build below
// hits trouble, because the grid is the more complex, runtime-control part.
private _lout = _dlg displayCtrl 87411;
lbClear _lout;
// a union of every carried-item source, so a bag in any slot or container is found. items covers the uniform, vest
// and backpack contents, and the explicit container calls are belt and suspenders.
private _allItems = (items ACE_player) + (uniformItems ACE_player) + (vestItems ACE_player) + (backpackItems ACE_player);
private _seen = [];
private _added = 0;
{
    private _it = _x;
    if !(_it in _seen) then {
        _seen pushBack _it;
        if ((_it find "ACM_BloodBag_") == 0 || {(_it find "ACM_FreshBloodBag_") == 0}) then {
            private _i = _lout lbAdd (getText (configFile >> "CfgWeapons" >> _it >> "displayName"));
            _lout lbSetData [_i, _it];
            private _pic = getText (configFile >> "CfgWeapons" >> _it >> "picture");
            if (_pic != "") then { _lout lbSetPicture [_i, _pic]; };
            _added = _added + 1;
        };
    };
} forEach _allItems;

// the slot bay grid, which is the visible representation.
call ACME_fnc_coolerClearSlots;
private _grp = _dlg displayCtrl 87415;
private _gpos = ctrlPosition _grp;  // the [x,y,w,h] of the group, in screen coords.
_gpos params [["_gx", 0], ["_gy", 0], ["_gw", 0.3], ["_gh", 0.4]];

// choose a grid shape that suits the capacity: 1 gives 1x1, 2 gives 1x2 stacked, 3 gives 1x3, 4 gives 2x2, and
// anything else fills columns.
private _cols = switch (true) do {
    case (_cap <= 1): { 1 };
    case (_cap == 2): { 1 };
    case (_cap == 3): { 1 };
    case (_cap == 4): { 2 };
    default { 2 };
};
private _rows = ceil (_cap / _cols);

private _padX = _gw * 0.04;
private _padY = _gh * 0.04;
private _cellW = (_gw - (_padX * (_cols + 1))) / _cols;
private _cellH = (_gh - (_padY * (_rows + 1))) / _rows;

private _slotCtrls = [];
private _selData   = lbCurSel _lin;

for "_s" from 0 to (_cap - 1) do {
    private _cx = _s mod _cols;
    private _cy = floor (_s / _cols);
    private _bx = _gx + _padX + (_cx * (_cellW + _padX));
    private _by = _gy + _padY + (_cy * (_cellH + _padY));

    private _filled = _s < (count _contents);
    private _bag = if (_filled) then { (_contents select _s) select 0 } else { "" };

    // the bay frame, a clickable backdrop. filled is a warm dark-red panel and empty is a cold dark-blue panel.
    private _frame = _dlg ctrlCreate ["RscText", -1, _grp];
    // convert the screen coords to group-local coords, because group child positions are relative to the group
    // origin.
    _frame ctrlSetPosition [_bx - _gx, _by - _gy, _cellW, _cellH];
    if (_filled) then {
        _frame ctrlSetBackgroundColor ([[0.16, 0.04, 0.05, 0.96]] call ACME_fnc_cbColor);
    } else {
        _frame ctrlSetBackgroundColor ([[0.05, 0.09, 0.13, 0.85]] call ACME_fnc_cbColor);
    };
    _frame ctrlCommit 0;
    _slotCtrls pushBack _frame;

    // the selection highlight border for the currently selected filled bay, drawn as a slightly inset bright frame.
    if (_filled && {_s == _selData}) then {
        private _hl = _dlg ctrlCreate ["RscText", -1, _grp];
        _hl ctrlSetPosition [_bx - _gx, _by - _gy, _cellW, _cellH * 0.02 max 0.004];
        _hl ctrlSetBackgroundColor (["warning", 1] call ACME_fnc_a11yColor);
        _hl ctrlCommit 0;
        _slotCtrls pushBack _hl;
    };

    // the bay number tab, top-left.
    private _num = _dlg ctrlCreate ["RscText", -1, _grp];
    _num ctrlSetPosition [_bx - _gx + (_cellW * 0.03), _by - _gy + (_cellH * 0.03), _cellW * 0.3, _cellH * 0.18];
    _num ctrlSetText format ["%1", _s + 1];
    _num ctrlSetFont "PuristaBold";
    _num ctrlSetTextColor (if (_filled) then { ["blood", 1] call ACME_fnc_a11yColor } else { ["cool", 1] call ACME_fnc_a11yColor });
    _num ctrlSetFontHeight (_cellH * 0.16);
    _num ctrlCommit 0;
    _slotCtrls pushBack _num;

    if (_filled) then {
        // the blood-bag art, centerd, with the aspect preserved. RscPictureKeepAspect letterboxes instead of
        // stretching.
        private _pic = getText (configFile >> "CfgWeapons" >> _bag >> "picture");
        if (_pic == "") then { _pic = "\z\ace\addons\medical_treatment\ui\bloodiv_ca.paa"; };
        private _img = _dlg ctrlCreate ["RscPictureKeepAspect", -1, _grp];
        // reserve the upper band of the cell for the art, because the unit label sits below. the control is centerd and
        // keepaspect fits the texture inside without distorting it.
        _img ctrlSetPosition [_bx - _gx + (_cellW * 0.10), _by - _gy + (_cellH * 0.08), _cellW * 0.80, _cellH * 0.64];
        _img ctrlSetText _pic;
        _img ctrlSetTextColor ([[1, 1, 1, 1]] call ACME_fnc_cbColor);
        _img ctrlCommit 0;
        _slotCtrls pushBack _img;

        // the unit label, at the bottom, centerd.
        private _lbl = _dlg ctrlCreate ["RscStructuredText", -1, _grp];
        _lbl ctrlSetPosition [_bx - _gx, _by - _gy + (_cellH * 0.78), _cellW, _cellH * 0.18];
        _lbl ctrlSetStructuredText parseText format ["<t align='center' color='#f2e6e6' size='0.85'>%1</t>", getText (configFile >> "CfgWeapons" >> _bag >> "displayName")];
        _lbl ctrlCommit 0;
        _slotCtrls pushBack _lbl;
    } else {
        // the empty-bay label, centerd.
        private _lbl = _dlg ctrlCreate ["RscStructuredText", -1, _grp];
        _lbl ctrlSetPosition [_bx - _gx, _by - _gy + (_cellH * 0.40), _cellW, _cellH * 0.22];
        _lbl ctrlSetStructuredText parseText "<t align='center' color='#5a7e96' size='0.95'>OPEN BAY</t>";
        _lbl ctrlCommit 0;
        _slotCtrls pushBack _lbl;
    };

    // a clickable hotspot covering the whole bay. it selects the matching mirror row, so unload targets this unit.
    if (_filled) then {
        private _hot = _dlg ctrlCreate ["ACME_CoolerHotspot", -1, _grp];
        _hot ctrlSetPosition [_bx - _gx, _by - _gy, _cellW, _cellH];
        _hot ctrlSetText "";
        _hot setVariable ["ACME_slotIdx", _s];
        _hot ctrlAddEventHandler ["ButtonClick", {
            params ["_c"];
            private _idx = _c getVariable ["ACME_slotIdx", -1];
            private _dlg2 = uiNamespace getVariable ["ACME_CLR_DLG", displayNull];
            if (!isNull _dlg2 && {_idx >= 0}) then {
                (_dlg2 displayCtrl 87410) lbSetCurSel _idx;
                call ACME_fnc_coolerRefresh;  // redraw, to move the selection highlight.
            };
        }];
        _hot ctrlCommit 0;
        _slotCtrls pushBack _hot;
    };
};

uiNamespace setVariable ["ACME_CLR_SlotCtrls", _slotCtrls];

