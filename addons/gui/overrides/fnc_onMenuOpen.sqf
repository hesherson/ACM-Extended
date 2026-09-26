#include "..\script_component.hpp"
/*
 * Author: Glowbal, mharis001
 * Handles opening the Medical Menu. Called from onLoad event.
 *
 * Arguments:
 * 0: Medical Menu display <DISPLAY>
 *
 * Return Value:
 * None
 *
 * Example:
 * [DISPLAY] call ace_medical_gui_fnc_onMenuOpen
 *
 * Public: No
 */

params ["_display"];

// Create background effects based on interact menu setting
if (ACEGVAR(interact_menu,menuBackground) == 1) then {[QACEGVAR(medical_gui,id), true] call ACEFUNC(common,blurScreen)};
if (ACEGVAR(interact_menu,menuBackground) == 2) then {0 cutRsc [QACEGVAR(interact_menu,menuBackground), "PLAIN", 1, false]};

// Fix mouse moving randomly
[{
    [{setMousePosition _this}, _this] call CBA_fnc_execNextFrame;
}, getMousePosition] call CBA_fnc_execNextFrame;

// Set middle header as target name
private _ctrlTitle = _display displayCtrl IDC_NAME;
_ctrlTitle ctrlSetText ([ACEGVAR(medical_gui,target)] call ACEFUNC(common,getName));

// Initially hide the triage select buttons
[_display] call ACEFUNC(medical_gui,toggleTriageSelect);

// Store display and give this concrete display its own renderer generation. ACE's stock lifecycle keeps a
// single global menuPFH handle. During fast close/reopen transitions (CPR/BVM/continuous actions), the new display
// can open before the old display's onUnload fires. The old onUnload then removes the *new/current* global PFH,
// leaving a perfectly visible medical menu whose controls never get rebound or refreshed. A one-shot refresh such
// as Direct Pressure then appears to "fix" every button, while a treatment that recreates the display also recovers
// it. Own the renderer by display generation instead of by one unqualified global handle.
uiNamespace setVariable [QACEGVAR(medical_gui,menuDisplay), _display];

private _menuEpoch = (missionNamespace getVariable ["ACME_medicalMenuPFHEpoch", 0]) + 1;
missionNamespace setVariable ["ACME_medicalMenuPFHEpoch", _menuEpoch];
_display setVariable ["ACME_medicalMenuPFHEpoch", _menuEpoch];

private _oldPFH = missionNamespace getVariable [QACEGVAR(medical_gui,menuPFH), -1];
if (_oldPFH isEqualType 0 && {_oldPFH >= 0}) then {
    [_oldPFH] call CBA_fnc_removePerFrameHandler;
};
ACEGVAR(medical_gui,menuPFH) = -1;

["ace_medicalMenuOpened", [ACE_player, ACEGVAR(medical_gui,target), _display]] call CBA_fnc_localEvent;

private _menuPFH = [{
    params ["_args", "_idPFH"];
    _args params ["_display", "_epoch"];

    private _currentDisplay = uiNamespace getVariable [QACEGVAR(medical_gui,menuDisplay), displayNull];
    private _currentEpoch = missionNamespace getVariable ["ACME_medicalMenuPFHEpoch", -1];

    if (isNull _display || {_display isNotEqualTo _currentDisplay} || {_epoch != _currentEpoch}) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
        if ((missionNamespace getVariable [QACEGVAR(medical_gui,menuPFH), -1]) == _idPFH) then {
            ACEGVAR(medical_gui,menuPFH) = -1;
        };
    };

    call ACEFUNC(medical_gui,menuPFH);
}, 0, [_display, _menuEpoch]] call CBA_fnc_addPerFrameHandler;

_display setVariable ["ACME_medicalMenuPFH", _menuPFH];
ACEGVAR(medical_gui,menuPFH) = _menuPFH;

// Hide categories if they don't have any actions (airway)
private _list = [
    [IDC_TRIAGE, true],
    [IDC_EXAMINE, true],
    [IDC_BANDAGE, "bandage"],
    [IDC_MEDICATION, "medication"],
    [IDC_AIRWAY, "airway"],
    [IDC_ADVANCED, "advanced"],
    [IDC_DRAG, "drag"],
    [IDC_TOGGLE, true]
];
private _countEnabled = {
    _x params ["", "_category"];
    if (_category isEqualType "") then { _x set [1, (ACEGVAR(medical_gui,actions) findIf {_category == _x select 1}) > -1]; };
    _x select 1
} count _list;
private _offsetX = POS_X(1.5) + 0.5 * (POS_X(12.33) - POS_X(_countEnabled * 1.5) - POS_W(2 * 0.2));
// 0.2 - divider gap size

// Set divider position
private _ctrl = _display displayCtrl IDC_TRIAGE_DIVIDER;
_ctrl ctrlSetPositionX _offsetX + POS_W(1.5) + POS_W(0.085); // 0.085 = (0.2 - 0.03) / 2
_ctrl ctrlCommit 0;

_ctrl = _display displayCtrl IDC_TOGGLE_DIVIDER;
_ctrl ctrlSetPositionX _offsetX + POS_W(1.5*(_countEnabled - 1)) + POS_W(0.2) + POS_W(0.085);
_ctrl ctrlCommit 0;

{
    _x params ["_idc", "_enabled"];

    if (_forEachIndex == 1 || {_forEachIndex == count _list - 1}) then {
        _offsetX = _offsetX + POS_W(0.2);
    };

    private _ctrl = _display displayCtrl _idc;
    if (_enabled) then {
        _ctrl ctrlSetPositionX _offsetX;
        _ctrl ctrlCommit 0;
        _offsetX = _offsetX + POS_W(1.5);
    } else {
        _ctrl ctrlShow false;
    };
} forEach _list;

if (GVAR(showPatientSideLabels)) then {
    (_display displayCtrl IDC_SIDE_LABEL_LEFT) ctrlShow true;
    (_display displayCtrl IDC_SIDE_LABEL_RIGHT) ctrlShow true;
};

// Set toggle button icon and tooltip
private _ctrl = _display displayCtrl IDC_TOGGLE;
if (ACEGVAR(medical_gui,target) == ACE_player) then {
    _ctrl ctrlSetText QACEPATHTOF(medical_gui,data\categories\toggle_to_other.paa);
    _ctrl ctrlSetTooltip ACELLSTRING(medical_gui,ToggleToOther);
} else {
    _ctrl ctrlSetText QACEPATHTOF(medical_gui,data\categories\toggle_to_self.paa);
    _ctrl ctrlSetTooltip ACELLSTRING(medical_gui,ToggleToSelf);
};
