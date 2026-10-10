// the live screen: repaint the selection highlight for the unified dial index. a selidx of 0 is the BPM field, 1 is
// the vt field, and 2 through 5 are the four bottom strip buttons, left to right.
// the color model, consistent across the ventilator:
// hover, meaning the cursor is on a field and not editing, is a light blue background with dark blue text on the
// value.
// active, or editing, meaning an editable field is being changed, is a dark blue background with light blue text on
// the value.
// the strip buttons are not editable, so they use the hover state only.
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _dlg) exitWith {};
private _selIdx = uiNamespace getVariable ["ACME_vent_selIdx", 0];
private _edit   = uiNamespace getVariable ["ACME_vent_editing", false];
private _simple = ((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])});

// the shared colors.
private _hoverBg   = [0, 0.988, 0.992,1];  // light blue.
private _hoverTxt  = [0, 0, 0.996,1];  // dark blue, lifted from 0.03, 0.10, 0.30, which read as black on the light-blue background.
private _activeBg  = [0, 0, 0.996,1];  // dark blue, lifted so it reads blue rather than black.
private _activeTxt = [0.70,0.88,1,1];  // light blue.
private _normalTxt = [1,1,1,1];

// the value controls, where BPM is 87721 and vt is 87726, and their box. vt uses 87725 as a background box and BPM
// uses its own background.
private _bpmVal = _dlg displayCtrl 87721;
private _vtVal  = _dlg displayCtrl 87726;
private _vtBox  = _dlg displayCtrl 87725;

// reset both value fields.
_bpmVal ctrlSetBackgroundColor [0,0,0,0]; _bpmVal ctrlSetTextColor _normalTxt;
_vtBox  ctrlSetBackgroundColor [0,0,0,0]; _vtVal ctrlSetTextColor _normalTxt;

// the BPM field, at selidx 0.
if (_selIdx == 0) then {
    if (_edit) then {
        _bpmVal ctrlSetBackgroundColor _activeBg; _bpmVal ctrlSetTextColor _activeTxt;  // editing: a dark background with light text.
    } else {
        _bpmVal ctrlSetBackgroundColor _hoverBg;  _bpmVal ctrlSetTextColor _hoverTxt;  // hover: a light background with dark text.
    };
};
// the vt field, at selidx 1.
if (_selIdx == 1 && {!_simple}) then {
    if (_edit) then {
        _vtBox ctrlSetBackgroundColor _activeBg; _vtVal ctrlSetTextColor _activeTxt;
    } else {
        _vtBox ctrlSetBackgroundColor _hoverBg;  _vtVal ctrlSetTextColor _hoverTxt;
    };
};

// the strip: a light-blue highlight box behind the selected strip icon. it is the hover state only, because it is
// not editable.
private _stripHl = [87748,87749,87752,87753];  // the alarm, graph, breath and menu highlight boxes.
private _stripSel = _selIdx - 2;
{
    private _b = _dlg displayCtrl _x;
    if (_forEachIndex == _stripSel) then {
        _b ctrlSetBackgroundColor _hoverBg;
    } else {
        _b ctrlSetBackgroundColor [0,0,0,0];
    };
} forEach _stripHl;

// keep the legacy field-select var in sync, because the readout refresh reads ACME_vent_sel.
uiNamespace setVariable ["ACME_vent_sel", (["bpm","vt"] select (_selIdx min 1))];
[] call ACME_fnc_ventPanelRefresh;
