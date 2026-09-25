/*
 * ACM Extended override of ACM/ACE medical GUI action rendering.
 *
 * B37 retains patient-scoped dropdown decisions across recreated displays and
 * stable per-row action controls within each live display.
 * Action conditions, inventory counts and patient findings still refresh on ACE's normal UI pass.
 * This function sends no network events and does not alter treatment callbacks.
 */

disableSerialization;
params [['_display', displayNull]];
if (isNull _display) exitWith {};

private _target = missionNamespace getVariable ['ace_medical_gui_target', objNull];
private _bodyPart = missionNamespace getVariable ['ace_medical_gui_selectedBodyPart', -1];
private _selectedCategory = missionNamespace getVariable ['ace_medical_gui_selectedCategory', ''];

// ACE calls the menu painter from a 0-delay PFH. Re-evaluating every grouped action, inventory count, tooltip,
// handler and control on every rendered frame is unnecessary and disproportionately hurts lower-FPS clients.
// Patient/body-part/category changes bypass the throttle and repaint immediately.
private _paintKey = [_target, _bodyPart, _selectedCategory];
private _lastPaintKey = _display getVariable ['ACME_menuPaintKey', []];
private _nextPaint = _display getVariable ['ACME_menuNextPaint', 0];
if (_paintKey isEqualTo _lastPaintKey && {diag_tickTime < _nextPaint}) exitWith {};
_display setVariable ['ACME_menuPaintKey', _paintKey];
_display setVariable ['ACME_menuNextPaint', diag_tickTime + 0.10];
// B44: this ACE category is airway plus breathing work, not airway alone.
private _airwayTab = _display displayCtrl 1340;
if (!isNull _airwayTab) then {_airwayTab ctrlSetTooltip "Airway / Breathing";};

private _asBool = {
    params ['_v'];
    if (isNil '_v') exitWith {false};
    if (_v isEqualType false) exitWith {_v};
    if (_v isEqualType 0) exitWith {_v != 0};
    if (_v isEqualType '') exitWith {(toLower _v) in ['1', 'true', 'yes', 'on', 'enabled']};
    false
};

private _leftRaw = missionNamespace getVariable ['ACME_a11y_menuLeftAlign', false];
if (!isNil 'CBA_settings_fnc_get') then {
    private _cbaVal = ['ACME_a11y_menuLeftAlign'] call CBA_settings_fnc_get;
    if (!isNil '_cbaVal') then { _leftRaw = _cbaVal; };
};
private _leftAlign = [_leftRaw] call _asBool;
private _clinicalDescriptors = ((missionNamespace getVariable ['ACME_hc_descriptors', false]) isEqualTo true);

private _group = _display displayCtrl 1599;  // idc_action_button_group.
if (isNull _group) exitWith {};

// ACE opens a fresh display after treatments and minigames. Restore this patient's
// last explicit section decisions, including keys whose actions are temporarily absent.
if (isNil {_display getVariable 'ACME_menuTarget'} || {
    _target isNotEqualTo (_display getVariable ['ACME_menuTarget', objNull])
}) then {
    _display setVariable ['ACME_menuTarget', _target];
    _display setVariable ['ACME_menuOpen', ['read', _target] call ACME_fnc_menuDropdownState];
};

// Repeated CBA notifications with the same value must not reset an open group.
// Grouping selects its own readable alignment without changing the saved flat-menu setting.
private _nestEnabled = [missionNamespace getVariable ['ACME_menuNestEnabled', true]] call _asBool;
_leftAlign = _leftAlign || {_nestEnabled};
missionNamespace setVariable ['ACME_leftAlign_resolved', _leftAlign, false];
// Turning grouping off only hides the headers; it does not close their saved sections.
_display setVariable ['ACME_menuNestSetting', _nestEnabled];

// Keep handles in row order. ctrlCreate appends a replacement to the engine control list.
// Re-reading allControls after replacing one row would reorder this cache on the next update.
if ((_display getVariable ['ACME_menuButtonGroup', controlNull]) isNotEqualTo _group) then {
    { ctrlDelete _x; } forEach (allControls _group);
    _display setVariable ['ACME_menuButtonGroup', _group];
    _display setVariable ['ACME_menuButtons', []];
};
private _actionButtons = +(_display getVariable ['ACME_menuButtons', []]);

// Handle triage through the native updater. Keep the open groups for a return to treatment.
private _ctrlTriage = _display displayCtrl 1400;
private _showTriage = _selectedCategory == 'triage';
if (!isNull _ctrlTriage) then {
    _ctrlTriage ctrlEnable _showTriage;
    lbClear _ctrlTriage;
};
_group ctrlEnable !_showTriage;
if (_showTriage) exitWith {
    { if (!isNull _x) then { ctrlDelete _x; }; } forEach _actionButtons;
    _display setVariable ['ACME_menuButtons', []];
    if (!isNull _ctrlTriage) then {
        [_ctrlTriage, _target] call ace_medical_gui_fnc_updateTriageCard;
    };
};

// Build display-local headers only when grouping is enabled. The collected actions already
// carry the correct categories and order for both grouped and flat menus.
private _menuActions = missionNamespace getVariable ['ace_medical_gui_actions', []];
// Check Airway and Check Breathing are head-only assessments. canTreatCached deliberately keeps these evidence
// checks available on corpses for AAR/training continuity, so the paint layer must not reintroduce a death-only
// gate which leaks patient death. Re-apply anatomy only because grouped children replace their condition after collection.
_menuActions = _menuActions select {
    private _class = toLower (_x param [8, '']);
    !(_class in ['checkairway', 'checkbreathing']) || {_bodyPart == 0 && {!isNull _target}}
};

// Do not retain a cached positioning row after the casualty stands up.
_menuActions = _menuActions select {
    (toLower (_x param [8, ''])) != 'acme_elevatehead'
        || {[_target, ACE_player] call ACME_fnc_headElevateCanStart}
};

// Dog tags always remain the last standalone examination, even if another addon
// supplied group metadata or the native collector fallback has no class metadata.
private _dogTagLabel = getText (configFile >> 'ace_medical_treatment_actions' >> 'CheckDogTags' >> 'displayName');
private _isDogTag = {
    private _class = toLower (_this param [8, '']);
    (_this param [1, '']) == 'examine' && {
        _class == 'checkdogtags' || {
            _class == '' && {_dogTagLabel != ''} && {(_this param [0, '']) == _dogTagLabel}
        }
    }
};
private _dogTags = _menuActions select {_x call _isDogTag};
_menuActions = _menuActions select {!(_x call _isDogTag)};
_dogTags = _dogTags apply {
    private _row = +_x;
    _row set [7, ''];
    _row
};
// Stop Direct Pressure is always the first treatment row whenever its normal condition makes it visible. Apply
// Direct Pressure follows it, still ahead of bandage headers/actions. Use stable treatment classes, never labels.
private _stopPressure = _menuActions select {toLower (_x param [8, '']) == 'acme_stopdirectpressure'};
private _pressure = _menuActions select {toLower (_x param [8, '']) == 'acme_directpressure'};
_menuActions = _menuActions select {
    private _class = toLower (_x param [8, '']);
    !(_class in ['acme_stopdirectpressure', 'acme_directpressure'])
};
if (_nestEnabled) then {
    private _groups = (missionNamespace getVariable ['ACME_menuGroups', []]) select {
        (_x select 2) isEqualTo _selectedCategory && {call (_x param [4, {true}])}
    };
    private _open = +(_display getVariable ['ACME_menuOpen', []]);
    private _markC = missionNamespace getVariable ['ACME_menuMarkClosed', '[ + ]  '];
    private _markO = missionNamespace getVariable ['ACME_menuMarkOpen', '[ - ]  '];
    private _indent = missionNamespace getVariable ['ACME_menuChildIndent', '        '];
    private _buckets = createHashMap;
    private _nameKeys = createHashMap;
    {
        _x params ['_key', '', '', '_names'];
        _buckets set [_key, []];
        {
            // The first active group owns a fallback name. Explicit class metadata wins.
            if !(_x in _nameKeys) then {_nameKeys set [_x, _key];};
        } forEach _names;
    } forEach _groups;
    private _out = [];
    {
        _x params ['_name', '_category', '_condition'];
        if (_category isEqualTo _selectedCategory) then {
            private _key = _x param [9, ''];
            if !(_key in _buckets) then {_key = _nameKeys getOrDefault [_name, ''];};
            if (_key == '') then {
                _out pushBack _x;
            } else {
                // Evaluate each grouped treatment condition once, including closed groups.
                if (call _condition) then {(_buckets get _key) pushBack _x;};
            };
        };
    } forEach _menuActions;
    {
        _x params ['_key', '_label', '_cat', '_names', ['_vis', {true}], ['_colr', []]];
        private _live = _buckets get _key;
        if (_live isNotEqualTo []) then {
            // Internal route keys remain stable when the descriptor setting changes live.
            switch (_key) do {
                case 'route_po': {_label = ['By Mouth', 'PO'] select _clinicalDescriptors;};
                case 'route_in': {_label = ['Inhaled', 'IN'] select _clinicalDescriptors;};
                case 'route_buc': {_label = ['Buccal', 'BUC'] select _clinicalDescriptors;};
            };
            private _isOpen = _key in _open;
            private _hdrCol = missionNamespace getVariable ['ACME_menuHeaderColorDefault', [1, 0.96, 0.84, 1]];
            if (([missionNamespace getVariable ['ACME_menuColorHeaders', false]] call _asBool)
                && {_colr isEqualType []} && {count _colr >= 3}) then {
                _hdrCol = _colr;
            };
                _out pushBack [
                    format ['%1%2', ([_markC, _markO] select _isOpen), _label],
                    _selectedCategory, {true},
                    {
                        params ['_button'];
                        private _menu = ctrlParent _button;
                        if (isNull _menu) exitWith {};
                        private _patient = missionNamespace getVariable ['ace_medical_gui_target', objNull];
                        // Reject a header left over from a patient change before the next UI pass.
                        if ((_button getVariable ['ACME_menuRowTarget', objNull]) isNotEqualTo _patient) exitWith {};
                        if ((_menu getVariable ['ACME_menuTarget', objNull]) isNotEqualTo _patient) exitWith {};
                        private _key = _button getVariable ['ACME_menuGroupKey', ''];
                        if (_key isEqualTo '') exitWith {};
                        private _open = ['toggle', _patient, _key] call ACME_fnc_menuDropdownState;
                        _menu setVariable ['ACME_menuOpen', _open];
                        // Make dropdown clicks visible on the next ACE UI pass instead of waiting for the normal paint cadence.
                        _menu setVariable ['ACME_menuNextPaint', 0];
                    }, [], '', _hdrCol, _key
                ];
            if (_isOpen) then {
                {
                    private _child = +_x;
                    _child set [0, format ['%1%2', _indent, _x select 0]];
                    _child set [2, {true}];
                    _out pushBack _child;
                } forEach _live;
            };
        };
    } forEach _groups;
    _menuActions = _out;
};

_menuActions = _stopPressure + _pressure + _menuActions + _dogTags;
private _shownIndex = 0;
private _actionIndex = 0;
{
    // Slots 6/7 are optional color/header metadata; slot 8 is the treatment class.
    // Native rows keep their original callback. Short drag/position rows have no item list.
    _x params ['_displayName', '_category', '_condition', '_statement', ['_items', []], ['_menuIcon', ''], ['_rowColor', []], ['_groupKey', '']];

    if (_category == _selectedCategory && {call _condition}) then {
        private _baseIcon = ['None', _menuIcon] select (_menuIcon != '');
        if ((_baseIcon select [0, 2]) == 'L_') then { _baseIcon = _baseIcon select [2]; };

        // ACM's treatment actions use lowercase item class spelling for the IVs, ACM_IV_16g and ACM_IV_14g, and ACM's gui
        // action-button classes are declared with an uppercase g, ACM_IV_16G and ACM_IV_14G.
        // do not create case-only alias classes in config.cpp, because arma config member names collide on case.
        switch (_baseIcon) do {
            case 'ACM_IV_16g': { _baseIcon = 'ACM_IV_16G'; };
            case 'ACM_IV_14g': { _baseIcon = 'ACM_IV_14G'; };
        };

        private _buttonClass = format ['ACM_MedicalMenu_ActionButton_%1', _baseIcon];
        if (_leftAlign) then {
            private _leftClass = format ['ACM_MedicalMenu_ActionButton_L_%1', _baseIcon];
            if (isClass (configFile >> _leftClass)) then { _buttonClass = _leftClass; };
        };
        if !(isClass (configFile >> _buttonClass)) then {
            _buttonClass = ['ACM_MedicalMenu_ActionButton_None', 'ACM_MedicalMenu_ActionButton_L_None'] select (_leftAlign && {isClass (configFile >> 'ACM_MedicalMenu_ActionButton_L_None')});
        };

        // Replace only a missing row or a changed class. Open groups and live action conditions
        // do not require clearing the whole list or waiting for a later frame to rebuild it.
        private _ctrl = _actionButtons param [_shownIndex, controlNull];
        if (isNull _ctrl || {(_ctrl getVariable ['ACME_menuButtonClass', '']) isNotEqualTo _buttonClass}) then {
            if (!isNull _ctrl) then { ctrlDelete _ctrl; };
            _ctrl = _display ctrlCreate [_buttonClass, -1, _group];
            _ctrl setVariable ['ACME_menuButtonClass', _buttonClass];
            _actionButtons set [_shownIndex, _ctrl];
        };
        _ctrl setVariable ['ACME_menuGroupKey', _groupKey];
        _ctrl setVariable ['ACME_menuRowTarget', _target];
        _ctrl ctrlRemoveAllEventHandlers 'ButtonClick';
        _ctrl ctrlSetPositionY (((((safezoneW / safezoneH) min 1.2) / 1.2) / 25) * (1.1 * _shownIndex));
        _ctrl ctrlCommit 0;

        private _countText = '';
        if (_items isNotEqualTo []) then {
            if ('ACE_surgicalKit' in _items && {(missionNamespace getVariable ['ace_medical_treatment_consumeSurgicalKit', 0]) == 2}) then {
                _items = ['ACE_suture'];
            };
            private _counts = [_items] call ace_medical_gui_fnc_countTreatmentItems;
            _countText = _counts call ace_medical_gui_fnc_formatItemCounts;
        };
        _ctrl ctrlSetTooltipColorText [1, 1, 1, 1];
        _ctrl ctrlSetTooltip _countText;

        private _tourniquets = _target getVariable ['ace_medical_tourniquets', [0,0,0,0,0,0]];
        private _hasTQ = _bodyPart >= 0 && {_bodyPart < count _tourniquets} && {(_tourniquets select _bodyPart) > 0};
        if (
            (missionNamespace getVariable ['ace_medical_gui_tourniquetWarning', true]) &&
            {(_category in ['examine', 'medication']) || {(_items findIf {'IV' in _x}) > -1}} &&
            {_hasTQ}
        ) then {
            _ctrl ctrlSetTooltipColorText [1, 1, 0, 1];
            _ctrl ctrlSetTooltip localize 'STR_ACE_medical_gui_TourniquetWarning';
        };

        // hardcore site descriptors. this is the single place ACE paints an action button label, so the rename
        // happens here rather than in a per-frame PFH racing ACE's own paint. _bodyPart is the real selected
        // index read above, so the limb is known rather than guessed from the button text.
        private _actionClass = toLower (_x param [8, '']);
        private _paintName = _displayName;
        // Clinical-descriptor wording: auscultation is the actual examination being performed.
        // Keep the ordinary ACM wording when descriptors are off.
        if (_actionClass == 'usestethoscope') then {
            // B47: normalize the stethoscope child label before adding indentation.  This gives Auscultate Chest
            // exactly the same one-indent padding as every other grouped submenu item and prevents inherited/
            // recycled text from accumulating a second indent on later paints.
            private _indent = missionNamespace getVariable ['ACME_menuChildIndent', '        '];
            // B54: a grouped child carries the indent prefix on its display name (see the nesting block above) and
            // an empty group key; only headers carry a key. B47 tested the key, so the indent it stripped from the
            // child name was never put back. Test the prefix itself.
            private _wasChild = _nestEnabled && {(count _displayName) >= (count _indent)}
                && {(_displayName select [0, count _indent]) == _indent};
            private _baseName = _displayName;
            if (_clinicalDescriptors) then {_baseName = 'Auscultate Chest';};
            while {(count _baseName) >= (count _indent) && {(_baseName select [0, count _indent]) == _indent}} do {
                _baseName = _baseName select [count _indent];
            };
            _paintName = if (_wasChild) then {
                format ['%1%2', _indent, _baseName]
            } else {
                _baseName
            };
        };
        _ctrl ctrlSetText ([_paintName, _bodyPart, true, _actionClass] call ACME_fnc_ivSiteRelabel);
        // the color is set on every row, every frame, with no conditional branch that skips it. these controls are
        // recycled between renders, so a row left uncolored keeps whatever the previous occupant of that handle had.
        // that is the same failure that produced the blinking box in an earlier build: a retained handle being painted
        // after its owner was gone. hence the explicit default rather than an if with no else.
        // it is routed through ACME_fnc_cbColor, so the colorblind mode applies here like everywhere else. protect stops
        // a correction from pushing a header down into the dark background, because a correction that makes something
        // harder to see is worse than no correction.
        // Count only visible treatment rows. Headers and ineligible actions never
        // advance the stripe, so every rendered list starts with a white action.
        // v1.1.0: ordinary medical-menu actions are uniformly white. The former alternating pale-red
        // stripe was purely decorative and made every other action look like a warning/error state.
        private _defaultColor = missionNamespace getVariable ['ACME_menuRowColorDefault', [1, 1, 1, 1]];
        private _textColor = [_defaultColor, _rowColor] select (_rowColor isEqualType [] && {(count _rowColor) >= 3});
        _ctrl ctrlSetTextColor ([_textColor, 'protect'] call ACME_fnc_cbColor);
        if (_groupKey == '') then {_actionIndex = _actionIndex + 1;};
        _ctrl ctrlShow true;
        // Match ACE's normal treatment lifecycle exactly: run the treatment statement first, then arm the reopen
        // flag. Direct Pressure Apply/Stop are immediate in-place state toggles, so they never touch pendingReopen.
        _ctrl ctrlAddEventHandler ['ButtonClick', _statement];
        if (_groupKey isEqualTo '' && {!(_actionClass in ['acme_directpressure', 'acme_stopdirectpressure'])}) then {
            _ctrl ctrlAddEventHandler ['ButtonClick', {
                // Chest-access preflight closes the medical menu on the accepted click and owns cancellation/reopen.
                // Do not let ACE's generic post-click handler reopen it over the carrier/Semi-Fowler animation.
                if !(ACE_player getVariable ["ACME_chestAccessPreflightActive", false]) then {
                    ace_medical_gui_pendingReopen = true;
                };
            }];
        };

        _shownIndex = _shownIndex + 1;
    };
} forEach _menuActions;

// Remove only unused tail controls. Store the same ordered handles for the next live update.
{ if (!isNull _x) then { ctrlDelete _x; }; } forEach (_actionButtons select [_shownIndex]);
_actionButtons resize _shownIndex;
_display setVariable ['ACME_menuButtons', _actionButtons];
missionNamespace setVariable ['ACME_leftAlign_diag', [true, 'renderer', _leftAlign, _shownIndex, 0], false];
