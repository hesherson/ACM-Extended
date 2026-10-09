/* Keep the visual pass after every procedural early return. */
private _acmeNVArgs = if (isNil "_this") then {[]} else {_this};
_acmeNVArgs call {
// the palpation tick. the feel-dot only tracks and colors while the left mouse button is held, through
// ACME_Thora_Palpating, exactly like the iv vein-finder, and otherwise it stays hidden. it colors red, then
// yellow, then green by proximity to the 5th ics accept zone of this side, and records whether the cursor is on
// the zone so a release can mark the site.
disableSerialization;
private _display = uiNamespace getVariable ["ACME_Thora_DLG", displayNull];
if (isNull _display) exitWith {};

// A modal chest procedure cannot remain open after its provider loses valid treatment contact. Closing through the
// common helper guarantees onUnload runs fn_thoraClose, which releases carrier custody and every provider pose.
private _thMedic = uiNamespace getVariable ["ACME_Thora_Medic", objNull];
private _thPatient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
private _kitChanged = !isNull _thPatient && {
    (_thPatient getVariable ["ACME_equipmentKitEpoch", 0]) != (uiNamespace getVariable ["ACME_Thora_PatientKitEpoch", 0])
};
private _invalidContact = _kitChanged || {isNull _thMedic} || {isNull _thPatient} || {!alive _thMedic} || {!local _thMedic}
    || {!([_thMedic] call ace_common_fnc_isPlayer)}
    || {_thMedic getVariable ["ACE_isUnconscious", false]}
    || {([_thPatient] call ACME_fnc_clinicalEpoch) != (uiNamespace getVariable ["ACME_Thora_PrepEpoch", -1])}
    || {isNull objectParent _thMedic && {(_thMedic distance _thPatient) > ace_medical_gui_maxDistance}}
    || {objectParent _thMedic isNotEqualTo objectParent _thPatient};
if (_invalidContact) exitWith {
    [86600] call ACME_fnc_minigameClose;
};

// somebody else worked this chest.
// the per-side incision, prep, opening and tube state is all written to the patient and broadcast, so it already
// replicates. this is what makes an open screen notice it: a version on the patient that no longer matches ours
// means another medic committed something, so repaint from the authoritative state.
// it runs every tick, so it lands within a frame of their commit rather than on a reopen.
// Refresh independent tube/seal inventory and permission state without changing the held tool.
[] call ACME_fnc_thoraUpdateTrayIcons;

private _thPat = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
if (!isNull _thPat) then {
    private _tv = _thPat getVariable ["ACME_thora_ver", 0];
    private _sideSeen = uiNamespace getVariable ["ACME_Thora_Side", "right"];
    private _prepSeen = [_sideSeen, +(_thPat getVariable [format ["ACME_thora_prep_%1", _sideSeen], []])];
    private _closureSeen = [_sideSeen,
        _thPat getVariable [format ["ACME_thora_tube_%1", _sideSeen], false],
        _thPat getVariable [format ["ACME_thora_sealed_%1", _sideSeen], false],
        _thPat getVariable [format ["ACME_thora_closed_%1", _sideSeen], false]];
    if (!(_closureSeen select 2) || {_closureSeen select 1}) then {
        uiNamespace setVariable ["ACME_Thora_Burp", ["", 0, 0, false]];
    };
    // Closure values can arrive separately from the version. Observe the values too.
    if (_tv != (uiNamespace getVariable ["ACME_thora_verSeen", -1])
        || {!(_prepSeen isEqualTo (_display getVariable ["ACME_Thora_PrepSeen", []]))}
        || {!(_closureSeen isEqualTo (_display getVariable ["ACME_Thora_ClosureSeen", []]))}) then {
        uiNamespace setVariable ["ACME_thora_verSeen", _tv];
        _display setVariable ["ACME_Thora_ClosureSeen", _closureSeen];
        _display setVariable ["ACME_Thora_PrepSeen", _prepSeen];
        // Merge remote applied prep even during a stroke, retaining local points that are still awaiting
        // submission/acknowledgement. The incision infection gate reads this same combined buffer.
        private _prepLocal = uiNamespace getVariable ["ACME_Thora_PrepLocal", createHashMap];
        if !(_prepLocal isEqualType createHashMap) then {_prepLocal = createHashMap;};
        private _mergedPrep = +(_prepSeen select 1);
        {_mergedPrep pushBackUnique _x;} forEach (_prepLocal getOrDefault [_sideSeen, []]);
        if (count _mergedPrep > 130) then {_mergedPrep resize 130;};
        _prepLocal set [_sideSeen, _mergedPrep];
        uiNamespace setVariable ["ACME_Thora_PrepLocal", _prepLocal];
        [] call ACME_fnc_thoraRender;
    };
};


// cabin motion. this minigame was simply forgotten when the shake went in, so a thoracostomy in a banking bird was
// the one procedure that stayed perfectly steady, and it is arguably the worst one to do in the air. shake the
// whole panel and keep the body rect in step, so the ics zone, the incision and the blood all ride with the
// chest.
private _thBase = uiNamespace getVariable ["ACME_Thora_BodyRectBase", []];
if (count _thBase >= 4) then {
    ([_display, "ACME_Thora_ShakeBase"] call ACME_fnc_uiShakeApply) params ["_tdx", "_tdy"];
    _thBase params ["_tbx", "_tby", "_tbw", "_tbh"];
    uiNamespace setVariable ["ACME_Thora_BodyRect", [_tbx + _tdx, _tby + _tdy, _tbw, _tbh]];
    // The bruise layer rides with the chest during cabin motion.
    [] call ACME_fnc_thoraRenderBruises;
};

// the darkness is drawn first, before any branch can bail out.
// this used to be the last line of this function, below thirteen exitwith branches for the held item, dragging, the
// mode, palpating and more. so in most states the tick returned long before it ever got here, and the screen only
// went dark once you clicked something and the state happened to fall all the way through. that is a control-flow
// bug rather than a lighting one, and it is why you could see everything until you touched the panel.
private _dot = uiNamespace getVariable ["ACME_Thora_Dot", controlNull];
if (isNull _dot) exitWith {};

// the held-tool sprite floats with the cursor whenever a tool is selected.
private _spr = uiNamespace getVariable ["ACME_Thora_ToolSpr", controlNull];
if (!isNull _spr) then {
    private _held = uiNamespace getVariable ["ACME_Thora_Held", ""];
    private _sd = (uiNamespace getVariable ["ACME_Thora_SprData", createHashMap]) getOrDefault [_held, []];
    private _uiS = [] call ACME_fnc_chestSealMouseCoords;
    if (_held isEqualTo "" || {count _sd != 2} || {count _uiS != 2}) then {
        _spr ctrlShow false;
    } else {
        _sd params ["_texRaw", "_frac"];
        _uiS params ["_mx", "_my"];
        private _sside = uiNamespace getVariable ["ACME_Thora_Side", "right"];
        private _texSide = _sside;
        if (_held isEqualTo "tube") then { _texSide = ["left", "right"] select (_sside == "left"); };
        private _tex = if ((_texRaw find "%1") >= 0) then { format [_texRaw, _texSide] } else { _texRaw };
        private _closureArt = [];
        if (_held in ["seal", "tube"]) then {
            _closureArt = [_held, _sside] call ACME_fnc_thoraClosureArt;
            _tex = _closureArt select 0;
            _frac = _closureArt select 1;
        };
        // a held kelly shows the open clamps once the tract has been opened on this side, and closed until then.
        if (_held isEqualTo "kelly") then {
            // a free toggle: closed while lmb is held, meaning clamping in, and open when released. it resets freely.
            _tex = if (uiNamespace getVariable ["ACME_Thora_LMBDown", false]) then {
                "\acm_extended\ui\items\kelly_clamps_closed_ca.paa"
            } else {
                "\acm_extended\ui\items\kelly_clamps_open_ca.paa"
            };
        };
        // the scalpel is mirrored on the left side, because it approaches the incision from the other direction.
        if (_held isEqualTo "scalpel") then {
            _tex = ["\x\acm\addons\airway\ui\surgical_airway\active_scalpel_h.paa", "\acm_extended\ui\items\active_scalpel_h2.paa"] select (_sside == "left");
        };
        // the finger shows the press art while lmb is held, meaning pushing in, and the normal art when released.
        if (_held isEqualTo "finger" && {uiNamespace getVariable ["ACME_Thora_LMBDown", false]}) then {
            _tex = format ["\acm_extended\ui\items\thoracostomy_finger_%1_press_ca.paa", _texSide];
        };
        private _rectS = uiNamespace getVariable ["ACME_Thora_BodyRect", [0, 0, 1, 1]];
        _rectS params ["_bxS", "_byS", "_bwS", "_bhS"];
        private _afS = uiNamespace getVariable ["ACME_Thora_AspectFix", 0.5625];
        private _hS = _bhS * _frac;
        if ((_held isEqualTo "finger" || {_held isEqualTo "kelly"}) && {uiNamespace getVariable ["ACME_Thora_LMBDown", false]}) then {
            _hS = _hS * (missionNamespace getVariable ["ACME_thora_fingerPushScale", 0.85]);
        };
        private _wS = _hS * _afS;
        private _anchorT = if (_held in ["seal", "tube"]) then {
            _closureArt select 2
        } else {
            (missionNamespace getVariable ["ACME_thora_toolAnchors", createHashMap]) getOrDefault [_held, [0.5, 0.5]]
        };
        _anchorT params ["_auT", "_avT"];
        private _px = _mx - (_auT * _wS);
        private _py = _my - (_avT * _hS);
        uiNamespace setVariable ["ACME_Thora_TubeSnap", false];
        if (_held in ["seal", "tube"]) then {
            private _pat = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
            private _inc = if (isNull _pat) then { [] } else { _pat getVariable [format ["ACME_thora_incision_%1", _sside], []] };
            private _openst = if (isNull _pat) then { "" } else { _pat getVariable [format ["ACME_thora_open_%1", _sside], ""] };
            private _closed = !isNull _pat && {
                (_pat getVariable [format ["ACME_thora_tube_%1", _sside], false])
                || {_pat getVariable [format ["ACME_thora_closed_%1", _sside], false]}
                || {(_held == "seal") && {_pat getVariable [format ["ACME_thora_sealed_%1", _sside], false]}}
            };
            if (count _inc == 3 && {_openst == "finger"} && {!_closed}) then {
                _inc params ["_ist", "_iang", "_ilenCm"];
                _ist params ["_isu", "_isv"];
                private _ilenUV = (_ilenCm * (missionNamespace getVariable ["ACME_thora_pxPerCm", 60])) / 2048;
                private _icU = _isu + ((cos _iang) * (_ilenUV / 2));
                private _icV = _isv + ((sin _iang) * (_ilenUV / 2));
                private _cuv = [] call ACME_fnc_thoraCursorUV;
                if (count _cuv == 2) then {
                    _cuv params ["_ccu", "_ccv"];
                    private _dU = _ccu - _icU;
                    private _dV = (_ccv - _icV) * (1 / _afS);
                    private _snapR = if (_held == "seal") then {missionNamespace getVariable ["ACME_thora_sealSnapR", 0.085]} else {missionNamespace getVariable ["ACME_thora_tubeSnapR", 0.055]};
                    if ((sqrt ((_dU * _dU) + (_dV * _dV))) <= _snapR) then {
                        private _anchor = _closureArt select 2;
                        _anchor params ["_au", "_av"];
                        _px = (_bxS + (_icU * _bwS)) - (_au * _wS);
                        _py = (_byS + (_icV * _bhS)) - (_av * _hS);
                        uiNamespace setVariable ["ACME_Thora_TubeSnap", true];
                    };
                };
            };
        };
        _spr ctrlSetText _tex;
        _spr ctrlSetPosition [_px, _py, _wS, _hS];
        _spr ctrlSetTextColor [1, 1, 1, 1];
        _spr ctrlShow true;
        _spr ctrlCommit 0;
    };
};

// an incision in progress: drive the cut. the first drag locks the angle, and then only the length grows, to the
// cap.
if (uiNamespace getVariable ["ACME_Thora_Cutting", false]) exitWith {
    _dot ctrlShow false;
    private _uv = [] call ACME_fnc_thoraCursorUV;
    if (count _uv != 2) exitWith {};
    (uiNamespace getVariable ["ACME_Thora_CutStart", [0, 0]]) params ["_su", "_sv"];
    _uv params ["_cu", "_cv"];
    private _du = _cu - _su;
    private _dv = _cv - _sv;
    private _locked = uiNamespace getVariable ["ACME_Thora_CutLocked", false];
    private _angle = uiNamespace getVariable ["ACME_Thora_CutAngle", 0];
    if (!_locked && {(sqrt ((_du * _du) + (_dv * _dv))) > 0.012}) then {
        _angle = _dv atan2 _du;
        uiNamespace setVariable ["ACME_Thora_CutAngle", _angle];
        uiNamespace setVariable ["ACME_Thora_CutLocked", true];
        _locked = true;
    };
    if (_locked) then {
        private _proj = (_du * (cos _angle)) + (_dv * (sin _angle));
        private _capUV = ((missionNamespace getVariable ["ACME_thora_incisionMaxCm", 5.08]) * (missionNamespace getVariable ["ACME_thora_pxPerCm", 60])) / 2048;
        private _len = ((_proj max (uiNamespace getVariable ["ACME_Thora_CutLen", 0])) max 0) min _capUV;
        uiNamespace setVariable ["ACME_Thora_CutLen", _len];
        [[_su, _sv], _angle, _len] call ACME_fnc_thoraDrawIncision;
    };
};

// chlorhexidine prep: paint an iodine trail everywhere we drag while holding lmb.
if (uiNamespace getVariable ["ACME_Thora_Prepping", false]) exitWith {
    _dot ctrlShow false;
    private _uv = [] call ACME_fnc_thoraCursorUV;
    if (count _uv != 2) exitWith {};
    _uv params ["_cu", "_cv"];
    if (_cu < 0 || {_cu > 1} || {_cv < 0} || {_cv > 1}) exitWith {};
    private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
    // a hard cutoff at the arm: no chlorhexidine below the inferior border of the safety triangle, which is the 5th ics
    // rib curve plus a small margin, so the prep never paints onto the arm.
    private _ribP = missionNamespace getVariable [["ACME_thora_ribRight", "ACME_thora_ribLeft"] select (_side == "left"), [0.5, 0.44, 0.4, 2.0, 0.05]];
    _ribP params ["_pruC", "_prvC", "_prslope", "_prcurv", ""];
    private _pdu = _cu - _pruC;
    private _pRibV = _prvC + (_prslope * _pdu) + (_prcurv * _pdu * _pdu);
    if (_cv > (_pRibV + (missionNamespace getVariable ["ACME_thora_prepArmMargin", 0.06]))) exitWith {};
    private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
    if (isNull _patient) exitWith {};
    private _key = format ["ACME_thora_prep_%1", _side];
    private _prepLocal = uiNamespace getVariable ["ACME_Thora_PrepLocal", createHashMap];
    if !(_prepLocal isEqualType createHashMap) then {_prepLocal = createHashMap;};
    private _pts = +(_prepLocal getOrDefault [_side, +(_patient getVariable [_key, []])]);
    private _last = uiNamespace getVariable ["ACME_Thora_PrepLast", []];
    private _add = (_pts isEqualTo []) || {count _last != 2} || {(sqrt ((((_cu - (_last select 0)) ^ 2)) + (((_cv - (_last select 1)) ^ 2)))) > 0.010};
    if (_add && {(count _pts) < 130}) then {
        _pts pushBack [_cu, _cv];
        _prepLocal set [_side, _pts];
        uiNamespace setVariable ["ACME_Thora_PrepLocal", _prepLocal];
        uiNamespace setVariable ["ACME_Thora_PrepLast", [_cu, _cv]];
        [] call ACME_fnc_thoraRenderPrep;
    };
};

if !(uiNamespace getVariable ["ACME_Thora_Palpating", false]) exitWith {
    _dot ctrlShow false;
    uiNamespace setVariable ["ACME_Thora_OnZone", false];
};

private _rect = uiNamespace getVariable ["ACME_Thora_BodyRect", []];
if (count _rect != 4) exitWith { _dot ctrlShow false; };
_rect params ["_bx", "_by", "_bw", "_bh"];

private _ui = [] call ACME_fnc_chestSealMouseCoords;
if (count _ui != 2) exitWith { _dot ctrlShow false; };
_ui params ["_ux", "_uy"];

private _u = (_ux - _bx) / (_bw max 1e-6);
private _v = (_uy - _by) / (_bh max 1e-6);
private _onBody = (_u >= 0) && {_u <= 1} && {_v >= 0} && {_v <= 1};
if (!_onBody) exitWith {
    _dot ctrlShow false;
    uiNamespace setVariable ["ACME_Thora_OnZone", false];
};

private _side = uiNamespace getVariable ["ACME_Thora_Side", "right"];
private _patZ = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
// the per-patient 5th ics target: a point on the rib curve, picked once at random along the rib and stored. the
// accept zone is a thin strip oriented along the rib tangent, narrow perpendicular and more forgiving lengthwise,
// so the space follows the rib and is genuinely hard to find.
private _tgt = if (isNull _patZ) then { [] } else { _patZ getVariable [format ["ACME_thora_ribTarget_%1", _side], []] };
private _targetConfirmed = count _tgt == 4;
// Keep one proposal while waiting for the owner reply. Regenerating here used to move the palpation target
// and send another owner command every render frame throughout a network round trip.
private _ribPending = uiNamespace getVariable ["ACME_Thora_RibPending", createHashMap];
if (count _tgt != 4) then {_tgt = _ribPending getOrDefault [_side, []];};
if (count _tgt != 4) then {
    private _rib = missionNamespace getVariable [["ACME_thora_ribRight", "ACME_thora_ribLeft"] select (_side == "left"), [0.5, 0.44, 0.4, 2.0, 0.05]];
    _rib params ["_ruC", "_rvC", "_rslope", "_rcurv", "_ruHalf"];
    private _dt = ((random 1.4) - 0.7) * _ruHalf;
    private _uT = _ruC + _dt;
    private _vT = _rvC + (_rslope * _dt) + (_rcurv * _dt * _dt);
    private _dvdu = _rslope + (2 * _rcurv * _dt);
    private _tl = sqrt (1 + (_dvdu * _dvdu));
    _tgt = [_uT, _vT, 1 / _tl, _dvdu / _tl];
    _ribPending set [_side, _tgt];
    uiNamespace setVariable ["ACME_Thora_RibPending", _ribPending];
    if (!isNull _patZ) then {
        [_patZ, _side, "ribTarget", _tgt, uiNamespace getVariable ["ACME_Thora_PrepEpoch", -1]] call ACME_fnc_thoraSideStateCommit;
    };
};
_tgt params ["_tU", "_tV", "_tTx", "_tTy"];
private _zAlong = missionNamespace getVariable ["ACME_thora_zoneAlong", 0.045];
private _zPerp = missionNamespace getVariable ["ACME_thora_zonePerp", 0.011];
private _dxu = _u - _tU;
private _dyv = _v - _tV;
private _along = (_dxu * _tTx) + (_dyv * _tTy);
private _perp = (_dxu * (- _tTy)) + (_dyv * _tTx);
private _d = sqrt (((_along / (_zAlong max 1e-6)) ^ 2) + ((_perp / (_zPerp max 1e-6)) ^ 2));

private _dw = uiNamespace getVariable ["ACME_Thora_DotW", 0.014];
private _dh = uiNamespace getVariable ["ACME_Thora_DotH", 0.02];
_dot ctrlSetPosition [_ux - (_dw / 2), _uy - (_dh / 2), _dw, _dh];
_dot ctrlCommit 0;
_dot ctrlShow true;

// Another viewer's proposal may win at the owner. Do not accept a palpation mark against provisional anatomy.
private _onZone = _targetConfirmed && {_d <= 1};
uiNamespace setVariable ["ACME_Thora_OnZone", _onZone];
uiNamespace setVariable ["ACME_Thora_CurUV", [_u, _v]];

private _col = if (_onZone) then {
    [0.20, 0.90, 0.28, 0.95]
} else {
    private _t = (1 - ((_d - 1) / 1.5)) max 0 min 1;
    [1, (0.15 + (0.70 * _t)) min 0.85, 0.15, (0.55 + (0.35 * _t))]
};
_dot ctrlSetTextColor _col;

// ACE darkness. it was forgotten here exactly like the shake was. a thoracostomy by feel, in a blacked-out cabin,
// is the procedure this whole system exists to make you respect.

};
[uiNamespace getVariable ["ACME_Thora_DLG", displayNull], [], "ACME_Thora_Shade"] call ACME_fnc_darknessShade;
[uiNamespace getVariable ["ACME_Thora_DLG", displayNull]] call ACME_fnc_minigameVisionTick;
