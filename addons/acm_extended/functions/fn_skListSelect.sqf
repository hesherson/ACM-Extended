/* Validate inventory at click time, before changing native selection or discarding a draw. */
params ["_button"];
private _d = ctrlParent _button;
(_button getVariable ["ACME_SK_Row", []]) params ["_kind", "_nativeID", "_data", "_value", "_item", "_back", "_label"];
private _list = _d displayCtrl _nativeID;
private _available = _item == "" || {([ACE_player, uiNamespace getVariable ["ACME_SK_Patient",objNull], _item] call ACME_fnc_treatmentSupplyCount) > 0};
if (_kind == "medication") then {
    private _holder = [ACE_player] call ACME_fnc_vialHolder;
    if (isNull _holder) then {_available = false;} else {
        private _pv = [_holder, _data, 0, _item] call ACME_fnc_vialPreview;
        _available = (_pv param [3, 0]) > 0.000001;
    };
};
if (!_available) exitWith {_back setVariable ["ACME_SK_FlashAt", diag_tickTime];};

private _stage = uiNamespace getVariable ["ACME_SK_WasteStage", ""];
private _nativeMoving = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Moving", false];
private _infusionMode = !((_d getVariable ["ACME_SK_Return", []]) isEqualTo []);
private _currentSessionMed = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medication", ""];
private _sameMedInfusionClick = _infusionMode && {_kind == "medication"} && {_data == _currentSessionMed};

// Native ACM disables its backing medication list as soon as solution is in the syringe.
// The visible ACME row may still be clicked for the SAME medication to deliberately bind the
// next vial after the current one reaches 0.00 mL. Different medications remain blocked below.
if (_kind == "medication" && {
    (_stage in ["compound","draw"] && {uiNamespace getVariable ["ACME_SK_WasteMoving", false]})
    || {!(_stage in ["compound","draw"]) && {_nativeMoving}}
    || {!(_stage in ["compound","draw"]) && {!(ctrlEnabled _list)} && {!_sameMedInfusionClick}}
}) exitWith {};

// An infusion syringe may never be relabeled while it contains solution. In compound mode use
// WasteFill; in the native Prep Infusion path use the actual ACM DrawnAmount.
if (_kind == "medication" && {_infusionMode}) then {
    private _fill = if (_stage in ["compound","draw"]) then {
        uiNamespace getVariable ["ACME_SK_WasteFill", 0]
    } else {
        missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0]
    };
    private _currentMed = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medication", ""];
    if (_fill > 0.0005 && {_currentMed != ""} && {_data != _currentMed}) exitWith {
        _back setVariable ["ACME_SK_FlashAt", diag_tickTime];
    };
};

private _index = -1;
if (_kind == "medication") then {
    for "_i" from 0 to ((lbSize _list) - 1) do {
        if ((_list lbData _i) == _data) exitWith {_index = _i;};
    };
    if (_index < 0) then {
        [_d] call ACME_fnc_skMedicationSync;
        for "_i" from 0 to ((lbSize _list) - 1) do {
            if ((_list lbData _i) == _data) exitWith {_index = _i;};
        };
    };
} else {
    for "_i" from 0 to ((lbSize _list) - 1) do {
        if (
            (_kind == "flush" && {(_list lbData _i) == _data})
            || {_kind != "flush" && {(_list lbValue _i) == _value} && {(_list lbText _i) == _label}}
        ) exitWith {_index = _i;};
    };
};

if (_index < 0 && {_kind == "medication"} && {_data == "EpinephrineCardiac"}) then {
    [_d] call ACME_fnc_skEpinephrineStock;
    for "_i" from 0 to ((lbSize _list) - 1) do {
        if ((_list lbData _i) == _data) exitWith {_index = _i;};
    };
};
if (_index < 0) exitWith {_back setVariable ["ACME_SK_FlashAt", diag_tickTime];};

if (_kind == "size"
    && {_value == (uiNamespace getVariable ["ACME_SK_CurSize", 10])}
    && {(uiNamespace getVariable ["ACME_SK_WasteStage", ""]) == "compound"}) exitWith {};

private _same = (lbCurSel _list) == _index;
_list lbSetCurSel _index;

// A changed medication selection fires LBSelChanged and skMedicationSelect owns the vial binding.
// Only an intentional click on the ALREADY-selected medication needs a manual select call, because
// LBSelChanged does not fire for the same row. This guarantees one click can unlock at most one vial.
if (_kind == "medication" && {_same}) then {
    private _reserved = 0;
    private _stageNow = uiNamespace getVariable ["ACME_SK_WasteStage", ""];
    if (_stageNow in ["compound","draw"]) then {
        {
            if ((_x param [0,""]) == _data) then {
                _reserved = _reserved + (_x param [1,0]);
            };
        } forEach (uiNamespace getVariable ["ACME_SK_CompoundComponents", []]);

        if ((missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medication", ""]) == _data) then {
            _reserved = _reserved + (((uiNamespace getVariable ["ACME_SK_WasteFill", 0])
                - (uiNamespace getVariable ["ACME_SK_WasteFloorMl", 0])) max 0);
        };
    } else {
        if ((missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medication", ""]) == _data) then {
            _reserved = missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0];
        };
    };

    private _selectedLimit = ["select", _data, _reserved, _d] call ACME_fnc_vialSession;
    private _size = (missionNamespace getVariable ["ACM_circulation_SyringeDraw_Size", 10]) max 0.1;
    missionNamespace setVariable ["ACM_circulation_SyringeDraw_MaxDose", (_selectedLimit max 0) min _size];
    [_d] call ACME_fnc_skMedicationStockRefresh;
};

// LBSelChanged does not fire when selecting the same flush/drawn row twice.
if (_same) then {
    switch (_kind) do {
        case "size": {[_list, _index] call ACME_fnc_skPickSize;};
        case "flush": {[_list, _index] call ACME_fnc_skPickFlush;};
        case "drawn": {[_list, _index] call ACME_fnc_skPickDrawn;};
    };
};
