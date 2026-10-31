// The single ACME debug overlay. Clinical, treatment and transport state share one patient and one toggle.
// B221 restores B218 presentation helpers; data additions and the missing-color fix stay intact.
disableSerialization;

private _cleanup = {
    {
        private _c = uiNamespace getVariable [_x, controlNull];
        if (!isNull _c) then {ctrlDelete _c;};
        uiNamespace setVariable [_x, controlNull];
    } forEach ["ACME_DebugMenuBackdrop", "ACME_DebugMenuCtrl", "ACME_DebugMenuCtrlTop", "ACME_DebugMenuCtrlL", "ACME_DebugMenuCtrlR", "ACME_DebugMenuCtrlS", "ACME_DebugMenuCtrlMeasure"];
};
if (!(call ACME_fnc_debugEnabled)) exitWith {call _cleanup;};
private _display = findDisplay 46;
if (isNull _display) then {_display = uiNamespace getVariable ["RscDisplayMission", displayNull];};
if (isNull _display) exitWith {call _cleanup;};

// Recreate older overlays before adding the backing, so it is always below every text control.
private _backdrop = uiNamespace getVariable ["ACME_DebugMenuBackdrop", controlNull];
if (isNull _backdrop || {!((ctrlParent _backdrop) isEqualTo _display)}) then {call _cleanup;};
private _control = {
    params ["_key", ["_visible", true]];
    private _c = uiNamespace getVariable [_key, controlNull];
    if (!isNull _c && {!((ctrlParent _c) isEqualTo _display)}) then {ctrlDelete _c; _c = controlNull;};
    if (isNull _c) then {_c = _display ctrlCreate ["RscStructuredText", -1];};
    uiNamespace setVariable [_key, _c];
    _c ctrlSetBackgroundColor [0, 0, 0, 0];
    _c ctrlShow _visible;
    _c
};
private _ctrlB = ["ACME_DebugMenuBackdrop"] call _control;
_ctrlB ctrlSetBackgroundColor [0.043, 0.082, 0.188, 0.74];
_ctrlB ctrlEnable false;
private _ctrlH = ["ACME_DebugMenuCtrl"] call _control;
private _ctrlT = ["ACME_DebugMenuCtrlTop", false] call _control;
private _ctrlL = ["ACME_DebugMenuCtrlL"] call _control;
private _ctrlR = ["ACME_DebugMenuCtrlR", false] call _control;
private _ctrlS = ["ACME_DebugMenuCtrlS", false] call _control;
private _ctrlM = ["ACME_DebugMenuCtrlMeasure", false] call _control;

// B176 resolution invariant: the debug overlay is one fixed-proportion strip pinned to the absolute left safe edge.
// Resolution, aspect ratio and UI scale may change the engine safe-zone coordinates, but every visible dimension below
// derives from the SAME safe-zone box and every text control receives the SAME final font scale.
private _baseFontH = safeZoneH * 0.0092;
private _fontH = _baseFontH;
private _applyFont = {
    {_x ctrlSetFontHeight _fontH;} forEach [_ctrlH, _ctrlT, _ctrlL, _ctrlR, _ctrlS, _ctrlM];
};
call _applyFont;

private _gapFactor = 0.26;
private _gap = _fontH * _gapFactor;
private _marginX = safeZoneH * 0.0025;
private _marginY = safeZoneH * 0.004;
private _x = safeZoneXAbs + _marginX;
private _y = safeZoneY + _marginY;
private _panelBottom = safeZoneY + safeZoneH - _marginY;

// B215: this is a width ceiling, not a fixed backdrop width. Final measured content determines the right edge
// after both width and height fitting; the strip always stays below one quarter of the screen.
private _totalW = (safeZoneH * 0.40) min (safeZoneWAbs * 0.245) min (safeZoneWAbs - (2 * _marginX));
private _valueW = 11;

private _renderBlock = {
    params ["_ctrl", "_rows"];
    _ctrl ctrlSetStructuredText parseText format ["<t font='EtelkaMonospacePro' shadow='1'>%1</t>", _rows joinString "<br/>"];
};
private _measureRows = {
    params ["_rows", "_width"];
    _ctrlM ctrlSetPosition [_x, _y, _width, safeZoneH * 4];
    _ctrlM ctrlCommit 0;
    [_ctrlM, _rows] call _renderBlock;
    (ctrlTextHeight _ctrlM) + (_fontH * 0.18)
};
private _measureNaturalWidth = {
    params ["_rows"];
    // Give the hidden measurement control deliberately excessive width so this pass measures the natural longest
    // line rather than a wrapped line. The final common font scale is then reduced until that line fits _totalW.
    _ctrlM ctrlSetPosition [_x, _y, safeZoneWAbs * 8, safeZoneH * 4];
    _ctrlM ctrlCommit 0;
    [_ctrlM, _rows] call _renderBlock;
    (ctrlTextWidth _ctrlM) + (safeZoneH * 0.005)
};
private _layout = {
    params ["_headerH", "_bodyH"];
    private _topPadding = _fontH * 0.75;
    private _bodyY = _y + _topPadding + _headerH + _gap;
    private _panelH = (_panelBottom - _y) max 0;
    // Never allow the structured-text control itself to extend below the panel. The previous layout expanded
    // the body to its measured content height, which is exactly how 1680x1050 drew text past the bottom edge.
    private _bodyAvail = (_panelBottom - _bodyY) max 0;

    _ctrlB ctrlSetPosition [_x, _y, _totalW, _panelH];
    _ctrlH ctrlSetPosition [_x, _y + _topPadding, _totalW, _headerH min ((_panelH - _topPadding) max 0)];
    _ctrlL ctrlSetPosition [_x, _bodyY min _panelBottom, _totalW, _bodyAvail];

    // Retire B162's separate top/right/footer regions in-place so an already running mission cannot leave one visible.
    {_x ctrlShow false;} forEach [_ctrlT, _ctrlR, _ctrlS];
    {_x ctrlCommit 0;} forEach [_ctrlB, _ctrlH, _ctrlL, _ctrlT, _ctrlR, _ctrlS];
};

private _cTitle = "#D9A441";
private _cSect  = _cTitle;
private _cLabel = "#C0B7A2";
private _cGood  = "#5FB56E";
private _cWarn  = "#D9A441";
private _cBad   = "#E04141";
private _cCrit  = "#FF5A5A";
private _cMute  = "#8A8474";
// Same airway/device blue as the ACE medical-menu chest-tube markers (0.19, 0.91, 0.93).
private _cTube  = "#30E8ED";

private _safe = {
    params ["_v"];
    private _s = if (_v isEqualType "") then {_v} else {str _v};
    _s = (_s splitString "&") joinString "&amp;";
    _s = (_s splitString "<") joinString "&lt;";
    _s = (_s splitString ">") joinString "&gt;";
    _s
};
private _yn = {params ["_v"]; if (_v) then {"yes"} else {"no"};};
private _ynCol = {params ["_v", ["_badWhenTrue", false]]; if (_badWhenTrue) exitWith {if (_v) then {_cBad} else {_cGood}}; if (_v) then {_cGood} else {_cMute};};
// All values start at the same column: words, integers, decimals and units use
// trailing padding only. The paired field width protects the next label.
private _padRight = {
    params ["_s", "_w"];
    if !(_s isEqualType "") then {_s = str _s;};
    while {count _s < _w} do {_s = _s + " ";};
    _s
};
private _alignValue = {
    params ["_v", ["_w", 11]];
    private _s = if (_v isEqualType "") then {_v} else {str _v};
    [_s, _w] call _padRight
};
private _pair = {
    // B221: an odd medication catalog ends in a single triplet. Never expand
    // it into undefined right-hand values/colors (RPT: Wrong color format any).
    if (count _this == 3) exitWith {_this call _one};
    params ["_a", "_av", "_ac", "_b", "_bv", "_bc"];
    if (_av in ["yes", "no"] && {(_a select [(count _a - 1) max 0]) != "?"}) then {_a = _a + "?";};
    if (_bv in ["yes", "no"] && {(_b select [(count _b - 1) max 0]) != "?"}) then {_b = _b + "?";};
    [_a, _av, _ac, _b, _bv, _bc]
};
private _one = {
    params ["_a", "_av", "_ac"];
    if (_av in ["yes", "no"] && {(_a select [(count _a - 1) max 0]) != "?"}) then {_a = _a + "?";};
    [_a, _av, _ac]
};
private _wrapValue = {
    params ["_s", "_width"];
    private _lines = [];
    while {count _s > _width} do {
        private _cut = _width;
        // Prefer a word/device boundary; keep all characters, including signs, units and separators.
        for "_i" from (_width - 1) to 1 step -1 do {
            if ((_s select [_i, 1]) in [" ", "+", ",", "/"]) exitWith {_cut = _i + 1;};
        };
        // Do not create an empty continuation line at a padding boundary.
        if ((_s select [0, _cut]) == (["", _cut] call _padRight)) then {_cut = _width;};
        _lines pushBack (_s select [0, _cut]);
        _s = _s select [_cut];
    };
    _lines pushBack _s;
    _lines
};
private _formatRow = {
    params ["_row", "_valueW", ["_labelWidths", [20, 20]]];
    if (_row isEqualType "") exitWith {_row};
    // A bullet has an explicit depth and spans both columns; it must not widen either label column.
    if (count _row == 4) exitWith {
        _row params ["", "_text", "_color", "_depth"];
        private _indent = if (_depth > 0) then {"    "} else {"  "};
        private _limit = ((_labelWidths select 0) + (_labelWidths select 1) + 2 * _valueW + 10 - count _indent - 2) max 10;
        private _lines = [_text, _limit] call _wrapValue;
        private _formatted = [];
        {
            _formatted pushBack format ["%1%2<t color='%3'>%4</t>", _indent, if (_forEachIndex == 0) then {"• "} else {"  "}, _color, [_x] call _safe];
        } forEach _lines;
        _formatted joinString "<br/>"
    };
    _row params ["_a", "_av", "_ac"];
    // B213: label widths are measured over the whole display, independently for each paired column.
    // Two spaces indent values under section titles. Exactly one space follows the longest label before ':'.
    private _labelW = _labelWidths select 0;
    private _labelWR = _labelWidths select 1;
    private _aTxt = [([_a, _labelW] call _padRight)] call _safe;
    private _avTxt = [([_av, _valueW] call _alignValue)] call _safe;
    if (count _row == 3) exitWith {
        format ["  <t color='%4'>%1 :</t> <t color='%3'>%2</t>", _aTxt, _avTxt, _ac, _cLabel]
    };
    private _b = _row select 3;
    private _bv = _row select 4;
    private _bc = _row select 5;
    private _aLines = [([_av, _valueW] call _alignValue), _valueW] call _wrapValue;
    private _bLines = [([_bv, _valueW] call _alignValue), _valueW] call _wrapValue;
    private _lines = [];
    for "_i" from 0 to (((count _aLines) max (count _bLines)) - 1) do {
        private _aLabel = [([if (_i == 0) then {_a} else {""}, _labelW] call _padRight)] call _safe;
        private _bLabel = [([if (_i == 0) then {_b} else {""}, _labelWR] call _padRight)] call _safe;
        private _aValue = [([_aLines param [_i, ""], _valueW] call _padRight)] call _safe;
        private _bValue = [([_bLines param [_i, ""], _valueW] call _padRight)] call _safe;
        _lines pushBack format ["  <t color='%7'>%1 :</t> <t color='%3'>%2</t>  <t color='%7'>%4 :</t> <t color='%6'>%5</t>", _aLabel, _aValue, _ac, _bLabel, _bValue, _bc, _cLabel];
    };
    _lines joinString "<br/>"
};
private _sect = {params ["_s"]; format ["<br/><t color='%1'>%2</t>", _cSect, _s];};
private _arr = {params ["_name"]; private _v = missionNamespace getVariable [_name, []]; if (_v isEqualType []) then {_v} else {[]};};
private _pushUnique = {params ["_a", "_o"]; if (!isNull _o && {!(_o in _a)}) then {_a pushBack _o;}; _a};

// One target selection is shared by every section.
private _patient = missionNamespace getVariable ["ACME_debug_target", objNull];
if (!isNull _patient && {!(_patient isKindOf "CAManBase")}) then {_patient = objNull;};
if (isNull _patient) then {
    private _last = missionNamespace getVariable ["ACME_debug_lastTreatmentTarget", objNull];
    if (!isNull _last && {_last isKindOf "CAManBase"}) then {_patient = _last;};
};
if (isNull _patient) then {
    private _cands = [];
    {
        { _cands = [_cands, _x] call _pushUnique; } forEach ([_x] call _arr);
    } forEach ["ACME_infusion_activePatients", "ACME_tbi_activePatients", "ACME_circ_activePatients", "ACME_autoBP_patients", "ACME_hpmk_activePatients"];
    if (_cands isEqualTo []) then {_patient = ACE_player;} else {_patient = _cands select 0;};
};

private _ver = getText (configFile >> "CfgPatches" >> "ACM_Extended" >> "version");
if (_ver == "") then {_ver = missionNamespace getVariable ["ACME_infusion_version", "?"];};
private _rc = missionNamespace getVariable ["ACME_debugRevision", ""];
if (_rc isEqualType "" && {_rc != ""}) then {_ver = format ["%1-%2", _ver, _rc];};
private _batch = missionNamespace getVariable ["ACME_buildBatch", "?"];
private _top = [];
private _left = [];
private _right = [];
private _network = [];
private _pName = if (isNull _patient) then {"NO PATIENT"} else {name _patient};
private _bloodTypeID = if (isNull _patient) then {-1} else {_patient getVariable ["ACM_circulation_BloodType", -1]};
private _bloodType = if (_bloodTypeID isEqualType 0 && {_bloodTypeID in [0,1,2,3,4,5,6,7]}) then {
    ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"] select _bloodTypeID
} else {"unknown"};
private _weight = if (isNull _patient) then {-1} else {_patient getVariable ["ACM_core_BodyWeight", 80]};
private _factionClass = if (isNull _patient) then {""} else {faction _patient};
private _factionName = getText (configFile >> "CfgFactionClasses" >> _factionClass >> "displayName");
if (_factionName == "") then {_factionName = ["unknown", _factionClass] select (_factionClass != "");};
private _patientSide = if (isNull _patient) then {"unknown"} else {str side group _patient};
private _sideColor = switch (toUpperANSI _patientSide) do {
    case "WEST": {"#4FA3FF"};
    case "EAST": {"#FF5555"};
    case "CIV": {"#BD83EA"};
    case "GUER": {"#64D978"};
    default {_cMute};
};
private _header = [
    format ["<t size='1.12' color='%1'>ACME DEBUG v%2 | %3</t>", _cTitle, [_ver] call _safe, [_batch] call _safe],
    ["Patient", _pName, _cLabel] call _one,
    ["Blood type", _bloodType, _cLabel, "Weight", if (_weight isEqualType 0 && {_weight > 0}) then {format ["%1 kg", _weight toFixed 1]} else {"unknown"}, _cLabel] call _pair,
    ["Side", _patientSide, _sideColor, "Faction", _factionName, _sideColor] call _pair
];
private _renderAll = {
    // Preserve the existing logical section builders, but serialize them into one compact vertical stream.
    private _allRows = [];
    _allRows append _top;
    _allRows append _network;
    _allRows append _left;
    _allRows append _right;

    // Size paired fields from paired values only. A full-width revision/device row
    // must not widen both columns or shift ordinary readings. Left alignment adds
    // no leading padding beyond these measured strings, so decimals and units fit.
    _valueW = 11;
    {
        if (_x isEqualType [] && {count _x >= 6}) then {
            private _vA = _x param [1, ""];
            private _sA = if (_vA isEqualType "") then {_vA} else {str _vA};
            _valueW = _valueW max (count _sA);
            private _vB = _x param [4, ""];
            private _sB = if (_vB isEqualType "") then {_vB} else {str _vB};
            _valueW = _valueW max (count _sB);
        };
    } forEach _allRows;

    private _labelWidths = [0, 0];
    {
        if (_x isEqualType [] && {count _x in [3, 6]}) then {
            _labelWidths set [0, (_labelWidths select 0) max (count (_x select 0))];
            if (count _x >= 6) then {_labelWidths set [1, (_labelWidths select 1) max (count (_x select 3))];};
        };
    } forEach (_header + _allRows);
    private _headerRows = _header apply {[_x, _valueW, _labelWidths] call _formatRow};
    private _separator = "";
    for "_i" from 1 to ((_labelWidths select 0) + (_labelWidths select 1) + 2 * _valueW + 10) do {_separator = _separator + "_";};
    _separator = format ["<t color='%1'>%2</t>", _cMute, _separator];
    private _bodyRows = [];
    private _hasSection = false;
    {
        private _row = [_x, _valueW, _labelWidths] call _formatRow;
        if (count _row >= 5 && {(_row select [0,5]) == "<br/>"}) then {
            if (_hasSection) then {_bodyRows pushBack _separator;};
            _hasSection = true;
            _row = _row select [5];
        };
        _bodyRows pushBack _row;
    } forEach _allRows;
    if (_hasSection) then {_bodyRows pushBack _separator;};

    // Every refresh starts from the exact same reference font. First fit the natural longest line to the fixed
    // panel width, then fit the complete vertical stream to the fixed panel height. Because both passes multiply
    // the SAME _fontH, width/height/text/spacing preserve one uniform scale on every resolution.
    _fontH = _baseFontH;
    call _applyFont;
    _gap = _fontH * _gapFactor;

    private _naturalW = ([ _headerRows ] call _measureNaturalWidth) max ([_bodyRows] call _measureNaturalWidth);
    if (_naturalW > _totalW && {_naturalW > 0}) then {
        _fontH = _fontH * ((_totalW / _naturalW) min 1);
        call _applyFont;
        _gap = _fontH * _gapFactor;
    };

    private _headerH = [_headerRows, _totalW] call _measureRows;
    private _bodyH = [_bodyRows, _totalW] call _measureRows;
    private _availableH = (_panelBottom - _y) max 0;
    private _neededH = (_fontH * 0.75) + _headerH + _gap + _bodyH;
    if (_neededH > _availableH && {_neededH > 0}) then {
        // Small guard keeps the last descender inside the panel despite engine text-metric rounding.
        _fontH = _fontH * ((_availableH / _neededH) * 0.992);
        call _applyFont;
        _gap = _fontH * _gapFactor;
        _headerH = [_headerRows, _totalW] call _measureRows;
        _bodyH = [_bodyRows, _totalW] call _measureRows;
    };

    // Height fitting can make the text substantially narrower. Measure again at the FINAL font size so
    // the backdrop follows the actual rightmost content instead of leaving the original maximum-width strip.
    _totalW = (([_headerRows] call _measureNaturalWidth) max ([_bodyRows] call _measureNaturalWidth)) min _totalW;
    [_headerH, _bodyH] call _layout;
    [_ctrlH, _headerRows] call _renderBlock;
    [_ctrlL, _bodyRows] call _renderBlock;
};

_top pushBack (["MACHINE / PATIENT OWNERSHIP"] call _sect);
private _role = if (isDedicated) then {"dedi"} else {if (isServer) then {"host"} else {"client"}};
_top pushBack (["Role", _role, if (isServer) then {_cGood} else {_cLabel}, "MP", if (isMultiplayer) then {"yes"} else {"no"}, if (isMultiplayer) then {_cGood} else {_cMute}] call _pair);
_top pushBack (["Client", clientOwner, _cLabel, "Server", if (isServer) then {"local"} else {"remote"}, if (isServer) then {_cGood} else {_cLabel}] call _pair);
private _own = if (isNull _patient) then {"-"} else {if (isServer) then {str owner _patient} else {if (local _patient) then {str clientOwner} else {"remote"}}};
private _loc = !isNull _patient && {local _patient};
private _netId = if (isNull _patient) then {"-"} else {netId _patient};
_top pushBack (["Owner", _own, if (_loc) then {_cGood} else {_cWarn}, "Local", if (_loc) then {"yes"} else {"no"}, if (_loc) then {_cGood} else {_cWarn}] call _pair);
private _epoch = if (isNull _patient) then {-1} else {[_patient] call ACME_fnc_clinicalEpoch};
_top pushBack (["NetID", _netId, _cMute, "Epoch", _epoch, _cLabel] call _pair);

_network pushBack (["RUNTIME / NETWORK"] call _sect);
private _naChest = missionNamespace getVariable ["ACME_NA2_chestInstalled", false];
private _naOwner = missionNamespace getVariable ["ACME_NA2_ownerInstalled", false];
_network pushBack (["Chest", if (_naChest) then {"on"} else {"off"}, if (_naChest) then {_cGood} else {_cBad}, "Owner", if (_naOwner) then {"on"} else {"off"}, if (_naOwner) then {_cGood} else {_cBad}] call _pair);
private _rev = missionNamespace getVariable ["ACME_networkAuditRevision", "none"];
_network pushBack (["Revision", _rev, _cMute] call _one);

_network pushBack (["COMPATIBILITY"] call _sect);
private _networkStatus = missionNamespace getVariable ["ACME_networkCompatStatus", "pending"];
private _serverBuild = missionNamespace getVariable ["ACME_networkCompatServerBuild", "unverified"];
private _networkColor = if (_networkStatus == "ok") then {_cGood} else {if (_networkStatus == "pending") then {_cWarn} else {_cBad}};
_network pushBack (["Network", _networkStatus, _networkColor, "Server", _serverBuild, _networkColor] call _pair);

private _missing = missionNamespace getVariable ["ACME_compatMissing", []];
if !(_missing isEqualType []) then {_missing = [];};
_network pushBack (["Issues", count _missing, if (_missing isEqualTo []) then {_cGood} else {_cBad}, "Checked", if (missionNamespace getVariable ["ACME_compatChecked", false]) then {"yes"} else {"no"}, if (missionNamespace getVariable ["ACME_compatChecked", false]) then {_cGood} else {_cWarn}] call _pair);
{
    _network pushBack format ["<t color='%1'>%2</t>", _cBad, [_x] call _safe];
} forEach (_missing select [0, (count _missing) min 8]);
if ((count _missing) > 8) then {_network pushBack format ["<t color='%1'>+%2 more compatibility issues</t>", _cWarn, (count _missing) - 8];};


if (isNull _patient) exitWith {
    _left pushBack (["Patient", "none", _cWarn] call _one);
    call _renderAll;
};

// Core vitals.
private _hr = if (alive _patient) then {round (_patient getVariable ["ace_medical_heartRate", 0])} else {0};
private _rr = round (_patient getVariable ["ACM_breathing_RespirationRate", 0]);
private _spo2 = round (_patient getVariable ["ace_medical_spo2", 0]);
private _bp = if (!isNil "ace_medical_status_fnc_getBloodPressure") then {[_patient] call ace_medical_status_fnc_getBloodPressure} else {[0,0]};
private _dia = round (_bp param [0, 0]);
private _sys = round (_bp param [1, 0]);
private _map = if (_sys > 0) then {round ((_sys + 2 * _dia) / 3)} else {round (_patient getVariable ["ACM_circulation_MAP", 0])};
private _circState = _patient getVariable ["ACME_circ_State", createHashMap];
private _etco2 = _circState getOrDefault ["etco2Observed", -1];
private _temp = _patient getVariable ["ACME_hypo_temp", 37];
private _pain = _patient getVariable ["ace_medical_pain", 0];
private _uncon = _patient getVariable ["ACE_isUnconscious", false];
private _arrest = _patient getVariable ["ace_medical_inCardiacArrest", false];
private _crit = _patient getVariable ["ACM_core_CriticalVitals_State", false];
private _coLMin = if (!isNil "ace_medical_status_fnc_getCardiacOutput") then {([_patient] call ace_medical_status_fnc_getCardiacOutput) * 60} else {0};

private _hrC = if (_hr <= 0 || {_hr < 40} || {_hr >= 180}) then {_cBad} else {if (_hr < 60 || {_hr >= 130}) then {_cWarn} else {_cGood}};
private _bpC = if (_sys <= 0 || {_sys < 80}) then {_cBad} else {if (_sys < 90 || {_sys > 160}) then {_cWarn} else {_cGood}};
private _mapC = if (_map <= 0 || {_map < 55}) then {_cBad} else {if (_map < 65 || {_map > 110}) then {_cWarn} else {_cGood}};
private _rrC = if (_rr <= 0 || {_rr < 8} || {_rr > 30}) then {_cBad} else {if (_rr < 10 || {_rr > 24}) then {_cWarn} else {_cGood}};
private _spC = if (_spo2 <= 0 || {_spo2 < 90}) then {_cBad} else {if (_spo2 < 94) then {_cWarn} else {_cGood}};
private _tempC = if (_temp < 32 || {_temp >= 40}) then {_cBad} else {if (_temp < 35 || {_temp >= 38.5}) then {_cWarn} else {_cGood}};

_left pushBack (["VITALS"] call _sect);
_left pushBack (["HR", _hr, _hrC, "BP", format ["%1/%2", _sys, _dia], _bpC] call _pair);
_left pushBack (["MAP", _map, _mapC, "RR", _rr, _rrC] call _pair);
_left pushBack (["CO", format ["%1 L/min", _coLMin toFixed 1], if (_coLMin <= 0.01) then {_cBad} else {if (_coLMin < 3) then {_cWarn} else {_cGood}}, "EtCO2", if (_etco2 < 0) then {"n/a"} else {round _etco2}, if (_etco2 < 0) then {_cMute} else {if (_etco2 < 20 || {_etco2 > 55}) then {_cWarn} else {_cGood}}] call _pair);
_left pushBack (["Temp", format ["%1 C", _temp toFixed 1], _tempC, "SpO2", format ["%1%2", _spo2, "%"], _spC] call _pair);
private _stateTxt = if (!alive _patient) then {"DEAD"} else {if (_arrest) then {"ARREST"} else {if (_uncon) then {"UNCON"} else {if (_crit) then {"CRITICAL"} else {"awake"}}}};
private _stateCol = if (!alive _patient || {_arrest}) then {_cCrit} else {if (_uncon || {_crit}) then {_cWarn} else {_cGood}};
_left pushBack (["State", _stateTxt, _stateCol, "Pain", format ["%1%2", round (_pain * 100), "%"], if (_pain > 0.8) then {_cBad} else {if (_pain > 0.4) then {_cWarn} else {_cGood}}] call _pair);

// Perfusion / hemorrhage.
private _normalBlood = missionNamespace getVariable ["ACME_hypo_bloodNormal", 6];
private _circ = _patient getVariable ["ace_medical_bloodVolume", _patient getVariable ["ACME_circulatingVolume", _normalBlood]];
private _blood = _patient getVariable ["ACM_circulation_Blood_Volume", _normalBlood];
private _plasma = _patient getVariable ["ACM_circulation_Plasma_Volume", 0];
private _cryst = _patient getVariable ["ACM_circulation_Saline_Volume", 0];
private _over = _patient getVariable ["ACM_circulation_Overload_Volume", 0];
private _eff = ((_blood + (_plasma * 0.3) - _over) min _normalBlood) max 0;
private _bleedLps = if (!isNil "ace_medical_status_fnc_getBloodLoss") then {[_patient] call ace_medical_status_fnc_getBloodLoss} else {0};
private _bleedMlMin = (_bleedLps max 0) * 60000;
private _jBleed = (_patient getVariable ["ACME_junctionalBleedLPS", 0]) * 60000;
private _intBleed = if (!isNil "ACM_circulation_fnc_getInternalBleedingRate") then {(([_patient] call ACM_circulation_fnc_getInternalBleedingRate) max 0) * 60000} else {0};
private _hemoBleed = if (!isNil "ACM_circulation_fnc_getHemothoraxBleedingRate") then {(([_patient] call ACM_circulation_fnc_getHemothoraxBleedingRate) max 0) * 60000} else {0};
private _capBleed = if (!isNil "ACM_circulation_fnc_getCapillaryDamageBleedingRate") then {(([_patient] call ACM_circulation_fnc_getCapillaryDamageBleedingRate) max 0) * 60000} else {0};
private _totalBleed = _bleedMlMin + _jBleed + _intBleed + _hemoBleed + _capBleed;
private _vaso = _patient getVariable ["ACM_circulation_Vasoconstriction_State", 0];
private _plate = _patient getVariable ["ACM_circulation_Platelet_Count", 3];
private _calcium = _patient getVariable ["ACM_circulation_Calcium_Count", 0];
private _bvCol = if (_circ < 3.6) then {_cBad} else {if (_circ < 4.4) then {_cWarn} else {_cGood}};
private _bleedCol = if (_bleedMlMin >= 500) then {_cBad} else {if (_bleedMlMin >= 100) then {_cWarn} else {_cGood}};
_left pushBack (["PERFUSION / BLEEDING"] call _sect);
_left pushBack (["CircVol", format ["%1L", _circ toFixed 2], _bvCol, "EffVol", format ["%1L", _eff toFixed 2], if (_eff < 3.6) then {_cBad} else {if (_eff < 4.4) then {_cWarn} else {_cGood}}] call _pair);
_left pushBack (["Blood", format ["%1L", _blood toFixed 2], _cLabel, "Plasma", format ["%1L", _plasma toFixed 2], _cLabel] call _pair);
_left pushBack (["Cryst", format ["%1L", _cryst toFixed 2], _cLabel, "ExcsVol", format ["%1L", _over toFixed 2], if (_over > 0.5) then {_cWarn} else {_cMute}] call _pair);
_left pushBack (["Ext", format ["%1 mL/min", round _bleedMlMin], _bleedCol, "Junc", format ["%1 mL/min", round _jBleed], if (_jBleed > 0) then {_cBad} else {_cGood}] call _pair);
_left pushBack (["Internal", format ["%1", round _intBleed], if (_intBleed > 0) then {_cBad} else {_cGood}, "HTX", format ["%1", round _hemoBleed], if (_hemoBleed > 0) then {_cBad} else {_cGood}] call _pair);
_left pushBack (["Cap", format ["%1", round _capBleed], if (_capBleed > 0) then {_cWarn} else {_cGood}, "SrcTot", format ["%1 mL/min", round _totalBleed], if (_totalBleed >= 500) then {_cBad} else {if (_totalBleed > 0) then {_cWarn} else {_cGood}}] call _pair);
_left pushBack (["VC", _vaso toFixed 2, _cLabel, "Platelets", _plate toFixed 2, if (_plate < 1.5) then {_cWarn} else {_cGood}] call _pair);
private _pressor = _circState getOrDefault ["pressorSupport", 0];
private _svr = _patient getVariable ["ace_medical_peripheralResistance", 100];
_left pushBack (["Pressor", _pressor toFixed 2, if (_pressor > 0) then {_cGood} else {_cMute}, "SVR", round _svr, _cLabel] call _pair);
_left pushBack (["Calcium", _calcium toFixed 2, _cLabel, "Coag", (_circState getOrDefault ["coagMult", 1]) toFixed 2, _cLabel] call _pair);

// Airway and chest.
private _airReflex = _patient getVariable ["ACM_airway_AirwayReflex_State", true];
private _collapse = _patient getVariable ["ACM_airway_AirwayCollapse_State", 0];
private _vomit = _patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0];
private _bloodObs = _patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0];
private _opa = _patient getVariable ["ACM_airway_AirwayItem_Oral", ""];
private _npa = _patient getVariable ["ACM_airway_AirwayItem_Nasal", ""];
private _ett = _patient getVariable ["ACME_ETT_Inserted", false];
private _cuff = _patient getVariable ["ACME_ETT_CuffInflated", false];
private _cric = _patient getVariable ["ACM_airway_SurgicalAirway_State", false];
private _ptx = _patient getVariable ["ACM_breathing_Pneumothorax_State", 0];
private _tptx = _patient getVariable ["ACM_breathing_TensionPneumothorax_State", false];
private _hemo = _patient getVariable ["ACM_breathing_Hemothorax_State", 0];
private _hemoFluid = _patient getVariable ["ACM_breathing_Hemothorax_Fluid", 0];
private _seal = _patient getVariable ["ACM_breathing_ChestSeal_State", false];
private _tubeL = _patient getVariable ["ACME_thora_tube_left", false];
private _tubeR = _patient getVariable ["ACME_thora_tube_right", false];
private _tractL = _patient getVariable ["ACME_thora_open_left", ""];
private _tractR = _patient getVariable ["ACME_thora_open_right", ""];
private _sealedL = _patient getVariable ["ACME_thora_sealed_left", false];
private _sealedR = _patient getVariable ["ACME_thora_sealed_right", false];
private _closedL = (_patient getVariable ["ACME_thora_closed_left", false]) || {_sealedL && {_tractL == "sealed"} && {!_tubeL}};
private _closedR = (_patient getVariable ["ACME_thora_closed_right", false]) || {_sealedR && {_tractR == "sealed"} && {!_tubeR}};
private _openL = _tractL == "finger" && {!_closedL};
private _openR = _tractR == "finger" && {!_closedR};
private _thoraL = if (_tubeL) then {"[TUBE]"} else {if (_closedL) then {"closed"} else {if (_openL) then {"open"} else {"none"}}};
private _thoraR = if (_tubeR) then {"[TUBE]"} else {if (_closedR) then {"closed"} else {if (_openR) then {"open"} else {"none"}}};
private _bvm = _patient getVariable ["ACM_breathing_isUsingBVM", false];
private _vent = _patient getVariable ["ACME_vent_driving", false];
// B125: classify the airway from ACM's actual patency result, not from a raw collapse latch. A mild collapse
// (C1) can still pass air, and a conscious casualty is explicitly patent in getAirwayState even if a stale collapse
// value has not been reconciled yet. Vomit/blood remain true obstructions and severe loss of patency stays red.
private _airwayPatency = if (!isNil "ACM_airway_fnc_getAirwayState") then {
    [_patient] call ACM_airway_fnc_getAirwayState
} else {
    if (_vomit > 0 || {_bloodObs > 0}) then {0} else {1 - ((_collapse min 3) / 3)}
};
private _fluidObstruction = (_vomit > 0) || {_bloodObs > 0};
private _airwayTxt = if (_ett) then {
    "ETT" + (if (_cuff) then {"+cuff"} else {""})
} else {if (_cric) then {
    "CRIC"
} else {if (_fluidObstruction || {_airwayPatency <= 0.20}) then {
    "OBSTRUCTED"
} else {if (_airwayPatency < 0.90) then {"NARROWED"} else {"OPEN"}}}};
private _airwayCol = if (_fluidObstruction || {_airwayPatency <= 0.20}) then {_cBad} else {if (_airwayPatency < 0.90) then {_cWarn} else {_cGood}};
private _obsCol = if (_vomit > 0 || {_bloodObs > 0} || {_collapse >= 3}) then {_cBad} else {if (_collapse > 0) then {_cWarn} else {_cGood}};
_left pushBack (["AIRWAY / CHEST"] call _sect);
_left pushBack (["Airway", _airwayTxt, _airwayCol, "Reflex", [_airReflex] call _yn, if (_airReflex) then {_cGood} else {_cWarn}] call _pair);
private _adj = [];
if (_opa != "") then {_adj pushBack "OPA";}; if (_npa != "") then {_adj pushBack "NPA";};
_left pushBack (["Adjunct", if (_adj isEqualTo []) then {"none"} else {_adj joinString "+"}, if (_adj isEqualTo []) then {_cMute} else {_cGood}, "Obs", format ["C%1 V%2 B%3", _collapse, _vomit, _bloodObs], _obsCol] call _pair);
_left pushBack (["PTX", _ptx toFixed 3, if (_ptx > 0) then {_cWarn} else {_cGood}, "TPTX", [_tptx] call _yn, [_tptx, true] call _ynCol] call _pair);
_left pushBack (["HTX", format ["%1 / %2L", _hemo, _hemoFluid toFixed 2], if (_hemo > 0 || {_hemoFluid > 0.3}) then {_cWarn} else {_cGood}, "Seal", [_seal] call _yn, if (_seal) then {_cGood} else {_cMute}] call _pair);
_left pushBack (["FThor Left", _thoraL, if (_tubeL) then {_cTube} else {if (_closedL || {_openL}) then {_cGood} else {_cMute}}, "FThor Right", _thoraR, if (_tubeR) then {_cTube} else {if (_closedR || {_openR}) then {_cGood} else {_cMute}}] call _pair);
_left pushBack (["BVM", [_bvm] call _yn, if (_bvm) then {_cGood} else {_cMute}, "Ventilator", [_vent] call _yn, if (_vent) then {_cGood} else {_cMute}] call _pair);

// Metabolic/coagulation summary.
private _acid = _circState getOrDefault ["totalAcidosis", _circState getOrDefault ["acidosis", 0]];
private _paCO2 = _circState getOrDefault ["paCO2", 40];
private _coag = _circState getOrDefault ["coagMult", 1];
private _shock = _circState getOrDefault ["shockSeverity", 0];
_left pushBack (["METABOLIC"] call _sect);
_left pushBack (["Acid", _acid toFixed 2, if (_acid >= 0.65) then {_cBad} else {if (_acid >= 0.30) then {_cWarn} else {_cGood}}, "PaCO2", _paCO2 toFixed 0, if (_paCO2 > 70) then {_cBad} else {if (_paCO2 > 50) then {_cWarn} else {_cGood}}] call _pair);
_left pushBack (["Coag", _coag toFixed 2, if (_coag > 1.5) then {_cBad} else {if (_coag > 1.1) then {_cWarn} else {_cGood}}, "Shock", _shock toFixed 2, if (_shock > 0.6) then {_cBad} else {if (_shock > 0.2) then {_cWarn} else {_cGood}}] call _pair);
private _cbrnExp = _patient getVariable ["ACM_cbrn_Exposed_State", false];
private _cbrnCont = _patient getVariable ["ACM_cbrn_Contaminated_State", false];
private _cbrnAir = _patient getVariable ["ACM_cbrn_AirwayInflammation", 0];
private _cbrnLung = _patient getVariable ["ACM_cbrn_LungTissueDamage", 0];
if (_cbrnExp || {_cbrnCont} || {_cbrnAir > 0} || {_cbrnLung > 0}) then {
    _left pushBack (["CBRN", format ["E:%1 C:%2", if (_cbrnExp) then {"Y"} else {"-"}, if (_cbrnCont) then {"Y"} else {"-"}], _cWarn, "Air/Lung", format ["%1/%2", _cbrnAir toFixed 1, _cbrnLung toFixed 1], _cWarn] call _pair);
};


// Neuro/TBI explains consciousness and ICP-related arrest on the same overlay.
private _tbi = _patient getVariable ["ACME_tbi_State", createHashMap];
private _icp = _tbi getOrDefault ["icp", 0];
private _cpp = _map - _icp;
private _tbiSev = _tbi getOrDefault ["severity", 0];
private _tbiStruct = _tbi getOrDefault ["structuralSeverity", _tbiSev];
private _tbiAutoreg = _tbi getOrDefault ["autoregIntegrity", 1];
private _tbiAutoInt = _tbi getOrDefault ["autonomicIntegrity", 1];
private _tbiTone = _tbi getOrDefault ["autonomicTone", 0];
private _hern = _tbi getOrDefault ["herniating", false];
private _cush = _tbi getOrDefault ["cushing", false];
private _obt = _patient getVariable ["ACME_obtunded", false];
_left pushBack (["NEURO / TBI"] call _sect);
_left pushBack (["Acute", _tbiSev toFixed 2, if (_tbiSev >= 0.65) then {_cBad} else {if (_tbiSev >= 0.30) then {_cWarn} else {_cGood}}, "Brain damage", _tbiStruct toFixed 2, if (_tbiStruct >= 0.80) then {_cBad} else {if (_tbiStruct >= 0.60) then {_cWarn} else {_cLabel}}] call _pair);
_left pushBack (["ICP", round _icp, if (_icp >= 30) then {_cBad} else {if (_icp > 20) then {_cWarn} else {_cGood}}, "CPP", round _cpp, if (_cpp < 50) then {_cBad} else {if (_cpp < 70) then {_cWarn} else {_cGood}}] call _pair);
_left pushBack (["Autoreg", _tbiAutoreg toFixed 2, if (_tbiAutoreg < 0.40) then {_cBad} else {if (_tbiAutoreg < 0.70) then {_cWarn} else {_cGood}}, "Auto", format ["%1 / %2", _tbiAutoInt toFixed 2, _tbiTone toFixed 2], if (_tbiTone < -0.35) then {_cBad} else {if (abs _tbiTone > 0.55) then {_cWarn} else {_cLabel}}] call _pair);
_left pushBack (["Herniation", [_hern] call _yn, [_hern, true] call _ynCol, "Cushing", [_cush] call _yn, [_cush, true] call _ynCol] call _pair);
_left pushBack (["Obtunded", [_obt] call _yn, if (_obt) then {_cWarn} else {_cMute}, "PerfOK", [(_tbi getOrDefault ["perfusionOK", true])] call _yn, if (_tbi getOrDefault ["perfusionOK", true]) then {_cGood} else {_cWarn}] call _pair);

// Resuscitation / rhythm.
private _nativeRh = _patient getVariable ["ACM_circulation_Cardiac_RhythmState", 0];
private _activeRh = _patient getVariable ["ACME_rhythm_active", 0];
private _aedRh = _patient getVariable ["ACM_circulation_AED_EKGRhythm", _nativeRh];
private _visualRh = if (_activeRh >= 100 && {!(_aedRh in [-1,1,2])}) then {_activeRh} else {_aedRh};
private _cpr = _patient getVariable ["ACM_circulation_isPerformingCPR", false];
private _revArr = _patient getVariable ["ACM_circulation_ReversibleCardiacArrest_State", false];
private _shockRes = _patient getVariable ["ACM_circulation_CardiacArrest_ShockResistant", false];
_right pushBack (["RHYTHM / RESUS"] call _sect);
_right pushBack (["Active", _activeRh, if (_activeRh >= 100 || {_nativeRh in [1,2,3,4,5]}) then {_cBad} else {_cGood}, "Native", _nativeRh, _cLabel] call _pair);
_right pushBack (["AED", _visualRh, if (_visualRh > 0) then {_cWarn} else {_cMute}, "CPR", [_cpr] call _yn, if (_cpr) then {_cGood} else {_cMute}] call _pair);
_right pushBack (["Arrest", [_arrest] call _yn, [_arrest, true] call _ynCol, "Rev", [_revArr] call _yn, if (_revArr) then {_cWarn} else {_cMute}] call _pair);
_right pushBack (["ShockR", [_shockRes] call _yn, if (_shockRes) then {_cWarn} else {_cMute}, "ROSCblk", _circState getOrDefault ["roscBlock", "-"], _cMute] call _pair);

// Hemostasis / devices.
private _jParts = ["leftarm", "rightarm", "leftleg", "rightleg"];
private _jTxt = [];
{private _s = _patient getVariable [format ["ACME_Junc_%1", _x], ""]; if (_s != "") then {_jTxt pushBack format ["%1:%2", _x select [0,2], _s];};} forEach _jParts;
// B129: ACM_disability_Tourniquet_Time is presentation data and may contain strings such as "13:37".
// Count the native ACE numeric tourniquet state instead, with a type guard for old/restored saves.
private _tq = _patient getVariable ["ace_medical_tourniquets", [0,0,0,0,0,0]];
private _tqCount = {_x isEqualType 0 && {_x > 0}} count _tq;
private _aajt = [];
if (_patient getVariable ["ACME_AAJT_zone3", false]) then {_aajt pushBack "Z3";};
if (_patient getVariable ["ACME_AAJT_inguinal", false]) then {_aajt pushBack format ["Ing-%1", _patient getVariable ["ACME_AAJT_inguinalSide", "?"]];};
if (_patient getVariable ["ACME_AAJT_axillaleft", false]) then {_aajt pushBack "AxL";};
if (_patient getVariable ["ACME_AAJT_axillaright", false]) then {_aajt pushBack "AxR";};
private _xstat = _patient getVariable ["ACME_XStat_needsSurgery", false];
private _dp = _patient getVariable ["ACME_DP_Active", false];
_right pushBack (["HEMOSTASIS / DEVICES"] call _sect);
_right pushBack (["TQ", _tqCount, if (_tqCount > 0) then {_cWarn} else {_cMute}, "DP", [_dp] call _yn, if (_dp) then {_cGood} else {_cMute}] call _pair);
_right pushBack (["Junc", if (_jTxt isEqualTo []) then {"none"} else {_jTxt joinString ","}, if (_jTxt isEqualTo []) then {_cMute} else {_cWarn}] call _one);
_right pushBack (["AAJT", if (_aajt isEqualTo []) then {"none"} else {_aajt joinString "+"}, if (_aajt isEqualTo []) then {_cMute} else {_cWarn}, "XStat", [_xstat] call _yn, if (_xstat) then {_cWarn} else {_cMute}] call _pair);
private _hpmk = _patient getVariable ["ACME_hpmk_state", ""];
private _fract = _patient getVariable ["ACM_disability_Fracture_State", [0,0,0,0,0,0]];
private _splints = _patient getVariable ["ace_medical_treatment_splints", [0,0,0,0,0,0]];
private _fractN = {_x > 0} count _fract;
private _splintN = {_x > 0} count _splints;
_right pushBack (["HPMK", if (_hpmk == "") then {"none"} else {_hpmk}, if (_hpmk in ["wrapped","exposed"]) then {_cGood} else {_cMute}, "Fr/Spl", format ["%1/%2", _fractN, _splintN], if (_fractN > _splintN) then {_cWarn} else {if (_fractN > 0) then {_cGood} else {_cMute}}] call _pair);

// B213: discover the installed medication catalog once, so optional/added drugs have permanent zero-valued slots too.
// Route variants share one drug row; the displayed total is onset/washout-aware reference-dose equivalents,
// not inventory, injected milligrams, sedation equivalence or an undegraded administration count.
private _medicationFamily = {
    params ["_class"];
    private _name = _class;
    {
        private _at = (count _name) - (count _x);
        if (_at > 0 && {(_name select [_at]) == _x}) exitWith {_name = _name select [0, _at];};
    } forEach ["_IV_L", "_IV", "_IM", "_BUC", "_PO", "_IN", "_L"];
    if (_name == "EpinephrineCardiac") then {_name = "Epinephrine";};
    _name
};
private _medicationGroups = missionNamespace getVariable ["ACME_debugMedicationGroups", []];
if (_medicationGroups isEqualTo []) then {
    private _names = ("true" configClasses (configFile >> "ACM_Medication" >> "Medications")) apply {configName _x};
    _names = _names select {(_x select [0,4]) != "ACM_"};
    _names sort true;
    {
        private _class = _x;
        private _family = [_class] call _medicationFamily;
        private _index = _medicationGroups findIf {(_x select 0) == _family};
        if (_index < 0) then {
            _medicationGroups pushBack [_family, [_class]];
        } else {
            ((_medicationGroups select _index) select 1) pushBackUnique _class;
        };
    } forEach _names;
    missionNamespace setVariable ["ACME_debugMedicationGroups", _medicationGroups];
};
private _medicationRows = [];
private _medicationLabel = {
    params ["_name"];
    // Preserve acronyms (TXA/HTS) while separating CamelCase words, including optional future medications.
    private _chars = toArray _name;
    private _label = "";
    {
        private _previous = if (_forEachIndex > 0) then {_chars select (_forEachIndex - 1)} else {0};
        private _next = _chars param [_forEachIndex + 1, 0];
        private _upper = _x >= 65 && {_x <= 90};
        private _previousLower = (_previous >= 97 && {_previous <= 122}) || {_previous >= 48 && {_previous <= 57}};
        private _acronymEnd = _previous >= 65 && {_previous <= 90} && {_next >= 97} && {_next <= 122};
        if (_forEachIndex > 0 && {_upper} && {_previousLower || {_acronymEnd}}) then {_label = _label + " ";};
        _label = _label + (if (_x == 95) then {" "} else {toString [_x]});
    } forEach _chars;
    _label
};
{
    _x params ["_family", "_classes"];
    private _effect = 0;
    {
        private _value = [_patient, _x, false] call ACME_fnc_medicationCountCompat;
        if (_value isEqualType 0 && {finite _value}) then {_effect = _effect + (_value max 0);};
    } forEach _classes;
    _medicationRows pushBack [[_family] call _medicationLabel, _effect toFixed 2, if (_effect > 0) then {_cGood} else {_cMute}];
} forEach _medicationGroups;
_right pushBack (["MEDICATIONS"] call _sect);
_right pushBack format ["  <t color='%1'>Effective reference-dose equivalents</t>", _cMute];
{
    // An odd catalog leaves a real single-field final row. Passing it to the
    // six-argument pair builder read undefined _b/_bv/_bc and printed a ghost colon.
    _right pushBack (if (count _x == 3) then {_x call _one} else {_x call _pair});
} forEach ([_medicationRows] call ACME_fnc_debugMedicationColumns);

// Nondrug sedation/awareness state is deliberately separated beneath the medication list.
([_patient] call ACME_fnc_sedationComponents) params ["_ket", "_prop", "_mid", "_fent", "_adjunct", "_sed"];
private _sedated = _patient getVariable ["ACME_ket_sedated", false];
private _par = _patient getVariable ["ACME_roc_paralyzed", false];
private _awakePar = _patient getVariable ["ACME_roc_awakeParalysis", false];
_right pushBack (["SEDATION / AWARENESS"] call _sect);
_right pushBack (["Sedation load", _sed toFixed 2, if (_sed >= 1 || {_sedated}) then {_cGood} else {if (_sed > 0) then {_cWarn} else {_cMute}}, "Sedated", [_sedated] call _yn, if (_sedated) then {_cGood} else {_cMute}] call _pair);
_right pushBack (["Paralyzed", [_par] call _yn, if (_par) then {_cWarn} else {_cMute}, "Aware", [_awakePar] call _yn, if (_awakePar) then {_cCrit} else {_cGood}] call _pair);

// Cerebral seizure state is independent of motor expression under neuromuscular blockade.
private _szState = _patient getVariable ["ACME_lido_seizureState", ""];
private _szDrive = _patient getVariable ["ACME_seizure_drive", 0];
private _szSupp = _patient getVariable ["ACME_seizure_suppression", 0];
private _szControlled = _patient getVariable ["ACME_seizure_suppressed", false];
private _szMasked = _par && {_szState == "active"};
private _szMotor = if (_szState != "active") then {"none"} else {if (_szMasked) then {"MASKED"} else {"VISIBLE"}};
_right pushBack (["SEIZURE CONTROL"] call _sect);
_right pushBack (["Seizing", if (_szState == "") then {"none"} else {_szState}, if (_szState == "active") then {_cCrit} else {if (_szState == "postictal") then {_cWarn} else {_cMute}}, "Motor", _szMotor, if (_szMasked) then {_cWarn} else {if (_szState == "active") then {_cCrit} else {_cMute}}] call _pair);
_right pushBack (["Drive", _szDrive toFixed 2, _cLabel, "Suppress", _szSupp toFixed 2, if (_szControlled) then {_cGood} else {if (_szSupp > 0) then {_cWarn} else {_cMute}}] call _pair);

// B215: one bullet per connected physical bag, with contents nested beneath it. This is read-only:
// never allocate bag identities from a debug refresh or bind an unidentified bag to another bag's medication.
private _medEntries = _patient getVariable ["ACME_infusion_BagMedications", []];
if !(_medEntries isEqualType []) then {_medEntries = [];};
private _ivMap = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
private _fluidRows = [];
private _bpShort = {
    params ["_bp"];
    switch (toLowerANSI _bp) do {
        case "leftarm": {"LUE"}; case "rightarm": {"RUE"};
        case "leftleg": {"LLE"}; case "rightleg": {"RLE"};
        case "body": {"Torso"}; case "head": {"Head"}; default {_bp};
    }
};
private _fluidShort = {
    params ["_type"];
    switch (toLowerANSI _type) do {
        case "blood": {"Blood"}; case "freshblood": {"Fresh Blood"}; case "plasma": {"Plasma"};
        case "saline": {"NS"}; case "acme_saliney": {"NS-Y"}; case "plasmalyte": {"PL"};
        case "hts": {"HTS"}; case "hts3": {"HTS"}; case "hypertonicsaline": {"HTS"};
        case "mannitol": {"Mannitol"}; case "fbtk": {"FBTK"};
        case "acme_empty": {""}; case "acme_emptysaline": {""}; default {_type};
    }
};
private _medicationShort = {
    params ["_name"];
    _name = [_name] call _medicationFamily;
    switch (_name) do {
        case "Epinephrine": {"Epi"}; case "Norepinephrine": {"Norepi"};
        case "CalciumChloride": {"CaCl2"}; case "CalciumGluconate": {"Ca Gluc"};
        case "Magnesium": {"MgSO4"}; case "HTS3": {"HTS 3%"};
        default {[_name] call _medicationLabel};
    }
};
private _matchingBagMeds = {
    params ["_bag", "_bp", "_index", "_entries"];
    private _uid = _bag param [8, "", [""]];
    _entries select {
        private _entry = _x;
        private _matches = false;
        if (_entry isEqualType [] && {count _entry >= 15}) then {
            private _entryUid = _entry param [23, "", [""]];
            if (_entryUid != "") then {
                _matches = _uid != "" && {_uid == _entryUid};
            } else {
                // Legacy data is slot-exact AND metadata-exact, never nearest-volume/identity-only fallback.
                _matches = (toLowerANSI (_entry param [1, ""])) == toLowerANSI _bp
                    && {(_entry param [2, -1]) == _index}
                    && {(_entry param [3, ""]) == (_bag param [0, ""])}
                    && {(_entry param [4, -1]) == (_bag param [3, -1])}
                    && {(_entry param [5, true]) isEqualTo (_bag param [4, true])}
                    && {(_entry param [6, -1]) == (_bag param [5, -1])}
                    && {(_entry param [7, 0]) == (_bag param [6, 0])}
                    && {(_entry param [8, -1]) == (_bag param [7, -1])};
            };
            private _dose = _entry param [14, 0, [0]];
            _matches = _matches && {_dose > 0.000001};
        };
        _matches
    }
};
private _fluidBagRows = {
    params ["_bag", "_bp", "_index", "_entries"];
    if !(_bag isEqualType [] && {count _bag >= 7}) exitWith {[]};
    private _type = _bag param [0, "", [""]];
    private _short = [_type] call _fluidShort;
    private _remaining = _bag param [1, 0, [0]];
    // FBTK is a receiving bag and remains connected while empty. Empty plumbing markers are never bags.
    if (_short == "" || {_remaining <= 0.01 && {toLowerANSI _type != "fbtk"}}) exitWith {[]};
    // Native field 6 is the initial mixture volume (including added medication solution), not remaining mL.
    private _volume = _bag param [6, 0, [0]];
    private _size = if (_volume > 0) then {format ["%1 mL", _volume toFixed 0]} else {"Unknown size"};
    private _rows = [["bullet", format ["%1 %2", _size, _short], _cGood, 0]];
    private _site = _bag param [3, -1, [0]];
    private _isIV = _bag param [4, true, [true]];
    private _where = format ["%1 %2%3", [_bp] call _bpShort, if (_isIV) then {"IV"} else {"IO"}, if (_site >= 0) then {str _site} else {""}];
    private _volumeLabel = if (toLowerANSI _type == "fbtk") then {"collected"} else {"remaining"};
    _rows pushBack ["bullet", format ["%1 | %2 mL %3", _where, (_remaining max 0) toFixed 0, _volumeLabel], _cLabel, 1];
    private _bloodType = _bag param [5, -1, [0]];
    if (toLowerANSI _type in ["blood", "freshblood", "fbtk"] && {_bloodType in [0,1,2,3,4,5,6,7]}) then {
        _rows pushBack ["bullet", "Blood type: " + (["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"] select _bloodType), _cLabel, 1];
    };
    private _meds = [_bag, _bp, _index, _entries] call _matchingBagMeds;
    if !(_meds isEqualTo []) then {
        private _control = _meds select 0;
        private _drops = (_control param [21, 0, [0]]) max 0;
        private _dropSet = (_control param [20, 20, [0]]) max 1;
        _rows pushBack ["bullet", format ["Clamp: %1 gtt/min (%2 gtt/mL)", _drops toFixed 0, _dropSet toFixed 0], if (_drops > 0) then {_cGood} else {_cWarn}, 1];
        {
            private _name = _x param [11, "?", [""]];
            private _dose = _x param [14, 0, [0]];
            _rows pushBack ["bullet", format ["%1: %2 remaining", [_name] call _medicationShort, [_name, _dose] call ACME_fnc_formatDose], _cLabel, 1];
        } forEach _meds;
    };
    _rows
};
if (_ivMap isEqualType createHashMap) then {
    private _parts = keys _ivMap;
    _parts sort true;
    {
        private _bp = _x;
        private _bags = _ivMap getOrDefault [_bp, []];
        if (_bags isEqualType []) then {
            {_fluidRows append ([_x, _bp, _forEachIndex, _medEntries] call _fluidBagRows);} forEach _bags;
        };
    } forEach _parts;
};
_right pushBack (["FLUIDS / INFUSIONS"] call _sect);
if (_fluidRows isEqualTo []) then {
    _right pushBack ["bullet", "No connected bags", _cMute, 0];
} else {
    _right append _fluidRows;
};

call _renderAll;
