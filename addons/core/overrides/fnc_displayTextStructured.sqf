#include "..\script_component.hpp"
/*
 * Author: commy2, Glowbal, GitHawk
 * Display a structured text.
 *
 * Arguments:
 * 0: Text <ANY>
 * 1: Size of the textbox <NUMBER> (default: 1.5)
 * 2: Target Unit. Will only display if target is the player controlled object <OBJECT> (default: ACE_player)
 * 3: Custom Width <NUMBER> (default: 10)
 *
 * Return Value:
 * None
 *
 * Example:
 * [["Test: %1", 123], 1.5] call ace_common_fnc_displayTextStructured
 * ["wow", 1, ace_player, 3] call ace_common_fnc_displayTextStructured
 *
 * Public: Yes
 */

params [["_text", ""], ["_size", 1.5, [0]], ["_target", ACE_player, [objNull]], ["_width", 10, [0]]];

if ((missionNamespace getVariable ["ACME_hc_descriptors", false]) isEqualTo true) then {
    if (_text isEqualType "") then {
        private _c = [_text] call ACME_fnc_clinTerm;
        if (_c isNotEqualTo "") then {_text = _c;};
    } else {
        if (_text isEqualType []) then {
            private _copy = +_text;
            {
                if (_x isEqualType "") then {
                    private _c = [_x] call ACME_fnc_clinTerm;
                    if (_c isNotEqualTo "") then {_copy set [_forEachIndex, _c];};
                };
            } forEach _copy;
            _text = _copy;
        };
    };
    private _sel = missionNamespace getVariable ["ace_medical_gui_selectedBodyPart", -1];
    if ((_sel in [2,3,4,5])
        && {!isNull (uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull])}
        && {_text isEqualType ""}) then {
        _text = [_text, _sel, false] call ACME_fnc_ivSiteRelabel;
    };
};

if (_target != ACE_player) exitWith {};

if (typeName _text != "TEXT") then {
    if (_text isEqualType []) then {
        if (count _text > 0) then {
            {
                if (_x isEqualType "" && {isLocalized _x}) then {
                    _text set [_forEachIndex, localize _x];
                };
            } forEach _text;
            _text = format _text;
        };
    };
    if (_text isEqualType "" && {isLocalized _text}) then {
        _text = localize _text;
    };
    _text = parseText format ["<t align='center'><t size='0.35'> </t><br/>%1<br/><t size='0.35'> </t></t>", _text];
};

("ACE_RscHint" call BIS_fnc_rscLayer) cutRsc ["ACE_RscHint", "PLAIN", 0, true];

disableSerialization;
private _ctrlHint = uiNamespace getVariable "ACE_ctrlHint";

_ctrlHint ctrlSetBackgroundColor ACEGVAR(common,displayTextColor);
_ctrlHint ctrlSetTextColor ACEGVAR(common,displayTextFontColor);

// Use profile settings from CfgUIGrids.hpp
private _xPos = profileNamespace getVariable ["IGUI_GRID_ACE_displayText_X", ((safeZoneX + safeZoneW) - (10 *(((safeZoneW / safeZoneH) min 1.2) / 40)) - 2.9 *(((safeZoneW / safeZoneH) min 1.2) / 40))];
private _yPos = profileNamespace getVariable ["IGUI_GRID_ACE_displayText_Y", safeZoneY + 0.175 * safeZoneH];
private _wPos =  (_width *(((safeZoneW / safeZoneH) min 1.2) / 40));
// The legacy size argument is a caller estimate, not a minimum height. Measure actual wrapped
// content after establishing width, for strings, localized arrays and preformatted TEXT alike.
_ctrlHint ctrlSetPosition [_xPos, _yPos, _wPos, safeZoneH];
_ctrlHint ctrlCommit 0;
_ctrlHint ctrlSetStructuredText _text;
private _hPos = ((ctrlTextHeight _ctrlHint) + (safeZoneH * 0.003)) min safeZoneH;

// Ensure still in bounds for the measured width/height.
_xPos = safeZoneX max (_xPos min (safeZoneX + safeZoneW - _wPos));
_yPos = safeZoneY max (_yPos min (safeZoneY + safeZoneH - _hPos));
if (!isNull curatorCamera) then {
    _xPos = _xPos min ((safeZoneX + safeZoneW - 12.5 * (((safeZoneW / safeZoneH) min 1.2) / 40)) - _wPos);
};
_ctrlHint ctrlSetPosition [_xPos, _yPos, _wPos, _hPos];
// Position/height settle together: no frame with the old oversized backing under a new short result.
_ctrlHint ctrlCommit 0;
