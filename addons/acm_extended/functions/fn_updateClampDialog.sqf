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
private _edit = uiNamespace getVariable ["ACME_RollerClamp_Edit", []];
private _keepEdit = false;
private _applying = false;

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
            if (count _edit == 10 && {(_edit select 0) isEqualTo _display}
                && {(_edit select 1) isEqualTo ACE_player} && {(_edit select 2) isEqualTo _patient}
                && {_bagId != "" && {(_edit select 4) == _bagId}}
                && {(_edit select 3) == ([_patient] call ACME_fnc_clinicalEpoch)}) then {
                _keepEdit = true;
                private _stamp = _edit select 5;
                private _ledger = _entry param [28,[]];
                private _receiptIndex = _ledger findIf {(_x param [0,-1]) == (_stamp select 0)};
                private _confirmed = false;
                if (_receiptIndex >= 0) then {
                    private _receipt = _ledger select _receiptIndex;
                    _confirmed = (_receipt select 1) > (_stamp select 1)
                        || {(_receipt select 1) == (_stamp select 1) && {(_receipt select 2) >= (_stamp select 2)}};
                };
                // A replica must retain every receipt already observed. This
                // also orders interleaved edits from different providers.
                if (_confirmed) then {
                    _confirmed = ((_edit select 9) findIf {
                        private _known = _x;
                        private _i = _ledger findIf {(_x select 0) == (_known select 0)};
                        _i < 0 || {private _seen = _ledger select _i;
                            (_seen select 1) < (_known select 1)
                            || {(_seen select 1) == (_known select 1) && {(_seen select 2) < (_known select 2)}}}
                    }) < 0;
                };
                if (_confirmed) then {
                    _edit set [6,_entry param [22,_position]];
                    _edit set [7,_dropSet]; _edit set [8,true]; _edit set [9,_ledger];
                    uiNamespace setVariable ["ACME_RollerClamp_Edit",_edit];
                } else {
                    _dropSet = _edit select 7;
                    if (!_dragging) then {_position = _edit select 6;};
                };
                _dropsPerMinute = [_position] call ACME_fnc_clampPositionToDrops;
                _applying = !(_edit select 8);
            };
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
if (!_keepEdit && {!(_edit isEqualTo [])}) then {
    uiNamespace setVariable ["ACME_RollerClamp_Edit", []];
};

private _rateText = if (_hasEntry) then {
    [_doseRemaining, _lastVolume, _dropSet, _dropsPerMinute, _position] call ACME_fnc_formatRate
} else {
    private _mlPerMinute = if (_dropSet > 0) then {_dropsPerMinute / _dropSet} else {0};
    format ["%1 gtt/mL | %2 gtt/min | %3 mL/min | %4%5 open", round _dropSet, round _dropsPerMinute, _mlPerMinute toFixed 1, round (((_position max 0) min 1) * 100), "%"]
};

if (_applying) then {_rateText = _rateText + " | Applying...";};
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

// Native tooltips are static: changing them under the cursor repeatedly restarts the popup.
if !(_display getVariable ["ACME_clampReadoutReady",false]) then {
    _display setVariable ["ACME_clampReadoutReady",true];
    {_x ctrlSetTooltip "";} forEach [_ctrlTitle,_ctrlRate,_ctrlDrag,_ctrlWheel,_ctrlBG];
    _ctrlDrop ctrlSetTooltip "Cycle the drop set (gtt/mL).";
};
// The existing bottom rate strip is the sole live readout. IDC 86210 is the
// backdrop; writing a tooltip into it displays a duplicate across the panel.
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
