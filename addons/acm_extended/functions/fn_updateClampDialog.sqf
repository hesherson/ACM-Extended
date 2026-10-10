/* Keep the close-focus pass after every clamp display update. */
private _acmeNVArgs = if (isNil "_this") then {[]} else {_this};
_acmeNVArgs call {
private _display = findDisplay 86200;
if (isNull _display) exitWith {};
call ACME_fnc_onClampLoad;  // idempotent; covers environments where config onload never fires

private _dragging = uiNamespace getVariable ["ACME_RollerClamp_Dragging", false];

// the cached ui state. the dialog stays alive and visually correct even when the data context cannot be resolved,
// such as a deselected bag, a closed menu or a console test.
private _dropSet = uiNamespace getVariable ["ACME_RollerClamp_DropSet", missionNamespace getVariable ["ACME_infusion_defaultDropSet", 20]];
private _position = uiNamespace getVariable ["ACME_RollerClamp_Position", 1];
private _medName = uiNamespace getVariable ["ACME_RollerClamp_MedName", ""];
private _dropsPerMinute = [_position] call ACME_fnc_clampPositionToDrops;
private _doseRemaining = -1;
private _lastVolume = -1;
private _hasEntry = false;
private _componentText = [];

private _result = call ACME_fnc_getSelectedInfusionEntryIndexes;
if !(_result isEqualTo []) then {
    _result params ["_patient", "_indexes"];
    if !(_indexes isEqualTo []) then {
        private _entries = _patient getVariable ["ACME_infusion_BagMedications", []];
        private _entryIndex = _indexes select 0;
        if (_entryIndex >= 0 && {_entryIndex < count _entries}) then {
            private _entry = _entries select _entryIndex;
            _hasEntry = true;
            _dropSet = _entry param [20, missionNamespace getVariable ["ACME_infusion_defaultDropSet", 20]];
            if (_dragging) then {
                // while grabbed, the wheel is the source of truth.
                _dropsPerMinute = [_position] call ACME_fnc_clampPositionToDrops;
            } else {
                _dropsPerMinute = _entry param [21, 60];
                _position = _entry param [22, ([_dropsPerMinute] call ACME_fnc_dropsToClampPosition)];
            };
            private _medication = _entry param [11, ""];
            _doseRemaining = _entry param [14, -1];
            _lastVolume = _entry param [10, -1];
            if (_medication isEqualType "" && {_medication != ""}) then {
                _medName = [_medication] call ACME_fnc_infusionName;
                if (_medName == "") then {_medName = _medication};
            };

            private _bagId = _entry param [23, ""];
            private _same = _entries select {(_x param [23, ""]) == _bagId};
            if (_same isEqualTo []) then {_same = [_entry];};
            _componentText = _same apply {
                [_x select 11] call ACME_fnc_infusionName
            };
            if (count _same > 1) then {_medName = format ["Mixed infusion (%1 medications)", count _same];};
            uiNamespace setVariable ["ACME_RollerClamp_DropSet", _dropSet];
            uiNamespace setVariable ["ACME_RollerClamp_Position", _position];
            uiNamespace setVariable ["ACME_RollerClamp_MedName", _medName];
        };
    };
};

private _rateText = if (_hasEntry) then {
    [_doseRemaining, _lastVolume, _dropSet, _dropsPerMinute, _position] call ACME_fnc_formatRate
} else {
    private _mlPerMinute = if (_dropSet > 0) then {_dropsPerMinute / _dropSet} else {0};
    format ["%1 gtt/mL | %2 gtt/min | %3 mL/min | %4%5 open", round _dropSet, round _dropsPerMinute, _mlPerMinute toFixed 1, round (((_position max 0) min 1) * 100), "%"]
};

private _flash = uiNamespace getVariable ["ACME_RollerClamp_Flash", ["", -1]];
_flash params ["_flashText", "_flashUntil"];
if (_flashUntil > CBA_missionTime && {_flashText != ""}) then {
    _rateText = format ["%1  |  %2", _flashText, _rateText];
};

private _ctrlTitle = _display displayCtrl 86205;
private _ctrlRate = _display displayCtrl 86206;
private _ctrlWheel = _display displayCtrl 86202;
private _ctrlDrag = _display displayCtrl 86203;
private _ctrlBG = _display displayCtrl 86201;
private _ctrlDrop = _display displayCtrl 86207;
private _ctrlClamp = _display displayCtrl 86208;

private _percent = round (((_position max 0) min 1) * 100);
private _mlPerMinute = if (_dropSet > 0) then {_dropsPerMinute / _dropSet} else {0};
private _tooltip = format ["Roller clamp: %1%2 open | %3 gtt/mL | %4 gtt/min | %5 mL/min", _percent, "%", round _dropSet, round _dropsPerMinute, _mlPerMinute toFixed 1];

// Native tooltips are static: changing them under the cursor repeatedly restarts the popup.
if !(_display getVariable ["ACME_clampReadoutReady",false]) then {
    _display setVariable ["ACME_clampReadoutReady",true];
    {_x ctrlSetTooltip "";} forEach [_ctrlTitle,_ctrlRate,_ctrlDrag,_ctrlWheel,_ctrlBG];
    _ctrlDrop ctrlSetTooltip "Cycle the drop set (gtt/mL).";
};
private _readout = _display displayCtrl 86210;
if (isNull _readout) then {
    _readout = _display ctrlCreate ["RscText",86210];
    _readout ctrlEnable false;
    _readout ctrlSetBackgroundColor [0,0,0,0.6];
    _readout ctrlSetFont "RobotoCondensed";
    _readout ctrlSetFontHeight (safeZoneH * 0.019);
    _readout ctrlSetPosition [safeZoneX + safeZoneW * 0.60,safeZoneY + safeZoneH * 0.72,safeZoneW * 0.37,safeZoneH * 0.045];
    _readout ctrlCommit 0;
};
if (ctrlText _readout != _tooltip) then {_readout ctrlSetText _tooltip;};
private _heading = [format ["Roller Clamp - %1",_medName],"Roller Clamp"] select (_medName == "");
if (ctrlText _ctrlTitle != _heading) then {_ctrlTitle ctrlSetText _heading;};
if (ctrlText _ctrlRate != _rateText) then {_ctrlRate ctrlSetText _rateText;};
private _dropText = format ["Drop Set: %1",round _dropSet];
if (ctrlText _ctrlDrop != _dropText) then {_ctrlDrop ctrlSetText _dropText;};
private _clampText = ["Open Clamp","Close Clamp"] select (_dropsPerMinute > 0);
if (ctrlText _ctrlClamp != _clampText) then {_ctrlClamp ctrlSetText _clampText;};

if !(uiNamespace getVariable ["ACME_RollerClamp_LoggedUpdate", false]) then {
    uiNamespace setVariable ["ACME_RollerClamp_LoggedUpdate", true];
};

// the per-frame mover owns the wheel while it is grabbed.
if (!_dragging) then {
    [_position] call ACME_fnc_placeClampWheel;
};

};

// Darkness/NV state is refreshed independently by fn_registerClampDragRuntime.
// Do not sample it here: this function can run during the dialog-transition frame,
// when currentVisionMode can briefly report normal vision and latch a black shade.
