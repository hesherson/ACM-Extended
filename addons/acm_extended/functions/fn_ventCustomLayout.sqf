// device-accurate layouts for WEIGHT, ALERTS 1/2 and ALERTS 2/2, built from the panel's proven primitives.
// static labels are plain RscText, every editable number is an ACME_VentBtn registered in ACME_vent_valFields at
// its knob index, and the one standard painter, fn_ventpanellistrefresh, highlights the selected number and the
// nav strip exactly as it does on every other screen. the layout is device-accurate and the machinery is not
// special in any way. that combination is the whole point: an earlier build drew these screens with bespoke
// structured text, bespoke rects and a bespoke painter, and every one of those bespoke pieces broke.
// the geometry rules are consistent with the established ui.
// font: the list-row size, _sh times 0.13, for labels and values, with units at 0.7x and baseline-dropped.
// value boxes: sized for the longest string the dial can put in them, plus universal padding, so a value can
// never outgrow its own highlight while being edited.
// right alignment: every value cluster ends on the common right edge the list rows use, 0.86, with universal
// gaps between pieces. labels anchor left at 0.06, with a single indent step at 0.14 where the device indents.
// glyph math: the engine draws glyphs square in pixels at about 0.5 font-heights per character, converted to a
// screen-width fraction through pixelw and pixelh, so the rects are exact on any resolution and aspect.
// call it as [_screen] call ACME_fnc_ventCustomLayout.
params ["_screen"];
disableSerialization;
private _dlg = uiNamespace getVariable ["ACME_vent_dlg", displayNull];
if (isNull _dlg) exitWith {};
(uiNamespace getVariable ["ACME_vent_scrRect", [0,0,1,1]]) params ["_sx","_sy","_sw","_sh"];

// PARAMS packs six label and value rows, and a long label such as "PAT. WEIGHT" plus a long value such as "SIMV
// VC PS" cannot both fit on one line at the big list-row size. so PARAMS drops to a denser row font, and the
// three-to-five row screens, ALERTS and WEIGHT, keep the full size. the box height follows the font, so the
// highlight stays proportional.
// PARAMS used to shrink to 0.09 to cram six rows onto one page. it uses the same font as every other screen now
// and splits across two pages instead, which is how the rest of the device already behaves.
private _fVal  = 0.13;  // the value and label font as an sh-fraction. every screen shares it, and PARAMS restates it explicitly.
private _fUnit = 0.091;  // the unit font, at 0.7x, as on the device.
private _boxH  = 0.13;  // the value box height tracks the font.
private _padX  = 0.010;  // universal padding inside a value box, as an sw fraction.
private _gap   = 0.015;  // a universal gap between pieces on a line, as an sw fraction.
private _rightEdge = 0.83;  // the right edge of the value column. it is pulled in from the screen edge so a trailing unit
                             // it has margin to the rounded corner and cannot clip. it was 0.86, flush, which clipped.
private _leftEdge  = 0.06;  // the left edge of the list rows.
private _indent    = 0.14;  // a single indent step for LIMIT and ALERT.

private _white = [0.92,0.92,0.92,1];
private _unitC = [0.84,0.87,0.91,1];

// the glyph advance as an sw-fraction for a font given as an sh-fraction. it is exact on any aspect ratio.
// the factor is the average glyph advance as a fraction of the font height. 0.5 was too small for purista,
// because a condensed bold face still advances about 0.56 em on caps, which let multi-character units like
// "cmH2O" and "BPM" render wider than their fitted box and clip off the right edge. 0.56 sizes them to their
// real width.
private _chW = { params ["_f"]; (0.56 * _f * _sh * (pixelW / pixelH)) / _sw };

private _statics = uiNamespace getVariable ["ACME_vent_graphBars", []];
private _fields  = [];

// a static text piece with its rect fitted to the string, so the placement is exact and alignment is moot.
private _mkStatic = {
    params ["_x","_yTop","_txt","_f","_col"];
    // a one-character unit gets two characters of box. chw assumes an average 0.56 em advance, which is fine across
    // a word like "cmH2O" and badly under-measures a single wide glyph, because a percent sign is nearly twice
    // that. its box therefore came out narrower than the glyph and clipped it down the middle, wherever the cluster
    // placed it, because a control clips its own text. two characters clears it with room spare.
    private _w = (((count _txt) max 2) * ([_f] call _chW)) + 0.012;
    private _c = _dlg ctrlCreate ["RscText", -1];
    _c ctrlSetPosition [_sx + _sw*_x, _sy + _sh*_yTop, _sw*_w, _sh*(_f * 1.15)];
    _c ctrlSetText _txt;
    _c ctrlSetFontHeight (_sh * _f);
    _c ctrlSetTextColor _col;
    _c ctrlSetBackgroundColor ([[0,0,0,0]] call ACME_fnc_ventColor);
    _c ctrlCommit 0; _c ctrlShow true;
    _statics pushBack _c;
    _w
};
// a label on a value line. it uses the same font as the values, vertically centerd against the value boxes.
private _mkLabel = {
    params ["_x","_lineY","_txt"];
    [_x, _lineY + (_boxH - _fVal*1.15)*0.5, _txt, _fVal, _white] call _mkStatic;
};
// an editable number. it is sized for its maximum string and registered at its knob index. ACME_VentValG is a
// centerd RscText, because buttons do not reliably take ctrlSetBackgroundColor and the whole job of this
// control is to take the highlight, so the number floats in the middle of its padded box and the highlight hugs
// it evenly.
private _mkVal = {
    params ["_x","_yTop","_maxCh","_txt","_idx"];
    private _w = (_maxCh * ([_fVal] call _chW)) + 2*_padX;
    private _c = _dlg ctrlCreate ["ACME_VentValG", -1];
    _c ctrlSetPosition [_sx + _sw*_x, _sy + _sh*_yTop, _sw*_w, _sh*_boxH];
    _c ctrlSetFontHeight (_sh * _fVal);
    _c ctrlSetText _txt;
    _c ctrlSetBackgroundColor ([[0,0,0,0]] call ACME_fnc_ventColor);
    _c ctrlSetTextColor _white;
    _c ctrlCommit 0; _c ctrlShow true;
    while {count _fields <= _idx} do { _fields pushBack controlNull };
    _fields set [_idx, _c];
    _w
};

// a right-aligned editable value. its right edge lands on _rightEdge, so a whole column of values lines up on
// the right however wide each is. it uses the same registration as _mkVal. _maxCh sizes the box for the widest
// string the field can hold, such as a mode name, so the highlight never clips a long value.
private _mkRightVal = {
    params ["_yTop","_maxCh","_txt","_idx"];
    private _w = (_maxCh * ([_fVal] call _chW)) + 2*_padX;
    private _x = _rightEdge - _w;
    [_x, _yTop, _maxCh, _txt, _idx] call _mkVal;
};


// the pieces are ["val", maxchars, text, idx], ["txt", text, font, color] and ["gap", width].
private _cluster = {
    params ["_lineY", "_pieces"];
    // self-fitting. the cluster is right-aligned on _rightEdge, so a long line simply ran off the left of the screen
    // and the first value box disappeared. that is what happened to the 50 on the mv line. character width depends
    // on the screen aspect through _chW, so no hand-tuned set of widths is safe across resolutions. instead the row
    // measures itself, and if it will not fit between _leftEdge and _rightEdge it shrinks its own fonts until it
    // does.
    private _fV0 = _fVal; private _fU0 = _fUnit; private _bH0 = _boxH;
    private _measure = {
        private _w = 0;
        {
            _w = _w + (switch (_x select 0) do {
                case "val": { ((_x select 1) * ([_fVal] call _chW)) + 2*_padX };
                case "txt": { (((count (_x select 1)) max 2) * ([(_x select 2)] call _chW)) + 0.012 };
                default    { _x select 1 };
            });
        } forEach _pieces;
        _w
    };
    private _avail = _rightEdge - _leftEdge;
    private _total = call _measure;
    if (_total > _avail && {_total > 0}) then {
        // shrink both fonts and the box height by the same factor, floored so it can never become unreadable.
        private _k = ((_avail / _total) max 0.72);
        _fVal  = _fV0 * _k;
        _fUnit = _fU0 * _k;
        _boxH  = _bH0 * _k;
        // unit-font pieces carry their own size in the piece, so rescale those too.
        _pieces = _pieces apply {
            if ((_x select 0) isEqualTo "txt") then { [_x select 0, _x select 1, (_x select 2) * _k, _x select 3] } else { _x }
        };
        _total = call _measure;
    };
    private _widths = _pieces apply {
        switch (_x select 0) do {
            case "val": { ((_x select 1) * ([_fVal] call _chW)) + 2*_padX };
            case "txt": { (((count (_x select 1)) max 2) * ([(_x select 2)] call _chW)) + 0.012 };  // see _mkStatic.
            default    { _x select 1 };
        }
    };
    // never start left of the label column, whatever the measurement says.
    private _cx = (_rightEdge - _total) max _leftEdge;
    {
        private _w = _widths select _forEachIndex;
        switch (_x select 0) do {
            case "val": {
                [_cx, _lineY, _x select 1, _x select 2, _x select 3] call _mkVal;
            };
            case "txt": {
                private _f2 = _x select 2;
                // same-size statics center against the value boxes, and smaller units drop toward the baseline.
                private _fac = if (_f2 >= _fVal * 0.99) then { 0.5 } else { 0.78 };
                private _yAdj = _lineY + (_boxH - _f2*1.15) * _fac;
                [_cx, _yAdj, _x select 1, _f2, _x select 3] call _mkStatic;
            };
        };
        _cx = _cx + _w;
    } forEach _pieces;
    // restore, so a row that had to shrink does not drag every row after it down with it.
    _fVal = _fV0; _fUnit = _fU0; _boxH = _bH0;
};

switch (_screen) do {

    // PARAMS, page 1 of 2.
    // there are six rows, with the label on the left and the value right-aligned, so the whole value column lines up
    // and nothing collides.
    // o2 ENRICHMENT at [21%] edits in place, with the dial running 21 to 100.
    // i:e RATIO at [1:2.0] edits in place, on the ladder.
    // PEEP at [5 cmH2O] edits in place, with the dial running 0 to 20.
    // VENT. MODE at SIMV vc ps opens the mode sub-screen and returns here.
    // PATIENT INTERFACE at INVASIVE opens the interface sub-screen and returns here.
    // PATIENT WEIGHT at 70 kg opens the weight sub-screen and returns here.
    // rows 0 to 2 are editable value fields, and rows 3 to 5 are navigating rows, whose value shows the current
    // setting and whose middle-click opens the matching sub-screen. all six register as fields, so the one dial and
    // one painter select and highlight them uniformly. fn_ventpanellistclick reads ACME_vent_paramsNav to tell them
    // apart.
    case "params": {
        private _tP  = uiNamespace getVariable ["ACME_vent_target", ACE_player];
        private _fio = if (isNull _tP) then { uiNamespace getVariable ["ACME_vent_fio2", 21] } else { _tP getVariable ["ACME_vent_fio2", 21] };
        private _ieP = if (isNull _tP) then { 2.0 } else { _tP getVariable ["ACME_vent_ie", 2.0] };
        private _pep = if (isNull _tP) then { 5 } else { _tP getVariable ["ACME_vent_peep", 5] };
        private _mod = if (isNull _tP) then { "SIMV VC PS" } else { _tP getVariable ["ACME_vent_mode", "SIMV VC PS"] };
        private _ifc = if (isNull _tP) then { "INVASIVE" } else { _tP getVariable ["ACME_vent_iface", "INVASIVE"] };
        private _wgt = if (isNull _tP) then { 70 } else { _tP getVariable ["ACME_vent_weight", 70] };
        // interface names are long, so they are abbreviated for the readout and the value fits beside its label.
        private _ifcShort = switch (_ifc) do {
            case "NON INVASIVE": { "NON-INV" };
            case "NEBULIZER":    { "NEB" };
            default { "INVASIVE" };
        };
        // two pages of three, at the standard row pitch. the split is the natural one the screen already had: page 1 is
        // the three values the dial edits in place, and page 2 is the three that open a sub-screen.
        // it uses the same text size as the ALERTS screen, with no solving and no per-page scaling. _fVal stays at the
        // shared 0.13 and units at 0.091, which is what every other screen on this device uses. an earlier pass derived
        // a font per page, and while it never overlapped, it made PARAMS the only screen with its own type size and
        // shrank the unit to the point of being unreadable.
        // the room to do that comes from the right edge. on this screen only, the value column runs to 0.99 instead of
        // the usual 0.83, which is how the real device draws it, with values sitting hard against the right of the
        // glass. the left edge keeps its normal padding, so the label column is unchanged.
        // at 0.13 the screen holds about 15.8 characters, so labels are abbreviated to fit rather than the type being
        // shrunk to fit them. every row is checked against that budget:
        // o2 ENRICH. is 13.7, i:e RATIO is 15.0, PEEP is 9.5 and p. supp. is 13.5.
        // TRIGGER is 15.5, MODE is 14.0, interf. is 15.0 and WEIGHT is 10.4.
        _fVal  = 0.13;
        _fUnit = 0.091;
        _boxH  = 0.13;
        _rightEdge = 0.99;  // PARAMS only. every other screen keeps 0.83, set above and untouched.
        _padX = 0.005;  // PARAMS only. it is half the universal padding, because these boxes hold short numbers, and the
                              // wide padding was reserving room the labels needed. it still clears a two-digit value comfortably, which is the
                              // most any dial on this screen produces bar the i:e ratio.

        private _pg = uiNamespace getVariable ["ACME_vent_paramsPage", 0];
        private _psup = if (isNull _tP) then { 10 } else { _tP getVariable ["ACME_vent_psup", 10] };
        private _trig = if (isNull _tP) then {missionNamespace getVariable ["ACME_vent_trigSensCmH2O", -2]} else {_tP getVariable ["ACME_vent_trigSensCmH2O", missionNamespace getVariable ["ACME_vent_trigSensCmH2O", -2]]};

        // the format is [label, value text, max value chars, unit text with "" for none, opens-a-sub-screen].
        // the labels are spelled out. the abbreviations were bought with space the value boxes were wasting, because
        // each box was sized for a string far wider than its dial can ever produce. a field whose dial tops out at two
        // digits does not need room for eight characters, so the boxes are sized to what the value actually reaches and
        // the labels get the difference.
        // max chars is the widest the dial can produce rather than the widest thing that could ever be typed:
        // o2 runs 21 to 100, so 3. PEEP runs 0 to 20, so 2. p. SUPPORT runs 0 to 50, so 2. WEIGHT is 3. TRIGGER holds
        // "-0.25", so 5.
        // i:e keeps 6 for "1:0.33", which really is that wide, and it was not asked to change.
        // there are five per page, split by what the row does rather than by what happened to fit. page 1 is everything
        // the dial edits in place and page 2 is everything that opens a sub-screen. TRIGGER moved from page 2 to page 1
        // because it edits in place and belonged with its own kind, which also removes the page-2 row offset the knob
        // used to need.
        private _rowsP = if (_pg == 0) then {[
            ["O2 ENRICHMENT", str _fio,                            3, "%",     false],
            ["I:E RATIO",     ([_ieP] call ACME_fnc_ventFormatIE), 6, "",      false],
            ["PEEP",          str _pep,                            2, "cmH2O", false],
            ["P. SUPPORT",    str _psup,                           2, "cmH2O", false],
            // TRIGGER reserved 5 characters for "-0.25", which made its box visibly wider and taller-looking than every
            // other value on the screen. the reserve is a multiplier on character width rather than a character count, so
            // it takes a fraction. 4.0 is a three-digit box plus one character for the minus sign, which is exactly what
            // this field needs and nothing more. the reserve assumes every glyph is a full digit wide, and the two widest
            // ladder steps are "-0.25" and "-1.5", where a minus and a full stop are both far narrower than a digit, so
            // they land inside 4.0 in practice. raise it back toward 5 if any step looks tight in game.
            ["TRIGGER",       (if (_trig == 0) then {"OFF"} else {str _trig}), 4.0, (if (_trig == 0) then {""} else {"cmH2O"}), false]
        ]} else {[
            // sized to the actual string rather than to a reserved maximum. these only ever repaint on returning from their
            // sub-screen, never under a turning dial, so there is nothing to keep a stable width for and the reserve was
            // just stealing room from the label beside it.
            ["MODE",          _mod,                     count _mod,            "", true ],
            ["INTERFACE",     _ifcShort,           count _ifcShort,            "", true ],
            ["WEIGHT",        str _wgt,                             3, "kg",   true ]
        ]};
        if (((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])})) then {
            _rowsP = if (_pg == 0) then {[
                ["O2 ENRICHMENT", "AUTO", 4, "", false],
                ["I:E RATIO", "AUTO", 4, "", false],
                ["PEEP", "AUTO", 4, "", false],
                ["P. SUPPORT", "AUTO", 4, "", false],
                ["TRIGGER", "AUTO", 4, "", false]
            ]} else {[
                ["MODE", "SIMPLE", 6, "", false],
                ["INTERFACE", "AUTO", 4, "", false],
                ["WEIGHT", "AUTO", 4, "", false]
            ]};
        };

        // the same five-row ladder the ALERTS screens use, on both pages. a page with three rows leaves the last two
        // positions empty rather than spreading three rows over the whole window, so the row pitch never changes as you
        // move between pages and the panel stops changing shape under you.
        private _ly = [0.150, 0.291, 0.432, 0.573, 0.714];
        private _navFlags = [];
        {
            _x params ["_lb","_vt","_mx","_un","_nv"];
            [_leftEdge, _ly select _forEachIndex, _lb] call _mkLabel;
            private _pieces = [["val", _mx, _vt, _forEachIndex]];
            if (_un != "") then {
                // a one-character unit sits hard against its number. the percent sign belongs to the figure, and at the normal
                // gap it drifted far enough right to be clipped by the edge of the glass.
                _pieces pushBack ["gap", (if ((count _un) <= 1) then { 0.001 } else { 0.006 })];
                _pieces pushBack ["txt", _un, _fUnit, _unitC];
            };
            [_ly select _forEachIndex, _pieces] call _cluster;
            _navFlags pushBack _nv;
        } forEach _rowsP;

        uiNamespace setVariable ["ACME_vent_paramsNav", _navFlags];
        uiNamespace setVariable ["ACME_vent_listCount", count _rowsP];
        uiNamespace setVariable ["ACME_vent_editingParam", -1];
    };

    // ALERTS, page 1 of 2.
    // [6] < rr < [25] BPM, with both bounds editable.
    // PRESSURE, a printed header.
    // LIMIT at [40] cmH2O.
    // ALERT at [40] cmH2O.
    // INV i:e at [on].
    case "alerts": {
        private _t = uiNamespace getVariable ["ACME_vent_target", ACE_player];
        private _rrLo = _t getVariable ["ACME_vent_alertRRLow", 6];
        private _rrHi = _t getVariable ["ACME_vent_alertRRHigh", 25];
        private _pLim = _t getVariable ["ACME_vent_alertPLimit", 40];
        private _simple = ((missionNamespace getVariable ["ACME_vent_simpleMode", false]) && {!((uiNamespace getVariable ["ACME_vent_target", objNull]) getVariable ["ACME_vent_nivMask", false])});
        private _pAlt = _t getVariable ["ACME_vent_alertPAlert", 40];
        private _inv  = _t getVariable ["ACME_vent_alertInvIE", true];
        private _ly = [0.150, 0.291, 0.432, 0.573, 0.714];

        [_ly select 0, [
            ["val", 2, str _rrLo, 0],
            ["gap", _gap],
            ["txt", "< RR <", _fVal, _white],
            ["gap", _gap],
            ["val", 2, str _rrHi, 1],
            ["gap", _gap * 0.7],
            ["txt", "BPM", _fUnit, _unitC]
        ]] call _cluster;

        [_leftEdge, _ly select 1, "PRESSURE"] call _mkLabel;

        [_indent, _ly select 2, "LIMIT"] call _mkLabel;
        [_ly select 2, [
            ["val", (if (_simple) then {4} else {2}), (if (_simple) then {"AUTO"} else {str _pLim}), 2],
            ["gap", _gap * 0.7],
            ["txt", "cmH2O", _fUnit, _unitC]
        ]] call _cluster;

        [_indent, _ly select 3, "ALERT"] call _mkLabel;
        [_ly select 3, [
            ["val", 2, str _pAlt, 3],
            ["gap", _gap * 0.7],
            ["txt", "cmH2O", _fUnit, _unitC]
        ]] call _cluster;

        [_leftEdge, _ly select 4, "INV I:E"] call _mkLabel;
        [_ly select 4, [
            ["val", 3, (if (_inv) then {"ON"} else {"OFF"}), 4]
        ]] call _cluster;

        uiNamespace setVariable ["ACME_vent_listCount", 5];
    };

    // ALERTS, page 2 of 2.
    // LOW TVe at [85] %.
    // LEAK at [100] %.
    // APNEA t. at [30] s.
    // Both absolute L/min bounds are editable on one line.
    // PEEP: at [5.0] cmH2O.
    case "alerts2": {
        private _t2 = uiNamespace getVariable ["ACME_vent_target", ACE_player];
        private _lowTVe = _t2 getVariable ["ACME_vent_alertLowTVe", 85];
        private _leak   = _t2 getVariable ["ACME_vent_alertLeak", 100];
        private _apnea  = _t2 getVariable ["ACME_vent_alertApnea", 30];
        ([_t2] call ACME_fnc_ventMVLimits) params ["_mvLo", "_mvHi"];
        private _pp2    = _t2 getVariable ["ACME_vent_alertPEEP", 5.0];
        private _ly = [0.150, 0.291, 0.432, 0.573, 0.714];

        [_leftEdge, _ly select 0, "LOW TVe"] call _mkLabel;
        [_ly select 0, [["val", 2, str _lowTVe, 0], ["gap", _gap * 0.7], ["txt", "%", _fUnit, _unitC]]] call _cluster;

        [_leftEdge, _ly select 1, "LEAK"] call _mkLabel;
        [_ly select 1, [["val", 3, str _leak, 1], ["gap", _gap * 0.7], ["txt", "%", _fUnit, _unitC]]] call _cluster;

        [_leftEdge, _ly select 2, "APNEA T."] call _mkLabel;
        [_ly select 2, [["val", 2, str _apnea, 2], ["gap", _gap * 0.7], ["txt", "s", _fUnit, _unitC]]] call _cluster;

        [_ly select 3, [
            ["val", 4, _mvLo toFixed 1, 3],
            ["gap", _gap],
            ["txt", "< MV <", _fVal, _white],
            ["gap", _gap],
            ["val", 4, _mvHi toFixed 1, 4],
            ["gap", _gap * 0.5],
            ["txt", "L/min", _fUnit, _unitC]
        ]] call _cluster;

        [_leftEdge, _ly select 4, "PEEP:"] call _mkLabel;
        [_ly select 4, [["val", 4, _pp2 toFixed 1, 5], ["gap", _gap * 0.7], ["txt", "cmH2O", _fUnit, _unitC]]] call _cluster;

        uiNamespace setVariable ["ACME_vent_listCount", 6];
    };

    // WEIGHT.
    // SELECT with [15] kg and [50] kg.
    // PATIENT with [20] kg and [60] kg.
    // WEIGHT with [30] kg and [70] +.
    // and [40] kg.
    // the dial order runs down column one, 15 to 40, then down column two, 50 to 70+, then onto the tray. only 70+
    // commits, which is the navclick weight rule, and the rest hint, exactly as before.
    case "weight": {
        private _rowsY = [0.165, 0.315, 0.465, 0.615];
        private _wVal = (2 * ([_fVal] call _chW)) + 2*_padX;
        private _fKg = 0.085;
        private _kgY = { params ["_lineY"]; _lineY + (_boxH - _fKg*1.15) * 0.78 };
        // the caption, pale blue like the device.
        private _capC = [0.62, 0.75, 0.88, 1];
        [_leftEdge, 0.315 + (_boxH - 0.105*1.15)*0.5, "SELECT",  0.105, _capC] call _mkStatic;
        [_leftEdge, 0.465 + (_boxH - 0.105*1.15)*0.5, "PATIENT", 0.105, _capC] call _mkStatic;
        [_leftEdge, 0.615 + (_boxH - 0.105*1.15)*0.5, "WEIGHT",  0.105, _capC] call _mkStatic;
        // column one: 15, 20, 30 and 40, with the numbers ending on a shared edge and kg after each.
        private _c1Right = 0.56;
        {
            private _ly = _rowsY select _forEachIndex;
            [_c1Right - _wVal, _ly, 2, _x, _forEachIndex] call _mkVal;
            [_c1Right + 0.008, [_ly] call _kgY, "kg", _fKg, _unitC] call _mkStatic;
        } forEach ["15","20","30","40"];
        // column two: 50, 60 and 70+, in rows 0 to 2.
        private _c2Right = 0.84;
        {
            private _ly = _rowsY select _forEachIndex;
            [_c2Right - _wVal, _ly, 2, _x, 4 + _forEachIndex] call _mkVal;
            private _sfx = if (_x == "70") then { "+" } else { "kg" };
            private _sfxF = if (_sfx == "+") then { _fVal } else { _fKg };
            private _sfxY = if (_sfx == "+") then { _ly + (_boxH - _fVal*1.15)*0.5 } else { [_ly] call _kgY };
            [_c2Right + 0.008, _sfxY, _sfx, _sfxF, (if (_sfx == "+") then { _white } else { _unitC })] call _mkStatic;
        } forEach ["50","60","70"];

        uiNamespace setVariable ["ACME_vent_listCount", 7];
    };
};

uiNamespace setVariable ["ACME_vent_graphBars", _statics];  // the statics ride the teardown list of the router.
uiNamespace setVariable ["ACME_vent_valFields", _fields];  // the values are torn down by the field pass of the router.
