/* Keep the visual pass after every procedural early return. */
private _acmeNVArgs = if (isNil "_this") then {[]} else {_this};
_acmeNVArgs call {
params ["_args", "_h"];
disableSerialization;

private _display = uiNamespace getVariable ["ACME_CS_DLG", displayNull];
if (isNull _display || {_display isNotEqualTo (_args param [0, displayNull])}
    || {_h != (uiNamespace getVariable ["ACME_CS_PFH", -1])}) exitWith {[_h] call CBA_fnc_removePerFrameHandler;};
private _medic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
if (isNull _medic || {!alive _medic} || {_medic isNotEqualTo ACE_player}
    || {_medic getVariable ["ACE_isUnconscious", false]}
    || {isNull (uiNamespace getVariable ["ACME_CS_Patient", objNull])}) exitWith {
    _display closeDisplay 2;
};

// MOVING OFF A SEAL RELEASES ITS PEEL LOCK, AND THAT IS THE ONLY RELEASE.
// fn_chestSealScroll locks the corner to the direction of the first notch on a seal and holds that lock even
// when the peel is rolled back to flat, so rolling hard past flat cannot start a fresh peel on the other corner.
// something has to let go of it, and moving the cursor off the seal is the honest input for that: you have
// stopped working this one.
// it also lays the seal flat, so a half peeled corner cannot be stranded on a casualty by walking away from it.
// this is per frame and it is guarded on a peel actually being active, which is rare, so the search below runs
// almost never. it is NOT a timer: nothing here counts elapsed time and a peel left alone under the cursor stays
// exactly where the medic put it.
private _burpLock = uiNamespace getVariable ["ACME_CS_BurpIdx", -1];
if (_burpLock >= 0) then {
    if (([] call ACME_fnc_chestSealSealAt) != _burpLock) then {
        uiNamespace setVariable ["ACME_CS_BurpIdx", -1];
        uiNamespace setVariable ["ACME_CS_BurpFrame", 0];
        uiNamespace setVariable ["ACME_CS_BurpFired", false];
        uiNamespace setVariable ["ACME_CS_BurpDir", 0];
        [] call ACME_fnc_chestSealRender;
    };
};

// THE BURP HAS NO TIMER AND THIS TICK DOES NOT TOUCH IT BEYOND THE RELEASE ABOVE.
// the peel is one frame per scroll notch, held in ACME_CS_BurpFrame and driven entirely by fn_chestSealScroll,
// which calls fn_chestSealRender itself on every notch.
// a timed peel used to live here and it could not have worked. fn_chestSealRender is EVENT DRIVEN and is never
// called per frame, so a texture picked from elapsed time was written once and never advanced. the same block
// also carried a safety close on a timeout, which is what let a peeled seal drop by itself.
// nothing about a peel belongs in a per frame handler now. it moves when the medic moves the wheel and at no
// other moment.

private _patient = uiNamespace getVariable ["ACME_CS_Patient", objNull];
if (isNull _patient) exitWith {closeDialog 0;};

// The procedure diagram is explicit-state only. During a physical roll, hold the requested endpoint; once the
// animation finishes do NOT reclassify from transient body geometry. This prevents external/ambiguous animation
// states from silently flipping the procedural canvas.
private _uiSide = uiNamespace getVariable ["ACME_CS_Side", "front"];
private _flipUntil = uiNamespace getVariable ["ACME_CS_FlipLockedUntil", 0];
private _flipTarget = uiNamespace getVariable ["ACME_CS_FlipTarget", ""];
private _flipLocked = (_flipUntil isEqualType 0) && {_flipUntil > diag_tickTime} && {_flipTarget in ["front","back"]};
if (_flipLocked && {_uiSide != _flipTarget}) then {
    uiNamespace setVariable ["ACME_CS_Side", _flipTarget];
    [] call ACME_fnc_chestSealRender;
};

// the darkness is drawn first, above every branch that can bail out, the mouse-validity guards below included.
// this used to be the last line of this function, beneath seven exitwith branches. in most states the tick
// returned long before reaching it, so the screen only went dark once you clicked and the state happened to fall
// all the way through. that is a control-flow bug rather than a lighting one.

private _isFiniteNumber = {
    params ["_value"];
    ((typeName _value) isEqualTo "SCALAR") && {finite _value}
};

// Live authoritative snapshots are applied on receipt and checked every render tick.
[_patient, _patient getVariable ["ACME_CS_netSnapshot", []]] call ACME_fnc_chestSealSyncUI;
[_patient, uiNamespace getVariable ["ACME_CS_Side", "front"], uiNamespace getVariable ["ACME_CS_BodyRect", [0,0,0,0]]] call ACME_fnc_chestSealPresenceRender;

private _dots = uiNamespace getVariable ["ACME_CS_Dots", []];
private _hideDots = {
    {if (!isNull _x) then {_x ctrlShow false;};} forEach _dots;
};
private _resetDragFrame = {
    call _hideDots;
    uiNamespace setVariable ["ACME_CS_DragPt", []];
    uiNamespace setVariable ["ACME_CS_DragLast", -1];
    uiNamespace setVariable ["ACME_CS_ArchBlend", 0];
};

private _mouse = [[], false] call ACME_fnc_chestSealMouseCoords;
if !(_mouse isEqualType [] && {count _mouse >= 2}) exitWith {call _resetDragFrame;};
_mouse params ["_mx", "_my"];
if !(([_mx] call _isFiniteNumber) && {[_my] call _isFiniteNumber}) exitWith {call _resetDragFrame;};

private _af = uiNamespace getVariable ["ACME_CS_AspectFix", 0.5625];
if !(([_af] call _isFiniteNumber) && {_af > 0.05} && {_af < 4}) then {_af = 0.5625;};

// vehicle motion: the casualty moves and your hand does not.
// it is applied before anything is drawn or hit-tested, so the body art and the hit zones move together. you do
// not miss because the game nudged your click, you miss because the chest you were aiming at is no longer there.
// in a hard bank, forget it and wait for straight and level, like a real crew would.
private _mBase = uiNamespace getVariable ["ACME_CS_BodyRectBase", []];
if (count _mBase >= 4) then {
    ([_display, "ACME_CS_ShakeBase"] call ACME_fnc_uiShakeApply) params ["_mdx", "_mdy"];
    _mBase params ["_mbx", "_mby", "_mbw", "_mbh"];
    uiNamespace setVariable ["ACME_CS_BodyRect", [_mbx + _mdx, _mby + _mdy, _mbw, _mbh]];
};

private _bodyRect = uiNamespace getVariable ["ACME_CS_BodyRect", [0,0,0,0]];
private _bodyValid = _bodyRect isEqualType [] && {count _bodyRect >= 4};
private _bx = 0;
private _by = 0;
private _bw = 0;
private _bh = 0;
if (_bodyValid) then {
    _bx = _bodyRect select 0;
    _by = _bodyRect select 1;
    _bw = _bodyRect select 2;
    _bh = _bodyRect select 3;
    _bodyValid = ([_bx] call _isFiniteNumber) && {[_by] call _isFiniteNumber} && {[_bw] call _isFiniteNumber} && {[_bh] call _isFiniteNumber} && {_bw > 0} && {_bh > 0};
};

private _heldSeal = uiNamespace getVariable ["ACME_CS_Held", false];
private _heldSpear = uiNamespace getVariable ["ACME_CS_SpearHeld", false];

private _curSeal = uiNamespace getVariable ["ACME_CS_CursorSeal", controlNull];
if (!isNull _curSeal) then {
    if (_heldSeal) then {
        private _sw = uiNamespace getVariable ["ACME_CS_SealW", 0.03];
        private _sh = uiNamespace getVariable ["ACME_CS_SealH", 0.05];
        if !(([_sw] call _isFiniteNumber) && {_sw > 0}) then {_sw = 0.03;};
        if !(([_sh] call _isFiniteNumber) && {_sh > 0}) then {_sh = 0.05;};
        private _sealX = _mx - (_sw / 2);
        private _sealY = _my - (_sh / 2);
        if (([_sealX] call _isFiniteNumber) && {[_sealY] call _isFiniteNumber}) then {
            _curSeal ctrlSetTextColor ([[1,1,1,0.95]] call ACME_fnc_cbColor);
            _curSeal ctrlSetPosition [_sealX, _sealY, _sw, _sh];
            _curSeal ctrlCommit 0;
            _curSeal ctrlShow true;
        } else {
            _curSeal ctrlShow false;
        };
    } else {
        _curSeal ctrlShow false;
    };
};

private _curSpear = uiNamespace getVariable ["ACME_CS_CursorSpear", controlNull];
if (!isNull _curSpear) then {
    private _front = (uiNamespace getVariable ["ACME_CS_Side", "front"]) == "front";
    if (_heldSpear && {_bodyValid} && {_front}) then {
        private _onBodyNow = (_mx >= _bx) && {_mx <= (_bx + _bw)} && {_my >= _by} && {_my <= (_by + _bh)};
        private _patientSide = if (!_onBodyNow) then {"left"} else {if (_mx >= (_bx + _bw / 2)) then {"left"} else {"right"}};
        private _target = if (_patientSide == "left") then {
            uiNamespace getVariable ["ACME_CS_NCDTargetLeft", [0.57421875, 0.29296875]]
        } else {
            uiNamespace getVariable ["ACME_CS_NCDTargetRight", [0.4140625, 0.29296875]]
        };
        _target params ["_tx", "_ty"];
        private _targetX = _bx + (_bw * _tx);
        private _targetY = _by + (_bh * _ty);
        private _dx = (_mx - _targetX) / _af;
        private _dy = _my - _targetY;
        private _dist = 1e9;
        if (([_dx] call _isFiniteNumber) && {[_dy] call _isFiniteNumber}) then {
            private _distSq = (_dx * _dx + _dy * _dy) max 0;
            if ([_distSq] call _isFiniteNumber) then {_dist = sqrt _distSq;};
        };
        private _placeR = uiNamespace getVariable ["ACME_CS_NCDPlaceR", _bh * 0.018];
        private _fadeR = uiNamespace getVariable ["ACME_CS_NCDFadeR", _bh * 0.19];
        if !(([_placeR] call _isFiniteNumber) && {_placeR > 0}) then {_placeR = _bh * 0.018;};
        if !(([_fadeR] call _isFiniteNumber) && {_fadeR > _placeR}) then {_fadeR = _bh * 0.19;};
        private _alpha = 0.50;
        if (([_dist] call _isFiniteNumber) && {_dist <= _fadeR}) then {
            private _denom = (_fadeR - _placeR) max 0.000001;
            private _proximity = (1 - (((_dist - _placeR) max 0) / _denom)) max 0 min 1;
            _alpha = 0.50 + (0.50 * _proximity);
            if (_dist <= _placeR) then {_alpha = 1;};
        };
        _curSpear ctrlSetText (if (_patientSide == "left") then {"\acm_extended\ui\items\nar_spear_left_ca.paa"} else {"\acm_extended\ui\items\nar_spear_right_ca.paa"});
        _curSpear ctrlSetTextColor [1,1,1,_alpha];
        // anchor the sprite so the needle tip sits at the cursor, using the measured tip fraction within the body-sized
        // canvas, so aiming the cursor at the 5th ics aims the tip. it is mirrored per side.
        private _tipFx = if (_patientSide == "left") then {0.4502} else {0.5493};
        private _tipFy = 0.4971;
        _curSpear ctrlSetPosition [_mx - (_bw * _tipFx), _my - (_bh * _tipFy), _bw, _bh];
        _curSpear ctrlCommit 0;
        _curSpear ctrlShow true;
    } else {
        _curSpear ctrlShow false;
    };
};

if (_heldSeal || {_heldSpear} || {!(uiNamespace getVariable ["ACME_CS_Dragging", false])}) exitWith {
    // Tool/idle/burp presence used to sit BELOW this exit and therefore never ran.
    // A stationary burp still heartbeats; released hands send an empty point list.
    private _tool = if (_heldSpear) then {"spear"} else {if (_heldSeal) then {"seal"} else {"finger"}};
    private _pts = [];
    if (_bodyValid && {_heldSeal || {_heldSpear}}) then {
        private _nx = (_mx - _bx) / _bw;
        private _ny = (_my - _by) / _bh;
        if (_nx >= -0.1 && {_nx <= 1.1} && {_ny >= -0.1} && {_ny <= 1.1}) then { _pts = [[_nx, _ny]]; };
    };
    [_patient, uiNamespace getVariable ["ACME_CS_Side", "front"], _tool, _pts] call ACME_fnc_chestSealPresenceSend;
    call _resetDragFrame;
};
if (!_bodyValid) exitWith {call _resetDragFrame;};

private _now = diag_tickTime;
if !([_now] call _isFiniteNumber) exitWith {call _resetDragFrame;};
private _last = uiNamespace getVariable ["ACME_CS_DragLast", -1];
if !([_last] call _isFiniteNumber) then {_last = -1;};
private _dt = if (_last < 0) then {0} else {(_now - _last) max 0 min 0.2};
if !([_dt] call _isFiniteNumber) then {_dt = 0;};
uiNamespace setVariable ["ACME_CS_DragLast", _now];

private _pt = uiNamespace getVariable ["ACME_CS_DragPt", []];
if !(_pt isEqualType [] && {count _pt >= 2}) then {_pt = [_mx, _my];};
_pt params ["_px", "_py"];
if !([_px] call _isFiniteNumber) then {_px = _mx;};
if !([_py] call _isFiniteNumber) then {_py = _my;};

// a heavy drag. distance still matters, and the gain and cap are softened so the rake no longer accelerates
// aggressively just because the cursor gets pulled farther from the fingertip cluster.
private _baseRate = uiNamespace getVariable ["ACME_CS_DragBaseRate", 0.95];
private _gainRate = uiNamespace getVariable ["ACME_CS_DragGainRate", 2.4];
private _maxRate  = uiNamespace getVariable ["ACME_CS_DragMaxRate", 2.8];
if !(([_baseRate] call _isFiniteNumber) && {_baseRate >= 0}) then {_baseRate = 0.95;};
if !(([_gainRate] call _isFiniteNumber) && {_gainRate >= 0}) then {_gainRate = 2.4;};
if !(([_maxRate]  call _isFiniteNumber) && {_maxRate  > 0}) then {_maxRate = 2.8;};
private _oldPx = _px;
private _oldPy = _py;
private _lagX = _mx - _px;
private _lagY = _my - _py;
private _lag = sqrt (((_lagX * _lagX) + (_lagY * _lagY)) max 0);
private _lagNorm = if (_bh > 0 && {[_lag] call _isFiniteNumber}) then {_lag / _bh} else {0};
private _lagDenom = uiNamespace getVariable ["ACME_CS_DragLagDenom", 0.36];
if !(([_lagDenom] call _isFiniteNumber) && {_lagDenom > 0.01}) then {_lagDenom = 0.36;};
private _lagCurve = ((_lagNorm max 0) / ((_lagNorm max 0) + _lagDenom)) min 1;
private _rate = (_baseRate + (_gainRate * _lagCurve)) min _maxRate;
// A second update at the same timestamp must not snap the resisted finger to the cursor.
private _f = ((_rate * _dt) max 0) min 1;
if !([_f] call _isFiniteNumber) then {_f = 1;};
_px = _px + (_lagX * _f);
_py = _py + (_lagY * _f);
if !(([_px] call _isFiniteNumber) && {[_py] call _isFiniteNumber}) then {
    _px = _mx;
    _py = _my;
};
uiNamespace setVariable ["ACME_CS_DragPt", [_px, _py]];

// a downward rake motion flattens the four fingertips into a straighter row. when the drag slows or stops, the
// fingertips ease back into the default arched hand shape.
private _archBlendPrev = uiNamespace getVariable ["ACME_CS_ArchBlend", 0];
if !(([_archBlendPrev] call _isFiniteNumber) && {_archBlendPrev >= 0}) then {_archBlendPrev = 0;};
private _moveY = _py - _oldPy;
private _downSpeed = if (_dt > 0 && {_bh > 0} && {[_moveY] call _isFiniteNumber}) then {((_moveY / _dt) / _bh) max 0} else {0};
private _archTarget = (_downSpeed / 0.55) max 0 min 1;
private _archRate = if (_archTarget > _archBlendPrev) then {8.0} else {3.0};
private _archBlend = _archBlendPrev + ((_archTarget - _archBlendPrev) * (((_archRate * _dt) max 0) min 1));
if !([_archBlend] call _isFiniteNumber) then {_archBlend = 0;};
_archBlend = _archBlend max 0 min 1;
uiNamespace setVariable ["ACME_CS_ArchBlend", _archBlend];

private _dotW = uiNamespace getVariable ["ACME_CS_DotW", 0.006];
private _dotH = uiNamespace getVariable ["ACME_CS_DotH", 0.011];
if !(([_dotW] call _isFiniteNumber) && {_dotW > 0}) then {_dotW = 0.006;};
if !(([_dotH] call _isFiniteNumber) && {_dotH > 0}) then {_dotH = 0.011;};
// the hand on the chest shows on left click and on nothing else. it is the four-finger rake.
// the right button used to put a single finger on the chest. it does not any more, because a hand appearing
// under the cursor without the medic asking for it reads as a bug.
// note that lmb only rakes when bare-handed, because while a seal or a spear is in hand, lmb is the place action
// and no rake occurs, which mousedown handles.
// to bring the one-finger feeler back, restore the rmb case below.
// the hand on the chest is whichever mouse button is held. lmb is the four-finger rake and rmb is the single
// finger feeler. neither held means no hand on the chest at all.
// note that lmb only rakes when bare-handed, because while a seal or a spear is in hand, lmb is the place action
// and no rake occurs, which mousedown handles.
private _lmb = uiNamespace getVariable ["ACME_CS_LMB", false];
private _rmb = uiNamespace getVariable ["ACME_CS_RMB", false];
private _mode = switch (true) do {
    case (_heldSeal || _heldSpear): { 0 };  // something is in hand, so no fingers on the chest.
    case (_lmb): { 4 };
    case (_rmb): { 1 };
    default { 0 };
};
uiNamespace setVariable ["ACME_CS_FingerMode", _mode];
// mode 0 means no hand on the chest, because no button is held or something is in hand. an empty layout gives no
// fingertips, so nothing is drawn, nothing is revealed and nothing is broadcast to the other medics.
private _layout = if (_mode == 0) then {[]} else { if (_mode == 1) then {[[0, 0]]} else {
    private _defaultLayout = [[-1.35,-0.62],[-0.45,-1.02],[0.45,-1.02],[1.35,-0.62]];
    private _flatLayout    = [[-1.35,-0.82],[-0.45,-0.82],[0.45,-0.82],[1.35,-0.82]];
    private _out = [];
    {
        private _i = _forEachIndex;
        _x params ["_dx0", "_dy0"];
        (_flatLayout select _i) params ["_dx1", "_dy1"];
        _out pushBack [
            _dx0 + ((_dx1 - _dx0) * _archBlend),
            _dy0 + ((_dy1 - _dy0) * _archBlend)
        ];
    } forEach _defaultLayout;
    _out
}};
private _spacingH = uiNamespace getVariable ["ACME_CS_FingerSpacingH", (_dotH * 0.88)];
if !(([_spacingH] call _isFiniteNumber) && {_spacingH > 0}) then {_spacingH = _dotH * 0.88;};
// the four-finger rake sits slightly above the cursor, so you drag the fingers down the chest to find holes, and
// the single ics feeler sits directly on the cursor for maximum placement accuracy.
private _lift = if (_mode == 1) then {0} else {
    private _lf = uiNamespace getVariable ["ACME_CS_FingerLift", (_dotH * 1.6)];
    if !(([_lf] call _isFiniteNumber) && {_lf >= 0}) then {_lf = _dotH * 1.6;};
    _lf
};
private _fingerPoints = [];
{
    _x params ["_ox", "_oy"];
    private _fingerX = _px + (_ox * _spacingH * _af);
    private _fingerY = (_py - _lift) + (_oy * _spacingH);
    if (([_fingerX] call _isFiniteNumber) && {[_fingerY] call _isFiniteNumber}) then {
        _fingerPoints pushBack [_fingerX, _fingerY];
    };
} forEach _layout;

private _side = uiNamespace getVariable ["ACME_CS_Side", "front"];

// live presence: show every medic working this chest, to every other medic.
// we send the actual computed finger points, _fingerPoints, rather than a cursor position. that means peers see
// the real thing: four dots for the four-finger rake, with its true spread and the way it flattens and trails as
// you drag, or a single dot for the one-finger palpate. rebuilding that from a bare cursor on the receiving end
// would only ever be an approximation.
// the points are normalized to the body rect, so they map correctly onto any resolution or aspect, 32:9 as well
// as 16:9.
if (_bodyValid) then {
    private _toolNow = if (_heldSpear) then {"spear"} else { if (_heldSeal) then {"seal"} else {"finger"} };
    private _pts = [];
    if (_toolNow == "finger") then {
        // the fingertips themselves.
        {
            _x params ["_fpx", "_fpy"];
            _pts pushBack [((_fpx - _bx) / _bw), ((_fpy - _by) / _bh)];
        } forEach _fingerPoints;
    } else {
        // holding something: the tool sits on the cursor.
        _pts pushBack [((_mx - _bx) / _bw), ((_my - _by) / _bh)];
    };
    // only report while we are actually over the body, or we would paint a hand floating in the menu chrome on
    // everyone else's screen.
    private _onBody = (count _pts > 0) && {
        ((_pts select 0) select 0) >= -0.10 && {((_pts select 0) select 0) <= 1.10}
        && {((_pts select 0) select 1) >= -0.10} && {((_pts select 0) select 1) <= 1.10}
    };
    if (_onBody) then {
        [_patient, _side, _toolNow, _pts] call ACME_fnc_chestSealPresenceSend;
    } else {
        [_patient, _side, _toolNow, []] call ACME_fnc_chestSealPresenceSend;
    };

};
private _findR = uiNamespace getVariable ["ACME_CS_FindRadius", (_bh * 0.0075)];
if !(([_findR] call _isFiniteNumber) && {_findR > 0}) then {_findR = _bh * 0.0075;};
// clamp the reveal distance to the actual hole art footprint. this prevents one broad center-chest sweep from
// finding every wound on the thorax, because the cursor and finger center must pass directly over the hidden
// hole.
private _holeMetricW = (uiNamespace getVariable ["ACME_CS_HoleW", (_bh * 0.023 * _af)]) / (_af max 0.05);
private _holeMetricH = uiNamespace getVariable ["ACME_CS_HoleH", (_bh * 0.023)];
if !(([_holeMetricW] call _isFiniteNumber) && {_holeMetricW > 0}) then {_holeMetricW = _bh * 0.023;};
if !(([_holeMetricH] call _isFiniteNumber) && {_holeMetricH > 0}) then {_holeMetricH = _bh * 0.023;};
private _measuredFindR = ((_holeMetricW min _holeMetricH) * 0.32) max (_bh * 0.0045);
_findR = _findR min _measuredFindR;
private _holes = uiNamespace getVariable ["ACME_CS_Holes", []];
private _nearest = 1e9;
private _fingerNearest = [];
{_fingerNearest pushBack 1e9;} forEach _fingerPoints;
private _revealed = false;

// only the four-finger rake reveals occult wounds. the single-finger feeler is purely for locating the 5th
// ics.
if (_mode == 4) then {
{
    if (_x isEqualType [] && {count _x >= 5}) then {
        private _holeIndex = _forEachIndex;
        _x params ["_hSide", "_hx", "_hy", "_found", "_sealed"];
        if (!_sealed && {_hSide == _side} && {[_hx] call _isFiniteNumber} && {[_hy] call _isFiniteNumber}) then {
            private _holeX = _bx + (_bw * _hx);
            private _holeY = _by + (_bh * _hy);
            private _holeNearest = 1e9;
            {
                private _fingerIndex = _forEachIndex;
                _x params ["_fingerX", "_fingerY"];
                private _hdx = (_fingerX - _holeX) / (_af max 0.05);
                private _hdy = _fingerY - _holeY;
                if (([_hdx] call _isFiniteNumber) && {[_hdy] call _isFiniteNumber}) then {
                    private _holeDistSq = (_hdx * _hdx + _hdy * _hdy) max 0;
                    if ([_holeDistSq] call _isFiniteNumber) then {
                        private _holeDist = sqrt _holeDistSq;
                        if ([_holeDist] call _isFiniteNumber) then {
                            _holeNearest = _holeNearest min _holeDist;
                            if (_fingerIndex < count _fingerNearest) then {
                                _fingerNearest set [_fingerIndex, ((_fingerNearest select _fingerIndex) min _holeDist)];
                            };
                        };
                    };
                };
            } forEach _fingerPoints;
            _nearest = _nearest min _holeNearest;
            if (!_found && {_holeNearest <= _findR}) then {
                (_holes select _holeIndex) set [3, true];
                _revealed = true;
            };
        };
    };
} forEach _holes;
};

private _onBody = (_fingerPoints findIf {
    _x params ["_fingerX", "_fingerY"];
    _fingerX >= _bx && {_fingerX <= _bx + _bw} && {_fingerY >= _by} && {_fingerY <= _by + _bh}
}) >= 0;
private _fingerColor = ["danger", 0.95] call ACME_fnc_a11yColor;  // the default click feedback.
if (!_onBody) then {
    _fingerColor = ["inactive", 0.55] call ACME_fnc_a11yColor;  // dim off-body.
} else {
    if (_mode == 1) then {
        // the single-finger feeler stays red until the cursor is very close to a 5th ics target, then brightens to green.
        // it confirms where the NAR SPEAR will land. it is front side only.
        if (_side == "front") then {
            // the feeler greens only when it is on the 5th-ics line, at the correct height, anywhere along the acceptable
            // span. it gates on being within the horizontal span of a side ellipse, then drives the color purely by how
            // close the feeler is to the line in height: red off the line, yellow closing, and green only dead-on. this
            // greens along the whole space and never above or below it, and unlike the old combined-distance test it does
            // not fade back to red at the lateral ends of a valid placement.
            private _fu = (_px - _bx) / _bw;
            private _fv = (_py - _by) / _bh;
            private _ndv = 1e9;  // the smallest normalized height offset among the ellipses we are horizontally inside.
            {
                _x params ["_ecu", "_ecv", "_eru", "_erv"];
                if (_eru > 0 && {_erv > 0} && {[_fu] call _isFiniteNumber} && {[_fv] call _isFiniteNumber}) then {
                    if ((abs ((_fu - _ecu) / _eru)) <= 1) then {  // within the along-the-space span of this side.
                        private _d = abs ((_fv - _ecv) / _erv);
                        if ([_d] call _isFiniteNumber) then {_ndv = _ndv min _d;};
                    };
                };
            } forEach [
                uiNamespace getVariable ["ACME_CS_NCDEllipseLeft",  [0.555, 0.293, 0.052, 0.015]],
                uiNamespace getVariable ["ACME_CS_NCDEllipseRight", [0.445, 0.293, 0.052, 0.015]]
            ];
            if (_ndv <= 1) then {
                private _t = 1 - ((_ndv max 0) min 1);  // 0 at the height edge, rising to 1 dead-on the line.
                // a semantic ramp from bad through warning to correct. the green, blue or mono output depends on the colorblind
                // mode.
                private _from = if (_t < 0.5) then {["danger", 0.92 + (0.08 * _t)] call ACME_fnc_a11yColor} else {["warning", 0.92 + (0.08 * _t)] call ACME_fnc_a11yColor};
                private _to   = if (_t < 0.5) then {["warning", 0.92 + (0.08 * _t)] call ACME_fnc_a11yColor} else {["success", 0.92 + (0.08 * _t)] call ACME_fnc_a11yColor};
                private _tt = if (_t < 0.5) then {_t * 2} else {(_t - 0.5) * 2};
                _from params ["_fr", "_fg", "_fb", "_fa"];
                _to params ["_tr", "_tg", "_tb", "_ta"];
                _fingerColor = [_fr + ((_tr - _fr) * _tt), _fg + ((_tg - _fg) * _tt), _fb + ((_tb - _fb) * _tt), _fa];
            };
        };
    } else {
        if (_nearest <= (_findR * 1.8)) then {_fingerColor = ["warm", 0.98] call ACME_fnc_a11yColor;};
        if (_nearest <= _findR) then {_fingerColor = ["hot", 1.00] call ACME_fnc_a11yColor;};
    };
};

private _fingerColors = [];
private _fingerGlow = uiNamespace getVariable ["ACME_CS_FingerGlow", []];
private _nextFingerGlow = [];
private _decaySeconds = uiNamespace getVariable ["ACME_CS_FingerColorDecay", missionNamespace getVariable ["ACME_CS_fingerColorDecay", 0.28]];
if !(([_decaySeconds] call _isFiniteNumber) && {_decaySeconds > 0.05}) then {_decaySeconds = 0.28;};
{
    _x params ["_fingerX", "_fingerY"];
    private _idx = _forEachIndex;
    private _thisColor = _fingerColor;
    private _glowNow = 0;
    if (_mode == 4) then {
        private _onThisFinger = _fingerX >= _bx && {_fingerX <= _bx + _bw} && {_fingerY >= _by} && {_fingerY <= _by + _bh};
        private _baseColor = if (_onThisFinger) then {["danger", 0.95] call ACME_fnc_a11yColor} else {["inactive", 0.55] call ACME_fnc_a11yColor};
        _thisColor = _baseColor;
        if (_onThisFinger) then {
            private _fd = _fingerNearest param [_idx, 1e9];
            if (_fd <= (_findR * 1.8)) then {
                _glowNow = 0.45 max (1 - ((_fd - _findR) / ((_findR * 0.8) max 0.000001)));
            };
            if (_fd <= _findR) then {_glowNow = 1;};
        };

        private _oldGlow = _fingerGlow param [_idx, 0];
        if !(([_oldGlow] call _isFiniteNumber) && {_oldGlow >= 0}) then {_oldGlow = 0;};
        private _decayedGlow = _oldGlow - (_dt / _decaySeconds);
        private _glow = (_glowNow max _decayedGlow) max 0 min 1;
        _nextFingerGlow pushBack _glow;

        if (_glow > 0) then {
            private _hotColor = if (_glow > 0.72) then {["hot", 1.00] call ACME_fnc_a11yColor} else {["warm", 0.98] call ACME_fnc_a11yColor};
            _baseColor params ["_br", "_bg", "_bb", "_ba"];
            _hotColor params ["_hr", "_hg", "_hb", "_ha"];
            private _t = _glow max 0 min 1;
            _thisColor = [
                _br + ((_hr - _br) * _t),
                _bg + ((_hg - _bg) * _t),
                _bb + ((_hb - _bb) * _t),
                _ba + ((_ha - _ba) * _t)
            ];
        };
    };
    _fingerColors pushBack _thisColor;
} forEach _fingerPoints;
if (_mode == 4) then { uiNamespace setVariable ["ACME_CS_FingerGlow", _nextFingerGlow]; };

{
    if (!isNull _x && {_forEachIndex < count _fingerPoints}) then {
        (_fingerPoints select _forEachIndex) params ["_fingerX", "_fingerY"];
        private _dotX = _fingerX - (_dotW / 2);
        private _dotY = _fingerY - (_dotH / 2);
        if (([_dotX] call _isFiniteNumber) && {[_dotY] call _isFiniteNumber}) then {
            private _dotColor = _fingerColors param [_forEachIndex, _fingerColor];
            _x ctrlSetTextColor _dotColor;
            _x ctrlSetPosition [_dotX, _dotY, _dotW, _dotH];
            _x ctrlCommit 0;
            _x ctrlShow true;
        } else {
            _x ctrlShow false;
        };
    } else {
        if (!isNull _x) then {_x ctrlShow false;};
    };
} forEach _dots;

if (_revealed) then {
    uiNamespace setVariable ["ACME_CS_Holes", _holes];
    private _keys = (_holes select {_x select 3}) apply {[_x] call ACME_fnc_chestSealKey};
    ["reveal", _keys] call ACME_fnc_chestSealRequest;
    playSound "ACME_CS_HoleReveal";
    [] call ACME_fnc_chestSealRender;
};

// darkness. shade the casualty, rather than the panel chrome, by how dark it actually is where the medic is
// kneeling. rake and palpate in the dark and you will find nothing, because you cannot see the chest. put a
// light on it, or have someone else do it, and the chest comes back. it is applied last, so it sits over the
// body art, the holes, the seals and the fingers of the peer medics alike.

};
[uiNamespace getVariable ["ACME_CS_DLG", displayNull], [], "ACME_CS_Shade"] call ACME_fnc_darknessShade;
[uiNamespace getVariable ["ACME_CS_DLG", displayNull]] call ACME_fnc_minigameVisionTick;
