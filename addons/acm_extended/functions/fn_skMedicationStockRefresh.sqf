/* B48: put vial contents/count into the right side of ACM's native medication listbox.
   This deliberately avoids runtime-created child text controls: the medication label, icon and stock text all
   belong to one native RscListBox row, so they cannot become detached/blank independently. */
disableSerialization;
params [["_display", displayNull, [displayNull]]];
if (isNull _display) exitWith {};
private _list = _display displayCtrl 84006;
if (isNull _list) exitWith {};
private _holder = [ACE_player] call ACME_fnc_vialHolder;
if (isNull _holder) exitWith {
    for "_i" from 0 to ((lbSize _list) - 1) do {_list lbSetTextRight [_i, ""];};
};

private _rows = _display getVariable ["ACME_SK_MedicationRows", []];
private _stage = uiNamespace getVariable ["ACME_SK_WasteStage", ""];
private _sel = lbCurSel _list;
private _sessions = _display getVariable ["ACME_SK_VialSessions", createHashMap];

for "_i" from 0 to ((lbSize _list) - 1) do {
    private _med = _list lbData _i;
    if (_med == "") then {
        _list lbSetTextRight [_i, ""];
        continue;
    };

    private _reserved = 0;
    if (_stage in ["compound","draw"]) then {
        {
            if ((_x param [0, ""]) == _med) then {_reserved = _reserved + (_x param [1, 0]);};
        } forEach (uiNamespace getVariable ["ACME_SK_CompoundComponents", []]);
        if (_i == _sel) then {
            _reserved = _reserved + (((uiNamespace getVariable ["ACME_SK_WasteFill", 0])
                - (uiNamespace getVariable ["ACME_SK_WasteFloorMl", 0])) max 0);
        };
    } else {
        if (_stage == "" && {_i == _sel}) then {
            _reserved = missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0];
        };
    };

    private _physicalClass = "";
    private _ri = _rows findIf {(_x param [1, ""]) == _med};
    if (_ri >= 0) then {_physicalClass = (_rows select _ri) param [3, ""];};

    private _curMl = 0;
    private _vials = 0;
    private _total = 0;
    private _bound = !((_sessions getOrDefault [_med, []]) isEqualTo []);
    if (_bound) then {
        (["preview", _med, _reserved, _display] call ACME_fnc_vialSession) params ["_curB", "_vialsB", "_totalB", ""];
        _curMl = _curB;
        _vials = _vialsB;
        _total = _totalB;
    } else {
        ([_holder, _med, _reserved, _physicalClass] call ACME_fnc_vialPreview) params ["_vialsP", "_curP", "", "_totalP"];
        _curMl = _curP;
        _vials = _vialsP;
        _total = _totalP;
    };
    if (_physicalClass != "" && {_vials <= 0} && {_total <= 0.000001}) then {
        private _directCount = [_holder, _physicalClass] call ACME_fnc_vialItemCount;
        if (_med == "EpinephrineCardiac") then {
            _directCount = ([_holder, "ACME_Vial_EpinephrineCardiac"] call ACME_fnc_vialItemCount)
                + ([_holder, "ACME_Vial_EpinephrineCardiac"] call ACME_fnc_vialItemCount);
        };
        private _cap = [_med] call ACME_fnc_vialCapacity;
        if (_directCount > 0 && {_cap > 0}) then {
            _vials = _directCount;
            _curMl = _cap;
            _total = _directCount * _cap;
        };
    };

    private _count = str (_vials max 0);
    while {count _count < 2} do {_count = "0" + _count;};
    private _stock = format ["%1 mL  x%2", _curMl toFixed 2, _count];
    _list lbSetTextRight [_i, ""];
    private _label = _list lbText _i;
    _list lbSetTooltip [_i, format ["%1  |  %2", _label, _stock]];
};
