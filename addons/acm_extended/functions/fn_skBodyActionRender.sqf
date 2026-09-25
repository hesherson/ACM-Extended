/* B76: one contextual button directly above Draw Syringe on Body Map.
   Default: blinking red two-press Discard Syringe. After a site is chosen: explicit Push/Inject confirmation for
   the currently selected carousel syringe. */
disableSerialization;
private _d = findDisplay 84000;
if (isNull _d) exitWith {};
private _back = _d displayCtrl 84819;
private _btn = _d displayCtrl 84820;
if (isNull _back || {isNull _btn}) exitWith {};

// Push-duration controls are available for every vascular syringe administration. The grey number is guidance
// only. If the provider does not enter a number, the actual push defaults to 3 seconds in both normal and Hardcore
// medication modes.
private _hcMed = missionNamespace getVariable ["ACME_hcEff_medications",false];
private _durLabel = _d displayCtrl 84830;
private _durEdit = _d displayCtrl 84831;
private _durHint = _d displayCtrl 84832;
if (isNull _durLabel) then {
    _durLabel = _d ctrlCreate ["RscText",84830];
    _durLabel ctrlSetText "Seconds to Push over:";
    _durLabel ctrlSetTextColor [0.94,0.91,0.82,1];
    _durLabel ctrlSetBackgroundColor [0.043,0.082,0.188,0.90];
    _durLabel ctrlEnable false;
};
if (isNull _durEdit) then {
    _durEdit = _d ctrlCreate ["ACME_SK_PushDurationEdit",84831];
    _durEdit ctrlShow false; // Lay out the new control before it can receive focus.
    _durEdit ctrlSetText "";
    _durEdit ctrlSetTextColor [1,1,1,1];
    _durEdit ctrlSetBackgroundColor [0.02,0.03,0.06,0.94];
    _durEdit ctrlSetTooltip "Optional: type whole seconds to push over (1-300). Leave it blank for 3 seconds. Grey text is the recommended value.";
    // Recommendations live on a separate noninteractive control, never in the editable value.
    _durEdit setVariable ["ACME_SK_GhostActive",false];
    _durEdit ctrlAddEventHandler ["MouseButtonDown", {
        params ["_ctrl","_button"];
        if (_button == 0) then {ctrlSetFocus _ctrl;};
        false
    }];
    _durEdit ctrlAddEventHandler ["SetFocus", {
        params ["_ctrl"];
        uiNamespace setVariable ["ACME_SK_CarouselHeldDir",0];
        uiNamespace setVariable ["ACME_SK_CarouselRepeatAt",0];
        ((ctrlParent _ctrl) displayCtrl 84832) ctrlShow false;
    }];
    _durEdit setVariable ["ACME_SK_PushDurationFor",""];
    _durEdit ctrlAddEventHandler ["KeyUp", {
        params ["_ctrl"];
        private _raw = ctrlText _ctrl;
        private _clean = toString ((toArray _raw) select {_x >= 48 && {_x <= 57}});
        if (_clean != _raw) then {_ctrl ctrlSetText _clean;};
        // The edit owns the provider's draft. Rendering may read it, but routine UI refreshes must never
        // replace it with a default or recommendation. Store by stable syringe ID so carousel changes and
        // closing/reopening the Narc Box restore the exact value that was typed for that prepared syringe.
        private _draftId = _ctrl getVariable ["ACME_SK_PushDurationFor",""];
        if (_draftId != "") then {
            private _drafts = uiNamespace getVariable ["ACME_SK_PushDurationDrafts",createHashMap];
            if !(_drafts isEqualType createHashMap) then {_drafts = createHashMap;};
            _drafts set [_draftId,_clean];
            uiNamespace setVariable ["ACME_SK_PushDurationDrafts",_drafts];
        };
        // Validate once per real keystroke. The 25 Hz UI loop deliberately leaves this edit alone while focused.
        call ACME_fnc_skBodyActionRender;
        false
    }];
};
if (isNull _durHint) then {
    _durHint = _d ctrlCreate ["RscText",84832];
    _durHint ctrlSetTextColor [0.56,0.58,0.62,0.82];
    _durHint ctrlSetBackgroundColor [0,0,0,0];
    _durHint ctrlEnable false;
    _durHint ctrlShow false;
};
private _durFocusCtrl = focusedCtrl _d;
private _durFocused = !isNull _durFocusCtrl && {_durFocusCtrl isEqualTo _durEdit};

private _body = (uiNamespace getVariable ["ACME_SK_View","syringe"]) == "body";
private _editMode = uiNamespace getVariable ["ACME_SK_TagEditMode",false];
private _busy = uiNamespace getVariable ["ACME_SK_InjectionBusy",false];
private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
private _idx = [_store,false] call ACME_fnc_skSelectedIndex;
private _usable = _body && {!_editMode} && {_idx >= 0} && {_idx < count _store} && {(uiNamespace getVariable ["ACME_SK_SelFlush",""]) == ""};
if (!_usable) exitWith {
    _back ctrlShow false;
    _btn ctrlShow false;
    _durLabel ctrlShow false; _durEdit ctrlShow false; _durHint ctrlShow false;
};

private _viewL = _d displayCtrl 84150;
private _viewR = _d displayCtrl 84152;
private _vl = +(ctrlPosition _viewL);
private _vr = +(ctrlPosition _viewR);
private _gap = safeZoneH * 0.006;
private _actionX = _vl select 0;
private _actionW = ((_vr select 0) + (_vr select 2)) - _actionX;
private _r = [_actionX, (_vl select 1) - (_vl select 3) - _gap, _actionW, _vl select 3];
_back ctrlSetPosition _r; _btn ctrlSetPosition _r;
_back ctrlCommit 0; _btn ctrlCommit 0;

// Keep the duration row physically attached to the green Push button. This used to be ordinary executable
// layout code; wrapping it in a bare {...} code literal stopped it from running and left the controls at their
// default coordinates. Use the live Push rectangle every render so page-navigation/layout changes cannot offset it.
private _pushRect = +(ctrlPosition _btn);
private _durGap = 2 * pixelW;
private _durH = (_pushRect select 3) * 0.82;
private _durY = (_pushRect select 1) - _durH - (_gap * 0.65);
private _editW = (_pushRect select 2) * 0.23;
private _labelW = (_pushRect select 2) - _editW - _durGap;
_durLabel ctrlSetPosition [_pushRect select 0, _durY, _labelW, _durH];
_durLabel ctrlSetFontHeight (_durH * 0.63);
_durLabel ctrlCommit 0;
// Only move the edit when its rectangle changes. Reading/validating text never rewrites its caret or focus.
private _editRect = [(_pushRect select 0) + _labelW + _durGap, _durY, _editW, _durH];
if (!_durFocused && {(ctrlPosition _durEdit) isNotEqualTo _editRect}) then {
    _durEdit ctrlSetPosition _editRect;
    _durEdit ctrlSetFontHeight (_durH * 0.63);
    _durEdit ctrlCommit 0;
};
_durHint ctrlSetPosition (ctrlPosition _durEdit);
_durHint ctrlSetFontHeight (_durH * 0.63);
_durHint ctrlCommit 0;

private _entry = _store select _idx;
private _id = _entry param [11,"",[""]];

// Keep a local draft per physical prepared syringe. A redraw is presentation-only and must never reset the
// provider's chosen time. On a real syringe change, save the previous field before restoring the new syringe's
// draft. This also preserves the entry through page changes and closing/reopening the Narc Box.
private _durationDrafts = uiNamespace getVariable ["ACME_SK_PushDurationDrafts",createHashMap];
if !(_durationDrafts isEqualType createHashMap) then {_durationDrafts = createHashMap;};
private _durationFor = _durEdit getVariable ["ACME_SK_PushDurationFor",""];
if (_durationFor != _id) then {
    if (_durationFor != "") then {_durationDrafts set [_durationFor,ctrlText _durEdit];};
    // Keyboard focus is authoritative. A transient inventory/list refresh must never swap the live editor's
    // syringe identity underneath the provider's caret. A real carousel selection change takes focus away first.
    if (!_durFocused || {_durationFor == ""}) then {
        private _restoredDuration = _durationDrafts getOrDefault [_id,""];
        if ((ctrlText _durEdit) != _restoredDuration) then {_durEdit ctrlSetText _restoredDuration;};
        _durEdit setVariable ["ACME_SK_PushDurationFor",_id];
    };
} else {
    if (_id != "") then {_durationDrafts set [_id,ctrlText _durEdit];};
};
uiNamespace setVariable ["ACME_SK_PushDurationDrafts",_durationDrafts];

private _pending = uiNamespace getVariable ["ACME_SK_PendingInjection",[]];
// B121: an active Hardcore push owns this exact stable syringe. The normal green confirmation becomes a red
// Stop Push control. It remains clickable even though carousel/site controls are deliberately locked.
private _hcJob = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
private _hcOwns = _hcJob isEqualType createHashMap && {count _hcJob > 0} && {(_hcJob getOrDefault ["stableId",""]) == _id};
if (_hcOwns) exitWith {
    _durHint ctrlShow false;
    private _flowing = _hcJob getOrDefault ["flowing",false];
    _btn ctrlSetText (if (_flowing) then {"Stop Push"} else {"Stopping..."});
    _btn ctrlSetTooltip (if (_flowing) then {"Stop the active medication push and preserve the exact remaining syringe volume"} else {"Settling the last delivered medication volume"});
    _btn ctrlEnable _flowing;
    _back ctrlSetBackgroundColor (["danger",0.90] call ACME_fnc_a11yColor);
    if (_hcMed) then {
        _durLabel ctrlShow true;
        if !(ctrlShown _durEdit) then {_durEdit ctrlShow true;};
        if (ctrlEnabled _durEdit) then {_durEdit ctrlEnable false;};
        // Keep the provider's draft visible while disabled. The running transaction already owns its
        // authoritative duration; writing that value back into the edit would destroy the draft on redraw.
    };
    _back ctrlShow true;
    _btn ctrlShow true;
    _btn ctrlCommit 0;
};
if (_pending isEqualType [] && {count _pending >= 3}) then {
    _pending params ["_part","_site","_route"];
    if (_route != "im") then {
        // Recommendation is display-only. Never write it, blank, or the 3 s fallback into the editable value.
        private _suggested = str (round ([_entry] call ACME_fnc_medicationSuggestedPushSec));
        _durHint ctrlSetText _suggested;
    };
    private _total = ((_entry param [2,0,[0]]) + (_entry param [4,0,[0]])) max 0;
    private _ml = _total;
    if ((_entry param [6,"",[""]]) == "epiMixB12") then {
        private _choice = uiNamespace getVariable ["ACME_SK_EpiDoseChoice",0];
        _ml = ([1,2,_total] select (((_choice max 0) min 2))) min _total;
    };
    private _mlText = if (abs (_ml - round _ml) < 0.0005) then {str (round _ml)} else {if (abs (_ml*10 - round (_ml*10)) < 0.0005) then {_ml toFixed 1} else {_ml toFixed 2}};
    private _where = [_part,"abbr"] call ACME_fnc_bodyPartName;
    private _verb = "Inject";
    if (_route != "im") then {
        _verb = "Push";
        private _siteName = "IO";
        if (_site >= 0) then {
            private _catalog = [_part,_site] call ACME_fnc_ivVeinCatalog;
            _siteName = if (_catalog isEqualType createHashMap && {count _catalog > 0}) then {
                _catalog getOrDefault ["short",[_part,_site,false] call ACME_fnc_skSiteName]
            } else {
                [_part,_site,false] call ACME_fnc_skSiteName
            };
        };
        _where = if (_siteName == "") then {_where} else {format ["%1 %2",_where,_siteName]};
    };
    _btn ctrlSetText format ["%1 %2 mL in %3",_verb,_mlText,_where];
    _btn ctrlSetTooltip "Confirm administration of the currently selected syringe at the selected site";
    private _validPushTime = true;
    if (_route != "im") then {
        private _ghost = _durEdit getVariable ["ACME_SK_GhostActive",false];
        private _rawDur = if (_ghost) then {""} else {ctrlText _durEdit};
        private _hasTypedDuration = !_ghost && {_rawDur != ""};
        private _numDur = if (_hasTypedDuration) then {parseNumber _rawDur} else {3};
        // Blank or grey-placeholder means "use the 3 s fallback". Only an explicitly typed out-of-range value blocks.
        _validPushTime = !_hasTypedDuration || {_numDur >= 1 && {_numDur <= 300}};
    };
    private _bloodBusy = false;
    if (_route != "im") then {
        private _patient = uiNamespace getVariable ["ACME_SK_Patient",objNull];
        if (isNull _patient) then {_patient = _d getVariable ["ACME_SK_ReturnPatient",objNull];};
        if (!isNull _patient) then {_bloodBusy = [_patient,_part,_site] call ACME_fnc_medicationLineBloodBusy;};
    };
    _btn ctrlEnable (!_busy && {_total > 0} && {_validPushTime} && {!_bloodBusy});
    _btn ctrlSetTooltip (
        if (_bloodBusy) then {
            "Blood is present in this line. Finish or remove the blood bag before pushing medication."
        } else {
            if (_validPushTime) then {"Confirm administration. If no push time is entered, 3 seconds is used."}
            else {"Push duration must be 1-300 seconds. Grey text is only the recommendation."}
        }
    );
    _back ctrlSetBackgroundColor (if (_bloodBusy) then {[0.22,0.08,0.08,0.82]} else {["success",0.82] call ACME_fnc_a11yColor});
    private _showDuration = _route != "im";
    _durLabel ctrlShow _showDuration;
    if ((ctrlShown _durEdit) isNotEqualTo _showDuration) then {_durEdit ctrlShow _showDuration;};
    private _durationEnabled = _showDuration && {!_busy};
    if ((ctrlEnabled _durEdit) isNotEqualTo _durationEnabled) then {_durEdit ctrlEnable _durationEnabled;};
    _durHint ctrlShow (_showDuration && {!_busy} && {!_durFocused} && {(ctrlText _durEdit) == ""});
} else {
    _durLabel ctrlShow false; _durEdit ctrlShow false; _durHint ctrlShow false;
    private _armed = uiNamespace getVariable ["ACME_SK_DiscardArmedId",""];
    if (_armed != _id) then {uiNamespace setVariable ["ACME_SK_DiscardArmedId",""]; _armed = "";};
    _btn ctrlSetText (if (_armed == _id) then {"Confirm discard?"} else {"Discard Syringe"});
    _btn ctrlSetTooltip "Discard the currently selected syringe. Requires two presses.";
    _btn ctrlEnable (!_busy);
    private _a = 0.48 + 0.42 * (0.5 + 0.5 * sin (diag_tickTime * 300));
    _back ctrlSetBackgroundColor (["danger",_a] call ACME_fnc_a11yColor);
};
_back ctrlShow true;
_btn ctrlShow true;
_btn ctrlCommit 0;
