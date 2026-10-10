// this repaints the selection highlight for a list or menu screen. the selection is the unified index selidx,
// spanning the list rows, 0 to n-1, and then the four bottom-strip buttons, n to n+3.
// the color model, which is consistent across the whole ventilator:
// hover, or selected, meaning the cursor is on a non-editable item, is a light blue background with dark blue text.
// active, or editing, which is only for editable fields such as the BPM and VTi, is a dark blue background with
// light blue text.
// the list, menu and strip items are not editable, so they only ever use the hover state.
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _dlg) exitWith {};
private _n = uiNamespace getVariable ["ACME_vent_listCount", 0];
private _selIdx = uiNamespace getVariable ["ACME_vent_selIdx", 0];
private _rowIdc = [87781,87782,87783,87784,87785,87786];
private _screen = uiNamespace getVariable ["ACME_vent_screen", ""];
private _simple = ((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])});

// the shared hover colors.
private _hoverBg  = [0, 0.988, 0.992,1];  // light blue.
private _hoverTxt = [0, 0, 0.996,1];  // dark blue, lifted from 0.03, 0.10, 0.30, which read as black on the light-blue background.
// the active and editing colors, inverted. they are used on the value row of the o2 screen while the dial is
// changing it, so it matches the edit state of the BPM field exactly.
private _activeBg  = [0, 0, 0.996,1];
private _activeTxt = [0.70,0.88,1,1];
private _o2Editing = (uiNamespace getVariable ["ACME_vent_screen", ""]) == "o2" && {uiNamespace getVariable ["ACME_vent_editingFio2", false]};
// on the ALERTS screen the row currently being dialled gets the same active treatment as an editing BPM or vt
// field, so it is unmistakable which value the dial is about to change.
private _alertEditRow = if ((uiNamespace getVariable ["ACME_vent_screen", ""]) in ["alerts","alerts2"]) then {uiNamespace getVariable ["ACME_vent_editingAlert", -1]} else {-1};
if ((uiNamespace getVariable ["ACME_vent_screen", ""]) == "params") then { _alertEditRow = uiNamespace getVariable ["ACME_vent_editingParam", -1]; };
if ((uiNamespace getVariable ["ACME_vent_screen", ""]) == "ie" && {uiNamespace getVariable ["ACME_vent_editingIE", false]}) then { _alertEditRow = 0; };
if ((uiNamespace getVariable ["ACME_vent_screen", ""]) == "peep" && {uiNamespace getVariable ["ACME_vent_editingPeep", false]}) then { _alertEditRow = 0; };

// the value fields. if this screen split its rows into a label and a value, see fn_ventpanelvaluefields, the
// highlight belongs on the value and nowhere else. the label is printed on the device and stays printed, and the
// number is the only thing you are about to change, so the number is the only thing that should light. it is also
// how you find a value fast in a dark, shaking cabin: your eye goes to the lit block rather than to a row it then
// has to parse.
private _fields = uiNamespace getVariable ["ACME_vent_valFields", []];
private _hasFields = (count _fields) > 0;

// the rows: the hover state on the selected row, a light blue background with dark blue text, and normal
// otherwise. it is painted out to the selection count rather than the row-control count, because custom layouts,
// such as the 7-slot weight grid, register more value fields than there are row controls, and every one of them
// must take its turn under the cursor.
for "_i" from 0 to (_n - 1) do {
    private _c = if (_i < 6) then { _dlg displayCtrl (_rowIdc select _i) } else { controlNull };

    // does this slot have a value field? a menu row on a value screen, with no number, still highlights whole, because
    // there is nothing else on it to highlight.
    private _fld = if (_hasFields && {_i < (count _fields)}) then { _fields select _i } else { controlNull };
    private _target = if (isNull _fld) then { _c } else { _fld };
    if (!isNull _target) then {

        // if the value carries the highlight, the label must be explicitly cleared, or a stale highlight from a previous
        // screen would sit under it forever. controls do not forget.
        if (!isNull _fld && {!isNull _c}) then {
            _c ctrlSetBackgroundColor [0,0,0,0];
            _c ctrlSetTextColor [0.72,0.76,0.80,1];  // a printed label: dimmer than a value, and never selected.
        };

        private _automatic = _simple && {_screen == "params" || {_screen == "alerts" && {_i == 2}}};
        _target ctrlEnable (!_automatic);
        if (_automatic) then {
            _target ctrlSetBackgroundColor [0,0,0,0];
            _target ctrlSetTextColor [0.55,0.58,0.62,1];
        } else { if (_i == _selIdx) then {
            if (_o2Editing || {_i == _alertEditRow}) then {
                _target ctrlSetBackgroundColor _activeBg;
                _target ctrlSetTextColor _activeTxt;
            } else {
                _target ctrlSetBackgroundColor _hoverBg;
                _target ctrlSetTextColor _hoverTxt;
            };
        } else {
            _target ctrlSetBackgroundColor [0,0,0,0];
            _target ctrlSetTextColor [0.92,0.92,0.92,1];
        }; };
    };
};

// the strip: on list screens the strip is the visible nav chevrons, in order. highlight the selected one.
private _navList = uiNamespace getVariable ["ACME_vent_navList", []];
private _stripSel = _selIdx - _n;  // -1 or less means on a row, and 0 and above means which visible chevron.
{
    _x params ["", "_hlIdc"];
    private _b = _dlg displayCtrl _hlIdc;
    if (_forEachIndex == _stripSel) then {
        _b ctrlSetBackgroundColor _hoverBg;
    } else {
        _b ctrlSetBackgroundColor [0,0,0,0];
    };
} forEach _navList;
