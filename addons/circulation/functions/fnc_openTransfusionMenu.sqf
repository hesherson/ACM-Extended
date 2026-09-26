#include "..\script_component.hpp"
#include "..\TransfusionMenu_defines.hpp"
/*
 * Author: Blue
 * Open transfusion menu.
 *
 * Arguments:
 * 0: Medic <OBJECT>
 * 1: Patient <OBJECT>
 * 2: Body Part <STRING>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player, cursorObject, "LeftArm"] call ACM_circulation_fnc_openTransfusionMenu;
 *
 * Public: No
 */

params ["_medic", "_patient", "_bodyPart"];

if !(isNull findDisplay IDC_TRANSFUSIONMENU) exitWith {};

ACEGVAR(medical_gui,pendingReopen) = false; // Prevent medical menu from reopening

if (dialog) then { // If another dialog is open (medical menu) close it
    closeDialog 0;
};

private _menuGeneration = (missionNamespace getVariable [QGVAR(TransfusionMenu_Generation), 0]) + 1;
GVAR(TransfusionMenu_Generation) = _menuGeneration;

private _previousCloseID = missionNamespace getVariable [QGVAR(TransfusionMenu_CloseID), -1];
if (!(_previousCloseID isEqualTo -1) && {!(_previousCloseID isEqualTo "")}) then {
    [_previousCloseID, "keydown"] call CBA_fnc_removeKeyHandler;
};

private _medicalMenuKeybind = (["ACE3 Common", QACEGVAR(medical_gui,openMedicalMenuKey)] call CBA_FUNC(getKeybind) select 5) select 0;

private _closeID = [_medicalMenuKeybind, [false, false, false], { // H to close and open medical menu
    closeDialog 0;
    [ACEFUNC(medical_gui,openMenu), GVAR(TransfusionMenu_Target)] call CBA_fnc_execNextFrame;
}, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;
GVAR(TransfusionMenu_CloseID) = _closeID;

GVAR(TransfusionMenu_Target) = _patient;
GVAR(TransfusionMenu_Medic) = _medic;

GVAR(TransfusionMenu_Selection_IVBags_LastUpdate) = CBA_missionTime;
GVAR(TransfusionMenu_Selection_IVBags) = [];

GVAR(TransfusionMenu_Selected_AccessSite) = -1;
GVAR(TransfusionMenu_Selected_BodyPart) = toLowerANSI _bodyPart;
GVAR(TransfusionMenu_Selected_Inventory) = -1;

GVAR(TransfusionMenu_Move_Active) = false;
GVAR(TransfusionMenu_Move_Active_Moving) = false;
GVAR(TransfusionMenu_Move_IVBagContents) = [];
GVAR(TransfusionMenu_Move_OriginIV) = false;
GVAR(TransfusionMenu_Move_OriginBodyPart) = toLowerANSI _bodyPart;
GVAR(TransfusionMenu_Move_OriginAccessSite) = GVAR(TransfusionMenu_Selected_AccessSite);

if (GVAR(TransfusionMenu_Selected_AccessSite) == -1) then {
    private _selected = false;
    // Prefer a real access on the body part used to open the menu.
    for "_site" from 0 to 2 do {
        if (!_selected && {[_patient,_bodyPart,0,_site] call FUNC(hasIV)}) then {
            GVAR(TransfusionMenu_SelectIV) = true;
            GVAR(TransfusionMenu_Selected_AccessSite) = _site;
            _selected = true;
        };
    };
    if (!_selected && {[_patient,_bodyPart,0] call FUNC(hasIO)}) then {
        GVAR(TransfusionMenu_SelectIV) = false;
        GVAR(TransfusionMenu_Selected_AccessSite) = 0;
        _selected = true;
    };
    // If that part has no access, select the first ACTUAL IV/IO anywhere. Never invent a torso IO.
    if (!_selected) then {
        {
            private _part = _x;
            for "_site" from 0 to 2 do {
                if (!_selected && {[_patient,_part,0,_site] call FUNC(hasIV)}) then {
                    GVAR(TransfusionMenu_SelectIV) = true;
                    GVAR(TransfusionMenu_Selected_BodyPart) = _part;
                    GVAR(TransfusionMenu_Selected_AccessSite) = _site;
                    _selected = true;
                };
            };
            if (!_selected && {[_patient,_part,0] call FUNC(hasIO)}) then {
                GVAR(TransfusionMenu_SelectIV) = false;
                GVAR(TransfusionMenu_Selected_BodyPart) = _part;
                GVAR(TransfusionMenu_Selected_AccessSite) = 0;
                _selected = true;
            };
            if (_selected) exitWith {};
        } forEach ALL_BODY_PARTS;
    };
    if (!_selected) then {
        GVAR(TransfusionMenu_SelectIV) = true;
        GVAR(TransfusionMenu_Selected_AccessSite) = -1;
    };
};

createDialog QGVAR(TransfusionMenu_Dialog);
uiNamespace setVariable [QGVAR(TransfusionMenu_DLG),(findDisplay IDC_TRANSFUSIONMENU)];

private _display = uiNamespace getVariable [QGVAR(TransfusionMenu_DLG), displayNull];
if (isNull _display) exitWith {
    if (!(_closeID isEqualTo -1) && {!(_closeID isEqualTo "")}) then {
        [_closeID, "keydown"] call CBA_fnc_removeKeyHandler;
    };
};

_display setVariable ["ACM_TX_Generation", _menuGeneration];
_display setVariable ["ACM_TX_CloseID", _closeID];

{
    private _ctrl = _display displayCtrl _x;
    if (!isNull _ctrl) then {_ctrl ctrlShow false;};
} forEach [
    IDC_TRANSFUSIONMENU_BG_IO_TORSO,
    IDC_TRANSFUSIONMENU_BG_IO_RIGHTARM,
    IDC_TRANSFUSIONMENU_BG_IO_LEFTARM,
    IDC_TRANSFUSIONMENU_BG_IO_RIGHTLEG,
    IDC_TRANSFUSIONMENU_BG_IO_LEFTLEG,
    IDC_TRANSFUSIONMENU_BG_IV_RIGHTARM_UPPER,
    IDC_TRANSFUSIONMENU_BG_IV_RIGHTARM_MIDDLE,
    IDC_TRANSFUSIONMENU_BG_IV_RIGHTARM_LOWER,
    IDC_TRANSFUSIONMENU_BG_IV_LEFTARM_UPPER,
    IDC_TRANSFUSIONMENU_BG_IV_LEFTARM_MIDDLE,
    IDC_TRANSFUSIONMENU_BG_IV_LEFTARM_LOWER,
    IDC_TRANSFUSIONMENU_BG_IV_RIGHTLEG_UPPER,
    IDC_TRANSFUSIONMENU_BG_IV_RIGHTLEG_MIDDLE,
    IDC_TRANSFUSIONMENU_BG_IV_RIGHTLEG_LOWER,
    IDC_TRANSFUSIONMENU_BG_IV_LEFTLEG_UPPER,
    IDC_TRANSFUSIONMENU_BG_IV_LEFTLEG_MIDDLE,
    IDC_TRANSFUSIONMENU_BG_IV_LEFTLEG_LOWER,
    IDC_TRANSFUSIONMENU_BG_TOURNIQUET_RIGHTARM,
    IDC_TRANSFUSIONMENU_BG_TOURNIQUET_LEFTARM,
    IDC_TRANSFUSIONMENU_BG_TOURNIQUET_RIGHTLEG,
    IDC_TRANSFUSIONMENU_BG_TOURNIQUET_LEFTLEG
];

// ACME three-page navigation. Transfuse sits between Body Map (left) and Narc Box (right).
if (!isNull _display && {!isNil "ACME_fnc_skPageNavigate"}) then {
    private _canvas = call ACME_fnc_uiCanvas;
    _canvas params ["_uiX","_uiY","_uiW","_uiH"];
    private _w = (_uiW / 11) * 0.72;
    private _h = safeZoneH / 32;
    private _gap = 4 * pixelW;
    private _y = safeZoneY + (safeZoneH / 1.08);
    private _lx = (_uiX + (_uiW/2)) - (_gap/2) - _w;
    private _rx = (_uiX + (_uiW/2)) + (_gap/2);
    // Same pulsing blue backing used by the Narc Box page buttons. The actual buttons remain transparent.
    private _pulse0 = ["info",0.52] call ACME_fnc_a11yColor;
    private _lbBack = _display ctrlCreate ["RscText",86952];
    _lbBack ctrlSetPosition [_lx,_y,_w,_h];
    _lbBack ctrlSetBackgroundColor _pulse0;
    _lbBack ctrlEnable false;
    _lbBack ctrlCommit 0;
    private _rbBack = _display ctrlCreate ["RscText",86953];
    _rbBack ctrlSetPosition [_rx,_y,_w,_h];
    _rbBack ctrlSetBackgroundColor _pulse0;
    _rbBack ctrlEnable false;
    _rbBack ctrlCommit 0;

    private _lb = _display ctrlCreate ["ACME_TX_PageButton",86950];
    _lb ctrlSetPosition [_lx,_y,_w,_h];
    _lb ctrlSetText "< Body Map";
    _lb ctrlSetTooltip "Previous page";
    _lb ctrlAddEventHandler ["ButtonClick",{["left"] call ACME_fnc_skPageNavigate;}];
    _lb ctrlCommit 0;
    private _rb = _display ctrlCreate ["ACME_TX_PageButton",86951];
    _rb ctrlSetPosition [_rx,_y,_w,_h];
    _rb ctrlSetText "Narc Box >";
    _rb ctrlSetTooltip "Next page";
    _rb ctrlAddEventHandler ["ButtonClick",{["right"] call ACME_fnc_skPageNavigate;}];
    _rb ctrlCommit 0;
};

call FUNC(TransfusionMenu_UpdateSelection);
call FUNC(TransfusionMenu_SwitchTargetInventory);
[false] call FUNC(TransfusionMenu_UpdateBagList);

private _ctrlPatientName = _display displayCtrl IDC_TRANSFUSIONMENU_PATIENTNAME;

_ctrlPatientName ctrlSetText ([_patient, false, true] call ACEFUNC(common,getName));

private _inVehicle = !(isNull objectParent _medic);

private _pfh = [{
    params ["_args", "_idPFH"];
    _args params ["_display", "_medic", "_patient", "_inVehicle", "_generation", "_closeID"];

    // Superseded display. Retire only this PFH; never clean globals owned by the newer menu.
    if ((missionNamespace getVariable [QGVAR(TransfusionMenu_Generation), -1]) != _generation
        || {_display isNotEqualTo (findDisplay IDC_TRANSFUSIONMENU)}) exitWith {
        [_idPFH] call CBA_fnc_removePerFrameHandler;
    };

    private _dialogCondition = isNull _display;
    private _patientCondition = isNull _patient;
    private _medicCondition = isNull _medic || {!alive _medic} || {IS_UNCONSCIOUS(_medic)};
    private _vehicleCondition = false;
    private _distanceCondition = false;
    if (!_patientCondition && {!_medicCondition}) then {
        _vehicleCondition = objectParent _medic isNotEqualTo objectParent _patient;
        _distanceCondition = (_patient distance2D _medic) > ACEGVAR(medical_gui,maxDistance);
    };

    if (_medicCondition || _patientCondition || _dialogCondition
        || {_inVehicle && {_vehicleCondition}}
        || {!_inVehicle && {_distanceCondition}}) exitWith {

        if (GVAR(TransfusionMenu_Move_Active) && {!GVAR(TransfusionMenu_Move_Active_Moving)}
            && {!_patientCondition}) then {
            [_patient] call FUNC(TransfusionMenu_MoveBag_Cancel);
        };

        // Closing this exact display runs its unload cleanup immediately. Never leave a live dialog whose
        // render PFH has stopped, because all access pictures in the base config are visible by default.
        if (!isNull _display) then {_display closeDisplay 2;};

        if (!(_closeID isEqualTo -1) && {!(_closeID isEqualTo "")}) then {
            [_closeID, "keydown"] call CBA_fnc_removeKeyHandler;
        };
        if ((missionNamespace getVariable [QGVAR(TransfusionMenu_Generation), -1]) == _generation) then {
            if ((missionNamespace getVariable [QGVAR(TransfusionMenu_CloseID), -1]) isEqualTo _closeID) then {
                GVAR(TransfusionMenu_CloseID) = -1;
            };
            if ((missionNamespace getVariable [QGVAR(TransfusionMenu_Target), objNull]) isEqualTo _patient) then {
                GVAR(TransfusionMenu_Target) = objNull;
            };
        };
        [_idPFH] call CBA_fnc_removePerFrameHandler;
    };

    // Keep the Transfuse page buttons visually identical to Narc Box / Body Map: same accessibility blue and
    // same live pulse. Backings own the color so focused/pressed button states cannot darken it.
    private _navPulse = ["info", 0.30 + 0.45 * (0.5 + 0.5 * sin (diag_tickTime * 220))] call ACME_fnc_a11yColor;
    {
        private _pc = _display displayCtrl _x;
        if (!isNull _pc) then {_pc ctrlSetBackgroundColor _navPulse;};
    } forEach [86952,86953];

    private _ctrlTourniquetLeftArm = _display displayCtrl IDC_TRANSFUSIONMENU_BG_TOURNIQUET_LEFTARM;
    private _ctrlTourniquetRightArm = _display displayCtrl IDC_TRANSFUSIONMENU_BG_TOURNIQUET_RIGHTARM;
    private _ctrlTourniquetLeftLeg = _display displayCtrl IDC_TRANSFUSIONMENU_BG_TOURNIQUET_LEFTLEG;
    private _ctrlTourniquetRightLeg = _display displayCtrl IDC_TRANSFUSIONMENU_BG_TOURNIQUET_RIGHTLEG;

    private _ctrlTourniquetArray = [_ctrlTourniquetLeftArm, _ctrlTourniquetRightArm, _ctrlTourniquetLeftLeg, _ctrlTourniquetRightLeg];

    private _tourniquets = GET_TOURNIQUETS(_patient);
    if !(_tourniquets isEqualType [] && {count _tourniquets >= 6}) then {
        _tourniquets = DEFAULT_TOURNIQUET_VALUES;
    };
    {
        private _value = _tourniquets param [_forEachIndex + 2, 0];
        if !(_value isEqualType 0 && {finite _value}) then {_value = 0;};
        _x ctrlShow (_value > 0);
    } forEach _ctrlTourniquetArray;

    private _partIndex = ALL_BODY_PARTS find GVAR(TransfusionMenu_Selected_BodyPart);

    private _ctrlIVLeftArmUpper = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_LEFTARM_UPPER;
    private _ctrlIVLeftArmMiddle = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_LEFTARM_MIDDLE;
    private _ctrlIVLeftArmLower = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_LEFTARM_LOWER;
    private _ctrlIVRightArmUpper = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_RIGHTARM_UPPER;
    private _ctrlIVRightArmMiddle = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_RIGHTARM_MIDDLE;
    private _ctrlIVRightArmLower = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_RIGHTARM_LOWER;

    private _ctrlIVLeftLegUpper = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_LEFTLEG_UPPER;
    private _ctrlIVLeftLegMiddle = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_LEFTLEG_MIDDLE;
    private _ctrlIVLeftLegLower = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_LEFTLEG_LOWER;
    private _ctrlIVRightLegUpper = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_RIGHTLEG_UPPER;
    private _ctrlIVRightLegMiddle = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_RIGHTLEG_MIDDLE;
    private _ctrlIVRightLegLower = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IV_RIGHTLEG_LOWER;

    private _IVCtrlArray = [[_ctrlIVLeftArmUpper, _ctrlIVLeftArmMiddle, _ctrlIVLeftArmLower], [_ctrlIVRightArmUpper, _ctrlIVRightArmMiddle, _ctrlIVRightArmLower], [_ctrlIVLeftLegUpper, _ctrlIVLeftLegMiddle, _ctrlIVLeftLegLower], [_ctrlIVRightLegUpper, _ctrlIVRightLegMiddle, _ctrlIVRightLegLower]];

    private _IVArray = GET_IV(_patient);
    if !(_IVArray isEqualType [] && {count _IVArray >= 6}) then {
        _IVArray = ACM_IV_PLACEMENT_DEFAULT_0;
    };

    {
        _x params ["_xUpper", "_xMiddle", "_xLower"];

        private _accessSiteArray = _IVArray param [_forEachIndex + 2, [0,0,0]];
        if !(_accessSiteArray isEqualType [] && {count _accessSiteArray >= 3}) then {
            _accessSiteArray = [0,0,0];
        };

        private _IVUpper = _accessSiteArray param [0, 0];
        private _IVMiddle = _accessSiteArray param [1, 0];
        private _IVLower = _accessSiteArray param [2, 0];
        if !(_IVUpper isEqualType 0 && {finite _IVUpper}) then {_IVUpper = 0;};
        if !(_IVMiddle isEqualType 0 && {finite _IVMiddle}) then {_IVMiddle = 0;};
        if !(_IVLower isEqualType 0 && {finite _IVLower}) then {_IVLower = 0;};

        _xUpper ctrlShow (_IVUpper > 0);
        _xMiddle ctrlShow (_IVMiddle > 0);
        _xLower ctrlShow (_IVLower > 0);

        if (GVAR(TransfusionMenu_SelectIV) && (_forEachIndex + 2) == _partIndex) then {
            switch (GVAR(TransfusionMenu_Selected_AccessSite)) do {
                case 0: {
                    _xUpper ctrlSetTextColor [0.20,0.65,0.20,1];
                    _xMiddle ctrlSetTextColor [0.20,0.65,0.20,0.42];
                    _xLower ctrlSetTextColor [0.20,0.65,0.20,0.42];
                };
                case 1: {
                    _xUpper ctrlSetTextColor [0.20,0.65,0.20,0.42];
                    _xMiddle ctrlSetTextColor [0.20,0.65,0.20,1];
                    _xLower ctrlSetTextColor [0.20,0.65,0.20,0.42];
                };
                case 2: {
                    _xUpper ctrlSetTextColor [0.20,0.65,0.20,0.42];
                    _xMiddle ctrlSetTextColor [0.20,0.65,0.20,0.42];
                    _xLower ctrlSetTextColor [0.20,0.65,0.20,1];
                };
            };
        } else {
            _xUpper ctrlSetTextColor [0.20,0.65,0.20,0.42];
            _xMiddle ctrlSetTextColor [0.20,0.65,0.20,0.42];
            _xLower ctrlSetTextColor [0.20,0.65,0.20,0.42];
        };
    } forEach _IVCtrlArray;

    private _ctrlIOLeftArm = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IO_LEFTARM;
    private _ctrlIORightArm = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IO_RIGHTARM;
    private _ctrlIOLeftLeg = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IO_LEFTLEG;
    private _ctrlIORightLeg = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IO_RIGHTLEG;
    private _ctrlIOTorso = _display displayCtrl IDC_TRANSFUSIONMENU_BG_IO_TORSO;

    private _IOCtrlArray = [_ctrlIOTorso, _ctrlIOLeftArm, _ctrlIORightArm, _ctrlIOLeftLeg, _ctrlIORightLeg];
    private _IOArray = GET_IO(_patient);
    if !(_IOArray isEqualType [] && {count _IOArray >= 6}) then {
        _IOArray = ACM_IO_PLACEMENT_DEFAULT_0;
    };

    {
        private _value = _IOArray param [_forEachIndex + 1, 0];
        if !(_value isEqualType 0 && {finite _value}) then {_value = 0;};
        _x ctrlShow (_value > 0);

        if (!(GVAR(TransfusionMenu_SelectIV)) && (_forEachIndex + 1) == _partIndex) then {
            _x ctrlSetTextColor [0.20,0.65,0.20,1];
        } else {
            _x ctrlSetTextColor [0.20,0.65,0.20,0.42];
        };
    } forEach _IOCtrlArray;

    private _ctrlStopTransfusionButton = _display displayCtrl IDC_TRANSFUSIONMENU_BUTTON_STOPIV;
    private _ctrlAddBagButton = _display displayCtrl IDC_TRANSFUSIONMENU_BUTTON_ADDBAG;
    private _selectedPart = GVAR(TransfusionMenu_Selected_BodyPart);
    private _selectedSite = GVAR(TransfusionMenu_Selected_AccessSite);
    private _hasSelectedAccess = if (GVAR(TransfusionMenu_SelectIV)) then {
        _selectedSite >= 0 && {[_patient,_selectedPart,0,_selectedSite] call FUNC(hasIV)}
    } else {
        [_patient,_selectedPart,0] call FUNC(hasIO)
    };
    private _siteFlowRate = 0;
    if (_hasSelectedAccess && {_partIndex >= 0}) then {
        _siteFlowRate = [(GET_IO_FLOW_X(_patient,_partIndex)), (GET_IV_FLOW_X(_patient,_partIndex,_selectedSite))] select GVAR(TransfusionMenu_SelectIV);
    };
    private _typeString = [LLSTRING(Intraosseous_Short), LLSTRING(Intravenous_Short)] select GVAR(TransfusionMenu_SelectIV);
    private _physicalBlock = "";
    if (_hasSelectedAccess && {_partIndex >= 0}) then {
        if (GVAR(TransfusionMenu_SelectIV)
            && {_patient getVariable [format ["ACME_IV_BandOnPart_%1", _partIndex], false]}) then {
            _physicalBlock = "IV placement band is still applied. Remove the band before this IV can flow.";
        };
        if (_physicalBlock == "" && {!isNil "ACME_fnc_aajtOccludes"}
            && {[_patient, _partIndex] call ACME_fnc_aajtOccludes}) then {
            _physicalBlock = "AAJT-S compression is physically occluding this vascular territory.";
        };
        if (_physicalBlock == "" && {_patient getVariable ["ace_medical_inCardiacArrest", false]}
            && {!([_patient] call ACM_core_fnc_cprActive)}) then {
            _physicalBlock = "No forward perfusion during cardiac arrest. Start CPR for IV/IO flow.";
        };
    };

    if (!_hasSelectedAccess) then {
        _ctrlStopTransfusionButton ctrlSetText "No IV / IO access";
        _ctrlStopTransfusionButton ctrlSetTooltip "Establish and select an IV or IO before starting a transfusion";
        _ctrlStopTransfusionButton ctrlEnable false;
        if (!isNull _ctrlAddBagButton) then {_ctrlAddBagButton ctrlEnable false;};
    } else {
        if (!isNull _ctrlAddBagButton) then {_ctrlAddBagButton ctrlEnable true;};
        if (_physicalBlock != "") then {
            _ctrlStopTransfusionButton ctrlSetText "Flow physically blocked";
            _ctrlStopTransfusionButton ctrlSetTooltip _physicalBlock;
            _ctrlStopTransfusionButton ctrlEnable false;
        } else {
            _ctrlStopTransfusionButton ctrlEnable true;
            if (_siteFlowRate > 0) then {
                _ctrlStopTransfusionButton ctrlSetText (format [LLSTRING(TransfusionMenu_StopTransfusion_Display), _typeString]);
                _ctrlStopTransfusionButton ctrlSetTooltip (format [LLSTRING(TransfusionMenu_StopTransfusion_ToolTip), _typeString]);
            } else {
                _ctrlStopTransfusionButton ctrlSetText (format [LLSTRING(TransfusionMenu_StartTransfusion_Display), _typeString]);
                _ctrlStopTransfusionButton ctrlSetTooltip (format [LLSTRING(TransfusionMenu_StartTransfusion_ToolTip), _typeString]);
            };
        };
    };

    if ((GVAR(TransfusionMenu_Selection_IVBags_LastUpdate) + 1) < CBA_missionTime) then {
        GVAR(TransfusionMenu_Selection_IVBags_LastUpdate) = CBA_missionTime;
        [true] call FUNC(TransfusionMenu_UpdateBagList);
    };
// This loop only repaints menu controls. 10 Hz is responsive while avoiding dozens of control mutations
// on every rendered frame, which was especially costly on lower-FPS clients.
}, 0.10, [_display, _medic, _patient, _inVehicle, _menuGeneration, _closeID]] call CBA_fnc_addPerFrameHandler;

_display setVariable ["ACM_TX_PFH", _pfh];
_display displayAddEventHandler ["Unload", {
    params ["_display"];
    private _pfh = _display getVariable ["ACM_TX_PFH", -1];
    if (_pfh isEqualType 0 && {_pfh >= 0}) then {
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };

    private _closeID = _display getVariable ["ACM_TX_CloseID", -1];
    if (!(_closeID isEqualTo -1) && {!(_closeID isEqualTo "")}) then {
        [_closeID, "keydown"] call CBA_fnc_removeKeyHandler;
    };

    private _generation = _display getVariable ["ACM_TX_Generation", -1];
    if ((missionNamespace getVariable [QGVAR(TransfusionMenu_Generation), -2]) == _generation) then {
        if ((missionNamespace getVariable [QGVAR(TransfusionMenu_CloseID), -1]) isEqualTo _closeID) then {
            GVAR(TransfusionMenu_CloseID) = -1;
        };
        GVAR(TransfusionMenu_Target) = objNull;
    };
}];
